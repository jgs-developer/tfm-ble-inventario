"""Carga datos curados de vulnerabilidades BLE por fabricante (SweynTooth, 2020)."""

from db.database import SessionLocal, init_db
from db.models import VulnerabilidadFabricante

FUENTE = "https://asset-group.github.io/disclosures/sweyntooth/"

VULNERABILIDADES = [
    # (company_id, fabricante, cve_id, nombre, descripcion, severidad)
    (13, "Texas Instruments Inc.", "CVE-2019-17520", "Public Key Crash",
     "Un paquete con clave publica malformada provoca la caida del dispositivo (DoS).", "Media"),
    (13, "Texas Instruments Inc.", "CVE-2019-19193", "Invalid Connection Request",
     "Una peticion de conexion invalida provoca la caida del dispositivo (DoS).", "Media"),
    (37, "NXP Semiconductors (formerly Philips Semiconductors)", "CVE-2019-17519", "Link Layer Length Overflow",
     "Un paquete con el campo de longitud manipulado provoca denegacion de servicio.", "Media"),
    (37, "NXP Semiconductors (formerly Philips Semiconductors)", "CVE-2019-17060", "LLID Deadlock",
     "Una secuencia de paquetes provoca un bloqueo (deadlock) que fuerza el reinicio del dispositivo.", "Media"),
    (48, "ST Microelectronics", "CVE-2019-19192", "Sequential ATT Deadlock",
     "Una secuencia de peticiones ATT provoca un bloqueo del dispositivo.", "Media"),
    (205, "Microchip Technology Inc.", "CVE-2019-19195", "Invalid L2CAP Fragment",
     "Un fragmento L2CAP invalido provoca la caida del dispositivo (DoS).", "Media"),
    (210, "Dialog Semiconductor B.V.", "CVE-2019-17517", "Truncated L2CAP",
     "Un paquete L2CAP truncado provoca la caida del dispositivo (DoS). Afecta a DA14580.", "Media"),
    (210, "Dialog Semiconductor B.V.", "CVE-2019-17518", "Silent Length Overflow",
     "Un paquete con longitud de payload mayor a la esperada provoca desbordamiento de bufer. Afecta a DA1468x.", "Media"),
    (305, "Cypress Semiconductor", "CVE-2019-16336", "Link Layer Length Overflow",
     "Un paquete con el campo de longitud manipulado provoca denegacion de servicio.", "Media"),
    (305, "Cypress Semiconductor", "CVE-2019-17061", "LLID Deadlock",
     "Una secuencia de paquetes provoca un bloqueo (deadlock) que fuerza el reinicio del dispositivo.", "Media"),
    (529, "Telink Semiconductor Co. Ltd", "CVE-2019-19196", "Key Size Overflow",
     "Un tamano de clave de cifrado manipulado provoca la caida del dispositivo (DoS).", "Media"),
    (529, "Telink Semiconductor Co. Ltd", "CVE-2019-19194", "Zero LTK Installation",
     "Permite instalar una clave de sesion (LTK) de longitud cero, saltandose por completo el "
     "emparejamiento seguro BLE. Un atacante en rango puede acceder a funciones reservadas al "
     "propietario sin autenticarse.", "Critica"),
]


def cargar() -> None:
    init_db()
    db = SessionLocal()
    try:
        existentes = {
            v.cve_id for v in db.query(VulnerabilidadFabricante.cve_id).all()
        }
        insertadas = 0
        for company_id, fabricante, cve_id, nombre, descripcion, severidad in VULNERABILIDADES:
            if cve_id in existentes:
                continue
            db.add(VulnerabilidadFabricante(
                company_id=company_id,
                fabricante=fabricante,
                cve_id=cve_id,
                nombre_vulnerabilidad=nombre,
                descripcion=descripcion,
                severidad=severidad,
                fuente_url=FUENTE,
            ))
            insertadas += 1
        db.commit()
        print(f"Vulnerabilidades insertadas: {insertadas} (ya existentes: {len(existentes)})")
    finally:
        db.close()


if __name__ == "__main__":
    cargar()
