import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime, time
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session, abort
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from io import BytesIO

# --- 1. CORE CONFIGURATION ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY") 
ADMIN_PASSWORD = "PBE-Global-2026"

app = Flask(__name__)
app.secret_key = "PBE_SUPREME_FRESH_START_2026"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    for i in range(5):
        try: return psycopg2.connect(DATABASE_URL)
        except: time.sleep(2)
    return None

# --- 2. FRESH PAGE RESET (THE DOCTOR) ---
def init_fresh_system():
    conn = get_db()
    if not conn: return
    cur = conn.cursor()
    # CEO REQUEST: Reset everything to clear old phone numbers/errors
    cur.execute("DROP TABLE IF EXISTS pbe_master_registry CASCADE;")
    cur.execute("DROP TABLE IF EXISTS pbe_soul_audit CASCADE;")
    cur.execute("""
        CREATE TABLE pbe_master_registry (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT, gender TEXT, 
            pbe_uid TEXT UNIQUE, pbe_license TEXT UNIQUE, rank TEXT, department TEXT,
            phone_no TEXT UNIQUE, email TEXT UNIQUE, ghana_card TEXT UNIQUE, 
            photo_url TEXT, status TEXT DEFAULT 'PENDING', otp_code TEXT, 
            region TEXT, issuance_date DATE, expiry_date DATE
        );
        CREATE TABLE pbe_soul_audit (
            id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            action TEXT, actor TEXT, details TEXT, ip TEXT, device TEXT
        );
    """)
    conn.commit(); cur.close(); conn.close()

with app.app_context(): init_fresh_system()

