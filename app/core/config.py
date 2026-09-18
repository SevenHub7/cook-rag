"""
后端统一配置 —— 用 pydantic-settings 读取 .env
环境变量键名与原版 .env 完全一致，旧的 .env 不用改
"""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（cook-rag-backend/）
BACKEND_ROOT = Path(__file__).resolve().parents[2]

# 指代短句：用户输入这些词时，RAG 检索需要从对话历史里取出最近推荐的菜品名
# 作为新的检索 query（避免 LLM 在"怎么做？"这种零指代输入上瞎猜）
SHORT_REFERENCE_QUERIES = {
    "怎么做？",
    "做法？",
    "教程？",
    "详细步骤？",
    "怎么做",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 路径配置
    data_path: str = str(BACKEND_ROOT / "dishes")
    index_save_path: str = str(BACKEND_ROOT / "vector_index")

    # 模型配置
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    llm_model: str = "kimi-k2.6"

    # 检索配置
    top_k: int = 3

    # 生成配置
    temperature: float = 1.0
    max_tokens: int = 2048

    # API 密钥
    moonshot_api_key: str = ""

    # 服务配置
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    @field_validator("data_path", "index_save_path")
    @classmethod
    def _resolve_path(cls, v: str) -> str:
        """相对路径（如 ./dishes）统一按项目根目录解析，避免受启动位置影响"""
        p = Path(v)
        if not p.is_absolute():
            p = BACKEND_ROOT / p
        return str(p)


settings = Settings()
