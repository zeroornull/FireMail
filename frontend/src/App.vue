<template>
  <el-config-provider :locale="zhCn">
    <div class="app-container">
      <el-container>
        <el-header class="app-header">
          <div class="header-left">
            <h1>花火邮箱助手</h1>
          </div>
          
          <div class="header-right">
            <!-- 用户未登录状态 -->
            <template v-if="!isAuthenticated">
              <router-link to="/login">
                <el-button type="primary" plain>登录</el-button>
              </router-link>
              <router-link to="/register">
                <el-button type="primary">注册</el-button>
              </router-link>
            </template>
            
            <!-- 用户已登录状态 -->
            <template v-else>
              <el-dropdown @command="handleUserCommand">
                <span class="user-dropdown-link">
                  {{ currentUser ? currentUser.username : '用户' }}
                  <el-icon><arrow-down /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="account">账户设置</el-dropdown-item>
                    <el-dropdown-item v-if="isAdmin" command="admin">用户管理</el-dropdown-item>
                    <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </template>
            
            <div class="connection-status">
              <el-tag :type="websocketConnected ? 'success' : 'danger'">
                {{ websocketConnected ? '已连接' : '未连接' }}
              </el-tag>
            </div>
          </div>
        </el-header>
        
        <!-- 导航菜单 -->
        <el-menu 
          v-if="isAuthenticated"
          mode="horizontal" 
          :router="true" 
          :default-active="$route.path"
          class="app-nav"
        >
          <el-menu-item index="/">首页</el-menu-item>
          <el-menu-item index="/emails">邮箱管理</el-menu-item>
          <el-menu-item index="/import">批量导入</el-menu-item>
          <el-menu-item index="/admin/users" v-if="isAdmin">用户管理</el-menu-item>
          <el-menu-item index="/about">关于</el-menu-item>
        </el-menu>
        
        <el-main>
          <router-view v-if="!initializing"/>
          <div v-else class="loading-container">
            <el-skeleton :rows="6" animated />
          </div>
        </el-main>
        
        <el-footer class="app-footer">
          花火邮箱助手 &copy; 2025
        </el-footer>
      </el-container>
      
      <!-- 通知组件 -->
      <Notifications />
    </div>
  </el-config-provider>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useStore } from 'vuex'
import { ElConfigProvider, ElMessage } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import websocket from '@/services/websocket'
import Notifications from './components/Notifications.vue'

// 初始化状态
const initializing = ref(true)
const isConnected = ref(false)

// 使用Vuex来管理状态
const store = useStore()
const router = useRouter()

// 计算属性
const websocketConnected = computed(() => store.state.websocketConnected)
const isAuthenticated = computed(() => store.getters['auth/isAuthenticated'])
const currentUser = computed(() => store.getters['auth/currentUser'])
const isAdmin = computed(() => store.getters['auth/isAdmin'])

// 初始化认证状态
const initializeAuth = async () => {
  initializing.value = true
  
  if (isAuthenticated.value) {
    try {
      // 获取当前用户信息
      await store.dispatch('auth/getCurrentUser')
    } catch (error) {
      console.error('获取用户信息失败:', error)
    }
  }
  
  initializing.value = false
}

// 用户下拉菜单命令处理
const handleUserCommand = (command) => {
  switch (command) {
    case 'account':
      router.push('/account')
      break
    case 'admin':
      router.push('/admin/users')
      break
    case 'logout':
      handleLogout()
      break
  }
}

// 退出登录
const handleLogout = async () => {
  try {
    await store.dispatch('auth/logout')
    router.push('/login')
    ElMessage({
      type: 'success',
      message: '已成功退出登录'
    })
  } catch (error) {
    console.error('登出失败:', error)
    ElMessage.error('退出登录失败')
  }
}

// 更新连接状态
const updateConnectionStatus = () => {
  isConnected.value = websocket.isConnected
}

// 监听WebSocket连接变化
const handleConnect = () => {
  store.commit('SET_WEBSOCKET_CONNECTED', true)
}

const handleDisconnect = () => {
  store.commit('SET_WEBSOCKET_CONNECTED', false)
}

// 监听认证状态变化
watch(isAuthenticated, (newValue) => {
  // 认证状态发生变化时，重新处理WebSocket连接
  if (newValue) {
    if (!websocket.isConnected) {
      websocket.connect()
    }
  } else {
    websocket.disconnect()
  }
})

// 组件挂载时连接WebSocket和初始化认证
onMounted(async () => {
  // 初始化认证状态
  await initializeAuth()
  
  // 连接处理
  websocket.onConnect(() => {
    isConnected.value = true
  })
  
  // 断开连接处理
  websocket.onDisconnect(() => {
    isConnected.value = false
  })
  
  // 注册WebSocket事件处理器
  websocket.onConnect(handleConnect)
  websocket.onDisconnect(handleDisconnect)
  
  // 确保WebSocket连接（仅在用户已认证时）
  if (isAuthenticated.value && !websocket.isConnected) {
    websocket.connect()
  }
})

// 组件卸载时断开WebSocket连接
onUnmounted(() => {
  websocket.offConnect(handleConnect)
  websocket.offDisconnect(handleDisconnect)
  websocket.disconnect()
})
</script>

<style>
/* 全局样式 */
:root {
  --primary-color: #409eff;
  --success-color: #67c23a;
  --warning-color: #e6a23c;
  --danger-color: #f56c6c;
  --info-color: #909399;
  --text-color: #303133;
  --border-color: #dcdfe6;
  --background-color: #f5f7fa;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'PingFang SC', 'Helvetica Neue', Helvetica, 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  color: var(--text-color);
  background-color: var(--background-color);
  line-height: 1.5;
}

.app-container {
  min-height: 100vh;
}

.app-header {
  background-color: #fff;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  height: 60px !important;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.app-header h1 {
  font-size: 22px;
  color: var(--primary-color);
  margin: 0;
}

.connection-status {
  display: flex;
  align-items: center;
  margin-left: 16px;
}

.user-dropdown-link {
  display: flex;
  align-items: center;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-color);
}

.user-dropdown-link .el-icon {
  margin-left: 4px;
}

.app-nav {
  border-bottom: 1px solid var(--border-color);
}

.app-footer {
  text-align: center;
  color: var(--info-color);
  font-size: 14px;
  padding: 20px 0 !important;
  background-color: #fff;
  border-top: 1px solid var(--border-color);
}

.el-main {
  padding: 20px;
  background-color: var(--background-color);
}

.loading-container {
  padding: 40px 0;
}

/* 响应式布局 */
@media (max-width: 768px) {
  .header-right {
    flex-direction: column;
    align-items: flex-end;
  }
  
  .connection-status {
    margin-top: 10px;
  }
}
</style>