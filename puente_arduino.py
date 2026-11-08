import os
import time

import requests
import serial
import serial.tools.list_ports
from dotenv import load_dotenv

load_dotenv()  # lee el archivo .env de esta carpeta

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8081")
USUARIO = os.getenv("PUENTE_USUARIO")
PASSWORD = os.getenv("PUENTE_PASSWORD")
INTERVALO = float(os.getenv("INTERVALO", "1"))

if not USUARIO or not PASSWORD:
    raise SystemExit("Faltan PUENTE_USUARIO y PUENTE_PASSWORD en el archivo .env")


def buscar_puerto():
    for p in serial.tools.list_ports.comports():
        desc = (p.description + " " + (p.manufacturer or "")).lower()
        if any(k in desc for k in ("ch340", "arduino", "usb serial", "qinheng")):
            return p.device
    return None


def conectar_arduino():
    while True:
        puerto = buscar_puerto()
        if puerto:
            try:
                ard = serial.Serial(puerto, 9600, timeout=1)
                time.sleep(2)  # el Arduino se reinicia al abrir el puerto
                print(f"Arduino conectado en {puerto}")
                return ard
            except serial.SerialException as e:
                print("No se pudo abrir el puerto:", e)
        else:
            print("Arduino no encontrado, reintentando...")
        time.sleep(3)


def login():
    r = requests.post(
        f"{BACKEND}/api/auth/login",
        json={"documento": USUARIO, "contrasenna": PASSWORD},  # ajusta a tu API
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["token"]  # ajusta si el campo se llama distinto


def main():
    ard = conectar_arduino()
    token = None

    while True:
        try:
            if token is None:
                token = login()
                print("Sesión iniciada")

            r = requests.get(
                f"{BACKEND}/api/arduino/pendiente",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )

            if r.status_code in (401, 403):
                print("Token rechazado, iniciando sesión de nuevo...")
                token = None
                continue

            if r.status_code == 200:
                id_material = r.json()["idMaterial"]
                print("Orden recibida:", id_material)
                ard.write(f"{id_material}\n".encode())

        except serial.SerialException:
            print("Se perdió el Arduino, reconectando...")
            ard = conectar_arduino()
        except requests.RequestException as e:
            print("Backend no disponible:", e)
            token = None

        time.sleep(INTERVALO)


if __name__ == "__main__":
    main()