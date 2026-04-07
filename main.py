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
SUPERVISOR_PASSWORD = "PBE_Secure_2026"

app = Flask(__name__)
app.secret_key = "PBE_SUPREME_SOVEREIGN_2026_FINAL_STABLE"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    for i in range(5):
        try:
            return psycopg2.connect(DATABASE_URL)
        except:
            time.sleep(2)
    return None

# --- 2. SECURITY & SOUL AUDIT ---
def log_action(action, details):
    actor = session.get('role', 'SYSTEM')
    conn = get_db()
    if conn:
        try:
            cur = conn.cursor()
            device = f"{request.user_agent.platform} | {request.user_agent.browser}"
            cur.execute("""INSERT INTO pbe_soul_audit (action, actor, details, ip, device) 
                           VALUES (%s, %s, %s, %s, %s)""",
                        (action, actor, details, request.remote_addr, device))
            conn.commit(); cur.close(); conn.close()
        except: pass

def init_system():
    conn = get_db()
    if not conn: return
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS pbe_master_registry (id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT, gender TEXT, pbe_uid TEXT UNIQUE, pbe_license TEXT UNIQUE, rank TEXT, department TEXT, phone_no TEXT UNIQUE, email TEXT UNIQUE, ghana_card TEXT UNIQUE, photo_url TEXT, status TEXT DEFAULT 'PENDING', otp_code TEXT, region TEXT, issuance_date DATE, expiry_date DATE);")
    cur.execute("CREATE TABLE IF NOT EXISTS pbe_soul_audit (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, action TEXT, actor TEXT, details TEXT, ip TEXT, device TEXT);")
    cur.execute("CREATE TABLE IF NOT EXISTS pbe_blacklist (id SERIAL PRIMARY KEY, ip_address TEXT UNIQUE, locked_until TIMESTAMP);")
    conn.commit(); cur.close(); conn.close()

with app.app_context(): init_system()

def is_blacklisted(ip):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT locked_until FROM pbe_blacklist WHERE ip_address = %s", (ip,))
    res = cur.fetchone()
    cur.close(); conn.close()
    return True if res and res[0] > datetime.datetime.now() else False

def blacklist_ip(ip):
    lock_time = datetime.datetime.now() + datetime.timedelta(hours=72)
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_blacklist (ip_address, locked_until) VALUES (%s, %s) ON CONFLICT (ip_address) DO UPDATE SET locked_until = %s", (ip, lock_time, lock_time))
    conn.commit(); cur.close(); conn.close()

