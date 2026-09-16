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
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = int(os.getenv('PORT', '3000'))
BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
MINI_APP_URL = os.getenv('MINI_APP_URL', '').strip()
TEST_MODE = os.getenv('TEST_MODE', 'true').lower() == 'true'
DB = '/tmp/dogshappines_v8.sqlite3'
ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / 'assets'

CATALOG = [
    {'id': 1, 'name': 'Выгул собак', 'price': 700, 'desc': '30–60 минут, маршрут и фотоотчёт', 'image': 'service-walk.webp', 'group': 'pet'},
    {'id': 2, 'name': 'Передержка', 'price': 1200, 'desc': 'Домашняя передержка с заботой и связью', 'image': 'service-board.webp', 'group': 'home'},
    {'id': 3, 'name': 'Зооняня', 'price': 800, 'desc': 'Визит на дом, кормление и уход', 'image': 'service-sitter.webp', 'group': 'home'},
    {'id': 4, 'name': 'Кинолог', 'price': 1500, 'desc': 'Индивидуальное занятие и коррекция поведения', 'image': 'service-kinologist.webp', 'group': 'pet'},
    {'id': 5, 'name': 'Ветеринар онлайн', 'price': 900, 'desc': 'Консультация по питанию, здоровью и уходу', 'image': 'service-vet.webp', 'group': 'extra'},
    {'id': 6, 'name': 'Груминг', 'price': 1500, 'desc': 'Шерсть, когти и базовая гигиена', 'image': 'service-groom.webp', 'group': 'pet'},
    {'id': 7, 'name': 'Визит на дом', 'price': 800, 'desc': 'Кормление, игра и короткая прогулка', 'image': 'service-home.webp', 'group': 'home'},
    {'id': 8, 'name': 'Трансфер', 'price': 1000, 'desc': 'Поездка в клинику, салон или к родственникам', 'image': 'service-transfer.webp', 'group': 'extra'},
]

TARIFFS = [
    {'id': 'worklife', 'name': 'Ворк Лайф Пет', 'price': 4990, 'walks': 8, 'badge': '', 'desc': '8 прогулок по 60 минут'},
    {'id': 'toptail', 'name': 'Топ Хвостик', 'price': 8250, 'walks': 16, 'badge': 'Хит продаж', 'desc': '16 прогулок по 60 минут'},
]

DEMO_CLIENTS = [
    {'name': 'Анна', 'score': 24, 'rating': 5.0},
    {'name': 'Мария', 'score': 18, 'rating': 4.9},
    {'name': 'Ирина', 'score': 14, 'rating': 4.9},
]
DEMO_EXECUTORS = [
    {'name': 'Алина', 'score': 42, 'rating': 5.0},
    {'name': 'Екатерина', 'score': 35, 'rating': 4.9},
    {'name': 'Марко', 'score': 29, 'rating': 4.9},
]


def conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def ensure_column(c, table, col, definition):
    cols = {row['name'] for row in c.execute(f'PRAGMA table_info({table})').fetchall()}
    if col not in cols:
        c.execute(f'ALTER TABLE {table} ADD COLUMN {col} {definition}')


def init_db():
    c = conn()
    c.executescript('''
      CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        first_name TEXT,
        username TEXT,
        role TEXT DEFAULT '',
        rating_opt_in INTEGER DEFAULT 1
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
        scheduled_date TEXT,
        scheduled_time TEXT,
        duration_min INTEGER DEFAULT 60,
        address TEXT,
        pet_name TEXT,
        notes TEXT,
        created_at TEXT
      );
      CREATE TABLE IF NOT EXISTS pets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        breed TEXT
      );
      CREATE TABLE IF NOT EXISTS subscriptions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        plan_id TEXT,
        plan_name TEXT,
        price INTEGER,
        total_walks INTEGER,
        used_walks INTEGER DEFAULT 0,
        renew_date TEXT,
        status TEXT DEFAULT 'active'
      );
    ''')
    ensure_column(c, 'users', 'role', "TEXT DEFAULT ''")
    ensure_column(c, 'users', 'rating_opt_in', 'INTEGER DEFAULT 1')
    for col, definition in [
        ('scheduled_date', 'TEXT'), ('scheduled_time', 'TEXT'), ('duration_min', 'INTEGER DEFAULT 60'),
        ('address', 'TEXT'), ('pet_name', 'TEXT'), ('notes', 'TEXT')
    ]:
        ensure_column(c, 'orders', col, definition)
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
    print('setMyCommands', telegram('setMyCommands', {'commands': [{'command': 'start', 'description': 'Открыть приложение'}]}))
    print('setChatMenuButton', telegram('setChatMenuButton', {'menu_button': {'type': 'web_app', 'text': 'Открыть приложение', 'web_app': {'url': MINI_APP_URL}}}))
    print('setWebhook', telegram('setWebhook', {'url': MINI_APP_URL.rstrip('/') + '/telegram/webhook', 'allowed_updates': ['message']}))


