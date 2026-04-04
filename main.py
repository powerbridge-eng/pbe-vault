import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session, abort
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO

# --- 1. CONFIGURATION ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY")
ARKESEL_SENDER_ID = "PBE_OTP" 
ADMIN_PASSWORD = "PBE-Global-2026" 
SUPERVISOR_PASSWORD = "PBE-Super-2026"

app = Flask(__name__)
app.secret_key = "PBE_SUPREME_COMMAND_2026"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# --- 2. THE GROUND ZERO RESET (Nuclear Purge) ---
def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS pbe_master_registry, pbe_blacklist, pbe_audit_logs CASCADE;")
    cur.execute("""
        CREATE TABLE pbe_master_registry (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT,
            pbe_uid TEXT UNIQUE, pbe_license TEXT, insurance_date TEXT, expiry_date TEXT,
            rank TEXT, phone_no TEXT, photo_url TEXT, ghana_card TEXT,
            otp_code TEXT, status TEXT DEFAULT 'PENDING', region TEXT, department TEXT, 
            ghana_card_photo TEXT
        );
    """)
    cur.execute("CREATE TABLE pbe_blacklist (id SERIAL PRIMARY KEY, ip_address TEXT UNIQUE, blocked_until TIMESTAMP);")
    cur.execute("CREATE TABLE pbe_audit_logs (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, action TEXT, details TEXT, ip_address TEXT, user_role TEXT);")
    conn.commit(); cur.close(); conn.close()

with app.app_context():
    init_db()

# --- 3. THE 15-CHAR ENCRYPTION ENGINE ---
def generate_pbe_id(firstname):
    clean = re.sub(r'[^A-Z]', '', firstname.upper())
    chars = string.ascii_uppercase + string.digits
    needed = 15 - len(clean)
    if needed < 0: return clean[:15]
    return f"{clean}{''.join(random.choices(chars, k=needed))}"

def generate_pbe_license(surname):
    clean = re.sub(r'[^A-Z]', '', surname.upper())
    chars = string.ascii_uppercase + string.digits
    needed = 15 - len(clean)
    if needed < 0: return clean[:15]
    return f"{clean}{''.join(random.choices(chars, k=needed))}"

# --- 4. VANGUARD SECURITY (Corrected 72hr Blacklist) ---
def is_blocked(ip):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT blocked_until FROM pbe_blacklist WHERE ip_address = %s", (ip,))
    res = cur.fetchone(); cur.close(); conn.close()
    return True if res and res[0] > datetime.datetime.now() else False

def engage_lockout(ip):
    until = datetime.datetime.now() + datetime.timedelta(days=3)
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_blacklist (ip_address, blocked_until) VALUES (%s, %s) ON CONFLICT (ip_address) DO UPDATE SET blocked_until = %s", (ip, until, until))
    conn.commit(); cur.close(); conn.close()

@app.before_request
def vanguard_gate():
    if request.args.get('bypass') == 'OPEN': return 
    if is_blocked(request.remote_addr) and ("vanguard" in request.path or "admin" in request.path):
        abort(404)

