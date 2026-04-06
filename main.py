import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime, csv, json
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
ARKESEL_SENDER_ID = "PBE_OTP" 
ADMIN_PASSWORD = "PBE-Global-2026"
SUPERVISOR_PASSWORD = "PBE_Secure_2026"

app = Flask(__name__)
app.secret_key = "PBE_SUPREME_ULTIMATE_2026_V2"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

PBE_GUILDS = ["ELECTRICAL ENGINEERING", "SOLAR & ENERGY", "PLUMBING & HYDRAULICS", "MASONRY & CONSTRUCTION", "MECHANICAL & AUTO", "MEDIA TEAM (DDS)", "CCTV & SECURITY", "ICT & SOFTWARE", "HVAC & COOLING", "FASHION DESIGN", "GENERAL TECHNICAL"]

GH_REGIONS = ["Greater Accra", "Ashanti", "Western", "Central", "Eastern", "Volta", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Oti", "Western North"]

# --- 2. SELF-HEALING & RESET PROTOCOL ---
def init_and_heal_db(reset=False):
    conn = get_db(); cur = conn.cursor()
    if reset:
        cur.execute("DROP TABLE IF EXISTS pbe_master_registry CASCADE;")
        cur.execute("DROP TABLE IF EXISTS pbe_soul_audit CASCADE;")
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_master_registry (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT, gender TEXT, 
            pbe_uid TEXT UNIQUE, pbe_license TEXT UNIQUE, rank TEXT, department TEXT,
            phone_no TEXT UNIQUE, email TEXT UNIQUE, ghana_card TEXT UNIQUE, 
            photo_url TEXT, status TEXT DEFAULT 'PENDING', otp_code TEXT, 
            region TEXT, issuance_date DATE, expiry_date DATE
        );
    """)
    cur.execute("CREATE TABLE IF NOT EXISTS pbe_soul_audit (id SERIAL PRIMARY KEY);")
    # Healing missing columns
    cols = {"timestamp": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "action": "TEXT", "actor": "TEXT", "details": "TEXT", "ip": "TEXT", "device": "TEXT"}
    for col, defn in cols.items():
        cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='pbe_soul_audit' AND column_name='{col}';")
        if not cur.fetchone(): cur.execute(f"ALTER TABLE pbe_soul_audit ADD COLUMN {col} {defn};")
    conn.commit(); cur.close(); conn.close()

# CRITICAL: SET TO TRUE ONCE TO DELETE AND START NEW, THEN SET TO FALSE
with app.app_context():
    init_and_heal_db(reset=True) 

def log_action(action, details, actor="SYSTEM"):
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_soul_audit (action, actor, details, ip, device) VALUES (%s, %s, %s, %s, %s)",
                (action, actor, details, request.remote_addr, f"{request.user_agent.platform}"))
    conn.commit(); cur.close(); conn.close()

# --- 3. PBE 15-CHAR HYBRID LOGIC ---
def generate_pbe_id(firstname):
    now = datetime.datetime.now()
    prefix = f"PBE{now.strftime('%y%m')}" # PBE + YY + MM
    name_part = re.sub(r'[^A-Z]', '', firstname.upper())[:3] # First 3 letters
    needed = 15 - len(prefix) - len(name_part)
    nums = ''.join(random.choices(string.digits, k=needed))
    return f"{prefix}{name_part}{nums}"

def generate_pbe_lic(surname):
    prefix = "PBELIC" # 6 chars
    name_part = re.sub(r'[^A-Z]', '', surname.upper())[:3] # 3 letters
    needed = 15 - len(prefix) - len(name_part)
    nums = ''.join(random.choices(string.digits, k=needed))
    return f"{prefix}{name_part}{nums}"

# --- 4. UI DESIGN ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>PBE Supreme Command</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root { --pbe-grey: #414042; --pbe-gold: #f2a900; --bg: #e9eaec; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background: var(--bg); margin: 0; padding-bottom: 50px; }
        .header { background: var(--pbe-grey); color: white; padding: 30px; text-align: center; border-bottom: 5px solid var(--pbe-gold); }
        .logo-box { width: 75px; height: 75px; background: white; border-radius: 50%; margin: 0 auto 10px; border: 2px solid var(--pbe-gold); display: flex; align-items: center; justify-content: center; overflow: hidden; }
        .logo-box img { max-width: 100%; height: auto; }
        .container { max-width: 1350px; margin: auto; padding: 20px; }
        .layer-box { background: white; border-radius: 12px; padding: 20px; margin-bottom: 25px; border: 1px solid #d1d1d1; }
        .layer-title { font-size: 11px; font-weight: 800; color: #555; text-transform: uppercase; margin-bottom: 15px; border-left: 5px solid var(--pbe-grey); padding-left: 10px; }
        .matrix-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
        .matrix-item { background: #f8f9fa; border: 1px solid #ddd; border-radius: 8px; padding: 12px; text-align: center; font-size: 10px; font-weight: 700; text-decoration: none; color: #333; }
        .active-layer { background: #333 !important; color: var(--pbe-gold) !important; border-color: var(--pbe-gold) !important; }
        .registry-table { width: 100%; border-collapse: collapse; font-size: 12px; }
        .registry-table th { background: #f1f1f1; padding: 12px; text-align: left; text-transform: uppercase; border-bottom: 2px solid #ddd; }
        .registry-table td { padding: 15px 12px; border-bottom: 1px solid #eee; }
        .btn-6 { padding: 8px 12px; border-radius: 6px; color: white; text-decoration: none; font-size: 10px; font-weight: 800; margin: 2px; border: none; cursor: pointer; }
        .bg-navy { background: #1e293b; } .bg-wa { background: #22c55e; } .bg-red { background: #ef4444; } .bg-sus { background: #64748b; } .bg-gold { background: var(--pbe-gold); color: #000; }
        .audit-scroll { height: 160px; overflow-y: auto; background: #fff; padding: 15px; border-radius: 10px; font-family: monospace; font-size: 12px; border: 1px solid #ddd; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo-box"><img src="{{ url_for('static', filename='logo.png') }}" onerror="this.parentElement.style.display='none'"></div>
        <div style="font-size: 22px; font-weight: 900; letter-spacing: 2px;">PBE COMMAND CENTER</div>
    </div>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- 5. DASHBOARD ROUTE ---
@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('role'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor()
    
    # Regional Distribution Healing logic
    reg_counts = {}
    for r in GH_REGIONS:
        cur.execute("SELECT COUNT(*) FROM pbe_master_registry WHERE region = %s", (r,))
        reg_counts[r] = cur.fetchone()[0]

    cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    workers = cur.fetchall()
    cur.execute("SELECT * FROM pbe_soul_audit ORDER BY id DESC LIMIT 50")
    logs = cur.fetchall(); cur.close(); conn.close()

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <div class="layer-box">
            <div class="layer-title">🛠️ TECHNICAL GUILDS (MATRIX)</div>
            <div class="matrix-grid">
                <a href="#" class="matrix-item active-layer">GLOBAL VIEW</a>
                {{% for g in guilds %}}<a href="#" class="matrix-item">{{{{g}}}}</a>{{% endfor %}}
            </div>
        </div>

        <div class="layer-box">
            <div class="layer-title">🌍 REGIONAL WORKFORCE DISTRIBUTION (16 REGIONS)</div>
            <div class="matrix-grid">
                {{% for reg, count in stats.items() %}}
                <div class="matrix-item" style="text-align:left;">
                    {{{{reg}}}}: <b style="color:red; float:right;">{{{{count}}}}</b>
                </div>
                {{% endfor %}}
            </div>
        </div>

        <div class="layer-box">
            <div class="layer-title">👥 PERSONNEL REGISTRY CONTROL</div>
            <div style="overflow-x:auto;">
                <table class="registry-table">
                    <thead><tr><th>PBE-ID</th><th>NAME</th><th>RANK</th><th>COMMAND SUITE</th></tr></thead>
                    <tbody>
                        {{% for w in workers %}}
                        <tr>
                            <td><b>{{{{ w[5] }}}}</b></td>
                            <td>{{{{ w[1] }}}} {{{{ w[2] }}}}</td>
                            <td>{{{{ w[7] }}}}</td>
                            <td>
                                <a href="/admin/print/{{{{ w[5] }}}}" class="btn-6 bg-navy">PRINT</a>
                                <a href="/admin/renew/{{{{ w[0] }}}}" class="btn-6 bg-gold">RENEW</a>
                                <a href="/admin/suspend/{{{{ w[0] }}}}" class="btn-6 bg-sus">SUSPEND</a>
                                <a href="https://wa.me/{{{{ w[9] }}}}" class="btn-6 bg-wa" target="_blank">WA</a>
                                {{% if session['role'] == 'ADMIN' %}}
                                <a href="/admin/approve/{{{{ w[0] }}}}" class="btn-6 bg-navy">APPROVE</a>
                                <a href="/admin/delete/{{{{ w[0] }}}}" class="btn-6 bg-red" onclick="return confirm('ERASE?')">DELETE</a>
                                {{% endif %}}
                            </td>
                        </tr>
                        {{% endfor %}}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="layer-box">
            <div class="layer-title">🛡️ AUDIT LOGS & BRIEF REPORT</div>
            <div class="audit-scroll">
                {{% for l in logs %}}
                <div style="border-bottom:1px solid #f0f0f0; padding:5px;">
                    [{{{{ l[1].strftime('%H:%M:%S') }}}}] {{{{ l[3] }}}}: {{{{ l[4] }}}}
                </div>
                {{% endfor %}}
            </div>
        </div>
    """), guilds=PBE_GUILDS, workers=workers, logs=logs, stats=reg_counts)

