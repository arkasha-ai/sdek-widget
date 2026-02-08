#!/usr/bin/env python3
"""
TickTick API Client
Pure stdlib implementation (no external dependencies)
Supports OAuth2 authentication and all major task operations
"""
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


class TickTickClient:
    """Client for TickTick API using OAuth2 authentication"""
    
    BASE_URL = "https://api.ticktick.com"
    AUTH_URL = "https://ticktick.com/oauth"
    
    def __init__(self, username: str, password: str):
        """Initialize client with username and password"""
        self.username = username
        self.password = password
        self.access_token = None
        self.cookies = {}
        self.inbox_id = None
        self.user_id = None
        
    def login(self) -> bool:
        """Authenticate with TickTick using username/password"""
        url = f"{self.BASE_URL}/api/v2/user/signon?wc=true&remember=true"
        
        data = {
            "username": self.username,
            "password": self.password
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        
        try:
            request = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            with urllib.request.urlopen(request) as response:
                result = json.loads(response.read().decode('utf-8'))
                self.access_token = result.get('token')
                self.user_id = result.get('userId')
                self.inbox_id = result.get('inboxId')
                
                # Store cookies from response
                cookie_header = response.getheader('Set-Cookie')
                if cookie_header:
                    self.cookies = self._parse_cookies(cookie_header)
                
                return True
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"Login failed: {e.code} - {error_body}")
        except Exception as e:
            raise Exception(f"Login error: {str(e)}")
    
    def _parse_cookies(self, cookie_header: str) -> Dict[str, str]:
        """Parse Set-Cookie header into dict"""
        cookies = {}
        for cookie in cookie_header.split(','):
            parts = cookie.strip().split(';')[0].split('=', 1)
            if len(parts) == 2:
                cookies[parts[0]] = parts[1]
        return cookies
    
    def _make_request(
        self,
        endpoint: str,
        method: str = 'GET',
        data: Optional[Dict] = None
    ) -> Any:
        """Make authenticated request to TickTick API"""
        if not self.access_token:
            raise Exception("Not authenticated. Call login() first.")
        
        url = f"{self.BASE_URL}{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        
        # Add cookies if available
        if self.cookies:
            cookie_str = '; '.join([f"{k}={v}" for k, v in self.cookies.items()])
            headers['Cookie'] = cookie_str
        
        request_kwargs = {
            'headers': headers,
            'method': method
        }
        
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
            error_body = e.read().decode('utf-8') if e.code != 204 else ""
            if e.code == 204:  # No Content - success
                return None
            raise Exception(f"API request failed: {e.code} - {error_body}")
    
    def get_tasks(
        self,
        project_id: Optional[str] = None,
        completed: bool = False
    ) -> List[Dict]:
        """Get tasks, optionally filtered by project"""
        endpoint = "/api/v2/batch/check/0"
        result = self._make_request(endpoint)
        
        tasks = result.get('syncTaskBean', {}).get('update', [])
        
        # Filter by project if specified
        if project_id:
            tasks = [t for t in tasks if t.get('projectId') == project_id]
        
        # Filter by completion status
        tasks = [t for t in tasks if (t.get('status') == 2) == completed]
        
        return tasks
    
    def get_projects(self) -> List[Dict]:
        """Get all projects (lists)"""
        endpoint = "/api/v2/batch/check/0"
        result = self._make_request(endpoint)
        return result.get('projectProfiles', [])
    
    def get_tags(self) -> List[Dict]:
        """Get all tags"""
        endpoint = "/api/v2/batch/check/0"
        result = self._make_request(endpoint)
        return result.get('tags', [])
    
    def create_task(
        self,
        title: str,
        content: str = "",
        project_id: Optional[str] = None,
        due_date: Optional[str] = None,
        priority: int = 0,
        tags: Optional[List[str]] = None
    ) -> Dict:
        """
        Create a new task
        
        Args:
            title: Task title
            content: Task description
            project_id: Project ID (use inbox_id if None)
            due_date: ISO format date string
            priority: 0=none, 1=low, 3=medium, 5=high
            tags: List of tag names
        """
        task_data = {
            "title": title,
            "content": content,
            "projectId": project_id or self.inbox_id,
            "priority": priority,
            "timeZone": "Europe/Moscow"
        }
        
        if due_date:
            task_data["dueDate"] = due_date
        
        if tags:
            task_data["tags"] = tags
        
        endpoint = "/api/v2/task"
        return self._make_request(endpoint, method='POST', data=task_data)
    
    def update_task(self, task_id: str, **kwargs) -> Dict:
        """Update an existing task"""
        endpoint = f"/api/v2/task/{task_id}"
        return self._make_request(endpoint, method='POST', data=kwargs)
    
    def complete_task(self, task_id: str, project_id: str) -> None:
        """Mark task as completed"""
        endpoint = f"/api/v2/project/{project_id}/task/{task_id}/complete"
        self._make_request(endpoint, method='POST')
    
    def delete_task(self, task_id: str, project_id: str) -> None:
        """Delete a task"""
        endpoint = f"/api/v2/project/{project_id}/task/{task_id}"
        self._make_request(endpoint, method='DELETE')
    
    def get_overdue_tasks(self) -> List[Dict]:
        """Get all overdue tasks"""
        tasks = self.get_tasks(completed=False)
        now = datetime.now(timezone.utc)
        
        overdue = []
        for task in tasks:
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
        """Get tasks due today"""
        tasks = self.get_tasks(completed=False)
        today = datetime.now(timezone.utc).date()
        
        today_tasks = []
        for task in tasks:
            due_str = task.get('dueDate')
            if due_str:
                try:
                    due_date = datetime.fromisoformat(due_str.replace('Z', '+00:00')).date()
                    if due_date == today:
                        today_tasks.append(task)
                except Exception:
                    pass
        
        return today_tasks


