import json
from datetime import datetime, timezone
import app as base

DEMO_EXECUTORS = [
 {'id':990101,'name':'Алина','rating':5.0,'reviews':124,'area':'Хамовники','city':'Москва','distance':1.2,'price':700,'free':True,'sponsored':True,'image':'sitter-v8.webp','walks':286,'services':[1,2,3,7],'about':'Спокойно работает с разными темпераментами, остаётся на связи и присылает подробный отчёт.'},
 {'id':990102,'name':'Екатерина','rating':4.9,'reviews':98,'area':'Арбат','city':'Москва','distance':2.1,'price':800,'free':True,'sponsored':False,'image':'owner-v8.webp','walks':321,'services':[1,2,3,6],'about':'Любит длинные прогулки и активные игры, умеет работать с крупными собаками.'},
 {'id':990103,'name':'Мария','rating':5.0,'reviews':76,'area':'Тверской','city':'Москва','distance':2.8,'price':900,'free':False,'sponsored':False,'image':'hero-v8.webp','walks':412,'services':[1,2,3,4,7],'about':'Передержка, визиты и прогулки с аккуратным соблюдением режима питомца.'},
 {'id':990104,'name':'Максим','rating':4.8,'reviews':64,'area':'Пресненский','city':'Москва','distance':3.4,'price':650,'free':True,'sponsored':False,'image':'sitter-v8.webp','walks':199,'services':[1,4,8],'about':'Активные прогулки, базовые команды и комфортная работа с молодыми собаками.'},
]

def ensure_column(c, table, name, definition):
    cols={r['name'] for r in c.execute(f'PRAGMA table_info({table})').fetchall()}
    if name not in cols:c.execute(f'ALTER TABLE {table} ADD COLUMN {name} {definition}')

def init_v13():
    base.init_db();c=base.conn();ensure_column(c,'users','executor_enabled','INTEGER DEFAULT 0');ensure_column(c,'orders','target_executor_id','INTEGER')
    c.executescript('''CREATE TABLE IF NOT EXISTS executor_profiles(user_id INTEGER PRIMARY KEY,display_name TEXT,city TEXT DEFAULT 'Москва',area TEXT DEFAULT 'Центр',bio TEXT DEFAULT '',price INTEGER DEFAULT 700,rating REAL DEFAULT 5.0,reviews INTEGER DEFAULT 0,services_json TEXT DEFAULT '[1,2,3,4,7]',image TEXT DEFAULT 'sitter-v8.webp',sponsored INTEGER DEFAULT 0,active INTEGER DEFAULT 1);CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,order_id INTEGER,sender_id INTEGER,text TEXT,created_at TEXT);''');c.commit();c.close()

def upsert_executor(c,user):
    name=(user.get('first_name') or user.get('username') or 'Исполнитель').strip()
    c.execute('''INSERT INTO executor_profiles(user_id,display_name,city,area,bio,price,rating,reviews,services_json,image,sponsored,active) VALUES(?,?,?,?,?,?,?,?,?,?,?,1) ON CONFLICT(user_id) DO UPDATE SET display_name=excluded.display_name,active=1''',(user['id'],name,'Москва','Центр','Проверенный исполнитель Dog’s Happiness. Профиль создан после выбора роли исполнителя.',700,5.0,0,'[1,2,3,4,7]','sitter-v8.webp',0))

def executors(service_id=None):
    out=[dict(x) for x in DEMO_EXECUTORS if not service_id or int(service_id) in x['services']];c=base.conn()
    rows=c.execute('''SELECT ep.*,u.first_name,u.username,(SELECT COUNT(*) FROM orders o WHERE o.executor_id=ep.user_id AND o.status='done') completed,(SELECT COUNT(*) FROM orders o WHERE o.executor_id=ep.user_id AND o.status IN ('accepted','in_progress')) active_orders FROM executor_profiles ep JOIN users u ON u.id=ep.user_id WHERE ep.active=1 AND COALESCE(u.executor_enabled,0)=1''').fetchall();c.close()
    for r in rows:
        d=dict(r)
        try:services=[int(v) for v in json.loads(d.get('services_json') or '[]')]
        except:services=[1,2,3,4,7]
        if service_id and int(service_id) not in services:continue
        completed=int(d.get('completed') or 0)
        out.append({'id':int(d['user_id']),'name':d.get('display_name') or d.get('first_name') or 'Исполнитель','rating':float(d.get('rating') or 5),'reviews':int(d.get('reviews') or completed),'area':d.get('area') or 'Центр','city':d.get('city') or 'Москва','distance':1.0,'price':int(d.get('price') or 700),'free':int(d.get('active_orders') or 0)==0,'sponsored':bool(d.get('sponsored')),'image':d.get('image') or 'sitter-v8.webp','walks':completed,'services':services,'about':d.get('bio') or 'Исполнитель Dog’s Happiness.','dynamic':True})
    return out

def order_access(order,uid):
    return int(order['user_id'] or 0)==int(uid) or int(order['executor_id'] or 0)==int(uid) or int(order['target_executor_id'] or 0)==int(uid)

def save_message(order_id,sender_id,text):
    c=base.conn();c.execute('INSERT INTO messages(order_id,sender_id,text,created_at) VALUES(?,?,?,?)',(order_id,sender_id,text,datetime.now(timezone.utc).isoformat()));c.commit();c.close()
