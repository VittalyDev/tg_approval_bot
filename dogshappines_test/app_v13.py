import threading,time,urllib.parse
from datetime import datetime,timezone,timedelta
from pathlib import Path
import app as base
from v13_support import init_v13,upsert_executor,executors,order_access,save_message

class Handler(base.Handler):
    def serve_file(self,path,cache=False):
        if Path(path).name=='index.html':
            text=Path(path).read_text(encoding='utf-8')
            if '/assets/app-v13.css?v=13' not in text:text=text.replace('</head>','<link rel="stylesheet" href="/assets/app-v13.css?v=13">\n</head>')
            if '/assets/app-v13.js?v=13' not in text:text=text.replace('</body>','<script src="/assets/app-v13.js?v=13"></script>\n</body>')
            body=text.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body);return
        return super().serve_file(path,cache=False)

    def do_GET(self):
        p=urllib.parse.urlparse(self.path);path=p.path;q=urllib.parse.parse_qs(p.query)
        if path=='/health':return self.send_json({'status':'ok','test_mode':base.TEST_MODE,'ui':'premium-v13'})
        if path=='/api/executors':
            u=self.require_user();
            if not u:return
            return self.send_json(executors((q.get('service_id') or [None])[0]))
        if path=='/api/executor/orders':
            u=self.require_user();
            if not u:return
            c=base.conn();rows=c.execute("SELECT * FROM orders WHERE (status='open' AND (target_executor_id IS NULL OR target_executor_id=?)) OR executor_id=? ORDER BY scheduled_date,scheduled_time,id DESC",(u['id'],u['id'])).fetchall();c.close();return self.send_json([dict(r) for r in rows])
        if path=='/api/calendar':
            u=self.require_user();
            if not u:return
            role=(q.get('role') or ['client'])[0];c=base.conn()
            rows=c.execute("SELECT * FROM orders WHERE (executor_id=? AND status IN ('accepted','in_progress','done')) OR (target_executor_id=? AND status='open') ORDER BY scheduled_date,scheduled_time",(u['id'],u['id'])).fetchall() if role=='executor' else c.execute('SELECT * FROM orders WHERE user_id=? ORDER BY scheduled_date,scheduled_time',(u['id'],)).fetchall();c.close();return self.send_json([dict(r) for r in rows])
        if path.startswith('/api/orders/') and path.endswith('/messages'):
            u=self.require_user();
            if not u:return
            oid=int(path.strip('/').split('/')[2]);c=base.conn();o=c.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
            if not o or not order_access(o,u['id']):c.close();return self.send_json({'error':'Нет доступа к чату'},403)
            rows=c.execute("SELECT m.*,COALESCE(u.first_name,u.username,'Пользователь') sender_name FROM messages m LEFT JOIN users u ON u.id=m.sender_id WHERE m.order_id=? ORDER BY m.id",(oid,)).fetchall();c.close();return self.send_json([dict(r) for r in rows])
        if path=='/api/me':
            u=self.require_user();
            if not u:return
            c=base.conn();r=c.execute('SELECT * FROM users WHERE id=?',(u['id'],)).fetchone();c.close();d=dict(r) if r else {};return self.send_json({**u,'role':d.get('role') or '','executor_enabled':bool(d.get('executor_enabled')),'rating_opt_in':bool(d.get('rating_opt_in',1))})
        return super().do_GET()

    def do_POST(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/api/me/role':
            u=self.require_user();
            if not u:return
            d=self.read_json();role=d.get('role')
            if role not in ('client','executor'):return self.send_json({'error':'Некорректная роль'},400)
            c=base.conn();c.execute('UPDATE users SET role=?,executor_enabled=CASE WHEN ?="executor" THEN 1 ELSE COALESCE(executor_enabled,0) END WHERE id=?',(role,role,u['id']));
            if role=='executor':upsert_executor(c,u)
            c.commit();c.close();return self.send_json({'ok':True,'role':role})
        if path=='/api/orders':
            u=self.require_user();
            if not u:return
            d=self.read_json();item=next((x for x in base.CATALOG if x['id']==int(d.get('item_id',0))),None)
            if not item:return self.send_json({'error':'Услуга не найдена'},404)
            date=d.get('scheduled_date') or str(datetime.now().date());tm=d.get('scheduled_time') or datetime.now().strftime('%H:%M');dur=max(30,int(d.get('duration_min') or 60));target=d.get('executor_id')
            try:target=int(target) if target not in (None,'') else None
            except:target=None
            try:
                if datetime.fromisoformat(f'{date}T{tm}:00')<datetime.now()-timedelta(minutes=5):return self.send_json({'error':'Выбранное время уже прошло'},400)
            except:pass
            c=base.conn();cur=c.execute('''INSERT INTO orders(user_id,item_id,item_name,price,status,executor_id,target_executor_id,customer_name,customer_contact,scheduled_date,scheduled_time,duration_min,address,pet_name,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(u['id'],item['id'],item['name'],item['price'],'open',None,target,u.get('first_name','Клиент'),u.get('username',''),date,tm,dur,d.get('address','ул. Тверская, 12'),d.get('pet_name','Бублик'),d.get('notes',''),datetime.now(timezone.utc).isoformat()));c.commit();oid=cur.lastrowid;c.close();return self.send_json({'ok':True,'id':oid,'target_executor_id':target},201)
        if path.startswith('/api/orders/') and path.endswith('/messages'):
            u=self.require_user();
            if not u:return
            oid=int(path.strip('/').split('/')[2]);text=(self.read_json().get('text') or '').strip()
            if not text:return self.send_json({'error':'Сообщение пустое'},400)
            c=base.conn();o=c.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone();c.close()
            if not o or not order_access(o,u['id']):return self.send_json({'error':'Нет доступа к чату'},403)
            save_message(oid,u['id'],text[:1500]);return self.send_json({'ok':True},201)
        if path.startswith('/api/executor/orders/'):
            u=self.require_user();
            if not u:return
            a=path.strip('/').split('/');oid=int(a[3]);action=a[4] if len(a)>4 else '';c=base.conn();o=c.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
            if not o:c.close();return self.send_json({'error':'Заказ не найден'},404)
            if action=='accept':
                if o['target_executor_id'] not in (None,u['id']):c.close();return self.send_json({'error':'Заявка назначена другому исполнителю'},403)
                if base.has_conflict(c,u['id'],o['scheduled_date'],o['scheduled_time'],o['duration_min']):c.close();return self.send_json({'error':'На это время у вас уже есть заказ'},409)
                cur=c.execute("UPDATE orders SET executor_id=?,status='accepted' WHERE id=? AND status='open'",(u['id'],oid));c.commit();c.close();return self.send_json({'ok':cur.rowcount==1})
            c.close()
        return super().do_POST()

if __name__=='__main__':
    init_v13();threading.Thread(target=lambda:(time.sleep(1.2),base.configure_bot()),daemon=True).start();print('listening v13',base.PORT);base.ThreadingHTTPServer(('0.0.0.0',base.PORT),Handler).serve_forever()
