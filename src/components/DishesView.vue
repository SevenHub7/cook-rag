<script setup>
import { onMounted, ref, watch } from 'vue'
import { getDishes, getStats } from '../api'
import DishDetail from './DishDetail.vue'

const categories = ref([])
const difficulties = ref([])
const dishes = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref(null)

const category = ref(null)
const difficulty = ref(null)
const keyword = ref('')
const selected = ref(null)

const page = ref(1)
const pageSize = 60

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await getDishes({
      category: category.value,
      difficulty: difficulty.value,
      keyword: keyword.value.trim() || null,
    })
    dishes.value = data.dishes
    total.value = data.total
    page.value = 1
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  load()
  try {
    const s = await getStats()
    categories.value = s.supported_categories || []
    difficulties.value = s.supported_difficulties || []
  } catch {
    /* 后端未启动时静默 */
  }
})

watch([category, difficulty], load)

let timer = null
watch(keyword, () => {
  clearTimeout(timer)
  timer = setTimeout(load, 300)
})

function setCategory(c) {
  category.value = category.value === c ? null : c
}
function setDifficulty(d) {
  difficulty.value = difficulty.value === d ? null : d
}

const paged = () => dishes.value.slice(0, page.value * pageSize)
function more() {
  page.value++
}
</script>

<template>
  <section class="dishes">
    <div class="toolbar">
      <div class="chips">
        <button
          v-for="c in categories"
          :key="c"
          :class="['chip', { on: category === c }]"
          @click="setCategory(c)"
        >
          {{ c }}
        </button>
        <span class="sep"></span>
        <button
          v-for="d in difficulties"
          :key="d"
          :class="['chip', { on: difficulty === d }]"
          @click="setDifficulty(d)"
        >
          {{ d }}
        </button>
      </div>
      <input v-model="keyword" class="search" placeholder="搜菜名…" />
    </div>

    <div v-if="error" class="error">
      {{ error }}
      <br />请确认后端已启动（http://localhost:8000）
    </div>
    <div v-else-if="loading" class="hint">加载中…</div>
    <div v-else-if="!dishes.length" class="hint">没有符合条件的菜品，换个条件试试</div>

    <div v-else class="meta-line">共 {{ total }} 道菜</div>
    <div class="grid">
      <div
        v-for="d in paged()"
        :key="d.dish_name"
        class="card"
        @click="selected = d.dish_name"
      >
        <div class="thumb">
          <img v-if="d.image_url" :src="d.image_url" :alt="d.dish_name" loading="lazy" />
          <span v-else class="placeholder">🍽️</span>
        </div>
        <div class="info">
          <div class="name">{{ d.dish_name }}</div>
          <div class="tags">
            <span class="tag">{{ d.category }}</span>
            <span v-if="d.difficulty && d.difficulty !== '未知'" class="tag">{{ d.difficulty }}</span>
          </div>
        </div>
      </div>
    </div>
    <div v-if="dishes.length > page * pageSize" class="more-wrap">
      <button class="more" @click="more">加载更多（{{ dishes.length - page * pageSize }} 道）</button>
    </div>

    <DishDetail
      v-if="selected"
      :name="selected"
      @close="selected = null"
    />
  </section>
</template>

<style scoped>
.dishes {
  padding-top: 12px;
  flex: 1;
}
.toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  flex: 1;
}
.sep {
  width: 1px;
  height: 20px;
  background: var(--border);
  margin: 0 4px;
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
.search {
  font-size: 14px;
  padding: 7px 14px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--card);
  outline: none;
  width: 140px;
}
.search:focus {
  border-color: var(--primary);
}
.error {
  padding: 40px;
  text-align: center;
  color: #a32d2d;
}
.hint {
  padding: 40px;
  text-align: center;
  color: var(--muted);
}
.meta-line {
  font-size: 13px;
  color: var(--muted);
  margin-bottom: 8px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
}
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
}
.thumb {
  height: 120px;
  background: var(--bg);
  display: flex;
  align-items: center;
  justify-content: center;
}
.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.placeholder {
  font-size: 40px;
}
.info {
  padding: 10px 12px;
}
.name {
  font-weight: 600;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tags {
  display: flex;
  gap: 6px;
}
.tag {
  font-size: 11px;
  color: var(--muted);
  background: var(--bg);
  padding: 1px 8px;
  border-radius: 999px;
}
.more-wrap {
  text-align: center;
  padding: 16px;
}
.more {
  font-size: 14px;
  padding: 8px 24px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--card);
}
</style>
