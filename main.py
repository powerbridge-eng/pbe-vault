import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime, csv
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session, abort
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO, StringIO

# --- 1. CORE CONFIGURATION ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY")
ARKESEL_SENDER_ID = "PBE_OFFICE"
ADMIN_PASSWORD = "PBE-Global-2026"
OFFICE_LINE = "+233541803057"

app = Flask(__name__)
app.secret_key = "PBE_GLOBAL_INFRA_2026"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# --- 2. THE PBE WORLD MATRIX (Departments) ---
PBE_GUILDS = [
    "Electrical Engineering", "Solar & Energy", "Plumbing & Hydraulics", 
    "Masonry & Construction", "Mechanical & Auto", "Media Team (DDS)", 
    "CCTV & Security", "ICT & Software", "HVAC & Cooling", "General Technical"
]

GHANA_REGIONS = {
    "Greater Accra": "Accra", "Ashanti": "Kumasi", "Western": "Takoradi", 
    "Central": "Cape Coast", "Eastern": "Koforidua", "Volta": "Ho", 
    "Northern": "Tamale", "Upper East": "Bolgatanga", "Upper West": "Wa", 
    "Bono": "Sunyani", "Bono East": "Techiman", "Ahafo": "Goaso", 
    "Savannah": "Damongo", "North East": "Nalerigu", "Oti": "Dambai", "Western North": "Wiawso"
}

# --- 3. DATABASE & SOUL AUDIT ---
def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_master_registry (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT,
            gender TEXT, nationality TEXT, pbe_uid TEXT UNIQUE, pbe_license TEXT UNIQUE,
            issuance_date DATE, expiry_date DATE, rank TEXT, department TEXT,
            phone_no TEXT, photo_url TEXT, ghana_card_url TEXT, status TEXT DEFAULT 'PENDING',
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
    device = f"{request.user_agent.platform} | {request.user_agent.browser}"
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_soul_audit (action, details, ip_address, device_info) VALUES (%s, %s, %s, %s)",
                (action, details, request.remote_addr, device))
    conn.commit(); cur.close(); conn.close()

with app.app_context():
    init_db()

