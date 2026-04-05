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
app.secret_key = "PBE_ABSOLUTE_FINAL_BUILD_2026"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# --- 2. THE PBE WORLD MATRIX ---
PBE_GUILDS = [
    "ELECTRICAL ENGINEERING", "SOLAR & ENERGY", "PLUMBING & HYDRAULICS", 
    "MASONRY & CONSTRUCTION", "MECHANICAL & AUTO", "PBE TV", 
    "CCTV & SECURITY", "ICT & SOFTWARE", "HVAC & COOLING", "GENERAL TECHNICAL"
]

GHANA_REGIONS = ["Greater Accra", "Ashanti", "Western", "Central", "Eastern", "Volta", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Oti", "Western North"]

# --- 3. INFRASTRUCTURE & SOUL TRACKER ---
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

# --- 4. 15-CHAR GENERATION ---
def generate_15_char(name):
    clean = re.sub(r'[^A-Z]', '', name.upper())
    part = clean[:6]
    needed = 15 - len(part)
    return f"{part}{''.join(random.choices(string.digits + string.ascii_uppercase, k=needed))}"

# --- 5. UI DESIGN ---
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
        .btn-cmd { padding: 8px 12px; border-radius: 6px; color: white; text-decoration: none; font-size: 10px; font-weight: bold; margin-right: 5px; display: inline-block; }
        .bg-blue { background: #007bff; } .bg-wa { background: #28a745; } .bg-red { background: #dc3545; }
        .fab { position: fixed; bottom: 30px; right: 30px; width: 65px; height: 65px; background: var(--navy); color: var(--gold); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); text-decoration: none; z-index: 1001; border: 2px solid var(--gold); }
    </style>
</head>
<body>
    <div class="header">
        <img src="{{ url_for('static', filename='logo.png') }}" class="logo" onerror="this.style.display='none'">
        <div style="font-size: 22px; font-weight: 900;">PBE COMMAND CENTER</div>
    </div>
    <div class="container">{% block content %}{% endblock %}</div>
    <a href="/admin/invite" class="fab">＋</a>
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

# --- 6. ROUTES ---

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    sms_live = "..."
    try:
        r = requests.get("https://sms.arkesel.com/api/v2/clients/balance", headers={"api-key": ARKESEL_API_KEY}, timeout=3)
        sms_live = f"{r.json().get('data', {}).get('available_balance', '0.00')} GHS"
    except: sms_live = "OFFLINE"

    conn = get_db(); cur = conn.cursor()
    dept = request.args.get('dept')
    if dept: cur.execute("SELECT * FROM pbe_master_registry WHERE department = %s ORDER BY id DESC", (dept,))
    else: cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <div class="search-container">
            <input type="text" id="globalSearch" class="search-bar" placeholder="Search Names, ID or License..." onkeyup="filterRegistry()">
            <div class="sms-balance">SMS: {sms_live}</div>
        </div>
        <div class="section-card">
            <div class="section-title">🛠️ TECHNICAL GUILDS</div>
            <div class="guild-grid">
                <a href="/admin-dashboard" class="guild-btn {{{{ 'guild-active' if not current_dept }}}}">GLOBAL</a>
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
                            <td>ID: <b>{{{{ w[6] }}}}</b><br>LIC: <small>{{{{ w[7] }}}}</small></td>
                            <td>{{{{ w[1] }}}}, {{{{ w[2] }}}}</td>
                            <td>{{{{ w[10] }}}}</td>
                            <td><b style="color:{{{{ '#28a745' if w[15]=='ACTIVE' else 'orange' }}}};">{{{{ w[15] }}}}</b></td>
                            <td>
                                <a href="/admin/print-id/{{{{ w[6] }}}}" class="btn-cmd bg-blue">Print</a>
                                <a href="https://wa.me/{{{{ w[12] }}}}" class="btn-cmd bg-wa" target="_blank">WA</a>
                                <a href="/admin/delete/{{{{ w[0] }}}}" class="btn-cmd bg-red" onclick="return confirm('Erase?')">X</a>
                            </td>
                        </tr>
                        {{% endfor %}}
                    </tbody>
                </table>
            </div>
        </div>
    """), guilds=PBE_GUILDS, workers=workers, current_dept=dept)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        otp = request.form.get('otp')
        conn = get_db(); cur = conn.cursor(); cur.execute("SELECT id FROM pbe_master_registry WHERE otp_code = %s", (otp,))
        if cur.fetchone():
            fname, sname = request.form.get('firstname').upper().replace(" ", "_"), request.form.get('surname').upper().replace(" ", "_")
            photo = cloudinary.uploader.upload(request.files['photo'], public_id=f"PBE_PP_{fname}_{sname}")
            
            # BOTH Credentials are now generated as 15-char Name-Mixes
            uid = generate_15_char(fname)
            lic = generate_15_char(sname)
            
            cur.execute("""UPDATE pbe_master_registry SET surname=%s, firstname=%s, dob=%s, pbe_uid=%s, pbe_license=%s,
                        issuance_date=%s, expiry_date=%s, rank=%s, department=%s, photo_url=%s, 
                        status='PENDING', region=%s, station=%s WHERE otp_code=%s""",
                        (request.form.get('surname').upper(), fname, request.form.get('dob'), uid, lic,
                        datetime.date.today(), datetime.date.today() + datetime.timedelta(days=730),
                        request.form.get('rank'), request.form.get('department'), photo['secure_url'], 
                        request.form.get('region'), request.form.get('station'), otp))
            conn.commit(); cur.close(); conn.close()
            return "<div style='text-align:center; padding:100px;'><h1>RECEIVED ✅</h1></div>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="section-card" style="max-width:500px; margin: auto;">
            <h3>ENROLLMENT</h3>
            <form method="POST" enctype="multipart/form-data">
                <input name="otp" placeholder="OTP" style="width:100%; padding:12px; margin:5px 0;" required>
                <input name="surname" placeholder="Surname" style="width:100%; padding:12px; margin:5px 0;" required>
                <input name="firstname" placeholder="First Name" style="width:100%; padding:12px; margin:5px 0;" required>
                <select name="department" style="width:100%; padding:12px; margin:5px 0;">
                    {% for g in guilds %}<option value="{{g}}">{{g}}</option>{% endfor %}
                </select>
                <input name="rank" placeholder="Job Title" style="width:100%; padding:12px; margin:5px 0;" required>
                <input type="file" name="photo" required>
                <button class="btn-cmd bg-blue" style="width:100%; padding:15px; margin-top:10px;">SUBMIT</button>
            </form>
        </div>
    """), guilds=PBE_GUILDS)

