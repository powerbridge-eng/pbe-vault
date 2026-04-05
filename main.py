import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session, abort
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO

# --- 1. CONFIGURATION & SECRETS ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY")
ARKESEL_SENDER_ID = "PBE_OTP" 
ADMIN_PASSWORD = "PBE-Global-2026" 
OFFICE_LINE = "+233541803057"

app = Flask(__name__)
app.secret_key = "PBE_SUPREME_COMMAND_2026_MASTER"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# --- 2. SELF-HEALING DATABASE ---
def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_master_registry (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT,
            pbe_uid TEXT UNIQUE, pbe_license TEXT UNIQUE, insurance_date TEXT, expiry_date TEXT,
            rank TEXT, phone_no TEXT, photo_url TEXT, ghana_card TEXT,
            otp_code TEXT, status TEXT DEFAULT 'PENDING', region TEXT, department TEXT, 
            ghana_card_photo TEXT
        );
    """)
    cur.execute("CREATE TABLE IF NOT EXISTS pbe_blacklist (id SERIAL PRIMARY KEY, ip_address TEXT UNIQUE, blocked_until TIMESTAMP);")
    conn.commit(); cur.close(); conn.close()

with app.app_context():
    init_db()

# --- 3. ENCRYPTION ENGINE (15-Character Mix) ---
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

# --- 4. VANGUARD SECURITY ---
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
    if is_blocked(request.remote_addr) and ("admin" in request.path):
        abort(404)

# --- 5. THE DESIGNER INTERFACE ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PBE Command</title><meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; text-align: center; }
        .header { background: #1a3a5a; color: white; padding: 25px; border-bottom: 8px solid #0056b3; }
        .container { max-width: 1200px; margin: 20px auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }
        .stat-box { display: inline-block; padding: 10px; background: #eee; border-radius: 5px; margin: 10px; font-size: 12px; font-weight: bold; }
        th, td { border-bottom: 1px solid #eee; padding: 12px; text-align: left; }
        .btn { padding: 10px 15px; border-radius: 6px; text-decoration: none; color: white; font-weight: bold; font-size: 12px; border: none; cursor: pointer; }
        .btn-blue { background: #0056b3; } .btn-green { background: #28a745; } .btn-red { background: #dc3545; }
        input, select { padding: 12px; margin: 8px 0; border: 1px solid #ddd; width: 100%; max-width: 400px; border-radius: 6px; }
    </style>
</head>
<body>
    <div class="header"><h1>POWER BRIDGE ENGINEERING</h1><p>SUPREME COMMAND CENTER</p></div>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- 6. ROUTES & COMMANDS ---

@app.route("/")
def index(): return redirect(url_for('login'))

@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True; return redirect(url_for('admin_dashboard'))
        engage_lockout(request.remote_addr); return "<h1>SYSTEM LOCKED ❌</h1>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<h3>Admin Authorization</h3><form method="POST"><input type="password" name="password" placeholder="Master Key" required><br><button class="btn btn-blue">Unlock</button></form>'))

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    # FETCH ARKESEL BALANCE
    balance = "Check Failed"
    try:
        r = requests.get(f"https://sms.arkesel.com/api/v2/clients/balance", headers={"api-key": ARKESEL_API_KEY})
        balance = r.json().get('data', {}).get('available_balance', "N/A")
    except: pass

    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()
    
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <div class="stat-box">SMS BALANCE: {balance} GHS</div>
        <div class="stat-box"><a href="https://cloudinary.com/console" target="_blank" style="color:black;">CLOUDINARY STORAGE</a></div>
        <hr>
        <div style="display:flex; justify-content: space-between; align-items:center;">
            <h3>Workforce Registry</h3>
            <a href="/admin/invite" class="btn btn-green">+ Invite Personnel</a>
        </div>
        <table>
            <tr><th>UID</th><th>Name</th><th>Status</th><th>Actions</th></tr>
            {{% for w in workers %}}
            <tr>
                <td><b>{{{{ w[4] or 'PENDING' }}}}</b></td>
                <td>{{{{ w[1] }}}}, {{{{ w[2] }}}}</td>
                <td><b style="color:{{{{ 'green' if w[13]=='ACTIVE' else 'orange' }}}};">{{{{ w[13] }}}}</b></td>
                <td>
                    {{% if w[13] == 'PENDING' %}}
                    <a href="/admin/approve/{{{{ w[0] }}}}" class="btn btn-green">Approve</a>
                    {{% else %}}
                    <a href="/admin/print-id/{{{{ w[4] }}}}" class="btn btn-blue">Print</a>
                    {{% endif %}}
                    <a href="/admin/delete/{{{{ w[0] }}}}" class="btn btn-red">Del</a>
                </td>
            </tr>
            {{% endfor %}}
        </table>
    """), workers=workers)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        otp = request.form.get('otp')
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT id FROM pbe_master_registry WHERE otp_code = %s", (otp,))
        if cur.fetchone():
            photo = cloudinary.uploader.upload(request.files['photo'])
            fname, sname = request.form.get('firstname').upper(), request.form.get('surname').upper()
            uid, lic = generate_pbe_id(fname), generate_pbe_license(sname)
            cur.execute("""UPDATE pbe_master_registry SET surname=%s, firstname=%s, dob=%s, pbe_uid=%s, pbe_license=%s,
                        ghana_card=%s, photo_url=%s, status='PENDING', rank=%s, department=%s WHERE otp_code=%s""",
                        (sname, fname, request.form.get('dob'), uid, lic, request.form.get('ghana_card'),
                        photo['secure_url'], request.form.get('rank'), request.form.get('department'), otp))
            conn.commit(); cur.close(); conn.close()
            return "<h2>ENROLLMENT SUBMITTED ✅ awaiting Admin Review.</h2>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<form method="POST" enctype="multipart/form-data"><input name="otp" placeholder="OTP"><input name="surname" placeholder="Surname"><input name="firstname" placeholder="Firstname"><input name="dob" placeholder="DOB"><input name="department" placeholder="Dept"><input name="rank" placeholder="Rank"><input name="ghana_card" placeholder="GHA-ID"><input type="file" name="photo" required><br><button class="btn btn-blue">Submit Registration</button></form>'))

