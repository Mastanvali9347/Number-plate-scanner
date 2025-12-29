import mysql.connector
from mysql.connector import Error
import requests
import re

RTO_API_KEY = "861037d31amsh7470a636ab42985p13688djsnc6489f80bd5a"
RTO_API_HOST = "vehicle-rc-information.p.rapidapi.com"


def get_connection():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="Mastan@12345",
            database="vehicles_db",
            port=3306,
            autocommit=True
        )
    except Error as e:
        print("MySQL Error:", e)
        return None


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
            owner VARCHAR(100),
            model VARCHAR(100),
            fuel VARCHAR(20),
            reg_date VARCHAR(50),
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
            INDEX (plate),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cur.close()
    con.close()


def fetch_from_rto_api(reg_number):
    url = "https://vehicle-rc-information.p.rapidapi.com/vehicle-rc-details"

    headers = {
        "x-rapidapi-key": RTO_API_KEY,
        "x-rapidapi-host": RTO_API_HOST,
        "Content-Type": "application/json"
    }

    payload = {"vehicleNumber": reg_number}

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
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


def save_vehicle(vehicle):
    con = get_connection()
    if not con:
        return

    cur = con.cursor()
    cur.execute("""
        INSERT IGNORE INTO vehicles
        (reg_number, owner, model, fuel, reg_date, vehicle_class, color)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (
        vehicle["Registration Number"],
        vehicle["Owner Name"],
        vehicle["Vehicle Model"],
        vehicle["Fuel Type"],
        vehicle["Registration Date"],
        vehicle["Vehicle Class"],
        vehicle["Color"]
    ))
    cur.close()
    con.close()


def save_scan(user_id, plate):
    con = get_connection()
    if not con:
        return

    cur = con.cursor()
    cur.execute(
        "INSERT INTO scan_history (user_id, plate) VALUES (%s,%s)",
        (user_id, plate)
    )
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


def get_vehicle_details(plate, user_id):
    normalized = re.sub(r"[^A-Z0-9]", "", plate.upper())

    con = get_connection()
    if not con:
        return None

    cur = con.cursor(dictionary=True)
    cur.execute("""
        SELECT
            reg_number AS 'Registration Number',
            owner AS 'Owner Name',
            model AS 'Vehicle Model',
            fuel AS 'Fuel Type',
            reg_date AS 'Registration Date',
            vehicle_class AS 'Vehicle Class',
            color AS 'Color'
        FROM vehicles
        WHERE UPPER(REPLACE(reg_number,' ',''))=%s
    """, (normalized,))

    row = cur.fetchone()
    cur.close()
    con.close()

    if row:
        save_scan(user_id, normalized)
        return row

    vehicle = fetch_from_rto_api(normalized)
    if vehicle:
        save_vehicle(vehicle)
        save_scan(user_id, normalized)
        return vehicle

    return None


init_db()
