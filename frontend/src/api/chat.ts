/**
 * 对话相关 API 封装
 * 包含对话创建、消息发送（普通/流式）、历史查询等功能
 */

import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// ============ 类型定义 ============

/** 对话信息 */
export interface Conversation {
  id: number
  title: string | null
  mode: string
  model_config_ids: string | null
  created_at: string
}

/** 消息响应（非流式） */
export interface MessageResponse {
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

/** 历史消息条目 */
export interface MessageHistory {
  id: number
  role: 'user' | 'assistant'
  content: string | null
  image_data: string | null
  token_usage: string | null
  latency_ms: number | null
  raw_response: string | null
  created_at: string
}

/** 流式数据块 */
export interface StreamChunk {
  content: string
  finish_reason: string | null
}

// ============ API 函数 ============

/**
 * 创建新对话
 * @param modelConfigId 模型配置 ID
 * @param title 可选的对话标题
 * @returns 对话信息
 */
export async function createConversation(
  modelConfigId: number,
  title?: string
): Promise<Conversation> {
  const { data } = await api.post('/chat/create', {
    model_config_id: modelConfigId,
    title: title || null,
  })
  return data
}

/**
 * 获取对话列表
 * @param mode 可选的模式筛选
 */
export async function fetchConversations(mode?: string): Promise<Conversation[]> {
  const params = mode ? { mode } : {}
  const { data } = await api.get('/chat/list', { params })
  return data
}

/**
 * 发送消息（非流式）
 * @param conversationId 对话 ID
 * @param modelConfigId 模型配置 ID
 * @param content 消息内容
 * @param imageData 可选的 Base64 图片
 * @param temperature 可选的温度参数
 * @param maxTokens 可选的最大 token
 */
export async function sendMessage(
  conversationId: number,
  modelConfigId: number,
  content: string,
  imageData?: string,
  temperature?: number,
  maxTokens?: number
): Promise<MessageResponse> {
  const { data } = await api.post('/chat/send', {
    conversation_id: conversationId,
    model_config_id: modelConfigId,
    content,
    image_data: imageData || null,
    temperature: temperature ?? null,
    max_tokens: maxTokens ?? null,
  })
  return data
}

/**
 * 发送消息（流式 SSE）
 *
 * 使用 fetch + ReadableStream 实现 SSE 接收，
 * 每收到一个 chunk 就调用 onChunk 回调。
 *
 * @param conversationId 对话 ID
 * @param modelConfigId 模型配置 ID
 * @param content 消息内容
 * @param onChunk 收到增量数据时的回调
 * @param imageData 可选的 Base64 图片
 * @param temperature 可选的温度参数
 * @param maxTokens 可选的最大 token
 */
export async function sendMessageStream(
  conversationId: number,
  modelConfigId: number,
  content: string,
  onChunk: (chunk: StreamChunk) => void,
  imageData?: string,
  temperature?: number,
  maxTokens?: number
): Promise<void> {
  const body = {
    conversation_id: conversationId,
    model_config_id: modelConfigId,
    content,
    image_data: imageData || null,
    temperature: temperature ?? null,
    max_tokens: maxTokens ?? null,
  }

  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
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

    // 按行解析 SSE 数据
    const lines = buffer.split('\n')
    buffer = lines.pop() || '' // 最后一行可能不完整，留到下次处理

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed || trimmed === 'data: [DONE]') continue

      if (trimmed.startsWith('data: ')) {
        const jsonStr = trimmed.slice(6)
        try {
          const parsed = JSON.parse(jsonStr)
          if (parsed.error) {
            throw new Error(parsed.error)
          }
          onChunk(parsed as StreamChunk)
        } catch (e: any) {
          // JSON 解析错误忽略，可能是不完整的数据
          if (e.message && !e.message.includes('JSON')) {
            throw e
          }
        }
      }
    }
  }
}

/**
 * 获取对话历史消息
 * @param conversationId 对话 ID
 */
export async function getHistory(conversationId: number): Promise<MessageHistory[]> {
  const { data } = await api.get(`/chat/history/${conversationId}`)
  return data
}

/**
 * 删除对话
 * @param id 对话 ID
 */
export async function deleteConversation(id: number): Promise<void> {
  await api.delete(`/chat/${id}`)
}
