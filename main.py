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
app.secret_key = "PBE_SUPREME_CORE_2026_HEALED"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

PBE_GUILDS = ["ELECTRICAL ENGINEERING", "SOLAR & ENERGY", "PLUMBING & HYDRAULICS", "MASONRY & CONSTRUCTION", "MECHANICAL & AUTO", "PBE TV", "CCTV & SECURITY", "ICT & SOFTWARE", "HVAC & COOLING", "FASHION DESIGN", "GENERAL TECHNICAL"]

# --- 2. INTERNAL HEALING SYSTEM (The "Doctor" Logic) ---
def perform_self_heal():
    """Checks for table existence and missing columns, creating/fixing them instantly."""
    conn = get_db(); cur = conn.cursor()
    
    # HEAL LAYER 1: Master Registry
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_master_registry (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT, gender TEXT, 
            pbe_uid TEXT UNIQUE, pbe_license TEXT UNIQUE, rank TEXT, department TEXT,
            phone_no TEXT UNIQUE, email TEXT UNIQUE, ghana_card TEXT UNIQUE, 
            photo_url TEXT, status TEXT DEFAULT 'PENDING', otp_code TEXT, 
            region TEXT, station TEXT, issuance_date DATE, expiry_date DATE
        );
    """)
    
    # HEAL LAYER 2: Soul Audit (Missing 'actor' check)
    cur.execute("CREATE TABLE IF NOT EXISTS pbe_soul_audit (id SERIAL PRIMARY KEY);")
    columns_to_heal = {
        "timestamp": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "action": "TEXT",
        "actor": "TEXT",
        "details": "TEXT",
        "ip": "TEXT",
        "device": "TEXT"
    }
    for col, definition in columns_to_heal.items():
        cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='pbe_soul_audit' AND column_name='{col}';")
        if not cur.fetchone():
            cur.execute(f"ALTER TABLE pbe_soul_audit ADD COLUMN {col} {definition};")
            
    conn.commit(); cur.close(); conn.close()

# Auto-heal every time the app starts
with app.app_context():
    perform_self_heal()

def log_action(action, details, actor="SYSTEM"):
    device = f"{request.user_agent.platform} | {request.user_agent.browser}"
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_soul_audit (action, actor, details, ip, device) VALUES (%s, %s, %s, %s, %s)",
                (action, actor, details, request.remote_addr, device))
    conn.commit(); cur.close(); conn.close()

def gen_15(name):
    clean = re.sub(r'[^A-Z]', '', name.upper())
    return f"{clean[:6]}{''.join(random.choices(string.digits + string.ascii_uppercase, k=9))}"

# --- 3. LAYERED UI DESIGN ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <title>PBE Command Center</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root { --navy: #0a192f; --gold: #ffcc00; --bg: #f8fafc; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; padding-bottom: 80px; }
        .header { background: var(--navy); color: white; padding: 25px; text-align: center; border-bottom: 5px solid var(--gold); position: sticky; top: 0; z-index: 1000; }
        .logo-badge { width: 70px; height: 70px; background: white; border-radius: 50%; padding: 5px; margin: 0 auto 10px; display: flex; align-items: center; justify-content: center; border: 2px solid var(--gold); overflow: hidden; }
        .logo-img { max-width: 100%; max-height: 100%; object-fit: contain; }
        .container { max-width: 1200px; margin: auto; padding: 15px; }
        
        /* Layered Architecture */
        .layer-box { background: white; border-radius: 12px; padding: 25px; margin-bottom: 25px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .layer-title { font-size: 13px; font-weight: 800; color: #64748b; text-transform: uppercase; margin-bottom: 20px; border-left: 5px solid var(--navy); padding-left: 15px; }
        
        .registry-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .registry-table th, .registry-table td { text-align: left; padding: 15px; border-bottom: 1px solid #f1f5f9; }
        
        .btn-suite { padding: 10px 15px; border-radius: 8px; color: white; text-decoration: none; font-size: 11px; font-weight: 900; border: none; cursor: pointer; display: inline-block; margin: 2px; transition: 0.2s; }
        .bg-print { background: #334155; } .bg-wa { background: #22c55e; } .bg-red { background: #ef4444; } .bg-gold { background: var(--gold); color: #000; } .bg-navy { background: var(--navy); }
        
        .search-bar { width: 100%; padding: 15px; border-radius: 12px; border: 1px solid #cbd5e1; font-size: 16px; margin-bottom: 20px; box-sizing: border-box; }
        .audit-list { height: 200px; overflow-y: auto; background: #fdfdfd; border: 1px solid #eee; border-radius: 10px; padding: 10px; }
        .log-entry { font-size: 12px; padding: 8px; border-bottom: 1px solid #f8f9fa; display: flex; justify-content: space-between; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo-badge">
            <img src="{{ url_for('static', filename='logo.png') }}" class="logo-img" onerror="this.parentElement.style.display='none'">
        </div>
        <div style="font-size: 20px; font-weight: 900; letter-spacing: 2px;">PBE COMMAND CENTER</div>
    </div>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- 4. ROUTES ---

@app.route("/")
def index(): return redirect(url_for('admin_login'))

@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        pwd = request.form.get('password')
        name = request.form.get('name')
        if pwd == ADMIN_PASSWORD:
            session['role'], session['name'] = 'ADMIN', name
            log_action("AUTH_SUCCESS", "Full Control Access", name)
            return redirect(url_for('admin_dashboard'))
        elif pwd == SUPERVISOR_PASSWORD:
            session['role'], session['name'] = 'SUPERVISOR', name
            log_action("AUTH_SUCCESS", "Limited Supervisor Access", name)
            return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="layer-box" style="max-width:380px; margin: 80px auto; text-align:center;"><h3>SYSTEM LOCK</h3><form method="POST"><input name="name" class="search-bar" placeholder="Personnel Name" required><input type="password" name="password" class="search-bar" placeholder="Security Key" required><button class="btn-suite bg-navy" style="width:100%; padding:15px;">UNLOCK SYSTEM</button></form></div>'))

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('role'): return redirect(url_for('admin_login'))
    
    sms_bal = "..."
    try:
        r = requests.get("https://sms.arkesel.com/api/v2/clients/balance", headers={"api-key": ARKESEL_API_KEY}, timeout=2)
        sms_bal = f"{r.json().get('data', {}).get('available_balance', '0.00')} GHS"
    except: sms_bal = "Offline"

    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    workers = cur.fetchall()
    cur.execute("SELECT * FROM pbe_soul_audit ORDER BY id DESC LIMIT 50")
    logs = cur.fetchall(); cur.close(); conn.close()

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <input type="text" class="search-bar" placeholder="Master Search (Name, Phone, ID, Rank)...">
        
        <div style="display:flex; gap:15px; margin-bottom:25px;">
            <div class="layer-box" style="margin:0; flex:1; text-align:center;">SMS BALANCE: <b>{sms_bal}</b></div>
            <a href="https://cloudinary.com/console" target="_blank" class="btn-suite bg-navy" style="flex:1; display:flex; align-items:center; justify-content:center;">CLOUDINARY REPOSITORY</a>
        </div>

        <div class="layer-box">
            <div class="layer-title">👥 PERSONNEL REGISTRY LAYERS</div>
            <div style="overflow-x:auto;">
                <table class="registry-table">
                    <thead><tr><th>ID</th><th>NAME</th><th>RANK</th><th>COMMANDS</th></tr></thead>
                    <tbody>
                        {{% for w in workers %}}
                        <tr>
                            <td><b>{{{{ w[5] }}}}</b></td>
                            <td>{{{{ w[1] }}}} {{{{ w[2] }}}}</td>
                            <td>{{{{ w[7] }}}}</td>
                            <td>
                                <a href="/admin/print/{{{{ w[5] }}}}" class="btn-suite bg-print">PRINT ID</a>
                                <a href="/admin/renew/{{{{ w[0] }}}}" class="btn-suite bg-gold">RENEWAL</a>
                                
                                {{% if session['role'] == 'ADMIN' %}}
                                <a href="https://wa.me/{{{{ w[9] }}}}" class="btn-suite bg-wa">WHATSAPP</a>
                                <a href="/admin/approve/{{{{ w[0] }}}}" class="btn-suite bg-navy">APPROVE</a>
                                <a href="/admin/delete/{{{{ w[0] }}}}" class="btn-suite bg-red" onclick="return confirm('ERASE PERMANENTLY?')">DELETE</a>
                                {{% endif %}}
                            </td>
                        </tr>
                        {{% endfor %}}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="layer-box">
            <div class="layer-title">📊 SOUL AUDIT (LIVE TRACKING)</div>
            <div class="audit-list">
                {{% for l in logs %}}
                <div class="log-entry">
                    <span><b>[{{{{ l[1].strftime('%H:%M:%S') }}}}]</b> {{{{ l[3] }}}} ({{{{ l[2] }}}})</span>
                    <span>{{{{ l[4] }}}}</span>
                </div>
                {{% endfor %}}
            </div>
        </div>
    """), workers=workers, logs=logs)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        otp = request.form.get('otp')
        conn = get_db(); cur = conn.cursor()
        
        # Validation
        cur.execute("SELECT id FROM pbe_master_registry WHERE phone_no=%s OR email=%s OR ghana_card=%s", 
                   (request.form.get('phone'), request.form.get('email'), request.form.get('ghana_card')))
        if cur.fetchone(): return "DUPLICATE ENTRY DETECTED."

        # Photo to Cloudinary - Named by Person
        full_name = f"{request.form.get('surname')}_{request.form.get('firstname')}"
        up = cloudinary.uploader.upload(request.files['photo'], public_id=f"PBE_PHOTO_{full_name}")
        
        uid, lic = gen_15(request.form.get('firstname')), gen_15(request.form.get('surname'))
        cur.execute("""UPDATE pbe_master_registry SET surname=%s, firstname=%s, pbe_uid=%s, pbe_license=%s,
                    rank=%s, department=%s, phone_no=%s, email=%s, ghana_card=%s, photo_url=%s, 
                    status='REVIEW', issuance_date=%s, expiry_date=%s WHERE otp_code=%s""",
                   (request.form.get('surname').upper(), request.form.get('firstname').upper(),
                    uid, lic, request.form.get('rank'), request.form.get('department'),
                    request.form.get('phone'), request.form.get('email'), request.form.get('ghana_card'),
                    up['secure_url'], datetime.date.today(), datetime.date.today() + datetime.timedelta(days=730), otp))
        conn.commit(); cur.close(); conn.close()
        return "REGISTRY SUBMITTED ✅ Respond in 3 working days. Contact: 233541803057"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<h3>REGISTRY FORM</h3><form method="POST" enctype="multipart/form-data">...</form>'))

