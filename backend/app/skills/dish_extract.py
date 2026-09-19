import re
from typing import List, Optional
from app.schema.chat_schema import ChatMessage
from app.core.config import SHORT_REFERENCE_QUERIES

def extract_dish_by_recent_assistant(text: str) -> Optional[str]:
    """
    从 assistant 上一轮消息中提取菜品名称。
    兼容 markdown 加粗、普通文本等格式。
    匹配样例：
      "为您推荐：燕麦鸡蛋饼"
      "**为您推荐：燕麦鸡蛋饼**"
      "为您推荐：**燕麦鸡蛋饼**"
    """
    if not text:
        return None

    # 去掉常见 markdown 标记的干扰，只保留候选文本
    patterns = [
        r"为您推荐[：:]\s*\*{0,2}([^\n，。；\*]+?)\*{0,2}(?=\s|$|[，。；\n])",
        r"推荐[：:]\s*\*{0,2}([^\n，。；\*]+?)\*{0,2}(?=\s|$|[，。；\n])",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            dish = match.group(1).strip()
            if dish:
                return dish
    return None

def extract_dish_name_from_search_query(query: str) -> Optional[str]:
    """
    从 skill 改写后的检索 query 中提取菜名。
    格式样例："燕麦鸡蛋饼 菜谱 详细做法" -> "燕麦鸡蛋饼"
    """
    if not query:
        return None
    match = re.search(r"^(.*?)\s+菜谱\s+详细做法$", query)
    if match:
        return match.group(1).strip()
    return None


def build_rag_search_query(user_input: str, chat_history: List[ChatMessage]) -> str:
    """
    判断用户输入是否是指代短句，自动改写RAG检索词
    :param user_input: 用户当前输入文本，如 "怎么做？"
    :param chat_history: 完整对话历史 List[ChatMessage]
    :return: 用于向量检索的query
    """
    user_input = user_input.strip()

    # 不是指代短句，直接返回原query
    if user_input not in SHORT_REFERENCE_QUERIES:
        return user_input

    # 倒序找最后一条assistant消息
    last_assistant_msg = None
    for msg in reversed(chat_history):
        if msg.role == "assistant":
            last_assistant_msg = msg.content
            break

    if last_assistant_msg is None:
        return user_input

    dish_name = extract_dish_by_recent_assistant(last_assistant_msg)
    if dish_name:
        return f"{dish_name} 菜谱 详细做法"
    else:
        return user_input