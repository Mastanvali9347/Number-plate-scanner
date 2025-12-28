import mysql.connector
from mysql.connector import Error
import requests
import re

# ================= DATABASE =================
def get_connection():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="Mastan@12345",
            database="vehicles_db",
            port=3306
        )
    except Error as e:
        print("MySQL Error:", e)
        return None


def init_db():
    con = get_connection()
    if not con:
        return

    cur = con.cursor()

    # USERS TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL
        )
    """)

    # VEHICLES CACHE TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            reg_number VARCHAR(20) PRIMARY KEY,
            owner VARCHAR(100),
            model VARCHAR(100),
            fuel VARCHAR(20),
            reg_date VARCHAR(50),
            vehicle_class VARCHAR(50),
            color VARCHAR(50)
        )
    """)

    # SCAN HISTORY TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scan_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            plate VARCHAR(20) NOT NULL,
            scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX (username),
            INDEX (plate)
        )
    """)

    con.commit()
    cur.close()
    con.close()


# ================= RTO API =================
RTO_API_KEY = "861037d31amsh7470a636ab42985p13688djsnc6489f80bd5a"
RTO_API_HOST = "vehicle-rc-information.p.rapidapi.com"


def fetch_from_rto_api(reg_number):
    url = "https://vehicle-rc-information.p.rapidapi.com/vehicle-rc-details"

    payload = {"vehicleNumber": reg_number}
    headers = {
        "x-rapidapi-key": RTO_API_KEY,
        "x-rapidapi-host": RTO_API_HOST,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            return None

        data = response.json()
        result = data.get("result")

        if not result:
            return None

        return {
            "Registration Number": reg_number,
            "Owner Name": result.get("owner_name"),
            "Vehicle Model": result.get("model"),
            "Fuel Type": result.get("fuel_type"),
            "Registration Date": result.get("registration_date"),
            "Vehicle Class": result.get("vehicle_class"),
            "Color": result.get("color")
        }

    except Exception as e:
        print("RTO API ERROR:", e)
        return None


# ================= CACHE =================
def save_vehicle_to_db(vehicle):
    con = get_connection()
    if not con:
        return

    cur = con.cursor()
    cur.execute("""
        INSERT IGNORE INTO vehicles
        (reg_number, owner, model, fuel, reg_date, vehicle_class, color)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        vehicle["Registration Number"],
        vehicle["Owner Name"],
        vehicle["Vehicle Model"],
        vehicle["Fuel Type"],
        vehicle["Registration Date"],
        vehicle["Vehicle Class"],
        vehicle["Color"]
    ))

    con.commit()
    cur.close()
    con.close()


# ================= HISTORY =================
def save_scan_history(username, plate):
    con = get_connection()
    if not con:
        return

    cur = con.cursor()
    cur.execute("""
        INSERT INTO scan_history (username, plate)
        VALUES (%s, %s)
    """, (username, plate))

    con.commit()
    cur.close()
    con.close()


def get_scan_history(username):
    con = get_connection()
    if not con:
        return []

    cur = con.cursor(dictionary=True)
    cur.execute("""
        SELECT plate, scanned_at
        FROM scan_history
        WHERE username=%s
        ORDER BY scanned_at DESC
    """, (username,))

    rows = cur.fetchall()
    cur.close()
    con.close()
    return rows


# ================= MAIN VEHICLE LOOKUP =================
def get_vehicle_details(plate, username=None):
    normalized = re.sub(r"[^A-Z0-9]", "", plate.upper())

    # 1️⃣ CHECK CACHE
    con = get_connection()
    if con:
        cur = con.cursor(dictionary=True)
        cur.execute("""
            SELECT
                reg_number AS `Registration Number`,
                owner AS `Owner Name`,
                model AS `Vehicle Model`,
                fuel AS `Fuel Type`,
                reg_date AS `Registration Date`,
                vehicle_class AS `Vehicle Class`,
                color AS `Color`
            FROM vehicles
            WHERE UPPER(REPLACE(reg_number,' ',''))=%s
        """, (normalized,))
        row = cur.fetchone()
        cur.close()
        con.close()

        if row:
            if username:
                save_scan_history(username, normalized)
            return row

    # 2️⃣ FETCH FROM RTO
    vehicle = fetch_from_rto_api(normalized)
    if not vehicle:
        return None

    # 3️⃣ SAVE CACHE + HISTORY
    save_vehicle_to_db(vehicle)
    if username:
        save_scan_history(username, normalized)

    return vehicle


# ================= INIT =================
init_db()
