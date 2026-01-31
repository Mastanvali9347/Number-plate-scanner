import warnings
import uuid
import jwt
import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from pathlib import Path
from io import BytesIO
import cv2
import re
import easyocr

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from database import (
    get_vehicle_details,
    get_scan_history,
    get_connection
)

warnings.filterwarnings("ignore")
app = Flask(__name__)

CORS(app)

JWT_SECRET = "jwt-super-secret-key"
JWT_ALGO = "HS256"
JWT_EXPIRE_MIN = 120

BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXT = {"png", "jpg", "jpeg"}

reader = easyocr.Reader(["en"], gpu=False)

# ================= JWT HELPERS =================
def create_token(user_id, username):
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=JWT_EXPIRE_MIN)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def jwt_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization")

        if not auth or not auth.startswith("Bearer "):
            return jsonify({"error": "Unauthorized"}), 401

        token = auth.split(" ")[1]

        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
            request.user_id = payload["user_id"]
            request.username = payload["username"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return fn(*args, **kwargs)
    return wrapper

# ================= IMAGE PROCESS =================
def preprocess_image(path):
    img = cv2.imread(str(path))
    if img is None:
        return None

    img = cv2.resize(img, None, fx=2, fy=2)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 13, 15, 15)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh

def easy_ocr_extract(path):
    try:
        res = reader.readtext(str(path), detail=0, paragraph=True)
        return " ".join(res)
    except Exception:
        return ""

# ================= PLATE EXTRACTION =================
def extract_plate(text):
    if not text:
        return None

    text = text.upper()
    for junk in ["IND", "INDIA", "GOVT", "IN", "DL"]:
        text = text.replace(junk, "")

    text = (
        text.replace("O", "0")
            .replace("I", "1")
            .replace("Z", "2")
            .replace("S", "5")
            .replace("B", "8")
    )

    text = re.sub(r"[^A-Z0-9]", "", text)

    patterns = [
        r"[A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{4}",
        r"[A-Z]{2}[0-9]{2}[A-Z][0-9]{4}",
        r"[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{3,4}"
    ]

    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(0)

    return None

# ================= ROUTES =================
@app.route("/")
def index():
    return render_template("index.html")

# ================= AUTH =================
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Missing fields"}), 400

    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT id FROM users WHERE username=%s", (username,))
    if cur.fetchone():
        return jsonify({"error": "User exists"}), 409

    cur.execute(
        "INSERT INTO users (username, password) VALUES (%s,%s)",
        (username, generate_password_hash(password))
    )
    con.commit()
    cur.close()
    con.close()

    return jsonify({"success": True})

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    con = get_connection()
    cur = con.cursor(dictionary=True)

    cur.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = cur.fetchone()

    cur.close()
    con.close()

    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    token = jwt.encode({
        "user_id": user["id"],
        "username": user["username"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, JWT_SECRET, algorithm=JWT_ALGO)

    return jsonify({"token": token})

# ================= PROFILE =================
@app.route("/profile", methods=["GET"])
@jwt_required
def profile():
    con = get_connection()
    cur = con.cursor(dictionary=True)

    cur.execute(
        "SELECT COUNT(*) AS total FROM scan_history WHERE user_id=%s",
        (request.user_id,)
    )
    total = cur.fetchone()["total"]

    cur.execute(
        "SELECT scanned_at FROM scan_history WHERE user_id=%s ORDER BY scanned_at DESC LIMIT 1",
        (request.user_id,)
    )
    last = cur.fetchone()

    cur.close()
    con.close()

    return jsonify({
        "username": request.username,
        "total_scans": total,
        "last_scan": last["scanned_at"] if last else "N/A"
    })

# ================= SCAN =================
@app.route("/scan", methods=["POST"])
@jwt_required
def scan():
    file = request.files.get("image")
    if not file:
        return jsonify({"error": "No image uploaded"}), 400

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"error": "Invalid file type"}), 400

    filename = f"{uuid.uuid4().hex}.{ext}"
    path = UPLOAD_FOLDER / filename
    file.save(path)

    processed = preprocess_image(path)
    if processed is not None:
        cv2.imwrite(str(path), processed)

    text = easy_ocr_extract(path)
    plate = extract_plate(text)

    if not plate:
        return jsonify({
            "success": False,
            "message": "OCR completed but no valid number plate detected",
            "ocr_text": text
        }), 200

    details = get_vehicle_details(plate, request.user_id)

    return jsonify({
        "success": True,
        "plate": plate,
        "ocr_text": text,
        "source": details.get("source"),
        "vehicle": {
            "registration_number": details.get("Registration Number"),
            "owner": details.get("Owner Name"),
            "model": details.get("Vehicle Model"),
            "fuel": details.get("Fuel Type"),
            "registration_date": details.get("Registration Date"),
            "vehicle_class": details.get("Vehicle Class"),
            "color": details.get("Color")
        }
    })

# ================= HISTORY =================
@app.route("/history")
@jwt_required
def history():
    rows = get_scan_history(request.user_id)
    return jsonify([
        {"registration_number": r["plate"], "time": r["scanned_at"]}
        for r in rows
    ])

# ================= PDF =================
@app.route("/download-report", methods=["POST"])
@jwt_required
def download_report():
    data = request.get_json()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    y = 800
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "Vehicle Scan Report")
    y -= 40

    pdf.setFont("Helvetica", 12)
    for k, v in data.items():
        pdf.drawString(50, y, f"{k}: {v}")
        y -= 20

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="vehicle_report.pdf",
        mimetype="application/pdf"
    )

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
