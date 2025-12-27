import warnings
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from database import get_vehicle_details
from pathlib import Path
import cv2
import re
import easyocr


BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXT = {"png", "jpg", "jpeg"}

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8MB

warnings.filterwarnings("ignore")



reader = easyocr.Reader(['en'], gpu=False)

def preprocess_image(path):
    img = cv2.imread(str(path))
    if img is None:
        return None

    img = cv2.resize(img, None, fx=1.5, fy=1.5)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blur, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    return thresh


def easy_ocr_extract(image_path):
    try:
        results = reader.readtext(str(image_path), detail=1)

        if not results:
            return "", []

        text = " ".join([r[1] for r in results])

        ocr_raw = []
        for r in results:
            ocr_raw.append({
                "text": r[1],
                "confidence": float(r[2]),
                "bbox": [[int(p[0]), int(p[1])] for p in r[0]]
            })

        return text, ocr_raw

    except Exception as e:
        print("OCR ERROR:", e)
        return "", []


def extract_plate(text):
    if not text or not isinstance(text, str):
        return None

    text = text.upper()

    # Remove junk OCR words
    for junk in ["IND", "INDIA", "WND", "RRA", "ND", "FR", "IN"]:
        text = text.replace(junk, "")

    # Keep only letters & digits
    cleaned = re.sub(r"[^A-Z0-9]", "", text)

    # OCR character corrections
    cleaned = (
        cleaned
        .replace("O", "0")
        .replace("I", "1")
        .replace("Z", "2")
        .replace("S", "5")
        .replace("L", "T")
    )

    # 🔑 Collapse duplicated letters (BNB → NB)
    cleaned = re.sub(r"([A-Z])\1+", r"\1", cleaned)

    # Strict Indian number plate structure
    match = re.search(
        r"([A-Z]{2})([0-9]{1,2})([A-Z]{1,3})([0-9]{4})",
        cleaned
    )

    if not match:
        return None

    state, district, series, number = match.groups()

    return f"{state}{district}{series}{number}"



def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/scan", methods=["POST"])
def scan():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    filename = secure_filename(file.filename)
    save_path = UPLOAD_FOLDER / filename
    file.save(str(save_path))

    print("📸 Image saved:", save_path)

    # Preprocess image
    processed = preprocess_image(save_path)
    if processed is not None:
        cv2.imwrite(str(save_path), processed)

    # OCR
    ocr_text, ocr_raw = easy_ocr_extract(save_path)
    print("OCR TEXT:", ocr_text)

    plate = extract_plate(ocr_text)
    print("FINAL PLATE:", plate)

    if not plate:
        return jsonify({
            "plate_number": None,
            "ocr_text": ocr_text,
            "ocr_raw": ocr_raw,
            "message": "No valid number plate detected"
        }), 200

    details = get_vehicle_details(plate)

    return jsonify({
        "plate_number": plate,
        "vehicle_details": details,
        "ocr_text": ocr_text,
        "ocr_raw": ocr_raw
    }), 200


@app.route("/scan-plate", methods=["POST"])
def scan_plate_postman():
    data = request.get_json()

    if not data or "plate" not in data:
        return jsonify({"error": "Plate number required"}), 400

    corrected_plate = extract_plate(data["plate"])

    if not corrected_plate:
        return jsonify({
            "plate_number": None,
            "vehicle_details": None,
            "message": "Invalid plate format"
        }), 400

    details = get_vehicle_details(corrected_plate)

    if not details:
        return jsonify({
            "plate_number": corrected_plate,
            "vehicle_details": None,
            "message": "Vehicle not found"
        }), 404

    return jsonify({
        "plate_number": corrected_plate,
        "vehicle_details": details
    }), 200


@app.route("/uploads/<name>")
def uploaded_file(name):
    path = UPLOAD_FOLDER / name
    if path.exists():
        return send_file(str(path))
    return "File not found", 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
