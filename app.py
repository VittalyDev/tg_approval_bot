import os,json,hmac,hashlib,sqlite3,urllib.parse,urllib.request,threading,time
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from datetime import datetime,timezone
PORT=int(os.getenv('PORT','3000')); BOT_TOKEN=os.getenv('BOT_TOKEN','').strip(); MINI_APP_URL=os.getenv('MINI_APP_URL','').strip(); TEST_MODE=os.getenv('TEST_MODE','true').lower()=='true'; DB='/tmp/dh.sqlite3'
BRAND='/brand.webp'; HERO='/hero.webp'
CAT=[{'id':1,'name':'Выгул собак','price':890,'desc':'Прогулка, игры и фотоотчёт'},{'id':2,'name':'Зооняня','price':1200,'desc':'Присмотр за питомцем дома'},{'id':3,'name':'Кинолог','price':1500,'desc':'Индивидуальное занятие'},{'id':4,'name':'Передержка','price':1900,'desc':'Забота на время вашего отсутствия'}]
def conn():
 c=sqlite3.connect(DB,check_same_thread=False); c.row_factory=sqlite3.Row; return c
def initdb():
 c=conn(); c.executescript("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,first_name TEXT,username TEXT);CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,item_id INTEGER,item_name TEXT,price INTEGER,status TEXT DEFAULT 'open',executor_id INTEGER,created_at TEXT);CREATE TABLE IF NOT EXISTS pets(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,name TEXT,breed TEXT);"); c.commit(); c.close()
def validate(raw):
 if TEST_MODE and not raw:return {'id':777000,'first_name':'Тест','username':'tester'}
 try:
  v=dict(urllib.parse.parse_qsl(raw,keep_blank_values=True)); got=v.pop('hash'); d='\n'.join(f'{k}={v[k]}' for k in sorted(v)); secret=hmac.new(b'WebAppData',BOT_TOKEN.encode(),hashlib.sha256).digest(); calc=hmac.new(secret,d.encode(),hashlib.sha256).hexdigest()
  return json.loads(v.get('user','{}')) if hmac.compare_digest(calc,got) else None
 except:return None
