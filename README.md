# cook-rag-backend —— 尝尝咸淡 RAG 食谱问答后端

LangChain + FAISS 本地向量检索 + Kimi（Moonshot）大模型生成，FastAPI 提供 HTTP 接口。
前端仓库：`../cook-rag-web`

## 目录结构

```
cook-rag-backend/
├── app/                    # Web 层（新增）
│   ├── main.py             # FastAPI 入口 + lifespan 预热
│   ├── core/config.py      # 配置（pydantic-settings 读 .env）
│   ├── api/routes/         # 路由：chat / dishes / stats
│   └── services/rag_service.py  # RAG 服务单例（原 RecipeRAGSystem 改造）
├── rag_modules/            # RAG 核心四模块（未改动）
├── dishes/                 # 食谱数据（Markdown + 图片）
├── vector_index/           # 预构建 FAISS 索引
├── cli.py                  # 原 main.py 的终端交互模式（调试用）
└── run.sh                  # 一键启动脚本
```

## 快速开始（Ubuntu / WSL）

```bash
cd ~/cook-rag-backend
conda activate 你的环境名        # 或 source venv/bin/activate
pip install -r requirements.txt  # 首次或依赖更新后
./run.sh                         # 或: python3 -m uvicorn app.main:app --port 8000
```

首次启动会加载 embedding 模型 + FAISS 索引，约几十秒，看到 `预热完成，服务就绪` 即可。

## API 一览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | 问答。body: `{"question": "...", "stream": true, "category": null, "difficulty": null}`。`stream=true` 返回 SSE 流（`meta` → `delta`*n → `done`） |
| GET | `/api/dishes` | 菜品列表。query: `category` / `difficulty` / `keyword` |
| GET | `/api/dishes/{dish_name}` | 单品详情（完整 Markdown + 步骤图 URL） |
| GET | `/api/stats` | 知识库统计 |
| GET | `/api/health` | 健康检查 |
| GET | `/static/dishes/**` | 菜品图片静态服务 |
| GET | `/docs` | 自动生成的交互式接口文档 |

## 测试（后端起好后）

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/stats
curl http://localhost:8000/api/dishes | head -c 500
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "简单的早餐有什么推荐？", "stream": true}'
```

## 环境变量

复制 `.env.example` 为 `.env` 并填写。原有键名全部兼容，新增 `APP_HOST` / `APP_PORT`。
注意：`.env` 已被 `.gitignore` 忽略，不会提交。
