import os
import random
import requests
import urllib.parse
import re
import psycopg2
import cloudinary
import cloudinary.uploader
from datetime import datetime, date
from flask import Flask, request, jsonify, render_template, send_file, Response
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128
from reportlab.lib import colors
from reportlab.lib.units import inch

# --- 1. SECURE CONFIG ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY")
ARKESEL_SENDER_ID = os.environ.get("ARKESEL_SENDER_ID", "PBE_OTP")

# Cloudinary Setup
cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

app = Flask(__name__)

def get_db():
    # This connects to your external database set in Render environment variables
    return psycopg2.connect(DATABASE_URL)

# Initialize Database Table
def init_db():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pbe_master_registry (
                id SERIAL PRIMARY KEY,
                surname VARCHAR(100), firstname VARCHAR(100),
                gender VARCHAR(10), nationality VARCHAR(50),
                pbe_uid VARCHAR(20) UNIQUE, pbe_license VARCHAR(50) UNIQUE,
                rank VARCHAR(50), phone_no VARCHAR(20) UNIQUE,
                photo_url TEXT, otp_code VARCHAR(6), 
                status VARCHAR(20) DEFAULT 'ACTIVE', is_verified BOOLEAN DEFAULT FALSE,
                joined_date DATE DEFAULT CURRENT_DATE
            );
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database init error: {e}")

# Run initialization when the app starts
with app.app_context():
    init_db()

# --- 2. CORE UTILITIES ---
def send_arkesel_sms(phone: str, message: str):
    url = "https://sms.arkesel.com/api/v2/sms/send"
    headers = {"api-key": ARKESEL_API_KEY, "Content-Type": "application/json"}
    payload = {"sender": ARKESEL_SENDER_ID, "message": message, "recipients": [phone]}
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json()
    except: 
        return {"status": "error"}

# --- 3. ROUTES ---

@app.route("/")
def home():
    return """
    <html>
    <head><title>PBE Identity Vault</title></head>
    <body style="font-family:sans-serif; text-align:center; padding-top:100px; background-color:#f4f4f4;">
        <div style="background:white; display:inline-block; padding:50px; border-radius:15px; box-shadow: 0px 4px 15px rgba(0,0,0,0.1);">
            <h1 style="color:#1a3a5a;">POWER BRIDGE ENGINEERING</h1>
            <p style="font-size:1.2em; color:#555;">Identity Vault is <b>ONLINE</b> & Secure.</p>
            <div style="margin-top:20px; padding:10px; background:#e7f3ff; color:#0056b3; border-radius:5px;">
                Status: System Operational (Flask Edition)
            </div>
        </div>
    </body>
    </html>
    """

@app.route("/admin/print-id/<pbe_uid>")
def print_card(pbe_uid):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pbe_master_registry WHERE pbe_uid = %s", (pbe_uid,))
        emp = cursor.fetchone()
        
        if not emp:
            return "Employee not found", 404

        pdf_file = f"PBE_{pbe_uid}.pdf"
        c = canvas.Canvas(pdf_file, pagesize=(3.375*inch, 2.125*inch))
        
        # Identity Card Drawing Logic
        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(colors.black)
        x_data = 1.35 * inch
        
        # Drawing Data from Database
        c.drawString(x_data, 1.83*inch, f"Surname: {str(emp[1])}") 
        c.drawString(x_data, 1.63*inch, f"Firstname: {str(emp[2])}")
        c.drawString(x_data, 1.43*inch, f"Gender: {str(emp[3])}")
        c.drawString(x_data, 1.23*inch, f"UID: {str(emp[5])}")
        c.drawString(x_data, 1.03*inch, f"Rank: {str(emp[7])}")

        # Generate Barcode
        barcode = code128.Code128(emp[5], barHeight=0.2*inch, barWidth=0.8)
        barcode.drawOn(c, 1.1*inch, 0.18*inch)
        
        c.save()
        cursor.close()
        conn.close()
        
        return send_file(pdf_file, mimetype='application/pdf')
    except Exception as e:
        return f"Error generating ID: {str(e)}", 500

if __name__ == "__main__":
    # Render provides the PORT as an environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
