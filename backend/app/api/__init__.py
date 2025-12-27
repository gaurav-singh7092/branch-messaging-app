from .customers import router as customers_router
from .agents import router as agents_router
from .conversations import router as conversations_router
from .canned_messages import router as canned_messages_router
from .search import router as search_router
from .websocket import router as websocket_router
from .external import router as external_router

__all__ = [
    "customers_router",
    "agents_router", 
    "conversations_router",
    "canned_messages_router",
    "search_router",
    "websocket_router",
    "external_router"
]