# --- ID PRINTING WITH ROBOT MAPPING ---
@app.route("/admin/print/<uid>")
def print_id(uid):
    if not session.get('role'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT * FROM pbe_master_registry WHERE pbe_uid = %s", (uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    
    buffer = BytesIO(); c = canvas.Canvas(buffer, pagesize=(3.375*inch, 2.125*inch))
    tpl = os.path.join(app.root_path, 'static', 'Power Bridge Engineering ID Identity Template.png')
    if os.path.exists(tpl): c.drawImage(tpl, 0, 0, width=3.375*inch, height=2.125*inch)
    if w[12]: c.drawImage(w[12], 0.18*inch, 0.55*inch, width=1.02*inch, height=1.22*inch)

    c.setFont("Helvetica-Bold", 7); c.setFillColor(colors.black)
    c.drawString(1.35*inch, 1.55*inch, f"Surname: {w[1]}")
    c.drawString(1.35*inch, 1.40*inch, f"Firstname: {w[2]}")
    c.drawString(1.35*inch, 1.25*inch, f"ID No: {w[5]}")
    c.drawString(1.35*inch, 1.10*inch, f"License: {w[6]}")
    c.drawString(1.35*inch, 0.95*inch, f"Rank: {w[7]}")
    
    qr_c = qr.QrCodeWidget(f"{request.url_root}verify/{w[5]}")
    d = Drawing(40, 40, transform=[40./qr_c.getBounds()[2],0,0,40./qr_c.getBounds()[3],0,0])
    d.add(qr_c); d.drawOn(c, 2.8*inch, 0.15*inch)
    c.showPage(); c.save(); buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
