"""Configuración del agente vía variables de entorno (o .env)."""

import os

from dotenv import load_dotenv

load_dotenv()

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")
SCAN_DURATION_SECONDS = int(os.environ.get("SCAN_DURATION_SECONDS", "30"))
SCAN_INTERVAL_SECONDS = int(os.environ.get("SCAN_INTERVAL_SECONDS", "5"))
