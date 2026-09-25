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
                    "ui": "premium-v19",
                    "persistent_db": str(base.DB).startswith("/data/"),
                }
            )
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
    print("listening v19", base.PORT, "db", base.DB)
    base.ThreadingHTTPServer(("0.0.0.0", base.PORT), Handler).serve_forever()