# --- 3. PBE WORLD MATRIX ---
GH_REGIONS = ["Greater Accra", "Ashanti", "Western", "Central", "Eastern", "Volta", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Oti", "Western North"]
PBE_GUILDS = ["ELECTRICAL", "SOLAR", "PLUMBING", "MASONRY", "MECHANICAL", "PBE TV", "CCTV", "ICT", "HVAC", "FASHION", "GENERAL"]

# --- 4. EXECUTIVE UI ---
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
        .btn-6 { padding: 8px 12px; border-radius: 6px; color: white; text-decoration: none; font-size: 9px; font-weight: 800; margin: 2px; display: inline-block; border: none; cursor: pointer; }
        .bg-navy { background: #1e293b; } .bg-wa { background: #22c55e; } .bg-red { background: #ef4444; } .bg-gold { background: var(--pbe-gold); color: #000; } .bg-sus { background: #64748b; }
        .search-bar { width: 100%; padding: 15px; border-radius: 10px; border: 1px solid #ddd; font-size: 16px; box-sizing: border-box; }
        .fab-zone { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 12px; z-index: 1000; }
        .fab { width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; text-decoration: none; border: 2px solid var(--pbe-gold); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
        .fab-invite { background: #333; color: var(--pbe-gold); }
        .fab-audit { background: var(--pbe-grey); color: white; }
    </style>
</head>
<body>
    <div class="logo-standalone"><img src="{{ url_for('static', filename='logo.png') }}" class="logo-img" onerror="this.src='https://via.placeholder.com/100?text=PBE'"></div>
    <div class="nav-bar">PBE SUPREME COMMAND CENTER</div>
    <div class="container">{% block content %}{% endblock %}</div>
    <script>
        function runSearch() {
            let filter = document.getElementById('gSearch').value.toUpperCase();
            document.querySelectorAll('.worker-row').forEach(row => {
                row.style.display = row.innerText.toUpperCase().includes(filter) ? '' : 'none';
            });
        }
    </script>
</body>
</html>
"""

# --- 5. DASHBOARD ---
@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('role'): return redirect(url_for('admin_login'))
    role = session.get('role')
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
        <div style="display:flex; gap:10px; margin-bottom:20px; align-items:center;">
            <input type="text" id="gSearch" class="search-bar" placeholder="Search Personnel Registry..." onkeyup="runSearch()">
            {{% if role == 'ADMIN' %}}
            <a href="https://cloudinary.com/console" target="_blank" class="btn-6 bg-navy" style="white-space:nowrap; padding:15px;">☁️ CLOUDINARY</a>
            {{% endif %}}
        </div>
        <div class="layer-box">
            <div style="font-size:11px; font-weight:800; margin-bottom:10px;">🌍 GLOBAL ENGINEERING METRIC (16 REGIONS)</div>
            <div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap:10px;">
                {{% for reg, count in stats.items() %}}
                <div style="background:#f8f9fa; border:1px solid #ddd; border-radius:8px; padding:10px; font-size:10px; font-weight:700;">{{{{reg}}}}: <b style="color:red; float:right;">{{{{count}}}}</b></div>
                {{% endfor %}}
            </div>
        </div>
        <div class="layer-box">
            <table style="width:100%; border-collapse:collapse; font-size:11px;">
                <thead><tr style="background:#f1f1f1;"><th style="padding:10px; text-align:left;">LICENSE / ID</th><th style="text-align:left;">NAME</th><th style="text-align:left;">STATUS</th><th style="text-align:left;">COMMANDS</th></tr></thead>
                <tbody>
                    {{% for w in workers %}}
                    <tr class="worker-row" style="border-bottom:1px solid #eee;">
                        <td style="padding:12px;"><b>{{{{ w[6] }}}}</b><br><small>ID: {{{{ w[5] }}}}</small></td>
                        <td>{{{{ w[1] }}}} {{{{ w[2] }}}}</td>
                        <td><span style="color:{{ 'green' if w[13] == 'ACTIVE' else 'red' }}; font-weight:bold;">{{{{ w[13] }}}}</span></td>
                        <td>
                            <a href="/print/{{{{w[5]}}}}" class="btn-6 bg-navy">PRINT</a>
                            <a href="https://wa.me/{{{{ w[9] }}}}" target="_blank" class="btn-6 bg-wa">WA</a>
                            {{% if role == 'ADMIN' %}}
                            <a href="/approve/{{{{w[5]}}}}" class="btn-6 bg-wa">APPROVE</a>
                            <a href="/suspend/{{{{w[5]}}}}" class="btn-6 bg-sus">SUSPEND</a>
                            <a href="/renew/{{{{w[5]}}}}" class="btn-6 bg-gold">RENEW</a>
                            <a href="/delete/{{{{w[5]}}}}" class="btn-6 bg-red">DELETE</a>
                            {{% endif %}}
                        </td>
                    </tr>
                    {{% endfor %}}
                </tbody>
            </table>
        </div>
        <div class="fab-zone">
            <a href="#" class="fab fab-alert" title="Alerts">🔔 {expiry_alerts}</a>
            {{% if role == 'ADMIN' %}}<a href="/admin/audit" class="fab fab-audit">📜</a>{{% endif %}}
            <a href="/admin/invite" class="fab fab-invite">+</a>
        </div>
    """), stats=stats, workers=workers, role=role, expiry_alerts=expiry_alerts))

# --- 6. COMMANDS & ENROLLMENT ---
@app.route("/approve/<uid>")
def approve_cmd(uid):
    if session.get('role') != 'ADMIN': abort(403)
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE pbe_master_registry SET status = 'ACTIVE' WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close()
    log_action("APPROVE", f"Activated {uid}")
    return redirect(url_for('admin_dashboard'))

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        otp = request.form.get('otp')
        first, last = request.form.get('firstname').upper(), request.form.get('surname').upper()
        photo = cloudinary.uploader.upload(request.files['photo'], public_id=f"PBE_PASSPORT_{last}_{first}")
        id_img = cloudinary.uploader.upload(request.files['ghana_card_img'], public_id=f"PBE_GHANACARD_{last}_{first}")
        uid = f"PBE{datetime.datetime.now().strftime('%y%m')}{first[:3]}{''.join(random.choices(string.digits, k=4))}"
        lic = f"PBELIC{last[:3]}{''.join(random.choices(string.digits, k=6))}"
        conn = get_db(); cur = conn.cursor()
        cur.execute("""UPDATE pbe_master_registry SET surname=%s, firstname=%s, pbe_uid=%s, pbe_license=%s, rank=%s, department=%s, email=%s, photo_url=%s, ghana_card=%s, region=%s, issuance_date=%s, expiry_date=%s, status='PENDING' WHERE otp_code=%s""",
                   (last, first, uid, lic, request.form.get('rank'), request.form.get('department'), request.form.get('email'), photo['secure_url'], request.form.get('ghana_card_no'), request.form.get('region'), datetime.date.today(), datetime.date.today() + datetime.timedelta(days=730), otp))
        conn.commit(); cur.close(); conn.close(); return "<h1>REGISTRY SUBMITTED ✅</h1>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """<div class="layer-box" style="max-width:500px; margin:auto;"><h3>ENROLLMENT</h3><form method="POST" enctype="multipart/form-data"><input name="otp" placeholder="OTP" required style="width:100%; padding:10px; margin-bottom:10px;"><input name="firstname" placeholder="First Name" required style="width:100%; padding:10px; margin-bottom:10px;"><input name="surname" placeholder="Surname" required style="width:100%; padding:10px; margin-bottom:10px;"><input name="ghana_card_no" placeholder="Ghana Card No" required style="width:100%; padding:10px; margin-bottom:10px;"><select name="region" style="width:100%; padding:10px; margin-bottom:10px;">{% for r in regions %}<option value="{{r}}">{{r}}</option>{% endfor %}</select><select name="department" style="width:100%; padding:10px; margin-bottom:10px;">{% for g in guilds %}<option value="{{g}}">{{g}}</option>{% endfor %}</select><input name="rank" placeholder="Rank" required style="width:100%; padding:10px; margin-bottom:10px;"><input name="email" type="email" placeholder="Email" required style="width:100%; padding:10px; margin-bottom:10px;"><p>Passport Photo:</p><input type="file" name="photo" required><p>Ghana Card Image:</p><input type="file" name="ghana_card_img" required><button class="btn-6 bg-navy" style="width:100%; margin-top:10px;">SUBMIT</button></form></div>"""), regions=GH_REGIONS, guilds=PBE_GUILDS))

@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def admin_login():
    ip = request.remote_addr
    if is_blacklisted(ip): return "<h1>403: ACCESS DENIED (72HR BLACKLIST)</h1>"
    if request.method == 'POST':
        pwd = request.form.get('password')
        if pwd == ADMIN_PASSWORD: session['role'] = 'ADMIN'; return redirect(url_for('admin_dashboard'))
        elif pwd == SUPERVISOR_PASSWORD: session['role'] = 'SUPERVISOR'; return redirect(url_for('admin_dashboard'))
        else: blacklist_ip(ip); log_action("SECURITY", f"Intruder blocked: {ip}"); return redirect(url_for('admin_login'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """<div class="layer-box" style="max-width:400px; margin:auto; text-align:center;"><h3>SYSTEM LOCK</h3><form method="POST"><input type="password" name="password" required><button class="btn-6 bg-navy">UNLOCK</button></form></div>"""))

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if not session.get('role'): return redirect(url_for('admin_login'))
    if request.method == 'POST':
        otp = str(random.randint(111111, 999999)); phone = request.form.get('phone'); conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM pbe_master_registry WHERE phone_no = %s AND status = 'PENDING'", (phone,))
        cur.execute("INSERT INTO pbe_master_registry (phone_no, otp_code) VALUES (%s, %s)", (phone, otp))
        conn.commit(); cur.close(); conn.close(); requests.post("https://sms.arkesel.com/api/v2/sms/send", json={"sender": "PBE_OTP", "message": f"PBE: Use OTP {otp} to register: {request.url_root}register", "recipients": [phone]}, headers={"api-key": ARKESEL_API_KEY})
        return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """<div class="layer-box"><h3>+ INVITE</h3><form method="POST"><input name="phone" placeholder="233..." required style="width:100%; padding:10px;"><button class="btn-6 bg-navy">SEND OTP</button></form></div>"""))

@app.route("/admin/audit")
def view_audit():
    if session.get('role') != 'ADMIN': abort(403)
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT timestamp, action, actor, details, ip FROM pbe_soul_audit ORDER BY id DESC LIMIT 50")
    logs = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """<div class="layer-box"><h3>📜 AUDIT LOGS</h3>{% for l in logs %}<div style="font-size:11px; border-bottom:1px solid #eee; padding:5px;">[{{ l[0].strftime('%H:%M') }}] {{ l[2] }}: {{ l[1] }}</div>{% endfor %}<a href="/admin-dashboard" class="btn-6 bg-navy">BACK</a></div>"""))

@app.route("/")
def index(): return redirect(url_for('admin_login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
