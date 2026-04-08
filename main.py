import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime, time, csv
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session, abort
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from io import BytesIO, StringIO

# --- 1. CORE CONFIGURATION ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY")
ADMIN_PASSWORD = "PBE-Global-2026"
SUPERVISOR_PASSWORD = "PBE_Secure_2026"

app = Flask(__name__)
app.secret_key = "PBE_ABSOLUTE_FINAL_BUILD_2026"

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

# --- 2. SECURITY, AUDIT & NEW 2026 REGISTRY DOCTOR ---
def init_db():
    conn = get_db(); cur = conn.cursor()
    # BRAND NEW TABLE TO BYPASS THE OLD SCHEMA ERROR
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_registry_2026 (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT,
            pbe_uid TEXT UNIQUE, pbe_license TEXT UNIQUE, rank TEXT, department TEXT,
            phone_no TEXT, email TEXT, ghana_card_no TEXT, photo_url TEXT, ghana_card_url TEXT,
            status TEXT DEFAULT 'PENDING', otp_code TEXT, region TEXT, station TEXT,
            issuance_date DATE, expiry_date DATE
        );
    """)
    cur.execute("CREATE TABLE IF NOT EXISTS pbe_soul_audit (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, action TEXT, actor TEXT, details TEXT, ip_address TEXT, device_info TEXT);")
    cur.execute("CREATE TABLE IF NOT EXISTS pbe_ip_blacklist (id SERIAL PRIMARY KEY, ip_address TEXT UNIQUE, locked_until TIMESTAMP);")
    conn.commit(); cur.close(); conn.close()

with app.app_context(): init_db()

def log_soul_action(action, details):
    actor = session.get('role', 'SYSTEM')
    device = f"{request.user_agent.platform} | {request.user_agent.browser}"
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_soul_audit (action, actor, details, ip_address, device_info) VALUES (%s, %s, %s, %s, %s)",
                (action, actor, details, request.remote_addr, device))
    conn.commit(); cur.close(); conn.close()

def is_blacklisted(ip):
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT locked_until FROM pbe_ip_blacklist WHERE ip_address = %s", (ip,))
    res = cur.fetchone(); cur.close(); conn.close()
    return True if res and res[0] > datetime.datetime.now() else False

def blacklist_ip(ip):
    lock_time = datetime.datetime.now() + datetime.timedelta(hours=72)
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_ip_blacklist (ip_address, locked_until) VALUES (%s, %s) ON CONFLICT (ip_address) DO UPDATE SET locked_until = %s", (ip, lock_time, lock_time))
    conn.commit(); cur.close(); conn.close()

# --- 3. 15-CHAR ID/LICENSE GENERATOR ---
def generate_15_char(name):
    clean = re.sub(r'[^A-Z]', '', name.upper())
    part = clean[:6]
    needed = 15 - len(part)
    return f"{part}{''.join(random.choices(string.digits + string.ascii_uppercase, k=needed))}"

# --- 4. THE PBE WORLD MATRIX ---
PBE_GUILDS = [
    "ELECTRICAL ENGINEERING", "SOLAR & ENERGY", "PLUMBING & HYDRAULICS", 
    "MASONRY & CONSTRUCTION", "MECHANICAL & AUTO", "PBE TV", 
    "CCTV & SECURITY", "ICT & SOFTWARE", "HVAC & COOLING", "GENERAL TECHNICAL"
]
GHANA_REGIONS = ["Greater Accra", "Ashanti", "Western", "Central", "Eastern", "Volta", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Oti", "Western North"]

# --- 5. EXECUTIVE UI DESIGN ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
    <title>PBE Command Center</title>
    <style>
        :root { --navy: #343a40; --gold: #ffc107; --bg: #f4f6f9; --text: #495057; }
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: var(--bg); margin: 0; color: var(--text); padding-bottom: 100px; }
        .header { background: var(--navy); color: white; padding: 25px; text-align: center; border-bottom: 4px solid var(--gold); }
        .logo { height: 60px; margin-bottom: 10px; border-radius: 50%; }
        .container { max-width: 1200px; margin: auto; padding: 15px; }
        .search-container { display: flex; gap: 10px; margin-bottom: 20px; align-items: center; flex-wrap: wrap; }
        .search-bar { flex: 1; padding: 15px; border-radius: 10px; border: 1px solid #dee2e6; font-size: 16px; outline: none; background: #fff; min-width: 280px; }
        .sms-balance { background: #fff; padding: 15px; border-radius: 10px; border: 1px solid #dee2e6; font-weight: bold; }
        .section-card { background: #fff; border-radius: 15px; padding: 20px; margin-bottom: 20px; border: 1px solid #e9ecef; }
        .section-title { font-size: 13px; font-weight: 800; color: #6c757d; text-transform: uppercase; margin-bottom: 15px; border-left: 4px solid var(--navy); padding-left: 10px; }
        .guild-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; }
        .guild-btn { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 10px; padding: 15px 5px; text-align: center; text-decoration: none; color: var(--navy); font-size: 11px; font-weight: bold; }
        .guild-active { background: var(--navy); color: var(--gold); border-color: var(--gold); }
        .registry-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .registry-table th { text-align: left; padding: 12px; border-bottom: 2px solid #dee2e6; }
        .registry-table td { padding: 15px 12px; border-bottom: 1px solid #f1f3f5; }
        .btn-cmd { padding: 8px 12px; border-radius: 6px; color: white; text-decoration: none; font-size: 10px; font-weight: bold; margin: 2px; display: inline-block; border: none; cursor: pointer; }
        .bg-blue { background: #007bff; } .bg-wa { background: #28a745; } .bg-red { background: #dc3545; } .bg-sus { background: #6c757d; } .bg-gold { background: var(--gold); color: #000; } .bg-navy { background: var(--navy); }
        .fab-zone { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 12px; z-index: 1000; }
        .fab { width: 60px; height: 60px; background: var(--navy); color: var(--gold); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); text-decoration: none; border: 2px solid var(--gold); }
    </style>
</head>
<body>
    <div class="header">
        <img src="{{ url_for('static', filename='logo.png') }}" class="logo" onerror="this.style.display='none'">
        <div style="font-size: 22px; font-weight: 900;">PBE COMMAND CENTER</div>
    </div>
    <div class="container">{% block content %}{% endblock %}</div>
    <script>
        function filterRegistry() {
            let filter = document.getElementById('globalSearch').value.toUpperCase();
            document.querySelectorAll('.worker-row').forEach(row => {
                row.style.display = row.innerText.toUpperCase().includes(filter) ? '' : 'none';
            });
        }
    </script>
</body>
</html>
"""

