/**
 * Pinia 对话状态管理
 * 管理对话列表、当前对话、消息列表、加载/流式状态
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Conversation, MessageHistory, MessageResponse, StreamChunk } from '@/api/chat'
import {
  createConversation,
  fetchConversations,
  sendMessage,
  sendMessageStream,
  getHistory,
  deleteConversation as deleteConversationApi,
} from '@/api/chat'

/** 前端展示用的消息格式 */
export interface DisplayMessage {
  id: number | string  // 数据库 ID 或临时 ID
  role: 'user' | 'assistant'
  content: string
  imageData?: string   // Base64 图片数据
  tokenUsage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
  latencyMs?: number
  rawResponse?: Record<string, any>
  isStreaming?: boolean  // 是否正在流式接收中
  createdAt?: string
}

export const useChatStore = defineStore('chat', () => {
  // ============ 状态 ============

  /** 对话列表 */
  const conversations = ref<Conversation[]>([])

  /** 当前选中的对话 */
  const currentConversation = ref<Conversation | null>(null)

  /** 当前对话的消息列表 */
  const messages = ref<DisplayMessage[]>([])

  /** 是否正在加载 */
  const loading = ref(false)

  /** 是否正在流式接收 */
  const streaming = ref(false)

  /** 错误信息 */
  const error = ref<string | null>(null)

  // ============ 计算属性 ============

  /** 当前对话 ID */
  const currentConversationId = computed(() => currentConversation.value?.id ?? null)

  /** 是否有对话 */
  const hasConversations = computed(() => conversations.value.length > 0)

  // ============ 操作 ============

  /** 加载对话列表 */
  async function loadConversations() {
    try {
      conversations.value = await fetchConversations('single')
    } catch (e: any) {
      console.error('加载对话列表失败:', e)
    }
  }

  /**
   * 创建新对话
   * @param modelConfigId 模型配置 ID
   * @returns 创建的对话
   */
  async function createNewConversation(modelConfigId: number): Promise<Conversation> {
    const conv = await createConversation(modelConfigId)
    conversations.value.unshift(conv)
    currentConversation.value = conv
    messages.value = []
    return conv
  }

  /**
   * 切换到指定对话
   * @param conversationId 对话 ID
   */
  async function switchConversation(conversationId: number) {
    const conv = conversations.value.find(c => c.id === conversationId)
    if (!conv) return

    currentConversation.value = conv
    await loadMessages(conversationId)
  }

  /** 加载指定对话的消息 */
  async function loadMessages(conversationId: number) {
    loading.value = true
    error.value = null
    try {
      const history = await getHistory(conversationId)
      messages.value = history.map(h => ({
        id: h.id,
        role: h.role,
        content: h.content || '',
        imageData: h.image_data || undefined,
        tokenUsage: h.token_usage ? JSON.parse(h.token_usage) : undefined,
        latencyMs: h.latency_ms ?? undefined,
        rawResponse: h.raw_response ? JSON.parse(h.raw_response) : undefined,
        createdAt: h.created_at,
      }))
    } catch (e: any) {
      error.value = e.message || '加载消息失败'
      console.error('加载消息失败:', e)
    } finally {
      loading.value = false
    }
  }

  /**
   * 发送消息（非流式）
   * @param modelConfigId 模型配置 ID
   * @param content 消息内容
   * @param imageData 可选的图片数据
   */
  async function send(
    modelConfigId: number,
    content: string,
    imageData?: string
  ): Promise<void> {
    if (!currentConversation.value) return

    // 添加用户消息到列表
    const tempUserId = `temp-user-${Date.now()}`
    messages.value.push({
      id: tempUserId,
      role: 'user',
      content,
      imageData,
      createdAt: new Date().toISOString(),
    })

    loading.value = true
    error.value = null

    try {
      const response = await sendMessage(
        currentConversation.value.id,
        modelConfigId,
        content,
        imageData
      )

      // 用真实数据替换临时用户消息（获取数据库 ID）
      // 同时添加助手消息
      messages.value.push({
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.content,
        tokenUsage: response.usage,
        latencyMs: response.latency_ms,
        rawResponse: response.raw_response,
        createdAt: new Date().toISOString(),
      })

      // 更新对话列表中的标题（如果是第一条消息）
      updateConversationTitle(content)
    } catch (e: any) {
      error.value = e.message || '发送消息失败'
      // 移除用户消息（发送失败）
      messages.value = messages.value.filter(m => m.id !== tempUserId)
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 发送消息（流式）
   * @param modelConfigId 模型配置 ID
   * @param content 消息内容
   * @param imageData 可选的图片数据
   */
  async function sendStream(
    modelConfigId: number,
    content: string,
    imageData?: string
  ): Promise<void> {
    if (!currentConversation.value) return

    // 添加用户消息
    messages.value.push({
      id: `temp-user-${Date.now()}`,
      role: 'user',
      content,
      imageData,
      createdAt: new Date().toISOString(),
    })

    // 添加助手消息占位（标记为流式接收中）
    const assistantId = `stream-assistant-${Date.now()}`
    messages.value.push({
      id: assistantId,
      role: 'assistant',
      content: '',
      isStreaming: true,
      createdAt: new Date().toISOString(),
    })

    streaming.value = true
    error.value = null

    try {
      await sendMessageStream(
        currentConversation.value.id,
        modelConfigId,
        content,
        (chunk: StreamChunk) => {
          // 找到助手消息并追加内容
          const msg = messages.value.find(m => m.id === assistantId)
          if (msg) {
            msg.content += chunk.content
          }
        },
        imageData
      )

      // 流式完成，标记结束
      const msg = messages.value.find(m => m.id === assistantId)
      if (msg) {
        msg.isStreaming = false
      }

      // 更新对话标题
      updateConversationTitle(content)
    } catch (e: any) {
      error.value = e.message || '流式发送失败'
      // 移除未完成的助手消息
      const msg = messages.value.find(m => m.id === assistantId)
      if (msg && !msg.content) {
        messages.value = messages.value.filter(m => m.id !== assistantId)
      } else if (msg) {
        msg.isStreaming = false
      }
      throw e
    } finally {
      streaming.value = false
    }
  }

  /** 删除对话 */
  async function removeConversation(id: number) {
    try {
      await deleteConversationApi(id)
      conversations.value = conversations.value.filter(c => c.id !== id)
      if (currentConversation.value?.id === id) {
        currentConversation.value = null
        messages.value = []
      }
    } catch (e: any) {
      error.value = e.message || '删除对话失败'
      throw e
    }
  }

  /**
   * 更新对话标题（取用户第一条消息的前 20 个字符）
   */
  function updateConversationTitle(firstMessage: string) {
    if (!currentConversation.value) return
    // 只在标题还是默认值时更新
    if (currentConversation.value.title === '新对话') {
      const title = firstMessage.slice(0, 20) + (firstMessage.length > 20 ? '...' : '')
      currentConversation.value.title = title
      // 同步到列表
      const conv = conversations.value.find(c => c.id === currentConversation.value!.id)
      if (conv) conv.title = title
    }
  }

  /** 清空状态 */
  function clearState() {
    currentConversation.value = null
    messages.value = []
    error.value = null
  }

  return {
    // 状态
    conversations,
    currentConversation,
    messages,
    loading,
    streaming,
    error,
    // 计算属性
    currentConversationId,
    hasConversations,
    // 操作
    loadConversations,
    createNewConversation,
    switchConversation,
    loadMessages,
    send,
    sendStream,
    removeConversation,
    clearState,
  }
})
