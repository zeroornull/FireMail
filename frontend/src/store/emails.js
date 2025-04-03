import { defineStore } from 'pinia';
import api from '@/services/api';
import websocket from '@/services/websocket';

export const useEmailsStore = defineStore('emails', {
  state: () => ({
    emails: [],
    loading: false,
    error: null,
    selectedEmails: [],
    processingEmails: {},
    currentMailRecords: [],
    currentEmailId: null
  }),
  
  getters: {
    getEmailById: (state) => (id) => {
      return state.emails.find(email => email.id === id);
    },
    
    getProcessingStatus: (state) => (id) => {
      return state.processingEmails[id] || null;
    },
    
    hasSelectedEmails: (state) => {
      return state.selectedEmails.length > 0;
    },
    
    selectedEmailsCount: (state) => {
      return state.selectedEmails.length;
    },
    
    isAllSelected: (state) => {
      return state.emails.length > 0 && state.selectedEmails.length === state.emails.length;
    }
  },
  
  actions: {
    // 初始化WebSocket事件监听
    initWebSocketListeners() {
      // 邮箱列表更新
      websocket.onMessage('emails_list', (data) => {
        this.emails = data.data || [];
      });
      
      // 新增邮箱
      websocket.onMessage('email_added', () => {
        this.fetchEmails();
      });
      
      // 删除邮箱
      websocket.onMessage('emails_deleted', (data) => {
        if (data.email_ids) {
          this.emails = this.emails.filter(email => !data.email_ids.includes(email.id));
          // 更新已选邮箱
          this.selectedEmails = this.selectedEmails.filter(id => !data.email_ids.includes(id));
        }
      });
      
      // 邮箱导入
      websocket.onMessage('emails_imported', () => {
        this.fetchEmails();
      });
      
      // 处理进度更新
      websocket.onMessage('check_progress', (data) => {
        const { email_id, progress, message } = data;
        this.processingEmails[email_id] = { progress, message };
        
        // 进度完成后刷新邮箱列表
        if (progress === 100) {
          // 延迟刷新，确保服务器已完成处理
          setTimeout(() => {
            this.fetchEmails();
            // 如果正在查看此邮箱的邮件，也刷新邮件列表
            if (this.currentEmailId === email_id) {
              this.fetchMailRecords(email_id);
            }
          }, 1000);
        }
      });
      
      // 邮件记录
      websocket.onMessage('mail_records', (data) => {
        if (data.email_id === this.currentEmailId) {
          this.currentMailRecords = data.data || [];
        }
      });
      
      // 错误处理
      websocket.onMessage('error', (data) => {
        this.error = data.message;
      });
      
      // 连接成功时获取邮箱列表
      websocket.onConnect(() => {
        this.fetchEmails();
      });
    },
    
    // 通过API获取所有邮箱
    async fetchEmailsAPI() {
      this.loading = true;
      this.error = null;
      
      try {
        const response = await api.emails.getAll();
        this.emails = response;
      } catch (error) {
        this.error = '获取邮箱列表失败';
        console.error(error);
      } finally {
        this.loading = false;
      }
    },
    
    // 通过WebSocket获取所有邮箱
    fetchEmails() {
      if (!websocket.isConnected) {
        return this.fetchEmailsAPI();
      }
      
      this.loading = true;
      websocket.send('get_all_emails');
    },
    
    // 添加邮箱(API方式)
    async addEmailAPI(email, password, clientId, refreshToken) {
      this.loading = true;
      this.error = null;
      
      try {
        await api.emails.add(email, password, clientId, refreshToken);
        await this.fetchEmailsAPI();
        return true;
      } catch (error) {
        this.error = '添加邮箱失败';
        console.error(error);
        return false;
      } finally {
        this.loading = false;
      }
    },
    
    // 添加邮箱(WebSocket方式)
    addEmail(email, password, clientId, refreshToken) {
      if (!websocket.isConnected) {
        return this.addEmailAPI(email, password, clientId, refreshToken);
      }
      
      this.loading = true;
      websocket.send('add_email', { email, password, client_id: clientId, refresh_token: refreshToken });
      return true;
    },
    
    // 删除邮箱(API方式)
    async deleteEmailAPI(emailId) {
      this.loading = true;
      this.error = null;
      
      try {
        await api.emails.delete(emailId);
        // 从列表和选中列表中移除
        this.emails = this.emails.filter(email => email.id !== emailId);
        this.selectedEmails = this.selectedEmails.filter(id => id !== emailId);
        return true;
      } catch (error) {
        this.error = '删除邮箱失败';
        console.error(error);
        return false;
      } finally {
        this.loading = false;
      }
    },
    
    // 删除邮箱(WebSocket方式)
    deleteEmail(emailId) {
      if (!websocket.isConnected) {
        return this.deleteEmailAPI(emailId);
      }
      
      websocket.send('delete_emails', { email_ids: [emailId] });
      return true;
    },
    
    // 批量删除邮箱(API方式)
    async batchDeleteEmailsAPI(emailIds) {
      this.loading = true;
      this.error = null;
      
      try {
        await api.emails.batchDelete(emailIds);
        // 从列表和选中列表中移除
        this.emails = this.emails.filter(email => !emailIds.includes(email.id));
        this.selectedEmails = this.selectedEmails.filter(id => !emailIds.includes(id));
        return true;
      } catch (error) {
        this.error = '批量删除邮箱失败';
        console.error(error);
        return false;
      } finally {
        this.loading = false;
      }
    },
    
    // 批量删除邮箱(WebSocket方式)
    batchDeleteEmails(emailIds) {
      if (!websocket.isConnected) {
        return this.batchDeleteEmailsAPI(emailIds);
      }
      
      websocket.send('delete_emails', { email_ids: emailIds });
      return true;
    },
    
    // 删除选中的邮箱
    deleteSelectedEmails() {
      if (this.selectedEmails.length === 0) return false;
      
      const emailIds = [...this.selectedEmails];
      return this.batchDeleteEmails(emailIds);
    },
    
    // 检查邮箱邮件(API方式)
    async checkEmailAPI(emailId) {
      this.error = null;
      
      try {
        // 设置处理状态
        this.processingEmails[emailId] = { progress: 0, message: '开始检查...' };
        
        await api.emails.check(emailId);
        // 注意：这里不会获得实时进度，只有开始检查的状态
        
        return true;
      } catch (error) {
        this.error = '检查邮箱失败';
        this.processingEmails[emailId] = { progress: -1, message: '检查失败' };
        console.error(error);
        return false;
      }
    },
    
    // 检查邮箱邮件(WebSocket方式)
    checkEmail(emailId) {
      if (!websocket.isConnected) {
        return this.checkEmailAPI(emailId);
      }
      
      // 设置初始进度状态
      this.processingEmails[emailId] = { progress: 0, message: '开始检查...' };
      
      websocket.send('check_emails', { email_ids: [emailId] });
      return true;
    },
    
    // 批量检查邮箱邮件(API方式)
    async batchCheckEmailsAPI(emailIds) {
      this.error = null;
      
      try {
        // 设置处理状态
        emailIds.forEach(id => {
          this.processingEmails[id] = { progress: 0, message: '开始检查...' };
        });
        
        await api.emails.batchCheck(emailIds);
        // 注意：这里不会获得实时进度，只有开始检查的状态
        
        return true;
      } catch (error) {
        this.error = '批量检查邮箱失败';
        emailIds.forEach(id => {
          this.processingEmails[id] = { progress: -1, message: '检查失败' };
        });
        console.error(error);
        return false;
      }
    },
    
    // 批量检查邮箱邮件(WebSocket方式)
    batchCheckEmails(emailIds) {
      if (!websocket.isConnected) {
        return this.batchCheckEmailsAPI(emailIds);
      }
      
      // 设置初始进度状态
      emailIds.forEach(id => {
        this.processingEmails[id] = { progress: 0, message: '开始检查...' };
      });
      
      websocket.send('check_emails', { email_ids: emailIds });
      return true;
    },
    
    // 检查所有邮箱邮件
    checkAllEmails() {
      const emailIds = this.emails.map(email => email.id);
      return this.batchCheckEmails(emailIds);
    },
    
    // 检查选中的邮箱邮件
    checkSelectedEmails() {
      if (this.selectedEmails.length === 0) return false;
      
      const emailIds = [...this.selectedEmails];
      return this.batchCheckEmails(emailIds);
    },
    
    // 获取邮件记录(API方式)
    async fetchMailRecordsAPI(emailId) {
      this.loading = true;
      this.error = null;
      this.currentEmailId = emailId;
      
      try {
        const response = await api.emails.getMailRecords(emailId);
        this.currentMailRecords = response;
      } catch (error) {
        this.error = '获取邮件记录失败';
        console.error(error);
      } finally {
        this.loading = false;
      }
    },
    
    // 获取邮件记录(WebSocket方式)
    fetchMailRecords(emailId) {
      if (!websocket.isConnected) {
        return this.fetchMailRecordsAPI(emailId);
      }
      
      this.loading = true;
      this.currentEmailId = emailId;
      websocket.send('get_mail_records', { email_id: emailId });
    },
    
    // 批量导入邮箱(API方式)
    async importEmailsAPI(data) {
      this.loading = true;
      this.error = null;
      
      try {
        const response = await api.emails.import(data);
        await this.fetchEmailsAPI();
        return response;
      } catch (error) {
        this.error = '导入邮箱失败';
        console.error(error);
        return null;
      } finally {
        this.loading = false;
      }
    },
    
    // 批量导入邮箱(WebSocket方式)
    importEmails(data) {
      if (!websocket.isConnected) {
        return this.importEmailsAPI(data);
      }
      
      this.loading = true;
      websocket.send('import_emails', { data });
      return new Promise(resolve => {
        const handler = (message) => {
          if (message.type === 'import_result') {
            websocket.offMessage('import_result', handler);
            resolve(message);
          }
        };
        
        websocket.onMessage('import_result', handler);
        
        // 超时处理
        setTimeout(() => {
          websocket.offMessage('import_result', handler);
          resolve(null);
        }, 30000);
      });
    },
    
    // 选择/取消选择邮箱
    toggleSelectEmail(emailId) {
      const index = this.selectedEmails.indexOf(emailId);
      if (index === -1) {
        this.selectedEmails.push(emailId);
      } else {
        this.selectedEmails.splice(index, 1);
      }
    },
    
    // 选择所有邮箱
    selectAllEmails() {
      this.selectedEmails = this.emails.map(email => email.id);
    },
    
    // 取消选择所有邮箱
    deselectAllEmails() {
      this.selectedEmails = [];
    },
    
    // 切换全选/取消全选
    toggleSelectAll() {
      if (this.isAllSelected) {
        this.deselectAllEmails();
      } else {
        this.selectAllEmails();
      }
    },
    
    // 重置状态
    resetState() {
      this.emails = [];
      this.loading = false;
      this.error = null;
      this.selectedEmails = [];
      this.processingEmails = {};
      this.currentMailRecords = [];
      this.currentEmailId = null;
    }
  }
}); 