"""Inicializa ble_inventory.db con el esquema de db/models.py."""

from db.database import init_db

if __name__ == "__main__":
    init_db()
    print("Base de datos inicializada: ble_inventory.db")
