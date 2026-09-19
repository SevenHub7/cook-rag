"""聊天问答路由：POST /api/chat（支持 SSE 流式 / JSON 非流式）"""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional

from app.services.rag_service import rag_service
from app.schema.chat_schema import ChatMessage

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500, description="用户问题")
    stream: bool = Field(True, description="true=SSE 流式输出，false=一次性 JSON")
    category: Optional[str] = Field(None, description="前端指定的分类筛选（可选）")
    difficulty: Optional[str] = Field(None, description="前端指定的难度筛选（可选）")
    chat_history: list[ChatMessage] = Field(default=[], description="对话历史")

@router.post("/chat")
def chat(req: ChatRequest):
    if not rag_service.ready:
        raise HTTPException(status_code=503, detail="知识库还在初始化中，请稍后重试")

    if req.stream:
        def event_generator():
            for evt in rag_service.ask_stream(
                req.question, req.chat_history, req.category, req.difficulty
            ):
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    return rag_service.ask(req.question, req.chat_history, req.category, req.difficulty)