def seed_demo(user):
    if not TEST_MODE:
        return
    c = conn()
    uid = user['id']
    today = datetime.now(timezone.utc).date()
    if c.execute('SELECT COUNT(*) FROM pets WHERE user_id=?', (uid,)).fetchone()[0] == 0:
        c.executemany('INSERT INTO pets(user_id,name,breed) VALUES(?,?,?)', [
            (uid, 'Бублик', 'Собака · Корги'),
            (uid, 'Мурка', 'Кошка · Британская'),
            (uid, 'Чарли', 'Собака · Лабрадор'),
        ])
    if c.execute('SELECT COUNT(*) FROM subscriptions WHERE user_id=?', (uid,)).fetchone()[0] == 0:
        c.execute('INSERT INTO subscriptions(user_id,plan_id,plan_name,price,total_walks,used_walks,renew_date,status) VALUES(?,?,?,?,?,?,?,?)',
                  (uid, 'worklife', 'Ворк Лайф Пет', 4990, 8, 3, str(today + timedelta(days=22)), 'active'))
    if c.execute('SELECT COUNT(*) FROM orders WHERE user_id=?', (uid,)).fetchone()[0] == 0:
        demo = [
            (uid, 1, 'Выгул с Алиной', 700, 'accepted', 990101, user.get('first_name', 'Клиент'), user.get('username', ''), str(today), '17:00', 60, 'Ул. Корзо, 12', 'Бублик', '', datetime.now(timezone.utc).isoformat()),
            (uid, 1, 'Выгул с Марко', 700, 'done', 990102, user.get('first_name', 'Клиент'), user.get('username', ''), str(today - timedelta(days=2)), '18:00', 60, 'Ул. Корзо, 12', 'Бублик', '', datetime.now(timezone.utc).isoformat()),
            (uid, 2, 'Передержка с Еленой', 1200, 'done', 990103, user.get('first_name', 'Клиент'), user.get('username', ''), str(today - timedelta(days=7)), '11:00', 180, 'Ул. Корзо, 12', 'Мурка', '', datetime.now(timezone.utc).isoformat()),
        ]
        c.executemany('''INSERT INTO orders(user_id,item_id,item_name,price,status,executor_id,customer_name,customer_contact,scheduled_date,scheduled_time,duration_min,address,pet_name,notes,created_at)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', demo)
    if c.execute("SELECT COUNT(*) FROM orders WHERE user_id>=880000 AND status='open'").fetchone()[0] == 0:
        demo_open = [
            (880001, 1, 'Выгул собак', 700, 'open', None, 'Анна', '@anna_demo', str(today), '19:00', 60, 'Центр, Суботица', 'Ричи', 'Боится велосипедов', datetime.now(timezone.utc).isoformat()),
            (880002, 3, 'Зооняня', 800, 'open', None, 'Мария', '@maria_demo', str(today + timedelta(days=1)), '12:00', 90, 'Прозивка, Суботица', 'Луна', 'Корм в шкафу на кухне', datetime.now(timezone.utc).isoformat()),
            (880003, 1, 'Выгул собак', 700, 'open', None, 'Ирина', '@irina_demo', str(today + timedelta(days=1)), '18:00', 60, 'Mali Bajmok', 'Тоби', '', datetime.now(timezone.utc).isoformat()),
        ]
        c.executemany('''INSERT INTO orders(user_id,item_id,item_name,price,status,executor_id,customer_name,customer_contact,scheduled_date,scheduled_time,duration_min,address,pet_name,notes,created_at)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', demo_open)
    c.commit()
    c.close()


def minutes(time_str):
    try:
        hh, mm = map(int, time_str.split(':'))
        return hh * 60 + mm
    except Exception:
        return 0


def has_conflict(c, executor_id, date_str, time_str, duration, exclude_id=None):
    rows = c.execute("SELECT id,scheduled_time,duration_min FROM orders WHERE executor_id=? AND scheduled_date=? AND status IN ('accepted','in_progress')", (executor_id, date_str)).fetchall()
    start = minutes(time_str)
    end = start + int(duration or 60)
    for row in rows:
        if exclude_id and row['id'] == exclude_id:
            continue
        other_start = minutes(row['scheduled_time'] or '00:00')
        other_end = other_start + int(row['duration_min'] or 60)
        if start < other_end and other_start < end:
            return True
    return False


def get_user_row(user_id):
    c = conn()
    row = c.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    c.close()
    return dict(row) if row else None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(fmt % args)

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
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
            c.execute('INSERT OR IGNORE INTO users(id,first_name,username) VALUES(?,?,?)', (user['id'], user.get('first_name', ''), user.get('username', '')))
            c.execute('UPDATE users SET first_name=?, username=? WHERE id=?', (user.get('first_name', ''), user.get('username', ''), user['id']))
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
        self.send_header('Cache-Control', 'public,max-age=31536000,immutable' if cache else 'no-cache, no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        if path == '/health':
            return self.send_json({'status': 'ok', 'test_mode': TEST_MODE, 'ui': 'premium-v8'})
        if path.startswith('/assets/'):
            return self.serve_file(ASSET_DIR / path.split('/assets/', 1)[1], cache=True)
        if path == '/api/catalog':
            return self.send_json(CATALOG)
        if path == '/api/tariffs':
            return self.send_json(TARIFFS)

        user = self.require_user() if path.startswith('/api/') else None
        if path == '/api/me' and user:
            row = get_user_row(user['id']) or {}
            return self.send_json({**user, 'role': row.get('role') or '', 'rating_opt_in': bool(row.get('rating_opt_in', 1))})
        if path == '/api/orders' and user:
            c = conn(); rows = c.execute('SELECT * FROM orders WHERE user_id=? ORDER BY scheduled_date DESC, scheduled_time DESC, id DESC', (user['id'],)).fetchall(); c.close()
            return self.send_json([dict(r) for r in rows])
        if path == '/api/executor/orders' and user:
            c = conn(); rows = c.execute("SELECT * FROM orders WHERE status='open' OR executor_id=? ORDER BY scheduled_date,scheduled_time,id DESC", (user['id'],)).fetchall(); c.close()
            return self.send_json([dict(r) for r in rows])
        if path == '/api/pets' and user:
            c = conn(); rows = c.execute('SELECT * FROM pets WHERE user_id=? ORDER BY id DESC', (user['id'],)).fetchall(); c.close()
            return self.send_json([dict(r) for r in rows])
        if path == '/api/subscription' and user:
            c = conn(); row = c.execute("SELECT * FROM subscriptions WHERE user_id=? AND status='active' ORDER BY id DESC LIMIT 1", (user['id'],)).fetchone(); c.close()
            if not row:
                return self.send_json(None)
            result = dict(row); result['remaining_walks'] = max(0, int(result['total_walks']) - int(result['used_walks']))
            return self.send_json(result)
        if path == '/api/calendar' and user:
            role = (query.get('role') or ['client'])[0]
            c = conn()
            if role == 'executor':
                rows = c.execute("SELECT * FROM orders WHERE executor_id=? AND status IN ('accepted','in_progress','done') ORDER BY scheduled_date,scheduled_time", (user['id'],)).fetchall()
            else:
                rows = c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY scheduled_date,scheduled_time", (user['id'],)).fetchall()
            c.close(); return self.send_json([dict(r) for r in rows])
        if path == '/api/client/stats' and user:
            c = conn(); total = c.execute('SELECT COUNT(*) FROM orders WHERE user_id=?', (user['id'],)).fetchone()[0]; done = c.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND status='done'", (user['id'],)).fetchone()[0]; walks = c.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND item_id=1 AND status='done'", (user['id'],)).fetchone()[0]; pets = c.execute('SELECT COUNT(*) FROM pets WHERE user_id=?', (user['id'],)).fetchone()[0]; c.close()
            return self.send_json({'orders': total, 'done': done, 'walks': walks, 'pets': pets, 'rating': 5.0})
        if path == '/api/executor/stats' and user:
            c = conn(); completed = c.execute("SELECT COUNT(*) FROM orders WHERE executor_id=? AND status='done'", (user['id'],)).fetchone()[0]; active = c.execute("SELECT COUNT(*) FROM orders WHERE executor_id=? AND status IN ('accepted','in_progress')", (user['id'],)).fetchone()[0]; income = c.execute("SELECT COALESCE(SUM(price),0) FROM orders WHERE executor_id=? AND status='done'", (user['id'],)).fetchone()[0]; c.close()
            return self.send_json({'completed': completed, 'active': active, 'income': income, 'rating': 4.9, 'rank': 4})
        if path == '/api/leaderboard' and user:
            row = get_user_row(user['id']) or {}; c = conn(); client_score = c.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND status='done'", (user['id'],)).fetchone()[0]; exec_score = c.execute("SELECT COUNT(*) FROM orders WHERE executor_id=? AND status='done'", (user['id'],)).fetchone()[0]; c.close()
            clients = list(DEMO_CLIENTS)
            if row.get('rating_opt_in', 1): clients.append({'name': user.get('first_name') or 'Вы', 'score': client_score, 'rating': 5.0, 'me': True})
            executors = list(DEMO_EXECUTORS) + [{'name': user.get('first_name') or 'Вы', 'score': exec_score, 'rating': 4.9, 'me': True}]
            clients.sort(key=lambda x: x['score'], reverse=True); executors.sort(key=lambda x: x['score'], reverse=True)
            return self.send_json({'clients': clients, 'executors': executors, 'rating_opt_in': bool(row.get('rating_opt_in', 1))})
        if path.startswith('/api/'):
            return self.send_json({'error': 'not found'}, 404)
        return self.serve_file(ASSET_DIR / 'index.html')

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path == '/telegram/webhook':
            data = self.read_json(); message = data.get('message') or {}; chat_id = (message.get('chat') or {}).get('id')
            if chat_id and str(message.get('text', '')).startswith('/start') and MINI_APP_URL:
                telegram('sendMessage', {'chat_id': chat_id, 'text': "Dog's Happiness\nОткройте приложение", 'reply_markup': {'inline_keyboard': [[{'text': 'Открыть приложение', 'web_app': {'url': MINI_APP_URL}}]]}})
            return self.send_json({'ok': True})
        user = self.require_user()
        if not user: return
        data = self.read_json()
        if path == '/api/me/role':
            role = data.get('role')
            if role not in ('client', 'executor'): return self.send_json({'error': 'Некорректная роль'}, 400)
            c = conn(); c.execute('UPDATE users SET role=? WHERE id=?', (role, user['id'])); c.commit(); c.close(); return self.send_json({'ok': True, 'role': role})
        if path == '/api/me/rating-opt':
            enabled = 1 if bool(data.get('enabled')) else 0; c = conn(); c.execute('UPDATE users SET rating_opt_in=? WHERE id=?', (enabled, user['id'])); c.commit(); c.close(); return self.send_json({'ok': True, 'enabled': bool(enabled)})
        if path == '/api/subscription/buy':
            plan = next((p for p in TARIFFS if p['id'] == data.get('plan_id')), None)
            if not plan: return self.send_json({'error': 'Тариф не найден'}, 404)
            c = conn(); c.execute("UPDATE subscriptions SET status='inactive' WHERE user_id=? AND status='active'", (user['id'],)); renew = datetime.now(timezone.utc).date() + timedelta(days=30); c.execute('INSERT INTO subscriptions(user_id,plan_id,plan_name,price,total_walks,used_walks,renew_date,status) VALUES(?,?,?,?,?,?,?,?)', (user['id'], plan['id'], plan['name'], plan['price'], plan['walks'], 0, str(renew), 'active')); c.commit(); c.close(); return self.send_json({'ok': True})
        if path == '/api/orders':
            item = next((x for x in CATALOG if x['id'] == int(data.get('item_id', 0))), None)
            if not item: return self.send_json({'error': 'Услуга не найдена'}, 404)
            date = data.get('scheduled_date') or str(datetime.now(timezone.utc).date()); time_str = data.get('scheduled_time') or '17:00'; duration = int(data.get('duration_min') or 60)
            c = conn(); cur = c.execute('''INSERT INTO orders(user_id,item_id,item_name,price,status,customer_name,customer_contact,scheduled_date,scheduled_time,duration_min,address,pet_name,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (user['id'], item['id'], item['name'], item['price'], 'open', user.get('first_name','Клиент'), user.get('username',''), date, time_str, duration, data.get('address','Ул. Корзо, 12'), data.get('pet_name','Бублик'), data.get('notes',''), datetime.now(timezone.utc).isoformat())); c.commit(); oid = cur.lastrowid; c.close(); return self.send_json({'ok': True, 'id': oid}, 201)
        if path.startswith('/api/orders/') and path.endswith('/cancel'):
            oid = int(path.strip('/').split('/')[2]); c = conn(); cur = c.execute("UPDATE orders SET status='cancelled' WHERE id=? AND user_id=? AND status IN ('open','accepted')", (oid, user['id'])); c.commit(); c.close(); return self.send_json({'ok': cur.rowcount == 1})
        if path == '/api/pets':
            name = (data.get('name') or '').strip(); breed = (data.get('breed') or '').strip()
            if not name: return self.send_json({'error': 'Введите имя'}, 400)
            c = conn(); cur = c.execute('INSERT INTO pets(user_id,name,breed) VALUES(?,?,?)', (user['id'], name, breed)); c.commit(); pid = cur.lastrowid; c.close(); return self.send_json({'ok': True, 'id': pid}, 201)
        if path.startswith('/api/executor/orders/'):
            parts = path.strip('/').split('/'); oid = int(parts[3]); action = parts[4] if len(parts) > 4 else ''; c = conn(); order = c.execute('SELECT * FROM orders WHERE id=?', (oid,)).fetchone()
            if not order: c.close(); return self.send_json({'error': 'Заказ не найден'}, 404)
            if action == 'accept':
                if has_conflict(c, user['id'], order['scheduled_date'], order['scheduled_time'], order['duration_min']): c.close(); return self.send_json({'error': 'На это время у вас уже есть заказ'}, 409)
                cur = c.execute("UPDATE orders SET executor_id=?,status='accepted' WHERE id=? AND status='open'", (user['id'], oid)); c.commit(); c.close(); return self.send_json({'ok': cur.rowcount == 1})
            if action == 'status':
                status = data.get('status')
                if status not in ('in_progress', 'done'): c.close(); return self.send_json({'error': 'Некорректный статус'}, 400)
                cur = c.execute('UPDATE orders SET status=? WHERE id=? AND executor_id=?', (status, oid, user['id']))
                if status == 'done' and order['item_id'] == 1:
                    sub = c.execute("SELECT * FROM subscriptions WHERE user_id=? AND status='active' ORDER BY id DESC LIMIT 1", (order['user_id'],)).fetchone()
                    if sub and int(sub['used_walks']) < int(sub['total_walks']): c.execute('UPDATE subscriptions SET used_walks=used_walks+1 WHERE id=?', (sub['id'],))
                c.commit(); c.close(); return self.send_json({'ok': cur.rowcount == 1})
            c.close()
        return self.send_json({'error': 'not found'}, 404)


if __name__ == '__main__':
    init_db()
    threading.Thread(target=lambda: (time.sleep(1.2), configure_bot()), daemon=True).start()
    print('listening', PORT)
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