# --- 6. DASHBOARD & GLOBAL METRIC ---
@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('role'): return redirect(url_for('admin_login'))
    role = session.get('role')
    
    sms_live = "..."
    try:
        r = requests.get("https://sms.arkesel.com/api/v2/clients/balance", headers={"api-key": ARKESEL_API_KEY}, timeout=3)
        sms_live = f"{r.json().get('data', {}).get('available_balance', '0.00')} GHS"
    except: sms_live = "OFFLINE"

    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM pbe_registry_2026 WHERE expiry_date <= CURRENT_DATE + INTERVAL '30 days'")
    expiry_alerts = cur.fetchone()[0]

    dept = request.args.get('dept')
    if dept: cur.execute("SELECT * FROM pbe_registry_2026 WHERE department = %s ORDER BY id DESC", (dept,))
    else: cur.execute("SELECT * FROM pbe_registry_2026 ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <div class="search-container">
            <input type="text" id="globalSearch" class="search-bar" placeholder="Search Names, ID or License..." onkeyup="filterRegistry()">
            {{% if role == 'ADMIN' %}}
            <a href="https://cloudinary.com/console" target="_blank" class="btn-cmd bg-navy" style="padding:15px; font-size:14px;">☁️ CLOUDINARY</a>
            {{% endif %}}
            <div class="sms-balance">SMS: {sms_live}</div>
        </div>
        
        <div class="section-card">
            <div class="section-title">🛠️ TECHNICAL GUILDS</div>
            <div class="guild-grid">
                <a href="/admin-dashboard" class="guild-btn {{{{ 'guild-active' if not current_dept }}}}">GLOBAL METRIC</a>
                {{% for g in guilds %}}
                <a href="/admin-dashboard?dept={{{{ g }}}}" class="guild-btn {{{{ 'guild-active' if current_dept == g }}}}">{{{{ g }}}}</a>
                {{% endfor %}}
            </div>
        </div>

        <div class="section-card">
            <div class="section-title">👥 PERSONNEL REGISTRY</div>
            <div style="overflow-x:auto;">
                <table class="registry-table">
                    <thead><tr><th>PBE-ID / LICENSE</th><th>NAME</th><th>RANK</th><th>STATUS</th><th>COMMANDS</th></tr></thead>
                    <tbody>
                        {{% for w in workers %}}
                        <tr class="worker-row">
                            <td>ID: <b>{{{{ w[4] }}}}</b><br>LIC: <small>{{{{ w[5] }}}}</small></td>
                            <td>{{{{ w[1] }}}}, {{{{ w[2] }}}}</td>
                            <td>{{{{ w[6] }}}}</td>
                            <td><b style="color:{{{{ '#28a745' if w[13]=='ACTIVE' else '#dc3545' }}}};">{{{{ w[13] }}}}</b></td>
                            <td>
                                <a href="/admin/print-id/{{{{ w[4] }}}}" class="btn-cmd bg-blue">PRINT</a>
                                <a href="https://wa.me/{{{{ w[8] }}}}" class="btn-cmd bg-wa" target="_blank">WA</a>
                                <a href="mailto:{{{{ w[9] }}}}" class="btn-cmd bg-navy">EMAIL</a>
                                {{% if role == 'ADMIN' %}}
                                <a href="/admin/approve/{{{{ w[4] }}}}" class="btn-cmd bg-wa">APPROVE</a>
                                <a href="/admin/suspend/{{{{ w[4] }}}}" class="btn-cmd bg-sus">SUSPEND</a>
                                <a href="/admin/unsuspend/{{{{ w[4] }}}}" class="btn-cmd bg-blue">UNSUSPEND</a>
                                <a href="/admin/renew/{{{{ w[4] }}}}" class="btn-cmd bg-gold">RENEW</a>
                                <a href="/admin/delete/{{{{ w[4] }}}}" class="btn-cmd bg-red" onclick="return confirm('Erase Soul Record?')">DELETE</a>
                                {{% endif %}}
                            </td>
                        </tr>
                        {{% endfor %}}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="fab-zone">
            <a href="/admin/alerts" class="fab" title="Alerts">🔔 {{{{alerts}}}}</a>
            {{% if role == 'ADMIN' %}}<a href="/admin/audit" class="fab" title="Audit">📜</a>{{% endif %}}
            <a href="/admin/invite" class="fab" title="Invite">＋</a>
        </div>
    """), guilds=PBE_GUILDS, workers=workers, current_dept=dept, role=role, alerts=expiry_alerts)

# --- 7. COMMAND ENDPOINTS (THE 8 BUTTONS) ---
@app.route("/admin/approve/<uid>")
def approve_cmd(uid):
    if session.get('role') != 'ADMIN': abort(403)
    conn = get_db(); cur = conn.cursor(); cur.execute("UPDATE pbe_registry_2026 SET status = 'ACTIVE' WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close(); log_soul_action("APPROVE", f"Activated PBE-ID: {uid}")
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/suspend/<uid>")
def suspend_cmd(uid):
    if session.get('role') != 'ADMIN': abort(403)
    conn = get_db(); cur = conn.cursor(); cur.execute("UPDATE pbe_registry_2026 SET status = 'SUSPENDED' WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close(); log_soul_action("SUSPEND", f"Suspended PBE-ID: {uid}")
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/unsuspend/<uid>")
def unsuspend_cmd(uid):
    if session.get('role') != 'ADMIN': abort(403)
    conn = get_db(); cur = conn.cursor(); cur.execute("UPDATE pbe_registry_2026 SET status = 'ACTIVE' WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close(); log_soul_action("UNSUSPEND", f"Restored PBE-ID: {uid}")
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/renew/<uid>")
def renew_cmd(uid):
    if session.get('role') != 'ADMIN': abort(403)
    conn = get_db(); cur = conn.cursor(); cur.execute("UPDATE pbe_registry_2026 SET expiry_date = expiry_date + INTERVAL '2 years' WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close(); log_soul_action("RENEW", f"Extended license for {uid}")
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/delete/<uid>")
def delete_cmd(uid):
    if session.get('role') != 'ADMIN': abort(403)
    conn = get_db(); cur = conn.cursor(); cur.execute("DELETE FROM pbe_registry_2026 WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close(); log_soul_action("DELETE", f"Purged PBE-ID: {uid}")
    return redirect(url_for('admin_dashboard'))

# --- ROBOT MAPPING LOGIC ---
@app.route("/admin/print-id/<pbe_uid>")
def print_id(pbe_uid):
    if not session.get('role'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_registry_2026 WHERE pbe_uid = %s", (pbe_uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    if not w: abort(404)
    
    log_soul_action("PRINT", f"Printed ID for {pbe_uid}")
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(3.375*inch, 2.125*inch))
    
    tpl_path = os.path.join(app.root_path, 'static', 'ID TEMPLATE.png') 
    if os.path.exists(tpl_path): 
        c.drawImage(tpl_path, 0, 0, width=3.375*inch, height=2.125*inch)
    
    if w[11]: # photo_url from Cloudinary is now index 11
        try: 
            profile_img = ImageReader(w[11]) 
            c.saveState()
            c.setFillAlpha(0.2)
            c.drawImage(profile_img, 0.15*inch, 0.2*inch, width=0.6*inch, height=0.75*inch)
            c.restoreState()
            c.drawImage(profile_img, 2.3*inch, 0.55*inch, width=0.9*inch, height=1.1*inch)
        except: pass

    c.setFont("Helvetica-Bold", 8); c.setFillColor(colors.black)
    c.drawString(0.85*inch, 1.65*inch, f"{w[2]} {w[1]}") # Firstname Surname
    c.setFont("Helvetica", 7)
    c.drawString(0.85*inch, 1.45*inch, f"DEPT: {w[7]}")
    c.drawString(0.85*inch, 1.30*inch, f"RANK: {w[6]}")
    c.setFont("Helvetica-Bold", 7)
    c.drawString(0.85*inch, 1.10*inch, f"ID: {w[4]}")
    c.drawString(0.85*inch, 0.95*inch, f"LIC: {w[5]}")
    
    qr_code = qr.QrCodeWidget(f"{request.url_root}verify/{w[4]}")
    bounds = qr_code.getBounds(); d = Drawing(40, 40, transform=[40./(bounds[2]-bounds[0]),0,0,40./(bounds[3]-bounds[1]),0,0])
    d.add(qr_code); d.drawOn(c, 1.3*inch, 0.15*inch)
    
    c.showPage(); c.save(); buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=False, download_name=f"{w[4]}_ID.pdf")

# --- 8. ENROLLMENT & GHANA CARD ---
@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        otp = request.form.get('otp')
        conn = get_db(); cur = conn.cursor(); cur.execute("SELECT id FROM pbe_registry_2026 WHERE otp_code = %s", (otp,))
        if cur.fetchone():
            fname, sname = request.form.get('firstname').upper().replace(" ", "_"), request.form.get('surname').upper().replace(" ", "_")
            photo = cloudinary.uploader.upload(request.files['photo'], public_id=f"PBE_PP_{fname}_{sname}")
            ghana_card = cloudinary.uploader.upload(request.files['ghana_card_img'], public_id=f"PBE_GHANACARD_{fname}_{sname}")
            
            uid, lic = generate_15_char(fname), generate_15_char(sname)
            
            cur.execute("""UPDATE pbe_registry_2026 SET surname=%s, firstname=%s, dob=%s, pbe_uid=%s, pbe_license=%s,
                        issuance_date=%s, expiry_date=%s, rank=%s, department=%s, photo_url=%s, ghana_card_url=%s, 
                        email=%s, ghana_card_no=%s, status='PENDING', region=%s, station=%s WHERE otp_code=%s""",
                        (request.form.get('surname').upper(), fname, request.form.get('dob'), uid, lic,
                        datetime.date.today(), datetime.date.today() + datetime.timedelta(days=730),
                        request.form.get('rank'), request.form.get('department'), photo['secure_url'], ghana_card['secure_url'],
                        request.form.get('email'), request.form.get('ghana_card_no'), request.form.get('region'), request.form.get('station'), otp))
            conn.commit(); cur.close(); conn.close()
            # PERFECTLY ISOLATED SUCCESS SCREEN. NO DASHBOARD ACCESS.
            return "<div style='text-align:center; padding:100px; font-family:sans-serif;'><h1>REGISTRATION SUBMITTED ✅</h1><p style='font-size:20px; font-weight:bold; color:#495057;'>The office is going to respond in 3 working days.</p></div>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="section-card" style="max-width:500px; margin: auto;">
            <h3>ENROLLMENT FORM</h3>
            <form method="POST" enctype="multipart/form-data">
                <input name="otp" placeholder="OTP from SMS" style="width:100%; padding:12px; margin:5px 0; box-sizing:border-box;" required>
                <input name="surname" placeholder="Surname" style="width:100%; padding:12px; margin:5px 0; box-sizing:border-box;" required>
                <input name="firstname" placeholder="First Name" style="width:100%; padding:12px; margin:5px 0; box-sizing:border-box;" required>
                <input name="dob" placeholder="Date of Birth (e.g. 01/Jan/1990)" style="width:100%; padding:12px; margin:5px 0; box-sizing:border-box;" required>
                <input name="email" type="email" placeholder="Email Address" style="width:100%; padding:12px; margin:5px 0; box-sizing:border-box;" required>
                <input name="ghana_card_no" placeholder="Ghana Card ID Number" style="width:100%; padding:12px; margin:5px 0; box-sizing:border-box;" required>
                <select name="region" style="width:100%; padding:12px; margin:5px 0; box-sizing:border-box;">
                    {% for r in regions %}<option value="{{r}}">{{r}}</option>{% endfor %}
                </select>
                <select name="department" style="width:100%; padding:12px; margin:5px 0; box-sizing:border-box;">
                    {% for g in guilds %}<option value="{{g}}">{{g}}</option>{% endfor %}
                </select>
                <input name="rank" placeholder="Job Title" style="width:100%; padding:12px; margin:5px 0; box-sizing:border-box;" required>
                <p style="font-size:12px; margin-bottom:2px; font-weight:bold;">Passport Photo:</p>
                <input type="file" name="photo" style="margin-bottom:10px;" required>
                <p style="font-size:12px; margin-bottom:2px; font-weight:bold;">Ghana Card Image:</p>
                <input type="file" name="ghana_card_img" style="margin-bottom:10px;" required>
                <button class="btn-cmd bg-blue" style="width:100%; padding:15px; margin-top:10px;">SUBMIT REGISTRY</button>
            </form>
        </div>
    """), guilds=PBE_GUILDS, regions=GHANA_REGIONS)

