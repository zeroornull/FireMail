<template>
  <div class="about-container">
    <h1 class="page-title">关于花火邮箱助手</h1>
    
    <el-card class="about-card">
      <div class="about-content">
        <h2>项目介绍</h2>
        <p>花火邮箱助手是一款专为Microsoft邮箱设计的批量收件工具，旨在提供简单高效的邮件管理解决方案。</p>
        <p>通过实时的WebSocket通信，多线程并行处理，用户可以轻松管理多个邮箱账户，批量收取邮件。</p>
        
        <h2>功能特点</h2>
        <ul>
          <li><strong>批量导入：</strong> 支持批量导入邮箱账号，格式为"邮箱----密码----客户端ID----RefreshToken"</li>
          <li><strong>批量管理：</strong> 支持多选、全选邮箱，进行批量删除、收信，允许单个邮箱手动收信</li>
          <li><strong>WebSocket支持：</strong> 实时通信，及时反馈处理进度和结果</li>
          <li><strong>多线程处理：</strong> 提高邮件收取效率，支持并行处理多个邮箱</li>
          <li><strong>简洁界面：</strong> 简约现代的用户界面，操作简单直观</li>
          <li><strong>跨平台支持：</strong> 支持Windows和Linux平台，可打包为Docker容器部署</li>
        </ul>
        
        <h2>技术栈</h2>
        <ul>
          <li><strong>后端：</strong> Python 3.13, Flask, SQLite, WebSocket</li>
          <li><strong>前端：</strong> Vue 3, Vite, Element Plus</li>
          <li><strong>其他：</strong> OAuth 2.0, IMAP</li>
        </ul>
        
        <h2>版本信息</h2>
        <ul>
          <li><strong>当前版本：</strong> v1.0.0</li>
          <li><strong>更新日期：</strong> {{ new Date().toLocaleDateString() }}</li>
        </ul>
        
        <h2>注意事项</h2>
        <ul>
          <li>本工具仅用于方便用户管理自己的邮箱账户，请勿用于非法用途</li>
          <li>邮箱账号和密码等敏感信息仅存储在本地SQLite数据库中，请确保服务器安全</li>
          <li>由于Microsoft API限制，可能会有请求频率限制，请合理使用</li>
        </ul>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.about-container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 20px;
}

.page-title {
  font-size: 24px;
  margin-bottom: 20px;
  color: #409eff;
}

.about-card {
  margin-bottom: 20px;
}

.about-content {
  line-height: 1.6;
}

.about-content h2 {
  margin-top: 20px;
  margin-bottom: 10px;
  font-size: 1.5rem;
  color: #303133;
  border-bottom: 1px solid #ebeef5;
  padding-bottom: 10px;
}

.about-content p, .about-content ul {
  margin-bottom: 16px;
}

.about-content ul {
  padding-left: 20px;
}

.about-content li {
  margin-bottom: 8px;
}

@media (max-width: 768px) {
  .about-container {
    padding: 10px;
  }
}
</style>