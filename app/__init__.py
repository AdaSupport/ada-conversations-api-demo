import secrets
from nicegui import ui

from app.server import configure_endpoints

def start_web_server():
    configure_endpoints()
    storage_secret = secrets.token_hex(16)
    ui.run(storage_secret=storage_secret)
