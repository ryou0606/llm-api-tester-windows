<template>
  <div class="audio-page">
    <!-- STT 区域 -->
    <div class="section stt-section">
      <div class="section-header">
        <el-icon :size="20" color="#f56c6c"><Microphone /></el-icon>
        <h3>{{ $t('audio.sttTitle') }}</h3>
      </div>

      <div class="stt-content">
        <!-- API Key 输入 -->
        <div class="config-row">
          <el-input
            v-model="apiKey"
            :placeholder="$t('audio.apiKeyPlaceholder')"
            show-password
            size="small"
            style="max-width: 400px"
          />
        </div>

        <!-- 录音控制 -->
        <div class="record-area">
          <el-button
            :type="isRecording ? 'danger' : 'primary'"
            :icon="Microphone"
            circle
            size="large"
            class="record-btn"
            :class="{ recording: isRecording }"
            @click="toggleRecording"
          />
          <div class="record-status">
            <span v-if="!isRecording && !audioBlob">{{ $t('audio.clickToRecord') }}</span>
            <span v-else-if="isRecording" class="recording-text">
              {{ $t('audio.recording', { duration: recordDuration }) }}
            </span>
            <span v-else>{{ $t('audio.recordComplete', { duration: recordDuration }) }}</span>
          </div>
        </div>

        <!-- 录音回放 -->
        <div v-if="audioBlob" class="audio-playback">
          <audio controls :src="audioBlobUrl" ref="audioPlayerRef"></audio>
          <div class="audio-actions">
            <el-button size="small" @click="resetRecording">{{ $t('audio.reRecord') }}</el-button>
            <el-button type="primary" size="small" @click="handleSTT" :loading="sttLoading">
              {{ $t('audio.recognizeVoice') }}
            </el-button>
          </div>
        </div>

        <!-- STT 结果 -->
        <div v-if="sttResult" class="stt-result">
          <div class="result-label">{{ $t('audio.resultLabel') }}</div>
          <el-input
            v-model="sttResult"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 6 }"
            readonly
          />
          <div class="result-meta">
            <span>{{ $t('audio.audioDuration', { duration: sttDuration }) }}</span>
            <el-button size="small" @click="copyText(sttResult)">{{ $t('common.copy') }}</el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- TTS 区域 -->
    <div class="section tts-section">
      <div class="section-header">
        <el-icon :size="20" color="#409eff"><Headset /></el-icon>
        <h3>{{ $t('audio.ttsTitle') }}</h3>
      </div>

      <div class="tts-content">
        <!-- 配置行 -->
        <div class="tts-config">
          <div class="config-item">
            <label>{{ $t('audio.voice') }}</label>
            <el-select v-model="selectedVoice" style="width: 160px">
              <el-option
                v-for="v in voices"
                :key="v.id"
                :label="`${v.name} (${v.language}${v.gender})`"
                :value="v.id"
              />
            </el-select>
          </div>
          <div class="config-item">
            <label>{{ $t('audio.model') }}</label>
            <el-select v-model="selectedTTSModel" style="width: 200px">
              <el-option
                v-for="m in ttsModels"
                :key="m.id"
                :label="m.name"
                :value="m.id"
              >
                <div>
                  <span>{{ m.name }}</span>
                  <span style="color:#999;font-size:12px;margin-left:8px">{{ m.description }}</span>
                </div>
              </el-option>
            </el-select>
          </div>
        </div>

        <!-- 风格快捷按钮 -->
        <div class="style-presets">
          <label>{{ $t('audio.style') }}</label>
          <div class="preset-tags">
            <el-tag
              v-for="preset in stylePresets"
              :key="preset.id"
              :type="selectedStyle === preset.id ? '' : 'info'"
              :effect="selectedStyle === preset.id ? 'dark' : 'plain'"
              class="preset-tag"
              @click="toggleStyle(preset)"
            >
              {{ preset.label }}
            </el-tag>
            <el-tag
              :type="!selectedStyle ? '' : 'info'"
              :effect="!selectedStyle ? 'dark' : 'plain'"
              class="preset-tag"
              @click="selectedStyle = ''"
            >
              {{ $t('audio.default') }}
            </el-tag>
          </div>
        </div>

        <!-- 文本输入 -->
        <el-input
          v-model="ttsText"
          type="textarea"
          :autosize="{ minRows: 3, maxRows: 8 }"
          :placeholder="$t('audio.ttsPlaceholder')"
        />

        <!-- 生成按钮 -->
        <div class="tts-actions">
          <el-button
            type="primary"
            @click="handleTTS"
            :loading="ttsLoading"
            :disabled="!ttsText.trim()"
          >
            {{ $t('audio.generateVoice') }}
          </el-button>
        </div>

        <!-- TTS 结果播放 -->
        <div v-if="ttsAudioUrl" class="tts-result">
          <audio controls :src="ttsAudioUrl" ref="ttsPlayerRef"></audio>
          <div class="tts-result-actions">
            <el-button size="small" @click="downloadTTS">{{ $t('audio.downloadAudio') }}</el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Microphone, Headset } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { stt, tts, fetchVoices, fetchTTSModels, fetchStylePresets } from '@/api/audio'