# --- 9. SECURITY, INVITE & AUDIT ---
@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def admin_login():
    ip = request.remote_addr
    if is_blacklisted(ip): return "<div style='text-align:center; padding:50px; font-family:sans-serif;'><h1>403: SYSTEM ACCESS REVOKED</h1><p>IP locked due to unauthorized attempts.</p></div>"

    if request.method == 'POST':
        pwd = request.form.get('password')
        if pwd == ADMIN_PASSWORD: 
            session['role'] = 'ADMIN'
            log_soul_action("LOGIN", "Admin Access Granted")
            return redirect(url_for('admin_dashboard'))
        elif pwd == SUPERVISOR_PASSWORD: 
            session['role'] = 'SUPERVISOR'
            log_soul_action("LOGIN", "Supervisor Access Granted")
            return redirect(url_for('admin_dashboard'))
        else:
            blacklist_ip(ip)
            log_soul_action("SECURITY ALERT", f"Intruder Blocked from IP: {ip}")
            return redirect(url_for('admin_login'))

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="section-card" style="max-width:400px; margin:auto; text-align:center;">
            <h3>SYSTEM LOCK</h3>
            <form method="POST">
                <input type="password" name="password" style="width:100%; padding:12px; margin-bottom:15px; box-sizing:border-box;" required>
                <button class="btn-cmd bg-navy" style="width:100%; padding:15px;">UNLOCK</button>
            </form>
        </div>
    """))

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if not session.get('role'): return redirect(url_for('admin_login'))
    if request.method == 'POST':
        otp = str(random.randint(111111, 999999))
        phone = request.form.get('phone')
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM pbe_registry_2026 WHERE phone_no = %s AND status = 'PENDING'", (phone,))
        cur.execute("INSERT INTO pbe_registry_2026 (phone_no, otp_code) VALUES (%s, %s)", (phone, otp))
        conn.commit(); cur.close(); conn.close()
        requests.post("https://sms.arkesel.com/api/v2/sms/send", json={"sender": "PBE_OTP", "message": f"PBE: Use OTP {otp} to register: {request.url_root}register", "recipients": [phone]}, headers={"api-key": ARKESEL_API_KEY})
        log_soul_action("INVITE", f"OTP {otp} sent to {phone}")
        return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="section-card" style="max-width:400px; margin:auto;">
            <h3>+ SEND INVITE</h3>
            <form method="POST">
                <input name="phone" placeholder="+233..." style="width:100%; padding:12px; margin-bottom:15px; box-sizing:border-box;" required>
                <button class="btn-cmd bg-blue" style="width:100%; padding:15px;">SEND OTP LINK</button>
            </form>
        </div>
    """))

