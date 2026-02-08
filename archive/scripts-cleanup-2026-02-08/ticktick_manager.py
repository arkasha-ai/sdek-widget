#!/usr/bin/env python3
"""
TickTick Manager - полноценная интеграция с TickTick
Использует библиотеку ticktick-py для работы с API
"""
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from ticktick.oauth2 import OAuth2
from ticktick.api import TickTickClient


class TickTickManager:
    """Менеджер для работы с TickTick"""
    
    def __init__(self, username: str, password: str):
        """Инициализация клиента"""
        self.username = username
        self.password = password
        
        # OAuth2 setup
        self.oauth = OAuth2(
            client_id="",  # Not needed for username/password auth
            client_secret="",
            redirect_uri=""
        )
        
        # Initialize client
        self.client = TickTickClient(username, password, self.oauth)
        
    def get_all_tasks(self, completed: bool = False) -> List[Dict]:
        """Получить все задачи"""
        tasks = self.client.state.get('tasks', [])
        if completed:
            return [t for t in tasks if t.get('status') == 2]
        else:
            return [t for t in tasks if t.get('status') != 2]
    
    def get_overdue_tasks(self) -> List[Dict]:
        """Получить просроченные задачи"""
        now = datetime.now()
        overdue = []
        
        for task in self.get_all_tasks(completed=False):
            due_str = task.get('dueDate')
            if due_str:
                try:
                    # Parse ISO datetime
                    due_date = datetime.fromisoformat(due_str.replace('Z', '+00:00'))
                    if due_date.replace(tzinfo=None) < now:
                        overdue.append(task)
                except Exception as e:
                    print(f"Warning: Could not parse date for task {task.get('title')}: {e}")
        
        return overdue
    
    def get_today_tasks(self) -> List[Dict]:
        """Получить задачи на сегодня"""
        today = datetime.now().date()
        today_tasks = []
        
        for task in self.get_all_tasks(completed=False):
            due_str = task.get('dueDate')
            if due_str:
                try:
                    due_date = datetime.fromisoformat(due_str.replace('Z', '+00:00')).date()
                    if due_date == today:
                        today_tasks.append(task)
                except Exception:
                    pass
        
        return today_tasks
    
    def get_upcoming_tasks(self, days: int = 7) -> List[Dict]:
        """Получить задачи на ближайшие N дней"""
        now = datetime.now()
        future = now + timedelta(days=days)
        upcoming = []
        
        for task in self.get_all_tasks(completed=False):
            due_str = task.get('dueDate')
            if due_str:
                try:
                    due_date = datetime.fromisoformat(due_str.replace('Z', '+00:00'))
                    due_date_naive = due_date.replace(tzinfo=None)
                    if now <= due_date_naive <= future:
                        upcoming.append(task)
                except Exception:
                    pass
        
        # Сортировка по дате
        upcoming.sort(key=lambda t: t.get('dueDate', ''))
        return upcoming
    
    def create_task(
        self,
        title: str,
        content: str = "",
        project_name: Optional[str] = None,
        due_date: Optional[datetime] = None,
        priority: int = 0,
        tags: Optional[List[str]] = None
    ) -> Dict:
        """
        Создать новую задачу
        
        Args:
            title: Название задачи
            content: Описание
            project_name: Название проекта (если None - в Inbox)
            due_date: Дата выполнения
            priority: 0=none, 1=low, 3=medium, 5=high
            tags: Список тегов
        
        Returns:
            Созданная задача
        """
        # Найти проект по имени
        project_id = None
        if project_name:
            projects = self.client.state.get('projects', [])
            for project in projects:
                if project.get('name') == project_name:
                    project_id = project.get('id')
                    break
        
        # Если проект не найден, используем inbox
        if not project_id:
            project_id = self.client.inbox_id
        
        # Подготовить задачу
        task_builder = self.client.task.builder(
            title,
            projectId=project_id
        )
        
        if content:
            task_builder['content'] = content
        
        if due_date:
            # TickTick expects ISO format with timezone
            task_builder['dueDate'] = due_date.isoformat()
        
        if priority:
            task_builder['priority'] = priority
        
        if tags:
            task_builder['tags'] = tags
        
        # Создать задачу
        task = self.client.task.create(task_builder)
        return task
    
    def complete_task(self, task_id: str) -> None:
        """Отметить задачу как выполненную"""
        task = self.client.get_by_id(task_id, search='tasks')
        if task:
            self.client.task.complete(task)
    
    def delete_task(self, task_id: str) -> None:
        """Удалить задачу"""
        task = self.client.get_by_id(task_id, search='tasks')
        if task:
            self.client.task.delete(task)
    
    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        due_date: Optional[datetime] = None,
        priority: Optional[int] = None
    ) -> Dict:
        """Обновить задачу"""
        task = self.client.get_by_id(task_id, search='tasks')
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        if title:
            task['title'] = title
        if content is not None:
            task['content'] = content
        if due_date:
            task['dueDate'] = due_date.isoformat()
        if priority is not None:
            task['priority'] = priority
        
        return self.client.task.update(task)
    
    def get_projects(self) -> List[Dict]:
        """Получить все проекты"""
        return self.client.state.get('projects', [])
    
    def get_tags(self) -> List[Dict]:
        """Получить все теги"""
        return self.client.state.get('tags', [])
    
    def format_task_summary(self, task: Dict) -> str:
        """Форматировать задачу для вывода"""
        title = task.get('title', 'Untitled')
        priority = task.get('priority', 0)
        due = task.get('dueDate', '')
        tags = task.get('tags', [])
        
        # Приоритет
        priority_emoji = {
            0: '',
            1: '🔵',
            3: '🟡', 
            5: '🔴'
        }.get(priority, '')
        
        # Дата
        due_str = ''
        if due:
            try:
                due_date = datetime.fromisoformat(due.replace('Z', '+00:00'))
                due_str = f" 📅 {due_date.strftime('%Y-%m-%d %H:%M')}"
            except Exception:
                pass
        
        # Теги
        tags_str = ''
        if tags:
            tags_str = f" 🏷️ {', '.join(tags)}"
        
        return f"{priority_emoji} {title}{due_str}{tags_str}"


