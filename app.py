from flask import Flask, request, redirect, session, render_template_string, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from pathlib import Path
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.environ.get("CRM_SECRET_KEY", "GIJDUVON-TOZA-GILAM-PROFESSIONAL-SECRET-2026")
DB = Path(__file__).with_name("gijduvon_crm.db")

ROLES = {
    "admin": "Administrator",
    "operator": "Operator",
    "delivery": "Dostavchik",
    "washer": "Gilam yuvuvchi",
    "dryer": "Quritish xodimi",
    "packer": "Qadoqlash xodimi",
    "cashier": "Kassir",
}

STATUSES = [
    "Qabul qilindi", "Yuvilmoqda",
    "Qadoqlandi", "Yetkazishga tayyor", "Yetkazildi"
]


def connect_db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def ensure_column(con, table, column, declaration):
    columns = {row["name"] for row in con.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")


def init_db():
    with connect_db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'operator',
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            carpet_no TEXT UNIQUE NOT NULL,
            customer_id INTEGER NOT NULL,
            area REAL NOT NULL DEFAULT 0,
            price_per_m2 REAL NOT NULL DEFAULT 12000,
            total REAL NOT NULL DEFAULT 0,
            paid REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Qabul qilindi',
            delivery_user_id INTEGER,
            notes TEXT DEFAULT '',
            length_m REAL NOT NULL DEFAULT 0,
            width_m REAL NOT NULL DEFAULT 0,
            ko_rpacha_2m INTEGER NOT NULL DEFAULT 0,
            ko_rpacha_3m INTEGER NOT NULL DEFAULT 0,
            adyol_qty INTEGER NOT NULL DEFAULT 0,
            yostiq_qty INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(delivery_user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            carpet_no TEXT NOT NULL,
            customer_id INTEGER NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            sent_by INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(sent_by) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS delivery_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            notes TEXT DEFAULT '',
            created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(created_by) REFERENCES users(id)
        );
        """)
        ensure_column(con, "users", "active", "INTEGER NOT NULL DEFAULT 1")
        ensure_column(con, "customers", "notes", "TEXT DEFAULT ''")
        ensure_column(con, "orders", "delivery_user_id", "INTEGER")
        ensure_column(con, "orders", "notes", "TEXT DEFAULT ''")
        ensure_column(con, "orders", "length_m", "REAL NOT NULL DEFAULT 0")
        ensure_column(con, "orders", "width_m", "REAL NOT NULL DEFAULT 0")
        ensure_column(con, "orders", "ko_rpacha_2m", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(con, "orders", "ko_rpacha_3m", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(con, "orders", "adyol_qty", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(con, "orders", "yostiq_qty", "INTEGER NOT NULL DEFAULT 0")
        
        admin = con.execute("SELECT id FROM users WHERE username='admin'").fetchone()
        if not admin:
            con.execute(
                "INSERT INTO users(username,password_hash,role,active) VALUES(?,?,?,1)",
                ("admin", generate_password_hash("Admin123!"), "admin")
            )


init_db()


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    with connect_db() as con:
        return con.execute(
            "SELECT id, username, role, active FROM users WHERE id=?", (uid,)
        ).fetchone()


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or not user["active"]:
            session.clear()
            return redirect(url_for("home"))
        return fn(*args, **kwargs)
    return wrapper


def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            user = current_user()
            if user["role"] not in roles:
                return page(
                    "<div class='card'><h2>Ruxsat yo‘q</h2>"
                    "<p>Bu bo‘lim sizning lavozimingiz uchun yopiq.</p></div>",
                    title="Ruxsat yo‘q"
                ), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# YAGONA PROFESSIONAL DIZAYN (UI/UX)
BASE = """
<!doctype html><html lang="uz"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }} | G‘ijduvon Toza Gilam CRM</title>
<style>
:root {
  --primary: #064e3b;
  --primary-hover: #047857;
  --accent: #10b981;
  --bg-color: #f8fafc;
  --card-bg: #ffffff;
  --text-main: #0f172a;
  --text-muted: #64748b;
  --border-color: #e2e8f0;
}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg-color);color:var(--text-main);line-height:1.5}
header{background:var(--primary);color:#fff;padding:18px 28px;box-shadow:0 4px 20px rgba(0,0,0,0.08)}
header h2{margin:0 0 6px;font-size:22px;font-weight:700;letter-spacing:-0.5px}
header div{font-size:13px;color:#a7f3d0;text-transform:uppercase;letter-spacing:1px}
nav{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
nav a{color:#ecfdf5;text-decoration:none;background:rgba(255,255,255,0.12);padding:8px 14px;border-radius:8px;font-size:14px;font-weight:500;transition:all 0.2s ease}
nav a:hover{background:rgba(255,255,255,0.25);transform:translateY(-1px)}
main{max-width:1250px;margin:28px auto;padding:0 20px 50px}
.card{background:var(--card-bg);padding:24px;border-radius:16px;margin-bottom:20px;box-shadow:0 4px 6px -1px rgba(0,0,0,0.02),0 2px 4px -1px rgba(0,0,0,0.02);border:1px solid var(--border-color)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}
.stat{font-size:28px;font-weight:800;color:var(--primary-hover);margin-top:8px}
input,select,textarea,button{width:100%;padding:12px 16px;margin:6px 0 16px;border:1px solid var(--border-color);border-radius:10px;font-size:15px;background:#fff;outline:none;transition:all 0.2s}
input:focus,select:focus,textarea:focus{border-color:var(--accent);box-shadow:0 0 0 4px rgba(16,185,129,0.1)}
button,.btn{background:var(--accent);color:white;border:0;cursor:pointer;padding:12px 20px;border-radius:10px;font-weight:600;font-size:15px;text-decoration:none;display:inline-block;text-align:center;transition:all 0.2s}
button:hover,.btn:hover{background:var(--primary-hover);transform:translateY(-1px);box-shadow:0 4px 12px rgba(16,185,129,0.2)}
.btn.secondary{background:#64748b}.btn.secondary:hover{background:#475569;box-shadow:0 4px 12px rgba(100,116,139,0.2)}
.btn.sm{padding:6px 12px;font-size:13px;border-radius:8px}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:14px 12px;border-bottom:1px solid var(--border-color);vertical-align:middle}
th{background:#f8fafc;font-size:12px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.8px;font-weight:700}
tr:hover td{background:#fafafa}
.wrap{overflow-x:auto}.small{font-size:13px;color:var(--text-muted)}
.error{background:#fef2f2;color:#dc2626;padding:12px 16px;border-radius:10px;border:1px solid #fecaca;margin-bottom:16px;font-weight:500}
.success{background:#f0fdf4;color:#059669;padding:12px 16px;border-radius:10px;border:1px solid #bbf7d0;margin-bottom:16px;font-weight:500}
label{font-weight:600;font-size:13px;color:#334155;display:block;margin-bottom:4px}
.badge{display:inline-block;background:#ecfdf5;color:#047857;padding:6px 12px;border-radius:30px;font-size:12px;font-weight:600;border:1px solid #a7f3d0}
.calc-box{background:#f0fdf4;border:1px solid #bbf7d0;padding:20px;border-radius:12px;margin-bottom:20px}
.calc-title{font-weight:700;color:#166534;margin-bottom:10px;font-size:16px}
@media(max-width:768px){header{padding:14px 16px}main{margin:16px auto;padding:0 12px}.card{padding:16px}th,td{padding:10px 8px;font-size:13px}}
</style></head><body>
<header>
  <h2>G‘ijduvon Toza Gilam</h2>
  <div>Professional CRM &bull; {{ username or 'Kirish' }}</div>
  {% if username %}<nav>
    <a href="/">Bosh sahifa</a>
    {% if role in ['admin','operator'] %}<a href="/customers">Mijozlar</a><a href="/orders">Buyurtmalar</a>{% endif %}
    {% if role == 'admin' %}<a href="/employees">Xodimlar</a>{% endif %}
    {% if role in ['admin','delivery'] %}<a href="/delivery">Dostavchik paneli</a>{% endif %}
    {% if role == 'admin' %}<a href="/delivery-report">Dostavchik hisoboti</a>{% endif %}
    {% if role in ['admin','washer','dryer','packer'] %}<a href="/production">Ishlab chiqarish</a>{% endif %}
    {% if role in ['admin','cashier'] %}<a href="/finance">Moliya</a>{% endif %}
    <a href="/logout" style="background:rgba(239,68,68,0.2);color:#fca5a5;">Chiqish</a>
  </nav>{% endif %}
</header>
<main>{{ content|safe }}</main>
</body></html>
"""


def page(content, title="CRM", **context):
    inner = render_template_string(content, **context)
    user = current_user()
    return render_template_string(
        BASE, content=inner, title=title,
        username=user["username"] if user else None,
        role=user["role"] if user else None
    )


LOGIN = """
<div class="card" style="max-width:420px;margin:60px auto;padding:32px;">
  <h2 style="text-align:center;color:var(--primary);margin-bottom:24px;">Tizimga kirish</h2>
  {% if error %}<div class="error" style="text-align:center;">{{ error }}</div>{% endif %}
  <form method="post">
    <label>Login</label><input name="username" required autocomplete="username" placeholder="Loginingizni kiriting">
    <label>Parol</label><input type="password" name="password" required autocomplete="current-password" placeholder="Parolni kiriting">
    <button style="width:100%;margin-top:10px;">Kirish</button>
  </form>
  <p class="small" style="text-align:center;margin-top:20px;">Dastlabki administrator: <b>admin</b> / <b>Admin123!</b></p>
</div>
"""


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with connect_db() as con:
            user = con.execute(
                "SELECT * FROM users WHERE username=? AND active=1", (username,)
            ).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect("/")
        return page(LOGIN, title="Kirish", error="Login yoki parol noto‘g‘ri.")
    user = current_user()
    if not user:
        return page(LOGIN, title="Kirish", error=None)
    with connect_db() as con:
        stats = con.execute("""
            SELECT COUNT(*) orders_count,
                   COALESCE(SUM(total),0) total,
                   COALESCE(SUM(paid),0) paid,
                   SUM(CASE WHEN status='Yetkazishga tayyor' THEN 1 ELSE 0 END) ready
            FROM orders
        """).fetchone()
        cust_count = con.execute("SELECT COUNT(*) n FROM customers").fetchone()["n"]
        recent = con.execute("""
            SELECT o.carpet_no,c.name,o.total,o.status FROM orders o
            JOIN customers c ON c.id=o.customer_id ORDER BY o.id DESC LIMIT 10
        """).fetchall()
    content = """
    <div class="grid">
      <div class="card">Jami buyurtmalar<div class="stat">{{ s.orders_count or 0 }}</div></div>
      <div class="card">Mijozlar<div class="stat">{{ customers }}</div></div>
      <div class="card">Yetkazishga tayyor<div class="stat">{{ s.ready or 0 }}</div></div>
      <div class="card">Buyurtma summasi<div class="stat">{{ "%.0f"|format(s.total) }} so‘m</div></div>
      <div class="card">Qolgan qarz<div class="stat" style="color:#dc2626;">{{ "%.0f"|format(s.total-s.paid) }} so‘m</div></div>
    </div>
    <div class="card">
      <h3 style="margin-top:0;margin-bottom:16px;">So‘nggi buyurtmalar</h3>
      <div class="wrap"><table>
        <tr><th>Gilam №</th><th>Mijoz</th><th>Summa</th><th>Holat</th></tr>
        {% for o in recent %}
        <tr>
          <td><b>{{ o.carpet_no }}</b></td>
          <td>{{ o.name }}</td>
          <td>{{ "%.0f"|format(o.total) }} so‘m</td>
          <td><span class="badge">{{ o.status }}</span></td>
        </tr>
        {% else %}
        <tr><td colspan="4" style="text-align:center;color:var(--text-muted);">Hozircha buyurtma yo‘q.</td></tr>
        {% endfor %}
      </table></div>
    </div>
    """
    return page(content, title="Bosh sahifa", s=stats, customers=cust_count, recent=recent)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/customers", methods=["GET", "POST"])
@roles_required("admin", "operator")
def customers():
    error = None
    search = request.args.get("q", "").strip()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        notes = request.form.get("notes", "").strip()
        if not name or not phone:
            error = "Ism va telefon raqami majburiy."
        else:
            with connect_db() as con:
                con.execute(
                    "INSERT INTO customers(name,phone,address,notes) VALUES(?,?,?,?)",
                    (name, phone, address, notes)
                )
            return redirect("/customers")
    with connect_db() as con:
        if search:
            rows = con.execute("SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ? ORDER BY id DESC",
                               (f"%{search}%", f"%{search}%")).fetchall()
        else:
            rows = con.execute("SELECT * FROM customers ORDER BY id DESC LIMIT 100").fetchall()
    content = """
    <div class="card">
      <h2 style="margin-top:0;">Yangi mijoz qo‘shish</h2>
      {% if error %}<div class="error">{{ error }}</div>{% endif %}
      <form method="post">
        <label>Ism-familiya *</label><input name="name" placeholder="Masalan: Ali Valiyev" required>
        <label>Telefon *</label><input name="phone" type="tel" placeholder="+998901234567" required>
        <label>Manzil</label><input name="address" placeholder="Tuman, ko'cha, uy raqami">
        <label>Izoh</label><textarea name="notes" placeholder="Qo'shimcha ma'lumot..."></textarea>
        <button>Mijozni saqlash</button>
      </form>
    </div>
    
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;margin-bottom:16px;">
        <h2 style="margin:0;">Mijozlar ro‘yxati</h2>
        <form method="get" style="width:280px;margin:0;"><input name="q" value="{{ search }}" placeholder="Ism yoki tel bo'yicha qidirish..." style="margin:0;"></form>
      </div>
      <div class="wrap"><table>
        <tr><th>Ism</th><th>Telefon</th><th>Manzil</th><th>Izoh</th></tr>
        {% for c in rows %}
        <tr>
          <td><b>{{ c.name }}</b></td>
          <td><a href="tel:{{ c.phone }}" style="color:var(--primary);text-decoration:none;font-weight:600;">{{ c.phone }}</a></td>
          <td>{{ c.address }}</td>
          <td>{{ c.notes }}</td>
        </tr>
        {% else %}
        <tr><td colspan="4" style="text-align:center;color:var(--text-muted);">Mijozlar topilmadi.</td></tr>
        {% endfor %}
      </table></div>
    </div>
    """
    return page(content, title="Mijozlar", rows=rows, search=search, error=error)


@app.route("/orders", methods=["GET", "POST"])
@roles_required("admin", "operator")
def orders():
    error = None
    search = request.args.get("q", "").strip()
    if request.method == "POST":
        carpet_no = request.form.get("carpet_no", "").strip()
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        notes = request.form.get("notes", "").strip()
        try:
            area = float(request.form.get("area", "0"))
            price = float(request.form.get("price", "12000"))
            paid = float(request.form.get("paid", "0"))
            if not all([carpet_no, name, phone]) or area <= 0 or price < 0 or paid < 0:
                raise ValueError()
            total = area * price
            if paid > total:
                raise ValueError()
            with connect_db() as con:
                cur = con.execute(
                    "INSERT INTO customers(name,phone,address,notes) VALUES(?,?,?,?)",
                    (name, phone, address, notes)
                )
                con.execute("""
                    INSERT INTO orders(carpet_no,customer_id,area,price_per_m2,total,paid,notes)
                    VALUES(?,?,?,?,?,?,?)
                """, (carpet_no, cur.lastrowid, area, price, total, paid, notes))
            return redirect("/orders")
        except sqlite3.IntegrityError:
            error = "Gilam raqami takrorlangan. Boshqa raqam kiriting."
        except (ValueError, TypeError):
            error = "Maydon, narx va to‘lov qiymatlarini tekshiring."
    with connect_db() as con:
        if search:
            rows = con.execute("""
                SELECT o.*,c.name,c.phone FROM orders o JOIN customers c ON c.id=o.customer_id
                WHERE o.carpet_no LIKE ? OR c.name LIKE ? OR c.phone LIKE ?
                ORDER BY o.id DESC
            """, (f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
        else:
            rows = con.execute("""
                SELECT o.*,c.name,c.phone FROM orders o JOIN customers c ON c.id=o.customer_id
                ORDER BY o.id DESC LIMIT 100
            """).fetchall()
    content = """
    <div class="card">
      <h2 style="margin-top:0;">Buyurtma qo‘shish</h2>
      {% if error %}<div class="error">{{ error }}</div>{% endif %}
      <form method="post">
        <label>Gilam raqami *</label><input name="carpet_no" placeholder="GTG-0001" required>
        <label>Mijoz ismi *</label><input name="name" required>
        <label>Telefon *</label><input name="phone" type="tel" required>
        <label>Manzil</label><input name="address">
        <label>Maydon (m²) *</label><input type="number" name="area" min="0.1" step="0.1" required>
        <label>1 m² narxi (so'm)</label><input type="number" name="price" min="0" value="12000" required>
        <label>To‘langan summa (so'm)</label><input type="number" name="paid" min="0" value="0" required>
        <label>Izoh</label><textarea name="notes"></textarea>
        <button>Buyurtmani saqlash</button>
      </form>
    </div>
    
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;margin-bottom:16px;">
        <h2 style="margin:0;">Buyurtmalar</h2>
        <form method="get" style="width:280px;margin:0;"><input name="q" value="{{ search }}" placeholder="Gilam № yoki mijoz..." style="margin:0;"></form>
      </div>
      <div class="wrap"><table>
        <tr><th>Gilam №</th><th>Mijoz</th><th>Telefon</th><th>m²</th><th>Summa</th><th>Qarz</th><th>Holat</th><th>Chek</th></tr>
        {% for o in rows %}
        <tr>
          <td><b>{{ o.carpet_no }}</b></td>
          <td>{{ o.name }}</td>
          <td><a href="tel:{{ o.phone }}" style="color:var(--primary);text-decoration:none;">{{ o.phone }}</a></td>
          <td>{{ o.area }}</td>
          <td>{{ "%.0f"|format(o.total) }}</td>
          <td style="color:#dc2626;font-weight:600;">{{ "%.0f"|format(o.total-o.paid) }}</td>
          <td><span class="badge">{{ o.status }}</span></td>
          <td><a href="/receipt/{{ o.id }}" target="_blank" class="btn sm secondary">Chek</a></td>
        </tr>
        {% else %}
        <tr><td colspan="8" style="text-align:center;color:var(--text-muted);">Buyurtmalar topilmadi.</td></tr>
        {% endfor %}
      </table></div>
    </div>
    """
    return page(content, title="Buyurtmalar", rows=rows, search=search, error=error)


@app.route("/receipt/<int:order_id>")
@login_required
def receipt(order_id):
    with connect_db() as con:
        order = con.execute("""
            SELECT o.*, c.name, c.phone, c.address FROM orders o
            JOIN customers c ON c.id=o.customer_id WHERE o.id=?
        """, (order_id,)).fetchone()
    if not order:
        return "Buyurtma topilmadi", 404
    
    receipt_html = f"""
    <!doctype html><html><head><meta charset="utf-8">
    <title>Chek #{order['carpet_no']}</title>
    <style>
      body{{font-family:'Courier New',Courier,monospace;padding:15px;max-width:300px;margin:auto;background:#fff;color:#000}}
      h3,p{{text-align:center;margin:4px 0}}
      .line{{border-top:1px dashed #000;margin:10px 0}}
      .row{{display:flex;justify-content:space-between;margin:4px 0;font-size:13px}}
    </style></head><body onload="window.print()">
      <h3>G'IJDUVON TOZA GILAM</h3>
      <p>Tel: +998 90 123 45 67</p>
      <div class="line"></div>
      <p><b>Kvitansiya: #{order['carpet_no']}</b></p>
      <p style="font-size:11px;">Vaqt: {order['created_at']}</p>
      <div class="line"></div>
      <div class="row"><span>Mijoz:</span><span>{order['name']}</span></div>
      <div class="row"><span>Tel:</span><span>{order['phone']}</span></div>
      <div class="line"></div>
      <div class="row"><span>O'lcham:</span><span>{order['length_m']}m x {order['width_m']}m</span></div>
      <div class="row"><span>Maydon:</span><span>{order['area']} m²</span></div>
      <div class="row"><span>Ko'rpacha 2m:</span><span>{order['ko_rpacha_2m']} dona</span></div>
      <div class="row"><span>Ko'rpacha 3m:</span><span>{order['ko_rpacha_3m']} dona</span></div>
      <div class="row"><span>Adyol:</span><span>{order['adyol_qty']} dona</span></div>
      <div class="row"><span>Yostiq:</span><span>{order['yostiq_qty']} dona</span></div>
      <div class="line"></div>
      <div class="row"><b>Jami summa:</b><b>{order['total']:,.0f} so'm</b></div>
      <div class="row"><span>To'landi:</span><span>{order['paid']:,.0f} so'm</span></div>
      <div class="row"><b>Qarz:</b><b>{(order['total']-order['paid']):,.0f} so'm</b></div>
      <div class="line"></div>
      <p style="font-size:12px;">Xizmatimizdan foydalanganingiz uchun tashakkur!</p>
    </body></html>
    """
    return receipt_html


@app.route("/employees", methods=["GET", "POST"])
@roles_required("admin")
def employees():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "")
        if not username or len(password) < 8 or role not in ROLES or username == "admin":
            error = "Login kiriting, lavozim tanlang va kamida 8 belgili parol ishlating."
        else:
            try:
                with connect_db() as con:
                    con.execute(
                        "INSERT INTO users(username,password_hash,role,active) VALUES(?,?,?,1)",
                        (username, generate_password_hash(password), role)
                    )
                return redirect("/employees")
            except sqlite3.IntegrityError:
                error = "Bu login band."
    with connect_db() as con:
        rows = con.execute("SELECT id,username,role,active FROM users ORDER BY id").fetchall()
    content = """
    <div class="card">
      <h2 style="margin-top:0;">Xodim qo‘shish</h2>
      {% if error %}<div class="error">{{ error }}</div>{% endif %}
      <form method="post">
        <label>Login</label><input name="username" required placeholder="Xodim logini">
        <label>Vaqtinchalik parol (kamida 8 belgi)</label><input name="password" type="password" minlength="8" required placeholder="********">
        <label>Lavozim</label><select name="role">
          {% for key,label in roles.items() %}<option value="{{ key }}">{{ label }}</option>{% endfor %}
        </select>
        <button>Xodim yaratish</button>
      </form>
    </div>
    <div class="card">
      <h2 style="margin-top:0;">Xodimlar ro‘yxati</h2>
      <div class="wrap"><table>
        <tr><th>Login</th><th>Lavozim</th><th>Holat</th></tr>
        {% for u in rows %}
        <tr>
          <td><b>{{ u.username }}</b></td>
          <td>{{ roles.get(u.role,u.role) }}</td>
          <td><span class="badge" style="background:{{ '#ecfdf5' if u.active else '#fef2f2' }};color:{{ '#047857' if u.active else '#dc2626' }};">{{ 'Faol' if u.active else 'O‘chirilgan' }}</span></td>
        </tr>
        {% endfor %}
      </table></div>
    </div>
    """
    return page(content, title="Xodimlar", rows=rows, roles=ROLES, error=error)


@app.route("/delivery", methods=["GET", "POST"])
@roles_required("admin", "delivery")
def delivery():
    role = current_user()["role"]
    message = None
    error = None
    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "register":
            carpet_no = request.form.get("carpet_no", "").strip()
            name = request.form.get("name", "").strip()
            phone = request.form.get("phone", "").strip()
            address = request.form.get("address", "").strip()
            notes = request.form.get("notes", "").strip()
            if not all([carpet_no, name, phone]):
                error = "Gilam raqami, mijoz ismi va telefoni majburiy."
            else:
                try:
                    with connect_db() as con:
                        cur = con.execute(
                            "INSERT INTO customers(name,phone,address,notes) VALUES(?,?,?,?)",
                            (name, phone, address, notes)
                        )
                        order_cur = con.execute("""
                            INSERT INTO orders(carpet_no,customer_id,area,price_per_m2,total,paid,status,notes,delivery_user_id)
                            VALUES(?,?,0,12000,0,0,'Qabul qilindi',?,?)
                        """, (carpet_no, cur.lastrowid, notes, session["user_id"]))
                        con.execute("""
                            INSERT INTO delivery_events(order_id,customer_id,user_id,event_type)
                            VALUES(?,?,?,'picked_up')
                        """, (order_cur.lastrowid, cur.lastrowid, session["user_id"]))
                    return redirect(url_for("delivery", carpet_no=carpet_no, registered="1"))
                except sqlite3.IntegrityError:
                    error = "Bu gilam raqami avval ishlatilgan."

        elif action == "location":
            carpet_no = request.form.get("carpet_no", "").strip()
            try:
                lat = float(request.form.get("latitude", ""))
                lon = float(request.form.get("longitude", ""))
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    raise ValueError()
            except (ValueError, TypeError):
                lat = lon = None
                error = "GPS lokatsiya olinmadi."
            if not error:
                with connect_db() as con:
                    order = con.execute(
                        "SELECT customer_id FROM orders WHERE carpet_no=?", (carpet_no,)
                    ).fetchone()
                    if not order:
                        error = "Gilam raqami topilmadi."
                    else:
                        con.execute("""
                            INSERT INTO locations(carpet_no,customer_id,latitude,longitude,sent_by)
                            VALUES(?,?,?,?,?)
                        """, (carpet_no, order["customer_id"], lat, lon, session["user_id"]))
                        return redirect(url_for("delivery", carpet_no=carpet_no, location_sent="1"))

        elif action == "delivered":
            carpet_no = request.form.get("carpet_no", "").strip()
            with connect_db() as con:
                order = con.execute("""
                    SELECT id, customer_id, status FROM orders WHERE carpet_no=?
                """, (carpet_no,)).fetchone()
                if not order:
                    error = "Gilam raqami topilmadi."
                elif order["status"] == "Yetkazildi":
                    error = "Bu buyurtma allaqachon yetkazilgan."
                else:
                    con.execute("""
                        UPDATE orders SET status='Yetkazildi', delivery_user_id=?
                        WHERE id=?
                    """, (session["user_id"], order["id"]))
                    con.execute("""
                        INSERT INTO delivery_events(order_id,customer_id,user_id,event_type)
                        VALUES(?,?,?,'delivered')
                    """, (order["id"], order["customer_id"], session["user_id"]))
                    return redirect(url_for("delivery", carpet_no=carpet_no, delivered="1"))
        else:
            error = "Noma’lum amal."

    query = request.args.get("carpet_no", "").strip()
    with connect_db() as con:
        customer = None
        if query:
            customer = con.execute("""
                SELECT o.carpet_no,o.status,o.area,o.total,c.name,c.phone,c.address,c.notes
                FROM orders o JOIN customers c ON c.id=o.customer_id WHERE o.carpet_no=?
            """, (query,)).fetchone()
        locs = con.execute("""
            SELECT l.*,u.username,c.name,c.phone FROM locations l
            JOIN users u ON u.id=l.sent_by JOIN customers c ON c.id=l.customer_id
            ORDER BY l.id DESC LIMIT 50
        """).fetchall()

    if request.args.get("registered") == "1":
        message = "Mijoz va gilam ro‘yxatga olindi."
    elif request.args.get("location_sent") == "1":
        message = "Lokatsiya muvaffaqiyatli saqlandi."
    elif request.args.get("delivered") == "1":
        message = "Buyurtma yetkazildi deb belgilandi."

    content = """
    {% if role in ['delivery', 'admin'] %}
    <div class="card">
      <h2 style="margin-top:0;">Yangi mijoz va gilam qo‘shish</h2>
      {% if message %}<div class="success">{{ message }}</div>{% endif %}
      {% if error %}<div class="error">{{ error }}</div>{% endif %}
      <form method="post">
        <input type="hidden" name="action" value="register">
        <label>Gilam raqami *</label><input name="carpet_no" placeholder="GTG-0001" required>
        <label>Mijoz ism-familiyasi *</label><input name="name" required>
        <label>Telefon raqami *</label><input name="phone" type="tel" placeholder="+998901234567" required>
        <label>Uy manzili / mo‘ljal</label><input name="address">
        <label>Izoh</label><textarea name="notes"></textarea>
        <button>Mijoz va gilamni saqlash</button>
      </form>
    </div>
    {% endif %}

    <div class="card">
      <h2 style="margin-top:0;">Gilam raqami bilan qidirish</h2>
      <form method="get">
        <label>Gilam raqami</label>
        <input name="carpet_no" value="{{ query }}" placeholder="GTG-0001" required>
        <button>Mijozni qidirish</button>
      </form>
      {% if customer %}
      <div style="background:#f8fafc;padding:16px;border-radius:12px;margin-top:16px;border:1px solid var(--border-color);">
        <h3 style="margin-top:0;color:var(--primary);">Mijoz ma’lumotlari</h3>
        <p><b>Gilam raqami:</b> {{ customer.carpet_no }}</p>
        <p><b>Ism:</b> {{ customer.name }}</p>
        <p><b>Telefon:</b> <a href="tel:{{ customer.phone }}" style="color:var(--primary);text-decoration:none;">{{ customer.phone }}</a></p>
        <p><b>Manzil:</b> {{ customer.address }}</p>
        <p><b>Holat:</b> <span class="badge">{{ customer.status }}</span></p>
      </div>
      {% elif query %}<div class="error" style="margin-top:12px;">Gilam raqami topilmadi.</div>{% endif %}
    </div>

    {% if customer %}
    <div class="card">
      <h2 style="margin-top:0;">Yetkazish amallari</h2>
      {% if customer.status == 'Yetkazildi' %}
        <div class="success">Bu buyurtma allaqachon yetkazilgan.</div>
      {% else %}
        <form method="post" onsubmit="return confirm('Bu buyurtma mijozga yetkazildimi?');">
          <input type="hidden" name="action" value="delivered">
          <input type="hidden" name="carpet_no" value="{{ customer.carpet_no }}">
          <button style="background:#0284c7;">Yetkazildi deb belgilash</button>
        </form>
      {% endif %}
    </div>
    <div class="card">
      <h2 style="margin-top:0;">GPS lokatsiya yuborish</h2>
      <form method="post" id="gpsForm">
        <input type="hidden" name="action" value="location">
        <input type="hidden" name="carpet_no" value="{{ customer.carpet_no }}">
        <input type="hidden" name="latitude" id="lat"><input type="hidden" name="longitude" id="lon">
        <button type="button" onclick="sendGPS()" style="background:#ea580c;">GPS lokatsiyasini yuborish</button>
        <p id="gpsMessage" class="small" style="text-align:center;margin-top:8px;">Tugmani bosganda telefoningiz lokatsiyasi aniqlanadi.</p>
      </form>
    </div>
    <script>
    function sendGPS(){
      const msg=document.getElementById('gpsMessage');
      if(!navigator.geolocation){msg.textContent='Brauzer GPSni qo‘llamaydi.';return;}
      msg.textContent='Lokatsiya olinmoqda...';
      navigator.geolocation.getCurrentPosition(function(p){
        document.getElementById('lat').value=p.coords.latitude;
        document.getElementById('lon').value=p.coords.longitude;
        msg.textContent='Lokatsiya yuborilmoqda...';
        document.getElementById('gpsForm').submit();
      },function(e){msg.textContent='GPS xatosi: '+e.message;},
      {enableHighAccuracy:true,timeout:15000});
    }
    </script>
    {% endif %}

    <div class="card">
      <h2 style="margin-top:0;">Saqlangan lokatsiyalar</h2>
      <div class="wrap"><table>
        <tr><th>Gilam №</th><th>Mijoz</th><th>Dostavchik</th><th>Vaqt</th><th>Xarita</th></tr>
        {% for l in locs %}
        <tr>
          <td><b>{{ l.carpet_no }}</b></td>
          <td>{{ l.name }}<br><span class="small">{{ l.phone }}</span></td>
          <td>{{ l.username }}</td>
          <td>{{ l.created_at }}</td>
          <td><a target="_blank" rel="noopener" href="https://www.google.com/maps?q={{ l.latitude }},{{ l.longitude }}" class="btn sm secondary">Xaritada ochish</a></td>
        </tr>
        {% else %}
        <tr><td colspan="5" style="text-align:center;color:var(--text-muted);">Lokatsiyalar hali yuborilmagan.</td></tr>
        {% endfor %}
      </table></div>
    </div>
    """
    return page(content, title="Dostavchik paneli", role=role, query=query,
                customer=customer, locs=locs, message=message, error=error)


@app.route("/production", methods=["GET", "POST"])
@roles_required("admin", "washer", "dryer", "packer")
def production():
    role = current_user()["role"]
    error = None
    message = None

    if request.method == "POST":
        action = request.form.get("action", "status")
        carpet_no = request.form.get("carpet_no", "").strip()

        if action == "measure":
            if role not in ("admin", "washer"):
                return page("<div class='card'>Razmer va buyumlarni faqat yuvuvchi o‘zgartiradi.</div>"), 403
            try:
                length = float(request.form.get("length_m", "0") or 0)
                width = float(request.form.get("width_m", "0") or 0)
                k2 = int(request.form.get("ko_rpacha_2m", "0") or 0)
                k3 = int(request.form.get("ko_rpacha_3m", "0") or 0)
                adyol = int(request.form.get("adyol_qty", "0") or 0)
                yostiq = int(request.form.get("yostiq_qty", "0") or 0)
                paid = float(request.form.get("paid", "0") or 0)
                if length < 0 or width < 0 or min(k2, k3, adyol, yostiq, paid) < 0:
                    raise ValueError()
                if (length == 0) != (width == 0):
                    raise ValueError()
                area = round(length * width, 2)
                carpet_price = area * 12000
                total = carpet_price + k2 * 40000 + k3 * 50000 + adyol * 60000 + yostiq * 25000
                with connect_db() as con:
                    order = con.execute("SELECT id FROM orders WHERE carpet_no=?", (carpet_no,)).fetchone()
                    if not order:
                        error = "Gilam raqami topilmadi."
                    elif paid > total:
                        error = "To‘langan summa umumiy summadan katta bo‘lishi mumkin emas."
                    else:
                        con.execute("""
                            UPDATE orders SET length_m=?, width_m=?, area=?,
                                price_per_m2=12000, ko_rpacha_2m=?, ko_rpacha_3m=?,
                                adyol_qty=?, yostiq_qty=?, total=?, paid=?
                            WHERE carpet_no=?
                        """, (length, width, area, k2, k3, adyol, yostiq, total, paid, carpet_no))
                        message = f"Hisob saqlandi! Maydon: {area:.2f} m², Jami: {total:,.0f} so‘m."
            except (ValueError, TypeError):
                error = "Razmer va miqdorlarni to'g'ri kiriting."

        elif action == "status":
            status = request.form.get("status", "")
            allowed = {
                "admin": STATUSES,
                "washer": ["Yuvilmoqda"],
                "dryer": [],
                "packer": ["Qadoqlandi", "Yetkazishga tayyor"],
            }.get(role, [])
            if status not in allowed:
                error = "Bu holatni o‘zgartirishga ruxsatingiz yo‘q."
            else:
                with connect_db() as con:
                    cur = con.execute("UPDATE orders SET status=? WHERE carpet_no=?", (status, carpet_no))
                    if cur.rowcount == 0:
                        error = "Gilam raqami topilmadi."
                    else:
                        message = "Buyurtma holati yangilandi."
        else:
            error = "Noma’lum amal."

    with connect_db() as con:
        rows = con.execute("""
            SELECT o.id,o.carpet_no,o.status,o.area,o.length_m,o.width_m,o.total,o.paid,
                   o.ko_rpacha_2m,o.ko_rpacha_3m,o.adyol_qty,o.yostiq_qty,
                   c.name,c.phone
            FROM orders o JOIN customers c ON c.id=o.customer_id
            ORDER BY o.id DESC LIMIT 50
        """).fetchall()

    content = """
    <div class="card">
      <h2 style="margin-top:0;">Ishlab chiqarish paneli</h2>
      {% if message %}<div class="success">{{ message }}</div>{% endif %}
      {% if error %}<div class="error">{{ error }}</div>{% endif %}

      {% if role in ['admin', 'washer'] %}
      <form method="post" class="card" style="background:#f8fafc;border:1px solid var(--border-color);margin-top:16px;">
        <h3 style="margin-top:0;color:var(--primary);">Razmer va buyumlarni kiritish (Yuvuvchi)</h3>
        <input type="hidden" name="action" value="measure">
        <label>Gilam raqami *</label><input name="carpet_no" id="carpet_no" placeholder="GTG-0001" required>
        <div class="grid">
          <div><label>Uzunligi (m)</label><input type="number" step="0.01" name="length_m" id="len" min="0" placeholder="0" oninput="calcTotal()"></div>
          <div><label>Eni (m)</label><input type="number" step="0.01" name="width_m" id="wid" min="0" placeholder="0" oninput="calcTotal()"></div>
        </div>
        <div class="grid">
          <div><label>Ko‘rpacha (2m)</label><input type="number" name="ko_rpacha_2m" id="k2" min="0" value="0" oninput="calcTotal()"></div>
          <div><label>Ko‘rpacha (3m)</label><input type="number" name="ko_rpacha_3m" id="k3" min="0" value="0" oninput="calcTotal()"></div>
          <div><label>Adyol</label><input type="number" name="adyol_qty" id="adyol" min="0" value="0" oninput="calcTotal()"></div>
          <div><label>Yostiq</label><input type="number" name="yostiq_qty" id="yostiq" min="0" value="0" oninput="calcTotal()"></div>
        </div>
        <label>To‘langan summa (so‘m)</label><input type="number" name="paid" id="paid" min="0" value="0" oninput="calcTotal()">
        
        <div class="calc-box">
          <div class="calc-title">Avtomatik hisob-kitob:</div>
          <div>Maydon: <b><span id="res_area">0</span> m²</b> | Gilam summasi: <b><span id="res_carpet">0</span> so'm</b></div>
          <div>Qo'shimcha buyumlar: <b><span id="res_items">0</span> so'm</b></div>
          <div style="font-size:18px;margin-top:6px;color:#047857;">Jami summa: <b><span id="res_total">0</span> so'm</b></div>
          <div style="color:#dc2626;margin-top:4px;">Qolgan qarz: <b><span id="res_debt">0</span> so'm</b></div>
        </div>
        <button>Razmer va hisobni saqlash</button>
      </form>
      <script>
      function calcTotal(){
        const l = parseFloat(document.getElementById('len').value) || 0;
        const w = parseFloat(document.getElementById('wid').value) || 0;
        const k2 = parseInt(document.getElementById('k2').value) || 0;
        const k3 = parseInt(document.getElementById('k3').value) || 0;
        const adyol = parseInt(document.getElementById('adyol').value) || 0;
        const yostiq = parseInt(document.getElementById('yostiq').value) || 0;
        const paid = parseFloat(document.getElementById('paid').value) || 0;

        const area = Math.round((l * w) * 100) / 100;
        const carpetTotal = area * 12000;
        const itemsTotal = (k2 * 40000) + (k3 * 50000) + (adyol * 60000) + (yostiq * 25000);
        const grandTotal = carpetTotal + itemsTotal;
        const debt = grandTotal - paid;

        document.getElementById('res_area').innerText = area.toFixed(2);
        document.getElementById('res_carpet').innerText = carpetTotal.toLocaleString('uz-UZ');
        document.getElementById('res_items').innerText = itemsTotal.toLocaleString('uz-UZ');
        document.getElementById('res_total').innerText = grandTotal.toLocaleString('uz-UZ');
        document.getElementById('res_debt').innerText = (debt > 0 ? debt : 0).toLocaleString('uz-UZ');
      }
      </script>
      {% endif %}

      <form method="post" style="margin-top:20px;">
        <h3 style="margin-top:0;color:var(--primary);">Buyurtma holatini o‘zgartirish</h3>
        <input type="hidden" name="action" value="status">
        <label>Gilam raqami</label><input name="carpet_no" placeholder="GTG-0001" required>
        <label>Yangi holat</label><select name="status">
          {% for s in statuses %}<option value="{{ s }}">{{ s }}</option>{% endfor %}
        </select>
        <button style="background:#0284c7;">Holatni yangilash</button>
      </form>
    </div>

    <div class="card">
      <h2 style="margin-top:0;">Faol buyurtmalar</h2>
      <div class="wrap"><table>
        <tr><th>Gilam №</th><th>Mijoz</th><th>O‘lcham</th><th>Buyumlar</th><th>Summa</th><th>Holat</th><th>Chek</th></tr>
        {% for r in rows %}
        <tr>
          <td><b>{{ r.carpet_no }}</b></td>
          <td>{{ r.name }}<br><span class="small"><a href="tel:{{ r.phone }}" style="color:var(--primary);">{{ r.phone }}</a></span></td>
          <td>{{ r.length_m }}m × {{ r.width_m }}m<br><span class="small">({{ r.area }} m²)</span></td>
          <td class="small">K2: {{ r.ko_rpacha_2m }}, K3: {{ r.ko_rpacha_3m }}<br>Adyol: {{ r.adyol_qty }}, Yostiq: {{ r.yostiq_qty }}</td>
          <td><b>{{ "%.0f"|format(r.total) }}</b><br><span class="small">To‘landi: {{ "%.0f"|format(r.paid) }}</span></td>
          <td><span class="badge">{{ r.status }}</span></td>
          <td><a href="/receipt/{{ r.id }}" target="_blank" class="btn sm secondary">Chop etish</a></td>
        </tr>
        {% else %}
        <tr><td colspan="7" style="text-align:center;color:var(--text-muted);">Buyurtmalar yo‘q.</td></tr>
        {% endfor %}
      </table></div>
    </div>
    """
    return page(content, title="Ishlab chiqarish", role=role, statuses=STATUSES, rows=rows, message=message, error=error)


@app.route("/finance", methods=["GET", "POST"])
@roles_required("admin", "cashier")
def finance():
    error = None
    message = None
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        try:
            amount = float(request.form.get("amount", "0"))
            notes = request.form.get("notes", "").strip()
            if not title or amount <= 0:
                raise ValueError()
            with connect_db() as con:
                con.execute(
                    "INSERT INTO expenses(title,amount,notes,created_by) VALUES(?,?,?,?)",
                    (title, amount, notes, session["user_id"])
                )
            message = "Xarajat muvaffaqiyatli saqlandi."
        except (ValueError, TypeError):
            error = "Xarajat nomi va summasini to‘g‘ri kiriting."

    with connect_db() as con:
        sums = con.execute("SELECT COALESCE(SUM(total),0) t, COALESCE(SUM(paid),0) p FROM orders").fetchone()
        exp_sum = con.execute("SELECT COALESCE(SUM(amount),0) e FROM expenses").fetchone()["e"]
        expenses = con.execute("""
            SELECT e.*, u.username FROM expenses e
            LEFT JOIN users u ON u.id=e.created_by
            ORDER BY e.id DESC LIMIT 50
        """).fetchall()

    content = """
    <div class="grid">
      <div class="card">Jami tushum (Kirim)<div class="stat">{{ "%.0f"|format(sums.p) }} so‘m</div></div>
      <div class="card">Jami xarajat<div class="stat" style="color:#dc2626;">{{ "%.0f"|format(exp_sum) }} so‘m</div></div>
      <div class="card">Sof foyda<div class="stat">{{ "%.0f"|format(sums.p - exp_sum) }} so‘m</div></div>
    </div>

    <div class="card">
      <h2 style="margin-top:0;">Xarajat qo‘shish</h2>
      {% if message %}<div class="success">{{ message }}</div>{% endif %}
      {% if error %}<div class="error">{{ error }}</div>{% endif %}
      <form method="post">
        <label>Xarajat nomi (Suv, Elektr, Kimyo, Oylik va h.k.)</label><input name="title" required placeholder="Masalan: Ishchilar oyligi">
        <label>Summasi (so‘m)</label><input type="number" step="1000" name="amount" required placeholder="0">
        <label>Izoh</label><textarea name="notes" placeholder="Qo'shimcha izoh..."></textarea>
        <button style="background:#ea580c;">Xarajatni saqlash</button>
      </form>
    </div>

    <div class="card">
      <h2 style="margin-top:0;">Xarajatlar tarixi</h2>
      <div class="wrap"><table>
        <tr><th>Nomi</th><th>Summa</th><th>Izoh</th><th>Kiritdi</th><th>Vaqt</th></tr>
        {% for ex in expenses %}
        <tr>
          <td><b>{{ ex.title }}</b></td>
          <td style="color:#dc2626;font-weight:600;">{{ "%.0f"|format(ex.amount) }} so‘m</td>
          <td>{{ ex.notes }}</td>
          <td>{{ ex.username }}</td>
          <td>{{ ex.created_at }}</td>
        </tr>
        {% else %}
        <tr><td colspan="5" style="text-align:center;color:var(--text-muted);">Xarajatlar yo‘q.</td></tr>
        {% endfor %}
      </table></div>
    </div>
    """
    return page(content, title="Moliya", sums=sums, exp_sum=exp_sum, expenses=expenses, message=message, error=error)


@app.route("/delivery-report")
@roles_required("admin")
def delivery_report():
    with connect_db() as con:
        stats = con.execute("""
            SELECT u.username,
                   SUM(CASE WHEN de.event_type='picked_up' THEN 1 ELSE 0 END) picked,
                   SUM(CASE WHEN de.event_type='delivered' THEN 1 ELSE 0 END) delivered
            FROM users u
            LEFT JOIN delivery_events de ON de.user_id = u.id
            WHERE u.role = 'delivery'
            GROUP BY u.id
        """).fetchall()
        events = con.execute("""
            SELECT de.*, u.username, c.name, c.phone, o.carpet_no FROM delivery_events de
            JOIN users u ON u.id=de.user_id
            JOIN customers c ON c.id=de.customer_id
            JOIN orders o ON o.id=de.order_id
            ORDER BY de.id DESC LIMIT 50
        """).fetchall()

    content = """
    <div class="card">
      <h2 style="margin-top:0;">Dostavchiklar statistikasi</h2>
      <div class="wrap"><table>
        <tr><th>Dostavchik</th><th>Olingan gilamlar</th><th>Yetkazilgan gilamlar</th></tr>
        {% for s in stats %}
        <tr><td><b>{{ s.username }}</b></td><td>{{ s.picked or 0 }} dona</td><td>{{ s.delivered or 0 }} dona</td></tr>
        {% else %}
        <tr><td colspan="3" style="text-align:center;color:var(--text-muted);">Dostavchiklar mavjud emas.</td></tr>
        {% endfor %}
      </table></div>
    </div>

    <div class="card">
      <h2 style="margin-top:0;">So'nggi harakatlar jurnali (Log)</h2>
      <div class="wrap"><table>
        <tr><th>Vaqt</th><th>Dostavchik</th><th>Gilam №</th><th>Mijoz</th><th>Harakat</th></tr>
        {% for ev in events %}
        <tr>
          <td>{{ ev.created_at }}</td>
          <td>{{ ev.username }}</td>
          <td><b>{{ ev.carpet_no }}</b></td>
          <td>{{ ev.name }} ({{ ev.phone }})</td>
          <td><span class="badge">{{ 'Olib ketildi' if ev.event_type=='picked_up' else 'Yetkazildi' }}</span></td>
        </tr>
        {% else %}
        <tr><td colspan="5" style="text-align:center;color:var(--text-muted);">Voqealar yo‘q.</td></tr>
        {% endfor %}
      </table></div>
    </div>
    """
    return page(content, title="Dostavchik hisoboti", stats=stats, events=events)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
