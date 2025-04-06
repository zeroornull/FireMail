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
        
        # 检查mail_records表是否存在去重索引，如果不存在则添加
        try:
            cursor = self.conn.execute("PRAGMA index_list(mail_records)")
            index_exists = False
            for index in cursor.fetchall():
                if index['name'] == 'idx_mail_records_unique':
                    index_exists = True
                    break
            
            if not index_exists:
                logger.info("为mail_records表添加去重索引")
                self.conn.execute('''
                CREATE UNIQUE INDEX idx_mail_records_unique 
                ON mail_records(email_id, sender, subject, received_time)
                ''')
                self.conn.commit()
                logger.info("去重索引添加完成")
        except Exception as e:
            logger.error(f"添加去重索引时出错: {str(e)}")
        
        # 创建系统配置表
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 检查emails表是否缺少user_id列，如果缺少则添加
        cursor = self.conn.execute("PRAGMA table_info(emails)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'user_id' not in columns:
            logger.info("添加user_id列到emails表")
            self.conn.execute("ALTER TABLE emails ADD COLUMN user_id INTEGER")
            self.conn.commit()
        
        # 初始化系统配置
        self._init_system_config()
        
        self.conn.commit()
        logger.info("数据库表结构初始化完成")
    
    def _init_system_config(self):
        """初始化系统配置"""
        # 检查是否存在注册配置，默认为开启
        cursor = self.conn.execute("SELECT value FROM system_config WHERE key = 'allow_register'")
        result = cursor.fetchone()
        if not result:
            logger.info("初始化系统配置: 默认允许注册")
            self.conn.execute(
                "INSERT INTO system_config (key, value) VALUES ('allow_register', 'true')"
            )
            self.conn.commit()
        else:
            # 确保注册功能默认开启，防止旧数据导致无法注册
            if result['value'] != 'true':
                logger.info("重置系统配置: 默认允许注册")
                self.conn.execute(
                    "UPDATE system_config SET value = 'true' WHERE key = 'allow_register'"
                )
                self.conn.commit()
    
    def get_system_config(self, key):
        """获取系统配置"""
        try:
            cursor = self.conn.execute("SELECT value FROM system_config WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result['value'] if result else None
        except Exception as e:
            logger.error(f"获取系统配置失败: key={key}, 错误: {str(e)}")
            return None
    
    def set_system_config(self, key, value):
        """设置系统配置"""
        try:
            self.conn.execute(
                "INSERT OR REPLACE INTO system_config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (key, value)
            )
            self.conn.commit()
            logger.info(f"系统配置已更新: {key} = {value}")
            return True
        except Exception as e:
            logger.error(f"更新系统配置失败: {key} = {value}, 错误: {str(e)}")
            return False
    
    def is_registration_allowed(self):
        """检查是否允许注册"""
        try:
            allow_register = self.get_system_config('allow_register')
            # 如果配置不存在，默认允许注册
            if allow_register is None:
                logger.info("注册配置不存在，设置为默认允许")
                success = self.set_system_config('allow_register', 'true')
                if not success:
                    logger.warning("设置默认注册配置失败，仍然默认允许注册")
                return True
            
            logger.info(f"读取到注册配置: {allow_register}")
            return allow_register.lower() == 'true'
        except Exception as e:
            # 出现异常时，确保默认允许注册
            logger.error(f"检查注册状态时出错: {str(e)}，默认允许注册")
            return True
    
    def toggle_registration(self, allow):
        """开启或关闭注册功能"""
        value = 'true' if allow else 'false'
        logger.info(f"正在{'开启' if allow else '关闭'}注册功能")
        result = self.set_system_config('allow_register', value)
        if result:
            logger.info(f"注册功能已成功切换为: {value}")
        else:
            logger.error(f"切换注册功能失败，目标状态: {value}")
        return result
    
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
            # 先检查邮件是否已存在
            cursor = self.conn.execute(
                "SELECT id FROM mail_records WHERE email_id = ? AND sender = ? AND subject = ? AND received_time = ?",
                (email_id, sender, subject, received_time)
            )
            exists = cursor.fetchone() is not None
            
            if exists:
                logger.debug(f"邮件已存在，跳过: 邮箱ID={email_id}, 主题={subject}")
                return False  # 邮件已存在，返回False表示没有添加新记录
            
            # 邮件不存在，添加新记录
            self.conn.execute(
                "INSERT INTO mail_records (email_id, subject, sender, received_time, content) VALUES (?, ?, ?, ?, ?)",
                (email_id, subject, sender, received_time, content)
            )
            self.conn.commit()
            return True  # 添加了新记录，返回True
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