def main():
    """CLI interface for testing"""
    import sys
    import os
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  ticktick_client.py login <username> <password>")
        print("  ticktick_client.py list [project_id]")
        print("  ticktick_client.py create <title> [description]")
        print("  ticktick_client.py overdue")
        print("  ticktick_client.py today")
        sys.exit(1)
    
    command = sys.argv[1]
    
    # Load credentials from env
    username = os.getenv('TICKTICK_USERNAME')
    password = os.getenv('TICKTICK_PASSWORD')
    
    if not username or not password:
        print("Error: TICKTICK_USERNAME and TICKTICK_PASSWORD must be set")
        sys.exit(1)
    
    client = TickTickClient(username, password)
    
    try:
        if command == 'login':
            client.login()
            print(f"✅ Logged in as {username}")
            print(f"User ID: {client.user_id}")
            print(f"Inbox ID: {client.inbox_id}")
        
        elif command == 'list':
            client.login()
            project_id = sys.argv[2] if len(sys.argv) > 2 else None
            tasks = client.get_tasks(project_id=project_id)
            print(f"Found {len(tasks)} tasks:")
            for task in tasks:
                status = "✅" if task.get('status') == 2 else "⬜"
                print(f"{status} {task['title']}")
                if task.get('dueDate'):
                    print(f"   Due: {task['dueDate']}")
        
        elif command == 'create':
            if len(sys.argv) < 3:
                print("Error: title required")
                sys.exit(1)
            
            client.login()
            title = sys.argv[2]
            content = sys.argv[3] if len(sys.argv) > 3 else ""
            
            task = client.create_task(title, content)
            print(f"✅ Created task: {task['title']}")
        
        elif command == 'overdue':
            client.login()
            tasks = client.get_overdue_tasks()
            print(f"Found {len(tasks)} overdue tasks:")
            for task in tasks:
                print(f"⚠️  {task['title']}")
                print(f"   Due: {task['dueDate']}")
        
        elif command == 'today':
            client.login()
            tasks = client.get_today_tasks()
            print(f"Found {len(tasks)} tasks due today:")
            for task in tasks:
                print(f"📅 {task['title']}")
        
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
