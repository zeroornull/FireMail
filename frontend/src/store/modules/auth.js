import api from '@/services/api'
import { jwtDecode } from 'jwt-decode'
import router from '@/router'

// 从localStorage获取保存的token
const token = localStorage.getItem('token')
let initialUser = null

// 如果有token，尝试解析用户信息
if (token) {
  try {
    const decoded = jwtDecode(token)
    if (decoded.exp * 1000 > Date.now()) {
      initialUser = {
        id: decoded.user_id,
        username: decoded.username,
        isAdmin: decoded.is_admin
      }
    } else {
      // token已过期，清除
      localStorage.removeItem('token')
    }
  } catch (e) {
    console.error('无效的token:', e)
    localStorage.removeItem('token')
  }
}

const state = {
  token: token || null,
  user: initialUser,
  loading: false,
  error: null
}

const mutations = {
  AUTH_REQUEST(state) {
    state.loading = true
    state.error = null
  },
  AUTH_SUCCESS(state, { token, user }) {
    state.loading = false
    state.token = token
    state.user = user
  },
  AUTH_ERROR(state, error) {
    state.loading = false
    state.error = error
  },
  LOGOUT(state) {
    state.token = null
    state.user = null
  },
  CLEAR_ERROR(state) {
    state.error = null
  }
}

const actions = {
  // 用户登录
  async login({ commit }, { username, password }) {
    commit('AUTH_REQUEST')
    try {
      const response = await api.login(username, password)
      const token = response.data.token
      const user = {
        id: response.data.user.id,
        username: response.data.user.username,
        isAdmin: response.data.user.is_admin
      }
      
      // 保存token到localStorage
      localStorage.setItem('token', token)
      
      // 更新API请求头
      api.setAuthHeader(token)
      
      commit('AUTH_SUCCESS', { token, user })
      
      return user
    } catch (error) {
      localStorage.removeItem('token')
      commit('AUTH_ERROR', error.response?.data?.error || '登录失败')
      throw error
    }
  },
  
  // 用户注册
  async register({ commit }, { username, password }) {
    commit('AUTH_REQUEST')
    try {
      const response = await api.register(username, password)
      commit('CLEAR_ERROR')
      return response.data
    } catch (error) {
      commit('AUTH_ERROR', error.response?.data?.error || '注册失败')
      throw error
    }
  },
  
  // 用户登出
  async logout({ commit }) {
    try {
      await api.logout()
    } catch (e) {
      console.error('登出API调用失败:', e)
    }
    
    localStorage.removeItem('token')
    api.removeAuthHeader()
    commit('LOGOUT')
    
    // 重定向到登录页
    if (router.currentRoute.value.meta.requiresAuth) {
      router.push('/login')
    }
  },
  
  // 获取当前用户信息
  async getCurrentUser({ commit, state }) {
    if (!state.token) return null
    
    commit('AUTH_REQUEST')
    try {
      const response = await api.getCurrentUser()
      const user = {
        id: response.data.id,
        username: response.data.username,
        isAdmin: response.data.is_admin
      }
      commit('AUTH_SUCCESS', { token: state.token, user })
      return user
    } catch (error) {
      commit('AUTH_ERROR', error.response?.data?.error || '获取用户信息失败')
      // 如果令牌无效，登出用户
      if (error.response?.status === 401) {
        localStorage.removeItem('token')
        commit('LOGOUT')
        router.push('/login')
      }
      throw error
    }
  },
  
  // 修改密码
  async changePassword({ commit }, { oldPassword, newPassword }) {
    commit('AUTH_REQUEST')
    try {
      const response = await api.changePassword(oldPassword, newPassword)
      commit('CLEAR_ERROR')
      return response.data
    } catch (error) {
      commit('AUTH_ERROR', error.response?.data?.error || '修改密码失败')
      throw error
    }
  },
  
  // 管理员：获取所有用户
  async getAllUsers({ commit, state }) {
    if (!state.token || !state.user?.isAdmin) return []
    
    commit('AUTH_REQUEST')
    try {
      const response = await api.getAllUsers()
      commit('CLEAR_ERROR')
      return response.data
    } catch (error) {
      commit('AUTH_ERROR', error.response?.data?.error || '获取用户列表失败')
      throw error
    }
  },
  
  // 管理员：创建用户
  async createUser({ commit, state }, userData) {
    if (!state.token || !state.user?.isAdmin) throw new Error('需要管理员权限')
    
    commit('AUTH_REQUEST')
    try {
      const response = await api.createUser(userData)
      commit('CLEAR_ERROR')
      return response.data
    } catch (error) {
      commit('AUTH_ERROR', error.response?.data?.error || '创建用户失败')
      throw error
    }
  },
  
  // 管理员：删除用户
  async deleteUser({ commit, state }, userId) {
    if (!state.token || !state.user?.isAdmin) throw new Error('需要管理员权限')
    
    commit('AUTH_REQUEST')
    try {
      const response = await api.deleteUser(userId)
      commit('CLEAR_ERROR')
      return response.data
    } catch (error) {
      commit('AUTH_ERROR', error.response?.data?.error || '删除用户失败')
      throw error
    }
  },
  
  // 管理员：重置用户密码
  async resetUserPassword({ commit, state }, { userId, newPassword }) {
    if (!state.token || !state.user?.isAdmin) throw new Error('需要管理员权限')
    
    commit('AUTH_REQUEST')
    try {
      const response = await api.resetUserPassword(userId, newPassword)
      commit('CLEAR_ERROR')
      return response.data
    } catch (error) {
      commit('AUTH_ERROR', error.response?.data?.error || '重置密码失败')
      throw error
    }
  },
  
  // 清除认证错误
  clearError({ commit }) {
    commit('CLEAR_ERROR')
  }
}

const getters = {
  isAuthenticated: state => !!state.token,
  currentUser: state => state.user,
  isAdmin: state => state.user?.isAdmin || false,
  authError: state => state.error,
  authLoading: state => state.loading
}

export default {
  namespaced: true,
  state,
  mutations,
  actions,
  getters
} 