# --- 3. PBE WORLD MATRIX ---
PBE_GUILDS = ["ELECTRICAL ENGINEERING", "SOLAR & ENERGY", "PLUMBING & HYDRAULICS", "MASONRY & CONSTRUCTION", "MECHANICAL & AUTO", "PBE TV", "CCTV & SECURITY", "ICT & SOFTWARE", "HVAC & COOLING", "FASHION DESIGN", "ETC / GENERAL"]
GH_REGIONS = ["Greater Accra", "Ashanti", "Western", "Central", "Eastern", "Volta", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Oti", "Western North"]

# --- 4. ROBOT MAPPING LOGIC ---
def gen_pbe_uid(name):
    now = datetime.datetime.now()
    return f"PBE{now.strftime('%y%m')}{name[:3].upper()}{''.join(random.choices(string.digits, k=4))}"

# --- 5. EXECUTIVE UI ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>PBE Command Center</title>
    <style>
        :root { --pbe-grey: #414042; --pbe-gold: #f2a900; --bg: #f4f6f9; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; padding-bottom: 120px; }
        .logo-standalone { text-align: center; padding: 30px; background: white; border-bottom: 2px solid #eee; }
        .logo-img { width: 100px; height: 100px; border-radius: 50%; border: 3px solid var(--pbe-gold); }
        .nav-bar { background: var(--pbe-grey); color: white; padding: 15px; text-align: center; border-bottom: 4px solid var(--pbe-gold); font-weight: 900; letter-spacing: 2px; }
        .container { max-width: 1300px; margin: auto; padding: 20px; }
        .layer-box { background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #ddd; }
        .matrix-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
        .matrix-item { background: #f8f9fa; border: 1px solid #ddd; border-radius: 8px; padding: 12px; text-align: center; font-size: 10px; font-weight: 700; color: #333; text-decoration: none; }
        .btn-6 { padding: 8px 12px; border-radius: 6px; color: white; text-decoration: none; font-size: 9px; font-weight: 800; margin: 2px; display: inline-block; border: none; }
        .bg-navy { background: #1e293b; } .bg-wa { background: #22c55e; } .bg-red { background: #ef4444; } .bg-gold { background: var(--pbe-gold); color: #000; }
        .fab-zone { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 12px; z-index: 1000; }
        .fab { width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; text-decoration: none; border: 2px solid var(--pbe-gold); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
        .fab-invite { background: #333; color: var(--pbe-gold); }
        .fab-audit { background: var(--pbe-grey); color: white; }
        .fab-alert { background: #ff4d4d; color: white; }
    </style>
</head>
<body>
    <div class="logo-standalone"><img src="{{ url_for('static', filename='logo.png') }}" class="logo-img" onerror="this.src='https://via.placeholder.com/100?text=PBE'"></div>
    <div class="nav-bar">PBE SUPREME COMMAND CENTER</div>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- 6. ALL ACTIVE ROUTES (FIXED NOT FOUND ERRORS) ---

@app.route("/")
def home(): return redirect(url_for('admin_login'))

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('role'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM pbe_master_registry WHERE expiry_date <= CURRENT_DATE + INTERVAL '30 days'")
    expiry_alerts = cur.fetchone()[0]
    stats = {r: 0 for r in GH_REGIONS}
    for r in GH_REGIONS:
        cur.execute("SELECT COUNT(*) FROM pbe_master_registry WHERE region = %s", (r,))
        stats[r] = cur.fetchone()[0]
    cur.execute("SELECT * FROM pbe_master_registry WHERE surname IS NOT NULL ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <div class="layer-box">
            <div class="layer-title">🌍 REGIONAL MATRIX</div>
            <div class="matrix-grid">
                {{% for reg, count in stats.items() %}}
                <div class="matrix-item" style="text-align:left;">{{{{reg}}}}: <b style="color:red; float:right;">{{{{count}}}}</b></div>
                {{% endfor %}}
            </div>
        </div>
        <div class="layer-box">
            <div class="layer-title">🛠️ TECHNICAL GUILDS</div>
            <div class="matrix-grid">
                {{% for g in guilds %}}<a href="#" class="matrix-item">{{{{g}}}}</a>{{% endfor %}}
            </div>
        </div>
        <div class="fab-zone">
            <a href="/admin/alerts" class="fab fab-alert" title="Renewal Alerts">🔔 {{{{alerts}}}}</a>
            <a href="/admin/audit" class="fab fab-audit" title="Soul Audit">📜</a>
            <a href="/admin/invite" class="fab fab-invite" title="Invite">+</a>
        </div>
    """), guilds=PBE_GUILDS, stats=stats, workers=workers, alerts=expiry_alerts)

@app.route("/admin/audit")
def view_audit():
    if not session.get('role'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT * FROM pbe_soul_audit ORDER BY id DESC LIMIT 50")
    logs = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="layer-box"><h3>📜 SOUL AUDIT LOGS</h3>
        {% for l in logs %}<div>[{{ l[1] }}] {{ l[3] }}: {{ l[4] }}</div>{% endfor %}
        <a href="/admin-dashboard" class="btn-6 bg-navy">BACK</a></div>
    """), logs=logs)

@app.route("/admin/alerts")
def view_alerts():
    if not session.get('role'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_master_registry WHERE expiry_date <= CURRENT_DATE + INTERVAL '30 days'")
    alerts = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="layer-box"><h3>🔔 RENEWAL ALERTS (2-YEAR EXPIRY)</h3>
        {% for a in alerts %}<div>{{ a[1] }} {{ a[2] }} - Expires: {{ a[17] }}</div>{% endfor %}
        <a href="/admin-dashboard" class="btn-6 bg-navy">BACK</a></div>
    """), alerts=alerts)

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if request.method == 'POST':
        otp = str(random.randint(111111, 999999))
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO pbe_master_registry (phone_no, otp_code) VALUES (%s, %s)", (request.form.get('phone'), otp))
        conn.commit(); cur.close(); conn.close()
        requests.post("https://sms.arkesel.com/api/v2/sms/send", 
                     json={"sender": "PBE_OTP", "message": f"PBE: Use OTP {otp} to register here: {request.url_root}register", "recipients": [request.form.get('phone')]}, 
                     headers={"api-key": ARKESEL_API_KEY})
        return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="layer-box"><h3>+ SEND INVITE</h3>
        <form method="POST"><input name="phone" placeholder="233..." required><button class="btn-6 bg-navy">SEND OTP</button></form></div>
    """))

@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['role'] = 'ADMIN'
            return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="layer-box" style="max-width:400px; margin:auto; text-align:center;">
        <h3>SYSTEM LOCK</h3><form method="POST"><input type="password" name="password" required>
        <button class="btn-6 bg-navy">UNLOCK</button></form></div>
    """))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
