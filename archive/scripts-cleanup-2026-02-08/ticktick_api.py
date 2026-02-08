#!/usr/bin/env python3
"""
TickTick API Client - работа с OAuth токенами
"""
import json
import os
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any


TOKEN_FILE = os.path.expanduser("~/.openclaw/workspace/.ticktick_token.json")
BASE_URL = "https://api.ticktick.com"


class TickTickAPI:
    """Клиент для TickTick Open API с OAuth"""
    
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.inbox_id = None
        self._load_tokens()
    
    def _load_tokens(self):
        """Загрузить токены из файла"""
        if not os.path.exists(TOKEN_FILE):
            raise FileNotFoundError(
                f"Token file not found. Run ticktick_oauth.py first."
            )
        
        with open(TOKEN_FILE, 'r') as f:
            tokens = json.load(f)
            self.access_token = tokens.get('access_token')
            self.refresh_token = tokens.get('refresh_token')
    
    def _request(
        self,
        endpoint: str,
        method: str = 'GET',
        data: Optional[Dict] = None
    ) -> Any:
        """Выполнить HTTP запрос к API"""
        url = f"{BASE_URL}{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        request_kwargs = {'headers': headers, 'method': method}
        
        if data:
            request_kwargs['data'] = json.dumps(data).encode('utf-8')
        
        try:
            request = urllib.request.Request(url, **request_kwargs)
            with urllib.request.urlopen(request) as response:
                response_data = response.read().decode('utf-8')
                if response_data:
                    return json.loads(response_data)
                return None
                
        except urllib.error.HTTPError as e:
            if e.code == 204:  # No Content
                return None
            error_body = e.read().decode('utf-8')
            raise Exception(f"API error ({e.code}): {error_body}")
    
    def get_profile(self) -> Dict:
        """Получить профиль пользователя"""
        profile = self._request("/open/v1/user")
        self.inbox_id = profile.get('inboxId')
        return profile
    
    def get_projects(self) -> List[Dict]:
        """Получить все проекты"""
        return self._request("/open/v1/project")
    
    def get_tasks(self, project_id: Optional[str] = None) -> List[Dict]:
        """Получить задачи"""
        if project_id:
            return self._request(f"/open/v1/project/{project_id}/task")
        else:
            # Получить все задачи из всех проектов
            projects = self.get_projects()
            all_tasks = []
            for project in projects:
                tasks = self._request(f"/open/v1/project/{project['id']}/task")
                all_tasks.extend(tasks or [])
            return all_tasks
    
    def create_task(
        self,
        title: str,
        content: str = "",
        project_id: Optional[str] = None,
        due_date: Optional[datetime] = None,
        priority: int = 0,
        tags: Optional[List[str]] = None
    ) -> Dict:
        """
        Создать задачу
        
        priority: 0=none, 1=low, 3=medium, 5=high
        """
        if not project_id:
            profile = self.get_profile()
            project_id = profile['inboxId']
        
        task_data = {
            "title": title,
            "projectId": project_id,
            "priority": priority
        }
        
        if content:
            task_data["content"] = content
        
        if due_date:
            task_data["dueDate"] = due_date.strftime("%Y-%m-%dT%H:%M:%S%z")
        
        if tags:
            task_data["tags"] = tags
        
        return self._request(
            f"/open/v1/project/{project_id}/task",
            method='POST',
            data=task_data
        )
    
    def complete_task(self, project_id: str, task_id: str) -> None:
        """Отметить задачу выполненной"""
        self._request(
            f"/open/v1/project/{project_id}/task/{task_id}/complete",
            method='POST'
        )
    
    def delete_task(self, project_id: str, task_id: str) -> None:
        """Удалить задачу"""
        self._request(
            f"/open/v1/project/{project_id}/task/{task_id}",
            method='DELETE'
        )


