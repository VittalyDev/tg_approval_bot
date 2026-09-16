import json
import hmac
import hashlib
import mimetypes
import os
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = int(os.getenv('PORT', '3000'))
BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
MINI_APP_URL = os.getenv('MINI_APP_URL', '').strip()
TEST_MODE = os.getenv('TEST_MODE', 'true').lower() == 'true'
DB = '/tmp/dogshappines_premium_v4.sqlite3'
ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / 'assets'

CATALOG = [
    {'id': 1, 'name': 'Выгул собак', 'price': 700, 'desc': '30–60 минут, прогулка и фотоотчёт', 'image': 'icon-walk.webp'},
    {'id': 2, 'name': 'Передержка', 'price': 1200, 'desc': 'Домашняя передержка с заботой и связью', 'image': 'asset-5.webp'},
    {'id': 3, 'name': 'Зооняня', 'price': 800, 'desc': 'Визит на дом, кормление и уход', 'image': 'asset-6.webp'},
    {'id': 4, 'name': 'Груминг', 'price': 1500, 'desc': 'Уход за шерстью и базовая гигиена', 'image': 'asset-4.webp'},
    {'id': 5, 'name': 'Визит на дом', 'price': 800, 'desc': 'Кормление, игра и короткая прогулка', 'image': 'pet-premium.webp'},
    {'id': 6, 'name': 'Трансфер', 'price': 1000, 'desc': 'Поездка в клинику, салон или к родственникам', 'image': 'asset-5.webp'},
]


def conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    c = conn()
    c.executescript('''
      CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        first_name TEXT,
        username TEXT
      );
      CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        item_id INTEGER,
        item_name TEXT,
        price INTEGER,
        status TEXT DEFAULT 'open',
        executor_id INTEGER,
        customer_name TEXT,
        customer_contact TEXT,
        created_at TEXT
      );
      CREATE TABLE IF NOT EXISTS pets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        breed TEXT
      );
    ''')
    c.commit()
    c.close()


def validate_init_data(raw):
    if TEST_MODE and not raw:
        return {'id': 777000, 'first_name': 'Виталий', 'username': 'tester'}
    try:
        values = dict(urllib.parse.parse_qsl(raw, keep_blank_values=True))
        received_hash = values.pop('hash')
        data_check = '\n'.join(f'{key}={values[key]}' for key in sorted(values))
        secret = hmac.new(b'WebAppData', BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calculated, received_hash):
            return None
        return json.loads(values.get('user', '{}'))
    except Exception:
        return None


def telegram(method, payload):
    if not BOT_TOKEN:
        return False
    try:
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{BOT_TOKEN}/{method}',
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'},
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            return bool(json.load(response).get('ok'))
    except Exception as exc:
        print(method, 'FAIL', exc)
        return False


def configure_bot():
    if not BOT_TOKEN or not MINI_APP_URL:
        return
    print('setMyCommands', telegram('setMyCommands', {
        'commands': [{'command': 'start', 'description': 'Открыть приложение'}]
    }))
    print('setChatMenuButton', telegram('setChatMenuButton', {
        'menu_button': {
            'type': 'web_app',
            'text': 'Открыть приложение',
            'web_app': {'url': MINI_APP_URL},
        }
    }))
    print('setWebhook', telegram('setWebhook', {
        'url': MINI_APP_URL.rstrip('/') + '/telegram/webhook',
        'allowed_updates': ['message'],
    }))


