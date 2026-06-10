<template>
  <div class="model-list">
    <!-- 顶部操作栏 -->
    <div class="page-header">
      <div class="header-left">
        <h2>{{ $t('model.config') }}</h2>
        <span class="model-count">{{ $t('model.count', { count: filteredModels.length }) }}</span>
      </div>
      <div class="header-right">
        <el-input
          v-model="searchQuery"
          :placeholder="$t('common.search')"
          :prefix-icon="Search"
          clearable
          style="width: 240px"
        />
        <el-button @click="openSmartPaste" :icon="DocumentCopy" size="large">
          {{ $t('common.smartPaste') }}
        </el-button>
        <el-button type="primary" @click="openAddDialog" :icon="Plus" size="large">
          {{ $t('common.add') }}
        </el-button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="store.loading && store.models.length === 0" v-loading="true" style="height: 200px"></div>

    <!-- 空状态 -->
    <el-empty v-else-if="store.models.length === 0" :description="$t('model.noModels')">
      <el-button type="primary" @click="openAddDialog">{{ $t('model.addFirst') }}</el-button>
    </el-empty>

    <el-empty v-else-if="filteredModels.length === 0" :description="$t('model.noMatch')" />

    <!-- 模型卡片列表 -->
    <div v-else class="model-grid">
      <el-card
        v-for="model in filteredModels"
        :key="model.id"
        class="model-card"
        shadow="hover"
      >
        <template #header>
          <div class="card-header">
            <div class="card-title">
              <span class="model-name">{{ model.name }}</span>
              <el-tag
                :type="statusTagType(model.status)"
                size="small"
                effect="light"
              >
                {{ statusLabel(model.status) }}
              </el-tag>
            </div>
            <div class="card-actions">
              <el-tooltip :content="$t('common.test')" placement="top">
                <el-button
                  :icon="Link"
                  circle
                  size="small"
                  @click="handleTest(model)"
                  :loading="testingIds.has(model.id)"
                />
              </el-tooltip>
              <el-tooltip :content="$t('common.edit')" placement="top">
                <el-button
                  :icon="Edit"
                  circle
                  size="small"
                  @click="openEditDialog(model)"
                />
              </el-tooltip>
              <el-tooltip :content="$t('common.delete')" placement="top">
                <el-button
                  :icon="Delete"
                  circle
                  size="small"
                  type="danger"
                  @click="handleDelete(model)"
                />
              </el-tooltip>
            </div>
          </div>
        </template>

        <div class="card-body">
          <div class="info-row">
            <span class="info-label">{{ $t('model.apiType') }}</span>
            <el-tag size="small" effect="plain">{{ apiTypeLabel(model.api_type) }}</el-tag>
          </div>
          <div class="info-row">
            <span class="info-label">{{ $t('model.baseUrl') }}</span>
            <span class="info-value url-text" :title="model.base_url">{{ model.base_url }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">{{ $t('model.id') }}</span>
            <el-tag size="small" type="info">{{ model.model_id }}</el-tag>
          </div>
          <div class="info-row">
            <span class="info-label">{{ $t('model.apiKey') }}</span>
            <span class="info-value key-text">{{ model.api_key }}</span>
          </div>
          <div class="info-row" v-if="model.context_window">
            <span class="info-label">{{ $t('model.contextWindow') }}</span>
            <span class="info-value">{{ formatNumber(model.context_window) }} tokens</span>
          </div>
          <div class="capability-tags">
            <el-tag v-if="model.supports_vision" type="success" size="small" effect="plain">
              👁 {{ $t('model.vision') }}
            </el-tag>
            <el-tag v-if="model.supports_audio" type="warning" size="small" effect="plain">
              🎤 {{ $t('model.audio') }}
            </el-tag>
          </div>
        </div>
      </el-card>
    </div>

    <!-- ==================== 智能粘贴弹窗 ==================== -->
    <el-dialog
      v-model="smartPasteVisible"
      :title="$t('smartPaste.title')"
      width="800px"
      :close-on-click-modal="false"
      :close-on-press-escape="true"
    >
      <!-- 第一步：粘贴文本 -->
      <div v-if="smartStep === 'paste'">
        <div class="smart-tip">
          <el-alert type="info" :closable="false" show-icon>
            <template #title>
              <div>{{ $t('smartPaste.tip') }}</div>
              <div style="margin-top: 4px; font-size: 12px; color: #909399;">
                {{ $t('smartPaste.tipExtra') }}
              </div>
            </template>
          </el-alert>
        </div>
        <el-input
          v-model="smartPasteText"
          type="textarea"
          :rows="14"
          :placeholder="$t('smartPaste.placeholderFull')"
          class="smart-textarea"
        />
      </div>

      <!-- 第二步：识别结果确认 -->
      <div v-if="smartStep === 'preview'">
        <div class="smart-tip">
          <el-alert
            :type="smartParseResults.length > 0 ? 'success' : 'warning'"
            :closable="false"
            show-icon
          >
            <template #title>
              <span v-if="smartParseResults.length > 0">
                {{ $t('smartPaste.recognize', { count: smartParseResults.length }) }}
              </span>
              <span v-else>{{ $t('smartPaste.recognizeFailed') }}</span>
            </template>
          </el-alert>
        </div>

        <div class="parsed-cards">
          <el-card
            v-for="(item, idx) in smartParseResults"
            :key="idx"
            class="parsed-card"
            shadow="never"
          >
            <template #header>
              <div class="parsed-card-header">
                <div class="parsed-card-title">
                  <el-tag v-if="item.provider" type="primary" size="small" effect="dark">
                    {{ item.provider }}
                  </el-tag>
                  <span class="parsed-name">{{ item.name || ($t('smartPaste.model') + ' ' + (idx + 1)) }}</span>
                </div>
                <div class="parsed-card-actions">
                  <el-button size="small" text type="primary" @click="editParsedItem(idx)">
                    {{ $t('common.edit') }}
                  </el-button>
                  <el-button size="small" text type="danger" @click="removeParsedItem(idx)">
                    {{ $t('common.remove') }}
                  </el-button>
                </div>
              </div>
            </template>

            <!-- 编辑模式 -->
            <div v-if="editingParsedIdx === idx" class="parsed-edit-form">
              <el-form label-width="80px" size="small">
                <el-form-item :label="$t('model.name')">
                  <el-input v-model="item.name" :placeholder="$t('model.name')" />
                </el-form-item>
                <el-form-item :label="$t('model.baseUrl')">
                  <el-input v-model="item.base_url" placeholder="https://..." />
                </el-form-item>
                <el-form-item :label="$t('model.apiKey')">
                  <el-input v-model="item.api_key" placeholder="sk-..." show-password />
                </el-form-item>
                <el-form-item :label="$t('model.id')">
                  <el-input v-model="item.model_id" :placeholder="$t('model.id')" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" size="small" @click="editingParsedIdx = -1">
                    {{ $t('model.finishEdit') }}
                  </el-button>
                </el-form-item>
              </el-form>
            </div>

            <!-- 展示模式 -->
            <div v-else class="parsed-card-body">
              <div class="parsed-field" v-if="item.base_url">
                <span class="parsed-label">Base URL</span>
                <span class="parsed-value url-text">{{ item.base_url }}</span>
              </div>
              <div class="parsed-field" v-if="item.api_key">
                <span class="parsed-label">{{ $t('model.apiKey') }}</span>
                <span class="parsed-value key-text">{{ maskKey(item.api_key) }}</span>
              </div>
              <div class="parsed-field" v-if="item.model_id">
                <span class="parsed-label">{{ $t('model.id') }}</span>
                <el-tag size="small" type="info">{{ item.model_id }}</el-tag>
              </div>
              <div class="parsed-field" v-if="item.notes">
                <span class="parsed-label">{{ $t('model.notes') }}</span>
                <span class="parsed-value">{{ item.notes }}</span>
              </div>
              <div v-if="item.missing_fields.length > 0" class="parsed-missing">
                <el-tag type="warning" size="small" effect="plain">
                  {{ $t('model.missingField', { fields: item.missing_fields.join(', ') }) }}
                </el-tag>
              </div>
            </div>
          </el-card>
        </div>
      </div>

      <template #footer>
        <div v-if="smartStep === 'paste'">
          <el-button @click="smartPasteVisible = false">{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" @click="handleSmartParse" :loading="smartParsing" :disabled="!smartPasteText.trim()">
            {{ $t('smartPaste.recognizeBtn') }}
          </el-button>
        </div>
        <div v-if="smartStep === 'preview'">
          <el-button @click="smartStep = 'paste'">{{ $t('smartPaste.goBack') }}</el-button>
          <el-button @click="smartPasteVisible = false">{{ $t('common.cancel') }}</el-button>
          <el-button
            type="primary"
            @click="handleSmartSave"
            :loading="smartSaving"
            :disabled="validParsedModels.length === 0"
          >
            {{ $t('smartPaste.confirmSave', { count: validParsedModels.length }) }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- ==================== 添加/编辑模型弹窗 ==================== -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? $t('model.editModel') : $t('model.addModel')"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
        label-position="right"
      >
        <el-form-item :label="$t('model.name')" prop="name">
          <el-input v-model="formData.name" :placeholder="$t('model.namePlaceholder')" maxlength="255" show-word-limit />
        </el-form-item>

        <el-form-item :label="$t('model.apiType')" prop="api_type">
          <el-select v-model="formData.api_type" :placeholder="$t('model.selectApiType')" style="width: 100%">
            <el-option
              v-for="t in store.apiTypes"
              :key="t.value"
              :label="t.label"
              :value="t.value"
            >
              <div>
                <span>{{ t.label }}</span>
                <span style="color: #999; font-size: 12px; margin-left: 8px">{{ t.description }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('model.baseUrl')" prop="base_url">
          <el-input v-model="formData.base_url" :placeholder="$t('model.baseUrlPlaceholder')" />
        </el-form-item>

        <el-form-item :label="$t('model.apiKey')" prop="api_key">
          <el-input v-model="formData.api_key" :placeholder="isEditing ? $t('model.apiKeyEditPlaceholder') : 'sk-...'" show-password />
        </el-form-item>

        <el-form-item :label="$t('model.id')" prop="model_id">
          <div style="display: flex; gap: 8px; width: 100%">
            <el-input v-model="formData.model_id" placeholder="e.g. gpt-4o, claude-3.5-sonnet" style="flex: 1" />
            <el-button
              @click="handleFetchRemoteModels"
              :loading="fetchingModels"
              :disabled="!formData.base_url || !formData.api_key"
              title="$t('model.fetchModels')"
            >
              🔄 {{ $t('model.fetchList') }}
            </el-button>
          </div>
        </el-form-item>

        <!-- 远程模型列表选择 -->
        <el-form-item v-if="remoteModels.length > 0" :label="$t('model.availableModels')">
          <div class="remote-models-panel">
            <el-input
              v-model="remoteModelSearch"
              :placeholder="$t('common.search')"
              size="small"
              clearable
              style="margin-bottom: 8px"
            />
            <!-- $t('model.selectAll')/取消$t('model.selectAll') -->
            <div class="remote-models-toolbar" v-if="!isEditing">
              <el-checkbox
                :model-value="selectedRemoteModels.size > 0 && selectedRemoteModels.size === filteredRemoteModels.length"
                :indeterminate="selectedRemoteModels.size > 0 && selectedRemoteModels.size < filteredRemoteModels.length"
                @change="toggleSelectAll"
              >
                $t('model.selectAll')
              </el-checkbox>
              <span class="selected-count" v-if="selectedRemoteModels.size > 0">
                {{ $t('model.selectedCount', { count: selectedRemoteModels.size }) }}
              </span>
            </div>
            <div class="remote-models-list">
              <div
                v-for="m in filteredRemoteModels"
                :key="m.id"
                class="remote-model-item"
                :class="{
                  selected: isEditing ? formData.model_id === m.id : selectedRemoteModels.has(m.id),
                  'single-selected': isEditing && formData.model_id === m.id
                }"
                @click="handleRemoteModelClick(m)"
              >
                <el-checkbox
                  v-if="!isEditing"
                  :model-value="selectedRemoteModels.has(m.id)"
                  @click.stop
                  @change="toggleRemoteModel(m.id)"
                  style="margin-right: 8px"
                />
                <span class="remote-model-id">{{ m.id }}</span>
                <span class="remote-model-owner" v-if="m.owned_by">{{ m.owned_by }}</span>
              </div>
            </div>
            <div class="remote-models-count">
              {{ $t('model.totalModels', { total: remoteModels.length, shown: filteredRemoteModels.length }) }}
            </div>
          </div>
        </el-form-item>

        <el-form-item :label="$t('model.contextWindow')">
          <el-input-number
            v-model="formData.context_window"
            :min="0"
            :step="1000"
            :placeholder="$t('model.autoFill')"
            style="width: 100%"
          />
          <div class="form-tip">$t('model.autoFillTip')</div>
        </el-form-item>

        <el-form-item :label="$t('model.maxToken')">
          <el-input-number
            v-model="formData.max_tokens"
            :min="1"
            :step="1000"
            :placeholder="$t('common.optional')"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item :label="$t('model.capabilities')">
          <el-checkbox v-model="formData.supports_vision">$t('model.supportsVision')</el-checkbox>
          <el-checkbox v-model="formData.supports_audio">$t('model.supportsAudio')</el-checkbox>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button
          v-if="!isEditing && selectedRemoteModels.size > 1"
          type="success"
          @click="handleBatchAdd"
          :loading="store.loading"
        >
          🚀 {{ $t('model.batchAdd') }} ({{ selectedRemoteModels.size }})
        </el-button>
        <el-button type="primary" @click="handleSubmit" :loading="store.loading">
          {{ isEditing ? t('common.save') : t('common.add') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { Plus, Edit, Delete, Link, Search, DocumentCopy } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { useModelStore } from '@/stores/model'
import type { ModelConfig, ModelConfigCreate, SmartParseResult, RemoteModel } from '@/api/models'
import { smartParse, fetchRemoteModels } from '@/api/models'

const { t } = useI18n()
const store = useModelStore()
const formRef = ref<FormInstance>()
const dialogVisible = ref(false)
const isEditing = ref(false)
const editingId = ref<number | null>(null)
const testingIds = ref(new Set<number>())
const searchQuery = ref('')

// 智能粘贴相关
const smartPasteVisible = ref(false)
const smartStep = ref<'paste' | 'preview'>('paste')
const smartPasteText = ref('')
const smartParsing = ref(false)
const smartSaving = ref(false)
const smartParseResults = ref<SmartParseResult[]>([])
const editingParsedIdx = ref(-1)

// 远程模型列表相关
const fetchingModels = ref(false)
const remoteModels = ref<RemoteModel[]>([])
const remoteModelSearch = ref('')
const selectedRemoteModels = ref<Set<string>>(new Set())

// 搜索过滤
const filteredModels = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return store.models
  return store.models.filter(m =>
    m.name.toLowerCase().includes(q) ||
    m.model_id.toLowerCase().includes(q) ||
    m.base_url.toLowerCase().includes(q)
  )
})

// 远程模型过滤
const filteredRemoteModels = computed(() => {
  const q = remoteModelSearch.value.trim().toLowerCase()
  if (!q) return remoteModels.value
  return remoteModels.value.filter(m =>
    m.id.toLowerCase().includes(q) ||
    m.owned_by.toLowerCase().includes(q)
  )
})

// 有效解析结果（必填字段完整）
const validParsedModels = computed(() => {
  return smartParseResults.value.filter(m =>
    m.base_url && m.api_key && m.model_id
  )
})

// 表单数据
const formData = reactive<ModelConfigCreate>({
  name: '',
  api_type: 'openai_compat',
  base_url: '',
  api_key: '',
  model_id: '',
  context_window: null,
  max_tokens: null,
  supports_vision: false,
  supports_audio: false,
})

// 表单验证规则（api_key 在编辑模式下非必填）
const formRules: FormRules = {
  name: [{ required: true, message: t('model.name'), trigger: 'blur' }],
  api_type: [{ required: true, message: t('model.apiType'), trigger: 'change' }],
  base_url: [{ required: true, message: t('model.baseUrl'), trigger: 'blur' }],
  api_key: [{
    validator: (_rule: any, _value: string, callback: any) => {
      // 编辑模式下 api_key 非必填
      if (!isEditing.value && !_value) {
        callback(new Error(t('model.apiKey')))
      } else {
        callback()
      }
    },
    trigger: 'blur',
  }],
  model_id: [{ required: true, message: t('model.id'), trigger: 'blur' }],
}

// ============ 辅助函数 ============

function statusTagType(status: string) {
  switch (status) {
    case 'available': return 'success'
    case 'unavailable': return 'danger'
    default: return 'info'
  }
}

function statusLabel(status: string) {
  switch (status) {
    case 'available': return t('model.statusAvailable')
    case 'unavailable': return t('model.statusUnavailable')
    default: return t('model.statusNotTested')
  }
}

function apiTypeLabel(type: string) {
  const found = store.apiTypes.find(t => t.value === type)
  return found ? found.label : type
}

function formatNumber(num: number): string {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(0) + 'K'
  return num.toString()
}

function maskKey(key: string): string {
  if (!key) return ''
  if (key.length <= 8) return '****'
  return key.slice(0, 4) + '****' + key.slice(-4)
}

function resetForm() {
  formData.name = ''
  formData.api_type = 'openai_compat'
  formData.base_url = ''
  formData.api_key = ''
  formData.model_id = ''
  formData.context_window = null
  formData.max_tokens = null
  formData.supports_vision = false
  formData.supports_audio = false
  remoteModels.value = []
  remoteModelSearch.value = ''
  selectedRemoteModels.value = new Set()
}

// ============ 智能粘贴 ============

function openSmartPaste() {
  smartPasteText.value = ''
  smartParseResults.value = []
  smartStep.value = 'paste'
  editingParsedIdx.value = -1
  smartPasteVisible.value = true
}

async function handleSmartParse() {
  if (!smartPasteText.value.trim()) return

  smartParsing.value = true
  try {
    const result = await smartParse(smartPasteText.value)
    smartParseResults.value = result.models
    if (result.count === 0) {
      ElMessage.warning(t('smartPaste.recognizeFailed'))
      return
    }
    smartStep.value = 'preview'
    ElMessage.success(t('smartPaste.recognize', { count: result.count }))
  } catch (e: any) {
    ElMessage.error(t('smartPaste.parseFailed') + ': ' + (e.response?.data?.detail || e.message))
  } finally {
    smartParsing.value = false
  }
}

function editParsedItem(idx: number) {
  editingParsedIdx.value = idx
}

function removeParsedItem(idx: number) {
  smartParseResults.value.splice(idx, 1)
  if (editingParsedIdx.value >= smartParseResults.value.length) {
    editingParsedIdx.value = -1
  }
}

async function handleSmartSave() {
  const models = validParsedModels.value
  if (models.length === 0) {
    ElMessage.warning(t('smartPaste.noConfig'))
    return
  }

  smartSaving.value = true
  let successCount = 0
  let failCount = 0

  for (const m of models) {
    try {
      await store.addModel({
        name: m.name,
        api_type: m.api_type,
        base_url: m.base_url,
        api_key: m.api_key,
        model_id: m.model_id,
        context_window: m.context_window,
        max_tokens: m.max_tokens,
        supports_vision: m.supports_vision,
        supports_audio: m.supports_audio,
      })
      successCount++
    } catch {
      failCount++
    }
  }

  smartSaving.value = false
  smartPasteVisible.value = false

  if (successCount > 0) {
    ElMessage.success(t('model.saveSuccess', { success: successCount, fail: failCount }))
  } else {
    ElMessage.error(t('common.error'))
  }
}

// ============ 远程模型拉取 ============

async function handleFetchRemoteModels() {
  if (!formData.base_url || !formData.api_key) {
    ElMessage.warning(t('model.fillBaseUrlKey'))
    return
  }

  fetchingModels.value = true
  remoteModels.value = []
  remoteModelSearch.value = ''
  selectedRemoteModels.value = new Set()

  try {
    const result = await fetchRemoteModels(formData.base_url, formData.api_key)
    if (result.success) {
      remoteModels.value = result.models
      ElMessage.success(result.message)
    } else {
      ElMessage.error(result.message)
    }
  } catch (e: any) {
    ElMessage.error(t('model.fetchFailed') + ': ' + (e.response?.data?.detail || e.message))
  } finally {
    fetchingModels.value = false
  }
}

// ============ 远程模型多选 ============

function handleRemoteModelClick(m: RemoteModel) {
  if (isEditing.value) {
    // 编辑模式：单选
    formData.model_id = m.id
    formData.name = formData.name || m.id
  } else {
    // 添加模式：切换多选
    toggleRemoteModel(m.id)
  }
}

function toggleRemoteModel(modelId: string) {
  const newSet = new Set(selectedRemoteModels.value)
  if (newSet.has(modelId)) {
    newSet.delete(modelId)
  } else {
    newSet.add(modelId)
  }
  selectedRemoteModels.value = newSet
  // 同时更新 model_id 为最后选中的（单个添加时使用）
  if (newSet.size === 1) {
    formData.model_id = [...newSet][0]
    formData.name = formData.name || formData.model_id
  } else if (newSet.size === 0) {
    formData.model_id = ''
  }
}

function toggleSelectAll(checked: boolean) {
  if (checked) {
    const all = new Set(filteredRemoteModels.value.map(m => m.id))
    selectedRemoteModels.value = all
    if (all.size === 1) {
      formData.model_id = [...all][0]
      formData.name = formData.name || formData.model_id
    }
  } else {
    selectedRemoteModels.value = new Set()
    formData.model_id = ''
  }
}

async function handleBatchAdd() {
  const selected = [...selectedRemoteModels.value]
  if (selected.length === 0) {
    ElMessage.warning(t('model.selectAtLeast'))
    return
  }
  if (!formData.base_url || !formData.api_key) {
    ElMessage.warning(t('model.fillBaseUrlKey'))
    return
  }

  // 检查重复
  const duplicates: string[] = []
  const newModels: string[] = []
  for (const modelId of selected) {
    const exists = store.models.some(m =>
      m.base_url === formData.base_url && m.model_id === modelId
    )
    if (exists) {
      duplicates.push(modelId)
    } else {
      newModels.push(modelId)
    }
  }

  if (duplicates.length > 0) {
    if (newModels.length === 0) {
      ElMessage.warning(t('model.allExist', { models: duplicates.join(', ') }))
      return
    }
    try {
      await ElMessageBox.confirm(
        t('model.existWillSkip', { models: duplicates.join('\n'), count: newModels.length }),
        t('model.partialExist'),
        { type: 'warning', confirmButtonText: t('model.continueAdd'), cancelButtonText: t('common.cancel') }
      )
    } catch {
      return
    }
  }

  // 批量创建
  let successCount = 0
  let failCount = 0
  for (const modelId of newModels) {
    try {
      await store.addModel({
        name: selected.length > 1 ? modelId : (formData.name || modelId),
        api_type: formData.api_type,
        base_url: formData.base_url,
        api_key: formData.api_key,
        model_id: modelId,
        context_window: formData.context_window,
        max_tokens: formData.max_tokens,
        supports_vision: formData.supports_vision,
        supports_audio: formData.supports_audio,
      })
      successCount++
    } catch {
      failCount++
    }
  }

  dialogVisible.value = false
  if (successCount > 0) {
    ElMessage.success(t('model.addSuccess', { success: successCount, fail: failCount }))
  } else {
    ElMessage.error(t('model.addFailed'))
  }
}

// ============ 常规操作 ============

function openAddDialog() {
  isEditing.value = false
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(model: ModelConfig) {
  isEditing.value = true
  editingId.value = model.id
  formData.name = model.name
  formData.api_type = model.api_type
  formData.base_url = model.base_url
  formData.api_key = ''  // 不回填密钥
  formData.model_id = model.model_id
  formData.context_window = model.context_window
  formData.max_tokens = model.max_tokens
  formData.supports_vision = model.supports_vision
  formData.supports_audio = model.supports_audio
  remoteModels.value = []
  selectedRemoteModels.value = new Set()
  dialogVisible.value = true
  // 清除之前的验证状态
  nextTick(() => {
    formRef.value?.clearValidate()
  })
}

async function handleSubmit() {
  // 非编辑模式需要验证表单
  if (!isEditing.value) {
    const valid = await formRef.value?.validate().catch(() => false)
    if (!valid) return
  }

  try {
    if (isEditing.value && editingId.value !== null) {
      const updateData: any = { ...formData }
      if (!updateData.api_key) delete updateData.api_key
      // 确保 context_window 和 max_tokens 不会传 0（除非用户明确设置）
      if (updateData.context_window === 0) updateData.context_window = null
      if (updateData.max_tokens === 0) updateData.max_tokens = null
      await store.editModel(editingId.value, updateData)
      ElMessage.success(t('model.updateSuccess'))
    } else {
      // 新增时检查重复
      const exists = store.models.some(m =>
        m.base_url === formData.base_url && m.model_id === formData.model_id
      )
      if (exists) {
        try {
          await ElMessageBox.confirm(
            t('model.duplicateConfirm', { url: formData.base_url, id: formData.model_id }),
            t('model.modelExists'),
            { type: 'warning', confirmButtonText: t('model.stillAdd'), cancelButtonText: t('common.cancel') }
          )
        } catch {
          return
        }
      }
      await store.addModel(formData)
      ElMessage.success(t('model.addSuccess'))
    }
    dialogVisible.value = false
  } catch (e: any) {
    ElMessage.error(store.error || t('common.error'))
  }
}

async function handleDelete(model: ModelConfig) {
  try {
    await ElMessageBox.confirm(
      t('model.deleteConfirm', { name: model.name }),
      t('common.confirm'),
      { type: 'warning', confirmButtonText: t('common.delete'), cancelButtonText: t('common.cancel') }
    )
    await store.removeModel(model.id)
    ElMessage.success(t('common.deleted'))
  } catch {
    // 用户取消
  }
}

async function handleTest(model: ModelConfig) {
  testingIds.value.add(model.id)
  try {
    const result = await store.testConnection(model.id)
    if (result.success) {
      ElMessage.success(t('model.testSuccess', { latency: result.latency_ms }))
    } else {
      ElMessage.error(result.message)
    }
  } finally {
    testingIds.value.delete(model.id)
  }
}

// ============ 生命周期 ============

onMounted(async () => {
  await Promise.all([store.loadModels(), store.loadApiTypes()])
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-left h2 {
  font-size: 22px;
  font-weight: 600;
  color: #303133;
}

.model-count {
  font-size: 14px;
  color: #909399;
}

.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 20px;
}

.model-card {
  border-radius: 12px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.model-card:hover {
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.model-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-label {
  font-size: 13px;
  color: #909399;
  flex-shrink: 0;
  min-width: 70px;
}

.info-value {
  font-size: 13px;
  color: #303133;
  min-width: 0;
}

.url-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
  font-size: 12px;
}

.key-text {
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
  font-size: 12px;
  color: #909399;
}

.capability-tags {
  display: flex;
  gap: 6px;
  margin-top: 4px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

/* ============ 智能粘贴样式 ============ */

.smart-tip {
  margin-bottom: 16px;
}

.smart-textarea {
  font-family: 'SF Mono', 'Monaco', 'Menlo', 'Consolas', monospace;
}

.parsed-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 500px;
  overflow-y: auto;
  padding: 4px 0;
}

.parsed-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.parsed-card :deep(.el-card__header) {
  padding: 10px 16px;
  background: #f5f7fa;
}

.parsed-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.parsed-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.parsed-name {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.parsed-card-actions {
  display: flex;
  gap: 4px;
}

.parsed-card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.parsed-field {
  display: flex;
  align-items: center;
  gap: 8px;
}

.parsed-label {
  font-size: 12px;
  color: #909399;
  flex-shrink: 0;
  min-width: 65px;
}

.parsed-value {
  font-size: 13px;
  color: #303133;
  min-width: 0;
  word-break: break-all;
}

.parsed-missing {
  margin-top: 4px;
}

.parsed-edit-form {
  padding: 8px 0;
}

/* ============ 远程模型列表样式 ============ */

.remote-models-panel {
  width: 100%;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px;
  background: #fafafa;
}

.remote-models-list {
  max-height: 240px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.remote-model-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
  font-size: 13px;
}

.remote-model-item:hover {
  background: #ecf5ff;
}

.remote-model-item.selected {
  background: #409eff;
  color: white;
}

.remote-model-item.selected .remote-model-owner,
.remote-model-item.selected :deep(.el-checkbox__label) {
  color: rgba(255, 255, 255, 0.8);
}

.remote-model-item.selected :deep(.el-checkbox__inner) {
  border-color: rgba(255, 255, 255, 0.8);
}

.remote-model-item.single-selected {
  background: #409eff;
  color: white;
}

.remote-model-item.single-selected .remote-model-owner {
  color: rgba(255, 255, 255, 0.8);
}

.remote-models-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  padding: 4px 0;
  border-bottom: 1px solid #ebeef5;
}

.selected-count {
  font-size: 12px;
  color: #409eff;
  font-weight: 500;
}

.remote-model-id {
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
  font-size: 12px;
}

.remote-model-owner {
  font-size: 11px;
  color: #909399;
}

.remote-models-count {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
  text-align: center;
}
</style>