import type { Voice, TTSModel, StylePreset } from '@/api/audio'

const { t } = useI18n()

// ============ 共享 ============

const apiKey = ref('')

// ============ STT 状态 ============

const isRecording = ref(false)
const recordDuration = ref(0)
const audioBlob = ref<Blob | null>(null)
const audioBlobUrl = ref('')
const sttResult = ref('')
const sttDuration = ref(0)
const sttLoading = ref(false)
const audioPlayerRef = ref<HTMLAudioElement>()

let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []
let recordTimer: ReturnType<typeof setInterval> | null = null

// ============ TTS 状态 ============

const voices = ref<Voice[]>([])
const ttsModels = ref<TTSModel[]>([])
const stylePresets = ref<StylePreset[]>([])
const selectedVoice = ref('冰糖')
const selectedTTSModel = ref('mimo-v2.5-tts')
const selectedStyle = ref('')
const ttsText = ref('')
const ttsAudioUrl = ref('')
const ttsLoading = ref(false)
const ttsPlayerRef = ref<HTMLAudioElement>()

// ============ STT 方法 ============

async function toggleRecording() {
  if (isRecording.value) {
    stopRecording()
  } else {
    await startRecording()
  }
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream)
    audioChunks = []

    mediaRecorder.ondataavailable = (e) => {
      audioChunks.push(e.data)
    }

    mediaRecorder.onstop = () => {
      const blob = new Blob(audioChunks, { type: 'audio/wav' })
      audioBlob.value = blob
      audioBlobUrl.value = URL.createObjectURL(blob)
      stream.getTracks().forEach(t => t.stop())
    }

    mediaRecorder.start()
    isRecording.value = true
    recordDuration.value = 0

    recordTimer = setInterval(() => {
      recordDuration.value++
    }, 1000)
  } catch (e: any) {
    ElMessage.error(t('audio.micAccessDenied', { error: e.message }))
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
  isRecording.value = false
  if (recordTimer) {
    clearInterval(recordTimer)
    recordTimer = null
  }
}

function resetRecording() {
  audioBlob.value = null
  audioBlobUrl.value = ''
  sttResult.value = ''
  recordDuration.value = 0
}

async function handleSTT() {
  if (!audioBlob.value) return
  if (!apiKey.value) {
    ElMessage.warning(t('audio.inputApiKeyFirst'))
    return
  }

  sttLoading.value = true
  try {
    // 将 blob 转为 base64
    const base64 = await blobToBase64(audioBlob.value)
    const result = await stt(base64, apiKey.value)
    sttResult.value = result.text
    sttDuration.value = result.duration
    ElMessage.success(t('audio.transcribeComplete'))
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || e.message || t('audio.transcribeFailed'))
  } finally {
    sttLoading.value = false
  }
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      resolve(result.split(',')[1])
    }
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}

