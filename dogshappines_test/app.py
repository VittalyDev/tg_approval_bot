import os, json, hmac, hashlib, sqlite3, urllib.parse, urllib.request, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone

PORT = int(os.getenv('PORT', '3000'))
BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
MINI_APP_URL = os.getenv('MINI_APP_URL', '').strip()
TEST_MODE = os.getenv('TEST_MODE', 'true').lower() == 'true'
DB = '/tmp/dogshappines.sqlite3'
ASSET_DIR = os.path.join(os.path.dirname(__file__), 'assets')

CATALOG = [
    {'id': 1, 'name': 'Выгул собак', 'price': 890, 'desc': '30–60 минут, прогулка и отчёт'},
    {'id': 2, 'name': 'Зооняня', 'price': 1200, 'desc': 'Присмотр дома, кормление и забота'},
    {'id': 3, 'name': 'Кинолог', 'price': 1500, 'desc': 'Индивидуальное занятие с питомцем'},
    {'id': 4, 'name': 'Передержка', 'price': 1900, 'desc': 'Комфорт на время вашего отсутствия'},
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
        return json.loads(values.get('user', '{}')) if hmac.compare_digest(calculated, received_hash) else None
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

HTML = r'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,user-scalable=no"><script src="https://telegram.org/js/telegram-web-app.js"></script><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css"><title>Dog's Happiness</title><style>
:root{--bg:#050505;--card:#0d0c0b;--gold:#c99a55;--gold2:#efcd8f;--text:#f3eadc;--muted:#aa9a82;--line:rgba(213,170,99,.22);--line2:rgba(213,170,99,.36);--shadow:0 22px 50px rgba(0,0,0,.52)}*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}html,body{margin:0;background:radial-gradient(circle at 60% -12%,rgba(144,93,28,.22),transparent 29%),#050505;color:var(--text);font-family:Manrope,system-ui,sans-serif}body{min-height:100vh}button,input{font:inherit}button{cursor:pointer}#app{max-width:430px;margin:auto;padding:12px 12px calc(106px + env(safe-area-inset-bottom))}.top{height:64px;display:flex;align-items:center;justify-content:space-between}.brand{display:flex;align-items:center;gap:11px}.brand-logo{width:48px;height:48px;object-fit:cover;border-radius:16px;border:1px solid var(--line2);box-shadow:0 10px 28px #0009}.brand-name{font-family:'Cormorant Garamond',serif;font-weight:700;font-size:21px;line-height:1}.brand-sub{margin-top:4px;color:var(--muted);font-size:10px}.test-tag{height:30px;padding:0 11px;border-radius:999px;border:1px solid var(--line);display:flex;align-items:center;color:var(--gold2);font-size:9px;font-weight:800;letter-spacing:.18em;text-transform:uppercase}.hero{position:relative;min-height:292px;overflow:hidden;border:1px solid var(--line);border-radius:30px;background:linear-gradient(120deg,#100d09 0%,#090909 52%,#080706 100%);box-shadow:var(--shadow)}.hero:before{content:'';position:absolute;inset:0;background:radial-gradient(circle at 78% 26%,rgba(216,169,93,.25),transparent 28%),linear-gradient(90deg,rgba(0,0,0,.02),rgba(0,0,0,.18));pointer-events:none}.hero-copy{position:relative;z-index:3;width:56%;padding:24px 0 22px 22px}.eyebrow{color:var(--gold2);font-size:10px;font-weight:800;letter-spacing:.19em;text-transform:uppercase}.hero-title{font-family:'Cormorant Garamond',serif;font-size:39px;line-height:.93;font-weight:600;letter-spacing:-.035em;margin:10px 0 9px}.hero-text{color:#cbbda7;font-size:11px;line-height:1.48;margin:0 0 16px}.hero-actions{display:flex;flex-direction:column;gap:8px;width:145px}.btn{border:0;border-radius:15px;min-height:43px;padding:0 14px;font-size:11px;font-weight:800}.btn-gold{background:linear-gradient(145deg,#b57e38,#e2b76a);color:#171108;box-shadow:0 12px 24px rgba(181,126,56,.18)}.btn-dark{background:rgba(255,255,255,.025);color:var(--text);border:1px solid var(--line)}.hero-dog{position:absolute;z-index:2;right:-28px;bottom:-6px;width:60%;height:100%;object-fit:cover;object-position:50% 47%;-webkit-mask-image:linear-gradient(to left,#000 78%,transparent 100%);mask-image:linear-gradient(to left,#000 78%,transparent 100%)}.hero-monogram{position:absolute;right:15px;top:15px;z-index:4;width:36px;height:36px;border-radius:50%;border:1px solid var(--line);display:grid;place-items:center;color:var(--gold2);font-family:'Cormorant Garamond',serif;font-size:19px;background:#080706aa}.story-nav{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin:14px 0 15px}.story{text-align:center}.story-ring{aspect-ratio:1;border:1px solid var(--line2);border-radius:50%;display:grid;place-items:center;background:radial-gradient(circle at top,rgba(208,164,91,.16),rgba(255,255,255,.01));box-shadow:0 12px 22px #0008}.story-ring i{color:var(--gold2);font-size:18px}.story-label{margin-top:5px;color:#c6b69d;font-size:8px;white-space:nowrap}.section-head{display:flex;align-items:end;justify-content:space-between;margin:18px 2px 10px}.section-title{font-family:'Cormorant Garamond',serif;font-size:28px;line-height:1;margin:0}.section-note{color:var(--gold2);font-size:8px;text-transform:uppercase;letter-spacing:.12em}.mosaic{display:grid;grid-template-columns:1fr 1fr;gap:8px}.tile{position:relative;min-height:160px;overflow:hidden;border:1px solid var(--line);border-radius:2px;background:linear-gradient(145deg,#0f0c09,#080706);box-shadow:var(--shadow)}.tile.wide{grid-column:1/-1;min-height:178px}.tile-copy{position:absolute;z-index:3;left:14px;top:14px;right:14px;max-width:64%}.tile-kicker{font-family:'Cormorant Garamond',serif;color:var(--gold2);font-size:17px;line-height:.95;text-transform:uppercase}.tile-text{margin-top:6px;color:#a99880;font-size:9px;line-height:1.35}.tile-symbol{position:absolute;right:13px;bottom:13px;width:54px;height:54px;border-radius:50%;border:1px solid var(--line2);display:grid;place-items:center;background:#090807dd}.tile-symbol i{color:var(--gold2);font-size:22px}.quote-box{position:absolute;inset:50% auto auto 50%;transform:translate(-50%,-50%);width:76%;padding:18px 12px;border:1px solid var(--line2);background:#090807dc;text-align:center;font-family:'Cormorant Garamond',serif;color:var(--gold2);font-size:20px;line-height:1.05}.trust-strip{display:grid;grid-template-columns:repeat(4,1fr);margin-top:8px;border:1px solid var(--line);background:#0b0a09}.trust-item{padding:12px 6px;text-align:center;border-right:1px solid var(--line)}.trust-item:last-child{border-right:0}.trust-item i{display:block;color:var(--gold2);font-size:18px;margin-bottom:7px}.trust-item span{color:#bdad94;font-size:8px;line-height:1.25}.view.hidden{display:none}.page-hero{display:flex;align-items:center;gap:14px;padding:16px;border:1px solid var(--line);background:linear-gradient(135deg,#120e0b,#090807);border-radius:24px;box-shadow:var(--shadow);margin-bottom:12px}.page-hero-icon{width:72px;height:72px;border-radius:20px;border:1px solid var(--line2);display:grid;place-items:center;background:#0a0908}.page-hero-icon i{font-size:27px;color:var(--gold2)}.page-hero-title{font-family:'Cormorant Garamond',serif;font-size:28px;line-height:1;margin:0}.page-hero-sub{color:var(--muted);font-size:11px;line-height:1.35;margin-top:5px}.cards{display:grid;gap:9px}.service{display:grid;grid-template-columns:58px minmax(0,1fr) auto;align-items:center;gap:11px;padding:12px;border:1px solid var(--line);border-radius:20px;background:linear-gradient(180deg,rgba(255,255,255,.025),rgba(255,255,255,.008)),#0e0d0c;box-shadow:0 13px 28px #0006}.service-icon{width:58px;height:58px;border-radius:18px;border:1px solid var(--line);display:grid;place-items:center;background:#12100d}.service-icon i{color:var(--gold2);font-size:23px}.service-name{font-family:'Cormorant Garamond',serif;font-size:20px;font-weight:700;line-height:1}.service-desc{color:var(--muted);font-size:9px;line-height:1.35;margin-top:5px}.service-price{color:var(--gold2);font-size:12px;font-weight:800;text-align:right;margin-bottom:6px}.service-btn{height:36px;padding:0 12px;border:0;border-radius:12px;background:linear-gradient(145deg,#b57e38,#e2b76a);color:#171108;font-size:10px;font-weight:800}.mode{display:flex;gap:5px;padding:4px;border:1px solid var(--line);border-radius:17px;background:#0d0c0b;margin-bottom:10px}.mode button{flex:1;height:38px;border:0;border-radius:13px;background:transparent;color:var(--muted);font-size:10px;font-weight:800}.mode button.active{background:linear-gradient(145deg,#b57e38,#e2b76a);color:#171108}.order{padding:14px;border:1px solid var(--line);border-radius:20px;background:#0d0c0b;box-shadow:0 13px 28px #0006}.order-top{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}.order-name{font-family:'Cormorant Garamond',serif;font-size:21px;font-weight:700}.order-meta{margin-top:5px;color:var(--muted);font-size:9px}.status{display:inline-flex;height:28px;align-items:center;padding:0 9px;border-radius:999px;border:1px solid var(--line);color:var(--gold2);font-size:9px;font-weight:800}.order .btn{margin-top:12px;width:100%}.empty{padding:22px;border:1px dashed var(--line);border-radius:18px;color:var(--muted);text-align:center;font-size:11px}.profile-main{padding:14px;border:1px solid var(--line);border-radius:22px;background:#0d0c0b;box-shadow:var(--shadow)}.profile-row{display:flex;align-items:center;gap:13px}.profile-avatar{width:82px;height:82px;border-radius:22px;border:1px solid var(--line2);display:grid;place-items:center;background:linear-gradient(145deg,#21180f,#0a0908)}.profile-avatar i{font-size:30px;color:var(--gold2)}.profile-name{font-family:'Cormorant Garamond',serif;font-size:28px;font-weight:700;line-height:1}.profile-sub{color:var(--muted);font-size:10px;margin-top:5px}.profile-block{margin-top:10px;padding:14px;border:1px solid var(--line);border-radius:22px;background:#0d0c0b}.profile-block h3{font-family:'Cormorant Garamond',serif;font-size:23px;margin:0 0 9px}.fields{display:grid;gap:7px}.field{height:46px;border-radius:14px;border:1px solid var(--line);background:#15120f;color:var(--text);padding:0 13px;font-size:11px;outline:none}.pet-list{display:grid;gap:8px;margin-top:10px}.pet{display:flex;align-items:center;gap:10px;padding:10px;border:1px solid var(--line);background:#12100e;border-radius:16px}.pet-icon{width:48px;height:48px;border-radius:14px;border:1px solid var(--line);display:grid;place-items:center;background:#18130e}.pet-icon i{color:var(--gold2);font-size:20px}.pet-name{font-weight:800;font-size:12px}.pet-breed{color:var(--muted);font-size:9px;margin-top:3px}.bottom{position:fixed;left:50%;transform:translateX(-50%);bottom:max(8px,env(safe-area-inset-bottom));z-index:20;width:calc(100% - 20px);max-width:410px;display:grid;grid-template-columns:repeat(4,1fr);gap:4px;padding:5px;border:1px solid var(--line);border-radius:26px;background:rgba(6,6,6,.94);backdrop-filter:blur(18px);box-shadow:0 18px 40px #000b}.bottom button{height:60px;border:0;border-radius:19px;background:transparent;color:#826f54;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px}.bottom button i{font-size:18px}.bottom button span{font-size:8px}.bottom button.active{background:linear-gradient(180deg,rgba(201,154,85,.18),rgba(201,154,85,.09));color:var(--gold2);border:1px solid rgba(201,154,85,.12)}@media(max-width:390px){.hero{min-height:280px}.hero-copy{padding-left:18px}.hero-title{font-size:35px}.hero-dog{width:61%}.story-label{font-size:7px}}
</style></head><body><div id="app"><header class="top"><div class="brand"><img class="brand-logo" src="/assets/brand-icon.webp"><div><div class="brand-name">Dog's Happiness</div><div id="userLine" class="brand-sub">премиальный сервис</div></div></div><div class="test-tag">test</div></header><main>
<section id="view-home" class="view"><div class="hero"><div class="hero-copy"><div class="eyebrow">premium pet care</div><h1 class="hero-title">Забота<br>и доверие<br>в каждой<br>прогулке</h1><p class="hero-text">Проверенные ситтеры, индивидуальный подход и отчёты после каждой услуги.</p><div class="hero-actions"><button class="btn btn-gold" onclick="showView('catalog')">Выбрать услугу</button><button class="btn btn-dark" onclick="showView('orders')">Мои заказы</button></div></div><img class="hero-dog" src="/assets/hero-dog.webp"><div class="hero-monogram">DH</div></div>
<div class="story-nav"><div class="story" onclick="showView('catalog')"><div class="story-ring"><i class="fa-solid fa-dog"></i></div><div class="story-label">Услуги</div></div><div class="story"><div class="story-ring"><i class="fa-solid fa-location-dot"></i></div><div class="story-label">Ситтеры</div></div><div class="story"><div class="story-ring"><i class="fa-solid fa-camera"></i></div><div class="story-label">Отчёты</div></div><div class="story"><div class="story-ring"><i class="fa-solid fa-shield-halved"></i></div><div class="story-label">Безопасность</div></div><div class="story" onclick="showView('profile')"><div class="story-ring"><i class="fa-regular fa-user"></i></div><div class="story-label">Профиль</div></div></div>
<div class="section-head"><h2 class="section-title">Dog's Happiness</h2><div class="section-note">premium service</div></div><div class="mosaic"><article class="tile wide"><div class="tile-copy"><div class="tile-kicker">Профессиональные<br>догситтеры</div><div class="tile-text">Опыт, забота и любовь к животным.</div></div><div class="tile-symbol"><i class="fa-solid fa-user-shield"></i></div></article><article class="tile"><div class="tile-copy"><div class="tile-kicker">Больше,<br>чем прогулка</div><div class="tile-text">Активность, игры и внимание.</div></div><div class="tile-symbol"><i class="fa-solid fa-person-walking"></i></div></article><article class="tile"><div class="tile-copy"><div class="tile-kicker">Безопасность<br>прежде всего</div><div class="tile-text">Контроль заказа на каждом этапе.</div></div><div class="tile-symbol"><i class="fa-solid fa-shield-dog"></i></div></article><article class="tile"><div class="quote-box">Доверьте нам самого дорогого</div></article><article class="tile"><div class="tile-copy"><div class="tile-kicker">Фото и видео<br>отчёты</div><div class="tile-text">После каждой прогулки и визита.</div></div><div class="tile-symbol"><i class="fa-solid fa-camera-retro"></i></div></article></div>
<div class="trust-strip"><div class="trust-item"><i class="fa-solid fa-paw"></i><span>Проверенные<br>ситтеры</span></div><div class="trust-item"><i class="fa-solid fa-shield-halved"></i><span>Безопасность<br>и забота</span></div><div class="trust-item"><i class="fa-solid fa-camera"></i><span>Фото и видео<br>отчёты</span></div><div class="trust-item"><i class="fa-solid fa-crown"></i><span>Премиальный<br>сервис</span></div></div></section>
<section id="view-catalog" class="view hidden"><div class="page-hero"><div class="page-hero-icon"><i class="fa-solid fa-dog"></i></div><div><h2 class="page-hero-title">Услуги</h2><div class="page-hero-sub">Выберите формат ухода, который подходит вашему питомцу.</div></div></div><div id="catalogList" class="cards"></div></section>
<section id="view-orders" class="view hidden"><div class="page-hero"><div class="page-hero-icon"><i class="fa-regular fa-rectangle-list"></i></div><div><h2 class="page-hero-title">Заказы</h2><div class="page-hero-sub">История заказов и рабочий режим исполнителя.</div></div></div><div class="mode"><button id="modeCustomer" class="active" onclick="setMode('customer')">Мои заказы</button><button id="modeExecutor" onclick="setMode('executor')">Исполнитель</button></div><div id="ordersList" class="cards"></div></section>
<section id="view-profile" class="view hidden"><div class="profile-main"><div class="profile-row"><div class="profile-avatar"><i class="fa-regular fa-user"></i></div><div><div id="profileName" class="profile-name">Пользователь</div><div id="profileUser" class="profile-sub"></div></div></div></div><div class="profile-block"><h3>Мои питомцы</h3><div class="fields"><input id="petName" class="field" placeholder="Имя питомца"><input id="petBreed" class="field" placeholder="Порода"><button class="btn btn-gold" onclick="addPet()">Добавить питомца</button></div><div id="petsList" class="pet-list"></div></div></section></main></div>
<nav class="bottom"><button data-view="home" class="active" onclick="showView('home')"><i class="fa-solid fa-house"></i><span>Главная</span></button><button data-view="catalog" onclick="showView('catalog')"><i class="fa-solid fa-paw"></i><span>Услуги</span></button><button data-view="orders" onclick="showView('orders')"><i class="fa-regular fa-rectangle-list"></i><span>Заказы</span></button><button data-view="profile" onclick="showView('profile')"><i class="fa-regular fa-user"></i><span>Профиль</span></button></nav>
<script>const tg=window.Telegram?.WebApp;tg?.ready();tg?.expand();const initData=tg?.initData||'';let mode='customer';async function api(path,opt={}){opt.headers={...(opt.headers||{}),'Content-Type':'application/json','X-Telegram-Init-Data':initData};const r=await fetch(path,opt);const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.error||'Ошибка');return d}function setTab(v){document.querySelectorAll('.bottom button').forEach(b=>b.classList.toggle('active',b.dataset.view===v))}function showView(v){document.querySelectorAll('.view').forEach(x=>x.classList.add('hidden'));document.getElementById('view-'+v).classList.remove('hidden');setTab(v);window.scrollTo({top:0,behavior:'smooth'});if(v==='catalog')loadCatalog();if(v==='orders')loadOrders();if(v==='profile')loadPets()}async function boot(){const me=await api('/api/me');const n=me.first_name||me.username||'Пользователь';document.getElementById('userLine').textContent=n+' · премиальный pet care';document.getElementById('profileName').textContent=n;document.getElementById('profileUser').textContent=me.username?'@'+me.username:'Telegram ID '+me.id;await loadCatalog()}async function loadCatalog(){const items=await api('/api/catalog');const icons=['fa-dog','fa-house','fa-graduation-cap','fa-bed'];document.getElementById('catalogList').innerHTML=items.map((x,i)=>`<article class="service"><div class="service-icon"><i class="fa-solid ${icons[i%icons.length]}"></i></div><div><div class="service-name">${x.name}</div><div class="service-desc">${x.desc}</div></div><div><div class="service-price">${x.price} ₽</div><button class="service-btn" onclick="createOrder(${x.id})">Заказать</button></div></article>`).join('')}async function createOrder(id){await api('/api/orders',{method:'POST',body:JSON.stringify({item_id:id})});tg?.HapticFeedback?.notificationOccurred('success');showView('orders')}function setMode(v){mode=v;document.getElementById('modeCustomer').classList.toggle('active',v==='customer');document.getElementById('modeExecutor').classList.toggle('active',v==='executor');loadOrders()}function statusText(s){return({open:'Открыт',accepted:'Взят',in_progress:'В работе',done:'Завершён'})[s]||s}async function loadOrders(){const a=await api(mode==='executor'?'/api/executor/orders':'/api/orders');const t=document.getElementById('ordersList');if(!a.length){t.innerHTML='<div class="empty">Заказов пока нет</div>';return}t.innerHTML=a.map(o=>`<article class="order"><div class="order-top"><div><div class="order-name">${o.item_name}</div><div class="order-meta">Заказ #${o.id} · ${o.price} ₽</div></div><span class="status">${statusText(o.status)}</span></div>${mode==='executor'&&o.status==='open'?`<button class="btn btn-gold" onclick="acceptOrder(${o.id})">Взять заказ</button>`:''}${mode==='executor'&&o.status==='accepted'?`<button class="btn btn-gold" onclick="updateOrder(${o.id},'in_progress')">Начать</button>`:''}${mode==='executor'&&o.status==='in_progress'?`<button class="btn btn-gold" onclick="updateOrder(${o.id},'done')">Завершить</button>`:''}</article>`).join('')}async function acceptOrder(id){await api('/api/executor/orders/'+id+'/accept',{method:'POST'});loadOrders()}async function updateOrder(id,s){await api('/api/executor/orders/'+id+'/status',{method:'POST',body:JSON.stringify({status:s})});loadOrders()}async function loadPets(){const a=await api('/api/pets');const t=document.getElementById('petsList');if(!a.length){t.innerHTML='<div class="empty">Питомцев пока нет</div>';return}t.innerHTML=a.map(p=>`<div class="pet"><div class="pet-icon"><i class="fa-solid fa-dog"></i></div><div><div class="pet-name">${p.name}</div><div class="pet-breed">${p.breed||'Порода не указана'}</div></div></div>`).join('')}async function addPet(){const n=document.getElementById('petName').value.trim(),b=document.getElementById('petBreed').value.trim();if(!n)return;await api('/api/pets',{method:'POST',body:JSON.stringify({name:n,breed:b})});document.getElementById('petName').value='';document.getElementById('petBreed').value='';loadPets()}boot().catch(e=>document.body.insertAdjacentHTML('afterbegin',`<div class="empty" style="margin:12px">${e.message}</div>`));</script></body></html>'''

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): print(fmt % args)
    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode(); self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def json_body(self):
        try: return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0') or 0)) or b'{}')
        except Exception: return {}
    def current_user(self):
        u = validate_init_data(self.headers.get('X-Telegram-Init-Data',''))
        if u:
            c=conn(); c.execute('INSERT OR IGNORE INTO users(id,first_name,username) VALUES(?,?,?)',(u['id'],u.get('first_name',''),u.get('username',''))); c.commit(); c.close()
        return u
    def auth(self):
        u=self.current_user()
        if not u: self.send_json({'error':'Откройте приложение из Telegram'},401)
        return u
    def serve_asset(self, name):
        safe = os.path.basename(name)
        path = os.path.join(ASSET_DIR, safe)
        if not os.path.isfile(path): return self.send_json({'error':'asset not found'},404)
        with open(path,'rb') as f: body=f.read()
        self.send_response(200); self.send_header('Content-Type','image/webp'); self.send_header('Cache-Control','public,max-age=86400'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        p=urllib.parse.urlparse(self.path).path
        if p=='/health': return self.send_json({'status':'ok','test_mode':TEST_MODE})
        if p.startswith('/assets/'): return self.serve_asset(p.split('/assets/',1)[1])
        if p=='/api/catalog': return self.send_json(CATALOG)
        u=self.auth() if p.startswith('/api/') else None
        if p=='/api/me' and u: return self.send_json(u)
        if p=='/api/orders' and u:
            c=conn(); r=c.execute('SELECT * FROM orders WHERE user_id=? ORDER BY id DESC',(u['id'],)).fetchall(); c.close(); return self.send_json([dict(x) for x in r])
        if p=='/api/executor/orders' and u:
            c=conn(); r=c.execute("SELECT * FROM orders WHERE status='open' OR executor_id=? ORDER BY id DESC",(u['id'],)).fetchall(); c.close(); return self.send_json([dict(x) for x in r])
        if p=='/api/pets' and u:
            c=conn(); r=c.execute('SELECT * FROM pets WHERE user_id=? ORDER BY id DESC',(u['id'],)).fetchall(); c.close(); return self.send_json([dict(x) for x in r])
        if p.startswith('/api/'): return
        body=HTML.encode(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        p=urllib.parse.urlparse(self.path).path
        if p=='/telegram/webhook':
            d=self.json_body(); m=d.get('message') or {}; chat=(m.get('chat') or {}).get('id')
            if chat and str(m.get('text','')).startswith('/start') and MINI_APP_URL:
                telegram('sendMessage',{'chat_id':chat,'text':"Dog's Happiness\nОткройте тестовое приложение:",'reply_markup':{'inline_keyboard':[[{'text':'Открыть приложение','web_app':{'url':MINI_APP_URL}}]]}})
            return self.send_json({'ok':True})
        u=self.auth()
        if not u: return
        d=self.json_body()
        if p=='/api/orders':
            item=next((x for x in CATALOG if x['id']==int(d.get('item_id',0))),None)
            if not item: return self.send_json({'error':'Услуга не найдена'},404)
            c=conn(); q=c.execute('INSERT INTO orders(user_id,item_id,item_name,price,status,created_at) VALUES(?,?,?,?,?,?)',(u['id'],item['id'],item['name'],item['price'],'open',datetime.now(timezone.utc).isoformat())); c.commit(); i=q.lastrowid; c.close(); return self.send_json({'id':i,'ok':True},201)
        if p=='/api/pets':
            if not d.get('name'): return self.send_json({'error':'Введите имя'},400)
            c=conn(); q=c.execute('INSERT INTO pets(user_id,name,breed) VALUES(?,?,?)',(u['id'],d['name'],d.get('breed',''))); c.commit(); i=q.lastrowid; c.close(); return self.send_json({'id':i,'ok':True},201)
        if p.startswith('/api/executor/orders/'):
            a=p.strip('/').split('/'); oid=int(a[3]); act=a[4] if len(a)>4 else ''; c=conn()
            if act=='accept':
                q=c.execute("UPDATE orders SET executor_id=?,status='accepted' WHERE id=? AND status='open'",(u['id'],oid)); c.commit(); c.close(); return self.send_json({'ok':q.rowcount==1})
            if act=='status':
                st=d.get('status'); q=c.execute('UPDATE orders SET status=? WHERE id=? AND executor_id=?',(st,oid,u['id'])) if st in ('in_progress','done') else None; c.commit(); c.close(); return self.send_json({'ok':bool(q and q.rowcount==1)})
        return self.send_json({'error':'not found'},404)

if __name__=='__main__':
    init_db(); threading.Thread(target=lambda:(time.sleep(2),configure_bot()),daemon=True).start(); print('listening',PORT); ThreadingHTTPServer(('0.0.0.0',PORT),Handler).serve_forever()
