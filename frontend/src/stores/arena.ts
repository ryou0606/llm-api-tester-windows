/**
 * Pinia 对抗状态管理
 * 管理会话列表、当前会话、各模型消息、流式状态
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ArenaConversation, ArenaDetail, ArenaStreamChunk, ArenaHistoryMessage } from '@/api/arena'
import {
  createArena,
  fetchArenas,
  fetchArenaDetail,
  fetchArenaHistory,
  sendArenaMessageStream,
  deleteArena as deleteArenaApi,
} from '@/api/arena'

/** 前端展示用的消息格式 */
export interface ArenaDisplayMessage {
  id: number | string
  role: 'user' | 'assistant'
  content: string
  modelConfigId?: number
  tokenUsage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
  latencyMs?: number
  rawResponse?: Record<string, any>
  isStreaming?: boolean
  createdAt?: string
}

export const useArenaStore = defineStore('arena', () => {
  // ============ 状态 ============

  /** 对抗会话列表 */
  const arenas = ref<ArenaConversation[]>([])

  /** 当前对抗会话详情 */
  const currentArena = ref<ArenaDetail | null>(null)

  /** 当前选中查看的模型 ID */
  const activeModelId = ref<number | null>(null)

  /** 各模型的消息映射: { modelConfigId: ArenaDisplayMessage[] } */
  const modelMessages = ref<Record<number, ArenaDisplayMessage[]>>({})

  /** 用户消息列表（共享） */
  const userMessages = ref<ArenaDisplayMessage[]>([])

  /** 是否正在加载 */
  const loading = ref(false)

  /** 是否正在流式接收 */
  const streaming = ref(false)

  /** 正在流式接收的模型 ID 集合 */
  const streamingModelIds = ref<Set<number>>(new Set())

  /** 错误信息 */
  const error = ref<string | null>(null)

  // ============ 计算属性 ============

  /** 当前查看的模型的消息 */
  const currentModelMessages = computed(() => {
    if (!activeModelId.value) return []
    return modelMessages.value[activeModelId.value] || []
  })

  /** 合并用户消息和当前模型消息，按时间排序 */
  const displayMessages = computed<ArenaDisplayMessage[]>(() => {
    if (!activeModelId.value) return []

    const modelMsgs = modelMessages.value[activeModelId.value] || []

    // 合并用户消息和模型消息
    const all = [...userMessages.value, ...modelMsgs]
    all.sort((a, b) => {
      const ta = a.createdAt || ''
      const tb = b.createdAt || ''
      return ta.localeCompare(tb)
    })
    return all
  })

  /** 参与对抗的模型列表 */
  const arenaModels = computed(() => {
    return currentArena.value?.models || []
  })

  // ============ 操作 ============

  /** 加载对抗会话列表 */
  async function loadArenas() {
    try {
      arenas.value = await fetchArenas()
    } catch (e: any) {
      console.error('加载对抗列表失败:', e)
    }
  }

  /** 创建新的对抗会话 */
  async function createNewArena(modelConfigIds: number[], title?: string): Promise<ArenaConversation> {
    const arena = await createArena(modelConfigIds, title)
    arenas.value.unshift(arena)
    return arena
  }

  /** 进入对抗会话 */
  async function enterArena(conversationId: number) {
    loading.value = true
    error.value = null
    try {
      const detail = await fetchArenaDetail(conversationId)
      currentArena.value = detail

      // 默认选中第一个模型
      if (detail.models.length > 0) {
        activeModelId.value = detail.models[0].id
      }

      // 初始化各模型消息容器
      const msgs: Record<number, ArenaDisplayMessage[]> = {}
      for (const m of detail.models) {
        msgs[m.id] = []
      }
      modelMessages.value = msgs
      userMessages.value = []

      // 加载历史
      await loadHistory(conversationId)
    } catch (e: any) {
      error.value = e.message || '进入对抗失败'
    } finally {
      loading.value = false
    }
  }

  /** 加载历史消息 */
  async function loadHistory(conversationId: number) {
    try {
      const grouped = await fetchArenaHistory(conversationId)

      // 清空现有消息
      userMessages.value = []
      for (const key of Object.keys(modelMessages.value)) {
        modelMessages.value[Number(key)] = []
      }

      for (const [key, messages] of Object.entries(grouped)) {
        const mid = Number(key)
        if (mid === 0) {
          // 用户消息
          userMessages.value = messages.map(m => ({
            id: m.id,
            role: 'user' as const,
            content: m.content || '',
            createdAt: m.created_at,
          }))
        } else {
          // 模型消息
          if (!modelMessages.value[mid]) {
            modelMessages.value[mid] = []
          }
          modelMessages.value[mid] = messages.map(m => ({
            id: m.id,
            role: 'assistant' as const,
            content: m.content || '',
            modelConfigId: mid,
            tokenUsage: m.token_usage ? JSON.parse(m.token_usage) : undefined,
            latencyMs: m.latency_ms ?? undefined,
            rawResponse: m.raw_response ? JSON.parse(m.raw_response) : undefined,
            createdAt: m.created_at,
          }))
        }
      }
    } catch (e: any) {
      console.error('加载对抗历史失败:', e)
    }
  }

  /** 切换查看的模型 */
  function switchModel(modelConfigId: number) {
    activeModelId.value = modelConfigId
  }

  /** 发送消息（流式） */
  async function send(content: string): Promise<void> {
    if (!currentArena.value || !activeModelId.value) return

    const modelIds = currentArena.value.models.map(m => m.id)

    // 添加用户消息
    const tempUserId = `temp-user-${Date.now()}`
    userMessages.value.push({
      id: tempUserId,
      role: 'user',
      content,
      createdAt: new Date().toISOString(),
    })

    // 为每个模型添加占位消息
    for (const mid of modelIds) {
      if (!modelMessages.value[mid]) {
        modelMessages.value[mid] = []
      }
      modelMessages.value[mid].push({
        id: `stream-${mid}-${Date.now()}`,
        role: 'assistant',
        content: '',
        modelConfigId: mid,
        isStreaming: true,
        createdAt: new Date().toISOString(),
      })
    }

    streaming.value = true
    streamingModelIds.value = new Set(modelIds)
    error.value = null

    try {
      await sendArenaMessageStream(
        currentArena.value.id,
        modelIds,
        content,
        (chunk: ArenaStreamChunk) => {
          const mid = chunk.model_config_id
          const msgs = modelMessages.value[mid]
          if (!msgs || msgs.length === 0) return

          const lastMsg = msgs[msgs.length - 1]
          if (lastMsg.isStreaming) {
            if (chunk.error) {
              lastMsg.content += `\n[错误] ${chunk.error}`
              lastMsg.isStreaming = false
              streamingModelIds.value.delete(mid)
            } else {
              lastMsg.content += chunk.content
              if (chunk.finish_reason) {
                lastMsg.isStreaming = false
                streamingModelIds.value.delete(mid)
              }
            }
          }
        }
      )

      // 确保所有模型标记为完成
      for (const mid of modelIds) {
        const msgs = modelMessages.value[mid]
        if (msgs && msgs.length > 0) {
          const lastMsg = msgs[msgs.length - 1]
          lastMsg.isStreaming = false
        }
      }
      streamingModelIds.value.clear()

      // 更新标题
      updateArenaTitle(content)
    } catch (e: any) {
      error.value = e.message || '发送失败'
      // 标记所有流式消息为完成
      for (const mid of modelIds) {
        const msgs = modelMessages.value[mid]
        if (msgs && msgs.length > 0) {
          const lastMsg = msgs[msgs.length - 1]
          if (lastMsg.isStreaming) {
            if (!lastMsg.content) {
              msgs.pop()
            } else {
              lastMsg.isStreaming = false
            }
          }
        }
      }
      streamingModelIds.value.clear()
      throw e
    } finally {
      streaming.value = false
    }
  }

  /** 更新对抗标题 */
  function updateArenaTitle(firstMessage: string) {
    if (!currentArena.value) return
    if (currentArena.value.title?.startsWith('对抗 (')) {
      const title = firstMessage.slice(0, 20) + (firstMessage.length > 20 ? '...' : '')
      currentArena.value.title = title
      const arena = arenas.value.find(a => a.id === currentArena.value!.id)
      if (arena) arena.title = title
    }
  }

  /** 删除对抗会话 */
  async function removeArena(id: number) {
    try {
      await deleteArenaApi(id)
      arenas.value = arenas.value.filter(a => a.id !== id)
      if (currentArena.value?.id === id) {
        currentArena.value = null
        modelMessages.value = {}
        userMessages.value = []
        activeModelId.value = null
      }
    } catch (e: any) {
      error.value = e.message || '删除失败'
      throw e
    }
  }

  /** 清空状态 */
  function clearState() {
    currentArena.value = null
    modelMessages.value = {}
    userMessages.value = []
    activeModelId.value = null
    error.value = null
  }

  return {
    // 状态
    arenas,
    currentArena,
    activeModelId,
    modelMessages,
    userMessages,
    loading,
    streaming,
    streamingModelIds,
    error,
    // 计算属性
    currentModelMessages,
    displayMessages,
    arenaModels,
    // 操作
    loadArenas,
    createNewArena,
    enterArena,
    loadHistory,
    switchModel,
    send,
    removeArena,
    clearState,
  }
})
