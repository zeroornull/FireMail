<template>
  <div class="register-container">
    <div class="register-box">
      <h1 class="title">注册</h1>
      
      <div v-if="error" class="alert alert-danger">
        {{ error }}
      </div>
      
      <form @submit.prevent="handleRegister" class="register-form">
        <div class="form-group">
          <label for="username">用户名</label>
          <input 
            type="text" 
            id="username" 
            v-model="username" 
            class="form-control" 
            placeholder="请输入用户名" 
            required 
            autofocus
          />
          <small class="form-text text-muted">用户名长度应为3-20个字符</small>
        </div>
        
        <div class="form-group">
          <label for="password">密码</label>
          <input 
            type="password" 
            id="password" 
            v-model="password" 
            class="form-control" 
            placeholder="请输入密码" 
            required
          />
          <small class="form-text text-muted">密码长度应至少为6个字符</small>
        </div>
        
        <div class="form-group">
          <label for="confirmPassword">确认密码</label>
          <input 
            type="password" 
            id="confirmPassword" 
            v-model="confirmPassword" 
            class="form-control" 
            placeholder="请再次输入密码" 
            required
          />
        </div>
        
        <div class="form-actions">
          <button type="submit" class="btn btn-primary btn-block" :disabled="loading || !formValid">
            <span v-if="loading">注册中...</span>
            <span v-else>注册</span>
          </button>
        </div>
      </form>
      
      <div class="register-footer">
        <p>已有账号? <router-link :to="{ name: 'login' }">登录</router-link></p>
      </div>
    </div>
  </div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

export default {
  name: 'RegisterView',
  data() {
    return {
      username: '',
      password: '',
      confirmPassword: '',
      loading: false,
      error: ''
    };
  },
  computed: {
    ...mapGetters('auth', ['registrationEnabled']),
    formValid() {
      return this.username.length >= 3 && 
             this.username.length <= 20 && 
             this.password.length >= 6 && 
             this.password === this.confirmPassword;
    }
  },
  methods: {
    ...mapActions('auth', ['register']),
    async handleRegister() {
      // 验证表单
      if (!this.formValid) {
        if (this.username.length < 3 || this.username.length > 20) {
          this.error = '用户名长度应为3-20个字符';
        } else if (this.password.length < 6) {
          this.error = '密码长度应至少为6个字符';
        } else if (this.password !== this.confirmPassword) {
          this.error = '两次输入的密码不一致';
        }
        return;
      }
      
      this.loading = true;
      this.error = '';
      
      try {
        // 检查是否允许注册
        if (!this.registrationEnabled) {
          throw new Error('系统当前不允许注册新用户，请联系管理员');
        }
        
        await this.register({
          username: this.username,
          password: this.password
        });
        
        // 注册成功后跳转到登录页
        this.$router.push({ 
          name: 'login',
          params: { registrationSuccess: true }
        });
      } catch (error) {
        this.error = error.response?.data?.message || error.message || '注册失败，请稍后再试';
      } finally {
        this.loading = false;
      }
    }
  },
  mounted() {
    // 检查是否允许注册
    if (!this.registrationEnabled) {
      this.error = '系统当前不允许注册新用户，请联系管理员';
    }
  }
};
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 80px);
  padding: 20px;
}

.register-box {
  width: 100%;
  max-width: 400px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  padding: 30px;
}

.title {
  text-align: center;
  margin-bottom: 24px;
  color: #333;
  font-weight: 600;
}

.register-form {
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
}

.form-control {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
  transition: border-color 0.3s;
}

.form-control:focus {
  border-color: #42b983;
  outline: none;
}

.form-text {
  display: block;
  margin-top: 5px;
  font-size: 12px;
}

.text-muted {
  color: #6c757d;
}

.btn {
  display: inline-block;
  padding: 10px 20px;
  font-size: 16px;
  font-weight: 500;
  text-align: center;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s, opacity 0.3s;
  border: none;
}

.btn-primary {
  background-color: #42b983;
  color: white;
}

.btn-primary:hover {
  background-color: #3aa876;
}

.btn-block {
  display: block;
  width: 100%;
}

.btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.form-actions {
  margin-top: 30px;
}

.register-footer {
  text-align: center;
  margin-top: 20px;
  color: #666;
}

.register-footer a {
  color: #42b983;
  text-decoration: none;
}

.register-footer a:hover {
  text-decoration: underline;
}

.alert {
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 20px;
}

.alert-danger {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}
</style> 