
import os
import random
import string
import re
import requests
import psycopg2
import cloudinary
import cloudinary.uploader
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

# Initialize Table with all PBE Requirements
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
    conn.commit()
    cur.close()
    conn.close()

with app.app_context():
    init_db()

# --- 2. THE ENCRYPTION ENGINE ---
def generate_pbe_code(name):
    """Creates a 15-character unique ID mixed with the name"""
    clean_name = re.sub(r'[^a-zA-Z]', '', name).upper()
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(chars, k=15))
    return f"{clean_name}{random_part}"[:15]

# --- 3. UI TEMPLATE ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PBE Command Center</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; background: #f4f7f6; margin: 0; text-align: center; }
        .header { background: #1a3a5a; color: white; padding: 20px; }
        .logo { width: 100px; margin-bottom: 10px; }
        .container { max-width: 1100px; margin: 20px auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.9em; }
        th, td { border-bottom: 1px solid #ddd; padding: 12px; text-align: left; }
        .btn { padding: 8px 12px; border-radius: 5px; text-decoration: none; font-size: 13px; display: inline-block; cursor: pointer; border: none; }
        .btn-blue { background: #0056b3; color: white; }
        .btn-green { background: #28a745; color: white; }
        .btn-red { background: #dc3545; color: white; }
        input { padding: 10px; margin: 5px; border: 1px solid #ddd; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <img src="/static/logo.png" class="logo" onerror="this.src='https://via.placeholder.com/100?text=PBE+LOGO'">
        <h1>PBE IDENTITY COMMAND CENTER</h1>
    </div>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- 4. ADMIN ROUTES (The Dashboard) ---

@app.route("/admin")
def admin_dashboard():
    search = request.args.get('search', '')
    conn = get_db()
    cur = conn.cursor()
    if search:
        cur.execute("SELECT * FROM pbe_master_registry WHERE surname ILIKE %s OR pbe_uid ILIKE %s", (f'%{search}%', f'%{search}%'))
    else:
        cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    workers = cur.fetchall()
    cur.close()
    conn.close()
    return render_template_string(BASE_HTML + """
    {% block content %}
        <h2>Worker Registry Management</h2>
        <form method="GET" style="margin-bottom:20px;">
            <input type="text" name="search" placeholder="Search Name or UID..." style="width:40%;">
            <button type="submit" class="btn btn-blue">Search</button>
            <a href="/admin/invite" class="btn btn-green">+ New Invitation</a>
        </form>
        <table>
            <tr><th>UID</th><th>Name</th><th>License</th><th>Rank</th><th>Status</th><th>Actions</th></tr>
            {% for w in workers %}
            <tr>
                <td><b>{{ w[4] }}</b></td>
                <td>{{ w[1] }}, {{ w[2] }}</td>
                <td>{{ w[5] }}</td>
                <td>{{ w[8] }}</td>
                <td>{{ w[13] }}</td>
                <td>
                    <a href="/admin/print-id/{{ w[4] }}" class="btn btn-blue">Print ID</a>
                    <a href="https://wa.me/{{ w[9] }}?text=Your PBE ID is ready: {{ request.url_root }}verify/{{ w[4] }}" class="btn btn-green">WhatsApp</a>
                    <a href="/admin/delete/{{ w[0] }}" class="btn btn-red" onclick="return confirm('Delete permanently?')">Del</a>
                </td>
            </tr>
            {% endfor %}
        </table>
    {% endblock %}
    """, workers=workers)

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if request.method == 'POST':
        phone = request.form.get('phone')
        otp = str(random.randint(100000, 999999))
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO pbe_master_registry (phone_no, otp_code) VALUES (%s, %s)", (phone, otp))
        conn.commit()
        cur.close()
        conn.close()
        
        msg = f"PBE: Use code {otp} to register at {request.url_root}register"
        requests.post("https://sms.arkesel.com/api/v2/sms/send", 
                      json={"sender": ARKESEL_SENDER_ID, "message": msg, "recipients": [phone]},
                      headers={"api-key": ARKESEL_API_KEY})
        return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML + "{% block content %}<h3>Invite Worker</h3><form method='POST'><input name='phone' placeholder='233...' required><button class='btn btn-blue'>Send SMS OTP</button></form>{% endblock %}")

@app.route("/admin/delete/<int:id>")
def delete_worker(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM pbe_master_registry WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('admin_dashboard'))

# --- 5. THE PRECISION PRINT ENGINE ---

@app.route("/admin/print-id/<pbe_uid>")
def print_id(pbe_uid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_master_registry WHERE pbe_uid = %s", (pbe_uid,))
    w = cur.fetchone()
    cur.close()
    conn.close()
    
    if not w: return "Not Found", 404

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(3.375*inch, 2.125*inch))
    
    # Background
    template = "POWER BRIDGE ENGINEERING ID CARD TEMPLATE.png"
    if os.path.exists(template):
        c.drawImage(template, 0, 0, width=3.375*inch, height=2.125*inch)

    # Photo (from Cloudinary)
    if w[10]: # photo_url
        try: c.drawImage(w[10], 0.2*inch, 0.65*inch, width=0.9*inch, height=1.1*inch)
        except: pass

    # Smart Encrypted Details
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(colors.black)
    x_col = 1.35*inch
    
    c.drawString(x_col, 1.6*inch, f"SURNAME: {w[1]}".upper())
    c.drawString(x_col, 1.45*inch, f"FIRSTNAME: {w[2]}".upper())
    c.drawString(x_col, 1.25*inch, f"ID NO: {w[4]}") # The 15-char UID
    c.drawString(x_col, 1.1*inch, f"LICENSE: {w[5]}") # The 15-char License
    c.drawString(x_col, 0.95*inch, f"RANK: {w[8]}")
    c.drawString(x_col, 0.8*inch, f"INSURED: {w[6]}")
    c.drawString(x_col, 0.65*inch, f"EXPIRY: {w[7]}")
    c.drawString(x_col, 0.5*inch, f"DOB: {w[3]}")

    # QR Code
    qr_code = qr.QrCodeWidget(f"{request.url_root}verify/{w[4]}")
    bounds = qr_code.getBounds()
    width, height = bounds[2]-bounds[0], bounds[3]-bounds[1]
    d = Drawing(45, 45, transform=[45./width,0,0,45./height,0,0])
    d.add(qr_code)
    d.drawOn(c, 2.8*inch, 0.15*inch)

    c.showPage()
    c.save()
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf')

@app.route("/verify/<uid>")
def verify(uid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT firstname, surname, rank, pbe_license, status FROM pbe_master_registry WHERE pbe_uid = %s", (uid,))
    w = cur.fetchone()
    if w:
        return f"<div style='text-align:center; padding:50px; font-family:sans-serif;'><h1>✅ VERIFIED PBE EMPLOYEE</h1><p>Name: {w[0]} {w[1]}</p><p>Rank: {w[2]}</p><p>License: {w[3]}</p><h3>STATUS: {w[4]}</h3></div>"
    return "<h1>❌ INVALID ID</h1>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
