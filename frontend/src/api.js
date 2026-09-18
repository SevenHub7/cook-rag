/**
 * 后端 API 封装
 * 开发阶段由 Vite proxy 转发到 http://localhost:8000
 */

async function getJSON(url) {
  const res = await fetch(url)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `请求失败 ${res.status}`)
  }
  return res.json()
}

export function getStats() {
  return getJSON('/api/stats')
}

export function getDishes({ category, difficulty, keyword } = {}) {
  const params = new URLSearchParams()
  if (category) params.set('category', category)
  if (difficulty) params.set('difficulty', difficulty)
  if (keyword) params.set('keyword', keyword)
  const qs = params.toString()
  return getJSON(`/api/dishes${qs ? `?${qs}` : ''}`)
}

export function getDish(name) {
  return getJSON(`/api/dishes/${encodeURIComponent(name)}`)
}

/**
 * 流式问答（SSE over POST fetch）
 * handlers: { onMeta, onDelta, onDone, onError }
 */
export async function chatStream({ question, category, difficulty }, handlers) {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, stream: true, category, difficulty }),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `请求失败 ${res.status}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  const dispatch = (evt) => {
    if (evt.type === 'meta') handlers.onMeta?.(evt)
    else if (evt.type === 'delta') handlers.onDelta?.(evt.content)
    else if (evt.type === 'done') handlers.onDone?.()
    else if (evt.type === 'error') handlers.onError?.(evt.message)
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // SSE 事件以空行分隔：data: {...}\n\n
    let idx
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const raw = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      for (const line of raw.split('\n')) {
        const t = line.trim()
        if (t.startsWith('data:')) {
          try {
            dispatch(JSON.parse(t.slice(5).trim()))
          } catch {
            // 忽略不完整的事件
          }
        }
      }
    }
  }
}
