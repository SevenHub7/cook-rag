from .chat import router as chat_router
from .dishes import router as dishes_router
from .stats import router as stats_router

__all__ = ["chat_router", "dishes_router", "stats_router"]
