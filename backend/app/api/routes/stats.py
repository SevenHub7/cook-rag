"""知识库统计与健康检查路由"""

from fastapi import APIRouter

from app.services.rag_service import rag_service

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
def stats():
    """知识库统计：文档数、分块数、分类分布、难度分布"""
    return rag_service.get_stats()


@router.get("/health")
def health():
    """健康检查：服务是否就绪"""
    return {"status": "ok" if rag_service.ready else "loading"}