# --- 4. EXECUTIVE UI DESIGN ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
    <title>PBE Command Center</title>
    <style>
        :root { --navy: #0a192f; --gold: #ffcc00; --red: #e63946; --green: #2a9d8f; --slate: #f1f5f9; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--slate); margin: 0; color: #1e293b; padding-bottom: 80px; }
        
        .app-header { background: var(--navy); color: white; padding: 20px; text-align: center; border-bottom: 5px solid var(--gold); position: sticky; top: 0; z-index: 1000; }
        .logo-img { height: 60px; filter: drop-shadow(0 2px 5px rgba(0,0,0,0.5)); }
        
        .container { max-width: 1200px; margin: auto; padding: 15px; }
        
        /* Dashboard Layers */
        .search-bar-container { margin-bottom: 20px; display: flex; gap: 10px; }
        .search-input { flex: 1; padding: 15px; border-radius: 12px; border: 1px solid #cbd5e1; font-size: 16px; outline: none; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        
        .layer-card { background: white; border-radius: 16px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }
        .layer-title { font-size: 13px; font-weight: 800; color: #64748b; text-transform: uppercase; margin-bottom: 15px; border-left: 4px solid var(--navy); padding-left: 10px; }
        
        /* Departmental Matrix Grid */
        .guild-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; }
        .guild-btn { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 15px 5px; text-align: center; text-decoration: none; color: var(--navy); font-size: 11px; font-weight: 700; transition: 0.3s; }
        .guild-btn:hover, .guild-active { background: var(--navy); color: var(--gold); border-color: var(--gold); }
        
        /* Tables */
        .worker-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .worker-table th { text-align: left; padding: 12px; color: #64748b; border-bottom: 2px solid #f1f5f9; }
        .worker-table td { padding: 15px 12px; border-bottom: 1px solid #f1f5f9; }
        
        .btn-small { padding: 8px 12px; border-radius: 8px; font-size: 11px; font-weight: bold; text-decoration: none; color: white; display: inline-block; border: none; cursor: pointer; }
        .bg-navy { background: var(--navy); } .bg-red { background: var(--red); } .bg-green { background: var(--green); }
        
        .fab { position: fixed; bottom: 25px; right: 25px; width: 60px; height: 60px; background: var(--navy); color: var(--gold); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 30px; box-shadow: 0 10px 20px rgba(0,0,0,0.2); text-decoration: none; z-index: 1001; border: 2px solid var(--gold); }
        
        .status-dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 5px; }
    </style>
</head>
<body>
    <div class="app-header">
        <img src="{{ url_for('static', filename='logo.png') }}" class="logo-img" onerror="this.style.display='none'">
        <div style="font-size: 18px; font-weight: 900; letter-spacing: 1px;">PBE COMMAND CENTER</div>
    </div>
    
    <div class="container">
        {% block content %}{% endblock %}
    </div>
    
    <a href="/admin/invite" class="fab">＋</a>

    <script>
        function filterWorkers() {
            let input = document.getElementById('globalSearch').value.toUpperCase();
            let rows = document.querySelectorAll('.worker-row');
            rows.forEach(row => {
                let text = row.innerText.toUpperCase();
                row.style.display = text.includes(input) ? '' : 'none';
            });
        }
    </script>
</body>
</html>
"""

# --- 5. ROUTES ---

@app.route("/")
def index(): return redirect(url_for('login'))

@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            log_soul_action("SECURITY_LOGIN", "Admin Portal Access")
            return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="layer-card" style="max-width:350px; margin: 80px auto; text-align:center;"><h3>SYSTEM LOCK</h3><form method="POST"><input type="password" name="password" style="width:100%; padding:15px; margin-bottom:10px; border-radius:10px; border:1px solid #ddd;" placeholder="Master Key" required><button class="btn-small bg-navy" style="width:100%; padding:15px;">AUTHENTICATE</button></form></div>'))

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    # Live Balance
    balance = "..."
    try:
        r = requests.get("https://sms.arkesel.com/api/v2/clients/balance", headers={"api-key": ARKESEL_API_KEY}, timeout=2)
        balance = f"{r.json().get('data', {}).get('available_balance', '0.00')} GHS"
    except: pass

    conn = get_db(); cur = conn.cursor()
    
    # Filters
    dept_filter = request.args.get('dept')
    if dept_filter:
        cur.execute("SELECT * FROM pbe_master_registry WHERE department = %s ORDER BY id DESC", (dept_filter,))
    else:
        cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    
    workers = cur.fetchall(); cur.close(); conn.close()

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <div class="search-bar-container">
            <input type="text" id="globalSearch" class="search-input" placeholder="Search by Name, ID, Phone or Rank..." onkeyup="filterWorkers()">
            <div class="layer-card" style="margin:0; padding:10px 20px; display:flex; align-items:center; font-weight:bold;">
                SMS: {balance}
            </div>
        </div>

        <div class="layer-card">
            <div class="layer-title">🛠️ Technical Guilds (Grouping)</div>
            <div class="guild-grid">
                <a href="/admin-dashboard" class="guild-btn {{{{ 'guild-active' if not current_dept }}}}">ALL SECTORS</a>
                {{% for g in guilds %}}
                <a href="/admin-dashboard?dept={{{{ g }}}}" class="guild-btn {{{{ 'guild-active' if current_dept == g }}}}">{{{{ g.upper() }}}}</a>
                {{% endfor %}}
            </div>
        </div>

        <div class="layer-card">
            <div class="layer-title">👥 {{{{ current_dept or 'GLOBAL' }}}} REGISTRY</div>
            <div style="overflow-x:auto;">
                <table class="worker-table">
                    <thead>
                        <tr><th>PBE-ID</th><th>NAME</th><th>RANK / DEPT</th><th>STATUS</th><th>COMMANDS</th></tr>
                    </thead>
                    <tbody>
                        {{% for w in workers %}}
                        <tr class="worker-row">
                            <td><b>{{{{ w[6] or 'PENDING' }}}}</b></td>
                            <td>{{{{ w[1] }}}}, {{{{ w[2] }}}}</td>
                            <td><small>{{{{ w[10] }}}}</small><br><b>{{{{ w[11] }}}}</b></td>
                            <td>
                                {{% set expiry = w[9] %}}
                                {{% if w[15] == 'ACTIVE' %}}
                                    <span class="status-dot" style="background:var(--green);"></span>Active
                                {{% else %}}
                                    <span class="status-dot" style="background:var(--red);"></span>Pending
                                {{% endif %}}
                            </td>
                            <td>
                                <a href="/admin/print-id/{{{{ w[6] }}}}" class="btn-small bg-navy">Print</a>
                                <a href="/admin/delete/{{{{ w[0] }}}}" class="btn-small bg-red" onclick="return confirm('Erase from matrix?')">X</a>
                            </td>
                        </tr>
                        {{% endfor %}}
                    </tbody>
                </table>
            </div>
        </div>
    """), guilds=PBE_GUILDS, workers=workers, current_dept=dept_filter)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        otp = request.form.get('otp')
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT id FROM pbe_master_registry WHERE otp_code = %s", (otp,))
        if cur.fetchone():
            fname = request.form.get('firstname').upper().replace(" ", "_")
            sname = request.form.get('surname').upper().replace(" ", "_")
            
            # Critical: Named Storage for searching
            p_id = f"PBE_PP_{fname}_{sname}"
            g_id = f"PBE_GHA_{fname}_{sname}"
            
            photo = cloudinary.uploader.upload(request.files['photo'], public_id=p_id)
            ghana_card = cloudinary.uploader.upload(request.files['ghana_card'], public_id=g_id)
            
            uid = f"PBE-{fname[:3]}-{''.join(random.choices(string.digits, k=6))}"
            lic = f"LIC-{''.join(random.choices(string.digits, k=10))}"
            
            cur.execute("""UPDATE pbe_master_registry SET surname=%s, firstname=%s, dob=%s, gender=%s,
                        pbe_uid=%s, pbe_license=%s, issuance_date=%s, expiry_date=%s, rank=%s, department=%s,
                        photo_url=%s, ghana_card_url=%s, status='PENDING', region=%s, station=%s WHERE otp_code=%s""",
                        (request.form.get('surname').upper(), fname, request.form.get('dob'), request.form.get('gender'),
                        uid, lic, datetime.date.today(), datetime.date.today() + datetime.timedelta(days=730),
                        request.form.get('rank'), request.form.get('department'), photo['secure_url'], 
                        ghana_card['secure_url'], request.form.get('region'), request.form.get('station'), otp))
            conn.commit(); cur.close(); conn.close()
            return "<div style='text-align:center; padding:100px;'><h1>REGISTRATION SENT ✅</h1><p>Processed in 3 working days.</p></div>"

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="layer-card" style="max-width:500px; margin: auto;">
            <h3>PERSONNEL ENROLLMENT</h3>
            <form method="POST" enctype="multipart/form-data">
                <input name="otp" placeholder="OTP" style="width:100%; padding:12px; margin:5px 0;" required>
                <input name="surname" placeholder="Surname" style="width:100%; padding:12px; margin:5px 0;" required>
                <input name="firstname" placeholder="First Name" style="width:100%; padding:12px; margin:5px 0;" required>
                <select name="department" style="width:100%; padding:12px; margin:5px 0;">
                    {% for g in guilds %}<option value="{{g}}">{{g}}</option>{% endfor %}
                </select>
                <input name="rank" placeholder="Specific Job Title (e.g. Master Mason)" style="width:100%; padding:12px; margin:5px 0;" required>
                <select name="region" style="width:100%; padding:12px; margin:5px 0;">
                    {% for r in regions %}<option value="{{r}}">{{r}}</option>{% endfor %}
                </select>
                <input name="station" placeholder="Station" style="width:100%; padding:12px; margin:5px 0;">
                <p style="font-size:11px; color:gray;">Passport Photo & Ghana Card Required:</p>
                <input type="file" name="photo" required>
                <input type="file" name="ghana_card" required>
                <button class="btn-small bg-navy" style="width:100%; padding:15px; margin-top:15px;">SUBMIT TO COMMAND</button>
            </form>
        </div>
    """), guilds=PBE_GUILDS, regions=GHANA_REGIONS.keys())

# --- 6. PRINT ENGINE (TEMPLATE MATCH) ---
@app.route("/admin/print-id/<pbe_uid>")
def print_id(pbe_uid):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT * FROM pbe_master_registry WHERE pbe_uid = %s", (pbe_uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    
    buffer = BytesIO(); c = canvas.Canvas(buffer, pagesize=(3.375*inch, 2.125*inch))
    tpl = os.path.join(app.root_path, 'static', 'Power Bridge Engineering ID Identity Template.png')
    if os.path.exists(tpl): c.drawImage(tpl, 0, 0, width=3.375*inch, height=2.125*inch)
    if w[13]: c.drawImage(w[13], 0.18*inch, 0.55*inch, width=1.02*inch, height=1.22*inch)

    c.setFont("Helvetica-Bold", 7); c.setFillColor(colors.black)
    c.drawString(1.35*inch, 1.55*inch, f"{w[1]}")
    c.drawString(1.35*inch, 1.40*inch, f"{w[2]}")
    c.drawString(1.35*inch, 1.25*inch, f"{w[6]}")
    
    qr_code = qr.QrCodeWidget(f"{request.url_root}verify/{w[6]}")
    bounds = qr_code.getBounds(); d = Drawing(40, 40, transform=[40./(bounds[2]-bounds[0]),0,0,40./(bounds[3]-bounds[1]),0,0])
    d.add(qr_code); d.drawOn(c, 2.8*inch, 0.15*inch)
    
    c.showPage(); c.save(); buffer.seek(0)
    log_soul_action("PRINT_ID", f"ID generated for {w[2]}")
    return send_file(buffer, mimetype='application/pdf')

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == 'POST':
        phone, otp = request.form.get('phone'), str(random.randint(111111, 999999))
        conn = get_db(); cur = conn.cursor(); cur.execute("INSERT INTO pbe_master_registry (phone_no, otp_code) VALUES (%s, %s)", (phone, otp)); conn.commit(); cur.close(); conn.close()
        requests.post("https://sms.arkesel.com/api/v2/sms/send", json={"sender": ARKESEL_SENDER_ID, "message": f"PBE COMMAND: Your enrollment code is {otp}. Fill form at {request.url_root}register", "recipients": [phone]}, headers={"api-key": ARKESEL_API_KEY})
        return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="layer-card" style="max-width:400px; margin:auto;"><h3>SEND ENROLLMENT INVITE</h3><form method="POST"><input name="phone" placeholder="233..." style="width:100%; padding:12px; margin-bottom:10px;"><button class="btn-small bg-navy" style="width:100%; padding:15px;">SEND SMS</button></form></div>'))

@app.route("/admin/delete/<int:id>")
def delete_worker(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("DELETE FROM pbe_master_registry WHERE id=%s", (id,)); conn.commit(); cur.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
