<template>
  <div class="home-container">
    <div class="hero-section">
      <div class="hero-content">
        <h1 class="hero-title">花火邮箱助手</h1>
        <p class="hero-subtitle">简单易用的微软邮箱批量收件工具</p>
        <div class="hero-buttons">
          <el-button type="primary" size="large" @click="navigateToEmails">开始使用</el-button>
          <el-button size="large" @click="navigateToImport">批量导入</el-button>
        </div>
      </div>
    </div>
    
    <div class="features-section">
      <h2 class="section-title">功能特点</h2>
      <div class="features-grid">
        <div class="feature-card">
          <el-icon size="40" color="#409eff"><CircleCheck /></el-icon>
          <h3>批量导入邮箱</h3>
          <p>支持"邮箱----密码----客户端ID----RefreshToken"的批量导入格式，一行一个</p>
        </div>
        
        <div class="feature-card">
          <el-icon size="40" color="#409eff"><Management /></el-icon>
          <h3>邮箱批量管理</h3>
          <p>支持多选、全选邮箱，进行批量删除、收信，允许单个邮箱手动收信</p>
        </div>
        
        <div class="feature-card">
          <el-icon size="40" color="#409eff"><Connection /></el-icon>
          <h3>实时通信</h3>
          <p>WebSocket实时通信，及时获取操作进度和结果反馈</p>
        </div>
        
        <div class="feature-card">
          <el-icon size="40" color="#409eff"><Cpu /></el-icon>
          <h3>多线程支持</h3>
          <p>收件操作采用多线程处理，提高效率，支持多邮箱并行处理</p>
        </div>
      </div>
    </div>
    
    <div class="quick-start-section">
      <h2 class="section-title">快速开始</h2>
      <div class="steps-container">
        <div class="step-item">
          <div class="step-number">1</div>
          <div class="step-content">
            <h3>导入邮箱</h3>
            <p>在"批量导入"页面添加邮箱，格式为"邮箱----密码----客户端ID----RefreshToken"</p>
          </div>
        </div>
        
        <div class="step-item">
          <div class="step-number">2</div>
          <div class="step-content">
            <h3>管理邮箱</h3>
            <p>在"邮箱管理"页面查看所有导入的邮箱，可以进行单个或批量操作</p>
          </div>
        </div>
        
        <div class="step-item">
          <div class="step-number">3</div>
          <div class="step-content">
            <h3>收取邮件</h3>
            <p>点击"收信"按钮开始收取邮件，可以查看实时进度</p>
          </div>
        </div>
        
        <div class="step-item">
          <div class="step-number">4</div>
          <div class="step-content">
            <h3>查看邮件</h3>
            <p>点击邮箱查看已收取的所有邮件内容</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { CircleCheck, Management, Connection, Cpu } from '@element-plus/icons-vue'

const router = useRouter()

const navigateToEmails = () => {
  router.push('/emails')
}

const navigateToImport = () => {
  router.push('/import')
}
</script>

<style scoped>
.home-container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 20px;
}

.hero-section {
  background: linear-gradient(135deg, #409eff 0%, #53a8ff 100%);
  color: white;
  border-radius: 12px;
  padding: 60px 30px;
  margin-bottom: 40px;
  text-align: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.hero-title {
  font-size: 3rem;
  margin-bottom: 16px;
  font-weight: bold;
}

.hero-subtitle {
  font-size: 1.5rem;
  margin-bottom: 30px;
  opacity: 0.9;
}

.hero-buttons {
  display: flex;
  gap: 20px;
  justify-content: center;
}

.section-title {
  text-align: center;
  font-size: 2rem;
  margin-bottom: 40px;
  color: #303133;
}

.features-section {
  margin-bottom: 40px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 30px;
}

.feature-card {
  background-color: white;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  text-align: center;
  transition: transform 0.3s, box-shadow 0.3s;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.feature-card h3 {
  margin: 20px 0 10px;
  color: #303133;
}

.feature-card p {
  color: #606266;
}

.quick-start-section {
  margin-bottom: 40px;
}

.steps-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.step-item {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.step-number {
  background-color: #409eff;
  color: white;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  font-weight: bold;
  font-size: 1.2rem;
  flex-shrink: 0;
}

.step-content h3 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #303133;
}

.step-content p {
  margin: 0;
  color: #606266;
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 2rem;
  }
  
  .hero-subtitle {
    font-size: 1.2rem;
  }
  
  .hero-buttons {
    flex-direction: column;
    gap: 10px;
    align-items: center;
  }
}
</style> 