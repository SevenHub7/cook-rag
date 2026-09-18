<script setup>
import { nextTick, ref, computed } from 'vue'
import { marked } from 'marked'
import { chatStream, getStats } from '../api'

const question = ref('')
const category = ref(null)
const difficulty = ref(null)
const loading = ref(false)
const listRef = ref(null)

const categories = ref([])
const difficulties = ref([])

const messages = ref([
  {
    role: 'assistant',
    text: '你好！我是你的私人做饭助手 🍳\n\n不知道吃什么？问我一句就行，比如：**"简单的早餐有什么推荐？"**、**"红烧肉怎么做？"**',
    sources: [],
  },
])

const suggestions = ['简单的早餐推荐', '有哪些素菜', '红烧鱼怎么做', '中等难度的汤品']

getStats()
  .then((s) => {
    categories.value = s.supported_categories || []
    difficulties.value = s.supported_difficulties || []
  })
  .catch(() => {})

function renderMd(text) {
  return marked.parse(text || '')
}

async function scrollToBottom() {
  await nextTick()
  listRef.value?.scrollTo({ top: listRef.value.scrollHeight, behavior: 'smooth' })
}

async function send(text) {
  const q = (text || question.value).trim()
  if (!q || loading.value) return

  messages.value.push({ role: 'user', text: q })
  const reply = { role: 'assistant', text: '', sources: [], route: null, streaming: true }
  messages.value.push(reply)
  question.value = ''
  loading.value = true
  scrollToBottom()

  try {
    await chatStream(
      { question: q, category: category.value, difficulty: difficulty.value },
      {
        onMeta: (evt) => {
          reply.route = evt.route
          reply.sources = evt.sources || []
          scrollToBottom()
        },
        onDelta: (chunk) => {
          reply.text += chunk
          scrollToBottom()
        },
        onDone: () => {},
        onError: (msg) => {
          reply.text += `\n\n⚠️ 出错了：${msg}`
        },
      }
    )
  } catch (e) {
    reply.text += `\n\n⚠️ ${e.message}\n\n请确认后端已启动（http://localhost:8000）`
  } finally {
    reply.streaming = false
    loading.value = false
    scrollToBottom()
  }
}

function setFilter(kind, val) {
  if (kind === 'category') category.value = category.value === val ? null : val
  else difficulty.value = difficulty.value === val ? null : val
}
</script>

<template>
  <section class="chat">
    <div class="filters" v-if="categories.length">
      <span class="label">分类</span>
      <button
        v-for="c in categories"
        :key="c"
        :class="['chip', { on: category === c }]"
        @click="setFilter('category', c)"
      >
        {{ c }}
      </button>
      <span class="label sep">难度</span>
      <button
        v-for="d in difficulties"
        :key="d"
        :class="['chip', { on: difficulty === d }]"
        @click="setFilter('difficulty', d)"
      >
        {{ d }}
      </button>
    </div>

    <div class="messages" ref="listRef">
      <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]">
        <div v-if="m.role === 'user'" class="bubble user">{{ m.text }}</div>
        <div v-else class="bubble assistant">
          <div class="md" v-html="renderMd(m.text)"></div>
          <div v-if="m.streaming && !m.text" class="dots">正在思考…</div>
          <div v-if="m.sources?.length" class="sources">
            <span class="src-label">参考食谱</span>
            <span v-for="s in m.sources" :key="s.dish_name" class="src">
              📖 {{ s.dish_name }}
              <em v-if="s.difficulty && s.difficulty !== '未知'"> · {{ s.difficulty }}</em>
            </span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="messages.length <= 1" class="suggestions">
      <button v-for="s in suggestions" :key="s" @click="send(s)">{{ s }}</button>
    </div>

    <form class="input-bar" @submit.prevent="send()">
      <input
        v-model="question"
        placeholder="问问吃什么，比如：今晚想吃鱼，怎么做好？"
        :disabled="loading"
      />
      <button type="submit" class="send" :disabled="loading || !question.trim()">
        {{ loading ? '回答中…' : '发送' }}
      </button>
    </form>
  </section>
</template>

<style scoped>
.chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding-top: 12px;
}
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  padding: 8px 0;
}
.filters .label {
  font-size: 13px;
  color: var(--muted);
  margin: 0 2px;
}
.filters .sep {
  margin-left: 10px;
}
.chip {
  font-size: 13px;
  padding: 4px 12px;
  border-radius: 999px;
  background: var(--card);
  border: 1px solid var(--border);
  color: var(--muted);
}
.chip.on {
  background: var(--primary-light);
  border-color: var(--primary);
  color: var(--primary);
  font-weight: 600;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px 4px;
  min-height: 200px;
}
.msg {
  display: flex;
  margin-bottom: 16px;
}
.msg.user {
  justify-content: flex-end;
}
.bubble.user {
  background: var(--primary);
  color: #fff;
  padding: 10px 16px;
  border-radius: 16px 16px 4px 16px;
  max-width: 75%;
  white-space: pre-wrap;
}
.bubble.assistant {
  background: var(--card);
  border: 1px solid var(--border);
  padding: 14px 18px;
  border-radius: 16px 16px 16px 4px;
  max-width: 90%;
}
.dots {
  color: var(--muted);
  font-size: 14px;
}
.sources {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed var(--border);
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.src-label {
  font-size: 12px;
  color: var(--muted);
}
.src {
  font-size: 12px;
  background: var(--bg);
  border: 1px solid var(--border);
  padding: 2px 10px;
  border-radius: 999px;
}
.src em {
  color: var(--muted);
  font-style: normal;
}
.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 4px;
}
.suggestions button {
  font-size: 13px;
  padding: 6px 14px;
  border-radius: 999px;
  background: var(--card);
  border: 1px solid var(--border);
  color: var(--text);
}
.suggestions button:hover {
  border-color: var(--primary);
  color: var(--primary);
}
.input-bar {
  display: flex;
  gap: 10px;
  padding: 12px 0 4px;
}
.input-bar input {
  flex: 1;
  font-size: 15px;
  padding: 12px 16px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--card);
  outline: none;
}
.input-bar input:focus {
  border-color: var(--primary);
}
.send {
  font-size: 15px;
  padding: 12px 26px;
  border-radius: 999px;
  background: var(--primary);
  color: #fff;
  font-weight: 600;
}
.send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
