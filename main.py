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
app.secret_key = "PBE_SUPREME_FORTIFIED_2026_FINAL"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db(): return psycopg2.connect(DATABASE_URL)

PBE_GUILDS = ["ELECTRICAL ENGINEERING", "SOLAR & ENERGY", "PLUMBING & HYDRAULICS", "MASONRY & CONSTRUCTION", "MECHANICAL & AUTO", "PBE TV", "CCTV & SECURITY", "ICT & SOFTWARE", "HVAC & COOLING", "FASHION DESIGN", "GENERAL TECHNICAL"]
GH_REGIONS = ["Greater Accra", "Ashanti", "Western", "Central", "Eastern", "Volta", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Oti", "Western North"]

# --- 2. SECURITY PROTOCOLS & SELF-HEALING ---
def perform_self_heal():
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

with app.app_context(): perform_self_heal()

def log_action(action, details, actor="SYSTEM"):
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_soul_audit (action, actor, details, ip, device) VALUES (%s, %s, %s, %s, %s)",
                (action, actor, details, request.remote_addr, f"{request.user_agent.platform}"))
    conn.commit(); cur.close(); conn.close()

# --- 3. 15-CHAR HYBRID LOGIC ---
def gen_id(name):
    now = datetime.datetime.now()
    prefix = f"PBE{now.strftime('%y%m')}{name[:3].upper()}"
    return prefix + ''.join(random.choices(string.digits, k=15-len(prefix)))

def gen_lic(name):
    prefix = f"PBELIC{name[:3].upper()}"
    return prefix + ''.join(random.choices(string.digits, k=15-len(prefix)))

