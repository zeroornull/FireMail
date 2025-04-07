<template>
  <div class="page-container">
    <div class="emails-container">
      <el-card class="email-list-card shadow">
        <template #header>
          <div class="card-header flex-between">
            <h2 class="page-title">邮箱列表</h2>
            <div class="actions flex gap-md">
              <el-button type="primary" @click="refreshEmails" :icon="Refresh" class="hover-scale">
                刷新列表
              </el-button>
              <el-button type="success" @click="showAddEmailDialog" :icon="Plus" class="hover-scale">
                添加邮箱
              </el-button>
            </div>
          </div>
        </template>
        
        <div class="toolbar flex gap-md mb-4">
          <el-button 
            type="danger" 
            :disabled="!hasSelectedEmails" 
            @click="handleBatchDelete"
            :icon="Delete"
            class="hover-scale"
          >
            批量删除
          </el-button>
          <el-button 
            type="primary" 
            :disabled="!hasSelectedEmails" 
            @click="handleBatchCheck"
            :icon="Download"
            class="hover-scale"
          >
            批量收信
          </el-button>
        </div>
        
        <el-table
          v-loading="loading"
          :data="emails"
          @selection-change="handleSelectionChange"
          style="width: 100%"
          stripe
          border
          highlight-current-row
          class="email-table"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="email" label="邮箱地址" width="220" />
          <el-table-column prop="mail_type" label="邮箱类型" width="120">
            <template #default="scope">
              <el-tag 
                :type="getMailTypeColor(scope.row.mail_type || 'outlook')" 
                effect="plain"
                class="mail-type-tag"
              >
                {{ getMailTypeName(scope.row.mail_type || 'outlook') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="password" label="密码" width="150">
            <template #default="scope">
              <div class="password-field flex-between">
                <span class="password-text">{{ scope.row.showPassword ? scope.row.password : '******' }}</span>
                <el-button 
                  type="primary" 
                  link
                  :icon="scope.row.showPassword ? Hide : View" 
                  @click="togglePasswordVisibility(scope.row)"
                  :loading="scope.row.passwordLoading"
                  class="password-toggle-btn"
                />
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="last_check_time" label="最后检查时间" width="180">
            <template #default="scope">
              <span class="time-field">{{ formatDate(scope.row.last_check_time) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="150">
            <template #default="scope">
              <div v-if="scope.row.progress !== undefined && scope.row.progress >= 0" class="progress-wrapper">
                <el-progress 
                  :percentage="scope.row.progress" 
                  :status="scope.row.progress >= 100 ? 'success' : ''" 
                  :stroke-width="8"
                  class="custom-progress"
                />
                <div class="progress-message text-muted">{{ scope.row.progressMessage }}</div>
              </div>
              <el-tag v-else type="info" effect="light" class="status-tag">空闲</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="300">
            <template #default="scope">
              <div class="action-buttons flex gap-sm">
                <el-button 
                  type="primary" 
                  size="small" 
                  @click="handleCheck(scope.row)"
                  :disabled="isEmailProcessing(scope.row)"
                  :icon="Refresh"
                  class="action-btn"
                >
                  {{getEmailActionText(scope.row)}}
                </el-button>
                <el-button 
                  type="info" 
                  size="small" 
                  @click="handleViewMails(scope.row)"
                  :icon="Message"
                  class="action-btn"
                >
                  查看邮件
                </el-button>
                <el-button 
                  type="danger" 
                  size="small" 
                  @click="handleDelete(scope.row)"
                  :disabled="isEmailProcessing(scope.row)"
                  :icon="Delete"
                  class="action-btn"
                >
                  删除
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
      
      <!-- 邮件详情悬浮窗口 -->
      <el-dialog
        v-model="mailListDialogVisible"
        title="邮件列表"
        width="90%"
        top="5vh"
        class="mail-list-dialog"
        destroy-on-close
      >
        <div v-if="currentEmail" class="mail-dialog-header flex-between mb-4">
          <h3 class="email-title">
            <span class="text-primary">{{ currentEmail.email }}</span> 的邮件
          </h3>
          <el-button 
            type="primary"
            size="small"
            @click="handleCheck(currentEmail)"
            :disabled="isEmailProcessing(currentEmail)"
            :icon="Refresh"
            class="refresh-btn hover-scale"
          >
            刷新邮件
          </el-button>
        </div>
        
        <el-table
          v-loading="loadingMails"
          :data="mailRecords"
          style="width: 100%"
          stripe
          border
          max-height="60vh"
          class="mail-list-table"
        >
          <el-table-column prop="subject" label="主题" min-width="250" show-overflow-tooltip />
          <el-table-column prop="sender" label="发件人" min-width="200" show-overflow-tooltip />
          <el-table-column prop="received_time" label="接收时间" width="180">
            <template #default="scope">
              <span class="time-field">{{ formatDate(scope.row.received_time) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="scope">
              <el-button 
                type="primary" 
                size="small" 
                @click="viewMailContent(scope.row)"
                :icon="Document"
                class="view-btn"
              >
                查看
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-dialog>
      
      <!-- 邮件内容查看对话框 -->
      <el-dialog
        v-model="mailContentDialogVisible"
        :title="selectedMail ? selectedMail.subject : '邮件内容'"
        width="70%"
        top="5vh"
        class="mail-content-dialog"
        append-to-body
      >
        <div v-if="selectedMail" class="mail-detail">
          <div class="mail-info bg-light p-4 rounded-md">
            <div class="info-item flex-between mb-2">
              <span class="label text-muted">发件人:</span>
              <span class="value">{{ selectedMail.sender }}</span>
            </div>
            <div class="info-item flex-between">
              <span class="label text-muted">接收时间:</span>
              <span class="value">{{ formatDate(selectedMail.received_time) }}</span>
            </div>
          </div>
          <el-divider />
          <div class="mail-content p-4 bg-light rounded-md">
            <pre class="content-text">{{ selectedMail.content }}</pre>
          </div>
        </div>
      </el-dialog>
      
      <!-- 添加邮箱对话框 -->
      <el-dialog
        v-model="addEmailDialogVisible"
        title="添加邮箱"
        width="500px"
        class="add-email-dialog"
      >
        <el-tabs v-model="addEmailActiveTab">
          <el-tab-pane label="单个添加" name="single">
            <el-form :model="newEmail" label-width="120px">
              <el-form-item label="邮箱类型">
                <el-select v-model="newEmail.mailType" placeholder="请选择邮箱类型">
                  <el-option
                    label="Outlook/Hotmail"
                    value="outlook"
                  />
                  <!-- 为以后扩展预留 -->
                </el-select>
              </el-form-item>
              <el-form-item label="邮箱地址">
                <el-input v-model="newEmail.email" />
              </el-form-item>
              <el-form-item label="密码">
                <el-input v-model="newEmail.password" type="password" />
              </el-form-item>
              <el-form-item v-if="newEmail.mailType === 'outlook'" label="客户端ID">
                <el-input v-model="newEmail.clientId" />
              </el-form-item>
              <el-form-item v-if="newEmail.mailType === 'outlook'" label="刷新令牌">
                <el-input v-model="newEmail.refreshToken" type="textarea" :rows="3" />
              </el-form-item>
            </el-form>
          </el-tab-pane>
          <el-tab-pane label="批量添加" name="batch">
            <p class="import-help">请按照以下格式输入邮箱信息，每行一个：<br/>邮箱地址----密码----客户端ID----刷新令牌</p>
            <el-form :model="batchImport" label-width="120px" :rules="batchImportRules" ref="batchImportFormRef">
              <el-form-item label="邮箱类型">
                <el-select v-model="batchImport.mailType" placeholder="请选择邮箱类型">
                  <el-option
                    label="Outlook/Hotmail"
                    value="outlook"
                  />
                  <!-- 为以后扩展预留 -->
                </el-select>
              </el-form-item>
              <el-form-item label="批量数据" prop="data">
                <el-input
                  v-model="batchImport.data"
                  type="textarea"
                  :rows="10"
                  placeholder="例如: example@outlook.com----password----clientid----refreshtoken"
                />
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>
        <template #footer>
          <el-button @click="addEmailDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleAddOrImport" :loading="addingEmail || importing">提交</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, reactive } from 'vue'
import { useStore } from 'vuex'
import { ElMessage, ElMessageBox } from 'element-plus'
import WebSocketService from '@/services/websocket'
import { 
  Delete, 
  Refresh, 
  Plus, 
  Download, 
  Document, 
  Message,
  View,
  Hide
} from '@element-plus/icons-vue'

export default {
  name: 'EmailsView',
  setup() {
    const store = useStore()
    
    // 状态
    const loadingMails = ref(false)
    const addEmailDialogVisible = ref(false)
    const addEmailActiveTab = ref('single') // 添加选项卡活动页
    const mailContentDialogVisible = ref(false)
    const mailListDialogVisible = ref(false)
    const addingEmail = ref(false)
    const importing = ref(false)
    
    // 表单数据
    const newEmail = reactive({
      email: '',
      password: '',
      clientId: '',
      refreshToken: '',
      mailType: 'outlook' // 默认为outlook类型
    })
    
    const batchImportFormRef = ref(null)
    
    // 批量导入数据
    const batchImport = reactive({
      data: '',
      mailType: 'outlook'
    })
    
    // 批量导入验证规则
    const batchImportRules = {
      data: [
        { required: true, message: '导入数据不能为空', trigger: 'blur' },
        { validator: validateBatchData, trigger: 'blur' }
      ]
    }
    
    // 验证批量导入数据
    function validateBatchData(rule, value, callback) {
      if (!value) {
        callback()
        return
      }
      
      const lines = value.trim().split('\n')
      let hasError = false
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim()
        if (!line) continue
        
        // 根据不同邮箱类型进行不同的验证
        if (batchImport.mailType === 'outlook') {
          const parts = line.split('----')
          if (parts.length !== 4) {
            hasError = true
            callback(new Error(`第 ${i + 1} 行格式错误，请使用"----"分隔邮箱、密码、客户端ID和RefreshToken`))
            break
          }
          
          if (!parts[0] || !parts[1] || !parts[2] || !parts[3]) {
            hasError = true
            callback(new Error(`第 ${i + 1} 行有空白字段，所有字段都必须填写`))
            break
          }
          
          // 简单的邮箱格式检查
          if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(parts[0])) {
            hasError = true
            callback(new Error(`第 ${i + 1} 行邮箱格式不正确`))
            break
          }
        }
      }
      
      if (!hasError) {
        callback()
      }
    }
    
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
        // 显示邮件列表对话框
        mailListDialogVisible.value = true
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
      resetAddEmailForm()
      addEmailDialogVisible.value = true
      addEmailActiveTab.value = 'single' // 默认显示单个添加
    }
    
    const handleAddOrImport = async () => {
      if (addEmailActiveTab.value === 'single') {
        await handleAddEmail()
      } else {
        await handleImport()
      }
    }
    
    const handleAddEmail = async () => {
      addingEmail.value = true
      try {
        // 根据不同邮箱类型调用不同的添加方法
        if (newEmail.mailType === 'outlook') {
          await store.dispatch('emails/addEmail', {
            email: newEmail.email,
            password: newEmail.password,
            clientId: newEmail.clientId,
            refreshToken: newEmail.refreshToken,
            mailType: newEmail.mailType
          })
        } else {
          // 未来添加对其他邮箱类型的支持
        }
        
        ElMessage.success('邮箱添加成功')
        addEmailDialogVisible.value = false
        resetAddEmailForm()
        refreshEmails()
      } catch (error) {
        ElMessage.error(error.message || '添加邮箱失败')
      } finally {
        addingEmail.value = false
      }
    }
    
    const handleImport = async () => {
      if (!batchImportFormRef.value) return
      
      try {
        await batchImportFormRef.value.validate()
        
        importing.value = true
        // 准备发送的数据
        const importData = {
          data: batchImport.data.trim(),
          mailType: batchImport.mailType
        }
        
        // 如果WebSocket连接成功，则使用WebSocket导入
        if (store.state.websocketConnected) {
          // 使用导入的WebSocketService
          WebSocketService.importEmails(importData)
          ElMessage.info('正在处理导入请求，请稍候...')
          
          // 设置监听导入结果的回调
          const handleImportResult = (result) => {
            if (result && result.success > 0) {
              ElMessage.success(`成功导入 ${result.success} 个邮箱`)
            } else {
              ElMessage.warning('没有成功导入任何邮箱，请检查导入数据')
            }
            // 刷新邮箱列表
            refreshEmails()
            // 移除监听器
            WebSocketService.offMessage('import_result', handleImportResult)
          }
          
          // 添加一次性监听器
          WebSocketService.onMessage('import_result', handleImportResult)
          
          // 设置超时
          setTimeout(() => {
            WebSocketService.offMessage('import_result', handleImportResult)
          }, 30000) // 30秒超时
        } else {
          // 否则使用API导入
          const result = await store.dispatch('emails/importEmails', importData)
          if (result && result.success > 0) {
            ElMessage.success(`成功导入 ${result.success} 个邮箱`)
          } else {
            ElMessage.warning('没有成功导入任何邮箱，请检查导入数据')
          }
          // 刷新邮箱列表
          refreshEmails()
        }
        
        addEmailDialogVisible.value = false
        resetBatchImportForm()
      } catch (error) {
        console.error('导入邮箱失败:', error)
        ElMessage.error('导入邮箱失败: ' + (error.message || '未知错误'))
      } finally {
        importing.value = false
      }
    }
    
    const resetAddEmailForm = () => {
      newEmail.email = ''
      newEmail.password = ''
      newEmail.clientId = ''
      newEmail.refreshToken = ''
      newEmail.mailType = 'outlook'
    }
    
    const resetBatchImportForm = () => {
      batchImport.data = ''
      batchImport.mailType = 'outlook'
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
    
    // 获取邮箱类型显示名称
    const getMailTypeName = (type) => {
      const types = {
        outlook: 'Outlook',
        gmail: 'Gmail',
        qq: 'QQ邮箱',
        '163': '163邮箱',
        'custom': '自定义'
      }
      return types[type] || type
    }
    
    // 根据邮箱类型返回标签颜色
    const getMailTypeColor = (type) => {
      const colors = {
        outlook: 'primary',
        gmail: 'success',
        qq: 'warning',
        '163': 'danger',
        'custom': 'info'
      }
      return colors[type] || 'info'
    }
    
    const togglePasswordVisibility = async (row) => {
      // 如果已经显示密码，则隐藏
      if (row.showPassword) {
        row.showPassword = false;
        return;
      }

      // 否则，从后端获取密码
      if (!row.password || row.password === '******') {
        row.passwordLoading = true;
        try {
          const response = await store.dispatch('emails/getEmailPassword', row.id);
          if (response && response.password) {
            row.password = response.password;
          }
        } catch (error) {
          console.error('获取密码失败:', error);
          ElMessage.error('获取密码失败: ' + (error.message || '未知错误'));
        } finally {
          row.passwordLoading = false;
        }
      }
      
      // 显示密码
      row.showPassword = true;
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
      addEmailActiveTab,
      mailContentDialogVisible,
      mailListDialogVisible,
      addingEmail,
      importing,
      
      // 数据
      emails,
      currentEmail,
      mailRecords,
      hasSelectedEmails,
      newEmail,
      batchImport,
      batchImportFormRef,
      batchImportRules,
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
      handleAddOrImport,
      handleImport,
      formatDate,
      isEmailProcessing,
      getEmailActionText,
      getMailTypeName,
      getMailTypeColor,
      togglePasswordVisibility,
      
      // 图标
      Delete,
      Refresh,
      Plus,
      Download,
      Document,
      Message,
      View,
      Hide
    }
  }
}
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 160px); /* 减去header和footer的高度 */
}

.emails-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.email-list-card {
  margin-bottom: 20px;
  transition: all var(--transition-normal);
}

.card-header {
  width: 100%;
}

.page-title {
  font-size: 1.5rem;
  color: var(--primary-color);
  margin: 0;
  position: relative;
  display: inline-block;
}

.page-title::after {
  content: '';
  position: absolute;
  bottom: -5px;
  left: 0;
  width: 40px;
  height: 3px;
  background-color: var(--primary-color);
  border-radius: 999px;
}

.email-table {
  border-radius: var(--border-radius);
  overflow: hidden;
}

.mail-type-tag {
  font-weight: 500;
}

.password-field {
  width: 100%;
}

.password-text {
  font-family: monospace;
}

.password-toggle-btn:hover {
  transform: scale(1.1);
}

.time-field {
  color: var(--secondary-text-color);
  font-size: 0.9rem;
}

.progress-wrapper {
  padding: 4px 0;
}

.progress-message {
  font-size: 0.8rem;
  margin-top: 4px;
}

.action-buttons {
  justify-content: flex-start;
}

.action-btn {
  transition: transform var(--transition-fast);
}

.action-btn:hover:not(:disabled) {
  transform: translateY(-2px);
}

.mail-dialog-header {
  padding: 0 0 10px 0;
  border-bottom: 1px solid var(--border-color-light);
}

.email-title {
  font-size: 1.2rem;
  margin: 0;
}

.mail-list-table {
  border-radius: var(--border-radius);
  overflow: hidden;
}

.mail-detail {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.mail-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.info-item {
  width: 100%;
}

.label {
  font-weight: 500;
  margin-right: 10px;
}

.mail-content {
  max-height: 400px;
  overflow-y: auto;
}

.content-text {
  font-family: inherit;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .actions {
    width: 100%;
    justify-content: flex-start;
  }
  
  .action-buttons {
    flex-wrap: wrap;
    gap: 5px;
  }
}

@media (max-width: 576px) {
  .email-table {
    font-size: 14px;
  }
  
  .password-toggle-btn {
    padding: 2px;
  }
  
  .action-btn {
    padding: 4px 8px;
  }
}
</style> 