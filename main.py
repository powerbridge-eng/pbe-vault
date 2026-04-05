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
ARKESEL_SENDER_ID = "PBE_OTP"  # STRICTLY UPDATED TO PBE_OTP
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
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root { --navy: #0a192f; --gold: #ffcc00; --bg: #f4f6f9; --text: #1e293b; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; padding-bottom: 100px; }
        .header { background: var(--navy); color: white; padding: 25px; text-align: center; border-bottom: 4px solid var(--gold); }
        .container { max-width: 1200px; margin: auto; padding: 15px; }
        .search-container { display: flex; gap: 10px; margin-bottom: 20px; }
        .search-bar { flex: 1; padding: 15px; border-radius: 10px; border: 1px solid #ddd; font-size: 16px; outline: none; }
        .section-card { background: #fff; border-radius: 15px; padding: 20px; margin-bottom: 20px; border: 1px solid #e2e8f0; }
        .registry-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .registry-table th, .registry-table td { text-align: left; padding: 12px; border-bottom: 1px solid #f1f3f5; }
        .btn-cmd { padding: 8px 10px; border-radius: 6px; color: white; text-decoration: none; font-size: 11px; font-weight: bold; margin-right: 3px; display: inline-block; border: none; cursor: pointer; }
        .bg-blue { background: #007bff; } .bg-wa { background: #28a745; } .bg-red { background: #dc3545; } .bg-suspend { background: #f59e0b; } .bg-email { background: #334155; }
        .audit-terminal { background: #000; color: #0f0; padding: 15px; border-radius: 10px; font-family: monospace; height: 150px; overflow-y: auto; font-size: 12px; border: 2px solid #333; }
        .fab { position: fixed; bottom: 30px; right: 30px; width: 65px; height: 65px; background: var(--navy); color: var(--gold); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); text-decoration: none; z-index: 1001; border: 2px solid var(--gold); }
    </style>
</head>
<body>
    <div class="header">
        <div style="font-size: 22px; font-weight: 900;">PBE COMMAND CENTER</div>
    </div>
    <div class="container">{% block content %}{% endblock %}</div>
    {% if session.get('logged_in') %}
    <a href="/admin/invite" class="fab">＋</a>
    {% endif %}
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

@app.route("/")
def index(): return redirect(url_for('login'))

@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            log_soul_action("SECURITY_LOGIN", "Admin Access")
            return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="section-card" style="max-width:350px; margin: 80px auto; text-align:center;"><h3>SYSTEM LOCK</h3><form method="POST"><input type="password" name="password" class="search-bar" placeholder="Master Key" style="width:100%; box-sizing:border-box; margin-bottom:10px;" required><button class="btn-cmd bg-blue" style="width:100%; padding:15px;">AUTHENTICATE</button></form></div>'))

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    sms_live = "..."
    try:
        r = requests.get("https://sms.arkesel.com/api/v2/clients/balance", headers={"api-key": ARKESEL_API_KEY}, timeout=3)
        sms_live = f"{r.json().get('data', {}).get('available_balance', '0.00')} GHS"
    except: sms_live = "OFFLINE"

    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    workers = cur.fetchall()
    cur.execute("SELECT * FROM pbe_soul_audit ORDER BY timestamp DESC LIMIT 20")
    logs = cur.fetchall(); cur.close(); conn.close()

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <div class="search-container">
            <input type="text" id="globalSearch" class="search-bar" placeholder="Search Master Registry..." onkeyup="filterRegistry()">
            <div class="section-card" style="margin:0; padding:15px; font-weight:bold;">SMS: {sms_live} | Cloudinary: 🟢</div>
        </div>
        <div class="section-card">
            <div style="font-size:13px; font-weight:800; color:#6c757d; margin-bottom:15px; border-left:4px solid #0a192f; padding-left:10px;">👥 PERSONNEL REGISTRY</div>
            <div style="overflow-x:auto;">
                <table class="registry-table">
                    <thead><tr><th>PBE-ID / LICENSE</th><th>NAME</th><th>RANK</th><th>COMMANDS</th></tr></thead>
                    <tbody>
                        {{% for w in workers %}}
                        <tr class="worker-row">
                            <td><b>{{{{ w[6] }}}}</b><br><small>{{{{ w[7] }}}}</small></td>
                            <td>{{{{ w[1] }}}}, {{{{ w[2] }}}}</td>
                            <td>{{{{ w[10] }}}}</td>
                            <td>
                                <a href="/admin/print-id/{{{{ w[6] }}}}" class="btn-cmd bg-blue"><i class="fas fa-print"></i></a>
                                <a href="https://wa.me/{{{{ w[12] }}}}" class="btn-cmd bg-wa" target="_blank"><i class="fab fa-whatsapp"></i></a>
                                <a href="mailto:{{{{ w[12] }}}}" class="btn-cmd bg-email"><i class="fas fa-envelope"></i></a>
                                <a href="/admin/suspend/{{{{ w[0] }}}}" class="btn-cmd bg-suspend"><i class="fas fa-pause"></i></a>
                                <a href="/admin/delete/{{{{ w[0] }}}}" class="btn-cmd bg-red" onclick="return confirm('Erase from Matrix?')"><i class="fas fa-trash"></i></a>
                            </td>
                        </tr>
                        {{% endfor %}}
                    </tbody>
                </table>
            </div>
        </div>
        <div class="section-card">
            <div style="font-size:13px; font-weight:800; color:#6c757d; margin-bottom:15px; border-left:4px solid #0a192f; padding-left:10px;">🛡️ Audit Logs & Live Tracking</div>
            <div class="audit-terminal">
                {{% for log in logs %}}
                <p>[{{{{ log[1].strftime('%H:%M:%S') }}}}] {{{{ log[2] }}}}: {{{{ log[3] }}}}</p>
                {{% endfor %}}
            </div>
        </div>
    """), workers=workers, logs=logs)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        otp = request.form.get('otp')
        conn = get_db(); cur = conn.cursor(); cur.execute("SELECT id FROM pbe_master_registry WHERE otp_code = %s", (otp,))
        if cur.fetchone():
            fname, sname = request.form.get('firstname').upper().replace(" ", "_"), request.form.get('surname').upper().replace(" ", "_")
            photo = cloudinary.uploader.upload(request.files['photo'], public_id=f"PBE_PP_{fname}_{sname}")
            uid = generate_15_char(fname)
            lic = generate_15_char(sname)
            cur.execute("""UPDATE pbe_master_registry SET surname=%s, firstname=%s, dob=%s, pbe_uid=%s, pbe_license=%s,
                        issuance_date=%s, expiry_date=%s, rank=%s, department=%s, photo_url=%s, 
                        status='ACTIVE', region=%s, station=%s WHERE otp_code=%s""",
                        (request.form.get('surname').upper(), fname, request.form.get('dob'), uid, lic,
                        datetime.date.today(), datetime.date.today() + datetime.timedelta(days=730),
                        request.form.get('rank'), request.form.get('department'), photo['secure_url'], 
                        request.form.get('region'), request.form.get('station'), otp))
            conn.commit(); cur.close(); conn.close()
            log_soul_action("REGISTRATION", f"Personnel {fname} joined.")
            return "<div style='text-align:center; padding:100px;'><h1>REGISTRATION SUCCESSFUL ✅</h1></div>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="section-card" style="max-width:500px; margin: auto;">
            <h3>PERSONNEL REGISTRY FORM</h3>
            <form method="POST" enctype="multipart/form-data">
                <input name="otp" placeholder="OTP Code" class="search-bar" style="width:100%; box-sizing:border-box; margin-bottom:10px;" required>
                <input name="surname" placeholder="Surname" class="search-bar" style="width:100%; box-sizing:border-box; margin-bottom:10px;" required>
                <input name="firstname" placeholder="First Name" class="search-bar" style="width:100%; box-sizing:border-box; margin-bottom:10px;" required>
                <select name="department" class="search-bar" style="width:100%; box-sizing:border-box; margin-bottom:10px;">
                    {% for g in guilds %}<option value="{{g}}">{{g}}</option>{% endfor %}
                </select>
                <input name="rank" placeholder="Job Rank" class="search-bar" style="width:100%; box-sizing:border-box; margin-bottom:10px;" required>
                <p style="font-size:11px; color:gray;">Upload ID Photo:</p>
                <input type="file" name="photo" required><br>
                <button class="btn-cmd bg-blue" style="width:100%; padding:15px; margin-top:20px;">SUBMIT REGISTRY</button>
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
    c.drawString(1.35*inch, 1.55*inch, f"Surname: {w[1]}")
    c.drawString(1.35*inch, 1.40*inch, f"Firstname: {w[2]}")
    c.drawString(1.35*inch, 1.25*inch, f"ID: {w[6]}")
    c.drawString(1.35*inch, 1.10*inch, f"Rank: {w[10]}")
    
    # Automated 2-year Expiry Logic
    expiry = w[9].strftime('%Y-%m-%d') if w[9] else "N/A"
    c.drawString(1.35*inch, 0.55*inch, f"EXP: {expiry}")
    
    qr_code = qr.QrCodeWidget(f"{request.url_root}verify/{w[6]}")
    bounds = qr_code.getBounds(); d = Drawing(40, 40, transform=[40./(bounds[2]-bounds[0]),0,0,40./(bounds[3]-bounds[1]),0,0])
    d.add(qr_code); d.drawOn(c, 2.8*inch, 0.15*inch)
    c.showPage(); c.save(); buffer.seek(0)
    log_soul_action("PRINT", f"ID generated for {w[2]}")
    return send_file(buffer, mimetype='application/pdf')

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == 'POST':
        phone, otp = request.form.get('phone'), str(random.randint(111111, 999999))
        conn = get_db(); cur = conn.cursor(); cur.execute("INSERT INTO pbe_master_registry (phone_no, otp_code) VALUES (%s, %s)", (phone, otp)); conn.commit(); cur.close(); conn.close()
        # SMS using PBE_OTP Sender ID
        requests.post("https://sms.arkesel.com/api/v2/sms/send", json={"sender": ARKESEL_SENDER_ID, "message": f"PBE: Your Registry OTP is {otp}. Register at: {request.url_root}register", "recipients": [phone]}, headers={"api-key": ARKESEL_API_KEY})
        log_soul_action("INVITE", f"OTP {otp} sent to {phone}")
        return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="section-card" style="max-width:400px; margin:auto;"><h3>SEND REGISTRY OTP</h3><form method="POST"><input name="phone" placeholder="233..." class="search-bar" style="width:100%; box-sizing:border-box;"><button class="btn-cmd bg-blue" style="width:100%; padding:15px; margin-top:10px;">SEND SMS</button></form></div>'))

@app.route("/admin/delete/<int:id>")
def delete_worker(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("DELETE FROM pbe_master_registry WHERE id=%s", (id,)); conn.commit(); cur.close(); conn.close()
    log_soul_action("DELETE", f"Record ID {id} Erased.")
    return redirect(url_for('admin_dashboard'))

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
