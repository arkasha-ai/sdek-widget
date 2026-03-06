#!/usr/bin/env python3
"""
Проверяет просроченные задачи в TickTick и выводит список.
Выход 0 + пустой stdout = нет просроченных
Выход 0 + stdout с задачами = есть просроченные
"""
import os, sys, json, subprocess
from datetime import datetime, timezone
from pathlib import Path

secrets_path = Path.home() / ".openclaw" / "secrets.env"
if secrets_path.exists():
    with open(secrets_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

TICKTICK_SCRIPT = Path.home() / ".openclaw" / "workspace" / "skills" / "ticktick-tasks" / "scripts" / "ticktick.js"

def run_ticktick(args):
    result = subprocess.run(
        ["node", str(TICKTICK_SCRIPT)] + args,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except Exception:
        return None

def main():
    now = datetime.now(timezone.utc)
    overdue = []

    # Получаем все проекты
    projects = run_ticktick(["list-projects"])
    if not projects:
        sys.exit(0)

    project_ids = [p.get("id") for p in projects if p.get("id")]

    for pid in project_ids:
        tasks = run_ticktick(["list-tasks", pid])
        if not tasks:
            continue
        for task in tasks:
            due = task.get("dueDate") or task.get("due_date")
            if not due:
                continue
            try:
                # TickTick format: "2026-03-04T09:00:00.000+0000"
                due_dt = datetime.fromisoformat(due.replace("Z", "+00:00"))
                if due_dt < now:
                    overdue.append({
                        "title": task.get("title", "?"),
                        "due": due_dt.strftime("%d.%m %H:%M"),
                        "project": task.get("projectId", pid)
                    })
            except Exception:
                continue

    if overdue:
        titles = [f"- {t['title']} (было {t['due']})" for t in overdue]
        print("\n".join(titles))

if __name__ == "__main__":
    main()
