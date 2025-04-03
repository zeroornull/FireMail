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

def generate_auth_string(user, token):
    """生成 OAuth2 授权字符串"""
    return f"user={user}\1auth=Bearer {token}\1\1"

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

def fetch_emails(email_address, access_token, folder="INBOX", callback=None):
    """获取指定文件夹中的邮件"""
    mail_records = []
    try:
        mail = imaplib.IMAP4_SSL('outlook.office365.com')
        auth_string = generate_auth_string(email_address, access_token)
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

def check_mail(email_info, db, progress_callback=None):
    """检查邮箱中的邮件并存储到数据库"""
    email_id = email_info['id']
    email_address = email_info['email']
    refresh_token = email_info['refresh_token']
    client_id = email_info['client_id']
    
    logger.info(f"开始检查邮箱: ID={email_id}, 邮箱={email_address}")
    
    # 报告初始进度
    if progress_callback:
        progress_callback(email_id, 0, "正在获取访问令牌...")
    
    # 获取新的访问令牌
    access_token = get_new_access_token(refresh_token, client_id)
    if not access_token:
        logger.error(f"邮箱{email_address}(ID={email_id})获取访问令牌失败")
        if progress_callback:
            progress_callback(email_id, -1, "获取访问令牌失败")
        return False
    
    # 更新数据库中的访问令牌
    logger.info(f"邮箱{email_address}(ID={email_id})成功获取访问令牌")
    db.update_email_token(email_id, access_token)
    
    if progress_callback:
        progress_callback(email_id, 10, "开始检查邮箱文件夹...")
    
    folders = ["INBOX", "Junk"]  # 收件箱和垃圾邮件文件夹
    
    all_mail_records = []
    for folder_idx, folder in enumerate(folders):
        logger.info(f"检查邮箱{email_address}(ID={email_id})的{folder}文件夹")
        
        def update_progress(progress, current_folder):
            if progress_callback:
                # 调整总体进度：10% 初始化 + 80% 收取邮件(每个文件夹占比相等) + 10% 存储邮件
                folder_progress = 10 + (progress * 0.8 / len(folders)) + (folder_idx * 0.8 / len(folders) * 100)
                message = f"检查{current_folder}文件夹: {progress}%"
                progress_callback(email_id, int(folder_progress), message)
        
        try:
            mail_records = fetch_emails(email_address, access_token, folder, update_progress)
            logger.info(f"从邮箱{email_address}(ID={email_id})的{folder}文件夹收取了{len(mail_records)}封邮件")
            all_mail_records.extend(mail_records)
        except Exception as e:
            logger.error(f"检查邮箱{email_address}(ID={email_id})的{folder}文件夹时出错: {str(e)}")
            if progress_callback:
                progress_callback(email_id, -1, f"检查{folder}文件夹失败: {str(e)}")
            return False
    
    # 存储邮件记录到数据库
    if progress_callback:
        progress_callback(email_id, 90, f"正在保存{len(all_mail_records)}封邮件...")
    
    saved_count = 0
    for record in all_mail_records:
        try:
            db.add_mail_record(
                email_id, 
                record['subject'], 
                record['sender'], 
                record['received_time'], 
                record['content']
            )
            saved_count += 1
        except Exception as e:
            logger.error(f"保存邮件记录失败: {str(e)}, 邮箱ID={email_id}, 主题={record.get('subject', 'Unknown')}")
    
    # 更新最后检查时间
    db.update_check_time(email_id)
    
    logger.info(f"邮箱{email_address}(ID={email_id})检查完成，成功保存{saved_count}/{len(all_mail_records)}封邮件")
    
    if progress_callback:
        progress_callback(email_id, 100, f"完成: 发现{len(all_mail_records)}封邮件，保存{saved_count}封")
    
    return True

class EmailChecker(threading.Thread):
    """邮件检查线程类"""
    def __init__(self, email_info, db, progress_callback=None):
        threading.Thread.__init__(self)
        self.email_info = email_info
        self.db = db
        self.progress_callback = progress_callback
        self.daemon = True  # 设置为守护线程，主线程结束时自动结束
    
    def run(self):
        try:
            check_mail(self.email_info, self.db, self.progress_callback)
        except Exception as e:
            logger.error(f"Error in email checker thread: {str(e)}")
            if self.progress_callback:
                self.progress_callback(
                    self.email_info['id'], 
                    -1, 
                    f"Error: {str(e)}"
                )

class EmailBatchProcessor:
    """邮件批量处理器"""
    def __init__(self, db, max_threads=5):
        self.db = db
        self.max_threads = max_threads
        self.active_threads = {}  # {email_id: thread}
        self.lock = threading.Lock()
        logger.info(f"邮件批量处理器初始化，最大线程数：{max_threads}")
    
    def check_emails(self, email_ids=None, progress_callback=None):
        """批量检查多个邮箱的邮件"""
        with self.lock:
            # 清理已完成的线程
            self._cleanup_threads()
            
            # 如果未指定邮箱ID，则获取所有邮箱
            if not email_ids:
                emails = self.db.get_all_emails()
                email_ids = [email['id'] for email in emails]
            
            # 记录将要处理的邮箱
            logger.info(f"开始处理 {len(email_ids)} 个邮箱")
            
            # 创建邮件检查线程
            for email_id in email_ids:
                # 检查是否已经有线程在处理
                if email_id in self.active_threads and self.active_threads[email_id].is_alive():
                    logger.warning(f"邮箱 ID {email_id} 正在被处理，跳过")
                    continue
                
                # 获取邮箱信息
                email_info = self.db.get_email_by_id(email_id)
                if not email_info:
                    logger.error(f"无法找到邮箱 ID {email_id}")
                    continue
                
                # 等待，直到线程数低于最大限制
                while len([t for t in self.active_threads.values() if t.is_alive()]) >= self.max_threads:
                    time.sleep(0.5)
                    self._cleanup_threads()
                
                # 创建并启动新线程
                thread = EmailChecker(email_info, self.db, progress_callback)
                thread.start()
                
                # 记录活动线程
                self.active_threads[email_id] = thread
                logger.info(f"开始处理邮箱 ID {email_id}: {email_info['email']}")
    
    def _cleanup_threads(self):
        """清理已完成的线程"""
        for email_id in list(self.active_threads.keys()):
            if not self.active_threads[email_id].is_alive():
                logger.info(f"邮箱 ID {email_id} 处理完成，清理线程")
                del self.active_threads[email_id]
    
    def wait_completion(self):
        """等待所有邮件检查线程完成"""
        logger.info("等待所有邮件检查线程完成")
        for thread in list(self.active_threads.values()):
            if thread.is_alive():
                thread.join()
        logger.info("所有邮件检查线程已完成")
    
    def is_email_being_processed(self, email_id):
        """检查指定邮箱是否正在处理中"""
        return email_id in self.active_threads and self.active_threads[email_id].is_alive()
    
    def stop_processing(self, email_id=None):
        """停止处理指定邮箱，如果未指定则停止所有"""
        with self.lock:
            if email_id is not None:
                if email_id in self.active_threads:
                    logger.info(f"停止处理邮箱 ID {email_id}")
                    # 线程是守护线程，会自动结束，只需从字典中移除
                    del self.active_threads[email_id]
            else:
                # 停止所有邮箱处理
                logger.info("停止处理所有邮箱")
                self.active_threads.clear() 