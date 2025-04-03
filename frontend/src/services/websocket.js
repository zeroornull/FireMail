// 添加WebSocket消息类型的常量
const MessageTypes = {
  // 认证相关
  AUTHENTICATE: 'authenticate', 
  AUTH_RESULT: 'auth_result',
  CONNECTION_ESTABLISHED: 'connection_established',
  
  // 邮箱操作
  GET_ALL_EMAILS: 'get_all_emails',    // 获取所有邮箱
  CHECK_EMAILS: 'check_emails',         // 批量检查邮箱
  DELETE_EMAILS: 'delete_emails',       // 批量删除邮箱
  ADD_EMAIL: 'add_email',               // 添加单个邮箱
  GET_MAIL_RECORDS: 'get_mail_records', // 获取邮件记录
  
  // 批量导入
  IMPORT_EMAILS: 'import_emails',       // 批量导入邮箱
  
  // 响应消息
  EMAILS_LIST: 'emails_list',          // 邮箱列表
  CHECK_PROGRESS: 'check_progress',    // 检查进度
  EMAILS_IMPORTED: 'emails_imported',  // 邮箱已导入
  EMAILS_DELETED: 'emails_deleted',    // 邮箱已删除
  EMAIL_ADDED: 'email_added',          // 邮箱已添加
  MAIL_RECORDS: 'mail_records',        // 邮件记录
  
  // 通知消息
  INFO: 'info',                        // 信息通知
  SUCCESS: 'success',                  // 成功通知
  WARNING: 'warning',                  // 警告通知
  ERROR: 'error'                       // 错误通知
};

class WebSocketService {
  constructor() {
    this.socket = null;
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectTimeoutId = null;
    this.baseDelay = 1000; // 1秒
    this.messageHandlers = {};
    this.connectHandlers = [];
    this.disconnectHandlers = [];
    
    this.url = this.getWebSocketUrl();
    console.log(`WebSocket服务URL: ${this.url}`);
  }

  getWebSocketUrl() {
    // 优先使用window.WS_URL (通过env-config.js设置)
    if (window.WS_URL) {
      console.log('使用env-config中的WS_URL:', window.WS_URL);
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      // 如果WS_URL是相对路径，则添加主机名
      if (window.WS_URL.startsWith('/')) {
        return `${protocol}//${window.location.host}${window.WS_URL}`;
      }
      return window.WS_URL;
    }
    
    // 使用Vite环境变量或动态计算
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host = import.meta.env.VITE_WS_HOST || window.location.hostname;
    const port = import.meta.env.VITE_WS_PORT || (window.location.port ? window.location.port : '8765');
    
    // 使用与当前页面相同的端口，或默认端口
    console.log(`构建WebSocket连接URL: protocol=${protocol}, host=${host}, port=${port}`);
    
    if (port === window.location.port) {
      console.log('使用与当前页面相同的端口，通过路径连接WebSocket');
      return `${protocol}://${host}/ws`;
    } else {
      console.log('使用指定端口连接WebSocket');
      return `${protocol}://${host}:${port}`;
    }
  }

  connect() {
    // 如果已经连接或正在连接中，不要重复连接
    if (this.socket && (this.socket.readyState === WebSocket.CONNECTING || this.socket.readyState === WebSocket.OPEN)) {
      console.log('WebSocket已经连接或正在连接中');
      return;
    }

    // 从localStorage获取token
    const token = localStorage.getItem('token');
    if (!token) {
      console.error('WebSocket连接失败: 未找到认证令牌');
      // 这是预期行为，未登录用户不应该连接WebSocket
      return;
    }

    try {
      console.log(`尝试连接WebSocket: ${this.url}`);
      this.socket = new WebSocket(this.url);

      this.socket.onopen = () => {
        console.log('WebSocket连接成功');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        
        // 连接成功后发送认证消息
        this.sendAuthMessage(token);
      };

      this.socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('WebSocket消息解析失败:', error);
        }
      };

      this.socket.onclose = (event) => {
        console.log(`WebSocket连接关闭: Code=${event.code}, Reason=${event.reason}`);
        this.isConnected = false;
        this.notifyDisconnect();
        
        // 自动重新连接，除非是正常关闭
        if (event.code !== 1000) {
          this.scheduleReconnect();
        }
      };