# --- 4. UI ARCHITECTURE (THE STANDALONE LOGO & BUTTONS) ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>PBE Command Center</title>
    <style>
        :root { --pbe-grey: #414042; --pbe-gold: #f2a900; --bg: #f4f6f9; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background: var(--bg); margin: 0; }
        
        /* STANDALONE LOGO SECTION */
        .logo-header { padding: 30px; text-align: center; background: white; border-bottom: 2px solid #eee; }
        .pbe-logo { width: 90px; height: 90px; border-radius: 50%; border: 3px solid var(--pbe-gold); box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        
        .nav-header { background: var(--pbe-grey); color: white; padding: 15px; text-align: center; border-bottom: 4px solid var(--pbe-gold); }
        .container { max-width: 1300px; margin: auto; padding: 20px; }
        .layer-box { background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #ddd; }
        .layer-title { font-size: 11px; font-weight: 800; color: #555; text-transform: uppercase; margin-bottom: 15px; border-left: 5px solid var(--pbe-grey); padding-left: 10px; }
        .matrix-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
        .matrix-btn { background: #f8f9fa; border: 1px solid #ddd; border-radius: 8px; padding: 12px; text-align: center; text-decoration: none; color: #333; font-size: 10px; font-weight: 700; }
        .registry-table { width: 100%; border-collapse: collapse; font-size: 11px; }
        .registry-table th { background: #f1f1f1; padding: 12px; text-align: left; }
        .registry-table td { padding: 15px 12px; border-bottom: 1px solid #eee; }
        .btn-6 { padding: 8px 12px; border-radius: 6px; color: white; text-decoration: none; font-size: 9px; font-weight: 800; margin: 2px; display: inline-block; border: none; }
        .bg-navy { background: #1e293b; } .bg-wa { background: #22c55e; } .bg-red { background: #ef4444; } .bg-gold { background: var(--pbe-gold); color: #000; }
        
        /* FAB CONTROLS */
        .fab-group { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 10px; }
        .fab { width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; text-decoration: none; border: 2px solid var(--pbe-gold); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
        .fab-invite { background: #333; color: var(--pbe-gold); }
        .fab-logs { background: var(--pbe-grey); color: white; }
    </style>
</head>
<body>
    <div class="logo-header">
        <img src="{{ url_for('static', filename='logo.png') }}" class="pbe-logo" onerror="this.src='https://via.placeholder.com/90?text=PBE'">
    </div>
    <div class="nav-header">
        <div style="font-size: 18px; font-weight: 900; letter-spacing: 2px;">PBE COMMAND CENTER</div>
    </div>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- 5. CORE ROUTES ---

@app.route("/")
def index(): return redirect(url_for('admin_login'))

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('role'): return redirect(url_for('admin_login'))
    
    # Live Balance Pull
    sms_bal = "Offline"
    try:
        r = requests.get("https://sms.arkesel.com/api/v2/clients/balance", headers={"api-key": ARKESEL_API_KEY}, timeout=3)
        if r.status_code == 200: sms_bal = f"{r.json().get('data', {}).get('available_balance', '0.00')} GHS"
    except: pass

    conn = get_db(); cur = conn.cursor()
    reg_counts = {r: 0 for r in GH_REGIONS}
    for r in GH_REGIONS:
        cur.execute("SELECT COUNT(*) FROM pbe_master_registry WHERE region = %s", (r,))
        reg_counts[r] = cur.fetchone()[0]

    cur.execute("SELECT * FROM pbe_master_registry WHERE surname IS NOT NULL ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <div style="display:flex; gap:10px; margin-bottom:15px;">
            <input type="text" id="gSearch" style="width:100%; padding:15px; border-radius:10px; border:1px solid #ddd;" placeholder="Global Search...">
            <div style="background:white; padding:15px; border-radius:10px; border:1px solid #ddd; white-space:nowrap;">SMS: <b style="color:green;">{sms_bal}</b></div>
        </div>

        <div class="layer-box">
            <div class="layer-title">🌍 REGIONAL DISTRIBUTION</div>
            <div class="matrix-grid">
                {{% for reg, count in stats.items() %}}
                <div class="matrix-btn" style="text-align:left;">{{{{reg}}}}: <b style="color:red; float:right;">{{{{count}}}}</b></div>
                {{% endfor %}}
            </div>
        </div>

        <div class="layer-box">
            <div class="layer-title">🛠️ TECHNICAL GUILDS</div>
            <div class="matrix-grid">
                <a href="#" class="matrix-btn" style="background:#333; color:var(--pbe-gold);">ALL SECTORS</a>
                {{% for g in guilds %}}<a href="#" class="matrix-btn">{{{{g}}}}</a>{{% endfor %}}
            </div>
        </div>

        <div class="layer-box">
            <div class="layer-title">👥 PERSONNEL REGISTRY CONTROL</div>
            <table class="registry-table">
                <thead><tr><th>PBE-ID</th><th>NAME</th><th>RANK</th><th>ACTIONS (6)</th></tr></thead>
                <tbody>
                    {{% for w in workers %}}
                    <tr>
                        <td><b>{{{{ w[5] }}}}</b></td>
                        <td>{{{{ w[1] }}}} {{{{ w[2] }}}}</td>
                        <td>{{{{ w[7] }}}}</td>
                        <td>
                            <a href="#" class="btn-6 bg-navy">PRINT</a>
                            <a href="#" class="btn-6 bg-gold">RENEW</a>
                            <a href="#" class="btn-6" style="background:#6c757d;">SUSPEND</a>
                            <a href="https://wa.me/{{{{ w[9] }}}}" target="_blank" class="btn-6 bg-wa">WA</a>
                            <a href="#" class="btn-6 bg-navy">APPROVE</a>
                            <a href="#" class="btn-6 bg-red">DELETE</a>
                        </td>
                    </tr>
                    {{% endfor %}}
                </tbody>
            </table>
        </div>

        <div class="fab-group">
            <a href="/admin/audit" class="fab fab-logs" title="Audit Logs">📜</a>
            <a href="/admin/invite" class="fab fab-invite" title="Send Invite">+</a>
        </div>
    """), guilds=PBE_GUILDS, stats=reg_counts, workers=workers)

@app.route("/admin/audit")
def view_audit():
    if not session.get('role'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_soul_audit ORDER BY id DESC LIMIT 100")
    logs = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="layer-box">
            <div class="layer-title">🛡️ SYSTEM AUDIT LOGS</div>
            <div style="font-family:monospace; font-size:12px;">
                {% for l in logs %}
                <div style="padding:10px; border-bottom:1px solid #eee;">
                    [{{ l[1].strftime('%H:%M:%S') }}] <b>{{ l[3] }}</b>: {{ l[4] }} <br>
                    <small style="color:grey;">IP: {{ l[5] }} | Device: {{ l[6] }}</small>
                </div>
                {% endfor %}
            </div>
        </div>
        <a href="/admin-dashboard" class="btn-6 bg-navy" style="padding:15px; width:100%; text-align:center;">BACK TO COMMAND</a>
    """), logs=logs)

# [Include standard Login, Invite, and Register routes from previous builds]

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