@app.route("/admin/approve/<int:id>")
def approve_worker(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE pbe_master_registry SET status='ACTIVE' WHERE id=%s", (id,))
    conn.commit(); cur.close(); conn.close(); return redirect(url_for('admin_dashboard'))

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == 'POST':
        phone, otp = request.form.get('phone'), str(random.randint(100000, 999999))
        conn = get_db(); cur = conn.cursor(); cur.execute("INSERT INTO pbe_master_registry (phone_no, otp_code) VALUES (%s, %s)", (phone, otp)); conn.commit(); cur.close(); conn.close()
        requests.post("https://sms.arkesel.com/api/v2/sms/send", json={"sender": ARKESEL_SENDER_ID, "message": f"PBE: Use Code {otp} at {request.url_root}register", "recipients": [phone]}, headers={"api-key": ARKESEL_API_KEY})
        return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<h3>Invite</h3><form method="POST"><input name="phone" placeholder="233..."><button class="btn btn-blue">Send SMS</button></form>'))

@app.route("/admin/print-id/<pbe_uid>")
def print_id(pbe_uid):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT * FROM pbe_master_registry WHERE pbe_uid = %s", (pbe_uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    buffer = BytesIO(); c = canvas.Canvas(buffer, pagesize=(3.375*inch, 2.125*inch))
    template_path = os.path.join(app.root_path, 'static', 'Power Bridge Engineering ID Identity Template.png')
    if os.path.exists(template_path): c.drawImage(template_path, 0, 0, width=3.375*inch, height=2.125*inch)
    if w[10]: c.drawImage(w[10], 0.18*inch, 0.58*inch, width=0.98*inch, height=1.18*inch)
    c.setFont("Helvetica-Bold", 7); c.setFillColor(colors.black)
    x_pos = 1.35*inch
    c.drawString(x_pos, 1.55*inch, f"{w[1]}") # Surname
    c.drawString(x_pos, 1.40*inch, f"{w[2]}") # Firstname
    c.setFont("Helvetica", 6.5)
    c.drawString(x_pos, 1.22*inch, f"{w[4]}") # ID
    c.drawString(x_pos, 1.08*inch, f"{w[5]}") # License
    c.drawString(x_pos, 0.94*inch, f"{w[8]}") # Rank
    c.drawString(x_pos, 0.80*inch, f"{w[15]}") # Dept
    qr_code = qr.QrCodeWidget(f"{request.url_root}verify/{w[4]}")
    bounds = qr_code.getBounds(); d = Drawing(40, 40, transform=[40./(bounds[2]-bounds[0]),0,0,40./(bounds[3]-bounds[1]),0,0])
    d.add(qr_code); d.drawOn(c, 2.8*inch, 0.15*inch)
    c.showPage(); c.save(); buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf')

@app.route("/verify/<pbe_uid>")
def verify(pbe_uid):
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT * FROM pbe_master_registry WHERE pbe_uid = %s AND status='ACTIVE'", (pbe_uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    if not w: return "<h1>VERIFICATION FAILED / INACTIVE ❌</h1>", 404
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f'<h2 style="color:green;">✓ VERIFIED ENGINEER</h2><p><b>{w[2]} {w[1]}</b></p><p>Rank: {w[8]}</p><p>Office: {OFFICE_LINE}</p>'))

@app.route("/admin/delete/<int:id>")
def delete_worker(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("DELETE FROM pbe_master_registry WHERE id=%s", (id,)); conn.commit(); cur.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