class TickTickManager:
    """Высокоуровневый менеджер для работы с TickTick"""
    
    def __init__(self):
        self.api = TickTickAPI()
        self.api.get_profile()  # Инициализация inbox_id
    
    def get_all_tasks(self, completed: bool = False) -> List[Dict]:
        """Получить все задачи"""
        tasks = self.api.get_tasks()
        if completed:
            return [t for t in tasks if t.get('status') == 2]
        return [t for t in tasks if t.get('status') != 2]
    
    def get_overdue_tasks(self) -> List[Dict]:
        """Получить просроченные задачи"""
        now = datetime.now(timezone.utc)
        overdue = []
        
        for task in self.get_all_tasks():
            due_str = task.get('dueDate')
            if due_str:
                try:
                    due_date = datetime.fromisoformat(due_str.replace('Z', '+00:00'))
                    if due_date < now:
                        overdue.append(task)
                except Exception:
                    pass
        
        return overdue
    
    def get_today_tasks(self) -> List[Dict]:
        """Получить задачи на сегодня"""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        today_tasks = []
        for task in self.get_all_tasks():
            due_str = task.get('dueDate')
            if due_str:
                try:
                    due_date = datetime.fromisoformat(due_str.replace('Z', '+00:00'))
                    if today_start <= due_date < today_end:
                        today_tasks.append(task)
                except Exception:
                    pass
        
        return today_tasks
    
    def get_upcoming_tasks(self, days: int = 7) -> List[Dict]:
        """Получить задачи на ближайшие N дней"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=days)
        
        upcoming = []
        for task in self.get_all_tasks():
            due_str = task.get('dueDate')
            if due_str:
                try:
                    due_date = datetime.fromisoformat(due_str.replace('Z', '+00:00'))
                    if now <= due_date <= future:
                        upcoming.append(task)
                except Exception:
                    pass
        
        upcoming.sort(key=lambda t: t.get('dueDate', ''))
        return upcoming
    
    def format_task(self, task: Dict, show_project: bool = False) -> str:
        """Форматировать задачу для вывода"""
        title = task.get('title', 'Untitled')
        priority = task.get('priority', 0)
        due = task.get('dueDate', '')
        
        # Эмодзи приоритета
        priority_emoji = {0: '', 1: '🔵', 3: '🟡', 5: '🔴'}.get(priority, '')
        
        # Дата
        due_str = ''
        if due:
            try:
                due_date = datetime.fromisoformat(due.replace('Z', '+00:00'))
                due_str = f" 📅 {due_date.strftime('%Y-%m-%d %H:%M')}"
            except Exception:
                pass
        
        result = f"{priority_emoji} {title}{due_str}".strip()
        
        if show_project and task.get('projectId'):
            result += f" [Project: {task['projectId']}]"
        
        return result


def main():
    """CLI для тестирования"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  ticktick_api.py list")
        print("  ticktick_api.py overdue")
        print("  ticktick_api.py today")
        print("  ticktick_api.py upcoming [days]")
        print("  ticktick_api.py create <title> [description]")
        print("  ticktick_api.py projects")
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        manager = TickTickManager()
        
        if command == 'list':
            tasks = manager.get_all_tasks()
            print(f"\n📋 Все задачи ({len(tasks)}):\n")
            for task in tasks:
                print(f"  {manager.format_task(task)}")
        
        elif command == 'overdue':
            tasks = manager.get_overdue_tasks()
            print(f"\n⚠️  Просроченные задачи ({len(tasks)}):\n")
            for task in tasks:
                print(f"  {manager.format_task(task)}")
        
        elif command == 'today':
            tasks = manager.get_today_tasks()
            print(f"\n📅 Задачи на сегодня ({len(tasks)}):\n")
            for task in tasks:
                print(f"  {manager.format_task(task)}")
        
        elif command == 'upcoming':
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            tasks = manager.get_upcoming_tasks(days=days)
            print(f"\n🗓️  Задачи на {days} дней ({len(tasks)}):\n")
            for task in tasks:
                print(f"  {manager.format_task(task)}")
        
        elif command == 'create':
            if len(sys.argv) < 3:
                print("Error: title required")
                sys.exit(1)
            
            title = sys.argv[2]
            content = sys.argv[3] if len(sys.argv) > 3 else ""
            
            task = manager.api.create_task(title, content)
            print(f"\n✅ Создана задача: {task['title']}")
        
        elif command == 'projects':
            projects = manager.api.get_projects()
            print(f"\n📁 Проекты ({len(projects)}):\n")
            for project in projects:
                print(f"  • {project.get('name', 'Unknown')}")
        
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