def tg(method,payload):
 if not BOT_TOKEN:return False
 try:
  q=urllib.request.Request(f'https://api.telegram.org/bot{BOT_TOKEN}/{method}',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'}); return json.load(urllib.request.urlopen(q,timeout=15)).get('ok',False)
 except Exception as e: print(method,'FAIL',e); return False
def configbot():
 if not MINI_APP_URL:return
 print('setMyCommands',tg('setMyCommands',{'commands':[{'command':'start','description':'Открыть приложение'}]})); print('setChatMenuButton',tg('setChatMenuButton',{'menu_button':{'type':'web_app','text':'Открыть приложение','web_app':{'url':MINI_APP_URL}}})); print('setWebhook',tg('setWebhook',{'url':MINI_APP_URL.rstrip('/')+'/telegram/webhook','allowed_updates':['message']}))
HTML='''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><script src="https://telegram.org/js/telegram-web-app.js"></script><title>Dog's Happiness</title><style>
*{box-sizing:border-box}:root{--bg:#070707;--s:#12100d;--g:#d7aa5a;--g2:#f1cb82;--t:#f7efe1;--m:#aa987c;--l:rgba(216,171,92,.22)}body{margin:0;background:radial-gradient(circle at 80% -10%,#2a1d0d 0,transparent 38%),var(--bg);color:var(--t);font-family:Inter,system-ui,sans-serif;min-height:100vh}#app{max-width:520px;margin:auto;padding:12px 12px 100px}.top{display:flex;align-items:center;justify-content:space-between;padding:6px 2px 12px}.user{display:flex;align-items:center;gap:10px}.avatar{width:42px;height:42px;border-radius:15px;border:1px solid var(--l);object-fit:cover}.muted{color:var(--m);font-size:11px}.hero{position:relative;min-height:250px;border:1px solid var(--l);border-radius:30px;overflow:hidden;background:radial-gradient(circle at 83% 22%,rgba(215,170,90,.28),transparent 28%),#0c0907;padding:20px 45% 20px 20px;box-shadow:0 22px 45px #0008}.hero h1{font-size:32px;line-height:1;margin:8px 0}.hero p{color:#d4c4aa;font-size:13px;line-height:1.5}.hero img{position:absolute;right:-26px;bottom:-24px;width:55%;max-width:250px;filter:drop-shadow(0 20px 30px #000)}.pill{color:var(--g2);font-size:10px;text-transform:uppercase;letter-spacing:.18em;font-weight:800}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}button{font:inherit}.btn{border:0;border-radius:15px;padding:11px 15px;font-size:12px;font-weight:800;background:linear-gradient(145deg,#b6833c,#e5b96a);color:#181108}.ghost{background:#15110c;color:var(--t);border:1px solid var(--l)}.section{margin-top:14px}.section h2{font-size:17px;margin:0 0 10px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:9px}.card{border:1px solid var(--l);background:linear-gradient(180deg,#ffffff08,#ffffff02),var(--s);border-radius:22px;padding:14px;box-shadow:0 12px 25px #0006}.card h3{font-size:14px;margin:0 0 6px}.card p{font-size:11px;line-height:1.4;color:var(--m);margin:0 0 12px}.price{color:var(--g2);font-weight:800;font-size:15px}.row{display:flex;justify-content:space-between;align-items:center;gap:8px}.tabs{position:fixed;bottom:max(10px,env(safe-area-inset-bottom));left:50%;transform:translateX(-50%);width:calc(100% - 20px);max-width:430px;display:grid;grid-template-columns:repeat(4,1fr);gap:3px;background:#090807ee;border:1px solid var(--l);padding:5px;border-radius:25px;backdrop-filter:blur(18px)}.tab{border:0;background:transparent;color:#8e7c60;padding:10px 4px;border-radius:18px;font-size:10px}.tab.active{background:#d6a65722;color:var(--g2)}.tab b{display:block;font-size:19px;line-height:1;margin-bottom:4px}.hidden{display:none!important}.order{margin-bottom:9px}.status{font-size:10px;padding:4px 8px;border-radius:99px;background:#d7aa5a22;color:var(--g2)}input{width:100%;background:#17130f;border:1px solid var(--l);color:var(--t);border-radius:14px;padding:12px;margin:5px 0}.notice{padding:12px;border-radius:16px;border:1px solid var(--l);background:#d7aa5a10;color:#dbc9aa;font-size:12px;margin-top:10px}
</style></head><body><div id="app"><header class="top"><div class="user"><img class="avatar" src="'''+BRAND+'''"><div><b id="uname">Dog's Happiness</b><div class="muted">премиальный pet care</div></div></div><span class="pill">TEST</span></header><main>
<section id="home" class="view"><div class="hero"><span class="pill">premium pet care</span><h1>Забота, которой можно доверять</h1><p>Выгул, ситтеры и уход за питомцем в одном приложении.</p><div class="actions"><button class="btn" onclick="go('catalog')">Выбрать услугу</button><button class="btn ghost" onclick="go('orders')">Мои заказы</button></div><img src="'''+HERO+'''"></div><div class="section"><h2>Почему мы</h2><div class="grid"><div class="card"><h3>🐾 Проверенные ситтеры</h3><p>Исполнители проходят проверку перед доступом к заказам.</p></div><div class="card"><h3>📸 Фотоотчёты</h3><p>После услуги вы получаете фото и статус выполнения.</p></div><div class="card"><h3>🛡 Безопасность</h3><p>Контроль статусов и история заказов.</p></div><div class="card"><h3>👑 Premium</h3><p>Аккуратный сервис и быстрый подбор.</p></div></div></div></section>
<section id="catalog" class="view hidden"><div class="section"><h2>Услуги</h2><div id="catalogGrid" class="grid"></div></div></section><section id="orders" class="view hidden"><div class="section"><h2>Заказы</h2><div class="actions"><button class="btn" onclick="setMode('customer')">Мои</button><button class="btn ghost" onclick="setMode('executor')">Исполнитель</button></div><div id="ordersList" style="margin-top:10px"></div></div></section><section id="profile" class="view hidden"><div class="section"><h2>Профиль</h2><div class="card"><h3 id="profileName">Пользователь</h3><p id="profileUser"></p><div class="notice">Тестовый стенд: клиентский и исполнительский сценарий.</div></div><div class="section"><h2>Питомцы</h2><div class="card"><input id="petName" placeholder="Имя питомца"><input id="petBreed" placeholder="Порода"><button class="btn" onclick="addPet()">Добавить</button><div id="pets"></div></div></div></div></section></main></div><nav class="tabs"><button class="tab active" onclick="go('home',this)"><b>⌂</b>Главная</button><button class="tab" onclick="go('catalog',this)"><b>🐾</b>Услуги</button><button class="tab" onclick="go('orders',this)"><b>▣</b>Заказы</button><button class="tab" onclick="go('profile',this)"><b>◉</b>Профиль</button></nav><script>
const tg=window.Telegram?.WebApp;tg?.ready();tg?.expand();const initData=tg?.initData||'';let mode='customer';async function api(p,o={}){o.headers={...(o.headers||{}),'Content-Type':'application/json','X-Telegram-Init-Data':initData};let r=await fetch(p,o),d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.error||r.status);return d}function go(id,el){document.querySelectorAll('.view').forEach(x=>x.classList.add('hidden'));document.getElementById(id).classList.remove('hidden');if(el){document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));el.classList.add('active')}if(id==='orders')loadOrders();if(id==='profile')loadPets()}async function boot(){let me=await api('/api/me'),n=me.first_name||me.username||'Пользователь';uname.textContent=n;profileName.textContent=n;profileUser.textContent=me.username?'@'+me.username:'Telegram ID '+me.id;let c=await api('/api/catalog');catalogGrid.innerHTML=c.map(x=>`<article class="card"><h3>${x.name}</h3><p>${x.desc}</p><div class="row"><span class="price">${x.price} ₽</span><button class="btn" onclick="buy(${x.id})">Заказать</button></div></article>`).join('')}async function buy(id){await api('/api/orders',{method:'POST',body:JSON.stringify({item_id:id})});tg?.HapticFeedback?.notificationOccurred('success');go('orders')}function setMode(m){mode=m;loadOrders()}async function loadOrders(){let a=await api(mode==='executor'?'/api/executor/orders':'/api/orders');ordersList.innerHTML=a.length?a.map(o=>`<div class="card order"><div class="row"><h3>${o.item_name}</h3><span class="status">${o.status}</span></div><p>#${o.id} · ${o.price} ₽</p>${mode==='executor'&&o.status==='open'?`<button class="btn" onclick="accept(${o.id})">Взять заказ</button>`:''}${mode==='executor'&&o.status==='accepted'?`<button class="btn" onclick="status(${o.id},'in_progress')">Начать</button>`:''}${mode==='executor'&&o.status==='in_progress'?`<button class="btn" onclick="status(${o.id},'done')">Завершить</button>`:''}</div>`).join(''):'<div class="notice">Пока нет заказов</div>'}async function accept(id){await api('/api/executor/orders/'+id+'/accept',{method:'POST'});loadOrders()}async function status(id,s){await api('/api/executor/orders/'+id+'/status',{method:'POST',body:JSON.stringify({status:s})});loadOrders()}async function loadPets(){let a=await api('/api/pets');pets.innerHTML=a.map(p=>`<p>🐾 ${p.name}${p.breed?' · '+p.breed:''}</p>`).join('')}async function addPet(){await api('/api/pets',{method:'POST',body:JSON.stringify({name:petName.value,breed:petBreed.value})});petName.value='';petBreed.value='';loadPets()}boot().catch(e=>document.body.insertAdjacentHTML('afterbegin','<div class="notice">'+e.message+'</div>'));
</script></body></html>'''
class H(BaseHTTPRequestHandler):
 def log_message(self,f,*a): print(f%a)
 def j(self,o,c=200):
  b=json.dumps(o,ensure_ascii=False).encode();self.send_response(c);self.send_header('Content-Type','application/json;charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def body(self):
  try:return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0') or 0)) or b'{}')
  except:return {}
 def user(self):
  u=validate(self.headers.get('X-Telegram-Init-Data',''))
  if u:
   c=conn();c.execute('INSERT OR IGNORE INTO users(id,first_name,username) VALUES(?,?,?)',(u['id'],u.get('first_name',''),u.get('username','')));c.commit();c.close()
  return u
 def auth(self):
  u=self.user()
  if not u:self.j({'error':'Откройте приложение из Telegram'},401)
  return u
 def do_GET(self):
  p=urllib.parse.urlparse(self.path).path
  if p in ('/brand.webp','/hero.webp'):
   fn=p[1:]; b=open(fn,'rb').read(); self.send_response(200); self.send_header('Content-Type','image/webp'); self.send_header('Cache-Control','public,max-age=86400'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b); return
  if p=='/health':return self.j({'status':'ok','test_mode':TEST_MODE})
  if p=='/api/catalog':return self.j(CAT)
  u=self.auth() if p.startswith('/api/') else None
  if p=='/api/me':return self.j(u) if u else None
  if p=='/api/orders' and u:
   c=conn();r=c.execute('SELECT * FROM orders WHERE user_id=? ORDER BY id DESC',(u['id'],)).fetchall();c.close();return self.j([dict(x) for x in r])
  if p=='/api/executor/orders' and u:
   c=conn();r=c.execute("SELECT * FROM orders WHERE status='open' OR executor_id=? ORDER BY id DESC",(u['id'],)).fetchall();c.close();return self.j([dict(x) for x in r])
  if p=='/api/pets' and u:
   c=conn();r=c.execute('SELECT * FROM pets WHERE user_id=? ORDER BY id DESC',(u['id'],)).fetchall();c.close();return self.j([dict(x) for x in r])
  if p.startswith('/api/'):return
  b=HTML.encode();self.send_response(200);self.send_header('Content-Type','text/html;charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def do_POST(self):
  p=urllib.parse.urlparse(self.path).path
  if p=='/telegram/webhook':
   d=self.body();m=d.get('message') or {};chat=(m.get('chat') or {}).get('id')
   if chat and m.get('text','').startswith('/start') and MINI_APP_URL:tg('sendMessage',{'chat_id':chat,'text':'Dog’s Happiness 🐾\nОткройте тестовое приложение:','reply_markup':{'inline_keyboard':[[{'text':'Открыть приложение','web_app':{'url':MINI_APP_URL}}]]}})
   return self.j({'ok':True})
  u=self.auth();
  if not u:return
  d=self.body()
  if p=='/api/orders':
   item=next((x for x in CAT if x['id']==int(d.get('item_id',0))),None)
   if not item:return self.j({'error':'Услуга не найдена'},404)
   c=conn();q=c.execute('INSERT INTO orders(user_id,item_id,item_name,price,status,created_at) VALUES(?,?,?,?,?,?)',(u['id'],item['id'],item['name'],item['price'],'open',datetime.now(timezone.utc).isoformat()));c.commit();i=q.lastrowid;c.close();return self.j({'id':i,'ok':True},201)
  if p=='/api/pets':
   if not d.get('name'):return self.j({'error':'Введите имя'},400)
   c=conn();q=c.execute('INSERT INTO pets(user_id,name,breed) VALUES(?,?,?)',(u['id'],d['name'],d.get('breed','')));c.commit();i=q.lastrowid;c.close();return self.j({'id':i,'ok':True},201)
  if p.startswith('/api/executor/orders/'):
   a=p.strip('/').split('/');oid=int(a[3]);act=a[4] if len(a)>4 else '';c=conn()
   if act=='accept':q=c.execute("UPDATE orders SET executor_id=?,status='accepted' WHERE id=? AND status='open'",(u['id'],oid));c.commit();c.close();return self.j({'ok':q.rowcount==1})
   if act=='status':
    st=d.get('status');q=c.execute('UPDATE orders SET status=? WHERE id=? AND executor_id=?',(st,oid,u['id'])) if st in ('in_progress','done') else None;c.commit();c.close();return self.j({'ok':bool(q and q.rowcount==1)})
  return self.j({'error':'not found'},404)
if __name__=='__main__':
 initdb();threading.Thread(target=lambda:(time.sleep(2),configbot()),daemon=True).start();print('listening',PORT);ThreadingHTTPServer(('0.0.0.0',PORT),H).serve_forever()
