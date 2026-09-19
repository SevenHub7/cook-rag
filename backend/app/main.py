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

from dotenv import load_dotenv
import os

# 获取 main.py 文件的路径，向上一层到项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(BASE_DIR, ".env")
load_dotenv(env_path)

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
    """启动时阻塞预热 RAG（加载模型 + 索引），完成后才开始接受请求。"""
    logger.info("RAG 服务预热开始（首次约需几十秒）...")
    try:
        await asyncio.to_thread(rag_service.initialize)
        logger.info("RAG 服务预热完成，开始监听请求")
    except Exception:
        logger.exception("RAG 服务预热失败，启动中止")
        raise
    yield


app = FastAPI(
    title="cook-rag API",
    description="一日三餐 RAG 食谱问答后端",
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
