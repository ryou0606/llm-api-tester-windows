/**
 * 语音 API 封装（STT / TTS）
 */

import axios from 'axios'

const api = axios.create({
  baseURL: '/api/audio',
  timeout: 60000,
})

// ============ 类型定义 ============

/** 音色信息 */
export interface Voice {
  id: string
  name: string
  language: string
  gender: string
}

/** TTS 模型 */
export interface TTSModel {
  id: string
  name: string
  description: string
}

/** 风格预设 */
export interface StylePreset {
  id: string
  label: string
  prompt: string
}

/** STT 结果 */
export interface STTResult {
  text: string
  duration: number
}

// ============ API 函数 ============

/** 语音识别 */
export async function stt(
  audioData: string,
  apiKey: string,
  modelId?: string,
  baseUrl?: string,
  language?: string
): Promise<STTResult> {
  const { data } = await api.post('/stt', {
    audio_data: audioData,
    api_key: apiKey,
    model_id: modelId || 'mimo-v2.5-asr',
    base_url: baseUrl || 'https://api.xiaomimimo.com/v1',
    language: language || 'auto',
  })
  return data
}

/** 语音合成（返回 Blob URL） */
export async function tts(
  text: string,
  apiKey: string,
  voice?: string,
  modelId?: string,
  baseUrl?: string,
  stylePrompt?: string
): Promise<Blob> {
  const response = await api.post('/tts', {
    text,
    api_key: apiKey,
    voice: voice || '冰糖',
    model_id: modelId || 'mimo-v2.5-tts',
    base_url: baseUrl || 'https://api.xiaomimimo.com/v1',
    style_prompt: stylePrompt || null,
  }, {
    responseType: 'blob',
  })
  return response.data
}

/** 通过模型配置 ID 语音合成（无需传 API Key） */
export async function ttsByModel(
  text: string,
  modelConfigId: number,
  voice?: string,
  stylePrompt?: string
): Promise<Blob> {
  const response = await api.post('/tts-by-model', {
    text,
    model_config_id: modelConfigId,
    voice: voice || '冰糖',
    style_prompt: stylePrompt || null,
  }, {
    responseType: 'blob',
  })
  return response.data
}

/** 获取音色列表 */
export async function fetchVoices(): Promise<Voice[]> {
  const { data } = await api.get('/voices')
  return data.voices
}

/** 获取 TTS 模型列表 */
export async function fetchTTSModels(): Promise<TTSModel[]> {
  const { data } = await api.get('/tts-models')
  return data.models
}

/** 获取风格预设 */
export async function fetchStylePresets(): Promise<StylePreset[]> {
  const { data } = await api.get('/style-presets')
  return data.presets
}
