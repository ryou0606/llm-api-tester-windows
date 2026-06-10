<template>
  <el-container class="app-container">
    <!-- 侧边栏导航 -->
    <el-aside width="220px" class="app-aside">
      <div class="logo">
        <el-icon :size="28" color="#409eff"><Monitor /></el-icon>
        <span class="logo-text">LLM Tester</span>
      </div>
      <el-menu
        :default-active="route.path"
        router
        class="side-menu"
        background-color="#1d1e1f"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="/">
          <el-icon><Setting /></el-icon>
          <span>{{ $t('menu.modelList') }}</span>
        </el-menu-item>
        <el-menu-item index="/test/0">
          <el-icon><ChatDotRound /></el-icon>
          <span>{{ $t('menu.modelTest') }}</span>
        </el-menu-item>
        <el-menu-item index="/arena">
          <el-icon><Trophy /></el-icon>
          <span>{{ $t('menu.arena') }}</span>
        </el-menu-item>
        <el-menu-item index="/vision">
          <el-icon><Picture /></el-icon>
          <span>{{ $t('menu.vision') }}</span>
        </el-menu-item>
        <el-menu-item index="/audio">
          <el-icon><Microphone /></el-icon>
          <span>{{ $t('menu.audio') }}</span>
        </el-menu-item>
        <el-menu-item index="/relay">
          <el-icon><Connection /></el-icon>
          <span>{{ $t('menu.relay') }}</span>
        </el-menu-item>
      </el-menu>

      <!-- 语言切换 -->
      <div class="language-switch">
        <el-dropdown @command="handleLanguageChange" trigger="click">
          <el-button class="language-btn" :icon="Setting">
            {{ currentLanguageLabel }}
            <el-icon class="el-icon--right"><arrow-down /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="zh-CN">🇨🇳 中文</el-dropdown-item>
              <el-dropdown-item command="en-US">🇺🇸 English</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-aside>

    <!-- 主内容区 -->
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import { Setting, ArrowDown } from '@element-plus/icons-vue'

const route = useRoute()
const { locale } = useI18n()

const currentLanguageLabel = computed(() => {
  return locale.value === 'zh-CN' ? '🇨🇳 中文' : '🇺🇸 English'
})

const handleLanguageChange = (lang: string) => {
  locale.value = lang
  localStorage.setItem('language', lang)
}
</script>

<style>
/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.app-container {
  height: 100vh;
}

.app-aside {
  background-color: #1d1e1f;
  border-right: 1px solid #333;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 20px;
  border-bottom: 1px solid #333;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.5px;
}

.side-menu {
  border-right: none;
  flex: 1;
}

.app-main {
  background-color: #f5f7fa;
  padding: 24px;
  overflow-y: auto;
}

.language-switch {
  padding: 16px;
  border-top: 1px solid #333;
}

.language-btn {
  width: 100%;
  background-color: #2d2d2d !important;
  border-color: #444 !important;
  color: #bfcbd9 !important;
}

.language-btn:hover {
  background-color: #3d3d3d !important;
  border-color: #409eff !important;
}
</style>
