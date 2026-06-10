<template>
  <div class="relay-page">
    <!-- 顶部状态卡片 -->
    <div class="status-card">
      <div class="status-info">
        <el-icon :size="32" color="#409eff"><Connection /></el-icon>
        <div class="status-text">
          <h3>{{ $t('relay.stationTitle') }}</h3>
          <p>{{ $t('relay.stationDesc') }}</p>
        </div>
      </div>
      <div class="status-endpoint">
        <el-tag type="success" effect="dark" size="large">
          {{ baseUrl }}/v1
        </el-tag>
      </div>
    </div>

    <!-- 接口说明 -->
    <div class="section">
      <h4>{{ $t('relay.availableApis') }}</h4>
      <div class="api-table">
        <div class="api-row api-header">
          <span class="api-method">{{ $t('relay.method') }}</span>
          <span class="api-path">{{ $t('relay.path') }}</span>
          <span class="api-desc">{{ $t('relay.desc') }}</span>
        </div>
        <div class="api-row">
          <el-tag size="small" type="success">GET</el-tag>
          <code>/v1/models</code>
          <span>{{ $t('relay.listModels') }}</span>
        </div>
        <div class="api-row">
          <el-tag size="small" type="warning">POST</el-tag>
          <code>/v1/chat/completions</code>
          <span>{{ $t('relay.chatCompletion') }}</span>
        </div>
      </div>
    </div>

    <!-- 已暴露模型列表 -->
    <div class="section">
      <div class="section-header">
        <h4>{{ $t('relay.availableModels', { count: relayModels.length }) }}</h4>
        <el-button size="small" :icon="Refresh" @click="loadModels" :loading="loading">
          {{ $t('common.refresh') }}
        </el-button>
      </div>

      <div v-if="loading && relayModels.length === 0" v-loading="true" style="height: 100px"></div>

      <el-empty v-else-if="relayModels.length === 0" :description="$t('relay.noModels')" />

      <div v-else class="model-list">
        <div v-for="model in relayModels" :key="model.id" class="model-item">
          <div class="model-info">
            <span class="model-id">{{ model.id }}</span>
            <span class="model-name">{{ model.name }}</span>
          </div>
          <el-tag size="small" type="info">{{ model.owned_by }}</el-tag>
        </div>
      </div>
    </div>

    <!-- 使用示例 -->
    <div class="section">
      <h4>{{ $t('relay.usageExample') }}</h4>
      <div class="code-examples">
        <div class="code-block">
          <div class="code-label">cURL</div>
          <pre><code>curl {{ baseUrl }}/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "{{ relayModels[0]?.id || 'model-id' }}",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'</code></pre>
        </div>
        <div class="code-block">
          <div class="code-label">{{ $t('relay.openclawConfig') }}</div>
          <pre><code>"baseUrl": "{{ baseUrl }}/v1"</code></pre>
        </div>
        <div class="code-block">
          <div class="code-label">Python</div>
          <pre><code>from openai import OpenAI

client = OpenAI(
    base_url="{{ baseUrl }}/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="{{ relayModels[0]?.id || 'model-id' }}",
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.choices[0].message.content)</code></pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Refresh, Connection } from '@element-plus/icons-vue'
import axios from 'axios'

interface RelayModel {
  id: string
  object: string
  owned_by: string
  name: string
  relay_config_id: number
}

const relayModels = ref<RelayModel[]>([])
const loading = ref(false)

const { t } = useI18n()

const baseUrl = computed(() => {
  return window.location.origin
})

async function loadModels() {
  loading.value = true
  try {
    const { data } = await axios.get('/v1/models')
    relayModels.value = data.data || []
  } catch (e) {
    console.error(t('relay.loadModelsFailed'), e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadModels()
})
</script>

<style scoped>
.relay-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 900px;
}

.status-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.status-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-text h3 {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 4px 0;
}

.status-text p {
  font-size: 13px;
  color: #909399;
  margin: 0;
}

.section {
  background: #fff;
  padding: 20px 24px;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.section h4 {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 16px 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h4 {
  margin: 0;
}

/* API 表格 */
.api-table {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.api-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: #f9f9fa;
  border-radius: 6px;
}

.api-row.api-header {
  background: none;
  font-size: 12px;
  font-weight: 600;
  color: #909399;
  padding: 0 12px;
}

.api-row code {
  font-size: 13px;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
  color: #303133;
  min-width: 220px;
}

.api-row span:last-child {
  font-size: 13px;
  color: #606266;
}

/* 模型列表 */
.model-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.model-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: #f9f9fa;
  border-radius: 8px;
}

.model-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.model-id {
  font-size: 13px;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
  color: #303133;
  font-weight: 500;
}

.model-name {
  font-size: 13px;
  color: #909399;
}

/* 代码示例 */
.code-examples {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.code-block {
  background: #1e1e1e;
  border-radius: 8px;
  overflow: hidden;
}

.code-label {
  background: #2d2d2d;
  padding: 6px 14px;
  font-size: 12px;
  color: #909399;
  border-bottom: 1px solid #333;
}

.code-block pre {
  padding: 14px;
  margin: 0;
  overflow-x: auto;
}

.code-block code {
  font-size: 12px;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
  color: #d4d4d4;
  line-height: 1.6;
}
</style>
