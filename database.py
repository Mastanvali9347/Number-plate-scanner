import mysql.connector
from mysql.connector import Error
import requests
import re

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
    if con is None:
        return

    cur = con.cursor()
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
    con.commit()
    cur.close()
    con.close()

RTO_API_KEY = "861037d31amsh7470a636ab42985p13688djsnc6489f80bd5a"
RTO_API_HOST = "vehicle-rc-information.p.rapidapi.com"

def fetch_from_rto_api(reg_number):
    url = "https://rapidapi.com/fatehbrar92/api/vehicle-rc-information"
    payload = {"vehicleNumber": reg_number}
    headers = {
        "x-rapidapi-key": RTO_API_KEY,
        "x-rapidapi-host": RTO_API_HOST,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code != 200:
            return None

        data = response.json()
        if not data.get("result"):
            return None

        r = data["result"]
        return {
            "Registration Number": reg_number,
            "Owner Name": r.get("owner_name"),
            "Vehicle Model": r.get("model"),
            "Fuel Type": r.get("fuel_type"),
            "Registration Date": r.get("registration_date"),
            "Vehicle Class": r.get("vehicle_class"),
            "Color": r.get("color")
        }
    except:
        return None

def save_vehicle_to_db(vehicle):
    con = get_connection()
    if con is None:
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
    con.commit()
    cur.close()
    con.close()

def get_vehicle_details(plate):
    normalized = re.sub(r"[^A-Z0-9]", "", plate.upper())

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
            return row

    vehicle = fetch_from_rto_api(normalized)
    if not vehicle:
        return None

    save_vehicle_to_db(vehicle)
    return vehicle

init_db()
