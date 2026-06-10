<template>
  <div class="model-test">
    <!-- 左侧面板 -->
    <div class="left-panel">
      <!-- 模型选择 -->
      <div class="panel-section">
        <div class="section-title">{{ $t('chat.selectModel') }}</div>
        <el-select
          v-model="selectedModelId"
          :placeholder="$t('chat.pleaseSelectModel')"
          style="width: 100%"
          @change="handleModelChange"
        >
          <el-option
            v-for="model in modelStore.models"
            :key="model.id"
            :label="model.name"
            :value="model.id"
          >
            <div class="model-option">
              <span class="option-name">{{ model.name }}</span>
              <el-tag
                :type="model.status === 'available' ? 'success' : model.status === 'unavailable' ? 'danger' : 'info'"
                size="small"
                effect="light"
              >
                {{ model.status === 'available' ? $t('model.statusAvailable') : model.status === 'unavailable' ? $t('model.statusUnavailable') : $t('model.statusNotTested') }}
              </el-tag>
            </div>
          </el-option>
        </el-select>
      </div>

      <!-- 新建对话按钮 -->
      <div class="panel-section">
        <el-button
          type="primary"
          style="width: 100%"
          :icon="Plus"
          :disabled="!selectedModelId"
          @click="handleCreateConversation"
        >
          {{ $t('chat.newConversation') }}
        </el-button>
      </div>

      <!-- 对话历史列表 -->
      <div class="panel-section history-section">
        <div class="section-title">{{ $t('chat.history') }}</div>
        <div v-if="chatStore.loading && chatStore.conversations.length === 0" class="history-loading">
          <el-icon class="is-loading"><Loading /></el-icon>
        </div>
        <el-empty v-else-if="chatStore.conversations.length === 0" :description="$t('chat.noConversations')" :image-size="60" />
        <div v-else class="history-list">
          <div
            v-for="conv in chatStore.conversations"
            :key="conv.id"
            class="history-item"
            :class="{ active: chatStore.currentConversation?.id === conv.id }"
            @click="handleSelectConversation(conv.id)"
          >
            <div class="history-title">{{ conv.title || $t('chat.defaultTitle') }}</div>
            <div class="history-time">{{ formatTime(conv.created_at) }}</div>
            <el-button
              class="history-delete"
              :icon="Delete"
              circle
              size="small"
              type="danger"
              plain
              @click.stop="handleDeleteConversation(conv.id)"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧主区域 -->
    <div class="main-area">
      <!-- 无对话时的提示 -->
      <div v-if="!chatStore.currentConversation" class="main-empty">
        <el-icon :size="64" color="#c0c4cc"><ChatDotRound /></el-icon>
        <h3>{{ $t('chat.selectOrCreate') }}</h3>
        <p>{{ $t('chat.selectOrCreateHint') }}</p>
      </div>

      <!-- 对话界面 -->
      <template v-else>
        <ChatBox
          ref="chatBoxRef"
          :messages="chatStore.messages"
          :loading="chatStore.loading"
          :streaming="chatStore.streaming"
          @send="handleSend"
        />
      </template>
    </div>

    <!-- 右侧信息面板（可折叠） -->
    <div class="info-panel" :class="{ collapsed: infoPanelCollapsed }">
      <div class="panel-toggle" @click="infoPanelCollapsed = !infoPanelCollapsed">
        <el-icon>
          <ArrowRight v-if="infoPanelCollapsed" />
          <ArrowLeft v-else />
        </el-icon>
      </div>
      <div v-if="!infoPanelCollapsed" class="panel-content">
        <div class="section-title">{{ $t('chat.modelInfo') }}</div>
        <template v-if="selectedModel">
          <div class="info-item">
            <span class="info-label">{{ $t('chat.name') }}</span>
            <span class="info-value">{{ selectedModel.name }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ $t('model.id') }}</span>
            <span class="info-value mono">{{ selectedModel.model_id }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ $t('model.apiType') }}</span>
            <span class="info-value">{{ apiTypeLabel(selectedModel.api_type) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Base URL</span>
            <span class="info-value mono url-text" :title="selectedModel.base_url">{{ selectedModel.base_url }}</span>
          </div>
          <div v-if="selectedModel.context_window" class="info-item">
            <span class="info-label">{{ $t('model.contextWindow') }}</span>
            <span class="info-value">{{ formatNumber(selectedModel.context_window) }} tokens</span>
          </div>
          <div v-if="selectedModel.max_tokens" class="info-item">
            <span class="info-label">{{ $t('model.maxOutput') }}</span>
            <span class="info-value">{{ formatNumber(selectedModel.max_tokens) }} tokens</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ $t('model.modalitySupport') }}</span>
            <div class="info-value capability-tags">
              <el-tag v-if="selectedModel.supports_vision" type="success" size="small" effect="plain">
                👁 {{ $t('model.vision') }}
              </el-tag>
              <el-tag v-if="selectedModel.supports_audio" type="warning" size="small" effect="plain">
                🎤 {{ $t('model.audio') }}
              </el-tag>
              <el-tag v-if="!selectedModel.supports_vision && !selectedModel.supports_audio" size="small" effect="plain">
                {{ $t('model.textOnly') }}
              </el-tag>
            </div>
          </div>
          <div class="info-item">
            <span class="info-label">{{ $t('model.status') }}</span>
            <el-tag
              :type="selectedModel.status === 'available' ? 'success' : selectedModel.status === 'unavailable' ? 'danger' : 'info'"
              size="small"
              effect="light"
            >
              {{ selectedModel.status === 'available' ? $t('model.statusAvailable') : selectedModel.status === 'unavailable' ? $t('model.statusUnavailable') : $t('model.statusNotTested') }}
            </el-tag>
          </div>
        </template>
        <div v-else class="info-empty">
          <span>{{ $t('chat.pleaseSelectModelFirst') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Delete, Loading, ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ChatBox from '@/components/ChatBox.vue'
import { useModelStore } from '@/stores/model'
import { useChatStore } from '@/stores/chat'
import type { ModelConfig } from '@/api/models'

const modelStore = useModelStore()
const chatStore = useChatStore()
const { t } = useI18n()

const chatBoxRef = ref<InstanceType<typeof ChatBox>>()
const selectedModelId = ref<number | null>(null)
const infoPanelCollapsed = ref(false)

// ============ 计算属性 ============

/** 当前选中的模型配置 */
const selectedModel = computed<ModelConfig | null>(() => {
  if (!selectedModelId.value) return null
  return modelStore.models.find(m => m.id === selectedModelId.value) || null
})

// ============ 方法 ============

function apiTypeLabel(type: string): string {
  const found = modelStore.apiTypes.find(t => t.value === type)
  return found ? found.label : type
}

function formatNumber(num: number): string {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(0) + 'K'
  return num.toString()
}

function formatTime(isoStr: string): string {
  try {
    const date = new Date(isoStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMin = Math.floor(diffMs / 60000)

    if (diffMin < 1) return t('chat.timeJustNow')
    if (diffMin < 60) return t('chat.timeMinutesAgo', { n: diffMin })
    const diffHour = Math.floor(diffMin / 60)
    if (diffHour < 24) return t('chat.timeHoursAgo', { n: diffHour })

    // 超过一天显示日期
    const month = (date.getMonth() + 1).toString().padStart(2, '0')
    const day = date.getDate().toString().padStart(2, '0')
    const hours = date.getHours().toString().padStart(2, '0')
    const mins = date.getMinutes().toString().padStart(2, '0')
    return `${month}-${day} ${hours}:${mins}`
  } catch {
    return isoStr
  }
}

/** 模型选择变化 */
function handleModelChange() {
  // 切换模型时清空当前对话
  chatStore.clearState()
  if (selectedModelId.value) {
    chatStore.loadConversations()
  }
}

/** 创建新对话 */
async function handleCreateConversation() {
  if (!selectedModelId.value) return
  try {
    await chatStore.createNewConversation(selectedModelId.value)
    ElMessage.success(t('chat.conversationCreated'))
  } catch (e: any) {
    ElMessage.error(t('chat.createFailed'))
  }
}

/** 选择对话 */
async function handleSelectConversation(id: number) {
  await chatStore.switchConversation(id)
}

/** 删除对话 */
async function handleDeleteConversation(id: number) {
  try {
    await ElMessageBox.confirm(t('chat.deleteConfirm'), t('chat.confirmDelete'), {
      type: 'warning',
      confirmButtonText: t('common.delete'),
      cancelButtonText: t('common.cancel'),
    })
    await chatStore.removeConversation(id)
    ElMessage.success(t('chat.conversationDeleted'))
  } catch {
    // 用户取消
  }
}

/** 发送消息（使用流式模式） */
async function handleSend(content: string, imageData?: string) {
  if (!selectedModelId.value || !chatStore.currentConversation) return

  try {
    await chatStore.sendStream(selectedModelId.value, content, imageData)
  } catch (e: any) {
    ElMessage.error(e.message || t('chat.sendFailed'))
  }
}

// ============ 生命周期 ============

onMounted(async () => {
  await modelStore.loadModels()
  await modelStore.loadApiTypes()
  await chatStore.loadConversations()

  // 如果 URL 中有模型 ID，自动选中
  // 路由格式: /test/:id
  const pathParts = window.location.pathname.split('/')
  const idFromUrl = pathParts[pathParts.length - 1]
  if (idFromUrl && idFromUrl !== '0') {
    const id = parseInt(idFromUrl)
    if (!isNaN(id) && modelStore.models.some(m => m.id === id)) {
      selectedModelId.value = id
    }
  }
})
</script>

<style scoped>
.model-test {
  display: flex;
  height: calc(100vh - 48px);
  gap: 0;
  margin: -24px;
}

/* ============ 左侧面板 ============ */

.left-panel {
  width: 250px;
  min-width: 250px;
  background: #fff;
  border-right: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-section {
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
}

.model-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.option-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  margin-right: 8px;
}

/* ============ 历史列表 ============ */

.history-section {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.history-loading {
  display: flex;
  justify-content: center;
  padding: 20px;
  color: #909399;
}

.history-list {
  flex: 1;
  overflow-y: auto;
}

.history-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  cursor: pointer;
  border-radius: 8px;
  margin-bottom: 4px;
  transition: background 0.2s;
  position: relative;
}

.history-item:hover {
  background: #f5f7fa;
}

.history-item.active {
  background: #ecf5ff;
  border-left: 3px solid #409eff;
}

.history-title {
  flex: 1;
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 4px;
}

.history-time {
  font-size: 11px;
  color: #c0c4cc;
  flex-shrink: 0;
  margin-right: 4px;
}

.history-delete {
  opacity: 0;
  transition: opacity 0.2s;
  flex-shrink: 0;
}

.history-item:hover .history-delete {
  opacity: 1;
}

/* ============ 主区域 ============ */

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
  min-width: 0;
}

.main-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #c0c4cc;
  gap: 12px;
}

.main-empty h3 {
  font-size: 18px;
  color: #909399;
  font-weight: 500;
}

.main-empty p {
  font-size: 14px;
}

/* ============ 信息面板 ============ */

.info-panel {
  width: 280px;
  min-width: 280px;
  background: #fff;
  border-left: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  transition: width 0.3s, min-width 0.3s;
  position: relative;
}

.info-panel.collapsed {
  width: 32px;
  min-width: 32px;
}

.panel-toggle {
  position: absolute;
  top: 12px;
  left: -12px;
  width: 24px;
  height: 24px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  font-size: 12px;
  color: #909399;
  transition: color 0.2s;
}

.panel-toggle:hover {
  color: #409eff;
  border-color: #409eff;
}

.panel-content {
  padding: 16px;
  overflow-y: auto;
  flex: 1;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 14px;
}

.info-label {
  font-size: 12px;
  color: #909399;
}

.info-value {
  font-size: 13px;
  color: #303133;
}

.info-value.mono {
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
  font-size: 12px;
}

.url-text {
  word-break: break-all;
}

.capability-tags {
  display: flex;
  gap: 6px;
}

.info-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100px;
  color: #c0c4cc;
  font-size: 14px;
}
</style>