def load_credentials() -> tuple:
    """Загрузить credentials из secrets.env"""
    secrets_file = os.path.expanduser('~/.openclaw/secrets.env')
    
    if not os.path.exists(secrets_file):
        raise FileNotFoundError("secrets.env not found")
    
    username = None
    password = None
    
    with open(secrets_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('TICKTICK_USERNAME='):
                username = line.split('=', 1)[1].strip('"\'')
            elif line.startswith('TICKTICK_PASSWORD='):
                password = line.split('=', 1)[1].strip('"\'')
    
    if not username or not password:
        raise ValueError("TICKTICK_USERNAME and TICKTICK_PASSWORD not found in secrets.env")
    
    return username, password


def main():
    """CLI для тестирования"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  ticktick_manager.py list")
        print("  ticktick_manager.py overdue")
        print("  ticktick_manager.py today")
        print("  ticktick_manager.py upcoming [days]")
        print("  ticktick_manager.py create <title> [description]")
        print("  ticktick_manager.py projects")
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        username, password = load_credentials()
        manager = TickTickManager(username, password)
        
        if command == 'list':
            tasks = manager.get_all_tasks()
            print(f"\n📋 Все задачи ({len(tasks)}):\n")
            for task in tasks:
                print(f"  {manager.format_task_summary(task)}")
        
        elif command == 'overdue':
            tasks = manager.get_overdue_tasks()
            print(f"\n⚠️  Просроченные задачи ({len(tasks)}):\n")
            for task in tasks:
                print(f"  {manager.format_task_summary(task)}")
        
        elif command == 'today':
            tasks = manager.get_today_tasks()
            print(f"\n📅 Задачи на сегодня ({len(tasks)}):\n")
            for task in tasks:
                print(f"  {manager.format_task_summary(task)}")
        
        elif command == 'upcoming':
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            tasks = manager.get_upcoming_tasks(days=days)
            print(f"\n🗓️  Задачи на {days} дней ({len(tasks)}):\n")
            for task in tasks:
                print(f"  {manager.format_task_summary(task)}")
        
        elif command == 'create':
            if len(sys.argv) < 3:
                print("Error: title required")
                sys.exit(1)
            
            title = sys.argv[2]
            content = sys.argv[3] if len(sys.argv) > 3 else ""
            
            task = manager.create_task(title, content)
            print(f"\n✅ Создана задача: {task['title']}")
        
        elif command == 'projects':
            projects = manager.get_projects()
            print(f"\n📁 Проекты ({len(projects)}):\n")
            for project in projects:
                name = project.get('name', 'Unknown')
                task_count = len([t for t in manager.get_all_tasks() 
                                 if t.get('projectId') == project.get('id')])
                print(f"  • {name} ({task_count} задач)")
        
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
