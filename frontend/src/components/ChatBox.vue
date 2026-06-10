<template>
  <div class="chat-box">
    <!-- 消息列表 -->
    <div class="message-list" ref="messageListRef">
      <!-- 空状态 -->
      <div v-if="messages.length === 0" class="empty-chat">
        <el-icon :size="48" color="#c0c4cc"><ChatDotRound /></el-icon>
        <p>发送消息开始对话</p>
      </div>

      <!-- 消息项 -->
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="message-item"
        :class="[`message-${msg.role}`, { 'message-streaming': msg.isStreaming }]"
      >
        <!-- 头像 -->
        <div class="message-avatar">
          <el-avatar v-if="msg.role === 'user'" :size="36" style="background: #409eff">
            <el-icon><User /></el-icon>
          </el-avatar>
          <el-avatar v-else :size="36" style="background: #67c23a">
            <el-icon><Monitor /></el-icon>
          </el-avatar>
        </div>

        <!-- 消息内容 -->
        <div class="message-body">
          <div class="message-role">{{ msg.role === 'user' ? '你' : 'AI' }}</div>
          <!-- 图片预览 -->
        <div v-if="msg.imageData" class="message-image">
          <img :src="`data:image/png;base64,${msg.imageData}`" alt="uploaded image" />
        </div>
        <div class="message-content" v-html="renderMarkdown(msg.content)"></div>
          <!-- 流式光标 -->
          <span v-if="msg.isStreaming" class="streaming-cursor">▊</span>
          <!-- 消息元数据 -->
          <div v-if="msg.role === 'assistant' && !msg.isStreaming && msg.latencyMs" class="message-meta">
            <span class="meta-item">
              <el-icon><Timer /></el-icon>
              {{ msg.latencyMs }}ms
            </span>
            <span v-if="msg.tokenUsage" class="meta-item">
              <el-icon><Coin /></el-icon>
              {{ msg.tokenUsage.total_tokens }} tokens
            </span>
            <span v-if="msg.tokenUsage" class="meta-item detail-link" @click="toggleDetail(msg.id)">
              <el-icon><View /></el-icon>
              详情
            </span>
          </div>
          <!-- 详情展开 -->
          <div v-if="expandedIds.has(msg.id)" class="message-detail">
            <div v-if="msg.tokenUsage" class="detail-row">
              <span>Prompt: {{ msg.tokenUsage.prompt_tokens }}</span>
              <span>Completion: {{ msg.tokenUsage.completion_tokens }}</span>
              <span>Total: {{ msg.tokenUsage.total_tokens }}</span>
            </div>
            <div v-if="msg.rawResponse" class="detail-json">
              <pre>{{ JSON.stringify(msg.rawResponse, null, 2) }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="input-area">
      <div class="input-toolbar">
        <el-tooltip :content="enableImageUpload ? '上传图片' : '上传图片（需在视觉页面使用）'" placement="top">
          <el-button :icon="Picture" circle size="small" :disabled="!enableImageUpload" @click="triggerImageUpload" />
        </el-tooltip>

        <!-- TTS 开关 + 设置 -->
        <el-popover placement="top" :width="260" trigger="click">
          <template #reference>
            <el-button
              circle size="small"
              :type="ttsEnabled ? 'success' : 'default'"
            >
              🔊
            </el-button>
          </template>
          <div class="tts-popover">
            <div class="tts-popover-title">🔊 语音播报设置</div>
            <div class="tts-popover-row">
              <span class="tts-label">播报模型</span>
              <el-select v-model="ttsModelId" size="small" placeholder="选择 TTS 模型" style="width: 100%">
                <el-option
                  v-for="m in ttsModelOptions"
                  :key="m.id"
                  :label="m.name"
                  :value="m.id"
                />
              </el-select>
            </div>
            <div class="tts-popover-row">
              <span class="tts-label">音色</span>
              <el-select v-model="ttsVoice" size="small" style="width: 100%">
                <el-option v-for="v in voiceOptions" :key="v.id" :label="v.name + ' (' + v.gender + ')'" :value="v.id" />
              </el-select>
            </div>
            <div class="tts-popover-row">
              <el-button
                :type="ttsEnabled ? 'danger' : 'primary'"
                size="small"
                style="width: 100%"
                @click="toggleTts"
              >
                {{ ttsEnabled ? '⏸ 关闭播报' : '▶ 开启播报' }}
              </el-button>
            </div>
          </div>
        </el-popover>

        <!-- TTS 播放状态 -->
        <el-tag v-if="ttsPlaying" closable @close="stopTts" type="warning" size="small" effect="dark">
          🔊 播放中...
        </el-tag>
        <el-tag v-else-if="ttsLoading" type="info" size="small" effect="plain">
          ⏳ 生成语音...
        </el-tag>

        <span v-if="imagePreview" class="image-preview-tag">
          <el-tag closable @close="clearImage" type="info" size="small">
            📷 已选择图片
          </el-tag>
        </span>
        <input ref="fileInputRef" type="file" accept="image/*" style="display:none" @change="handleFileSelect" />
      </div>
      <div class="input-row">
        <el-input
          ref="inputRef"
          v-model="inputText"
          type="textarea"
          :autosize="{ minRows: 1, maxRows: 6 }"
          placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
          :disabled="disabled"
          @keydown="handleKeydown"
        />
        <el-button
          type="primary"
          :icon="Promotion"
          :loading="loading"
          :disabled="!canSend"
          @click="handleSend"
        >
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, reactive, onMounted, onUnmounted } from 'vue'
import { Picture, Promotion, Timer, Coin, View, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { DisplayMessage } from '@/stores/chat'
import { useModelStore } from '@/stores/model'
import { fetchVoices, ttsByModel } from '@/api/audio'
import type { Voice } from '@/api/audio'

// ============ Props & Emits ============

const props = defineProps<{
  messages: DisplayMessage[]
  loading?: boolean
  streaming?: boolean
  disabled?: boolean
  enableImageUpload?: boolean
}>()

const emit = defineEmits<{
  send: [content: string, imageData?: string]
}>()

// ============ 状态 ============

const inputText = ref('')
const inputRef = ref()
const messageListRef = ref<HTMLElement>()
const expandedIds = reactive(new Set<string | number>())
const fileInputRef = ref<HTMLInputElement>()
const imagePreview = ref<string | null>(null)  // Base64 data
const imageFileName = ref<string>('')

// ============ TTS 状态 ============

const modelStore = useModelStore()
const ttsEnabled = ref(false)
const ttsLoading = ref(false)
const ttsPlaying = ref(false)
const ttsModelId = ref<number | null>(null)
const ttsVoice = ref('冰糖')
const voiceOptions = ref<Voice[]>([])
let currentAudio: HTMLAudioElement | null = null

// TTS 可用模型列表（从 modelStore 中筛选支持 TTS 的，或全部列出供用户选）
const ttsModelOptions = computed(() => {
  return modelStore.models.map(m => ({ id: m.id, name: m.name }))
})

// 从 localStorage 恢复 TTS 设置
function loadTtsSettings() {
  try {
    const saved = localStorage.getItem('llm_tester_tts')
    if (saved) {
      const cfg = JSON.parse(saved)
      ttsEnabled.value = cfg.enabled ?? false
      ttsModelId.value = cfg.modelId ?? null
      ttsVoice.value = cfg.voice ?? '冰糖'
    }
  } catch { /* ignore */ }
}

function saveTtsSettings() {
  localStorage.setItem('llm_tester_tts', JSON.stringify({
    enabled: ttsEnabled.value,
    modelId: ttsModelId.value,
    voice: ttsVoice.value,
  }))
}

function toggleTts() {
  if (!ttsModelId.value) {
    ElMessage.warning('请先选择一个 TTS 播报模型')
    return
  }
  ttsEnabled.value = !ttsEnabled.value
  saveTtsSettings()
  ElMessage.success(ttsEnabled.value ? '语音播报已开启' : '语音播报已关闭')
}

function stopTts() {
  if (currentAudio) {
    currentAudio.pause()
    currentAudio.src = ''
    currentAudio = null
  }
  ttsPlaying.value = false
}

async function speakText(text: string) {
  if (!ttsEnabled.value || !ttsModelId.value || !text.trim()) return

  // 截取合理长度（TTS 有 token 限制）
  const cleanText = text.replace(/```[\s\S]*?```/g, '代码块已省略')
    .replace(/`[^`]+`/g, '')
    .replace(/[#*_~\[\]()]/g, '')
    .trim()
  if (!cleanText || cleanText.length < 2) return

  // 限制 TTS 文本长度
  const ttsText = cleanText.length > 2000 ? cleanText.slice(0, 2000) + '...' : cleanText

  ttsLoading.value = true
  try {
    const blob = await ttsByModel(ttsText, ttsModelId.value, ttsVoice.value)
    const url = URL.createObjectURL(blob)

    stopTts()  // 停止之前的播放
    currentAudio = new Audio(url)
    ttsPlaying.value = true

    currentAudio.onended = () => {
      ttsPlaying.value = false
      URL.revokeObjectURL(url)
      currentAudio = null
    }
    currentAudio.onerror = () => {
      ttsPlaying.value = false
      URL.revokeObjectURL(url)
      currentAudio = null
    }

    await currentAudio.play()
  } catch (e: any) {
    console.error('TTS 失败:', e)
    ElMessage.error('语音合成失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    ttsLoading.value = false
  }
}

// ============ 计算属性 ============

const canSend = computed(() => {
  return (inputText.value.trim().length > 0 || imagePreview.value) && !props.loading && !props.streaming && !props.disabled
})

// ============ 方法 ============

/** 处理键盘事件 */
function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

/** 发送消息 */
function handleSend() {
  const content = inputText.value.trim()
  if ((!content && !imagePreview.value) || props.loading || props.streaming) return
  emit('send', content || '(图片)', imagePreview.value || undefined)
  inputText.value = ''
  clearImage()
}

/** 触发图片选择 */
function triggerImageUpload() {
  fileInputRef.value?.click()
}

/** 处理文件选择 */
function handleFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  readImageFile(file)
  input.value = ''  // 重置 input
}

/** 读取图片文件为 Base64 */
function readImageFile(file: File) {
  const reader = new FileReader()
  reader.onload = () => {
    const result = reader.result as string
    // 去掉 data:image/xxx;base64, 前缀
    imagePreview.value = result.split(',')[1]
    imageFileName.value = file.name
  }
  reader.readAsDataURL(file)
}

/** 清除已选图片 */
function clearImage() {
  imagePreview.value = null
  imageFileName.value = ''
}

/** 切换详情展开 */
function toggleDetail(id: string | number) {
  if (expandedIds.has(id)) {
    expandedIds.delete(id)
  } else {
    expandedIds.add(id)
  }
}

/**
 * 简单的 Markdown 渲染
 * 支持：代码块、行内代码、粗体、斜体、标题、列表、链接
 */
function renderMarkdown(text: string): string {
  if (!text) return ''

  let html = text

  // 转义 HTML
  html = html
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // 代码块 (```)
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_match, lang, code) => {
    return `<pre class="code-block"><code class="lang-${lang}">${code.trim()}</code></pre>`
  })

  // 行内代码 (`)
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')

  // 标题 (### / ## / #)
  html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>')
  html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>')
  html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>')

  // 粗体 (**)
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')

  // 斜体 (*)
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')

  // 链接
  html = html.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener">$1</a>'
  )

  // 无序列表
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')

  // 有序列表
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>')

  // 换行
  html = html.replace(/\n/g, '<br>')

  return html
}

