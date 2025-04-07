import requests
import imaplib
import email
from bs4 import BeautifulSoup
from email.header import decode_header
import chardet
import threading
import time
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("email_assistant.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('email_utils')

# Outlook邮箱处理类
class OutlookMailHandler:
    @staticmethod
    def get_new_access_token(refresh_token, client_id="9e5f94bc-e8a4-4e73-b8be-63364c29d753"):
        """刷新获取新的access_token"""
        tenant_id = 'common'
        refresh_token_data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': client_id,
        }

        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        try:
            response = requests.post(token_url, data=refresh_token_data)
            if response.status_code == 200:
                new_access_token = response.json().get('access_token')
                logger.info(f"Successfully obtained new access token")
                return new_access_token
            else:
                logger.error(f"Error refreshing token: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Exception during token refresh: {str(e)}")
            return None

    @staticmethod
    def generate_auth_string(user, token):
        """生成 OAuth2 授权字符串"""
        return f"user={user}\1auth=Bearer {token}\1\1"

    @staticmethod
    def fetch_emails(email_address, access_token, folder="INBOX", callback=None):
        """获取指定文件夹中的邮件"""
        mail_records = []
        try:
            mail = imaplib.IMAP4_SSL('outlook.office365.com')
            auth_string = OutlookMailHandler.generate_auth_string(email_address, access_token)
            mail.authenticate('XOAUTH2', lambda x: auth_string)
            
            status, messages = mail.select(folder)
            if status != "OK":
                logger.error(f"Failed to select folder {folder}: {status}")
                return mail_records
            
            status, message_ids = mail.search(None, 'ALL')
            if status != "OK":
                logger.error(f"Failed to search emails: {status}")
                return mail_records
            
            total_messages = len(message_ids[0].split())
            processed = 0
            
            for message_id in message_ids[0].split():
                try:
                    status, msg_data = mail.fetch(message_id, '(RFC822)')
                    if status != "OK":
                        logger.error(f"Failed to fetch email {message_id}: {status}")
                        continue
                    
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            subject = decode_mime_words(msg["subject"])
                            sender = decode_mime_words(msg["from"])
                            date_str = msg["date"]
                            
                            # 解析邮件内容
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    content_type = part.get_content_type()
                                    content_disposition = str(part.get("Content-Disposition"))
                                    
                                    if "attachment" not in content_disposition:
                                        if content_type == "text/plain":
                                            body += safe_decode(part.get_payload(decode=True))
                                        elif content_type == "text/html":
                                            html_content = safe_decode(part.get_payload(decode=True))
                                            body += strip_html(html_content)
                            else:
                                if msg.get_content_type() == "text/plain":
                                    body = safe_decode(msg.get_payload(decode=True))
                                elif msg.get_content_type() == "text/html":
                                    html_content = safe_decode(msg.get_payload(decode=True))
                                    body = strip_html(html_content)
                            
                            body = remove_extra_blank_lines(body)
                            
                            # 尝试转换日期字符串为日期时间对象
                            try:
                                received_time = email.utils.parsedate_to_datetime(date_str)
                            except:
                                received_time = datetime.now()
                            
                            mail_record = {
                                'subject': subject,
                                'sender': sender,
                                'received_time': received_time,
                                'content': body,
                                'folder': folder
                            }
                            
                            mail_records.append(mail_record)
                    
                    processed += 1
                    if callback:
                        # 报告进度
                        progress = int((processed / total_messages) * 100)
                        callback(progress, folder)
                        
                except Exception as e:
                    logger.error(f"Error processing email {message_id}: {str(e)}")
            
            mail.close()
            mail.logout()
            
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP authentication failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error fetching emails: {str(e)}")
        
        return mail_records

    @staticmethod
    def check_mail(email_info, db, progress_callback=None):
        """检查Outlook/Hotmail邮箱中的邮件并存储到数据库"""
        email_id = email_info['id']
        email_address = email_info['email']
        refresh_token = email_info['refresh_token']
        client_id = email_info['client_id']
        
        logger.info(f"开始检查Outlook邮箱: ID={email_id}, 邮箱={email_address}")
        
        # 报告初始进度
        if progress_callback:
            progress_callback(email_id, 0, "正在获取访问令牌...")
        
        # 获取新的访问令牌
        access_token = OutlookMailHandler.get_new_access_token(refresh_token, client_id)
        if not access_token:
            logger.error(f"邮箱{email_address}(ID={email_id})获取访问令牌失败")
            if progress_callback:
                progress_callback(email_id, -1, "获取访问令牌失败")
            return False
        
        # 更新令牌到数据库
        db.update_email_token(email_id, access_token)
        
        # 报告进度
        if progress_callback:
            progress_callback(email_id, 10, "开始获取邮件...")
        
        # 获取邮件
        def folder_progress_callback(progress, folder):
            msg = f"正在处理{folder}文件夹，进度{progress}%"
            # 将各文件夹的进度映射到总进度10-90%
            total_progress = 10 + int(progress * 0.8)
            if progress_callback:
                progress_callback(email_id, total_progress, msg)
        
        mail_records = OutlookMailHandler.fetch_emails(
            email_address, 
            access_token, 
            "INBOX", 
            folder_progress_callback
        )
        
        # 报告进度
        count = len(mail_records)
        if progress_callback:
            progress_callback(email_id, 90, f"获取到{count}封邮件，正在保存...")
        
        # 将邮件记录保存到数据库
        for record in mail_records:
            db.add_mail_record(
                email_id, 
                record['subject'], 
                record['sender'], 
                record['received_time'], 
                record['content']
            )
        
        # 更新最后检查时间
        db.update_check_time(email_id)
        
        # 报告完成
        if progress_callback:
            progress_callback(email_id, 100, f"完成，共处理{count}封邮件")
        
        logger.info(f"邮箱{email_address}(ID={email_id})检查完成，获取到{count}封邮件")
        return True

