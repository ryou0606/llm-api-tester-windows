/**
 * 后端 API 调用封装
 * 所有与后端的 HTTP 通信通过此模块进行
 */

import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// ============ 类型定义 ============

export interface ModelConfig {
  id: number
  name: string
  api_type: string
  base_url: string
  api_key: string
  model_id: string
  context_window: number | null
  max_tokens: number | null
  supports_vision: boolean
  supports_audio: boolean
  is_active: boolean
  status: 'untested' | 'available' | 'unavailable'
  last_tested_at: string | null
  created_at: string
  updated_at: string
}

export interface ModelConfigCreate {
  name: string
  api_type: string
  base_url: string
  api_key: string
  model_id: string
  context_window?: number | null
  max_tokens?: number | null
  supports_vision?: boolean
  supports_audio?: boolean
}

export interface ModelConfigUpdate {
  name?: string
  api_type?: string
  base_url?: string
  api_key?: string
  model_id?: string
  context_window?: number | null
  max_tokens?: number | null
  supports_vision?: boolean
  supports_audio?: boolean
  is_active?: boolean
}

export interface TestConnectionResult {
  success: boolean
  message: string
  latency_ms?: number
  model?: string
}

export interface ApiType {
  value: string
  label: string
  description: string
}

// ============ API 函数 ============

/** 获取所有模型配置 */
export async function fetchModels(): Promise<ModelConfig[]> {
  const { data } = await api.get('/models')
  return data
}

/** 获取单个模型配置 */
export async function fetchModel(id: number): Promise<ModelConfig> {
  const { data } = await api.get(`/models/${id}`)
  return data
}

/** 创建模型配置 */
export async function createModel(config: ModelConfigCreate): Promise<ModelConfig> {
  const { data } = await api.post('/models', config)
  return data
}

/** 更新模型配置 */
export async function updateModel(id: number, config: ModelConfigUpdate): Promise<ModelConfig> {
  const { data } = await api.put(`/models/${id}`, config)
  return data
}

/** 删除模型配置 */
export async function deleteModel(id: number): Promise<void> {
  await api.delete(`/models/${id}`)
}

/** 测试模型连接 */
export async function testModelConnection(id: number): Promise<TestConnectionResult> {
  const { data } = await api.post(`/models/${id}/test`)
  return data
}

/** 获取支持的 API 类型列表 */
export async function fetchApiTypes(): Promise<ApiType[]> {
  const { data } = await api.get('/models/meta/api-types')
  return data.types
}

/** 健康检查 */
export async function healthCheck(): Promise<{ status: string; version: string }> {
  const { data } = await api.get('/health')
  return data
}

// ============ 智能粘贴 & 远程模型 ============

export interface SmartParseResult {
  name: string
  api_type: string
  base_url: string
  api_key: string
  model_id: string
  provider: string
  context_window: number | null
  max_tokens: number | null
  supports_vision: boolean
  supports_audio: boolean
  notes: string
  missing_fields: string[]
}

export interface SmartParseResponse {
  count: number
  models: SmartParseResult[]
}

export interface RemoteModel {
  id: string
  owned_by: string
  name: string
}

export interface FetchRemoteModelsResponse {
  success: boolean
  models: RemoteModel[]
  message: string
}

export interface ProviderSuggestion {
  provider: string
  base_url: string
  api_type: string
  keywords: string[]
}

/** 智能粘贴解析 */
export async function smartParse(text: string): Promise<SmartParseResponse> {
  const { data } = await api.post('/models/parse', { text })
  return data
}

/** 拉取远程模型列表 */
export async function fetchRemoteModels(base_url: string, api_key: string): Promise<FetchRemoteModelsResponse> {
  const { data } = await api.post('/models/fetch-remote-models', { base_url, api_key })
  return data
}

/** 搜索提供商建议 */
export async function searchProviders(q: string): Promise<ProviderSuggestion[]> {
  const { data } = await api.get('/models/providers', { params: { q } })
  return data
}