      this.socket.onerror = (error) => {
        console.error('WebSocket错误:', error);
        this.isConnected = false;
      };
    } catch (error) {
      console.error('创建WebSocket连接失败:', error);
    }
  }

  sendAuthMessage(token) {
    if (!this.isConnected) return;
    
    try {
      // 发送认证消息
      this.socket.send(JSON.stringify({
        type: MessageTypes.AUTHENTICATE,
        token
      }));
      console.log('已发送WebSocket认证消息');
    } catch (error) {
      console.error('发送WebSocket认证消息失败:', error);
    }
  }

  scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('达到最大重连次数，停止重连');
      return;
    }

    // 清除之前的重连计时器
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
    }

    // 指数退避重连
    const delay = this.baseDelay * Math.pow(2, this.reconnectAttempts);
    console.log(`将在${delay}毫秒后尝试重新连接 (尝试 ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`);
    
    this.reconnectTimeoutId = setTimeout(() => {
      this.reconnectAttempts++;
      this.connect();
    }, delay);
  }

  disconnect() {
    if (this.socket) {
      this.socket.close(1000, '正常关闭');
      this.socket = null;
      this.isConnected = false;
      console.log('WebSocket连接已手动关闭');
    }
    
    // 清除重连计时器
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }
  }

  send(type, data = {}) {
    if (!this.isConnected) {
      console.error('WebSocket未连接，无法发送消息');
      return false;
    }

    try {
      const message = JSON.stringify({
        type,
        ...data
      });
      this.socket.send(message);
      console.log(`已发送WebSocket消息: ${type}`, data);
      return true;
    } catch (error) {
      console.error('发送WebSocket消息失败:', error);
      return false;
    }
  }

  handleMessage(message) {
    const type = message.type || 'unknown';
    console.log(`接收到WebSocket消息: ${type}`, message);
    
    // 处理认证结果消息
    if (type === MessageTypes.AUTH_RESULT) {
      if (message.success) {
        console.log('WebSocket认证成功');
        this.notifyConnect();
      } else {
        console.error('WebSocket认证失败:', message.error);
        this.disconnect();
      }
      return;
    }
    
    // 处理连接建立消息
    if (type === MessageTypes.CONNECTION_ESTABLISHED) {
      this.notifyConnect();
      return;
    }
    
    // 调用对应类型的处理函数
    const handlers = this.messageHandlers[type] || [];
    handlers.forEach(handler => {
      try {
        handler(message);
      } catch (error) {
        console.error(`处理"${type}"类型的消息时出错:`, error);
      }
    });
  }

  onMessage(type, handler) {
    if (!this.messageHandlers[type]) {
      this.messageHandlers[type] = [];
    }
    this.messageHandlers[type].push(handler);
  }

  offMessage(type, handler) {
    if (!this.messageHandlers[type]) return;
    
    if (handler) {
      // 移除特定处理函数
      this.messageHandlers[type] = this.messageHandlers[type].filter(h => h !== handler);
    } else {
      // 移除该类型的所有处理函数
      delete this.messageHandlers[type];
    }
  }

  onConnect(handler) {
    this.connectHandlers.push(handler);
    // 如果已经连接，立即调用
    if (this.isConnected) {
      handler();
    }
  }

  offConnect(handler) {
    this.connectHandlers = this.connectHandlers.filter(h => h !== handler);
  }

  onDisconnect(handler) {
    this.disconnectHandlers.push(handler);
  }

  offDisconnect(handler) {
    this.disconnectHandlers = this.disconnectHandlers.filter(h => h !== handler);
  }

  notifyConnect() {
    this.connectHandlers.forEach(handler => {
      try {
        handler();
      } catch (error) {
        console.error('执行连接回调时出错:', error);
      }
    });
  }

  notifyDisconnect() {
    this.disconnectHandlers.forEach(handler => {
      try {
        handler();
      } catch (error) {
        console.error('执行断开连接回调时出错:', error);
      }
    });
  }

  // 添加特定的邮箱相关消息发送方法
  getEmails() {
    return this.send(MessageTypes.GET_ALL_EMAILS);
  }

  checkEmails(emailIds) {
    return this.send(MessageTypes.CHECK_EMAILS, { email_ids: emailIds });
  }

  deleteEmails(emailIds) {
    return this.send(MessageTypes.DELETE_EMAILS, { email_ids: emailIds });
  }

  addEmail(email, password, clientId, refreshToken) {
    return this.send(MessageTypes.ADD_EMAIL, {
      email,
      password,
      client_id: clientId,
      refresh_token: refreshToken
    });
  }

  getMailRecords(emailId) {
    return this.send(MessageTypes.GET_MAIL_RECORDS, { email_id: emailId });
  }

  importEmails(data) {
    return this.send(MessageTypes.IMPORT_EMAILS, { data });
  }
}

// 单例模式
export default new WebSocketService(); 