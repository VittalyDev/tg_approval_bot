import threading
import time

import app_v14 as app


def init_runtime():
    app.init_v14()
    c = app.base.conn()
    app.ensure_column(c, "orders", "client_reviewed", "INTEGER DEFAULT 0")
    c.commit()
    c.close()

    original_executor_rows = app.executor_rows

    def executor_rows_with_live_availability(c, service_id=None, city=None, requester_id=None):
        rows = original_executor_rows(c, service_id, city, requester_id)
        for row in rows:
            busy = c.execute(
                "SELECT COUNT(*) FROM orders WHERE executor_id=? AND status='in_progress'",
                (row["id"],),
            ).fetchone()[0]
            row["free"] = int(busy or 0) == 0
        return rows

    app.executor_rows = executor_rows_with_live_availability


if __name__ == "__main__":
    init_runtime()
    threading.Thread(target=lambda: (time.sleep(1.2), app.base.configure_bot()), daemon=True).start()
    print("listening v14.1", app.base.PORT, "db", app.base.DB)
    app.base.ThreadingHTTPServer(("0.0.0.0", app.base.PORT), app.Handler).serve_forever()
