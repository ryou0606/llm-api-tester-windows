<template>
  <div class="arena-page">
    <!-- 左侧面板：对抗会话列表 -->
    <div class="left-panel">
      <div class="panel-section">
        <div class="section-header">
          <span class="section-title">{{ $t('arena.sessions') }}</span>
          <el-button type="primary" size="small" :icon="Plus" @click="showCreateDialog = true">
            {{ $t('arena.newSession') }}
          </el-button>
        </div>
      </div>

      <div class="panel-section history-section">
        <div v-if="arenaStore.arenas.length === 0" class="empty-hint">
          <el-empty :description="$t('arena.noSessions')" :image-size="48" />
        </div>
        <div v-else class="arena-list">
          <div
            v-for="arena in arenaStore.arenas"
            :key="arena.id"
            class="arena-item"
            :class="{ active: arenaStore.currentArena?.id === arena.id }"
            @click="handleEnterArena(arena.id)"
          >
            <div class="arena-title">{{ arena.title || $t('arena.defaultTitle') }}</div>
            <div class="arena-meta">
              {{ $t('arena.modelsCount', { count: (arena.model_config_ids || []).length }) }} · {{ formatTime(arena.created_at) }}
            </div>
            <el-button
              class="arena-delete"
              :icon="Delete"
              circle
              size="small"
              type="danger"
              plain
              @click.stop="handleDeleteArena(arena.id)"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧主区域 -->
    <div class="main-area">
      <!-- 无对抗时的提示 -->
      <div v-if="!arenaStore.currentArena" class="main-empty">
        <el-icon :size="64" color="#e6a23c"><Trophy /></el-icon>
        <h3>{{ $t('arena.multiModelArena') }}</h3>
        <p>{{ $t('arena.arenaDesc') }}</p>
        <el-button type="primary" @click="showCreateDialog = true" :icon="Plus">
          {{ $t('arena.createArena') }}
        </el-button>
      </div>

      <!-- 对抗界面 -->
      <template v-else>
        <!-- 顶部模型标签栏 -->
        <div class="model-tabs">
          <div
            v-for="model in arenaStore.arenaModels"
            :key="model.id"
            class="model-tab"
            :class="{
              active: arenaStore.activeModelId === model.id,
              streaming: arenaStore.streamingModelIds.has(model.id),
            }"
            @click="arenaStore.switchModel(model.id)"
          >
            <span class="tab-name">{{ model.name }}</span>
            <span v-if="arenaStore.streamingModelIds.has(model.id)" class="tab-loading">
              <el-icon class="is-loading"><Loading /></el-icon>
            </span>
            <span v-else-if="getModelResponse(model.id)" class="tab-done">✓</span>
          </div>
        </div>

        <!-- 对话区 -->
        <div class="chat-area">
          <ChatBox
            :messages="arenaStore.displayMessages"
            :loading="arenaStore.loading"
            :streaming="arenaStore.streaming"
            @send="handleSend"
          />
        </div>
      </template>
    </div>

    <!-- 创建对抗弹窗 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="$t('arena.createMultiModelArena')"
      width="560px"
      :close-on-click-modal="false"
    >
      <div class="create-form">
        <div class="form-label">{{ $t('arena.selectModelsHint') }}</div>
        <el-checkbox-group v-model="selectedModelIds" class="model-checkbox-group">
          <el-checkbox
            v-for="model in modelStore.models"
            :key="model.id"
            :value="model.id"
            :label="model.id"
            class="model-checkbox"
          >
            <div class="checkbox-model-info">
              <span class="checkbox-model-name">{{ model.name }}</span>
              <el-tag
                :type="model.status === 'available' ? 'success' : model.status === 'unavailable' ? 'danger' : 'info'"
                size="small"
                effect="light"
              >
                {{ model.model_id }}
              </el-tag>
            </div>
          </el-checkbox>
        </el-checkbox-group>
        <div v-if="modelStore.models.length === 0" class="no-models">
          <el-empty :description="$t('arena.pleaseAddModels')" :image-size="48" />
        </div>
      </div>

      <template #footer>
        <el-button @click="showCreateDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button
          type="primary"
          @click="handleCreateArena"
          :disabled="selectedModelIds.length < 2"
          :loading="creating"
        >
          {{ $t('arena.createWithModels', { count: selectedModelIds.length }) }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Delete, Loading } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ChatBox from '@/components/ChatBox.vue'
