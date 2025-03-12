from nicegui import app

from app.server.webhooks import router as webhooks_router
from app.webpage.index import router as index_router


def configure_endpoints():
    app.include_router(webhooks_router)
    app.include_router(index_router)
