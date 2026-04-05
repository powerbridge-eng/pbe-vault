import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime, csv
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session, abort
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO, StringIO

# --- 1. COMMAND CONFIGURATION (Environment Variables) ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY")
ARKESEL_SENDER_ID = "PBE_OFFICE"
ADMIN_PASSWORD = "PBE-Global-2026"
OFFICIAL_WA = "233245630637"
OFFICIAL_MAIL = "arkuhgilbert@gmail.com"

app = Flask(__name__)
app.secret_key = "PBE_MASTER_VANGUARD_FINAL_FIXED"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# --- 2. GLOBAL MATRIX (Departments & Regions) ---
PBE_GUILDS = [
    "Electrical Engineering", "Solar & Energy", "Plumbing & Hydraulics", 
    "Masonry & Construction", "Mechanical & Auto", "PBE TV", 
    "CCTV & Security", "ICT & Software", "HVAC & Cooling", "General Technical", "ETC"
]

GHANA_REGIONS = ["Greater Accra", "Ashanti", "Western", "Central", "Eastern", "Volta", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Oti", "Western North"]

# --- 3. DATABASE & SOUL TRACKER ---
def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_master_registry (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT,
            gender TEXT, nationality TEXT, pbe_uid TEXT UNIQUE, pbe_license TEXT UNIQUE,
            issuance_date DATE, expiry_date DATE, rank TEXT, department TEXT,
            phone_no TEXT, photo_url TEXT, status TEXT DEFAULT 'PENDING',
            otp_code TEXT, region TEXT, station TEXT, scans INT DEFAULT 0
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_soul_audit (
            id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            action TEXT, details TEXT, ip_address TEXT, device_info TEXT
        );
    """)
    conn.commit(); cur.close(); conn.close()

def log_soul_action(action, details):
    # SOUL TRACKER: CAPTURING IP AND DEVICE IDENTITY
    device = f"{request.user_agent.platform} | {request.user_agent.browser} | {request.user_agent.string[:40]}"
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_soul_audit (action, details, ip_address, device_info) VALUES (%s, %s, %s, %s)",
                (action, details, request.remote_addr, device))
    conn.commit(); cur.close(); conn.close()

with app.app_context():
    init_db()

# --- 4. CREDENTIAL GENERATOR (15-CHAR) ---
def generate_15_char(name):
    clean = re.sub(r'[^A-Z]', '', name.upper())
    return f"{clean[:6]}{''.join(random.choices(string.digits + string.ascii_uppercase, k=9))}"

# --- 5. THE MASTER INTERFACE ---
BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
    <title>PBE Command Center</title>
    <style>
        :root { --navy: #0a192f; --gold: #ffcc00; --red: #e63946; --green: #25D366; --blue: #007bff; --slate: #f1f5f9; --orange: #fd7e14; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--slate); margin: 0; padding-bottom: 100px; color: #1e293b; }
        .app-header { background: var(--navy); color: white; padding: 25px; text-align: center; border-bottom: 5px solid var(--gold); position: sticky; top: 0; z-index: 100; }
        .logo-main { height: 65px; margin-bottom: 10px; background: #fff; padding: 5px; border-radius: 8px; }
        .container { max-width: 1200px; margin: auto; padding: 15px; }
        .pulse-bar { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; align-items: center; }
        .search-field { flex: 1; padding: 15px; border-radius: 12px; border: 1px solid #cbd5e1; font-size: 16px; outline: none; }
        .live-stat { background: #fff; padding: 12px 15px; border-radius: 10px; border: 1px solid #e2e8f0; font-weight: bold; font-size: 12px; }
        .card-layer { background: #fff; border-radius: 16px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        .guild-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; }
        .guild-btn { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; text-align: center; text-decoration: none; color: var(--navy); font-size: 11px; font-weight: bold; }
        .guild-active { background: var(--navy); color: var(--gold); border-color: var(--gold); }
        table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 10px; }
        th { text-align: left; padding: 12px; border-bottom: 2px solid #f1f5f9; color: #64748b; }
        td { padding: 15px 12px; border-bottom: 1px solid #f1f3f5; }
        .cmd-btn { padding: 8px 10px; border-radius: 6px; color: white; text-decoration: none; font-size: 10px; font-weight: bold; display: inline-block; margin: 2px; transition: 0.2s; }
        .bg-navy { background: var(--navy); } .bg-wa { background: var(--green); } .bg-del { background: var(--red); } .bg-blue { background: var(--blue); } .bg-orange { background: var(--orange); }
        .fab-btn { position: fixed; bottom: 30px; right: 30px; width: 65px; height: 65px; background: var(--navy); color: var(--gold); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); text-decoration: none; z-index: 101; border: 2px solid var(--gold); }
    </style>
</head>
<body>
    <div class="app-header">
        <img src="{{ url_for('static', filename='logo.png') }}" class="logo-main" onerror="this.style.display='none'">
        <div style="font-size: 22px; font-weight: 900;">PBE COMMAND CENTER</div>
    </div>
    <div class="container">{% block content %}{% endblock %}</div>
    <a href="/admin/invite" class="fab-btn">＋</a>
</body>
</html>
"""

# --- 6. CORE ROUTES ---

@app.route("/")
def gate_redirect(): return redirect(url_for('pbe_login'))

@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def pbe_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            log_soul_action("SECURITY_LOGIN", "Master Entry")
            return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="card-layer" style="max-width:350px; margin: 100px auto; text-align:center;"><h3>HQ AUTHORIZATION</h3><form method="POST"><input type="password" name="password" style="width:100%; padding:15px; border-radius:10px; border:1px solid #ddd; margin-bottom:15px;" placeholder="Master Key" required><button class="cmd-btn bg-navy" style="width:100%; padding:15px; width:100%;">UNLOCK COMMAND</button></form></div>'))

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('logged_in'): return redirect(url_for('pbe_login'))
    
    # LIVE ARKESEL BALANCE PULSE
    sms_live = "CHECKING..."
    try:
        r = requests.get("https://sms.arkesel.com/api/v2/clients/balance", headers={"api-key": ARKESEL_API_KEY}, timeout=4)
        if r.status_code == 200:
            bal = r.json().get('data', {}).get('available_balance', '0.00')
            sms_live = f"{bal} GHS LEFT"
    except: sms_live = "OFFLINE"

    conn = get_db(); cur = conn.cursor()
    dept = request.args.get('dept')
    if dept: cur.execute("SELECT * FROM pbe_master_registry WHERE department = %s ORDER BY id DESC", (dept,))
    else: cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <div class="pulse-bar">
            <input type="text" id="search" class="search-field" placeholder="Search Global World Registry...">
            <div class="live-stat">💰 SMS: {sms_live}</div>
            <a href="/admin/audit-logs" class="live-stat" style="text-decoration:none; color:var(--navy);">📜 AUDIT LOGS</a>
            <a href="https://wa.me/{OFFICIAL_WA}" class="live-stat" style="text-decoration:none; background:var(--green); color:white;">📱 WA OFFICE</a>
        </div>

        <div class="card-layer">
            <div style="font-size:11px; font-weight:800; color:#64748b; margin-bottom:12px;">🛠️ TECHNICAL GUILDS</div>
            <div class="guild-grid">
                <a href="/admin-dashboard" class="guild-btn {{{{ 'guild-active' if not current_dept }}}}">GLOBAL WORLD</a>
                {{% for g in guilds %}}
                <a href="/admin-dashboard?dept={{{{ g }}}}" class="guild-btn {{{{ 'guild-active' if current_dept == g }}}}">{{{{ g.upper() }}}}</a>
                {{% endfor %}}
            </div>
        </div>

        <div class="card-layer">
            <div style="font-size:11px; font-weight:800; color:#64748b; margin-bottom:12px;">👥 PERSONNEL MATRIX</div>
            <div style="overflow-x:auto;">
                <table>
                    <thead><tr><th>PBE-ID / LIC</th><th>NAME</th><th>RANK</th><th>STATUS</th><th>ACTIONS</th></tr></thead>
                    <tbody>
                        {{% for w in workers %}}
                        <tr>
                            <td><b>{{{{ w[6] }}}}</b><br><small style="color:gray;">LIC: {{{{ w[7] }}}}</small></td>
                            <td>{{{{ w[1] }}}}, {{{{ w[2] }}}}</td>
                            <td>{{{{ w[10] }}}}<br><small>{{{{ w[11] }}}}</small></td>
                            <td>
                                {{% if w[14] == 'ACTIVE' %}} <span style="color:var(--green); font-weight:bold;">ACTIVE</span>
                                {{% elif w[14] == 'SUSPENDED' %}} <span style="color:var(--orange); font-weight:bold;">SUSPENDED</span>
                                {{% else %}} <span style="color:gray; font-weight:bold;">PENDING</span> {{% endif %}}
                            </td>
                            <td>
                                <a href="/admin/print-id/{{{{ w[6] }}}}" class="cmd-btn bg-blue">Print</a>
                                <a href="https://wa.me/{{{{ w[12] }}}}" class="cmd-btn bg-wa" target="_blank">WA</a>
                                <a href="/admin/suspend/{{{{ w[0] }}}}" class="cmd-btn bg-orange">Susp</a>
                                <a href="/admin/delete/{{{{ w[0] }}}}" class="cmd-btn bg-del" onclick="return confirm('ERASE PERMANENTLY?')">Del</a>
                            </td>
                        </tr>
                        {{% endfor %}}
                    </tbody>
                </table>
            </div>
        </div>
    """), guilds=PBE_GUILDS, workers=workers, current_dept=dept)

@app.route("/admin/audit-logs")
def view_audit():
    if not session.get('logged_in'): return redirect(url_for('pbe_login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_soul_audit ORDER BY timestamp DESC LIMIT 50")
    logs = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="card-layer">
            <h3>Accountability Soul Audit</h3>
            <table><tr><th>Time</th><th>Action</th><th>Device Fingerprint / IP Address</th></tr>
            {% for l in logs %}
            <tr><td>{{l[1].strftime('%H:%M:%S')}}</td><td><b>{{l[2]}}</b></td><td><small>{{l[5]}}</small></td></tr>
            {% endfor %}</table>
            <br><a href="/admin-dashboard" class="cmd-btn bg-navy">Return to Command</a>
        </div>
    """), logs=logs)

