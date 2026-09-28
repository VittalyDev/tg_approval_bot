import json
import threading
import time
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

import app_v14 as v14

base = v14.base
SLOT_START_MIN = 8 * 60
SLOT_END_MIN = 22 * 60
SLOT_STEP_MIN = 30


def init_v15():
    v14.init_v14()
    c = base.conn()
    c.executescript("""
      CREATE INDEX IF NOT EXISTS idx_orders_executor_time
      ON orders(executor_id, target_executor_id, scheduled_date, scheduled_time, status);
      CREATE INDEX IF NOT EXISTS idx_availability_executor_time
      ON availability(executor_id, start_at, end_at);
      CREATE TABLE IF NOT EXISTS executor_applications(
        user_id INTEGER PRIMARY KEY,
        data_json TEXT NOT NULL DEFAULT '{}',
        status TEXT NOT NULL DEFAULT 'submitted',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );
    """)
    c.commit(); c.close()


_orig_serialize_order = v14.serialize_order


def serialize_order_v15(c, row, viewer_id, viewer_role):
    d = _orig_serialize_order(c, row, viewer_id, viewer_role)
    photo = ""
    if d.get("pet_id"):
        pet = c.execute("SELECT photo_path FROM pets WHERE id=?", (d["pet_id"],)).fetchone()
        if pet:
            photo = pet["photo_path"] or ""
    d["pet_photo_url"] = photo
    return d


v14.serialize_order = serialize_order_v15


def minute_to_time(value):
    return f"{value // 60:02d}:{value % 60:02d}"


def parse_order_id(path, suffix=None):
    parts = path.strip("/").split("/")
    if len(parts) < 3 or parts[:2] != ["api", "orders"]:
        return None
    if suffix and (len(parts) < 4 or parts[-1] != suffix):
        return None
    try:
        return int(parts[2])
    except Exception:
        return None


def executor_slot_reason(c, executor_id, date_str, time_str, duration, exclude_order_id=None):
    start = v14.parse_dt(date_str, time_str)
    if not start:
        return "Некорректное время"
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
        a, b = v14.order_range(row)
        if a and v14.ranges_overlap(start, end, a, b):
            return "У исполнителя уже есть заказ"
    for block in c.execute(
        "SELECT * FROM availability WHERE executor_id=?", (executor_id,)
    ).fetchall():
        try:
            a = datetime.fromisoformat(block["start_at"])
            b = datetime.fromisoformat(block["end_at"])
        except Exception:
            continue
        if v14.ranges_overlap(start, end, a, b):
            return block["note"] or "Исполнитель недоступен"
    return ""


def order_edit_payload(c, uid, order, data):
    date_str = (data.get("scheduled_date") or order["scheduled_date"] or "").strip()
    time_str = (data.get("scheduled_time") or order["scheduled_time"] or "").strip()
    start = v14.parse_dt(date_str, time_str)
    if not start:
        raise ValueError("Укажите дату и время")
    if start < datetime.now() - timedelta(minutes=1):
        raise ValueError("Выбранное время уже прошло")
    try:
        duration = int(data.get("duration_min") or order["duration_min"] or 60)
    except Exception:
        duration = int(order["duration_min"] or 60)
    duration = max(30, min(2880, duration))
    try:
        pet_id = int(data.get("pet_id", order["pet_id"]))
    except Exception:
        raise ValueError("Выберите питомца")
    pet = c.execute(
        "SELECT * FROM pets WHERE id=? AND user_id=?", (pet_id, uid)
    ).fetchone()
    if not pet:
        raise ValueError("Питомец не найден")
    item_id = int(order["item_id"])
    address = (
        (data.get("address") if "address" in data else order["address"]) or ""
    ).strip()
    if item_id != 5 and len(address) < 5:
        raise ValueError("Укажите адрес")
    notes = (
        (data.get("notes") if "notes" in data else order["notes"]) or ""
    ).strip()[:1200]
    target = order["executor_id"] or order["target_executor_id"]
    ep = None
    if target:
        ep = c.execute(
            "SELECT * FROM executor_profiles WHERE user_id=? AND active=1", (target,)
        ).fetchone()
        if not ep:
            raise ValueError("Исполнитель больше недоступен")
        reason = executor_slot_reason(
            c, int(target), date_str, time_str, duration, order["id"]
        )
        if reason:
            raise ValueError(reason)
    item = next((x for x in base.CATALOG if int(x["id"]) == item_id), None)
    executor_base = (
        max(int(ep["price"] or 0), int(item["price"]))
        if ep and item
        else int(order["price"] or 0)
    )
    price = v14.calc_price(item_id, duration, executor_base)
    changed = (
        date_str != (order["scheduled_date"] or "")
        or time_str != (order["scheduled_time"] or "")
        or duration != int(order["duration_min"] or 60)
    )
    return {
        "scheduled_date": date_str,
        "scheduled_time": time_str,
        "duration_min": duration,
        "pet_id": pet_id,
        "pet_name": pet["name"],
        "address": address,
        "notes": notes,
        "price": price,
        "schedule_changed": changed,
        "target_executor_id": target,
    }