@app.route("/admin/audit")
def view_audit():
    if session.get('role') != 'ADMIN': abort(403)
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT timestamp, action, actor, details, ip_address FROM pbe_soul_audit ORDER BY id DESC LIMIT 100")
    logs = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="section-card">
            <div class="section-title">📜 SOUL AUDIT LOGS</div>
            <div style="font-family:monospace; font-size:12px; max-height:500px; overflow-y:auto; background:#1e1e1e; color:#00ff00; padding:15px; border-radius:8px;">
                {% for l in logs %}
                <div style="margin-bottom:8px; border-bottom:1px solid #333; padding-bottom:5px;">
                    <span style="color:#888;">[{{ l[0].strftime('%Y-%m-%d %H:%M') }}]</span> 
                    <span style="color:#ffc107;">[{{ l[2] }}]</span> 
                    <b>{{ l[1] }}</b>: {{ l[3] }} <span style="color:#888; float:right;">(IP: {{ l[4] }})</span>
                </div>
                {% endfor %}
            </div>
            <a href="/admin-dashboard" class="btn-cmd bg-navy" style="margin-top:20px; padding:10px;">BACK TO DASHBOARD</a>
        </div>
    """), logs=logs)

@app.route("/admin/alerts")
def view_alerts():
    if not session.get('role'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_registry_2026 WHERE expiry_date <= CURRENT_DATE + INTERVAL '30 days'")
    alerts = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="section-card">
            <div class="section-title">🔔 RENEWAL ALERTS</div>
            {% for a in alerts %}
            <div style="padding:10px; border-bottom:1px solid #eee; font-size:13px;">
                <b>{{ a[1] }} {{ a[2] }}</b> (ID: {{ a[6] }}) - <span style="color:red;">Expires: {{ a[9] }}</span>
            </div>
            {% endfor %}
            {% if not alerts %}<p>No upcoming renewals.</p>{% endif %}
            <a href="/admin-dashboard" class="btn-cmd bg-navy" style="margin-top:20px; padding:10px;">BACK</a>
        </div>
    """), alerts=alerts)

@app.route("/")
def index(): return redirect(url_for('admin_login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
