import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session, abort
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO

# --- 1. CORE CONFIGURATION ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY") 
ADMIN_PASSWORD = "PBE-Global-2026"
SUPERVISOR_PASSWORD = "PBE_Secure_2026"

app = Flask(__name__)
app.secret_key = "PBE_SUPREME_FINAL_STABLE_2026"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db(): return psycopg2.connect(DATABASE_URL)

PBE_GUILDS = ["ELECTRICAL ENGINEERING", "SOLAR & ENERGY", "PLUMBING & HYDRAULICS", "MASONRY & CONSTRUCTION", "MECHANICAL & AUTO", "PBE TV", "CCTV & SECURITY", "ICT & SOFTWARE", "HVAC & COOLING", "FASHION DESIGN", "GENERAL TECHNICAL"]
GH_REGIONS = ["Greater Accra", "Ashanti", "Western", "Central", "Eastern", "Volta", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Oti", "Western North"]

# --- 2. THE DOCTOR (SELF-HEALING SYSTEM) ---
def perform_self_heal():
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pbe_master_registry (
                id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT, gender TEXT, 
                pbe_uid TEXT UNIQUE, pbe_license TEXT UNIQUE, rank TEXT, department TEXT,
                phone_no TEXT UNIQUE, email TEXT UNIQUE, ghana_card TEXT UNIQUE, 
                photo_url TEXT, status TEXT DEFAULT 'PENDING', otp_code TEXT, 
                region TEXT, issuance_date DATE, expiry_date DATE
            );
            CREATE TABLE IF NOT EXISTS pbe_soul_audit (
                id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                action TEXT, actor TEXT, details TEXT, ip TEXT, device TEXT
            );
        """)
        conn.commit(); cur.close(); conn.close()
    except Exception as e: print(f"Heal Error: {e}")

with app.app_context(): perform_self_heal()

# --- 3. 15-CHAR HYBRID LOGIC ---
def gen_pbe_id(firstname):
    now = datetime.datetime.now()
    prefix = f"PBE{now.strftime('%y%m')}{firstname[:3].upper()}"
    return prefix + ''.join(random.choices(string.digits, k=15-len(prefix)))

def gen_pbe_lic(surname):
    prefix = f"PBELIC{surname[:3].upper()}"
    return prefix + ''.join(random.choices(string.digits, k=15-len(prefix)))

# --- 4. EXECUTIVE DESIGN (STANDALONE LOGO) ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>PBE Command Center</title>
    <style>
        :root { --pbe-grey: #414042; --pbe-gold: #f2a900; --bg: #f4f6f9; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background: var(--bg); margin: 0; padding-bottom: 80px; }
        .logo-section { text-align: center; padding: 25px; background: white; border-bottom: 2px solid #eee; }
        .logo-img { width: 90px; height: 90px; border-radius: 50%; border: 3px solid var(--pbe-gold); }
        .nav-header { background: var(--pbe-grey); color: white; padding: 15px; text-align: center; border-bottom: 4px solid var(--pbe-gold); font-weight: 900; }
        .container { max-width: 1300px; margin: auto; padding: 20px; }
        .layer-box { background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #ddd; }
        .layer-title { font-size: 11px; font-weight: 800; color: #555; text-transform: uppercase; margin-bottom: 15px; border-left: 5px solid var(--pbe-grey); padding-left: 10px; }
        .matrix-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
        .matrix-btn { background: #f8f9fa; border: 1px solid #ddd; border-radius: 8px; padding: 12px; text-align: center; font-size: 10px; font-weight: 700; text-decoration: none; color: #333; }
        .btn-6 { padding: 8px 12px; border-radius: 6px; color: white; text-decoration: none; font-size: 9px; font-weight: 800; margin: 2px; display: inline-block; border: none; }
        .bg-navy { background: #1e293b; } .bg-wa { background: #22c55e; } .bg-red { background: #ef4444; } .bg-gold { background: var(--pbe-gold); color: #000; }
        .fab-zone { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 12px; }
        .fab { width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; text-decoration: none; border: 2px solid var(--pbe-gold); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
    </style>
</head>
<body>
    <div class="logo-section"><img src="{{ url_for('static', filename='logo.png') }}" class="logo-img" onerror="this.src='https://via.placeholder.com/90?text=PBE'"></div>
    <div class="nav-header">PBE SUPREME COMMAND CENTER</div>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- 5. ROUTES ---

@app.route("/")
def home(): return redirect(url_for('admin_login'))

@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['role'] = 'ADMIN'
            return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="layer-box" style="max-width:380px; margin: 50px auto; text-align:center;"><form method="POST"><h3>SYSTEM LOCK</h3><input type="password" name="password" style="width:100%; padding:15px; border-radius:8px; border:1px solid #ddd;" placeholder="Master Key" required><button class="btn-6 bg-navy" style="width:100%; padding:15px; margin-top:10px;">AUTHENTICATE</button></form></div>'))

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('role'): return redirect(url_for('admin_login'))
    
    # Hybrid Balance Pull
    sms_bal = "Offline"
    try:
        r = requests.get("https://sms.arkesel.com/api/v2/clients/balance", headers={"api-key": ARKESEL_API_KEY}, timeout=3)
        if r.status_code == 200: sms_bal = f"{r.json()['data']['available_balance']} GHS"
    except: pass

    conn = get_db(); cur = conn.cursor()
    stats = {r: 0 for r in GH_REGIONS}
    for r in GH_REGIONS:
        cur.execute("SELECT COUNT(*) FROM pbe_master_registry WHERE region = %s", (r,))
        stats[r] = cur.fetchone()[0]

    cur.execute("SELECT * FROM pbe_master_registry WHERE surname IS NOT NULL ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <div style="display:flex; gap:10px; margin-bottom:15px;">
            <input type="text" id="gSearch" style="width:100%; padding:15px; border-radius:10px; border:1px solid #ddd;" placeholder="Search Personnel Registry...">
            <div style="background:white; padding:15px; border-radius:10px; border:1px solid #ddd; white-space:nowrap;">SMS: <b style="color:green;">{sms_bal}</b></div>
        </div>

        <div class="layer-box">
            <div class="layer-title">🌍 GHANA REGIONAL MATRIX</div>
            <div class="matrix-grid">
                {{% for reg, count in stats.items() %}}
                <div class="matrix-btn" style="text-align:left;">{{{{reg}}}}: <b style="color:red; float:right;">{{{{count}}}}</b></div>
                {{% endfor %}}
            </div>
        </div>

        <div class="layer-box">
            <div class="layer-title">👥 PERSONNEL REGISTRY</div>
            <table style="width:100%; border-collapse:collapse; font-size:11px;">
                <thead><tr style="background:#f1f1f1;"><th style="padding:10px; text-align:left;">ID</th><th style="text-align:left;">NAME</th><th style="text-align:left;">ACTIONS</th></tr></thead>
                <tbody>
                    {{% for w in workers %}}
                    <tr style="border-bottom:1px solid #eee;">
                        <td style="padding:12px;"><b>{{{{ w[5] }}}}</b></td>
                        <td>{{{{ w[1] }}}} {{{{ w[2] }}}}</td>
                        <td>
                            <a href="#" class="btn-6 bg-navy">PRINT</a>
                            <a href="https://wa.me/{{{{ w[9] }}}}" target="_blank" class="btn-6 bg-wa">WA</a>
                            <a href="#" class="btn-6 bg-red">DELETE</a>
                        </td>
                    </tr>
                    {{% endfor %}}
                </tbody>
            </table>
        </div>

        <div class="fab-zone">
            <a href="/admin/audit" class="fab" style="background:#414042; color:white;">📜</a>
            <a href="/admin/invite" class="fab" style="background:#333; color:var(--pbe-gold);">+</a>
        </div>
    """), guilds=PBE_GUILDS, stats=stats, workers=workers)

# --- INVITE & AUDIT LOGS ---
@app.route("/admin/audit")
def view_audit():
    if not session.get('role'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_soul_audit ORDER BY id DESC LIMIT 50")
    logs = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="layer-box">
            <div class="layer-title">🛡️ SYSTEM AUDIT LOGS</div>
            {% for l in logs %}
            <div style="padding:8px; border-bottom:1px solid #eee; font-size:11px;">
                [{{ l[1].strftime('%H:%M') }}] <b>{{ l[3] }}</b>: {{ l[4] }}
            </div>
            {% endfor %}
            <a href="/admin-dashboard" class="btn-6 bg-navy" style="width:100%; text-align:center; padding:15px; margin-top:15px;">BACK</a>
        </div>
    """), logs=logs)

# --- [ADD YOUR REGISTRATION FORM & INVITE ROUTES HERE] ---

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