class Handler(v14.Handler):
    def serve_file(self, path, cache=False):
        if Path(path).name == "index.html":
            text = Path(path).read_text(encoding="utf-8")
            for href in (
                "/assets/app-v13.css?v=13",
                "/assets/app-v14.css?v=14",
                "/assets/app-v15.css?v=15",
                "/assets/app-v16.css?v=16",
            ):
                if href not in text:
                    text = text.replace(
                        "</head>", f'<link rel="stylesheet" href="{href}">\n</head>'
                    )
            for src in (
                "/assets/app-v13.js?v=13",
                "/assets/app-v14.js?v=14",
                "/assets/app-v15.js?v=15",
                "/assets/app-v16.js?v=16",
            ):
                if src not in text:
                    text = text.replace(
                        "</body>", f'<script src="{src}"></script>\n</body>'
                    )
            return v14.serve_bytes(self, text.encode(), "text/html; charset=utf-8")
        return super().serve_file(path, cache=False)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        q = urllib.parse.parse_qs(parsed.query)
        if path == "/health":
            return self.send_json(
                {
                    "status": "ok",
                    "test_mode": base.TEST_MODE,
                    "ui": "premium-v20.2",
                    "persistent_db": str(base.DB).startswith("/data/"),
                }
            )
        if path == "/api/executor/application":
            user = self.require_user()
            if not user:
                return
            uid = int(user["id"])
            c = base.conn()
            row = c.execute(
                "SELECT data_json,status,created_at,updated_at FROM executor_applications WHERE user_id=?",
                (uid,),
            ).fetchone()
            c.close()
            if not row:
                return self.send_json({"data": {}, "status": "new"})
            try:
                data = json.loads(row["data_json"] or "{}")
            except Exception:
                data = {}
            return self.send_json({
                "data": data,
                "status": row["status"] or "submitted",
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            })

        if path.startswith("/api/executors/") and path.endswith("/slots"):
            user = self.require_user()
            if not user:
                return
            parts = path.strip("/").split("/")
            try:
                executor_id = int(parts[2])
            except Exception:
                return self.send_json({"error": "Исполнитель не найден"}, 404)
            date_str = (q.get("date") or [""])[0]
            try:
                duration = max(
                    30, min(2880, int((q.get("duration") or [60])[0]))
                )
            except Exception:
                duration = 60
            try:
                exclude_order_id = (
                    int((q.get("exclude_order_id") or [0])[0]) or None
                )
            except Exception:
                exclude_order_id = None
            try:
                datetime.fromisoformat(date_str)
            except Exception:
                return self.send_json({"error": "Укажите дату"}, 400)
            c = base.conn()
            if not c.execute(
                "SELECT 1 FROM executor_profiles WHERE user_id=? AND active=1",
                (executor_id,),
            ).fetchone():
                c.close()
                return self.send_json({"error": "Исполнитель недоступен"}, 404)
            slots = []
            for minute in range(SLOT_START_MIN, SLOT_END_MIN + 1, SLOT_STEP_MIN):
                t = minute_to_time(minute)
                reason = executor_slot_reason(
                    c,
                    executor_id,
                    date_str,
                    t,
                    duration,
                    exclude_order_id,
                )
                slots.append(
                    {"time": t, "available": not bool(reason), "reason": reason}
                )
            c.close()
            return self.send_json(
                {"date": date_str, "duration_min": duration, "slots": slots}
            )
        return super().do_GET()

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/executor/application":
            user = self.require_user()
            if not user:
                return
            uid = int(user["id"])
            data = self.read_json()

            if bool(data.get("_draft")):
                allowed = {
                    "full_name","age","primary_activity","city","preferred_areas","phone",
                    "telegram_username","social_url","self_employed_status","self_employed_help",
                    "services","animals","restrictions","experience_years","education","recent_courses",
                    "service_location","separate_room","simultaneous_pets","contract_ready","urgent_orders",
                    "anxious_experience","first_aid","emergency_response","reports_geo","work_days",
                    "work_hours","weekends","holidays","standards_agreement","cooperation_priorities",
                    "extra_info","own_pet","_last_step"
                }
                draft = {k: data.get(k) for k in allowed if k in data}
                payload = json.dumps(draft, ensure_ascii=False)
                if len(payload.encode("utf-8")) > 30000:
                    return self.send_json({"error": "Анкета слишком большая"}, 400)
                c = base.conn()
                row = c.execute(
                    "SELECT status,created_at FROM executor_applications WHERE user_id=?",
                    (uid,),
                ).fetchone()
                stamp = v14.now_iso()
                status = "submitted" if row and row["status"] == "submitted" else "draft"
                created = row["created_at"] if row and row["created_at"] else stamp
                c.execute(
                    """INSERT INTO executor_applications(user_id,data_json,status,created_at,updated_at)
                       VALUES(?,?,?,?,?)
                       ON CONFLICT(user_id) DO UPDATE SET
                         data_json=excluded.data_json,
                         status=excluded.status,
                         updated_at=excluded.updated_at""",
                    (uid, payload, status, created, stamp),
                )
                c.commit()
                c.close()
                return self.send_json({"ok": True, "status": status, "updated_at": stamp})

            def s(key, limit=500):
                return str(data.get(key) or "").strip()[:limit]

            full_name = s("full_name", 120)
            try:
                age = int(data.get("age") or 0)
            except Exception:
                age = 0
            primary_activity = s("primary_activity", 80)
            city = s("city", 80)
            preferred_areas = s("preferred_areas", 180)
            phone = s("phone", 30)
            telegram_username = s("telegram_username", 80)
            phone_digits = "".join(ch for ch in phone if ch.isdigit())

            services = data.get("services") or []
            valid_services = sorted({
                int(x) for x in services
                if str(x).isdigit() and 1 <= int(x) <= 8
            })
            work_days = [
                str(x) for x in (data.get("work_days") or [])
                if str(x) in ("Пн","Вт","Ср","Чт","Пт","Сб","Вс")
            ]
            try:
                experience_years = max(0.0, min(50.0, float(data.get("experience_years") or 0)))
            except Exception:
                experience_years = 0.0
            try:
                simultaneous_pets = max(1, min(20, int(data.get("simultaneous_pets") or 1)))
            except Exception:
                simultaneous_pets = 1

            if len(full_name) < 5:
                return self.send_json({"error": "Укажите ФИО"}, 400)
            if age < 18 or age > 80:
                return self.send_json({"error": "Укажите корректный возраст (18+)"}, 400)
            if not primary_activity:
                return self.send_json({"error": "Выберите основную деятельность"}, 400)
            if city not in v14.RUS_CITIES:
                return self.send_json({"error": "Выберите город из списка"}, 400)
            if len(preferred_areas) < 2:
                return self.send_json({"error": "Укажите районы работы"}, 400)
            if len(phone_digits) < 10:
                return self.send_json({"error": "Укажите контактный телефон"}, 400)
            if len(telegram_username) < 2:
                return self.send_json({"error": "Укажите Telegram"}, 400)
            if not valid_services:
                return self.send_json({"error": "Выберите хотя бы одну услугу"}, 400)
            if not s("animals", 220):
                return self.send_json({"error": "Укажите, с какими животными работаете"}, 400)
            if not s("service_location", 120):
                return self.send_json({"error": "Укажите формат оказания услуг"}, 400)
            if len(s("emergency_response", 700)) < 10:
                return self.send_json({"error": "Опишите действия в экстренной ситуации"}, 400)
            if not work_days or not s("work_hours", 120):
                return self.send_json({"error": "Заполните график работы"}, 400)
            if s("standards_agreement", 16) != "Да":
                return self.send_json({"error": "Для работы нужно согласиться соблюдать стандарты сервиса"}, 400)

            clean = {
                "full_name": full_name,
                "age": age,
                "primary_activity": primary_activity,
                "city": city,
                "preferred_areas": preferred_areas,
                "phone": phone,
                "telegram_username": telegram_username,
                "social_url": s("social_url", 300),
                "self_employed_status": s("self_employed_status", 40),
                "self_employed_help": s("self_employed_help", 16),
                "services": valid_services,
                "animals": s("animals", 220),
                "restrictions": s("restrictions", 500),
                "experience_years": experience_years,
                "education": s("education", 300),
                "recent_courses": s("recent_courses", 500),
                "service_location": s("service_location", 120),
                "separate_room": s("separate_room", 16),
                "simultaneous_pets": simultaneous_pets,
                "contract_ready": s("contract_ready", 16),
                "urgent_orders": s("urgent_orders", 16),
                "anxious_experience": s("anxious_experience", 16),
                "first_aid": s("first_aid", 16),
                "emergency_response": s("emergency_response", 700),
                "reports_geo": s("reports_geo", 16),
                "work_days": work_days,
                "work_hours": s("work_hours", 120),
                "weekends": s("weekends", 16),
                "holidays": s("holidays", 16),
                "standards_agreement": "Да",
                "cooperation_priorities": s("cooperation_priorities", 700),
                "extra_info": s("extra_info", 700),
                "own_pet": s("own_pet", 220),
            }

            c = base.conn()
            v14.upsert_executor(c, user)
            years_label = (
                "Без коммерческого опыта"
                if experience_years == 0
                else f"{experience_years:g} года опыта"
            )
            experience = f"{years_label} · {clean['animals']}"[:160]
            about_parts = [
                primary_activity,
                clean["cooperation_priorities"],
                clean["extra_info"],
            ]
            bio = " · ".join(x for x in about_parts if x)[:800]
            c.execute(
                """UPDATE executor_profiles SET
                   display_name=?,city=?,area=?,experience=?,bio=?,services_json=?,
                   active=1,onboarding_complete=1
                   WHERE user_id=?""",
                (
                    full_name, city, preferred_areas, experience, bio,
                    json.dumps(valid_services, ensure_ascii=False), uid,
                ),
            )
            stamp = v14.now_iso()
            c.execute(
                """INSERT INTO executor_applications(user_id,data_json,status,created_at,updated_at)
                   VALUES(?,?,?,?,?)
                   ON CONFLICT(user_id) DO UPDATE SET
                     data_json=excluded.data_json,
                     status=excluded.status,
                     updated_at=excluded.updated_at""",
                (
                    uid,
                    json.dumps(clean, ensure_ascii=False),
                    "submitted",
                    stamp,
                    stamp,
                ),
            )
            c.execute(
                "UPDATE users SET role='executor',executor_enabled=1,city=? WHERE id=?",
                (city, uid),
            )
            c.commit()
            c.close()
            return self.send_json({
                "ok": True,
                "role": "executor",
                "status": "submitted",
                "onboarding_complete": True,
            })

        if path.startswith("/api/orders/") and path.endswith("/edit"):
            user = self.require_user()
            if not user:
                return
            uid = int(user["id"])
            oid = parse_order_id(path, "edit")
            if not oid:
                return self.send_json({"error": "Заказ не найден"}, 404)
            data = self.read_json()
            c = base.conn()
            order = c.execute(
                "SELECT * FROM orders WHERE id=? AND user_id=?", (oid, uid)
            ).fetchone()
            if not order:
                c.close()
                return self.send_json({"error": "Заказ не найден"}, 404)
            if order["status"] not in ("open", "accepted"):
                c.close()
                return self.send_json(
                    {"error": "Этот заказ уже нельзя изменить"}, 409
                )
            try:
                p = order_edit_payload(c, uid, order, data)
            except ValueError as exc:
                c.close()
                return self.send_json({"error": str(exc)}, 409)
            old_status = order["status"]
            target = p["target_executor_id"]
            new_status = old_status
            executor_id = order["executor_id"]
            accepted_at = order["accepted_at"]
            event_text = "Клиент изменил параметры заказа"
            if old_status == "accepted" and p["schedule_changed"]:
                new_status = "open"
                executor_id = None
                accepted_at = None
                event_text = (
                    "Клиент изменил дату или время. "
                    "Исполнителю нужно подтвердить заказ заново"
                )
            c.execute(
                """UPDATE orders SET
                scheduled_date=?,scheduled_time=?,duration_min=?,pet_id=?,pet_name=?,
                address=?,notes=?,price=?,status=?,executor_id=?,target_executor_id=?,
                accepted_at=?,updated_at=? WHERE id=?""",
                (
                    p["scheduled_date"],
                    p["scheduled_time"],
                    p["duration_min"],
                    p["pet_id"],
                    p["pet_name"],
                    p["address"],
                    p["notes"],
                    p["price"],
                    new_status,
                    executor_id,
                    target,
                    accepted_at,
                    v14.now_iso(),
                    oid,
                ),
            )
            v14.add_event(c, oid, uid, "edited", event_text)
            c.commit()
            c.close()
            if target:
                v14.notify_user(
                    target,
                    f"Заказ №{oid} изменён: {p['scheduled_date']} {p['scheduled_time']}"
                    + (
                        " · требуется повторное подтверждение"
                        if new_status == "open"
                        else ""
                    ),
                )
            return self.send_json(
                {
                    "ok": True,
                    "id": oid,
                    "status": new_status,
                    "price": p["price"],
                    "requires_reconfirm": old_status == "accepted"
                    and p["schedule_changed"],
                }
            )
        return super().do_POST()


if __name__ == "__main__":
    init_v15()
    threading.Thread(
        target=lambda: (time.sleep(1.2), base.configure_bot()), daemon=True
    ).start()
    print("listening v20.2", base.PORT, "db", base.DB)
    base.ThreadingHTTPServer(("0.0.0.0", base.PORT), Handler).serve_forever()