/** 自动滚动到底部 */
function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

// ============ 监听 ============

// 消息变化时自动滚动
watch(
  () => props.messages.length,
  () => scrollToBottom()
)

// 流式接收时持续滚动
watch(
  () => props.messages.map(m => m.content).join(''),
  () => scrollToBottom()
)

// TTS: 监听最后一条助手消息的 isStreaming 从 true 变 false → 自动播报
watch(
  () => {
    const msgs = props.messages
    if (msgs.length === 0) return null
    const last = msgs[msgs.length - 1]
    if (last.role === 'assistant') return { streaming: last.isStreaming, content: last.content }
    return null
  },
  (val, oldVal) => {
    if (!val || !ttsEnabled.value) return
    // 从 streaming → not streaming，且有内容
    if (oldVal?.streaming && !val.streaming && val.content) {
      speakText(val.content)
    }
  }
)

// 保存 TTS 设置
watch([ttsEnabled, ttsModelId, ttsVoice], () => saveTtsSettings())

// 生命周期
onMounted(async () => {
  loadTtsSettings()
  // 加载音色列表
  try {
    voiceOptions.value = await fetchVoices()
  } catch { /* ignore */ }
})

onUnmounted(() => {
  stopTts()
})

// 暴露方法给父组件
defineExpose({ scrollToBottom, focus: () => inputRef.value?.focus() })
</script>

