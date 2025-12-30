import mysql.connector
from mysql.connector import Error
import requests
import re

RTO_API_KEY = "861037d31amsh7470a636ab42985p13688djsnc6489f80bd5a"
RTO_API_HOST = "vehicle-rc-information.p.rapidapi.com"
RTO_URL = "https://vehicle-rc-information.p.rapidapi.com/vehicle-rc-details"


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


# ================= AUTO MIGRATION =================
def migrate_vehicles_table():
    con = get_connection()
    if not con:
        return

    cur = con.cursor()
    cur.execute("SHOW COLUMNS FROM vehicles")
    columns = [c[0] for c in cur.fetchall()]

    migrations = {
        "owner": "ALTER TABLE vehicles CHANGE owner owner_name VARCHAR(100)",
        "model": "ALTER TABLE vehicles CHANGE model vehicle_model VARCHAR(100)",
        "fuel": "ALTER TABLE vehicles CHANGE fuel fuel_type VARCHAR(20)",
        "reg_date": "ALTER TABLE vehicles CHANGE reg_date registration_date VARCHAR(50)"
    }

    for old_col, sql in migrations.items():
        if old_col in columns:
            try:
                cur.execute(sql)
            except:
                pass

    if "created_at" not in columns:
        try:
            cur.execute(
                "ALTER TABLE vehicles ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            )
        except:
            pass

    con.commit()
    cur.close()
    con.close()


# ================= INIT DB =================
def init_db():
    con = get_connection()
    if not con:
        return

    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            reg_number VARCHAR(20) PRIMARY KEY,
            owner_name VARCHAR(100),
            vehicle_model VARCHAR(100),
            fuel_type VARCHAR(20),
            registration_date VARCHAR(50),
            vehicle_class VARCHAR(50),
            color VARCHAR(50)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scan_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            plate VARCHAR(20) NOT NULL,
            scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX (user_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    con.commit()
    cur.close()
    con.close()

    migrate_vehicles_table()


# ================= RTO API =================
def fetch_from_rto_api(reg_number):
    payload = {"vehicleNumber": reg_number}
    headers = {
        "x-rapidapi-key": RTO_API_KEY,
        "x-rapidapi-host": RTO_API_HOST,
        "Content-Type": "application/json"
    }

    try:
        res = requests.post(RTO_URL, json=payload, headers=headers, timeout=10)
        if res.status_code != 200:
            return None

        result = res.json().get("result")
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
        print("RTO API Error:", e)
        return None


# ================= SAVE VEHICLE =================
def save_vehicle(vehicle):
    con = get_connection()
    if not con:
        return

    cur = con.cursor()
    cur.execute("""
        INSERT INTO vehicles
        (reg_number, owner_name, vehicle_model, fuel_type, registration_date, vehicle_class, color)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
            owner_name=VALUES(owner_name),
            vehicle_model=VALUES(vehicle_model),
            fuel_type=VALUES(fuel_type),
            registration_date=VALUES(registration_date),
            vehicle_class=VALUES(vehicle_class),
            color=VALUES(color)
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


# ================= SCAN HISTORY =================
def save_scan(user_id, plate):
    con = get_connection()
    if not con:
        return

    cur = con.cursor()
    cur.execute(
        "INSERT INTO scan_history (user_id, plate) VALUES (%s,%s)",
        (user_id, plate)
    )
    con.commit()
    cur.close()
    con.close()


def get_scan_history(user_id):
    con = get_connection()
    if not con:
        return []

    cur = con.cursor(dictionary=True)
    cur.execute("""
        SELECT plate, scanned_at
        FROM scan_history
        WHERE user_id=%s
        ORDER BY scanned_at DESC
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    con.close()
    return rows


# ================= VEHICLE LOOKUP =================
def get_vehicle_details(plate, user_id=None):
    normalized = re.sub(r"[^A-Z0-9]", "", plate.upper())

    con = get_connection()
    if not con:
        return None

    cur = con.cursor(dictionary=True)
    cur.execute("""
        SELECT
            reg_number AS `Registration Number`,
            owner_name AS `Owner Name`,
            vehicle_model AS `Vehicle Model`,
            fuel_type AS `Fuel Type`,
            registration_date AS `Registration Date`,
            vehicle_class AS `Vehicle Class`,
            color AS `Color`
        FROM vehicles
        WHERE UPPER(REPLACE(reg_number,' ',''))=%s
    """, (normalized,))
    row = cur.fetchone()
    cur.close()
    con.close()

    if row:
        if user_id:
            save_scan(user_id, normalized)
        return row

    vehicle = fetch_from_rto_api(normalized)
    if not vehicle:
        return None

    save_vehicle(vehicle)
    if user_id:
        save_scan(user_id, normalized)

    return vehicle


init_db()
