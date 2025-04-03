import axios from 'axios';

// 获取API基础URL
const getBaseUrl = () => {
  // 优先使用window.API_URL (通过env-config.js设置)
  if (window.API_URL) {
    return window.API_URL;
  }
  
  // 其次使用Vite环境变量
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  
  // 最后使用当前域名
  return window.location.origin + '/api';
};

// 创建axios实例
const api = axios.create({
  baseURL: getBaseUrl(),
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 输出API基础URL
console.log('API基础URL:', api.defaults.baseURL);

// 请求拦截器
api.interceptors.request.use(
  config => {
    console.log(`API请求: ${config.method.toUpperCase()} ${config.url}`);
    return config;
  },
  error => {
    console.error('API请求错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  response => {
    console.log(`API响应: ${response.config.url}`, response.data);
    return response;
  },
  error => {
    if (error.response) {
      console.error('API响应错误:', error.response.status, error.response.data);
      
      // 特殊处理401未授权错误
      if (error.response.status === 401) {
        console.log('用户未认证，跳转到登录页面');
        // 清除本地存储的令牌
        localStorage.removeItem('token');
        // 如果不在登录页面，重定向到登录页面
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
      
      // 特殊处理409冲突错误
      else if (error.response.status === 409) {
        console.log('资源冲突:', error.response.data);
      }
    } else if (error.request) {
      console.error('API请求未收到响应:', error.request);
      // 服务器未响应的处理
      const errorMessage = '无法连接到服务器，请检查后端服务是否启动';
      error.response = { data: { message: errorMessage } };
    } else {
      console.error('API请求错误:', error.message);
    }
    return Promise.reject(error);
  }
);

// 认证相关API
export const setAuthHeader = (token) => {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }
}

export const removeAuthHeader = () => {
  delete api.defaults.headers.common['Authorization'];
}

// 从localStorage读取token并设置
const token = localStorage.getItem('token');
if (token) {
  setAuthHeader(token);
}

// API方法
export default {
  // 认证相关
  login: (username, password) => {
    return api.post('/auth/login', { username, password });
  },
  
  logout: () => {
    return api.post('/auth/logout');
  },
  
  register: (username, password) => {
    return api.post('/auth/register', { username, password });
  },
  
  getCurrentUser: () => {
    return api.get('/auth/user');
  },
  
  changePassword: (oldPassword, newPassword) => {
    return api.post('/auth/change-password', { old_password: oldPassword, new_password: newPassword });
  },
  
  // 用户管理 (管理员)
  getAllUsers: () => {
    return api.get('/users');
  },
  
  createUser: (userData) => {
    return api.post('/users', userData);
  },
  
  deleteUser: (userId) => {
    return api.delete(`/users/${userId}`);
  },
  
  resetUserPassword: (userId, newPassword) => {
    return api.post(`/users/${userId}/reset-password`, { new_password: newPassword });
  },
  
  // 邮箱相关
  getAllEmails: () => {
    return api.get('/emails');
  },
  
  getEmailById: (id) => {
    return api.get(`/emails/${id}`);
  },
  
  addEmail: (email, password, clientId, refreshToken) => {
    return api.post('/emails', {
      email,
      password,
      client_id: clientId,
      refresh_token: refreshToken
    });
  },
  
  deleteEmail: (id) => {
    return api.delete(`/emails/${id}`);
  },
  
  batchDeleteEmails: (ids) => {
    return api.post('/emails/batch_delete', { email_ids: ids });
  },
  
  checkEmail: (id) => {
    return api.post(`/emails/${id}/check`);
  },
  
  batchCheckEmails: (ids) => {
    return api.post('/emails/batch_check', { email_ids: ids });
  },
  
  getMailRecords: (emailId) => {
    return api.get(`/emails/${emailId}/mail_records`);
  },
  
  importEmails: (data) => {
    return api.post('/emails/import', { data });
  },
  
  // 工具方法
  setAuthHeader,
  removeAuthHeader
} 