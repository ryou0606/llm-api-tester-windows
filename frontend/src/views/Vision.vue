<template>
  <div class="vision-page">
    <!-- 左侧面板 -->
    <div class="left-panel">
      <!-- 模型选择（仅视觉模型） -->
      <div class="panel-section">
        <div class="section-title">{{ $t('vision.selectModel') }}</div>
        <el-select
          v-model="selectedModelId"
          :placeholder="$t('vision.selectModelPlaceholder')"
          style="width: 100%"
          @change="handleModelChange"
        >
          <el-option
            v-for="model in visionModels"
            :key="model.id"
            :label="model.name"
            :value="model.id"
          >
            <div class="model-option">
              <span class="option-name">{{ model.name }}</span>
              <el-tag size="small" type="success" effect="light">👁</el-tag>
            </div>
          </el-option>
        </el-select>
        <div v-if="visionModels.length === 0" class="no-models-hint">
          <el-text type="info" size="small">
            {{ $t('vision.noVisionModels') }}
          </el-text>
        </div>
      </div>

      <!-- 新建对话 -->
      <div class="panel-section">
        <el-button
          type="primary"
          style="width: 100%"
          :icon="Plus"
          :disabled="!selectedModelId"
          @click="handleCreateConversation"
        >
          {{ $t('vision.newConversation') }}
        </el-button>
      </div>

      <!-- 对话历史 -->
      <div class="panel-section history-section">
        <div class="section-title">{{ $t('vision.conversationHistory') }}</div>
        <div v-if="chatStore.loading && chatStore.conversations.length === 0" class="history-loading">
          <el-icon class="is-loading"><Loading /></el-icon>
        </div>
        <el-empty v-else-if="chatStore.conversations.length === 0" :description="$t('vision.noConversations')" :image-size="60" />
        <div v-else class="history-list">
          <div
            v-for="conv in chatStore.conversations"
            :key="conv.id"
            class="history-item"
            :class="{ active: chatStore.currentConversation?.id === conv.id }"
            @click="handleSelectConversation(conv.id)"
          >
            <div class="history-title">{{ conv.title || $t('vision.newConv') }}</div>
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
      <div v-if="!chatStore.currentConversation" class="main-empty">
        <el-icon :size="64" color="#67c23a"><Picture /></el-icon>
        <h3>{{ $t('vision.imageVisionTest') }}</h3>
        <p>{{ $t('vision.imageVisionDesc') }}</p>
      </div>

      <template v-else>
        <ChatBox
          :messages="chatStore.messages"
          :loading="chatStore.loading"
          :streaming="chatStore.streaming"
          :enable-image-upload="true"
          @send="handleSend"
        />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Delete, Loading } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ChatBox from '@/components/ChatBox.vue'
import { useModelStore } from '@/stores/model'
import { useChatStore } from '@/stores/chat'

const modelStore = useModelStore()
const chatStore = useChatStore()
const { t } = useI18n()

const selectedModelId = ref<number | null>(null)

// ============ 计算属性 ============

const visionModels = computed(() => {
  return modelStore.models.filter(m => m.supports_vision && m.is_active)
})

// ============ 方法 ============

function formatTime(isoStr: string): string {
  try {
    const date = new Date(isoStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMin = Math.floor(diffMs / 60000)
    if (diffMin < 1) return t('common.justNow')
    if (diffMin < 60) return t('common.minutesAgo', { n: diffMin })
    const diffHour = Math.floor(diffMin / 60)
    if (diffHour < 24) return t('common.hoursAgo', { n: diffHour })
    const month = (date.getMonth() + 1).toString().padStart(2, '0')
    const day = date.getDate().toString().padStart(2, '0')
    return `${month}-${day}`
  } catch {
    return isoStr
  }
}

function handleModelChange() {
  chatStore.clearState()
  if (selectedModelId.value) {
    chatStore.loadConversations()
  }
}

async function handleCreateConversation() {
  if (!selectedModelId.value) return
  try {
    await chatStore.createNewConversation(selectedModelId.value)
    ElMessage.success(t('vision.conversationCreated'))
  } catch {
    ElMessage.error(t('vision.createConvFailed'))
  }
}

async function handleSelectConversation(id: number) {
  await chatStore.switchConversation(id)
}

async function handleDeleteConversation(id: number) {
  try {
    await ElMessageBox.confirm(t('vision.deleteConvConfirm'), t('vision.confirmDelete'), {
      type: 'warning',
      confirmButtonText: t('common.delete'),
      cancelButtonText: t('common.cancel'),
    })
    await chatStore.removeConversation(id)
    ElMessage.success(t('common.deleted'))
  } catch {
    // 取消
  }
}

async function handleSend(content: string, imageData?: string) {
  if (!selectedModelId.value || !chatStore.currentConversation) return
  try {
    await chatStore.sendStream(selectedModelId.value, content, imageData)
  } catch (e: any) {
    ElMessage.error(e.message || t('common.sendFailed'))
  }
}

// ============ 生命周期 ============

onMounted(async () => {
  await modelStore.loadModels()
  await modelStore.loadApiTypes()
  await chatStore.loadConversations()
})
</script>

<style scoped>
.vision-page {
  display: flex;
  height: calc(100vh - 48px);
  margin: -24px;
}

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

.no-models-hint {
  margin-top: 8px;
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

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
  min-width: 0;
  padding: 16px;
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
</style>