def seed_demo(user):
    if not TEST_MODE:
        return
    c = conn()
    uid = user['id']
    if c.execute('SELECT COUNT(*) FROM pets WHERE user_id=?', (uid,)).fetchone()[0] == 0:
        c.executemany(
            'INSERT INTO pets(user_id,name,breed) VALUES(?,?,?)',
            [
                (uid, 'Бублик', 'Собака · Корги'),
                (uid, 'Мурка', 'Кошка · Британская'),
                (uid, 'Чарли', 'Собака · Лабрадор'),
            ],
        )
    if c.execute('SELECT COUNT(*) FROM orders WHERE user_id=?', (uid,)).fetchone()[0] == 0:
        now = datetime.now(timezone.utc).isoformat()
        c.execute(
            'INSERT INTO orders(user_id,item_id,item_name,price,status,executor_id,customer_name,customer_contact,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
            (uid, 1, 'Выгул с Алиной', 700, 'accepted', uid, user.get('first_name', 'Клиент'), user.get('username', ''), now),
        )
        c.execute(
            'INSERT INTO orders(user_id,item_id,item_name,price,status,executor_id,customer_name,customer_contact,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
            (uid, 2, 'Передержка с Марией', 1200, 'done', uid, user.get('first_name', 'Клиент'), user.get('username', ''), now),
        )
    c.commit()
    c.close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(fmt % args)

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        try:
            length = int(self.headers.get('Content-Length', '0') or 0)
            return json.loads(self.rfile.read(length) or b'{}')
        except Exception:
            return {}

    def current_user(self):
        user = validate_init_data(self.headers.get('X-Telegram-Init-Data', ''))
        if user:
            c = conn()
            c.execute(
                'INSERT OR IGNORE INTO users(id,first_name,username) VALUES(?,?,?)',
                (user['id'], user.get('first_name', ''), user.get('username', '')),
            )
            c.commit()
            c.close()
            seed_demo(user)
        return user

    def require_user(self):
        user = self.current_user()
        if not user:
            self.send_json({'error': 'Откройте приложение из Telegram'}, 401)
        return user

    def serve_file(self, path, cache=False):
        if not path.exists() or not path.is_file():
            return self.send_json({'error': 'not found'}, 404)
        body = path.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', mimetypes.guess_type(str(path))[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'public,max-age=86400' if cache else 'no-cache')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == '/health':
            return self.send_json({'status': 'ok', 'test_mode': TEST_MODE, 'ui': 'premium-v4'})
        if path.startswith('/assets/'):
            return self.serve_file(ASSET_DIR / path.split('/assets/', 1)[1], cache=True)
        if path == '/api/catalog':
            return self.send_json(CATALOG)

        user = self.require_user() if path.startswith('/api/') else None
        if path == '/api/me' and user:
            return self.send_json(user)
        if path == '/api/orders' and user:
            c = conn()
            rows = c.execute('SELECT * FROM orders WHERE user_id=? ORDER BY id DESC', (user['id'],)).fetchall()
            c.close()
            return self.send_json([dict(r) for r in rows])
        if path == '/api/executor/orders' and user:
            c = conn()
            rows = c.execute("SELECT * FROM orders WHERE status='open' OR executor_id=? ORDER BY id DESC", (user['id'],)).fetchall()
            c.close()
            return self.send_json([dict(r) for r in rows])
        if path == '/api/pets' and user:
            c = conn()
            rows = c.execute('SELECT * FROM pets WHERE user_id=? ORDER BY id DESC', (user['id'],)).fetchall()
            c.close()
            return self.send_json([dict(r) for r in rows])
        if path.startswith('/api/'):
            return
        return self.serve_file(ASSET_DIR / 'index.html')

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path == '/telegram/webhook':
            data = self.read_json()
            message = data.get('message') or {}
            chat_id = (message.get('chat') or {}).get('id')
            if chat_id and str(message.get('text', '')).startswith('/start') and MINI_APP_URL:
                telegram('sendMessage', {
                    'chat_id': chat_id,
                    'text': "Dog's Happiness\nОткройте приложение",
                    'reply_markup': {
                        'inline_keyboard': [[{
                            'text': 'Открыть приложение',
                            'web_app': {'url': MINI_APP_URL},
                        }]],
                    },
                })
            return self.send_json({'ok': True})

        user = self.require_user()
        if not user:
            return
        data = self.read_json()

        if path == '/api/orders':
            item = next((x for x in CATALOG if x['id'] == int(data.get('item_id', 0))), None)
            if not item:
                return self.send_json({'error': 'Услуга не найдена'}, 404)
            c = conn()
            cur = c.execute(
                'INSERT INTO orders(user_id,item_id,item_name,price,status,customer_name,customer_contact,created_at) VALUES(?,?,?,?,?,?,?,?)',
                (
                    user['id'], item['id'], item['name'], item['price'], 'open',
                    user.get('first_name', 'Клиент'), user.get('username', ''),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            c.commit()
            order_id = cur.lastrowid
            c.close()
            return self.send_json({'ok': True, 'id': order_id}, 201)

        if path == '/api/pets':
            name = (data.get('name') or '').strip()
            breed = (data.get('breed') or '').strip()
            if not name:
                return self.send_json({'error': 'Введите имя'}, 400)
            c = conn()
            cur = c.execute('INSERT INTO pets(user_id,name,breed) VALUES(?,?,?)', (user['id'], name, breed))
            c.commit()
            pet_id = cur.lastrowid
            c.close()
            return self.send_json({'ok': True, 'id': pet_id}, 201)

        if path.startswith('/api/executor/orders/'):
            parts = path.strip('/').split('/')
            order_id = int(parts[3])
            action = parts[4] if len(parts) > 4 else ''
            c = conn()
            if action == 'accept':
                cur = c.execute(
                    "UPDATE orders SET executor_id=?,status='accepted' WHERE id=? AND status='open'",
                    (user['id'], order_id),
                )
                c.commit()
                c.close()
                return self.send_json({'ok': cur.rowcount == 1})
            if action == 'status':
                status = data.get('status')
                if status not in ('in_progress', 'done'):
                    c.close()
                    return self.send_json({'error': 'Некорректный статус'}, 400)
                cur = c.execute(
                    'UPDATE orders SET status=? WHERE id=? AND executor_id=?',
                    (status, order_id, user['id']),
                )
                c.commit()
                c.close()
                return self.send_json({'ok': cur.rowcount == 1})
            c.close()

        return self.send_json({'error': 'not found'}, 404)


if __name__ == '__main__':
    init_db()
    threading.Thread(target=lambda: (time.sleep(1.5), configure_bot()), daemon=True).start()
    print('listening', PORT)
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
