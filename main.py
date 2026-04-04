import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session
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
ADMIN_PASSWORD = "PBE-Global-2026" # <-- SET YOUR PASSWORD HERE
ADMIN_EMAIL = "Powerbridgee@gmail.com"

app = Flask(__name__)
app.secret_key = "PBE_SUPER_SECRET_KEY" # Needed for login sessions

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_master_registry (
            id SERIAL PRIMARY KEY,
            surname TEXT, firstname TEXT, dob TEXT,
            pbe_uid TEXT UNIQUE, pbe_license TEXT,
            insurance_date TEXT, expiry_date TEXT,
            rank TEXT, phone_no TEXT,
            photo_url TEXT, ghana_card TEXT,
            otp_code TEXT, status TEXT DEFAULT 'PENDING'
        );
    """)
    cols = ["dob", "insurance_date", "expiry_date", "ghana_card", "otp_code", "photo_url"]
    for col in cols:
        cur.execute(f"ALTER TABLE pbe_master_registry ADD COLUMN IF NOT EXISTS {col} TEXT;")
    conn.commit(); cur.close(); conn.close()

with app.app_context():
    init_db()

def generate_pbe_code(name):
    clean_name = re.sub(r'[^a-zA-Z]', '', name).upper()
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=15))
    return f"{clean_name}{random_part}"[:15]

# --- UI TEMPLATE ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PBE Command Center</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; background: #f4f7f6; margin: 0; text-align: center; }
        .header { background: #1a3a5a; color: white; padding: 30px; border-bottom: 8px solid #0056b3; }
        .logo-container { background: white; width: 110px; height: 110px; margin: 0 auto 15px; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
        .logo-container img { width: 90px; border-radius: 50%; }
        .container { max-width: 1100px; margin: -20px auto 40px; background: white; padding: 40px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); position: relative; z-index: 2; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.85em; }
        th, td { border-bottom: 1px solid #ddd; padding: 12px; text-align: left; }
        .btn { padding: 8px 15px; border-radius: 5px; text-decoration: none; font-size: 13px; display: inline-block; border: none; color: white; cursor: pointer; font-weight: bold; }
        .btn-blue { background: #0056b3; } .btn-green { background: #28a745; } .btn-red { background: #dc3545; }
        input { padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 6px; width: 100%; max-width: 400px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo-container"><img src="/static/logo.png" onerror="this.src='https://via.placeholder.com/100?text=PBE'"></div>
        <h1>POWER BRIDGE ENGINEERING</h1>
    </div>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- AUTHENTICATION ---
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return "<h1>WRONG PASSWORD ❌</h1>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <h2>Admin Login</h2>
        <form method="POST">
            <input type="password" name="password" placeholder="Enter Admin Password" required><br>
            <button class="btn btn-blue" type="submit">Unlock Dashboard</button>
        </form>
        <p style="margin-top:20px;"><a href="/forgot-password" style="color:#666; font-size:12px;">Forgot Password?</a></p>
    """))

@app.route("/forgot-password")
def forgot_password():
    return f"<h1>SECURITY ALERT 🛡️</h1><p>Password reset instructions have been sent to <b>{ADMIN_EMAIL}</b> only.</p>"

