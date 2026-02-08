#!/usr/bin/env python3
"""
TickTick Integration - работа с неофициальным V2 API
Использует прямую авторизацию username/password без OAuth
"""
import json
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import os


class TickTickClient:
    """Клиент для TickTick V2 API (неофициальный)"""
    
    BASE_URL = "https://api.ticktick.com"
    
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies)
        )
        urllib.request.install_opener(self.opener)
        
        self.inbox_id = None
        self.user_id = None
        self._authenticated = False
    
    def login(self) -> bool:
        """Авторизация через username/password"""
        url = f"{self.BASE_URL}/api/v2/user/signon?wc=true&remember=true"
        
        data = {
            "username": self.username,
            "password": self.password
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
            "Origin": "https://ticktick.com"
        }
        
        try:
            request = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers=headers
            )
            
            with urllib.request.urlopen(request) as response:
                result = json.loads(response.read().decode('utf-8'))
                self.user_id = result.get('userId')
                self.inbox_id = result.get('inboxId')
                self._authenticated = True
                return True
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"Login failed ({e.code}): {error_body}")
        except Exception as e:
            raise Exception(f"Login error: {str(e)}")
    
    def _request(
        self,
        endpoint: str,
        method: str = 'GET',
        data: Optional[Dict] = None
    ) -> Any:
        """Выполнить HTTP запрос к API"""
        if not self._authenticated:
            raise Exception("Not authenticated. Call login() first.")
        
        url = f"{self.BASE_URL}{endpoint}"
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
            "Origin": "https://ticktick.com"
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
            if e.code == 204:  # No Content - success
                return None
            error_body = e.read().decode('utf-8')
            raise Exception(f"API error ({e.code}): {error_body}")
    
    def sync(self) -> Dict:
        """Синхронизация - получить все данные аккаунта"""
        return self._request("/api/v2/batch/check/0")
    
    def get_tasks(self) -> List[Dict]:
        """Получить все задачи"""
        data = self.sync()
        return data.get('syncTaskBean', {}).get('update', [])
    
    def get_projects(self) -> List[Dict]:
        """Получить все проекты"""
        data = self.sync()
        return data.get('projectProfiles', [])
    
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
        task_data = {
            "title": title,
            "projectId": project_id or self.inbox_id,
            "priority": priority,
            "timeZone": "Europe/Moscow"
        }
        
        if content:
            task_data["content"] = content
        
        if due_date:
            # TickTick expects ISO format with timezone
            task_data["dueDate"] = due_date.isoformat()
        
        if tags:
            task_data["tags"] = tags
        
        return self._request("/api/v2/task", method='POST', data=task_data)
    
    def complete_task(self, task_id: str, project_id: str) -> None:
        """Отметить задачу выполненной"""
        self._request(
            f"/api/v2/project/{project_id}/task/{task_id}/complete",
            method='POST'
        )
    
    def delete_task(self, task_id: str, project_id: str) -> None:
        """Удалить задачу"""
        self._request(
            f"/api/v2/project/{project_id}/task/{task_id}",
            method='DELETE'
        )
    
    def update_task(self, task_id: str, **kwargs) -> Dict:
        """Обновить задачу"""
        return self._request(
            f"/api/v2/task/{task_id}",
            method='POST',
            data=kwargs
        )


class TickTickManager:
    """Высокоуровневый менеджер для работы с TickTick"""
    
    def __init__(self, username: str, password: str):
        self.client = TickTickClient(username, password)
        self.client.login()
    
    def get_all_tasks(self, completed: bool = False) -> List[Dict]:
        """Получить все задачи"""
        tasks = self.client.get_tasks()
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
    
    def format_task(self, task: Dict) -> str:
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
        
        return f"{priority_emoji} {title}{due_str}".strip()


def load_credentials():
    """Загрузить credentials из secrets.env"""
    secrets_file = os.path.expanduser('~/.openclaw/secrets.env')
    
    username = None
    password = None
    
    with open(secrets_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('TICKTICK_USERNAME='):
                username = line.split('=', 1)[1]
            elif line.startswith('TICKTICK_PASSWORD='):
                password = line.split('=', 1)[1]
    
    return username, password


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  ticktick_integration.py list")
        print("  ticktick_integration.py overdue")
        print("  ticktick_integration.py today")
        print("  ticktick_integration.py upcoming [days]")
        print("  ticktick_integration.py create <title> [description]")
        print("  ticktick_integration.py projects")
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        username, password = load_credentials()
        manager = TickTickManager(username, password)
        
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
            
            task = manager.client.create_task(title, content)
            print(f"\n✅ Создана задача: {task['title']}")
        
        elif command == 'projects':
            projects = manager.client.get_projects()
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
