/**
 * Pinia 模型状态管理
 * 管理模型配置的全局状态
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ModelConfig, ModelConfigCreate, ModelConfigUpdate, ApiType, TestConnectionResult, SmartParseResponse, FetchRemoteModelsResponse } from '@/api/models'
import {
  fetchModels,
  createModel,
  updateModel,
  deleteModel,
  testModelConnection,
  fetchApiTypes,
  smartParse,
  fetchRemoteModels,
} from '@/api/models'

export const useModelStore = defineStore('model', () => {
  // ============ 状态 ============

  const models = ref<ModelConfig[]>([])
  const apiTypes = ref<ApiType[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ============ 操作 ============

  /** 加载所有模型配置 */
  async function loadModels() {
    loading.value = true
    error.value = null
    try {
      models.value = await fetchModels()
    } catch (e: any) {
      error.value = e.response?.data?.detail || '加载模型列表失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /** 加载 API 类型列表 */
  async function loadApiTypes() {
    try {
      apiTypes.value = await fetchApiTypes()
    } catch (e: any) {
      console.error('加载 API 类型失败:', e)
    }
  }

  /** 添加模型 */
  async function addModel(config: ModelConfigCreate) {
    loading.value = true
    error.value = null
    try {
      const newModel = await createModel(config)
      models.value.unshift(newModel)
      return newModel
    } catch (e: any) {
      error.value = e.response?.data?.detail || '创建模型失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /** 更新模型 */
  async function editModel(id: number, config: ModelConfigUpdate) {
    loading.value = true
    error.value = null
    try {
      const updated = await updateModel(id, config)
      const index = models.value.findIndex(m => m.id === id)
      if (index !== -1) {
        models.value[index] = updated
      }
      return updated
    } catch (e: any) {
      error.value = e.response?.data?.detail || '更新模型失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /** 删除模型 */
  async function removeModel(id: number) {
    loading.value = true
    error.value = null
    try {
      await deleteModel(id)
      models.value = models.value.filter(m => m.id !== id)
    } catch (e: any) {
      error.value = e.response?.data?.detail || '删除模型失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /** 测试模型连接 */
  async function testConnection(id: number) {
    try {
      const result = await testModelConnection(id)
      // 更新本地模型状态
      const index = models.value.findIndex(m => m.id === id)
      if (index !== -1) {
        models.value[index].status = result.success ? 'available' : 'unavailable'
        models.value[index].last_tested_at = new Date().toISOString()
      }
      return result
    } catch (e: any) {
      const msg = e.response?.data?.detail || '测试连接失败'
      return { success: false, message: msg } as TestConnectionResult
    }
  }

  return {
    models,
    apiTypes,
    loading,
    error,
    loadModels,
    loadApiTypes,
    addModel,
    editModel,
    removeModel,
    testConnection,
  }
})