<style scoped>
.chat-box {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
}

/* ============ 消息列表 ============ */

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty-chat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #c0c4cc;
  gap: 12px;
}

.empty-chat p {
  font-size: 14px;
}

/* ============ 消息项 ============ */

.message-item {
  display: flex;
  gap: 12px;
  max-width: 85%;
}

.message-user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-assistant {
  align-self: flex-start;
}

.message-avatar {
  flex-shrink: 0;
}

.message-body {
  min-width: 0;
}

.message-role {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.message-user .message-role {
  text-align: right;
}

.message-content {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.message-user .message-content {
  background: #409eff;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message-image {
  margin-bottom: 6px;
}

.message-image img {
  max-width: 300px;
  max-height: 200px;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s;
}

.message-image img:hover {
  transform: scale(1.05);
}

.message-assistant .message-content {
  background: #f4f4f5;
  color: #303133;
  border-bottom-left-radius: 4px;
}

/* 流式光标 */
.streaming-cursor {
  display: inline-block;
  color: #409eff;
  animation: blink 0.8s step-end infinite;
  margin-left: 2px;
}

@keyframes blink {
  50% { opacity: 0; }
}

/* ============ 消息元数据 ============ */

.message-meta {
  display: flex;
  gap: 12px;
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 3px;
}

.detail-link {
  cursor: pointer;
  color: #409eff;
}

.detail-link:hover {
  text-decoration: underline;
}

.message-detail {
  margin-top: 8px;
  padding: 10px;
  background: #f9f9fa;
  border-radius: 8px;
  font-size: 12px;
}

.detail-row {
  display: flex;
  gap: 16px;
  color: #606266;
  margin-bottom: 8px;
}

.detail-json pre {
  max-height: 200px;
  overflow: auto;
  font-size: 11px;
  color: #606266;
  white-space: pre-wrap;
  word-break: break-all;
}

/* ============ Markdown 渲染样式 ============ */

.message-content :deep(h2) {
  font-size: 18px;
  margin: 8px 0 4px;
}

.message-content :deep(h3) {
  font-size: 16px;
  margin: 6px 0 4px;
}

.message-content :deep(h4) {
  font-size: 14px;
  margin: 4px 0 2px;
}

.message-content :deep(.code-block) {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
  font-size: 13px;
}

.message-content :deep(.inline-code) {
  background: rgba(0, 0, 0, 0.06);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
}

.message-user .message-content :deep(.inline-code) {
  background: rgba(255, 255, 255, 0.2);
}

.message-content :deep(ul) {
  padding-left: 20px;
  margin: 4px 0;
}

.message-content :deep(li) {
  margin: 2px 0;
}

.message-content :deep(a) {
  color: #409eff;
  text-decoration: none;
}

.message-content :deep(a:hover) {
  text-decoration: underline;
}

/* ============ 输入区域 ============ */

.input-area {
  border-top: 1px solid #ebeef5;
  padding: 12px 16px;
  background: #fafafa;
}

.input-toolbar {
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.image-preview-tag {
  display: inline-flex;
  align-items: center;
}

.input-row {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.input-row .el-textarea {
  flex: 1;
}

.input-row .el-button {
  height: 40px;
  flex-shrink: 0;
}

/* ============ TTS 设置 Popover ============ */

.tts-popover {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tts-popover-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  text-align: center;
}

.tts-popover-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tts-label {
  font-size: 12px;
  color: #909399;
}
</style>