@app.route("/admin/print-id/<pbe_uid>")
def print_id(pbe_uid):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT * FROM pbe_master_registry WHERE pbe_uid = %s", (pbe_uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    
    buffer = BytesIO(); c = canvas.Canvas(buffer, pagesize=(3.375*inch, 2.125*inch))
    tpl = os.path.join(app.root_path, 'static', 'Power Bridge Engineering ID Identity Template.png')
    if os.path.exists(tpl): c.drawImage(tpl, 0, 0, width=3.375*inch, height=2.125*inch)
    if w[13]: c.drawImage(w[13], 0.18*inch, 0.55*inch, width=1.02*inch, height=1.22*inch)

    c.setFont("Helvetica-Bold", 7.5); c.setFillColor(colors.black)
    c.drawString(1.35*inch, 1.55*inch, f"{w[1]}") # Surname
    c.drawString(1.35*inch, 1.40*inch, f"{w[2]}") # Firstname
    c.drawString(1.35*inch, 1.25*inch, f"{w[6]}") # ID Number (15 char)
    c.drawString(1.35*inch, 1.10*inch, f"{w[7]}") # LICENSE Number (15 char)
    
    qr_code = qr.QrCodeWidget(f"{request.url_root}verify/{w[6]}")
    bounds = qr_code.getBounds(); d = Drawing(40, 40, transform=[40./(bounds[2]-bounds[0]),0,0,40./(bounds[3]-bounds[1]),0,0])
    d.add(qr_code); d.drawOn(c, 2.8*inch, 0.15*inch)
    c.showPage(); c.save(); buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf')

# [Rest of routes: login, invite, delete, etc. maintained exactly as discussed]

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
