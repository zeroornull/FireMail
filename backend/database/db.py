import sqlite3
import os
import threading
import logging
import hashlib
import secrets

# 配置日志
logger = logging.getLogger('database')

class Database:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Database, cls).__new__(cls)
                cls._instance.conn = None
                cls._instance.init_db()
            return cls._instance
    
    def init_db(self):
        """初始化数据库连接和表结构"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'huohuo_email.db')
        
        # 确保目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        logger.info(f"初始化数据库: {db_path}")
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        # 创建用户表
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建邮箱表 (添加user_id外键)
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            client_id TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            access_token TEXT,
            last_check_time TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, email)
        )
        ''')
        
        # 创建邮件记录表
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS mail_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id INTEGER NOT NULL,
            subject TEXT,
            sender TEXT,
            received_time TIMESTAMP,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (email_id) REFERENCES emails (id)
        )
        ''')
        
        # 检查是否需要创建默认管理员用户
        cursor = self.conn.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
        if cursor.fetchone()[0] == 0:
            self._create_default_admin()
        
        # 检查emails表是否缺少user_id列，如果缺少则添加
        cursor = self.conn.execute("PRAGMA table_info(emails)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'user_id' not in columns:
            logger.info("添加user_id列到emails表")
            self.conn.execute("ALTER TABLE emails ADD COLUMN user_id INTEGER")
            self.conn.commit()
        
        self.conn.commit()
        logger.info("数据库表结构初始化完成")
    
    def _create_default_admin(self):
        """创建默认管理员账号"""
        admin_username = "admin"
        admin_password = "admin123"
        
        salt = secrets.token_hex(16)
        password_hash = self._hash_password(admin_password, salt)
        
        try:
            self.conn.execute(
                "INSERT INTO users (username, password_hash, salt, is_admin) VALUES (?, ?, ?, 1)",
                (admin_username, password_hash, salt)
            )
            self.conn.commit()
            logger.info(f"创建默认管理员账号: {admin_username}")
        except sqlite3.IntegrityError:
            logger.warning(f"管理员账号 {admin_username} 已存在")
    
    def _hash_password(self, password, salt):
        """密码哈希"""
        return hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            100000
        ).hex()
    
    # 用户相关方法
    def authenticate_user(self, username, password):
        """验证用户凭据"""
        cursor = self.conn.execute(
            "SELECT id, username, password_hash, salt, is_admin FROM users WHERE username = ?",
            (username,)
        )
        user = cursor.fetchone()
        if not user:
            logger.warning(f"用户不存在: {username}")
            return None
        
        password_hash = self._hash_password(password, user['salt'])
        if password_hash != user['password_hash']:
            logger.warning(f"用户密码错误: {username}")
            return None
        
        return {'id': user['id'], 'username': user['username'], 'is_admin': user['is_admin']}
    
    def get_user_by_id(self, user_id):
        """根据ID获取用户信息"""
        cursor = self.conn.execute(
            "SELECT id, username, is_admin FROM users WHERE id = ?",
            (user_id,)
        )
        return cursor.fetchone()
    
    def create_user(self, username, password, is_admin=False):
        """创建新用户"""
        try:
            # 检查是否需要将此用户设置为管理员（如果是第一个注册的用户）
            if not is_admin:
                cursor = self.conn.execute("SELECT COUNT(*) FROM users")
                if cursor.fetchone()[0] == 0:
                    is_admin = True
                    logger.info(f"第一个注册的用户 {username} 将被设置为管理员")
            
            salt = secrets.token_hex(16)
            password_hash = self._hash_password(password, salt)
            
            self.conn.execute(
                "INSERT INTO users (username, password_hash, salt, is_admin) VALUES (?, ?, ?, ?)",
                (username, password_hash, salt, 1 if is_admin else 0)
            )
            self.conn.commit()
            logger.info(f"创建用户成功: {username}, 管理员权限: {is_admin}")
            return True, is_admin
        except sqlite3.IntegrityError:
            logger.warning(f"用户已存在: {username}")
            return False, False
    
    def update_user_password(self, user_id, new_password):
        """更新用户密码"""
        try:
            salt = secrets.token_hex(16)
            password_hash = self._hash_password(new_password, salt)
            
            self.conn.execute(
                "UPDATE users SET password_hash = ?, salt = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (password_hash, salt, user_id)
            )
            self.conn.commit()
            logger.info(f"用户ID {user_id} 密码更新成功")
            return True
        except Exception as e:
            logger.error(f"更新用户密码失败: {str(e)}")
            return False
    
    def delete_user(self, user_id):
        """删除用户"""
        try:
            # 先获取用户关联的所有邮箱
            cursor = self.conn.execute("SELECT id FROM emails WHERE user_id = ?", (user_id,))
            email_ids = [row['id'] for row in cursor.fetchall()]
            
            # 删除邮件记录
            if email_ids:
                placeholders = ','.join(['?'] * len(email_ids))
                self.conn.execute(f"DELETE FROM mail_records WHERE email_id IN ({placeholders})", email_ids)
            
            # 删除邮箱
            self.conn.execute("DELETE FROM emails WHERE user_id = ?", (user_id,))
            
            # 删除用户
            self.conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            self.conn.commit()
            logger.info(f"用户ID {user_id} 删除成功")
            return True
        except Exception as e:
            logger.error(f"删除用户失败: {str(e)}")
            return False
    
    def get_all_users(self):
        """获取所有用户"""
        cursor = self.conn.execute("SELECT id, username, is_admin, created_at FROM users ORDER BY created_at DESC")
        return cursor.fetchall()
    
    # 邮箱相关方法 (修改为包含user_id)
    def add_email(self, user_id, email, password, client_id, refresh_token):
        """添加新的邮箱账号"""
        try:
            logger.info(f"尝试添加邮箱: {email} (用户ID: {user_id})")
            cursor = self.conn.execute(
                "INSERT INTO emails (user_id, email, password, client_id, refresh_token) VALUES (?, ?, ?, ?, ?)",
                (user_id, email, password, client_id, refresh_token)
            )
            self.conn.commit()
            email_id = cursor.lastrowid
            logger.info(f"邮箱添加成功: {email}, ID: {email_id}")
            return email_id
        except sqlite3.IntegrityError:
            # 邮箱已存在
            logger.warning(f"邮箱已存在: {email}")
            return False
        except Exception as e:
            logger.error(f"添加邮箱失败: {email}, 错误: {str(e)}")
            return False
    
    def get_all_emails(self, user_id=None):
        """获取所有邮箱账号，可以按用户ID过滤"""
        logger.debug(f"获取所有邮箱账号 (用户ID: {user_id if user_id else 'all'})")
        if user_id:
            cursor = self.conn.execute(
                "SELECT * FROM emails WHERE user_id = ? ORDER BY created_at DESC", 
                (user_id,)
            )
        else:
            cursor = self.conn.execute("SELECT * FROM emails ORDER BY created_at DESC")
        return cursor.fetchall()
    
    def get_email_by_id(self, email_id, user_id=None):
        """根据ID获取邮箱账号，可以验证所有者"""
        logger.debug(f"获取邮箱 ID: {email_id}")
        if user_id:
            cursor = self.conn.execute(
                "SELECT * FROM emails WHERE id = ? AND user_id = ?", 
                (email_id, user_id)
            )
        else:
            cursor = self.conn.execute("SELECT * FROM emails WHERE id = ?", (email_id,))
        return cursor.fetchone()
    
    def update_email_token(self, email_id, access_token):
        """更新邮箱的访问令牌"""
        logger.debug(f"更新邮箱访问令牌, ID: {email_id}")
        self.conn.execute(
            "UPDATE emails SET access_token = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (access_token, email_id)
        )
        self.conn.commit()
    
    def update_check_time(self, email_id):
        """更新邮箱的最后检查时间"""
        logger.debug(f"更新邮箱最后检查时间, ID: {email_id}")
        self.conn.execute(
            "UPDATE emails SET last_check_time = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (email_id,)
        )
        self.conn.commit()
    
    def delete_email(self, email_id, user_id=None):
        """删除邮箱账号，可以验证所有者"""
        logger.info(f"删除邮箱账号, ID: {email_id}")
        # 构建SQL查询条件
        sql_where = "id = ?"
        params = [email_id]
        
        if user_id:
            sql_where += " AND user_id = ?"
            params.append(user_id)
        
        # 先删除相关的邮件记录
        self.conn.execute("DELETE FROM mail_records WHERE email_id = ?", (email_id,))
        
        # 再删除邮箱
        self.conn.execute(f"DELETE FROM emails WHERE {sql_where}", params)
        self.conn.commit()
    
    def delete_emails(self, email_ids, user_id=None):
        """批量删除邮箱账号，可以验证所有者"""
        if not email_ids:
            return
            
        logger.info(f"批量删除邮箱账号, IDs: {email_ids}")
        
        # 如果指定了用户ID，需要验证每个邮箱的所有者
        if user_id:
            # 获取该用户拥有的邮箱
            placeholders = ','.join(['?'] * len(email_ids))
            cursor = self.conn.execute(
                f"SELECT id FROM emails WHERE id IN ({placeholders}) AND user_id = ?",
                email_ids + [user_id]
            )
            valid_ids = [row['id'] for row in cursor.fetchall()]
            
            if not valid_ids:
                logger.warning(f"用户ID {user_id} 没有权限删除任何指定的邮箱")
                return
            
            email_ids = valid_ids
        
        placeholders = ','.join(['?'] * len(email_ids))
        # 先删除相关的邮件记录
        self.conn.execute(f"DELETE FROM mail_records WHERE email_id IN ({placeholders})", email_ids)
        # 再删除邮箱
        self.conn.execute(f"DELETE FROM emails WHERE id IN ({placeholders})", email_ids)
        self.conn.commit()
    
    def add_mail_record(self, email_id, subject, sender, received_time, content):
        """添加邮件记录"""
        logger.debug(f"添加邮件记录, 邮箱ID: {email_id}, 主题: {subject}")
        try:
            self.conn.execute(
                "INSERT INTO mail_records (email_id, subject, sender, received_time, content) VALUES (?, ?, ?, ?, ?)",
                (email_id, subject, sender, received_time, content)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"添加邮件记录失败: {str(e)}")
            return False
    
    def get_mail_records(self, email_id, user_id=None):
        """获取指定邮箱的所有邮件记录，可以验证所有者"""
        logger.debug(f"获取邮箱邮件记录, ID: {email_id}")
        
        # 如果指定了用户ID，先验证邮箱所有权
        if user_id:
            email = self.get_email_by_id(email_id, user_id)
            if not email:
                logger.warning(f"用户ID {user_id} 没有权限访问邮箱ID {email_id}")
                return []
        
        cursor = self.conn.execute(
            "SELECT * FROM mail_records WHERE email_id = ? ORDER BY received_time DESC", 
            (email_id,)
        )
        return cursor.fetchall()
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            logger.info("关闭数据库连接")
            self.conn.close()
            self.conn = None 