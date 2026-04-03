import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO

# --- 1. CONFIGURATION ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY")
ARKESEL_SENDER_ID = os.environ.get("ARKESEL_SENDER_ID", "PBE_AUTH")

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

app = Flask(__name__)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# --- 2. DATABASE INITIALIZATION ---
def init_db():
    conn = get_db()
    cur = conn.cursor()
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
    cols = ["dob", "insurance_date", "expiry_date", "ghana_card"]
    for col in cols:
        cur.execute(f"ALTER TABLE pbe_master_registry ADD COLUMN IF NOT EXISTS {col} TEXT;")
    conn.commit()
    cur.close()
    conn.close()

with app.app_context():
    init_db()

# --- 3. UTILITIES ---
def generate_pbe_code(name):
    clean_name = re.sub(r'[^a-zA-Z]', '', name).upper()
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=15))
    return f"{clean_name}{random_part}"[:15]

# --- 4. UI TEMPLATE ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PBE Command Center</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; background: #f4f7f6; margin: 0; text-align: center; }
        .header { background: #1a3a5a; color: white; padding: 20px; }
        .logo { width: 100px; margin-bottom: 10px; border-radius: 5px; }
        .container { max-width: 1100px; margin: 20px auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.85em; }
        th, td { border-bottom: 1px solid #ddd; padding: 10px; text-align: left; }
        .btn { padding: 6px 10px; border-radius: 4px; text-decoration: none; font-size: 12px; display: inline-block; border: none; color: white; }
        .btn-blue { background: #0056b3; } .btn-green { background: #28a745; } .btn-red { background: #dc3545; }
    </style>
</head>
<body>
    <div class="header">
        <img src="/static/logo.png" class="logo" onerror="this.src='https://via.placeholder.com/100?text=PBE+LOGO'">
        <h1>PBE COMMAND CENTER</h1>
    </div>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- 5. ROUTES ---
@app.route("/")
def home():
    return redirect(url_for('admin_dashboard'))

@app.route("/admin")
def admin_dashboard():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    workers = cur.fetchall()
    cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <h2>Worker Registry</h2>
        <a href="/admin/invite" class="btn btn-green">+ New Invitation</a>
        <table>
            <tr><th>UID</th><th>Name</th><th>Rank</th><th>Status</th><th>Actions</th></tr>
            {% for w in workers %}
            <tr>
                <td><b>{{ w[4] }}</b></td>
                <td>{{ w[1] }}, {{ w[2] }}</td>
                <td>{{ w[8] }}</td>
                <td>{{ w[13] }}</td>
                <td>
                    <a href="/admin/print-id/{{ w[4] }}" class="btn btn-blue">Print</a>
                    <a href="https://wa.me/{{ w[9] }}?text=PBE Verification: {{ request.url_root }}verify/{{ w[4] }}" class="btn btn-green" target="_blank">WA</a>
                    <a href="/admin/delete/{{ w[0] }}" class="btn btn-red" onclick="return confirm('Delete?')">Del</a>
                </td>
            </tr>
            {% endfor %}
        </table>
    """), workers=workers)

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if request.method == 'POST':
        phone = request.form.get('phone')
        otp = str(random.randint(100000, 999999))
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO pbe_master_registry (phone_no, otp_code) VALUES (%s, %s)", (phone, otp))
        conn.commit(); cur.close(); conn.close()
        msg = f"PBE: Use code {otp} to register at {request.url_root}register"
        requests.post("https://sms.arkesel.com/api/v2/sms/send", 
                      json={"sender": ARKESEL_SENDER_ID, "message": msg, "recipients": [phone]},
                      headers={"api-key": ARKESEL_API_KEY})
        return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <h3>Invite Worker</h3>
        <form method='POST'><input name='phone' placeholder='233...' required><button class='btn btn-blue'>Send OTP</button></form>
    """))

@app.route("/admin/print-id/<pbe_uid>")
def print_id(pbe_uid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_master_registry WHERE pbe_uid = %s", (pbe_uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    if not w: return "Not Found", 404
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(3.375*inch, 2.125*inch))
    template = "POWER BRIDGE ENGINEERING ID CARD TEMPLATE.png"
    if os.path.exists(template): c.drawImage(template, 0, 0, width=3.375*inch, height=2.125*inch)
    if w[10]: 
        try: c.drawImage(w[10], 0.2*inch, 0.65*inch, width=0.9*inch, height=1.1*inch)
        except: pass
    c.setFont("Helvetica-Bold", 7.5); c.setFillColor(colors.black)
    x_col = 1.35*inch
    c.drawString(x_col, 1.6*inch, f"SURNAME: {w[1]}".upper())
    c.drawString(x_col, 1.45*inch, f"FIRSTNAME: {w[2]}".upper())
    c.drawString(x_col, 1.25*inch, f"ID NO: {w[4]}")
    c.drawString(x_col, 1.1*inch, f"LICENSE: {w[5]}")
    c.drawString(x_col, 0.95*inch, f"RANK: {w[8]}")
    c.drawString(x_col, 0.8*inch, f"INSURED: {w[6]}")
    c.drawString(x_col, 0.65*inch, f"EXPIRY: {w[7]}")
    c.drawString(x_col, 0.5*inch, f"DOB: {w[3]}")
    qr_code = qr.QrCodeWidget(f"{request.url_root}verify/{w[4]}")
    bounds = qr_code.getBounds(); width, height = bounds[2]-bounds[0], bounds[3]-bounds[1]
    d = Drawing(45, 45, transform=[45./width,0,0,45./height,0,0]); d.add(qr_code)
    d.drawOn(c, 2.8*inch, 0.15*inch); c.showPage(); c.save(); buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf')

@app.route("/verify/<uid>")
def verify(uid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT firstname, surname, rank, pbe_license, status FROM pbe_master_registry WHERE pbe_uid = %s", (uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    if w: return f"<div style='text-align:center; padding:50px; font-family:sans-serif;'><h1>✅ VERIFIED</h1><p>Name: {w[0]} {w[1]}</p><p>Rank: {w[2]}</p><h3>STATUS: {w[4]}</h3></div>"
    return "<h1>❌ INVALID ID</h1>"

@app.route("/admin/delete/<int:id>")
def delete_worker(id):
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM pbe_master_registry WHERE id = %s", (id,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
