from __future__ import annotations

import getpass
import os
import plistlib
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from .util import atomic_write

LABEL = "org.couchsync"


def command(cfg, task: str) -> list[str]:
    return [sys.executable, "-m", "couchsync", "--config", str(cfg.config.resolve()), task]


def launchd(cfg, task: str) -> dict:
    result = {
        "Label": f"{LABEL}.{task}",
        "ProgramArguments": command(cfg, task),
        "RunAtLoad": True,
        "ProcessType": "Background",
        "Umask": 0o077,
        "StandardOutPath": str(cfg.logs / f"{task}.out.log"),
        "StandardErrorPath": str(cfg.logs / f"{task}.err.log"),
    }
    if task == "sync":
        result["StartInterval"] = cfg.interval
        # Calendar triggers coalesce on wake; worker's due guard prevents excess scraping.
        result["StartCalendarInterval"] = {"Minute": 0}
    else:
        result["KeepAlive"] = True
    return result


def windows_xml(cfg, task: str, user: str | None = None) -> bytes:
    ns = "http://schemas.microsoft.com/windows/2004/02/mit/task"
    ET.register_namespace("", ns)

    def sub(parent, name, text=None, **attrs):
        e = ET.SubElement(parent, f"{{{ns}}}{name}", attrs)
        e.text = text
        return e

    root = ET.Element(f"{{{ns}}}Task", {"version": "1.2"})
    triggers = sub(root, "Triggers")
    trigger = sub(triggers, "LogonTrigger")
    sub(trigger, "Enabled", "true")
    if task == "sync":
        repetition = sub(trigger, "Repetition")
        sub(repetition, "Interval", f"PT{cfg.interval}S")
        sub(repetition, "StopAtDurationEnd", "false")
    principals = sub(root, "Principals")
    principal = sub(principals, "Principal", id="Author")
    sub(principal, "UserId", user or getpass.getuser())
    sub(principal, "LogonType", "InteractiveToken")
    sub(principal, "RunLevel", "LeastPrivilege")
    settings = sub(root, "Settings")
    sub(settings, "MultipleInstancesPolicy", "IgnoreNew")
    sub(settings, "DisallowStartIfOnBatteries", "false")
    sub(settings, "StopIfGoingOnBatteries", "false")
    sub(settings, "StartWhenAvailable", "true")
    sub(settings, "ExecutionTimeLimit", "PT0S" if task == "serve" else "PT30M")
    if task == "serve":
        restart = sub(settings, "RestartOnFailure")
        sub(restart, "Interval", "PT1M")
        sub(restart, "Count", "3")
    actions = sub(root, "Actions", Context="Author")
    action = sub(actions, "Exec")
    args = command(cfg, task)
    sub(action, "Command", args[0])
    sub(action, "Arguments", subprocess.list2cmdline(args[1:]))
    return ET.tostring(root, encoding="utf-16", xml_declaration=True)


def manage(cfg, action: str, task: str = "all") -> None:
    cfg.initialize()
    if task not in {"all", "sync", "serve"}:
        raise ValueError("Unknown service task")
    tasks = ("sync", "serve") if task == "all" else (task,)
    if action == "install" and "sync" in tasks:
        from .scraper.selectors import SelectorError, load

        adapter = load(cfg.selectors, cfg.categories)
        if any("expected_count" in s for s in adapter["sources"]):
            raise SelectorError(
                "The fixed-count first-sync profile is not suitable for hourly work; upgrade-events first"
            )
    for task in tasks:
        if sys.platform == "darwin":
            path = Path.home() / "Library/LaunchAgents" / f"{LABEL}.{task}.plist"
            domain = f"gui/{os.getuid()}"
            target = f"{domain}/{LABEL}.{task}"
            if action == "install":
                if path.exists():
                    raise RuntimeError("Service already installed; uninstall before reinstalling")
                atomic_write(path, plistlib.dumps(launchd(cfg, task)))
                # Installation is separate from starting the service.
                print(f"{task}: installed; run service start --task {task} to load it")
                continue
            args = {
                "start": ["launchctl", "bootstrap", domain, str(path)],
                "stop": ["launchctl", "bootout", target],
                "status": ["launchctl", "print", target],
                "uninstall": ["launchctl", "bootout", target],
            }[action]
            result = subprocess.run(args, check=False, capture_output=True)
            print(f"{task}: {'active' if result.returncode == 0 else 'inactive or action failed'}")
            if action == "uninstall":
                path.unlink(missing_ok=True)
            elif action in {"start", "stop"} and result.returncode:
                raise RuntimeError("launchctl action failed; see service status")
        elif sys.platform == "win32":
            name = f"Couchsync-{task}"
            if action == "install":
                path = cfg.data / f"{task}-task.xml"
                atomic_write(path, windows_xml(cfg, task))
                try:
                    subprocess.run(
                        ["schtasks", "/Create", "/TN", name, "/XML", str(path)], check=True
                    )
                finally:
                    path.unlink(missing_ok=True)
                continue
            verb = {"start": "/Run", "stop": "/End", "status": "/Query", "uninstall": "/Delete"}[
                action
            ]
            args = ["schtasks", verb, "/TN", name]
            if action == "uninstall":
                args.append("/F")
            subprocess.run(args, check=True)
        else:
            raise RuntimeError("Automatic service management supports macOS and Windows")
