"""菜品目录路由"""

from fastapi import APIRouter, HTTPException
from typing import Optional

from app.services.rag_service import rag_service

router = APIRouter(prefix="/api", tags=["dishes"])


@router.get("/dishes")
def list_dishes(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    keyword: Optional[str] = None,
):
    """菜品列表，可按分类（荤菜/素菜/...）、难度（简单/中等/...）、菜名关键词筛选"""
    if not rag_service.ready:
        raise HTTPException(status_code=503, detail="知识库还在初始化中，请稍后重试")
    items = rag_service.list_dishes(category, difficulty, keyword)
    return {"total": len(items), "dishes": items}


@router.get("/dishes/{dish_name}")
def get_dish(dish_name: str):
    """单品详情：完整 Markdown 食谱 + 步骤图片"""
    if not rag_service.ready:
        raise HTTPException(status_code=503, detail="知识库还在初始化中，请稍后重试")
    detail = rag_service.get_dish(dish_name)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"未找到菜品: {dish_name}")
    return detail