// ============ TTS 方法 ============

function toggleStyle(preset: StylePreset) {
  selectedStyle.value = selectedStyle.value === preset.id ? '' : preset.id
}

async function handleTTS() {
  if (!ttsText.value.trim()) return
  if (!apiKey.value) {
    ElMessage.warning(t('audio.inputApiKeyFirst'))
    return
  }

  ttsLoading.value = true
  try {
    const stylePrompt = selectedStyle.value
      ? stylePresets.value.find(p => p.id === selectedStyle.value)?.prompt
      : undefined

    const blob = await tts(
      ttsText.value,
      apiKey.value,
      selectedVoice.value,
      selectedTTSModel.value,
      undefined,
      stylePrompt
    )

    // 释放旧的 URL
    if (ttsAudioUrl.value) {
      URL.revokeObjectURL(ttsAudioUrl.value)
    }
    ttsAudioUrl.value = URL.createObjectURL(blob)
    ElMessage.success(t('audio.voiceGenComplete'))
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || e.message || t('audio.synthFailed'))
  } finally {
    ttsLoading.value = false
  }
}

function downloadTTS() {
  if (!ttsAudioUrl.value) return
  const a = document.createElement('a')
  a.href = ttsAudioUrl.value
  a.download = 'tts_output.wav'
  a.click()
}

function copyText(text: string) {
  navigator.clipboard.writeText(text)
  ElMessage.success(t('common.copied'))
}

// ============ 生命周期 ============

onMounted(async () => {
  try {
    const [v, m, s] = await Promise.all([fetchVoices(), fetchTTSModels(), fetchStylePresets()])
    voices.value = v
    ttsModels.value = m
    stylePresets.value = s
  } catch (e) {
    console.error(t('audio.loadConfigFailed'), e)
  }
})
</script>

<style scoped>
.audio-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 900px;
  margin: 0 auto;
}

.section {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.section-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

/* ============ STT ============ */

.config-row {
  margin-bottom: 16px;
}

.record-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px;
}

.record-btn {
  width: 64px !important;
  height: 64px !important;
  font-size: 24px !important;
  transition: all 0.3s;
}

.record-btn.recording {
  animation: pulse 1.5s ease-in-out infinite;
  box-shadow: 0 0 0 8px rgba(245, 108, 108, 0.2);
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.record-status {
  font-size: 14px;
  color: #909399;
}

.recording-text {
  color: #f56c6c;
  font-weight: 500;
}

.audio-playback {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: #f9f9fa;
  border-radius: 8px;
}

.audio-playback audio {
  width: 100%;
  max-width: 400px;
}

.audio-actions {
  display: flex;
  gap: 8px;
}

.stt-result {
  margin-top: 16px;
  padding: 16px;
  background: #f0f9eb;
  border-radius: 8px;
  border: 1px solid #e1f3d8;
}

.result-label {
  font-size: 13px;
  font-weight: 600;
  color: #67c23a;
  margin-bottom: 8px;
}

.result-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

/* ============ TTS ============ */

.tts-config {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.config-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.config-item label {
  font-size: 13px;
  color: #606266;
  font-weight: 500;
  white-space: nowrap;
}

.style-presets {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.style-presets label {
  font-size: 13px;
  color: #606266;
  font-weight: 500;
  flex-shrink: 0;
}

.preset-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.preset-tag {
  cursor: pointer;
  transition: all 0.2s;
}

.preset-tag:hover {
  transform: translateY(-1px);
}

.tts-actions {
  margin-top: 12px;
}

.tts-result {
  margin-top: 16px;
  padding: 16px;
  background: #ecf5ff;
  border-radius: 8px;
  border: 1px solid #d9ecff;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.tts-result audio {
  width: 100%;
  max-width: 500px;
}

.tts-result-actions {
  display: flex;
  gap: 8px;
}
</style>
