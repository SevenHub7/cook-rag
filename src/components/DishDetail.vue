<script setup>
import { onMounted, ref } from 'vue'
import { marked } from 'marked'
import { getDish } from '../api'

const props = defineProps({ name: String })
const emit = defineEmits(['close'])

const dish = ref(null)
const error = ref(null)

onMounted(async () => {
  try {
    dish.value = await getDish(props.name)
  } catch (e) {
    error.value = e.message
  }
})

function renderMd(text) {
  return marked.parse(text || '')
}
</script>

<template>
  <div class="mask" @click.self="emit('close')">
    <div class="panel">
      <button class="close" @click="emit('close')">✕</button>
      <div v-if="error" class="err">{{ error }}</div>
      <div v-else-if="!dish" class="loading">加载中…</div>
      <template v-else>
        <h2 class="title">{{ dish.dish_name }}</h2>
        <div class="tags">
          <span class="tag">{{ dish.category }}</span>
          <span v-if="dish.difficulty !== '未知'" class="tag">{{ dish.difficulty }}</span>
        </div>
        <div v-if="dish.images?.length" class="imgs">
          <img v-for="img in dish.images" :key="img" :src="img" loading="lazy" />
        </div>
        <div class="md content" v-html="renderMd(dish.content)"></div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  z-index: 10;
}
.panel {
  background: var(--card);
  border-radius: 16px;
  max-width: 720px;
  width: 100%;
  max-height: 85vh;
  overflow-y: auto;
  padding: 28px;
  position: relative;
}
.close {
  position: absolute;
  top: 14px;
  right: 14px;
  font-size: 16px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--bg);
  color: var(--muted);
}
.close:hover {
  color: var(--text);
}
.loading,
.err {
  text-align: center;
  padding: 30px;
  color: var(--muted);
}
.title {
  font-size: 22px;
  margin-bottom: 8px;
}
.tags {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
}
.tag {
  font-size: 12px;
  color: var(--primary);
  background: var(--primary-light);
  padding: 2px 10px;
  border-radius: 999px;
}
.imgs {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 8px;
  margin: 12px 0;
}
.imgs img {
  width: 100%;
  height: 120px;
  object-fit: cover;
  border-radius: 8px;
}
.content {
  font-size: 14px;
  color: var(--text);
}
</style>
