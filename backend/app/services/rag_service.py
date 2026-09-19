"""
RAG 服务层 —— 对 rag_modules 四个核心模块的编排（原 main.py 的 RecipeRAGSystem 改造）

单例模式：FastAPI 启动时（lifespan）调用 initialize() 一次性完成预热
（加载 embedding 模型 + FAISS 向量索引 + 构建 BM25），之后所有请求复用同一实例。
"""

import logging
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from langchain_core.documents import Document

from app.core.config import settings
from rag_modules import (
    DataPreparationModule,
    GenerationIntegrationModule,
    IndexConstructionModule,
    RetrievalOptimizationModule,
)

from app.skills.dish_extract import build_rag_search_query, extract_dish_name_from_search_query

from app.schema.chat_schema import ChatMessage

logger = logging.getLogger(__name__)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


class RAGService:
    """RAG 服务单例"""

    def __init__(self):
        self._initialized = False
        self._lock = threading.Lock()
        self.data_module: Optional[DataPreparationModule] = None
        self.index_module: Optional[IndexConstructionModule] = None
        self.retrieval_module: Optional[RetrievalOptimizationModule] = None
        self.generation_module: Optional[GenerationIntegrationModule] = None

    # ------------------------------------------------------------------
    # 初始化（预热）
    # ------------------------------------------------------------------
    @property
    def ready(self) -> bool:
        return self._initialized

    def initialize(self):
        """加载文档 + 向量索引 + LLM。耗时操作，只在服务启动时跑一次。"""
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return

            if not settings.moonshot_api_key:
                raise ValueError("请在 .env 中设置 MOONSHOT_API_KEY")

            logger.info("RAG 服务预热开始（首次加载约需几十秒）...")

            # 1. 数据准备模块
            self.data_module = DataPreparationModule(settings.data_path)

            # 2. 索引模块（加载/构建 FAISS 向量索引）
            self.index_module = IndexConstructionModule(
                model_name=settings.embedding_model,
                index_save_path=settings.index_save_path,
            )

            vectorstore = self.index_module.load_index()
            if vectorstore is not None:
                logger.info("成功加载已保存的向量索引")
                # 检索模块仍需要文档和分块
                self.data_module.load_documents()
                chunks = self.data_module.chunk_documents()
            else:
                logger.info("未找到已保存的索引，开始构建新索引...")
                self.data_module.load_documents()
                chunks = self.data_module.chunk_documents()
                vectorstore = self.index_module.build_vector_index(chunks)
                self.index_module.save_index()

            # 3. 检索优化模块（向量 + BM25 混合检索）
            self.retrieval_module = RetrievalOptimizationModule(vectorstore, chunks)

            # 4. 生成集成模块（Kimi LLM）
            self.generation_module = GenerationIntegrationModule(
                model_name=settings.llm_model,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )

            self._initialized = True
            stats = self.data_module.get_statistics()
            logger.info(
                "RAG 服务预热完成：文档 %s 篇 / 分块 %s 个 / 分类 %s",
                stats.get("total_documents"),
                stats.get("total_chunks"),
                list(stats.get("categories", {}).keys()),
            )

    # ------------------------------------------------------------------
    # 问答（核心链路，逻辑与原 ask_question 完全一致，去掉了终端打印）
    # ------------------------------------------------------------------
    def _extract_filters(self, query: str) -> Dict[str, str]:
        """从问题中自动提取分类/难度过滤条件（沿用原逻辑）"""
        filters: Dict[str, str] = {}
        for cat in DataPreparationModule.get_supported_categories():
            if cat in query:
                filters["category"] = cat
                break
        for diff in sorted(
            DataPreparationModule.get_supported_difficulties(), key=len, reverse=True
        ):
            if diff in query:
                filters["difficulty"] = diff
                break
        return filters

    def _retrieve(
        self,
        question: str,
        chat_history: List[ChatMessage],
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
    ):
        """完整检索链路：路由 -> Skill指代改写 -> LLM重写兜底 -> 过滤检索 -> 取父文档"""
        # 1. 查询路由
        route = self.generation_module.query_router(question)

        # 2. 【新增】优先调用Skill处理指代问句（怎么做/要什么食材）
        skill_rewritten = build_rag_search_query(user_input=question, chat_history=chat_history)
        logger.info(f"【Skill指代改写】原始question={question}, skill输出={skill_rewritten}, history_len={len(chat_history)}")

        # 2.5 若 skill 改写成功，尝试提取明确菜名，用于检索后精确过滤
        explicit_dish: Optional[str] = None
        if skill_rewritten != question:
            explicit_dish = extract_dish_name_from_search_query(skill_rewritten)
            if explicit_dish:
                logger.info(f"【Skill指代改写】提取明确菜名: {explicit_dish}")

        # 3. 智能查询重写（列表查询保持原样）
        if route == "list":
            rewritten = question
        else:
         # 如果skill改写后的query和原始不一样，优先用skill结果；否则走LLM兜底
            if skill_rewritten != question:
                rewritten = skill_rewritten
            else:
                rewritten = self.generation_module.query_rewrite(question)

        # 4. 过滤条件 = 自动提取 + 前端显式指定（显式优先）
        filters = self._extract_filters(question)
        if category:
            filters["category"] = category
        if difficulty:
            filters["difficulty"] = difficulty

        # 5. 检索
        # list 路径（"推荐一些早餐"这种列表式查询）：不按相似度排序，从符合条件的菜品里随机采样，
        # 避免每个 chunk 都集中到同一道菜上导致反复推荐同一道菜
        if route == "list":
            chunks = self.retrieval_module.random_sample_search(
                rewritten, filters, top_k=settings.top_k
            )
        elif filters:
            chunks = self.retrieval_module.metadata_filtered_search(
                rewritten, filters, top_k=settings.top_k
            )
        else:
            chunks = self.retrieval_module.hybrid_search(
                rewritten, top_k=settings.top_k
            )

        # 5.5 若 skill 已提取明确菜名，只保留该菜名的 chunk（避免同类菜品混入）
        if explicit_dish and chunks:
            filtered = [
                c for c in chunks
                if c.metadata.get("dish_name") == explicit_dish
            ]
            if filtered:
                logger.info(f"【菜名精确过滤】{explicit_dish}: 原 {len(chunks)} 个 chunk -> 过滤后 {len(filtered)} 个")
                chunks = filtered
            else:
                logger.warning(f"【菜名精确过滤】{explicit_dish} 过滤后为空，回退到混合检索结果")

        # 6. 取完整父文档
        parents = self.data_module.get_parent_documents(chunks) if chunks else []
        return route, rewritten, filters, parents

    def _sources(self, docs: List[Document]) -> List[Dict[str, Any]]:
        return [
            {
                "dish_name": d.metadata.get("dish_name", "未知菜品"),
                "category": d.metadata.get("category", "未知"),
                "difficulty": d.metadata.get("difficulty", "未知"),
                "detail_url": f"/api/dishes/{d.metadata.get('dish_name', '')}",
            }
            for d in docs
        ]

    def ask(
        self,
        question: str,
        chat_history: List[ChatMessage],
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
    ) -> Dict[str, Any]:
        """非流式问答，一次性返回完整回答"""
        route, rewritten, filters, parents = self._retrieve(
            question, chat_history, category, difficulty
        )

        if not parents:
            return {
                "route": route,
                "rewritten_query": rewritten,
                "filters": filters,
                "sources": [],
                "answer": "抱歉，没有找到相关的食谱信息。请尝试其他菜品名称或关键词。",
            }

        if route == "list":
            answer = self.generation_module.generate_list_answer(question, parents)
        elif route == "detail":
            answer = self.generation_module.generate_step_by_step_answer(
                question, parents
            )
        else:
            answer = self.generation_module.generate_basic_answer(question, parents)

        return {
            "route": route,
            "rewritten_query": rewritten,
            "filters": filters,
            "sources": self._sources(parents),
            "answer": answer,
        }

    def ask_stream(
        self,
        question: str,
        chat_history: List[ChatMessage],
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """流式问答，逐条 yield 事件字典（SSE 用）

        事件类型：
          meta  -> {"type":"meta", "route":..., "sources":[...]}
          delta -> {"type":"delta", "content":"回答片段"}
          done  -> {"type":"done"}
          error -> {"type":"error", "message":"..."}
        """
        try:
            route, rewritten, filters, parents = self._retrieve(
                question, chat_history, category, difficulty
            )
            yield {
                "type": "meta",
                "route": route,
                "rewritten_query": rewritten,
                "filters": filters,
                "sources": self._sources(parents),
            }

            if not parents:
                yield {
                    "type": "delta",
                    "content": "抱歉，没有找到相关的食谱信息。请尝试其他菜品名称或关键词。",
                }
                yield {"type": "done"}
                return

            if route == "list":
                # 列表回答没有流式接口，整段发出
                yield {
                    "type": "delta",
                    "content": self.generation_module.generate_list_answer(
                        question, parents
                    ),
                }
            elif route == "detail":
                for chunk in self.generation_module.generate_step_by_step_answer_stream(
                    question, parents
                ):
                    yield {"type": "delta", "content": chunk}
            else:
                for chunk in self.generation_module.generate_basic_answer_stream(
                    question, parents
                ):
                    yield {"type": "delta", "content": chunk}

            yield {"type": "done"}
        except Exception as e:  # noqa: BLE001
            logger.exception("问答处理失败")
            yield {"type": "error", "message": str(e)}

    # ------------------------------------------------------------------
    # 菜品目录
    # ------------------------------------------------------------------
    def list_dishes(
        self,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """菜品列表，可按分类/难度/关键词筛选"""
        items = []
        for doc in self.data_module.documents or []:
            m = doc.metadata
            if category and m.get("category") != category:
                continue
            if difficulty and m.get("difficulty") != difficulty:
                continue
            if keyword and keyword not in m.get("dish_name", ""):
                continue
            items.append(
                {
                    "dish_name": m.get("dish_name", ""),
                    "category": m.get("category", ""),
                    "difficulty": m.get("difficulty", ""),
                    "image_url": self._cover_image(doc),
                }
            )
        items.sort(key=lambda x: (x["category"], x["dish_name"]))
        return items

    def get_dish(self, dish_name: str) -> Optional[Dict[str, Any]]:
        """单品详情：完整 Markdown 食谱 + 步骤图片 URL"""
        for doc in self.data_module.documents or []:
            if doc.metadata.get("dish_name") == dish_name:
                return {
                    "dish_name": dish_name,
                    "category": doc.metadata.get("category", ""),
                    "difficulty": doc.metadata.get("difficulty", ""),
                    "content": doc.page_content,
                    "images": self._dish_images(doc),
                }
        return None

    def _rel_static(self, source_path: str) -> str:
        """本地绝对路径 -> /static/dishes/... URL"""
        try:
            rel = (
                Path(source_path)
                .resolve()
                .relative_to(Path(settings.data_path).resolve())
                .as_posix()
            )
            return f"/static/dishes/{rel}"
        except ValueError:
            return ""

    def _dish_images(self, doc: Document) -> List[str]:
        """菜品步骤图：只有 md 独占同名文件夹时，文件夹里的图片才算它的"""
        source = doc.metadata.get("source", "")
        folder = Path(source).parent
        dish_name = doc.metadata.get("dish_name", "")
        if folder.name != dish_name:
            return []
        imgs = sorted(
            p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTS
        )
        return [self._rel_static(str(p)) for p in imgs]

    def _cover_image(self, doc: Document) -> Optional[str]:
        imgs = self._dish_images(doc)
        return imgs[0] if imgs else None

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------
    def get_stats(self) -> Dict[str, Any]:
        stats = (
            self.data_module.get_statistics() if self.data_module else {}
        )
        stats["supported_categories"] = (
            DataPreparationModule.get_supported_categories()
        )
        stats["supported_difficulties"] = (
            DataPreparationModule.get_supported_difficulties()
        )
        stats["ready"] = self._initialized
        return stats


# 全局单例，路由层直接 import 使用
rag_service = RAGService()
