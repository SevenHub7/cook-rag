<script setup>
import { ref } from 'vue'
import ChatView from './components/ChatView.vue'
import DishesView from './components/DishesView.vue'

const tab = ref('chat')
</script>

<template>
  <div class="layout">
    <header class="header">
      <div class="brand">🍳 尝尝咸淡</div>
      <nav class="tabs">
        <button :class="{ active: tab === 'chat' }" @click="tab = 'chat'">
          问问吃什么
        </button>
        <button :class="{ active: tab === 'dishes' }" @click="tab = 'dishes'">
          菜谱大全
        </button>
      </nav>
    </header>
    <main class="main">
      <ChatView v-show="tab === 'chat'" />
      <DishesView v-show="tab === 'dishes'" />
    </main>
  </div>
</template>

<style scoped>
.layout {
  max-width: 860px;
  margin: 0 auto;
  padding: 16px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 4px;
  border-bottom: 1px solid var(--border);
}
.brand {
  font-size: 22px;
  font-weight: 700;
}
.tabs button {
  font-size: 15px;
  padding: 8px 18px;
  color: var(--muted);
  border-radius: 999px;
}
.tabs button.active {
  background: var(--primary-light);
  color: var(--primary);
  font-weight: 600;
}
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
</style>
