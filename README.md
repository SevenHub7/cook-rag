# cook-rag：一日三餐 RAG 食谱问答（前后端 monorepo）

> 用 LangChain + FAISS + BGE + Kimi 构建的本地菜谱 RAG 系统，支持聊天问答和菜谱大全浏览。

---

## 仓库结构

```
cook-rag/                          本仓库根目录
├── backend/                       后端：FastAPI + LangChain RAG 服务
│   ├── app/                       FastAPI 应用（main / routes / services / skills / schema）
│   ├── rag_modules/               RAG 核心四模块（数据准备 / 索引 / 检索 / 生成）
│   ├── dishes/                    菜品 Markdown + 配图
│   ├── vector_index/              预构建的 FAISS 索引
│   ├── config.py                  RAGConfig（LangChain 配置）
│   ├── cli.py                     旧 main.py 保留的终端调试模式
│   ├── requirements.txt           Python 依赖
│   ├── run.sh                     一键启动脚本
│   ├── .env.example               环境变量模板（自己复制成 .env 填 API Key）
│   └── README.md                  后端说明（接口、启动、故障排查）
│
├── frontend/                      前端：Vue 3 + Vite 单页应用
│   ├── src/
│   │   ├── App.vue                主框架（顶栏 + Tab 路由）
│   │   ├── api.js                 后端 API 封装（含 SSE 流式读取）
│   │   ├── style.css              全局样式
│   │   └── components/
│   │       ├── ChatView.vue       聊天问答页（流式打字 + 筛选）
│   │       ├── DishesView.vue     菜谱大全页（分类/难度筛选 + 搜索）
│   │       └── DishDetail.vue     菜品详情弹窗
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js             dev proxy: /api /static -> :8000
│   ├── .gitignore
│   └── README.md                  前端说明
│
├── .gitignore                     全局忽略规则（合并了 backend/frontend 的规则）
└── README.md                      本文件
```

---

## 启动顺序

后端必须先起，前端 dev proxy 才能转发。

### 1. 启动后端（端口 8000）

```bash
cd backend
conda activate <你的环境名>          # 或 source venv/bin/activate
cp .env.example .env                  # 第一次启动需要；填入 MOONSHOT_API_KEY 等
pip install -r requirements.txt       # 首次或依赖有更新时执行
./run.sh                              # 看到 "RAG 服务预热完成" 才算就绪（约 30 秒）
```

接口文档自动可用：http://localhost:8000/docs
健康检查：`curl http://localhost:8000/api/health`

### 2. 启动前端（端口 5173）

```bash
cd frontend
npm install                           # 首次或 package.json 变化时执行
npm run dev
```

浏览器打开 http://localhost:5173 即可使用。

---

## 完整命令速查

| 想做什么 | 命令 |
|---------|------|
| 跑后端 | `cd backend && ./run.sh` |
| 跑前端 | `cd frontend && npm run dev` |
| 后端装依赖 | `cd backend && pip install -r requirements.txt` |
| 前端装依赖 | `cd frontend && npm install` |
| 前端构建产物 | `cd frontend && npm run build`（产物在 `frontend/dist/`） |
| 后端接口文档 | 浏览器打开 http://localhost:8000/docs |

---

## 关键设计要点

- **RAG 链路**：用户 query → 路由分流 → 指代问句改写（Skill）→ 混合检索（BM25 + 向量 + RRF）→ 菜名精确过滤 → 取父文档 → LLM 流式生成
- **流式输出**：POST `/api/chat` 用 SSE，前端 `EventSource` 逐字拼接 Markdown 渲染
- **数据隔离**：`dishes/` `vector_index/` 全部由后端持有，前端通过 `/static/dishes/...` 访问图片
- **零 CORS 配置**：前端 dev proxy 把 `/api` `/static` 转发到 `:8000`，不需要 `CORSMiddleware`

---

## 故障排查

| 现象 | 原因 |
|------|------|
| 后端 503 "服务暂未就绪" | RAG 预热未完成，等待日志里出现 "RAG 服务预热完成" |
| 后端启动后无响应 | 检查 `.env` 中 `MOONSHOT_API_KEY` 是否正确 |
| 前端白屏 / 跨域报错 | 后端没起，或 `vite.config.js` 的 proxy 端口对不上 |
| 推荐菜品每次都一样 | 确认走的是 `list` 路径（问题 "推荐早餐"），不要用"燕麦鸡蛋饼 做法"这种 `detail` 路径 |
| 怎么做？回答跑偏到红烧肉 | 检查日志里 `history_len` 是否 > 0，前端是否传了 `chat_history` |

更详细的接口说明、配置项、常见问题见各子目录的 README：

- 后端：[`backend/README.md`](backend/README.md)
- 前端：[`frontend/README.md`](frontend/README.md)

---

## License

Private project.