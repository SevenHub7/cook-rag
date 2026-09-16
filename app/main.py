"""
cook-rag 后端入口

启动方式（在 cook-rag-backend/ 目录下，先激活你的 Python 环境）：
    ./run.sh
    或
    python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

首次启动会加载 embedding 模型 + FAISS 索引，约需几十秒，属正常现象。
接口文档（启动后自动可用）：http://localhost:8000/docs
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import chat_router, dishes_router, stats_router
from app.core.config import settings
from app.services.rag_service import rag_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时预热 RAG（加载模型 + 索引），放在线程池里跑不阻塞事件循环"""
    logger.info("正在预热 RAG 服务（首次约需几十秒）...")
    await asyncio.to_thread(rag_service.initialize)
    logger.info("预热完成，服务就绪")
    yield
    # 暂无需清理逻辑


app = FastAPI(
    title="cook-rag API",
    description="尝试尝咸淡 RAG 食谱问答后端",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS：开发阶段前端 Vite 跑在 5173 端口（虽然 dev proxy 已转发，这里双保险）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 菜品图片静态服务：/static/dishes/breakfast/xxx.jpg
app.mount(
    "/static/dishes",
    StaticFiles(directory=settings.data_path),
    name="dishes",
)

app.include_router(chat_router)
app.include_router(dishes_router)
app.include_router(stats_router)


@app.get("/")
def root():
    return {
        "name": "cook-rag API",
        "docs": "/docs",
        "endpoints": [
            "POST /api/chat",
            "GET /api/dishes",
            "GET /api/dishes/{dish_name}",
            "GET /api/stats",
            "GET /api/health",
        ],
    }
