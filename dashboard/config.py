"""Configuración del dashboard vía variables de entorno (o .env)."""

import os

from dotenv import load_dotenv

load_dotenv()

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")
