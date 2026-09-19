import base64
import binascii
import json
import mimetypes
import os
import threading
import time
import urllib.parse
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import app_v13 as v13

base = v13.base
DATA_DIR = Path(os.getenv("DATA_DIR", "/data" if Path("/data").exists() else "/tmp"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
base.DB = os.getenv("DB_PATH", str(DATA_DIR / "dogshappines.sqlite3"))
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

REPORT_REQUIRED_SERVICES = {1, 2, 3, 7}
RUS_CITIES = [
    "Москва", "Санкт-Петербург", "Казань", "Екатеринбург",
    "Новосибирск", "Сочи", "Нижний Новгород", "Краснодар"
]

DURATION_PRICE_FACTORS = {
    1: {30: 0.65, 60: 1.0, 90: 1.35},
    2: {720: 0.65, 1440: 1.0, 2880: 1.85},
    3: {30: 0.7, 60: 1.0, 120: 1.75},
    4: {60: 1.0, 90: 1.35},
    5: {30: 1.0, 60: 1.65},
    6: {60: 1.0, 120: 1.65},
    7: {30: 0.75, 60: 1.0},
    8: {30: 0.75, 60: 1.0, 120: 1.75},
}


def ensure_column(c, table, name, definition):
    cols = {r["name"] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}
    if name not in cols:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def init_v14():
    v13.init_v13()
    c = base.conn()
    for name, definition in [
        ("city", "TEXT DEFAULT 'Москва'"),
        ("notifications_enabled", "INTEGER DEFAULT 1"),
        ("privacy_hide_contacts", "INTEGER DEFAULT 1"),
        ("photo_url", "TEXT"),
        ("created_at", "TEXT"),
    ]:
        ensure_column(c, "users", name, definition)

    for name, definition in [
        ("pet_id", "INTEGER"),
        ("target_executor_id", "INTEGER"),
        ("accepted_at", "TEXT"),
        ("started_at", "TEXT"),
        ("completed_at", "TEXT"),
        ("cancelled_at", "TEXT"),
        ("subscription_debited", "INTEGER DEFAULT 0"),
        ("updated_at", "TEXT"),
    ]:
        ensure_column(c, "orders", name, definition)

    ensure_column(c, "pets", "photo_path", "TEXT")

    c.executescript("""
      CREATE TABLE IF NOT EXISTS reports(
        order_id INTEGER PRIMARY KEY,
        executor_id INTEGER NOT NULL,
        summary TEXT NOT NULL,
        distance_km REAL,
        attachments_json TEXT DEFAULT '[]',
        created_at TEXT NOT NULL,
        updated_at TEXT
      );
      CREATE TABLE IF NOT EXISTS reviews(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER UNIQUE NOT NULL,
        client_id INTEGER NOT NULL,
        executor_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        text TEXT DEFAULT '',
        created_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS availability(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        executor_id INTEGER NOT NULL,
        start_at TEXT NOT NULL,
        end_at TEXT NOT NULL,
        note TEXT DEFAULT '',
        created_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS order_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        actor_id INTEGER,
        event_type TEXT NOT NULL,
        text TEXT NOT NULL,
        created_at TEXT NOT NULL
      );
    """)
    ensure_column(c, "messages", "type", "TEXT DEFAULT 'text'")
    ensure_column(c, "messages", "attachment_url", "TEXT")
    ensure_column(c, "executor_profiles", "active", "INTEGER DEFAULT 1")

    # Final demo cleanup: keep geography consistent with the Russia-only product scope.
    city_marks = ",".join("?" for _ in RUS_CITIES)
    c.execute(
        f"UPDATE users SET city='Москва' WHERE city IS NULL OR TRIM(city)='' OR city NOT IN ({city_marks})",
        tuple(RUS_CITIES),
    )
    c.execute(
        f"UPDATE executor_profiles SET city='Москва' WHERE city IS NULL OR TRIM(city)='' OR city NOT IN ({city_marks})",
        tuple(RUS_CITIES),
    )
    for old_area, new_area in {
        "Прозивка": "Хамовники",
        "Mali Bajmok": "Арбат",
        "Радиалац": "Пресненский",
        "Баймок": "Арбат",
    }.items():
        c.execute("UPDATE executor_profiles SET area=? WHERE area=?", (new_area, old_area))

    c.commit()
    c.close()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def parse_dt(date_str, time_str):
    try:
        return datetime.fromisoformat(f"{date_str}T{time_str}:00")
    except Exception:
        return None


def order_range(row):
    start = parse_dt(row["scheduled_date"], row["scheduled_time"])
    if not start:
        return None, None
    return start, start + timedelta(minutes=max(1, int(row["duration_min"] or 60)))


def ranges_overlap(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end


def executor_conflict(c, executor_id, date_str, time_str, duration, exclude_order_id=None):
    start = parse_dt(date_str, time_str)
    if not start:
        return True
    end = start + timedelta(minutes=max(1, int(duration or 60)))
    rows = c.execute(
        """SELECT * FROM orders
           WHERE status IN ('open','accepted','in_progress')
             AND (executor_id=? OR target_executor_id=?)""",
        (executor_id, executor_id),
    ).fetchall()
    for row in rows:
        if exclude_order_id and int(row["id"]) == int(exclude_order_id):
            continue
        other_start, other_end = order_range(row)
        if other_start and ranges_overlap(start, end, other_start, other_end):
            return True
    blocks = c.execute(
        "SELECT * FROM availability WHERE executor_id=?",
        (executor_id,),
    ).fetchall()
    for block in blocks:
        try:
            b_start = datetime.fromisoformat(block["start_at"])
            b_end = datetime.fromisoformat(block["end_at"])
        except Exception:
            continue
        if ranges_overlap(start, end, b_start, b_end):
            return True
    return False


def calc_price(item_id, duration, base_price=None):
    item = next((x for x in base.CATALOG if int(x["id"]) == int(item_id)), None)
    if not item:
        return 0
    duration = int(duration or 60)
    factors = DURATION_PRICE_FACTORS.get(int(item_id), {})
    if duration in factors:
        factor = factors[duration]
    else:
        base_minutes = 1440 if int(item_id) == 2 else 60
        factor = max(0.65, duration / base_minutes)
    amount = int(base_price) if base_price is not None else int(item["price"])
    return int(round((amount * factor) / 50.0) * 50)


def safe_attachment_name(name):
    return Path(name or "").name.replace("..", "")[:100]


def save_data_url(data_url, prefix):
    if not data_url or "," not in data_url:
        raise ValueError("Некорректное изображение")
    header, encoded = data_url.split(",", 1)
    if "base64" not in header:
        raise ValueError("Изображение должно быть base64")
    ext = "jpg"
    if "image/png" in header:
        ext = "png"
    elif "image/webp" in header:
        ext = "webp"
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("Не удалось прочитать изображение")
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("Изображение слишком большое")
    name = f"{prefix}-{uuid.uuid4().hex}.{ext}"
    (UPLOAD_DIR / name).write_bytes(raw)
    return f"/uploads/{name}"


def user_settings_row(c, user_id):
    return c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()


def upsert_executor(c, user):
    row = user_settings_row(c, user["id"])
    city = (row["city"] if row and row["city"] in RUS_CITIES else "Москва")
    photo = (row["photo_url"] if row else None) or "sitter-v8.webp"
    name = (user.get("first_name") or user.get("username") or "Исполнитель").strip()
    c.execute(
        """INSERT INTO executor_profiles(
             user_id,display_name,city,area,bio,price,rating,reviews,
             services_json,image,sponsored,active
           ) VALUES(?,?,?,?,?,?,?,?,?,?,?,1)
           ON CONFLICT(user_id) DO UPDATE SET
             display_name=excluded.display_name,
             city=excluded.city,
             image=CASE WHEN executor_profiles.image IS NULL OR executor_profiles.image='' THEN excluded.image ELSE executor_profiles.image END,
             active=1""",
        (
            user["id"], name, city, "Центр",
            "Исполнитель Dog’s Happiness. Укажите опыт, формат работы и особенности ухода в настройках профиля.",
            700, 5.0, 0, "[1,2,3,4,6,7,8]", photo, 0
        ),
    )


def executor_rows(c, service_id=None, city=None, requester_id=None):
    rows = c.execute(
        """SELECT ep.*,u.first_name,u.username,u.photo_url,
          (SELECT COUNT(*) FROM orders o WHERE o.executor_id=ep.user_id AND o.status='done') completed,
          (SELECT COUNT(*) FROM reviews r WHERE r.executor_id=ep.user_id) review_count,
          (SELECT AVG(r.rating) FROM reviews r WHERE r.executor_id=ep.user_id) avg_rating
          FROM executor_profiles ep
          JOIN users u ON u.id=ep.user_id
          WHERE ep.active=1 AND COALESCE(u.executor_enabled,0)=1"""
    ).fetchall()
    out = []
    for row in rows:
        d = dict(row)
        try:
            services = [int(v) for v in json.loads(d.get("services_json") or "[]")]
        except Exception:
            services = [1, 2, 3, 4, 6, 7, 8]
        if service_id and int(service_id) not in services:
            continue
        if city and d.get("city") and d.get("city") != city:
            continue
        if not base.TEST_MODE and requester_id and int(d["user_id"]) == int(requester_id):
            continue
        rating = float(d.get("avg_rating") or d.get("rating") or 5.0)
        out.append({
            "id": int(d["user_id"]),
            "name": d.get("display_name") or d.get("first_name") or "Исполнитель",
            "rating": round(rating, 1),
            "reviews": int(d.get("review_count") or 0),
            "area": d.get("area") or "Центр",
            "city": d.get("city") or "Москва",
            "price": max(
                int(d.get("price") or 700),
                int(next((x["price"] for x in base.CATALOG if service_id and int(x["id"]) == int(service_id)), 0) or 0)
            ),
            "free": True,
            "sponsored": bool(d.get("sponsored")),
            "image": d.get("photo_url") or d.get("image") or "sitter-v8.webp",
            "walks": int(d.get("completed") or 0),
            "services": services,
            "about": d.get("bio") or "",
            "dynamic": True,
        })
    return out


def executor_name(c, executor_id):
    if not executor_id:
        return None
    row = c.execute(
        "SELECT display_name FROM executor_profiles WHERE user_id=?",
        (executor_id,),
    ).fetchone()
    return row["display_name"] if row else None


def report_for(c, order_id):
    row = c.execute("SELECT * FROM reports WHERE order_id=?", (order_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        d["attachments"] = json.loads(d.pop("attachments_json") or "[]")
    except Exception:
        d["attachments"] = []
    return d


def review_for(c, order_id):
    row = c.execute("SELECT * FROM reviews WHERE order_id=?", (order_id,)).fetchone()
    return dict(row) if row else None


def serialize_order(c, row, viewer_id, viewer_role):
    d = dict(row)
    eid = d.get("executor_id") or d.get("target_executor_id")
    d["executor_name"] = executor_name(c, eid)
    d["report_ready"] = bool(c.execute("SELECT 1 FROM reports WHERE order_id=?", (d["id"],)).fetchone())
    d["reviewed"] = bool(c.execute("SELECT 1 FROM reviews WHERE order_id=?", (d["id"],)).fetchone())
    if viewer_role == "executor" and d.get("status") == "open":
        owner = user_settings_row(c, d["user_id"])
        if owner and int(owner["privacy_hide_contacts"] or 0):
            d["customer_contact"] = ""
    return d


def order_access(row, uid):
    return (
        int(row["user_id"] or 0) == int(uid)
        or int(row["executor_id"] or 0) == int(uid)
        or int(row["target_executor_id"] or 0) == int(uid)
    )


def add_event(c, order_id, actor_id, event_type, text, add_chat=True):
    ts = now_iso()
    c.execute(
        "INSERT INTO order_events(order_id,actor_id,event_type,text,created_at) VALUES(?,?,?,?,?)",
        (order_id, actor_id, event_type, text, ts),
    )
    if add_chat:
        c.execute(
            "INSERT INTO messages(order_id,sender_id,type,text,created_at) VALUES(?,?,?,?,?)",
            (order_id, 0, "system", text, ts),
        )


def notify_user(user_id, text):
    if not user_id or not base.BOT_TOKEN:
        return
    c = base.conn()
    row = user_settings_row(c, user_id)
    c.close()
    if row and int(row["notifications_enabled"] or 0) == 0:
        return
    threading.Thread(
        target=lambda: base.telegram("sendMessage", {"chat_id": int(user_id), "text": text}),
        daemon=True,
    ).start()


def debit_subscription_once(c, order):
    if int(order["item_id"] or 0) != 1 or int(order["subscription_debited"] or 0):
        return
    sub = c.execute(
        """SELECT * FROM subscriptions
           WHERE user_id=? AND status='active'
           ORDER BY id DESC LIMIT 1""",
        (order["user_id"],),
    ).fetchone()
    if not sub:
        c.execute("UPDATE orders SET subscription_debited=1 WHERE id=?", (order["id"],))
        return
    if int(sub["used_walks"] or 0) < int(sub["total_walks"] or 0):
        c.execute("UPDATE subscriptions SET used_walks=used_walks+1 WHERE id=?", (sub["id"],))
    c.execute("UPDATE orders SET subscription_debited=1 WHERE id=?", (order["id"],))


def serve_bytes(handler, body, content_type, cache="no-store"):
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", cache)
    handler.end_headers()
    handler.wfile.write(body)


class Handler(v13.Handler):
    def current_user(self):
        user = base.validate_init_data(self.headers.get("X-Telegram-Init-Data", ""))
        if not user:
            return None
        c = base.conn()
        c.execute(
            """INSERT OR IGNORE INTO users(
               id,first_name,username,photo_url,city,notifications_enabled,privacy_hide_contacts,created_at
               ) VALUES(?,?,?,?,?,?,?,?)""",
            (
                user["id"], user.get("first_name", ""), user.get("username", ""),
                user.get("photo_url"), "Москва", 1, 1, now_iso(),
            ),
        )
        c.execute(
            "UPDATE users SET first_name=?,username=?,photo_url=COALESCE(?,photo_url) WHERE id=?",
            (user.get("first_name", ""), user.get("username", ""), user.get("photo_url"), user["id"]),
        )
        c.commit()
        c.close()
        return user

    def serve_file(self, path, cache=False):
        if Path(path).name == "index.html":
            text = Path(path).read_text(encoding="utf-8")
            if "/assets/app-v13.css?v=13" not in text:
                text = text.replace("</head>", '<link rel="stylesheet" href="/assets/app-v13.css?v=13">\n</head>')
            if "/assets/app-v14.css?v=14" not in text:
                text = text.replace("</head>", '<link rel="stylesheet" href="/assets/app-v14.css?v=14">\n</head>')
            if "/assets/app-v13.js?v=13" not in text:
                text = text.replace("</body>", '<script src="/assets/app-v13.js?v=13"></script>\n</body>')
            if "/assets/app-v14.js?v=14" not in text:
                text = text.replace("</body>", '<script src="/assets/app-v14.js?v=14"></script>\n</body>')
            return serve_bytes(self, text.encode(), "text/html; charset=utf-8")
        return super().serve_file(path, cache=False)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        q = urllib.parse.parse_qs(parsed.query)

        if path == "/health":
            return self.send_json({
                "status": "ok",
                "test_mode": base.TEST_MODE,
                "ui": "premium-v14",
                "persistent_db": str(base.DB).startswith("/data/"),
            })

        if path.startswith("/uploads/"):
            name = safe_attachment_name(path.split("/uploads/", 1)[1])
            file_path = UPLOAD_DIR / name
            if not file_path.exists():
                return self.send_json({"error": "not found"}, 404)
            return serve_bytes(
                self,
                file_path.read_bytes(),
                mimetypes.guess_type(str(file_path))[0] or "application/octet-stream",
                "private,max-age=3600",
            )

        if not path.startswith("/api/"):
            return super().do_GET()

        user = self.require_user()
        if not user:
            return
        uid = int(user["id"])
        c = base.conn()

        if path == "/api/me":
            row = user_settings_row(c, uid)
            d = dict(row) if row else {}
            c.close()
            return self.send_json({
                **user,
                "role": d.get("role") or "",
                "city": d.get("city") if d.get("city") in RUS_CITIES else "Москва",
                "notifications_enabled": bool(d.get("notifications_enabled", 1)),
                "privacy_hide_contacts": bool(d.get("privacy_hide_contacts", 1)),
                "executor_enabled": bool(d.get("executor_enabled")),
                "rating_opt_in": bool(d.get("rating_opt_in", 1)),
            })

        if path == "/api/settings":
            row = user_settings_row(c, uid)
            ep = c.execute("SELECT active FROM executor_profiles WHERE user_id=?", (uid,)).fetchone()
            c.close()
            return self.send_json({
                "city": (row["city"] if row and row["city"] in RUS_CITIES else "Москва"),
                "notifications_enabled": bool(row["notifications_enabled"] if row else 1),
                "privacy_hide_contacts": bool(row["privacy_hide_contacts"] if row else 1),
                "rating_opt_in": bool(row["rating_opt_in"] if row else 1),
                "executor_profile_active": bool(ep["active"]) if ep else False,
                "has_executor_profile": bool(ep),
                "cities": RUS_CITIES,
            })

        if path == "/api/executors":
            service = (q.get("service_id") or [None])[0]
            city = (q.get("city") or [None])[0]
            if city not in RUS_CITIES:
                row = user_settings_row(c, uid)
                city = row["city"] if row and row["city"] in RUS_CITIES else "Москва"
            rows = executor_rows(c, service, city, uid)
            c.close()
            return self.send_json(rows)

        if path == "/api/executor/profile":
            row = c.execute("SELECT * FROM executor_profiles WHERE user_id=?", (uid,)).fetchone()
            if not row:
                c.close()
                return self.send_json(None)
            d = dict(row)
            d["name"] = d.get("display_name") or user.get("first_name") or user.get("username") or "Исполнитель"
            urow = user_settings_row(c, uid)
            if urow and urow["photo_url"]:
                d["image"] = urow["photo_url"]
            try:
                d["services"] = json.loads(d.pop("services_json") or "[]")
            except Exception:
                d["services"] = []
            c.close()
            return self.send_json(d)

        if path == "/api/orders":
            rows = c.execute(
                "SELECT * FROM orders WHERE user_id=? ORDER BY scheduled_date DESC,scheduled_time DESC,id DESC",
                (uid,),
            ).fetchall()
            result = [serialize_order(c, r, uid, "client") for r in rows]
            c.close()
            return self.send_json(result)

        if path.startswith("/api/orders/") and path.endswith("/messages"):
            oid = int(path.strip("/").split("/")[2])
            order = c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
            if not order or not order_access(order, uid):
                c.close()
                return self.send_json({"error": "Нет доступа к чату"}, 403)
            rows = c.execute(
                """SELECT m.*,COALESCE(u.first_name,u.username,'Система') sender_name
                   FROM messages m LEFT JOIN users u ON u.id=m.sender_id
                   WHERE m.order_id=? ORDER BY m.id""",
                (oid,),
            ).fetchall()
            c.close()
            return self.send_json([dict(r) for r in rows])

        if path.startswith("/api/orders/") and path.endswith("/report"):
            oid = int(path.strip("/").split("/")[2])
            order = c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
            if not order or not order_access(order, uid):
                c.close()
                return self.send_json({"error": "Нет доступа к отчёту"}, 403)
            report = report_for(c, oid)
            c.close()
            return self.send_json(report)

        if path.startswith("/api/orders/"):
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[0] == "api" and parts[1] == "orders":
                oid = int(parts[2])
                order = c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
                if not order or not order_access(order, uid):
                    c.close()
                    return self.send_json({"error": "Заказ не найден"}, 404)
                role = "client" if int(order["user_id"]) == uid else "executor"
                result = serialize_order(c, order, uid, role)
                result["events"] = [dict(x) for x in c.execute(
                    "SELECT * FROM order_events WHERE order_id=? ORDER BY id", (oid,)
                ).fetchall()]
                result["report"] = report_for(c, oid)
                result["review"] = review_for(c, oid)
                c.close()
                return self.send_json(result)

        if path == "/api/executor/orders":
            rows = c.execute(
                """SELECT * FROM orders
                   WHERE (status='open' AND (target_executor_id IS NULL OR target_executor_id=?))
                      OR executor_id=?
                   ORDER BY scheduled_date,scheduled_time,id DESC""",
                (uid, uid),
            ).fetchall()
            result = [serialize_order(c, r, uid, "executor") for r in rows]
            c.close()
            return self.send_json(result)

        if path == "/api/calendar":
            role = (q.get("role") or ["client"])[0]
            if role == "executor":
                orders = c.execute(
                    """SELECT * FROM orders
                       WHERE (target_executor_id=? AND status='open')
                          OR (executor_id=? AND status IN ('accepted','in_progress','done'))
                       ORDER BY scheduled_date,scheduled_time""",
                    (uid, uid),
                ).fetchall()
                blocks = c.execute(
                    "SELECT * FROM availability WHERE executor_id=? ORDER BY start_at",
                    (uid,),
                ).fetchall()
                result = {
                    "orders": [serialize_order(c, r, uid, "executor") for r in orders],
                    "blocks": [dict(r) for r in blocks],
                }
            else:
                orders = c.execute(
                    "SELECT * FROM orders WHERE user_id=? ORDER BY scheduled_date,scheduled_time",
                    (uid,),
                ).fetchall()
                result = {
                    "orders": [serialize_order(c, r, uid, "client") for r in orders],
                    "blocks": [],
                }
            c.close()
            return self.send_json(result)

        if path == "/api/executor/availability":
            rows = c.execute(
                "SELECT * FROM availability WHERE executor_id=? ORDER BY start_at",
                (uid,),
            ).fetchall()
            c.close()
            return self.send_json([dict(r) for r in rows])

        if path == "/api/pets":
            rows = c.execute(
                "SELECT id,user_id,name,breed,photo_path FROM pets WHERE user_id=? ORDER BY id DESC",
                (uid,),
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["photo_url"] = d.pop("photo_path") or ""
                out.append(d)
            c.close()
            return self.send_json(out)

        if path == "/api/client/stats":
            total = c.execute("SELECT COUNT(*) FROM orders WHERE user_id=?", (uid,)).fetchone()[0]
            done = c.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND status='done'", (uid,)).fetchone()[0]
            walks = c.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND item_id=1 AND status='done'", (uid,)).fetchone()[0]
            pets = c.execute("SELECT COUNT(*) FROM pets WHERE user_id=?", (uid,)).fetchone()[0]
            c.close()
            return self.send_json({"orders": total, "done": done, "walks": walks, "pets": pets})

        if path == "/api/executor/stats":
            completed = c.execute("SELECT COUNT(*) FROM orders WHERE executor_id=? AND status='done'", (uid,)).fetchone()[0]
            active = c.execute("SELECT COUNT(*) FROM orders WHERE executor_id=? AND status IN ('accepted','in_progress')", (uid,)).fetchone()[0]
            income = c.execute("SELECT COALESCE(SUM(price),0) FROM orders WHERE executor_id=? AND status='done'", (uid,)).fetchone()[0]
            avg = c.execute("SELECT AVG(rating) FROM reviews WHERE executor_id=?", (uid,)).fetchone()[0] or 5.0
            all_exec = c.execute(
                """SELECT ep.user_id,COUNT(o.id) score FROM executor_profiles ep
                   LEFT JOIN orders o ON o.executor_id=ep.user_id AND o.status='done'
                   WHERE ep.active=1 GROUP BY ep.user_id ORDER BY score DESC"""
            ).fetchall()
            rank = next((i + 1 for i, r in enumerate(all_exec) if int(r["user_id"]) == uid), None)
            c.close()
            return self.send_json({
                "completed": completed, "active": active, "income": income,
                "rating": round(float(avg), 1), "rank": rank or 1
            })

        if path == "/api/leaderboard":
            client_rows = c.execute(
                """SELECT u.id,u.first_name,u.username,COUNT(o.id) score
                   FROM users u LEFT JOIN orders o ON o.user_id=u.id AND o.status='done'
                   WHERE COALESCE(u.rating_opt_in,1)=1
                   GROUP BY u.id ORDER BY score DESC,u.id ASC LIMIT 50"""
            ).fetchall()
            exec_rows = c.execute(
                """SELECT ep.user_id,ep.display_name,COUNT(DISTINCT o.id) score,
                          COALESCE(AVG(r.rating),5.0) rating
                   FROM executor_profiles ep
                   LEFT JOIN orders o ON o.executor_id=ep.user_id AND o.status='done'
                   LEFT JOIN reviews r ON r.executor_id=ep.user_id
                   WHERE ep.active=1
                   GROUP BY ep.user_id ORDER BY score DESC,rating DESC LIMIT 50"""
            ).fetchall()
            me_row = user_settings_row(c, uid)
            c.close()
            return self.send_json({
                "clients": [
                    {"id": r["id"], "name": r["first_name"] or r["username"] or "Клиент", "score": int(r["score"] or 0), "me": int(r["id"]) == uid}
                    for r in client_rows
                ],
                "executors": [
                    {"id": r["user_id"], "name": r["display_name"], "score": int(r["score"] or 0), "rating": round(float(r["rating"] or 5.0), 1), "me": int(r["user_id"]) == uid}
                    for r in exec_rows
                ],
                "rating_opt_in": bool(me_row["rating_opt_in"] if me_row else 1),
            })

        c.close()
        return super().do_GET()

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/telegram/webhook":
            return super().do_POST()

        user = self.require_user()
        if not user:
            return
        uid = int(user["id"])
        data = self.read_json()
        c = base.conn()

        if path == "/api/me/role":
            role = data.get("role")
            if role not in ("client", "executor"):
                c.close()
                return self.send_json({"error": "Некорректная роль"}, 400)
            c.execute(
                """UPDATE users SET role=?,executor_enabled=
                   CASE WHEN ?='executor' THEN 1 ELSE COALESCE(executor_enabled,0) END
                   WHERE id=?""",
                (role, role, uid),
            )
            if role == "executor":
                upsert_executor(c, user)
            c.commit()
            c.close()
            return self.send_json({"ok": True, "role": role})

        if path == "/api/me/rating-opt":
            enabled = 1 if bool(data.get("enabled")) else 0
            c.execute("UPDATE users SET rating_opt_in=? WHERE id=?", (enabled, uid))
            c.commit()
            c.close()
            return self.send_json({"ok": True, "enabled": bool(enabled)})

        if path == "/api/subscription/buy":
            plan = next((x for x in base.TARIFFS if x["id"] == data.get("plan_id")), None)
            if not plan:
                c.close()
                return self.send_json({"error": "Тариф не найден"}, 404)
            c.execute("UPDATE subscriptions SET status='inactive' WHERE user_id=? AND status='active'", (uid,))
            renew = datetime.now(timezone.utc).date() + timedelta(days=30)
            c.execute(
                "INSERT INTO subscriptions(user_id,plan_id,plan_name,price,total_walks,used_walks,renew_date,status) VALUES(?,?,?,?,?,?,?,?)",
                (uid, plan["id"], plan["name"], plan["price"], plan["walks"], 0, str(renew), "active"),
            )
            c.commit()
            c.close()
            return self.send_json({"ok": True})

        if path == "/api/settings":
            city = data.get("city")
            if city not in RUS_CITIES:
                city = None
            fields = []
            values = []
            if city:
                fields.append("city=?")
                values.append(city)
            for key in ("notifications_enabled", "privacy_hide_contacts", "rating_opt_in"):
                if key in data:
                    fields.append(f"{key}=?")
                    values.append(1 if bool(data[key]) else 0)
            if fields:
                values.append(uid)
                c.execute(f"UPDATE users SET {','.join(fields)} WHERE id=?", tuple(values))
            if city:
                c.execute("UPDATE executor_profiles SET city=? WHERE user_id=?", (city, uid))
            if "executor_profile_active" in data:
                c.execute(
                    "UPDATE executor_profiles SET active=? WHERE user_id=?",
                    (1 if bool(data["executor_profile_active"]) else 0, uid),
                )
            c.commit()
            c.close()
            return self.send_json({"ok": True})

        if path == "/api/executor/profile":
            row = c.execute("SELECT * FROM executor_profiles WHERE user_id=?", (uid,)).fetchone()
            if not row:
                upsert_executor(c, user)
            bio = (data.get("bio") or "").strip()[:800]
            area = (data.get("area") or "Центр").strip()[:80]
            price = max(300, min(10000, int(data.get("price") or 700)))
            services = data.get("services") or []
            valid_services = sorted({int(x) for x in services if str(x).isdigit() and 1 <= int(x) <= 8})
            if not valid_services:
                valid_services = [1]
            c.execute(
                "UPDATE executor_profiles SET bio=?,area=?,price=?,services_json=? WHERE user_id=?",
                (bio, area, price, json.dumps(valid_services), uid),
            )
            c.commit()
            c.close()
            return self.send_json({"ok": True})

        if path == "/api/orders":
            try:
                item_id = int(data.get("item_id"))
            except Exception:
                c.close()
                return self.send_json({"error": "Услуга не найдена"}, 404)
            item = next((x for x in base.CATALOG if int(x["id"]) == item_id), None)
            if not item:
                c.close()
                return self.send_json({"error": "Услуга не найдена"}, 404)
            try:
                target = int(data.get("executor_id")) if data.get("executor_id") not in (None, "") else None
            except Exception:
                target = None
            date_str = data.get("scheduled_date") or ""
            time_str = data.get("scheduled_time") or ""
            start = parse_dt(date_str, time_str)
            if not start:
                c.close()
                return self.send_json({"error": "Укажите дату и время"}, 400)
            if start < datetime.now() - timedelta(minutes=1):
                c.close()
                return self.send_json({"error": "Выбранное время уже прошло"}, 400)
            duration = max(30, min(2880, int(data.get("duration_min") or 60)))
            pet_id = data.get("pet_id")
            pet = None
            if pet_id not in (None, ""):
                try:
                    pet = c.execute("SELECT * FROM pets WHERE id=? AND user_id=?", (int(pet_id), uid)).fetchone()
                except Exception:
                    pet = None
            if not pet:
                c.close()
                return self.send_json({"error": "Сначала выберите питомца"}, 400)
            ep = None
            if target:
                ep = c.execute("SELECT * FROM executor_profiles WHERE user_id=? AND active=1", (target,)).fetchone()
                if not ep:
                    c.close()
                    return self.send_json({"error": "Исполнитель больше недоступен"}, 409)
                try:
                    services = [int(x) for x in json.loads(ep["services_json"] or "[]")]
                except Exception:
                    services = []
                if item_id not in services:
                    c.close()
                    return self.send_json({"error": "Исполнитель не оказывает эту услугу"}, 409)
                if executor_conflict(c, target, date_str, time_str, duration):
                    c.close()
                    return self.send_json({"error": "У исполнителя уже занято это время. Выберите другое время."}, 409)
            address = (data.get("address") or "").strip()
            if item_id != 5 and len(address) < 5:
                c.close()
                return self.send_json({"error": "Укажите адрес"}, 400)
            executor_base = max(int(ep["price"] or 0), int(item["price"])) if target else int(item["price"])
            price = calc_price(item_id, duration, executor_base)
            ts = now_iso()
            cur = c.execute(
                """INSERT INTO orders(
                   user_id,item_id,item_name,price,status,executor_id,target_executor_id,
                   customer_name,customer_contact,scheduled_date,scheduled_time,duration_min,
                   address,pet_id,pet_name,notes,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    uid, item_id, item["name"], price, "open", None, target,
                    user.get("first_name", "Клиент"), user.get("username", ""),
                    date_str, time_str, duration, address, int(pet["id"]), pet["name"],
                    (data.get("notes") or "").strip()[:1200], ts, ts,
                ),
            )
            oid = cur.lastrowid
            add_event(c, oid, uid, "created", "Заявка создана и отправлена исполнителю" if target else "Заявка создана")
            c.commit()
            c.close()
            if target:
                notify_user(target, f"Новая заявка: {item['name']} · {date_str} {time_str}")
            return self.send_json({"ok": True, "id": oid, "price": price}, 201)

        if path.startswith("/api/orders/") and path.endswith("/cancel"):
            oid = int(path.strip("/").split("/")[2])
            order = c.execute("SELECT * FROM orders WHERE id=? AND user_id=?", (oid, uid)).fetchone()
            if not order:
                c.close()
                return self.send_json({"error": "Заказ не найден"}, 404)
            if order["status"] not in ("open", "accepted"):
                c.close()
                return self.send_json({"error": "Этот заказ уже нельзя отменить"}, 409)
            c.execute(
                "UPDATE orders SET status='cancelled',cancelled_at=?,updated_at=? WHERE id=?",
                (now_iso(), now_iso(), oid),
            )
            add_event(c, oid, uid, "cancelled", "Заказ отменён клиентом")
            target = order["executor_id"] or order["target_executor_id"]
            c.commit()
            c.close()
            notify_user(target, f"Заказ №{oid} отменён клиентом")
            return self.send_json({"ok": True})

        if path.startswith("/api/orders/") and path.endswith("/messages"):
            oid = int(path.strip("/").split("/")[2])
            order = c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
            if not order or not order_access(order, uid):
                c.close()
                return self.send_json({"error": "Нет доступа к чату"}, 403)
            if order["status"] in ("cancelled", "declined"):
                c.close()
                return self.send_json({"error": "Чат по закрытой заявке доступен только для чтения"}, 409)
            text = (data.get("text") or "").strip()
            if not text:
                c.close()
                return self.send_json({"error": "Сообщение пустое"}, 400)
            c.execute(
                "INSERT INTO messages(order_id,sender_id,type,text,created_at) VALUES(?,?,?,?,?)",
                (oid, uid, "text", text[:1500], now_iso()),
            )
            other = order["user_id"] if int(order["user_id"]) != uid else (order["executor_id"] or order["target_executor_id"])
            c.commit()
            c.close()
            notify_user(other, f"Новое сообщение по заказу №{oid}: {text[:120]}")
            return self.send_json({"ok": True}, 201)

        if path.startswith("/api/orders/") and path.endswith("/report"):
            oid = int(path.strip("/").split("/")[2])
            order = c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
            if not order or int(order["executor_id"] or 0) != uid:
                c.close()
                return self.send_json({"error": "Отчёт может добавить только назначенный исполнитель"}, 403)
            if order["status"] not in ("accepted", "in_progress"):
                c.close()
                return self.send_json({"error": "Для этого заказа отчёт уже нельзя изменить"}, 409)
            summary = (data.get("summary") or "").strip()
            if len(summary) < 8:
                c.close()
                return self.send_json({"error": "Напишите короткий итог услуги"}, 400)
            attachments = []
            for img in (data.get("images") or [])[:3]:
                try:
                    attachments.append(save_data_url(img, f"report-{oid}"))
                except ValueError as exc:
                    c.close()
                    return self.send_json({"error": str(exc)}, 400)
            old = report_for(c, oid)
            if old and not attachments:
                attachments = old.get("attachments") or []
            if int(order["item_id"] or 0) in REPORT_REQUIRED_SERVICES and not attachments:
                c.close()
                return self.send_json({"error": "Для этой услуги добавьте хотя бы одно фото"}, 400)
            distance = data.get("distance_km")
            try:
                distance = round(float(distance), 2) if distance not in (None, "") else None
            except Exception:
                distance = None
            c.execute(
                """INSERT INTO reports(order_id,executor_id,summary,distance_km,attachments_json,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?)
                   ON CONFLICT(order_id) DO UPDATE SET
                   summary=excluded.summary,distance_km=excluded.distance_km,
                   attachments_json=excluded.attachments_json,updated_at=excluded.updated_at""",
                (oid, uid, summary, distance, json.dumps(attachments), now_iso(), now_iso()),
            )
            add_event(c, oid, uid, "report", "Исполнитель добавил отчёт", add_chat=False)
            c.commit()
            c.close()
            return self.send_json({"ok": True})

        if path.startswith("/api/orders/") and path.endswith("/review"):
            oid = int(path.strip("/").split("/")[2])
            order = c.execute("SELECT * FROM orders WHERE id=? AND user_id=?", (oid, uid)).fetchone()
            if not order or order["status"] != "done" or not order["executor_id"]:
                c.close()
                return self.send_json({"error": "Отзыв можно оставить только после завершённой услуги"}, 409)
            try:
                rating = int(data.get("rating"))
            except Exception:
                rating = 0
            if rating < 1 or rating > 5:
                c.close()
                return self.send_json({"error": "Выберите оценку от 1 до 5"}, 400)
            try:
                c.execute(
                    "INSERT INTO reviews(order_id,client_id,executor_id,rating,text,created_at) VALUES(?,?,?,?,?,?)",
                    (oid, uid, order["executor_id"], rating, (data.get("text") or "").strip()[:800], now_iso()),
                )
            except Exception:
                c.close()
                return self.send_json({"error": "Отзыв по этому заказу уже оставлен"}, 409)
            c.execute("UPDATE orders SET client_reviewed=1 WHERE id=?", (oid,))
            add_event(c, oid, uid, "review", f"Клиент поставил оценку {rating}", add_chat=False)
            c.commit()
            c.close()
            notify_user(order["executor_id"], f"По заказу №{oid} оставили оценку {rating}/5")
            return self.send_json({"ok": True})

        if path.startswith("/api/pets/") and path.endswith("/photo"):
            pid = int(path.strip("/").split("/")[2])
            pet = c.execute("SELECT * FROM pets WHERE id=? AND user_id=?", (pid, uid)).fetchone()
            if not pet:
                c.close()
                return self.send_json({"error": "Питомец не найден"}, 404)
            try:
                url = save_data_url(data.get("data_url"), f"pet-{pid}")
            except ValueError as exc:
                c.close()
                return self.send_json({"error": str(exc)}, 400)
            c.execute("UPDATE pets SET photo_path=? WHERE id=?", (url, pid))
            c.commit()
            c.close()
            return self.send_json({"ok": True, "photo_url": url})

        if path == "/api/pets":
            name = (data.get("name") or "").strip()
            breed = (data.get("breed") or "").strip()
            if not name:
                c.close()
                return self.send_json({"error": "Введите имя"}, 400)
            cur = c.execute(
                "INSERT INTO pets(user_id,name,breed) VALUES(?,?,?)",
                (uid, name[:80], breed[:120]),
            )
            c.commit()
            pid = cur.lastrowid
            c.close()
            return self.send_json({"ok": True, "id": pid}, 201)

        if path == "/api/executor/availability":
            start_at = data.get("start_at") or ""
            end_at = data.get("end_at") or ""
            try:
                start = datetime.fromisoformat(start_at)
                end = datetime.fromisoformat(end_at)
            except Exception:
                c.close()
                return self.send_json({"error": "Укажите корректное время"}, 400)
            if end <= start:
                c.close()
                return self.send_json({"error": "Окончание должно быть позже начала"}, 400)
            if end - start > timedelta(days=7):
                c.close()
                return self.send_json({"error": "Нельзя блокировать больше 7 дней одним интервалом"}, 400)
            rows = c.execute(
                """SELECT * FROM orders WHERE executor_id=? AND status IN ('accepted','in_progress')
                   OR (target_executor_id=? AND status='open')""",
                (uid, uid),
            ).fetchall()
            for row in rows:
                a, b = order_range(row)
                if a and ranges_overlap(start, end, a, b):
                    c.close()
                    return self.send_json({"error": "На это время уже есть заявка или заказ"}, 409)
            cur = c.execute(
                "INSERT INTO availability(executor_id,start_at,end_at,note,created_at) VALUES(?,?,?,?,?)",
                (uid, start.isoformat(), end.isoformat(), (data.get("note") or "").strip()[:200], now_iso()),
            )
            c.commit()
            bid = cur.lastrowid
            c.close()
            return self.send_json({"ok": True, "id": bid}, 201)

        if path == "/api/executor/availability/delete":
            bid = int(data.get("id") or 0)
            cur = c.execute("DELETE FROM availability WHERE id=? AND executor_id=?", (bid, uid))
            c.commit()
            c.close()
            return self.send_json({"ok": bool(cur.rowcount)})

        if path.startswith("/api/executor/orders/"):
            parts = path.strip("/").split("/")
            oid = int(parts[3])
            action = parts[4] if len(parts) > 4 else ""
            order = c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
            if not order:
                c.close()
                return self.send_json({"error": "Заказ не найден"}, 404)

            if action == "accept":
                if order["status"] != "open":
                    c.close()
                    return self.send_json({"error": "Заявка уже недоступна"}, 409)
                if order["target_executor_id"] not in (None, uid):
                    c.close()
                    return self.send_json({"error": "Заявка адресована другому исполнителю"}, 403)
                if executor_conflict(c, uid, order["scheduled_date"], order["scheduled_time"], order["duration_min"], oid):
                    c.close()
                    return self.send_json({"error": "В расписании уже есть пересечение"}, 409)
                c.execute(
                    "UPDATE orders SET executor_id=?,status='accepted',accepted_at=?,updated_at=? WHERE id=?",
                    (uid, now_iso(), now_iso(), oid),
                )
                add_event(c, oid, uid, "accepted", "Исполнитель подтвердил заявку")
                c.commit()
                c.close()
                notify_user(order["user_id"], f"Исполнитель подтвердил заказ №{oid}")
                return self.send_json({"ok": True})

            if action == "reject":
                if order["status"] != "open" or int(order["target_executor_id"] or 0) != uid:
                    c.close()
                    return self.send_json({"error": "Эту заявку нельзя отклонить"}, 409)
                c.execute(
                    "UPDATE orders SET status='declined',updated_at=? WHERE id=?",
                    (now_iso(), oid),
                )
                add_event(c, oid, uid, "declined", "Исполнитель отклонил заявку")
                c.commit()
                c.close()
                notify_user(order["user_id"], f"Исполнитель отклонил заказ №{oid}. Выберите другого исполнителя.")
                return self.send_json({"ok": True})

            if action == "status":
                status = data.get("status")
                current = order["status"]
                allowed = {("accepted", "in_progress"), ("in_progress", "done")}
                if (current, status) not in allowed or int(order["executor_id"] or 0) != uid:
                    c.close()
                    return self.send_json({"error": "Недопустимый переход статуса"}, 409)
                if status == "done":
                    if int(order["item_id"] or 0) in REPORT_REQUIRED_SERVICES and not report_for(c, oid):
                        c.close()
                        return self.send_json({"error": "Перед завершением добавьте фотоотчёт"}, 409)
                    c.execute(
                        "UPDATE orders SET status='done',completed_at=?,updated_at=? WHERE id=?",
                        (now_iso(), now_iso(), oid),
                    )
                    debit_subscription_once(c, order)
                    add_event(c, oid, uid, "done", "Услуга завершена")
                else:
                    c.execute(
                        "UPDATE orders SET status='in_progress',started_at=?,updated_at=? WHERE id=?",
                        (now_iso(), now_iso(), oid),
                    )
                    add_event(c, oid, uid, "started", "Исполнитель начал услугу")
                c.commit()
                c.close()
                notify_user(order["user_id"], f"Статус заказа №{oid}: {'услуга завершена' if status == 'done' else 'услуга началась'}")
                return self.send_json({"ok": True})

        c.close()
        return super().do_POST()


if __name__ == "__main__":
    init_v14()
    threading.Thread(target=lambda: (time.sleep(1.2), base.configure_bot()), daemon=True).start()
    print("listening v14", base.PORT, "db", base.DB)
    base.ThreadingHTTPServer(("0.0.0.0", base.PORT), Handler).serve_forever()
