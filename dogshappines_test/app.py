import os, json, hmac, hashlib, sqlite3, urllib.parse, urllib.request, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone

PORT = int(os.getenv('PORT', '3000'))
BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
MINI_APP_URL = os.getenv('MINI_APP_URL', '').strip()
TEST_MODE = os.getenv('TEST_MODE', 'true').lower() == 'true'
DB = '/tmp/dogshappines.sqlite3'

CATALOG = [
    {'id': 1, 'name': 'Выгул собак', 'price': 890, 'desc': 'Прогулка, игры и фотоотчёт'},
    {'id': 2, 'name': 'Зооняня', 'price': 1200, 'desc': 'Присмотр за питомцем дома'},
    {'id': 3, 'name': 'Кинолог', 'price': 1500, 'desc': 'Индивидуальное занятие'},
    {'id': 4, 'name': 'Передержка', 'price': 1900, 'desc': 'Забота на время вашего отсутствия'},
]

def conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = conn()
    c.executescript('''
      CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, first_name TEXT, username TEXT);
      CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,item_id INTEGER,item_name TEXT,price INTEGER,status TEXT DEFAULT 'open',executor_id INTEGER,created_at TEXT);
      CREATE TABLE IF NOT EXISTS pets(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,name TEXT,breed TEXT);
    ''')
    c.commit(); c.close()

def validate_init_data(raw):
    if TEST_MODE and not raw:
        return {'id': 777000, 'first_name': 'Тест', 'username': 'tester'}
    try:
        values = dict(urllib.parse.parse_qsl(raw, keep_blank_values=True))
        received_hash = values.pop('hash')
        data_check = '\n'.join(f'{k}={values[k]}' for k in sorted(values))
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
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            return bool(json.load(response).get('ok'))
    except Exception as e:
        print(method, 'FAIL', e)
        return False

def configure_bot():
    if not BOT_TOKEN or not MINI_APP_URL:
        return
    print('setMyCommands', telegram('setMyCommands', {'commands': [{'command': 'start', 'description': 'Открыть приложение'}]}))
    print('setChatMenuButton', telegram('setChatMenuButton', {'menu_button': {'type': 'web_app', 'text': 'Открыть приложение', 'web_app': {'url': MINI_APP_URL}}}))
    print('setWebhook', telegram('setWebhook', {'url': MINI_APP_URL.rstrip('/') + '/telegram/webhook', 'allowed_updates': ['message']}))