@app.route("/logout")
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# --- ROUTES ---
@app.route("/")
def home():
    return redirect(url_for('admin_dashboard'))

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        otp = request.form.get('otp')
        surname, firstname = request.form.get('surname').upper(), request.form.get('firstname').upper()
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT id FROM pbe_master_registry WHERE otp_code = %s", (otp,))
        if cur.fetchone():
            pbe_id, pbe_license = generate_pbe_code(firstname), generate_pbe_code(surname)
            upload = cloudinary.uploader.upload(request.files['photo'])
            cur.execute("""UPDATE pbe_master_registry SET surname=%s, firstname=%s, dob=%s, pbe_uid=%s, pbe_license=%s,
                        ghana_card=%s, photo_url=%s, status='ACTIVE', rank=%s, insurance_date=%s, expiry_date=%s
                        WHERE otp_code=%s""", (surname, firstname, request.form.get('dob'), pbe_id, pbe_license,
                        request.form.get('ghana_card'), upload['secure_url'], request.form.get('rank'),
                        request.form.get('insurance'), request.form.get('expiry'), otp))
            conn.commit(); cur.close(); conn.close()
            return "<h1>REGISTRATION SUCCESSFUL ✅</h1>"
        return "<h1>INVALID CODE ❌</h1>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <h2>Employee Enrollment</h2>
        <form method="POST" enctype="multipart/form-data">
            <input type="text" name="otp" placeholder="SMS Code" required>
            <input type="text" name="surname" placeholder="Surname" required>
            <input type="text" name="firstname" placeholder="First Name" required>
            <input type="date" name="dob" required>
            <input type="text" name="ghana_card" placeholder="Ghana Card">
            <input type="text" name="rank" placeholder="Rank">
            <input type="text" name="insurance" placeholder="Insurance Date">
            <input type="text" name="expiry" placeholder="Expiry Date">
            <input type="file" name="photo" required><br>
            <button class="btn btn-blue" type="submit">Register</button>
        </form>
    """))

@app.route("/admin")
def admin_dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <h2>Worker Registry</h2>
        <div style="margin-bottom:20px;">
            <a href="/admin/invite" class="btn btn-green">+ Invite</a>
            <a href="/logout" class="btn btn-red" style="background:#666;">Logout</a>
        </div>
        <table>
            <tr><th>PBE-ID</th><th>Name</th><th>License</th><th>Status</th><th>Actions</th></tr>
            {% for w in workers %}
            <tr><td><b>{{ w[4] or 'PENDING' }}</b></td><td>{{ w[1] }}, {{ w[2] }}</td><td>{{ w[5] }}</td><td>{{ w[13] }}</td>
            <td>{% if w[4] %}<a href="/admin/print-id/{{ w[4] }}" class="btn btn-blue">Print</a>{% endif %}
            <a href="/admin/delete/{{ w[0] }}" class="btn btn-red">Del</a></td></tr>{% endfor %}
        </table>
    """), workers=workers)

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == 'POST':
        phone = request.form.get('phone')
        otp = str(random.randint(100000, 999999))
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO pbe_master_registry (phone_no, otp_code) VALUES (%s, %s)", (phone, otp))
        conn.commit(); cur.close(); conn.close()
        requests.post("https://sms.arkesel.com/api/v2/sms/send", 
                      json={"sender": ARKESEL_SENDER_ID, "message": f"PBE Code: {otp}", "recipients": [phone]},
                      headers={"api-key": ARKESEL_API_KEY})
        return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <h3>Invite Worker</h3>
        <form method='POST'><input name='phone' placeholder='233...' required><button class='btn btn-blue'>Send SMS</button></form>
    """))

@app.route("/admin/print-id/<pbe_uid>")
def print_id(pbe_uid):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_master_registry WHERE pbe_uid = %s", (pbe_uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(3.375*inch, 2.125*inch))
    template = "POWER BRIDGE ENGINEERING ID CARD TEMPLATE.png"
    if os.path.exists(template): c.drawImage(template, 0, 0, width=3.375*inch, height=2.125*inch)
    if w[10]: 
        try: c.drawImage(w[10], 0.2*inch, 0.65*inch, width=0.9*inch, height=1.1*inch)
        except: pass
    c.setFont("Helvetica-Bold", 7.5); c.setFillColor(colors.black)
    x_col = 1.35*inch
    c.drawString(x_col, 1.6*inch, f"SURNAME: {w[1]}"); c.drawString(x_col, 1.45*inch, f"FIRSTNAME: {w[2]}")
    c.drawString(x_col, 1.25*inch, f"ID NO: {w[4]}"); c.drawString(x_col, 1.1*inch, f"LICENSE: {w[5]}")
    c.drawString(x_col, 0.95*inch, f"RANK: {w[8]}"); c.drawString(x_col, 0.8*inch, f"INSURED: {w[6]}")
    c.drawString(x_col, 0.65*inch, f"EXPIRY: {w[7]}"); c.drawString(x_col, 0.5*inch, f"DOB: {w[3]}")
    qr_code = qr.QrCodeWidget(f"{request.url_root}verify/{w[4]}")
    bounds = qr_code.getBounds(); d = Drawing(45, 45, transform=[45./(bounds[2]-bounds[0]),0,0,45./(bounds[3]-bounds[1]),0,0])
    d.add(qr_code); d.drawOn(c, 2.8*inch, 0.15*inch); c.showPage(); c.save(); buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf')

@app.route("/verify/<uid>")
def verify(uid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT firstname, surname, rank, pbe_license, status, insurance_date, expiry_date FROM pbe_master_registry WHERE pbe_uid = %s", (uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    if w:
        return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
            <h1 style='color:green;'>✅ VERIFIED EMPLOYEE</h1>
            <p><b>Name:</b> {w[0]} {w[1]}</p><p><b>Rank:</b> {w[2]}</p><p><b>License:</b> {w[3]}</p>
            <p><b>Insurance:</b> {w[5]}</p><p><b>Expiry:</b> {w[6]}</p><h3>STATUS: {w[4]}</h3>
        """))
    return "<h1>❌ INVALID ID</h1>"

@app.route("/admin/delete/<int:id>")
def delete_worker(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("DELETE FROM pbe_master_registry WHERE id = %s", (id,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
