#!/usr/bin/env python3
"""
TickTick OAuth2 Setup
Выполняет начальную авторизацию и сохраняет токены
"""
import json
import os
import urllib.request
import urllib.parse
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser
from threading import Thread
import time


# OAuth endpoints
AUTH_URL = "https://ticktick.com/oauth/authorize"
TOKEN_URL = "https://ticktick.com/oauth/token"
REDIRECT_URI = "http://localhost:8080/callback"

# Token storage
TOKEN_FILE = os.path.expanduser("~/.openclaw/workspace/.ticktick_token.json")


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler для получения OAuth callback"""
    
    auth_code = None
    
    def do_GET(self):
        """Обработать GET запрос с authorization code"""
        if self.path.startswith('/callback'):
            # Извлечь code из query параметров
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            
            if 'code' in params:
                OAuthCallbackHandler.auth_code = params['code'][0]
                
                # Отправить успешный ответ
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"""
                    <html>
                    <body>
                    <h1>Authorization successful!</h1>
                    <p>You can close this window and return to the terminal.</p>
                    </body>
                    </html>
                """)
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"<h1>Error: No authorization code received</h1>")
    
    def log_message(self, format, *args):
        """Подавить логирование HTTP запросов"""
        pass


def load_credentials():
    """Загрузить credentials из secrets.env"""
    secrets_file = os.path.expanduser('~/.openclaw/secrets.env')
    
    client_id = None
    client_secret = None
    
    with open(secrets_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('TICKTICK_CLIENT_ID='):
                client_id = line.split('=', 1)[1]
            elif line.startswith('TICKTICK_CLIENT_SECRET='):
                client_secret = line.split('=', 1)[1]
    
    if not client_id or not client_secret:
        raise ValueError("TICKTICK_CLIENT_ID and TICKTICK_CLIENT_SECRET not found")
    
    return client_id, client_secret


def start_oauth_flow(client_id: str, client_secret: str):
    """Выполнить OAuth авторизацию"""
    
    # 1. Построить authorization URL
    params = {
        'client_id': client_id,
        'redirect_uri': REDIRECT_URI,
        'scope': 'tasks:read tasks:write',
        'response_type': 'code',
        'state': 'random_state_string'
    }
    
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    
    print("\n🔐 Starting OAuth authorization flow...")
    print(f"\nOpening browser for authorization: {auth_url}\n")
    
    # 2. Запустить локальный HTTP сервер для получения callback
    server = HTTPServer(('localhost', 8080), OAuthCallbackHandler)
    server_thread = Thread(target=server.handle_request)
    server_thread.daemon = True
    server_thread.start()
    
    # 3. Открыть браузер
    webbrowser.open(auth_url)
    
    # 4. Ждать authorization code
    print("Waiting for authorization callback...")
    timeout = 120  # 2 минуты
    start_time = time.time()
    
    while OAuthCallbackHandler.auth_code is None:
        if time.time() - start_time > timeout:
            raise TimeoutError("Authorization timeout")
        time.sleep(0.5)
    
    auth_code = OAuthCallbackHandler.auth_code
    print(f"✅ Received authorization code: {auth_code[:20]}...")
    
    # 5. Обменять code на access token
    print("\n🔄 Exchanging code for access token...")
    
    token_data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': auth_code,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code'
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    request = urllib.request.Request(
        TOKEN_URL,
        data=urllib.parse.urlencode(token_data).encode('utf-8'),
        headers=headers
    )
    
    try:
        with urllib.request.urlopen(request) as response:
            token_response = json.loads(response.read().decode('utf-8'))
            
            # 6. Сохранить токены
            with open(TOKEN_FILE, 'w') as f:
                json.dump(token_response, f, indent=2)
            
            print(f"✅ Access token saved to {TOKEN_FILE}")
            print(f"\nToken expires in: {token_response.get('expires_in', 'unknown')} seconds")
            
            return token_response
    
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise Exception(f"Token exchange failed: {e.code} - {error_body}")


def main():
    try:
        client_id, client_secret = load_credentials()
        token_response = start_oauth_flow(client_id, client_secret)
        
        print("\n" + "="*50)
        print("✅ OAuth authorization complete!")
        print("="*50)
        print("\nYou can now use the TickTick integration.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