HTML = r'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><script src="https://telegram.org/js/telegram-web-app.js"></script><title>Dog's Happiness</title><style>
*{box-sizing:border-box}:root{--bg:#070707;--surface:#12100d;--gold:#d7aa5a;--gold2:#f4d393;--text:#f7efe1;--muted:#aa987c;--line:rgba(216,171,92,.23)}body{margin:0;background:radial-gradient(circle at 80% -10%,#2b1d0d 0,transparent 38%),#070707;color:var(--text);font-family:Inter,system-ui,sans-serif;min-height:100vh}#app{max-width:520px;margin:auto;padding:12px 12px 102px}.top{display:flex;justify-content:space-between;align-items:center;padding:6px 2px 12px}.brand{display:flex;align-items:center;gap:10px}.logo{width:44px;height:44px;border:1px solid var(--line);border-radius:15px;display:grid;place-items:center;font-size:25px;background:radial-gradient(circle,#3b2a14,#0d0b08);box-shadow:0 8px 22px #0008}.muted{font-size:11px;color:var(--muted)}.test{font-size:9px;letter-spacing:.15em;color:var(--gold2);border:1px solid var(--line);border-radius:99px;padding:5px 8px}.hero{min-height:265px;position:relative;overflow:hidden;padding:21px 39% 20px 20px;border:1px solid var(--line);border-radius:30px;background:radial-gradient(circle at 82% 31%,rgba(215,170,90,.27),transparent 28%),linear-gradient(135deg,#171009,#090807);box-shadow:0 22px 45px #0009}.hero:after{content:'🐕';position:absolute;right:10px;bottom:-4px;font-size:120px;filter:grayscale(1) sepia(1) brightness(.65) drop-shadow(0 15px 20px #000);opacity:.88}.eyebrow{color:var(--gold2);font-size:10px;font-weight:800;letter-spacing:.18em;text-transform:uppercase}.hero h1{font-size:31px;line-height:1.02;margin:9px 0}.hero p{font-size:13px;line-height:1.5;color:#d3c0a4}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}button{font:inherit}.btn{border:0;border-radius:15px;padding:11px 14px;background:linear-gradient(145deg,#b47f37,#e5b96b);color:#171108;font-size:12px;font-weight:800}.btn.alt{background:#15110d;color:var(--text);border:1px solid var(--line)}.section{margin-top:15px}.section h2{font-size:17px;margin:0 0 10px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:9px}.card{padding:14px;border:1px solid var(--line);border-radius:21px;background:linear-gradient(180deg,#ffffff08,#ffffff02),var(--surface);box-shadow:0 12px 26px #0006}.card h3{font-size:14px;margin:0 0 6px}.card p{font-size:11px;line-height:1.4;color:var(--muted);margin:0 0 12px}.icon{width:43px;height:43px;border-radius:14px;display:grid;place-items:center;margin-bottom:9px;font-size:22px;background:radial-gradient(circle,#4a3519,#17110b);border:1px solid var(--line);color:var(--gold2)}.row{display:flex;align-items:center;justify-content:space-between;gap:8px}.price{font-size:15px;font-weight:800;color:var(--gold2)}.hidden{display:none!important}.tabs{position:fixed;left:50%;bottom:max(10px,env(safe-area-inset-bottom));transform:translateX(-50%);width:calc(100% - 20px);max-width:430px;display:grid;grid-template-columns:repeat(4,1fr);gap:3px;padding:5px;border:1px solid var(--line);border-radius:25px;background:#090807ee;backdrop-filter:blur(18px);box-shadow:0 18px 40px #0009}.tab{border:0;background:transparent;color:#8f7d61;padding:9px 2px;border-radius:17px;font-size:9px}.tab b{display:block;font-size:20px;line-height:1.1;margin-bottom:3px;color:#9f855c}.tab.active{background:#d7aa5a22;color:var(--gold2)}.tab.active b{color:var(--gold2)}.status{font-size:10px;padding:4px 8px;border-radius:99px;background:#d7aa5a20;color:var(--gold2)}.order{margin-bottom:9px}.notice{padding:12px;border:1px solid var(--line);border-radius:16px;background:#d7aa5a10;color:#d5c09e;font-size:12px}.field{width:100%;padding:12px;margin:5px 0;border:1px solid var(--line);border-radius:14px;background:#17130f;color:var(--text)}
</style></head><body><div id="app"><header class="top"><div class="brand"><div class="logo">🐾</div><div><b id="uname">Dog's Happiness</b><div class="muted">премиальный pet care</div></div></div><span class="test">TEST</span></header><main>
<section id="home" class="view"><div class="hero"><span class="eyebrow">premium pet care</span><h1>Забота, которой можно доверять</h1><p>Выгул, ситтеры и уход за питомцем в одном приложении.</p><div class="actions"><button class="btn" onclick="go('catalog')">Выбрать услугу</button><button class="btn alt" onclick="go('orders')">Мои заказы</button></div></div><div class="section"><h2>Почему мы</h2><div class="grid"><div class="card"><div class="icon">🐾</div><h3>Проверенные ситтеры</h3><p>Доступ к заказам после проверки.</p></div><div class="card"><div class="icon">📸</div><h3>Фотоотчёты</h3><p>Отчёт после каждой услуги.</p></div><div class="card"><div class="icon">🛡</div><h3>Безопасность</h3><p>Статусы и история заказов.</p></div><div class="card"><div class="icon">👑</div><h3>Premium</h3><p>Аккуратный и быстрый сервис.</p></div></div></div></section>
<section id="catalog" class="view hidden"><div class="section"><h2>Услуги</h2><div id="catalogGrid" class="grid"></div></div></section>
<section id="orders" class="view hidden"><div class="section"><h2>Заказы</h2><div class="actions"><button class="btn" onclick="setMode('customer')">Мои</button><button class="btn alt" onclick="setMode('executor')">Исполнитель</button></div><div id="ordersList" style="margin-top:10px"></div></div></section>
<section id="profile" class="view hidden"><div class="section"><h2>Профиль</h2><div class="card"><h3 id="profileName">Пользователь</h3><p id="profileUser"></p><div class="notice">Тестовый стенд. Боевой бот и его данные не затрагиваются.</div></div><div class="section"><h2>Питомцы</h2><div class="card"><input class="field" id="petName" placeholder="Имя питомца"><input class="field" id="petBreed" placeholder="Порода"><button class="btn" onclick="addPet()">Добавить</button><div id="pets"></div></div></div></div></section></main></div>
<nav class="tabs"><button class="tab active" onclick="go('home',this)"><b>⌂</b>Главная</button><button class="tab" onclick="go('catalog',this)"><b>🐾</b>Услуги</button><button class="tab" onclick="go('orders',this)"><b>▣</b>Заказы</button><button class="tab" onclick="go('profile',this)"><b>◉</b>Профиль</button></nav><script>
const tg=window.Telegram?.WebApp;tg?.ready();tg?.expand();const initData=tg?.initData||'';let mode='customer';async function api(p,o={}){o.headers={...(o.headers||{}),'Content-Type':'application/json','X-Telegram-Init-Data':initData};const r=await fetch(p,o),d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.error||r.status);return d}function go(id,el){document.querySelectorAll('.view').forEach(x=>x.classList.add('hidden'));document.getElementById(id).classList.remove('hidden');if(el){document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));el.classList.add('active')}if(id==='orders')loadOrders();if(id==='profile')loadPets()}async function boot(){const me=await api('/api/me'),n=me.first_name||me.username||'Пользователь';uname.textContent=n;profileName.textContent=n;profileUser.textContent=me.username?'@'+me.username:'Telegram ID '+me.id;const c=await api('/api/catalog');catalogGrid.innerHTML=c.map(x=>`<article class="card"><div class="icon">🐕</div><h3>${x.name}</h3><p>${x.desc}</p><div class="row"><span class="price">${x.price} ₽</span><button class="btn" onclick="buy(${x.id})">Заказать</button></div></article>`).join('')}async function buy(id){await api('/api/orders',{method:'POST',body:JSON.stringify({item_id:id})});tg?.HapticFeedback?.notificationOccurred('success');go('orders')}function setMode(m){mode=m;loadOrders()}async function loadOrders(){const a=await api(mode==='executor'?'/api/executor/orders':'/api/orders');ordersList.innerHTML=a.length?a.map(o=>`<div class="card order"><div class="row"><h3>${o.item_name}</h3><span class="status">${o.status}</span></div><p>#${o.id} · ${o.price} ₽</p>${mode==='executor'&&o.status==='open'?`<button class="btn" onclick="accept(${o.id})">Взять заказ</button>`:''}${mode==='executor'&&o.status==='accepted'?`<button class="btn" onclick="statusOrder(${o.id},'in_progress')">Начать</button>`:''}${mode==='executor'&&o.status==='in_progress'?`<button class="btn" onclick="statusOrder(${o.id},'done')">Завершить</button>`:''}</div>`).join(''):'<div class="notice">Пока нет заказов</div>'}async function accept(id){await api('/api/executor/orders/'+id+'/accept',{method:'POST'});loadOrders()}async function statusOrder(id,s){await api('/api/executor/orders/'+id+'/status',{method:'POST',body:JSON.stringify({status:s})});loadOrders()}async function loadPets(){const a=await api('/api/pets');pets.innerHTML=a.map(p=>`<p>🐾 ${p.name}${p.breed?' · '+p.breed:''}</p>`).join('')}async function addPet(){await api('/api/pets',{method:'POST',body:JSON.stringify({name:petName.value,breed:petBreed.value})});petName.value='';petBreed.value='';loadPets()}boot().catch(e=>document.body.insertAdjacentHTML('afterbegin','<div class="notice">'+e.message+'</div>'));
</script></body></html>'''

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): print(fmt % args)
    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode(); self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def json_body(self):
        try: return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0') or 0)) or b'{}')
        except: return {}
    def user(self):
        u = validate_init_data(self.headers.get('X-Telegram-Init-Data',''))
        if u:
            c=conn(); c.execute('INSERT OR IGNORE INTO users(id,first_name,username) VALUES(?,?,?)',(u['id'],u.get('first_name',''),u.get('username',''))); c.commit(); c.close()
        return u
    def auth(self):
        u=self.user()
        if not u: self.send_json({'error':'Откройте приложение из Telegram'},401)
        return u
    def do_GET(self):
        p=urllib.parse.urlparse(self.path).path
        if p=='/health': return self.send_json({'status':'ok','test_mode':TEST_MODE})
        if p=='/api/catalog': return self.send_json(CATALOG)
        u=self.auth() if p.startswith('/api/') else None
        if p=='/api/me': return self.send_json(u) if u else None
        if p=='/api/orders' and u:
            c=conn(); rows=c.execute('SELECT * FROM orders WHERE user_id=? ORDER BY id DESC',(u['id'],)).fetchall(); c.close(); return self.send_json([dict(x) for x in rows])
        if p=='/api/executor/orders' and u:
            c=conn(); rows=c.execute("SELECT * FROM orders WHERE status='open' OR executor_id=? ORDER BY id DESC",(u['id'],)).fetchall(); c.close(); return self.send_json([dict(x) for x in rows])
        if p=='/api/pets' and u:
            c=conn(); rows=c.execute('SELECT * FROM pets WHERE user_id=? ORDER BY id DESC',(u['id'],)).fetchall(); c.close(); return self.send_json([dict(x) for x in rows])
        if p.startswith('/api/'): return
        body=HTML.encode(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        p=urllib.parse.urlparse(self.path).path
        if p=='/telegram/webhook':
            d=self.json_body(); m=d.get('message') or {}; chat=(m.get('chat') or {}).get('id')
            if chat and m.get('text','').startswith('/start') and MINI_APP_URL:
                telegram('sendMessage',{'chat_id':chat,'text':'Dog’s Happiness 🐾\nОткройте тестовое приложение:','reply_markup':{'inline_keyboard':[[{'text':'Открыть приложение','web_app':{'url':MINI_APP_URL}}]]}})
            return self.send_json({'ok':True})
        u=self.auth()
        if not u: return
        d=self.json_body()
        if p=='/api/orders':
            item=next((x for x in CATALOG if x['id']==int(d.get('item_id',0))),None)
            if not item: return self.send_json({'error':'Услуга не найдена'},404)
            c=conn(); q=c.execute('INSERT INTO orders(user_id,item_id,item_name,price,status,created_at) VALUES(?,?,?,?,?,?)',(u['id'],item['id'],item['name'],item['price'],'open',datetime.now(timezone.utc).isoformat())); c.commit(); oid=q.lastrowid; c.close(); return self.send_json({'id':oid,'ok':True},201)
        if p=='/api/pets':
            if not d.get('name'): return self.send_json({'error':'Введите имя'},400)
            c=conn(); q=c.execute('INSERT INTO pets(user_id,name,breed) VALUES(?,?,?)',(u['id'],d['name'],d.get('breed',''))); c.commit(); pid=q.lastrowid; c.close(); return self.send_json({'id':pid,'ok':True},201)
        if p.startswith('/api/executor/orders/'):
            parts=p.strip('/').split('/'); oid=int(parts[3]); action=parts[4] if len(parts)>4 else ''; c=conn()
            if action=='accept':
                q=c.execute("UPDATE orders SET executor_id=?,status='accepted' WHERE id=? AND status='open'",(u['id'],oid)); c.commit(); c.close(); return self.send_json({'ok':q.rowcount==1})
            if action=='status':
                st=d.get('status'); q=c.execute('UPDATE orders SET status=? WHERE id=? AND executor_id=?',(st,oid,u['id'])) if st in ('in_progress','done') else None; c.commit(); c.close(); return self.send_json({'ok':bool(q and q.rowcount==1)})
        return self.send_json({'error':'not found'},404)

if __name__=='__main__':
    init_db(); threading.Thread(target=lambda:(time.sleep(2),configure_bot()),daemon=True).start(); print('listening',PORT); ThreadingHTTPServer(('0.0.0.0',PORT),Handler).serve_forever()