# --- 7. PRINT ENGINE (PDF CLONE MAPPING) ---
@app.route("/admin/print-id/<pbe_uid>")
def print_id(pbe_uid):
    if not session.get('logged_in'): return redirect(url_for('pbe_login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT * FROM pbe_master_registry WHERE pbe_uid = %s", (pbe_uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    
    buffer = BytesIO(); c = canvas.Canvas(buffer, pagesize=(3.375*inch, 2.125*inch))
    
    # 1. THE BASE TEMPLATE (Cloned from design)
    tpl = os.path.join(app.root_path, 'static', 'Power Bridge Engineering ID Identity Template.png')
    if os.path.exists(tpl): c.drawImage(tpl, 0, 0, width=3.375*inch, height=2.125*inch)
    
    # 2. MAIN PHOTO (Left Side) - Removed Background blending via mask
    if w[13]:
        # Main Passport
        c.drawImage(w[13], 0.18*inch, 0.55*inch, width=1.02*inch, height=1.22*inch, mask='auto')
        # Ghost Photo (Right Side - Transparent)
        c.saveState()
        c.setFillAlpha(0.2)
        c.drawImage(w[13], 2.2*inch, 0.55*inch, width=0.8*inch, height=1.0*inch, mask='auto')
        c.restoreState()

    # 3. TEXT MAPPING
    c.setFont("Helvetica-Bold", 7); c.setFillColor(colors.black)
    c.drawString(1.35*inch, 1.55*inch, f"{w[1]}") # Surname
    c.drawString(1.35*inch, 1.40*inch, f"{w[2]}") # Firstname
    c.drawString(1.35*inch, 1.25*inch, f"{w[6]}") # ID
    c.drawString(1.35*inch, 1.10*inch, f"{w[7]}") # License
    
    qr_code = qr.QrCodeWidget(f"{request.url_root}verify/{w[6]}")
    bounds = qr_code.getBounds(); d = Drawing(40, 40, transform=[40./(bounds[2]-bounds[0]),0,0,40./(bounds[3]-bounds[1]),0,0])
    d.add(qr_code); d.drawOn(c, 2.8*inch, 0.15*inch)
    
    c.showPage(); c.save(); buffer.seek(0)
    log_soul_action("PRINT_ID", f"Physical Card Cloned for {w[1]}")
    return send_file(buffer, mimetype='application/pdf')

# [Registration, Invite, Suspend, Delete routes fully integrated with 'pbe_login' endpoint fixes]

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if not session.get('logged_in'): return redirect(url_for('pbe_login'))
    if request.method == 'POST':
        phone, otp = request.form.get('phone'), str(random.randint(111111, 999999))
        conn = get_db(); cur = conn.cursor(); cur.execute("INSERT INTO pbe_master_registry (phone_no, otp_code) VALUES (%s, %s)", (phone, otp)); conn.commit(); cur.close(); conn.close()
        # SMS TRIGGER
        requests.post("https://sms.arkesel.com/api/v2/sms/send", json={"sender": "PBE_OFFICE", "message": f"PBE: Use code {otp} at {request.url_root}register", "recipients": [phone]}, headers={"api-key": ARKESEL_API_KEY})
        log_soul_action("INVITE", f"OTP {otp} sent to {phone}")
        return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="card-layer" style="max-width:400px; margin:auto;"><h3>Invite Worker</h3><form method="POST"><input name="phone" placeholder="233..."><button class="cmd-btn bg-blue" style="width:100%; padding:15px; margin-top:10px;">Send OTP</button></form></div>'))

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        otp = request.form.get('otp')
        conn = get_db(); cur = conn.cursor(); cur.execute("SELECT id FROM pbe_master_registry WHERE otp_code = %s", (otp,))
        if cur.fetchone():
            fname, sname = request.form.get('firstname').upper().replace(" ", "_"), request.form.get('surname').upper().replace(" ", "_")
            photo = cloudinary.uploader.upload(request.files['photo'], public_id=f"PBE_PP_{fname}_{sname}")
            uid, lic = generate_15_char(fname), generate_15_char(sname)
            cur.execute("""UPDATE pbe_master_registry SET surname=%s, firstname=%s, dob=%s, pbe_uid=%s, pbe_license=%s,
                        issuance_date=%s, expiry_date=%s, rank=%s, department=%s, photo_url=%s, 
                        status='PENDING', region=%s, station=%s WHERE otp_code=%s""",
                        (request.form.get('surname').upper(), fname, request.form.get('dob'), uid, lic,
                        datetime.date.today(), datetime.date.today() + datetime.timedelta(days=730),
                        request.form.get('rank'), request.form.get('department'), photo['secure_url'], 
                        request.form.get('region'), request.form.get('station'), otp))
            conn.commit(); cur.close(); conn.close()
            return "<div style='text-align:center; padding:100px;'><h1>REGISTRATION RECEIVED ✅</h1></div>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="card-layer" style="max-width:500px; margin: auto;">
            <h3>PERSONNEL ENROLLMENT</h3>
            <form method="POST" enctype="multipart/form-data">
                <input name="otp" placeholder="OTP" style="width:100%; padding:12px; margin:5px 0;" required>
                <input name="surname" placeholder="Surname" style="width:100%; padding:12px; margin:5px 0;" required>
                <input name="firstname" placeholder="First Name" style="width:100%; padding:12px; margin:5px 0;" required>
                <select name="department" style="width:100%; padding:12px; margin:5px 0;">
                    {% for g in guilds %}<option value="{{g}}">{{g}}</option>{% endfor %}
                </select>
                <input name="rank" placeholder="Job Title" style="width:100%; padding:12px; margin:5px 0;" required>
                <input type="file" name="photo" required>
                <button class="cmd-btn bg-navy" style="width:100%; padding:15px; margin-top:10px;">SUBMIT</button>
            </form>
        </div>
    """), guilds=PBE_GUILDS)

@app.route("/admin/suspend/<int:id>")
def suspend_worker(id):
    if not session.get('logged_in'): return redirect(url_for('pbe_login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("UPDATE pbe_master_registry SET status='SUSPENDED' WHERE id=%s", (id,)); conn.commit(); cur.close(); conn.close()
    log_soul_action("SUSPEND", f"Worker {id} moved to Investigation")
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/delete/<int:id>")
def delete_worker(id):
    if not session.get('logged_in'): return redirect(url_for('pbe_login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("DELETE FROM pbe_master_registry WHERE id=%s", (id,)); conn.commit(); cur.close(); conn.close()
    log_soul_action("DELETE", f"Worker record {id} erased")
    return redirect(url_for('admin_dashboard'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