# 通用辅助函数
def decode_mime_words(s):
    """解码邮件标题"""
    if not s:
        return ""
    try:
        decoded_fragments = decode_header(s)
        return ''.join([str(t[0], t[1] or 'utf-8') if isinstance(t[0], bytes) else t[0] for t in decoded_fragments])
    except Exception as e:
        logger.error(f"Error decoding MIME words: {str(e)}")
        return s if isinstance(s, str) else str(s)

def strip_html(content):
    """去除 HTML 标签"""
    try:
        soup = BeautifulSoup(content, "html.parser")
        return soup.get_text()
    except Exception as e:
        logger.error(f"Error stripping HTML: {str(e)}")
        return content

def safe_decode(byte_content):
    """自动检测并解码字节数据"""
    if not byte_content:
        return ""
    try:
        result = chardet.detect(byte_content)
        encoding = result['encoding']
        if encoding is not None:
            return byte_content.decode(encoding)
        else:
            return byte_content.decode('utf-8', errors='ignore')
    except Exception as e:
        logger.error(f"Error decoding content: {str(e)}")
        return byte_content.decode('utf-8', errors='ignore')

def remove_extra_blank_lines(text):
    """去除多余空行"""
    if not text:
        return ""
    lines = text.splitlines()
    return "\n".join(filter(lambda line: line.strip(), lines))

# 邮件处理器工厂
class EmailHandlerFactory:
    @staticmethod
    def get_handler(mail_type):
        """根据邮箱类型返回对应的处理器"""
        if mail_type == 'outlook':
            return OutlookMailHandler
        else:
            logger.error(f"不支持的邮箱类型: {mail_type}")
            return None

# 邮件批量处理类
class EmailBatchProcessor:
    def __init__(self, db):
        self.db = db
        self.threads = {}  # 存储正在运行的线程
        self.stop_flags = {}  # 存储停止标志
        self.progress = {}  # 存储进度信息
    
    def is_email_being_processed(self, email_id):
        """检查邮箱是否正在处理中"""
        return email_id in self.threads and self.threads[email_id].is_alive()
    
    def stop_processing(self, email_id):
        """停止处理指定邮箱"""
        if email_id in self.stop_flags:
            self.stop_flags[email_id] = True
    
    def check_emails(self, email_ids, progress_callback=None):
        """批量检查邮箱"""
        for email_id in email_ids:
            if self.is_email_being_processed(email_id):
                logger.info(f"邮箱ID {email_id} 正在处理中，跳过")
                continue
            
            # 获取邮箱信息
            email_info = self.db.get_email_by_id(email_id)
            if not email_info:
                logger.error(f"邮箱ID {email_id} 不存在")
                continue
            
            # 初始化停止标志
            self.stop_flags[email_id] = False
            
            # 创建线程处理
            thread = threading.Thread(
                target=self._check_email_thread,
                args=(email_info, progress_callback)
            )
            thread.daemon = True
            self.threads[email_id] = thread
            thread.start()
    
    def _check_email_thread(self, email_info, progress_callback):
        """邮箱检查线程"""
        email_id = email_info['id']
        
        try:
            # 获取邮箱类型对应的处理器
            mail_type = email_info['mail_type'] if 'mail_type' in email_info else 'outlook'
            handler = EmailHandlerFactory.get_handler(mail_type)
            
            if not handler:
                if progress_callback:
                    progress_callback(email_id, -1, f"不支持的邮箱类型: {mail_type}")
                return
            
            # 处理邮箱
            handler.check_mail(email_info, self.db, progress_callback)
            
        except Exception as e:
            logger.error(f"检查邮箱 ID {email_id} 时出错: {str(e)}")
            if progress_callback:
                progress_callback(email_id, -1, f"处理出错: {str(e)}")
        finally:
            # 清理线程记录
            if email_id in self.threads:
                del self.threads[email_id]
            if email_id in self.stop_flags:
                del self.stop_flags[email_id] 