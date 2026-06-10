/**
 * 多模型对抗 API 封装
 */

import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

// ============ 类型定义 ============

/** 对抗会话 */
export interface ArenaConversation {
  id: number
  title: string | null
  mode: string
  model_config_ids: number[]
  created_at: string
}

/** 对抗会话详情（含模型信息） */
export interface ArenaDetail extends ArenaConversation {
  models: {
    id: number
    name: string
    model_id: string
    api_type: string
    status: string
  }[]
}

/** 单个模型的响应 */
export interface ArenaModelResponse {
  content: string
  model: string
  usage: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
  latency_ms: number
  raw_response: Record<string, any>
  finish_reason: string
}

/** 流式数据块 */
export interface ArenaStreamChunk {
  model_config_id: number
  content: string
  finish_reason: string | null
  error?: string
}

/** 历史消息 */
export interface ArenaHistoryMessage {
  id: number
  role: 'user' | 'assistant'
  content: string | null
  token_usage: string | null
  latency_ms: number | null
  raw_response: string | null
  created_at: string
}

// ============ API 函数 ============

/** 创建对抗会话 */
export async function createArena(
  modelConfigIds: number[],
  title?: string
): Promise<ArenaConversation> {
  const { data } = await api.post('/arena/create', {
    model_config_ids: modelConfigIds,
    title: title || null,
  })
  return data
}

/** 获取对抗会话列表 */
export async function fetchArenas(): Promise<ArenaConversation[]> {
  const { data } = await api.get('/arena/list')
  return data
}

/** 获取对抗会话详情 */
export async function fetchArenaDetail(id: number): Promise<ArenaDetail> {
  const { data } = await api.get(`/arena/${id}`)
  return data
}

/** 获取对抗历史（按模型分组） */
export async function fetchArenaHistory(
  conversationId: number
): Promise<Record<string, ArenaHistoryMessage[]>> {
  const { data } = await api.get(`/arena/${conversationId}/history`)
  return data
}

/** 发送消息（非流式） */
export async function sendArenaMessage(
  conversationId: number,
  modelConfigIds: number[],
  content: string
): Promise<Record<string, ArenaModelResponse>> {
  const { data } = await api.post('/arena/send', {
    conversation_id: conversationId,
    model_config_ids: modelConfigIds,
    content,
  })
  return data
}

/** 发送消息（流式 SSE） */
export async function sendArenaMessageStream(
  conversationId: number,
  modelConfigIds: number[],
  content: string,
  onChunk: (chunk: ArenaStreamChunk) => void
): Promise<void> {
  const response = await fetch('/api/arena/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      conversation_id: conversationId,
      model_config_ids: modelConfigIds,
      content,
    }),
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`流式请求失败 (${response.status}): ${errorText}`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('无法读取流式响应')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed || trimmed === 'data: [DONE]') continue

      if (trimmed.startsWith('data: ')) {
        const jsonStr = trimmed.slice(6)
        try {
          const parsed = JSON.parse(jsonStr)
          if (parsed.error && !parsed.model_config_id) {
            throw new Error(parsed.error)
          }
          onChunk(parsed as ArenaStreamChunk)
        } catch (e: any) {
          if (e.message && !e.message.includes('JSON')) {
            throw e
          }
        }
      }
    }
  }
}

/** 删除对抗会话 */
export async function deleteArena(id: number): Promise<void> {
  await api.delete(`/arena/${id}`)
}