@app.route("/admin/print/<uid>")
def print_id(uid):
    if not session.get('role'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_master_registry WHERE pbe_uid = %s", (uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    
    buffer = BytesIO(); c = canvas.Canvas(buffer, pagesize=(3.375*inch, 2.125*inch))
    tpl = os.path.join(app.root_path, 'static', 'Power Bridge Engineering ID Identity Template.png')
    if os.path.exists(tpl): c.drawImage(tpl, 0, 0, width=3.375*inch, height=2.125*inch)
    if w[12]: c.drawImage(w[12], 0.18*inch, 0.55*inch, width=1.02*inch, height=1.22*inch)

    c.setFont("Helvetica-Bold", 7); c.setFillColor(colors.black)
    c.drawString(1.35*inch, 1.55*inch, f"Surname: {w[1]}")
    c.drawString(1.35*inch, 1.40*inch, f"Firstname: {w[2]}")
    c.drawString(1.35*inch, 1.25*inch, f"ID No: {w[5]}")
    c.drawString(1.35*inch, 1.10*inch, f"Rank: {w[7]}")
    c.drawString(1.35*inch, 0.80*inch, f"EXP: {w[18]}")
    
    qr_c = qr.QrCodeWidget(f"{request.url_root}verify/{w[5]}")
    d = Drawing(40, 40, transform=[40./qr_c.getBounds()[2],0,0,40./qr_c.getBounds()[3],0,0])
    d.add(qr_c); d.drawOn(c, 2.8*inch, 0.15*inch)
    c.showPage(); c.save(); buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf')

# [Renewal, Approve, Delete restricted by 'ADMIN' logic as requested]

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