import { useArenaStore } from '@/stores/arena'
import { useModelStore } from '@/stores/model'

const arenaStore = useArenaStore()
const modelStore = useModelStore()
const { t } = useI18n()

const showCreateDialog = ref(false)
const selectedModelIds = ref<number[]>([])
const creating = ref(false)

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

function getModelResponse(modelId: number): boolean {
  const msgs = arenaStore.modelMessages[modelId]
  return !!(msgs && msgs.length > 0 && msgs[msgs.length - 1].content)
}

async function handleCreateArena() {
  if (selectedModelIds.value.length < 2) {
    ElMessage.warning(t('arena.selectAtLeast2'))
    return
  }
  creating.value = true
  try {
    await arenaStore.createNewArena(selectedModelIds.value)
    ElMessage.success(t('arena.arenaCreated'))
    showCreateDialog.value = false
    selectedModelIds.value = []
  } catch (e: any) {
    ElMessage.error(e.message || t('common.createFailed'))
  } finally {
    creating.value = false
  }
}

async function handleEnterArena(id: number) {
  await arenaStore.enterArena(id)
}

async function handleDeleteArena(id: number) {
  try {
    await ElMessageBox.confirm(t('arena.deleteConfirm'), t('arena.confirmDelete'), {
      type: 'warning',
      confirmButtonText: t('common.delete'),
      cancelButtonText: t('common.cancel'),
    })
    await arenaStore.removeArena(id)
    ElMessage.success(t('common.deleted'))
  } catch {
    // 取消
  }
}

async function handleSend(content: string) {
  try {
    await arenaStore.send(content)
  } catch (e: any) {
    ElMessage.error(e.message || t('common.sendFailed'))
  }
}

// ============ 生命周期 ============

onMounted(async () => {
  await Promise.all([modelStore.loadModels(), arenaStore.loadArenas()])
})
</script>

<style scoped>
.arena-page {
  display: flex;
  height: calc(100vh - 48px);
  margin: -24px;
}

/* ============ 左侧面板 ============ */

.left-panel {
  width: 260px;
  min-width: 260px;
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

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.history-section {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 0;
}

.empty-hint {
  padding: 20px;
}

.arena-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.arena-item {
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
  position: relative;
  margin-bottom: 4px;
}

.arena-item:hover {
  background: #f5f7fa;
}

.arena-item.active {
  background: #fdf6ec;
  border-left: 3px solid #e6a23c;
}

.arena-title {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-right: 24px;
}

.arena-meta {
  font-size: 11px;
  color: #c0c4cc;
  margin-top: 4px;
}

.arena-delete {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0;
  transition: opacity 0.2s;
}

.arena-item:hover .arena-delete {
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
  gap: 16px;
}

.main-empty h3 {
  font-size: 20px;
  color: #303133;
  font-weight: 600;
}

.main-empty p {
  font-size: 14px;
  color: #909399;
}

/* ============ 模型标签栏 ============ */

.model-tabs {
  display: flex;
  gap: 0;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  padding: 0 16px;
  overflow-x: auto;
  flex-shrink: 0;
}

.model-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 20px;
  font-size: 13px;
  font-weight: 500;
  color: #606266;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
  white-space: nowrap;
  position: relative;
}

.model-tab:hover {
  color: #e6a23c;
  background: #fdf6ec;
}

.model-tab.active {
  color: #e6a23c;
  border-bottom-color: #e6a23c;
  font-weight: 600;
}

.model-tab.streaming .tab-name {
  color: #409eff;
}

.tab-loading {
  color: #409eff;
  font-size: 12px;
}

.tab-done {
  color: #67c23a;
  font-size: 12px;
  font-weight: 700;
}

/* ============ 对话区 ============ */

.chat-area {
  flex: 1;
  overflow: hidden;
  padding: 16px;
}

/* ============ 创建弹窗 ============ */

.create-form {
  max-height: 400px;
  overflow-y: auto;
}

.form-label {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 16px;
}

.model-checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.model-checkbox {
  margin-right: 0;
  padding: 10px 12px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  transition: border-color 0.2s;
}

.model-checkbox:hover {
  border-color: #e6a23c;
}

.checkbox-model-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.checkbox-model-name {
  font-size: 14px;
  font-weight: 500;
}

.no-models {
  padding: 20px;
}
</style>