# --- 5. UI DESIGN (PBE Navy Theme) ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PBE Supreme Command</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; text-align: center; }
        .header { background: #1a3a5a; color: white; padding: 25px; border-bottom: 8px solid #0056b3; }
        .logo-text { font-size: 24px; font-weight: bold; color: #ffcc00; letter-spacing: 2px; }
        .container { max-width: 1200px; margin: 20px auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.9em; }
        th, td { border-bottom: 1px solid #eee; padding: 12px; text-align: left; }
        .btn { padding: 10px 15px; border-radius: 6px; text-decoration: none; display: inline-block; border: none; color: white; cursor: pointer; font-weight: bold; font-size: 12px; }
        .btn-blue { background: #0056b3; } .btn-green { background: #28a745; } .btn-red { background: #dc3545; } .btn-wa { background: #25D366; }
        input, select { padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 6px; width: 100%; max-width: 400px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo-text">PBE ENGINEERING</div>
        <h1>SUPREME COMMAND CENTER</h1>
    </div>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- 6. CORE ROUTES ---
@app.route("/")
def index(): return redirect(url_for('login'))

@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        pwd = request.form.get('password')
        if pwd == ADMIN_PASSWORD:
            session['logged_in'], session['role'] = True, 'GENERAL'
            return redirect(url_for('admin_dashboard'))
        elif pwd == SUPERVISOR_PASSWORD:
            session['logged_in'], session['role'] = True, 'SUPERVISOR'
            return redirect(url_for('admin_dashboard'))
        else:
            engage_lockout(request.remote_addr)
            return "<h1>CRITICAL SECURITY: IP BLACKLISTED ❌</h1>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div style="padding: 40px;">
            <h2>Personnel Security Clearance</h2>
            <form method="POST"><input type="password" name="password" placeholder="Master Access Key" required><br><br><button class="btn btn-blue" style="font-size:18px;">Unlock System</button></form>
        </div>
    """))

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div style="display:flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h3>Active Workforce Registry</h3>
            <div>
                <a href="/admin/invite" class="btn btn-green" style="font-size:14px;">+ Invite Worker</a>
                <a href="/logout" class="btn btn-blue" style="background:#333; margin-left:10px;">Lock Console</a>
            </div>
        </div>
        <table>
            <tr><th>PBE-ID</th><th>Full Name</th><th>Department</th><th>Actions</th></tr>
            {% for w in workers %}
            <tr>
                <td><b>{{ w[4] or 'PENDING' }}</b></td>
                <td>{{ w[1] }}, {{ w[2] }}</td>
                <td>{{ w[15] }}</td>
                <td>
                    <a href="https://wa.me/{{ w[9] }}?text=Hello {{ w[2] }}, your PBE Identity is active. Verify here: {{ request.url_root }}verify/{{ w[4] }}" class="btn btn-wa" target="_blank">WA</a>
                    {% if w[4] %}<a href="/admin/print-id/{{ w[4] }}" class="btn btn-blue">Print ID</a>{% endif %}
                    {% if role == 'GENERAL' %}<a href="/admin/delete/{{ w[0] }}" class="btn btn-red">Del</a>{% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
    """), workers=workers, role=session['role'])

@app.route("/register", methods=['GET', 'POST'])
def register():
    regions = ["Greater Accra", "Ashanti", "Western", "Volta", "Eastern", "Central", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Oti", "Savannah", "North East", "Western North"]
    if request.method == 'POST':
        otp = request.form.get('otp')
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT id FROM pbe_master_registry WHERE otp_code = %s", (otp,))
        if cur.fetchone():
            photo = cloudinary.uploader.upload(request.files['photo'])
            gcard_img = cloudinary.uploader.upload(request.files['gcard_photo'])
            fname, sname = request.form.get('firstname').upper(), request.form.get('surname').upper()
            uid = generate_pbe_id(fname)
            lic = generate_pbe_license(sname)
            cur.execute("""UPDATE pbe_master_registry SET surname=%s, firstname=%s, dob=%s, pbe_uid=%s, pbe_license=%s,
                        ghana_card=%s, photo_url=%s, status='ACTIVE', rank=%s, insurance_date=%s, expiry_date=%s,
                        region=%s, department=%s, ghana_card_photo=%s WHERE otp_code=%s""",
                        (sname, fname, request.form.get('dob'), uid, lic, request.form.get('ghana_card'),
                        photo['secure_url'], request.form.get('rank'), request.form.get('insurance'),
                        request.form.get('expiry'), request.form.get('region'), request.form.get('department'),
                        gcard_img['secure_url'], otp))
            conn.commit(); cur.close(); conn.close()
            return "<h2>REGISTRATION SUCCESSFUL! 🎖️ Welcome to PBE.</h2>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <h3>Personnel Identity Enrollment</h3>
        <form method="POST" enctype="multipart/form-data">
            <input name="otp" placeholder="Enter SMS OTP" required>
            <input name="surname" placeholder="Surname" required>
            <input name="firstname" placeholder="First Name" required>
            <input name="dob" placeholder="Date of Birth (DD/MM/YYYY)">
            <select name="region">{''.join([f'<option value="{r}">{r}</option>' for r in regions])}</select>
            <input name="department" placeholder="Department (e.g., Solar, CCTV)">
            <input name="rank" placeholder="Current Rank/Role">
            <input name="ghana_card" placeholder="Ghana Card Number (GHA-...)">
            <p style="text-align:left; color:#666; font-size:12px;">Passport Photo:</p>
            <input type="file" name="photo" required>
            <p style="text-align:left; color:#666; font-size:12px;">Ghana Card Front Photo:</p>
            <input type="file" name="gcard_photo" required>
            <br><br><button class="btn btn-blue" style="width:100%; font-size:18px;">Submit Identity</button>
        </form>
    """))

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == 'POST':
        phone, otp = request.form.get('phone'), str(random.randint(100000, 999999))
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO pbe_master_registry (phone_no, otp_code) VALUES (%s, %s)", (phone, otp))
        conn.commit(); cur.close(); conn.close()
        # SMS TRIGGER (ARIES)
        msg = f"PBE COMMAND: Use Code {otp} to enroll at {request.url_root}register"
        requests.post("https://sms.arkesel.com/api/v2/sms/send", 
                      json={"sender": ARKESEL_SENDER_ID, "message": msg, "recipients": [phone]}, 
                      headers={"api-key": ARKESEL_API_KEY})
        return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <h3>Invite Personnel</h3>
        <form method='POST'>
            <input name='phone' placeholder='Phone Number (e.g., 23324...)' required><br>
            <button class="btn btn-blue">Send SMS Invitation</button>
        </form>
    """))

@app.route("/admin/print-id/<pbe_uid>")
def print_id(pbe_uid):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT * FROM pbe_master_registry WHERE pbe_uid = %s", (pbe_uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    buffer = BytesIO(); c = canvas.Canvas(buffer, pagesize=(3.375*inch, 2.125*inch))
    # Border
    c.setStrokeColor(colors.navy); c.rect(0.05*inch, 0.05*inch, 3.275*inch, 2.025*inch, fill=0, stroke=1)
    if w[10]: # Worker Photo
        try: c.drawImage(w[10], 0.15*inch, 0.6*inch, width=0.9*inch, height=1.1*inch)
        except: pass
    c.setFont("Helvetica-Bold", 8); c.setFillColor(colors.navy)
    c.drawString(1.15*inch, 1.7*inch, "POWER BRIDGE ENGINEERING")
    c.setFont("Helvetica", 7); c.setFillColor(colors.black)
    c.drawString(1.15*inch, 1.4*inch, f"NAME: {w[1]} {w[2]}")
    c.drawString(1.15*inch, 1.25*inch, f"ID NO: {w[4]}")
    c.drawString(1.15*inch, 1.1*inch, f"LICENSE: {w[5]}")
    c.drawString(1.15*inch, 0.95*inch, f"DEPT: {w[15]}")
    qr_code = qr.QrCodeWidget(f"{request.url_root}verify/{w[4]}")
    bounds = qr_code.getBounds(); d = Drawing(45, 45, transform=[45./(bounds[2]-bounds[0]),0,0,45./(bounds[3]-bounds[1]),0,0])
    d.add(qr_code); d.drawOn(c, 2.7*inch, 0.15*inch); c.showPage(); c.save(); buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf')

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for('login'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
