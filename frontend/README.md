# cook-rag-web —— 尝尝咸淡前端

Vue 3 + Vite。聊天问答（SSE 流式渲染）+ 菜谱大全（分类/难度筛选 + 菜品详情）。
后端仓库：`../cook-rag-backend`

## 快速开始（Ubuntu / WSL）

```bash
# 0. 先启动后端（另开一个终端）
cd ~/cook-rag-backend
conda activate 你的环境名
./run.sh

# 1. 再启动前端
cd ~/cook-rag-web
npm install     # 首次或 package.json 变更后
npm run dev
```

打开 http://localhost:5173 即可使用。

## 说明

- 开发阶段 Vite 会把 `/api` 和 `/static` 请求自动转发到 `http://localhost:8000`（见 `vite.config.js`），无需任何 CORS 配置
- 首次打开聊天页如果后端还在预热（首次启动约几十秒），接口会返回 503，等后端日志出现「预热完成，服务就绪」后刷新页面
- `npm run build` 可产出静态文件到 `dist/`，部署时由后端或 Nginx 托管

## 目录结构

```
cook-rag-web/
├── index.html
├── vite.config.js      # 端口 + dev 代理配置
├── package.json
└── src/
    ├── main.js         # 入口
    ├── style.css       # 全局样式
    ├── api.js          # 后端 API 封装（含 SSE 流式解析）
    ├── App.vue         # 布局 + 页签切换
    └── components/
        ├── ChatView.vue    # 聊天页（流式渲染 + 分类/难度筛选）
        ├── DishesView.vue  # 菜谱大全（筛选 + 卡片网格）
        └── DishDetail.vue  # 菜品详情弹窗（Markdown + 步骤图）
```
