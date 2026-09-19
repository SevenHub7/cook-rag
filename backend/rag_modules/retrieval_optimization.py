"""
检索优化模块
"""

import logging
import hashlib
import random
from typing import List, Dict, Any

from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

class RetrievalOptimizationModule:
    """检索优化模块 - 负责混合检索和过滤"""
    
    def __init__(self, vectorstore: FAISS, chunks: List[Document]):
        """
        初始化检索优化模块
        
        Args:
            vectorstore: FAISS向量存储
            chunks: 文档块列表
        """
        self.vectorstore = vectorstore
        self.chunks = chunks
        self.setup_retrievers()

    def setup_retrievers(self):
        """设置向量检索器和BM25检索器"""
        logger.info("正在设置检索器...")

        # 向量检索器
        self.vector_retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 100}
        )

        # BM25检索器
        self.bm25_retriever = BM25Retriever.from_documents(
            self.chunks,
            k=100
        )

        logger.info("检索器设置完成")
    

    def random_sample_search(self, query: str, filters: Dict[str, Any], top_k: int = 5) -> List[Document]:
        """
        随机采样检索 - 完全不依赖FAISS/BM25，直接从符合条件的父文档中随机采样
        专用于list推荐查询，彻底解决同一道菜反复出现的问题
        """
        logger.info(f"[RandomSample] 从 {len(self.chunks)} 个chunk中按filters={filters}随机采样top_k={top_k}")

        # 1. 按filters筛选所有chunk
        candidate_chunks = []
        for chunk in self.chunks:
            match = True
            for key, value in filters.items():
                if key in chunk.metadata:
                    if isinstance(value, list):
                        if chunk.metadata[key] not in value:
                            match = False
                            break
                    else:
                        if chunk.metadata[key] != value:
                            match = False
                            break
                else:
                    match = False
                    break
            if match:
                candidate_chunks.append(chunk)

        if not candidate_chunks:
            logger.warning(f"[RandomSample] 无符合条件的chunk，回退到hybrid_search")
            return self.hybrid_search(query, top_k)

        logger.info(f"[RandomSample] 符合条件chunk数: {len(candidate_chunks)}")

        # 2. 按parent_id分组，每个父文档只取一个代表chunk
        parent_map = {}
        for chunk in candidate_chunks:
            pid = chunk.metadata.get('parent_id', '')
            if pid and pid not in parent_map:
                parent_map[pid] = chunk

        parent_chunks = list(parent_map.values())
        logger.info(f"[RandomSample] 去重后父文档数: {len(parent_chunks)}")

        # 3. 随机打乱后取top_k
        random.shuffle(parent_chunks)
        sampled = parent_chunks[:top_k]

        dish_names = [c.metadata.get('dish_name', '?') for c in sampled]
        logger.info(f"[RandomSample] 最终采样: {dish_names}")

        return sampled
    def hybrid_search(self, query: str, top_k: int = 3) -> List[Document]:
        """
        混合检索 - 结合向量检索和BM25检索，使用RRF重排
        注入随机query扰动，使推荐结果多样化

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            检索到的文档列表
        """
        # 随机query扰动：给查询加一个随机关键词，让embedding向量偏移到不同方向
        # 从而每次搜索命中不同的文档区域，避免永远返回同一道菜
        boosters = ["家常", "美味", "营养", "健康", "经典", "传统", "特色", "简单", "快手", "下饭", "清淡", "鲜美", "香浓", "地道", "正宗"]
        booster = random.choice(boosters)
        augmented_query = query + " " + booster
        logger.info(f"[RandomBoost] query='{query}' booster='{booster}' augmented='{augmented_query}'")

        # 分别获取向量检索和BM25检索结果（使用增强后的query）
        vector_docs = self.vector_retriever.invoke(augmented_query)
        bm25_docs = self.bm25_retriever.invoke(query)  # BM25用原始query保证关键词匹配

        # 使用RRF重排
        reranked_docs = self._rrf_rerank(vector_docs, bm25_docs)
        return reranked_docs[:top_k]
    
    def metadata_filtered_search(self, query: str, filters: Dict[str, Any], top_k: int = 5) -> List[Document]:
        """
        带元数据过滤的检索
        
        Args:
            query: 查询文本
            filters: 元数据过滤条件
            top_k: 返回结果数量
            
        Returns:
            过滤后的文档列表
        """
        # 先进行混合检索，获取更多候选（hybrid_search内部已有随机扰动）
        docs = self.hybrid_search(query, top_k * 5)
        
        # 应用元数据过滤
        filtered_docs = []
        for doc in docs:
            match = True
            for key, value in filters.items():
                if key in doc.metadata:
                    if isinstance(value, list):
                        if doc.metadata[key] not in value:
                            match = False
                            break
                    else:
                        if doc.metadata[key] != value:
                            match = False
                            break
                else:
                    match = False
                    break
            
            if match:
                filtered_docs.append(doc)
                if len(filtered_docs) >= top_k:
                    break
        
        return filtered_docs

    def _rrf_rerank(self, vector_docs: List[Document], bm25_docs: List[Document], k: int = 60) -> List[Document]:
        """
        使用RRF (Reciprocal Rank Fusion) 算法重排文档

        Args:
            vector_docs: 向量检索结果
            bm25_docs: BM25检索结果
            k: RRF参数，用于平滑排名

        Returns:
            重排后的文档列表（每个父文档只保留最相关的一个chunk）
        """
        doc_scores = {}
        doc_objects = {}

        # 计算向量检索结果的RRF分数
        for rank, doc in enumerate(vector_docs):
            # 使用文档内容的确定性哈希作为唯一标识
            doc_id = hashlib.md5(doc.page_content.encode('utf-8')).hexdigest()
            doc_objects[doc_id] = doc

            # RRF公式: 1 / (k + rank)
            rrf_score = 1.0 / (k + rank + 1)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score

            logger.debug(f"向量检索 - 文档{rank+1}: RRF分数 = {rrf_score:.4f}")

        # 计算BM25检索结果的RRF分数
        for rank, doc in enumerate(bm25_docs):
            doc_id = hashlib.md5(doc.page_content.encode('utf-8')).hexdigest()
            doc_objects[doc_id] = doc

            rrf_score = 1.0 / (k + rank + 1)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score

            logger.debug(f"BM25检索 - 文档{rank+1}: RRF分数 = {rrf_score:.4f}")

        # 按最终RRF分数排序
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

        # 构建最终结果 - 每个父文档只保留最相关的一个chunk（提升多样性）
        seen_parents = set()
        reranked_docs = []
        for doc_id, final_score in sorted_docs:
            if doc_id in doc_objects:
                doc = doc_objects[doc_id]
                parent_id = doc.metadata.get('parent_id', '')
                # 跳过已出现过的父文档，确保结果多样性
                if parent_id in seen_parents:
                    continue
                seen_parents.add(parent_id)
                # 将RRF分数添加到文档元数据中
                doc.metadata['rrf_score'] = final_score
                reranked_docs.append(doc)
                logger.debug(f"最终排序 - 文档: {doc.page_content[:50]}... 最终RRF分数: {final_score:.4f}")

        logger.info(f"RRF重排完成: 向量检索{len(vector_docs)}个文档, BM25检索{len(bm25_docs)}个文档, 合并后{len(reranked_docs)}个文档")

        return reranked_docs
