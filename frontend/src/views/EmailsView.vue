<template>
  <div class="emails-container">
    <el-card class="email-list-card">
      <template #header>
        <div class="card-header">
          <h2>邮箱列表</h2>
          <div class="actions">
            <el-button type="primary" @click="refreshEmails">刷新列表</el-button>
            <el-button type="success" @click="showAddEmailDialog">添加邮箱</el-button>
            <el-button type="warning" @click="showImportDialog">批量导入</el-button>
          </div>
        </div>
      </template>
      
      <div class="toolbar">
        <el-button 
          type="danger" 
          :disabled="!hasSelectedEmails" 
          @click="handleBatchDelete"
        >
          批量删除
        </el-button>
        <el-button 
          type="primary" 
          :disabled="!hasSelectedEmails" 
          @click="handleBatchCheck"
        >
          批量收信
        </el-button>
      </div>
      
      <el-table
        v-loading="loading"
        :data="emails"
        @selection-change="handleSelectionChange"
        style="width: 100%"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="email" label="邮箱地址" width="220" />
        <el-table-column prop="password" label="密码" width="120">
          <template #default="scope">
            ******
          </template>
        </el-table-column>
        <el-table-column prop="last_check_time" label="最后检查时间" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.last_check_time) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="150">
          <template #default="scope">
            <div v-if="scope.row.progress !== undefined && scope.row.progress >= 0">
              <el-progress :percentage="scope.row.progress" />
              <div class="progress-message">{{ scope.row.progressMessage }}</div>
            </div>
            <el-tag v-else type="info">空闲</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作">
          <template #default="scope">
            <el-button 
              type="primary" 
              size="small" 
              @click="handleCheck(scope.row)"
              :disabled="isEmailProcessing(scope.row)"
            >
              {{getEmailActionText(scope.row)}}
            </el-button>
            <el-button 
              type="info" 
              size="small" 
              @click="handleViewMails(scope.row)"
            >
              查看邮件
            </el-button>
            <el-button 
              type="danger" 
              size="small" 
              @click="handleDelete(scope.row)"
              :disabled="isEmailProcessing(scope.row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 邮件内容显示 -->
    <el-card v-if="currentEmail" class="mail-content-card">
      <template #header>
        <div class="card-header">
          <h2>{{ currentEmail.email }} 的邮件</h2>
          <el-button @click="currentEmail = null">关闭</el-button>
        </div>
      </template>
      
      <el-table
        v-loading="loadingMails"
        :data="mailRecords"
        style="width: 100%"
      >
        <el-table-column prop="subject" label="主题" width="250" />
        <el-table-column prop="sender" label="发件人" width="200" />
        <el-table-column prop="received_time" label="接收时间" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.received_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作">
          <template #default="scope">
            <el-button 
              type="primary" 
              size="small" 
              @click="viewMailContent(scope.row)"
            >
              查看内容
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <el-dialog
        v-model="mailContentDialogVisible"
        :title="selectedMail ? selectedMail.subject : '邮件内容'"
        width="70%"
      >
        <div v-if="selectedMail">
          <p><strong>发件人:</strong> {{ selectedMail.sender }}</p>
          <p><strong>接收时间:</strong> {{ formatDate(selectedMail.received_time) }}</p>
          <div class="mail-content">
            <pre>{{ selectedMail.content }}</pre>
          </div>
        </div>
      </el-dialog>
    </el-card>
    
    <!-- 添加邮箱对话框 -->
    <el-dialog
      v-model="addEmailDialogVisible"
      title="添加邮箱"
      width="500px"
    >
      <el-form :model="newEmail" label-width="120px">
        <el-form-item label="邮箱地址">
          <el-input v-model="newEmail.email" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="newEmail.password" type="password" />
        </el-form-item>
        <el-form-item label="客户端ID">
          <el-input v-model="newEmail.clientId" />
        </el-form-item>
        <el-form-item label="刷新令牌">
          <el-input v-model="newEmail.refreshToken" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addEmailDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAddEmail" :loading="addingEmail">提交</el-button>
      </template>
    </el-dialog>
    
    <!-- 批量导入对话框 -->
    <el-dialog
      v-model="importDialogVisible"
      title="批量导入邮箱"
      width="600px"
    >
      <p class="import-help">请按照以下格式输入邮箱信息，每行一个：<br/>邮箱地址----密码----客户端ID----刷新令牌</p>
      <el-input
        v-model="importData"
        type="textarea"
        :rows="10"
        placeholder="例如: example@outlook.com----password----clientid----refreshtoken"
      />
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleImport" :loading="importing">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useStore } from 'vuex'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'EmailsView',
  setup() {
    const store = useStore()
    
    // 状态
    const loadingMails = ref(false)
    const addEmailDialogVisible = ref(false)
    const importDialogVisible = ref(false)
    const mailContentDialogVisible = ref(false)
    const addingEmail = ref(false)
    const importing = ref(false)
    
    // 表单数据
    const newEmail = ref({
      email: '',
      password: '',
      clientId: '',
      refreshToken: ''
    })
    const importData = ref('')
    const selectedMail = ref(null)
    
    // 计算属性
    const emails = computed(() => store.state.emails.emails)
    const loading = computed(() => store.state.emails.loading)
    const currentEmail = computed(() => store.state.emails.currentEmail)
    const mailRecords = computed(() => {
      const emailId = currentEmail.value?.id
      return emailId ? store.getters['emails/mailRecords'](emailId) : []
    })

    const selectedEmails = ref([])
    const hasSelectedEmails = computed(() => selectedEmails.value.length > 0)
    
    // 方法
    const refreshEmails = async () => {
      try {
        await store.dispatch('emails/fetchAllEmails')
        ElMessage.success('刷新成功')
      } catch (error) {
        console.error('获取邮箱列表失败:', error)
        ElMessage.error('获取邮箱列表失败，请检查网络连接')
      }
    }
    
    const handleSelectionChange = (selection) => {
      selectedEmails.value = selection
    }
    
    const handleDelete = (row) => {
      ElMessageBox.confirm(
        `确定要删除邮箱 ${row.email} 吗？`,
        '提示',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(async () => {
        try {
          await store.dispatch('emails/deleteEmail', row.id)
          ElMessage.success('删除成功')
        } catch (error) {
          console.error('删除邮箱失败:', error)
          ElMessage.error('删除邮箱失败: ' + error.message)
        }
      }).catch(() => {
        // 取消删除，不做任何操作
      })
    }
    
    const handleBatchDelete = () => {
      if (!hasSelectedEmails.value) {
        ElMessage.warning('请先选择要删除的邮箱')
        return
      }

      const count = selectedEmails.value.length
      const emailIds = selectedEmails.value.map(email => email.id)

      ElMessageBox.confirm(
        `确定要删除选中的 ${count} 个邮箱吗？`,
        '批量删除确认',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(async () => {
        try {
          await store.dispatch('emails/batchDeleteEmails', emailIds)
          ElMessage.success(`已成功删除 ${count} 个邮箱`)
          selectedEmails.value = []
        } catch (error) {
          console.error('批量删除邮箱失败:', error)
          ElMessage.error('批量删除邮箱失败: ' + error.message)
        }
      }).catch(() => {
        // 取消删除，不做任何操作
      })
    }
    
    const handleCheck = async (row) => {
      try {
        await store.dispatch('emails/checkEmail', row.id)
        ElMessage.info(`正在检查邮箱 ${row.email} 的邮件，请稍候...`)
      } catch (error) {
        console.error('检查邮箱失败:', error)
        ElMessage.error('检查邮箱失败: ' + error.message)
      }
    }
    
    const handleBatchCheck = async () => {
      if (!hasSelectedEmails.value) {
        ElMessage.warning('请先选择要检查的邮箱')
        return
      }

      const count = selectedEmails.value.length
      const emailIds = selectedEmails.value.map(email => email.id)

      try {
        await store.dispatch('emails/batchCheckEmails', emailIds)
        ElMessage.info(`正在检查 ${count} 个邮箱的邮件，请稍候...`)
      } catch (error) {
        console.error('批量检查邮箱失败:', error)
        ElMessage.error('批量检查邮箱失败: ' + error.message)
      }
    }
    
    const handleViewMails = async (row) => {
      loadingMails.value = true
      try {
        // 设置当前选中的邮箱
        store.commit('emails/SET_CURRENT_EMAIL', row)
        // 获取邮件记录
        await store.dispatch('emails/getMailRecords', row.id)
      } catch (error) {
        console.error('获取邮件记录失败:', error)
        ElMessage.error('获取邮件记录失败: ' + error.message)
      } finally {
        loadingMails.value = false
      }
    }
    
    const viewMailContent = (mail) => {
      selectedMail.value = mail
      mailContentDialogVisible.value = true
    }
    
    const showAddEmailDialog = () => {
      newEmail.value = {
        email: '',
        password: '',
        clientId: '',
        refreshToken: ''
      }
      addEmailDialogVisible.value = true
    }
    
    const handleAddEmail = async () => {
      // 验证表单
      if (!newEmail.value.email || !newEmail.value.password) {
        ElMessage.warning('邮箱地址和密码不能为空')
        return
      }
      
      addingEmail.value = true
      try {
        await store.dispatch('emails/addEmail', {
          email: newEmail.value.email,
          password: newEmail.value.password,
          clientId: newEmail.value.clientId || null,
          refreshToken: newEmail.value.refreshToken || null
        })
        
        ElMessage.success('邮箱添加成功')
        addEmailDialogVisible.value = false
        // 重置表单
        newEmail.value = {
          email: '',
          password: '',
          clientId: '',
          refreshToken: ''
        }
        
        // 刷新邮箱列表
        refreshEmails()
      } catch (error) {
        console.error('添加邮箱失败:', error)
        ElMessage.error('添加邮箱失败: ' + error.message)
      } finally {
        addingEmail.value = false
      }
    }
    
    const showImportDialog = () => {
      importData.value = ''
      importDialogVisible.value = true
    }
    
    const handleImport = async () => {
      if (!importData.value.trim()) {
        ElMessage.warning('导入数据不能为空')
        return
      }
      
      importing.value = true
      try {
        // 如果WebSocket连接成功，则使用WebSocket导入
        if (store.state.websocketConnected) {
          const WebSocketService = require('@/services/websocket').default
          WebSocketService.importEmails(importData.value)
          ElMessage.info('正在处理导入请求，请稍候...')
        } else {
          // 否则使用API导入
          await store.dispatch('emails/importEmails', importData.value)
          ElMessage.success('导入成功')
          // 刷新邮箱列表
          refreshEmails()
        }
        
        importDialogVisible.value = false
        importData.value = ''
      } catch (error) {
        console.error('导入邮箱失败:', error)
        ElMessage.error('导入邮箱失败: ' + error.message)
      } finally {
        importing.value = false
      }
    }
    
    const formatDate = (dateStr) => {
      if (!dateStr) return '未检查'
      
      try {
        const date = new Date(dateStr)
        return date.toLocaleString('zh-CN')
      } catch (e) {
        return dateStr
      }
    }
    
    const isEmailProcessing = (email) => {
      return store.getters.isCheckingEmail(email.id)
    }
    
    const getEmailActionText = (email) => {
      return isEmailProcessing(email) ? '检查中...' : '检查邮件'
    }
    
    // 生命周期钩子
    onMounted(() => {
      refreshEmails()
    })
    
    return {
      // 状态
      loading,
      loadingMails,
      addEmailDialogVisible,
      importDialogVisible,
      mailContentDialogVisible,
      addingEmail,
      importing,
      
      // 数据
      emails,
      currentEmail,
      mailRecords,
      hasSelectedEmails,
      newEmail,
      importData,
      selectedMail,
      
      // 方法
      refreshEmails,
      handleSelectionChange,
      handleDelete,
      handleBatchDelete,
      handleCheck,
      handleBatchCheck,
      handleViewMails,
      viewMailContent,
      showAddEmailDialog,
      handleAddEmail,
      showImportDialog,
      handleImport,
      formatDate,
      isEmailProcessing,
      getEmailActionText
    }
  }
}
</script>

<style scoped>
.emails-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  font-size: 18px;
}

.actions {
  display: flex;
  gap: 10px;
}

.toolbar {
  margin-bottom: 15px;
  display: flex;
  gap: 10px;
}

.progress-message {
  font-size: 12px;
  color: #666;
  margin-top: 5px;
}

.mail-content {
  margin-top: 15px;
  border: 1px solid #e0e0e0;
  padding: 15px;
  white-space: pre-wrap;
  background-color: #f9f9f9;
  border-radius: 4px;
  max-height: 400px;
  overflow-y: auto;
}

.import-help {
  color: #666;
  margin-bottom: 15px;
}
</style> 