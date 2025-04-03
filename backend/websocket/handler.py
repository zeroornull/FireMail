import json
import asyncio
import logging
import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger('websocket_handler')

class WebSocketHandler:
    def __init__(self, host='0.0.0.0', port=8765):
        self.host = host
        self.port = port
        self.connections = set()
        self.email_processor = None
        self.db = None
    
    def set_dependencies(self, db, email_processor):
        """设置依赖的数据库和邮件处理器"""
        self.db = db
        self.email_processor = email_processor
    
    async def register(self, websocket):
        """注册新的WebSocket连接"""
        self.connections.add(websocket)
        logger.info(f"New client connected. Total connections: {len(self.connections)}")
    
    async def unregister(self, websocket):
        """注销WebSocket连接"""
        self.connections.remove(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.connections)}")
    
    async def broadcast(self, message):
        """向所有连接的客户端广播消息"""
        if not self.connections:
            return
        
        message_str = json.dumps(message)
        await asyncio.gather(
            *[connection.send(message_str) for connection in self.connections],
            return_exceptions=True
        )
    
    async def send_to_client(self, websocket, message):
        """发送消息给特定客户端"""
        await websocket.send(json.dumps(message))
    
    async def handle_message(self, websocket, message_str):
        """处理从客户端接收到的消息"""
        try:
            message = json.loads(message_str)
            action = message.get('action')
            
            if action == 'get_all_emails':
                await self.handle_get_all_emails(websocket)
            
            elif action == 'add_email':
                email = message.get('email')
                password = message.get('password')
                client_id = message.get('client_id')
                refresh_token = message.get('refresh_token')
                await self.handle_add_email(websocket, email, password, client_id, refresh_token)
            
            elif action == 'delete_emails':
                email_ids = message.get('email_ids', [])
                await self.handle_delete_emails(websocket, email_ids)
            
            elif action == 'check_emails':
                email_ids = message.get('email_ids', [])
                await self.handle_check_emails(websocket, email_ids)
            
            elif action == 'get_mail_records':
                email_id = message.get('email_id')
                await self.handle_get_mail_records(websocket, email_id)
            
            elif action == 'import_emails':
                data = message.get('data', '')
                await self.handle_import_emails(websocket, data)
            
            else:
                await self.send_to_client(websocket, {
                    'type': 'error',
                    'message': f'Unknown action: {action}'
                })
        
        except json.JSONDecodeError:
            await self.send_to_client(websocket, {
                'type': 'error',
                'message': 'Invalid JSON format'
            })
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            await self.send_to_client(websocket, {
                'type': 'error',
                'message': f'Error: {str(e)}'
            })
    
    async def handle_get_all_emails(self, websocket):
        """处理获取所有邮箱的请求"""
        emails = self.db.get_all_emails()
        # 转换为可序列化的字典列表
        emails_list = [dict(email) for email in emails]
        await self.send_to_client(websocket, {
            'type': 'emails_list',
            'data': emails_list
        })
    
    async def handle_add_email(self, websocket, email, password, client_id, refresh_token):
        """处理添加邮箱的请求"""
        if not all([email, password, client_id, refresh_token]):
            await self.send_to_client(websocket, {
                'type': 'error',
                'message': 'All fields are required'
            })
            return
        
        success = self.db.add_email(email, password, client_id, refresh_token)
        if success:
            await self.send_to_client(websocket, {
                'type': 'success',
                'message': f'Email {email} added successfully'
            })
            # 通知所有客户端更新
            await self.broadcast({
                'type': 'email_added',
                'message': f'New email added: {email}'
            })
        else:
            await self.send_to_client(websocket, {
                'type': 'error',
                'message': f'Email {email} already exists'
            })
    
    async def handle_delete_emails(self, websocket, email_ids):
        """处理删除邮箱的请求"""
        if not email_ids:
            await self.send_to_client(websocket, {
                'type': 'error',
                'message': 'No email IDs provided'
            })
            return
        
        # 获取正在处理的邮箱
        processing_ids = []
        for email_id in email_ids:
            if self.email_processor.is_email_being_processed(email_id):
                processing_ids.append(email_id)
        
        # 停止正在处理的邮箱
        for email_id in processing_ids:
            self.email_processor.stop_processing(email_id)
        
        # 删除邮箱
        self.db.delete_emails(email_ids)
        
        await self.send_to_client(websocket, {
            'type': 'success',
            'message': f'Deleted {len(email_ids)} emails'
        })
        
        # 通知所有客户端更新
        await self.broadcast({
            'type': 'emails_deleted',
            'email_ids': email_ids
        })
    
    async def handle_check_emails(self, websocket, email_ids):
        """处理检查邮件的请求"""
        if not email_ids:
            # 如果没有提供 ID，则获取所有邮箱
            emails = self.db.get_all_emails()
            email_ids = [email['id'] for email in emails]
        
        if not email_ids:
            await self.send_to_client(websocket, {
                'type': 'error',
                'message': 'No emails found'
            })
            return
        
        # 定义进度回调
        def progress_callback(email_id, progress, message):
            asyncio.run_coroutine_threadsafe(
                self.broadcast({
                    'type': 'check_progress',
                    'email_id': email_id,
                    'progress': progress,
                    'message': message
                }),
                asyncio.get_event_loop()
            )
        
        # 启动邮件检查线程
        self.email_processor.check_emails(email_ids, progress_callback)
        
        await self.send_to_client(websocket, {
            'type': 'info',
            'message': f'Started checking {len(email_ids)} emails'
        })
    
    async def handle_get_mail_records(self, websocket, email_id):
        """处理获取邮件记录的请求"""
        if not email_id:
            await self.send_to_client(websocket, {
                'type': 'error',
                'message': 'Email ID is required'
            })
            return
        
        mail_records = self.db.get_mail_records(email_id)
        mail_records_list = [dict(record) for record in mail_records]
        
        await self.send_to_client(websocket, {
            'type': 'mail_records',
            'email_id': email_id,
            'data': mail_records_list
        })
    
    async def handle_import_emails(self, websocket, data):
        """处理批量导入邮箱的请求"""
        if not data:
            await self.send_to_client(websocket, {
                'type': 'error',
                'message': 'No data provided'
            })
            return
        
        lines = data.strip().split('\n')
        success_count = 0
        failed_lines = []
        
        for line_number, line in enumerate(lines, 1):
            parts = line.strip().split('----')
            if len(parts) != 4:
                failed_lines.append((line_number, line, 'Invalid format'))
                continue
            
            email, password, client_id, refresh_token = parts
            if not all([email, password, client_id, refresh_token]):
                failed_lines.append((line_number, line, 'Missing required fields'))
                continue
            
            success = self.db.add_email(email, password, client_id, refresh_token)
            if success:
                success_count += 1
            else:
                failed_lines.append((line_number, line, 'Email already exists'))
        
        result = {
            'type': 'import_result',
            'total': len(lines),
            'success': success_count,
            'failed': len(failed_lines),
            'failed_details': [
                {'line': line_num, 'content': content, 'reason': reason}
                for line_num, content, reason in failed_lines
            ]
        }
        
        await self.send_to_client(websocket, result)
        
        if success_count > 0:
            # 通知所有客户端更新
            await self.broadcast({
                'type': 'emails_imported',
                'count': success_count
            })
    
    async def handle_client(self, websocket, path):
        """处理客户端连接"""
        await self.register(websocket)
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except ConnectionClosed:
            logger.info("Client connection closed")
        finally:
            await self.unregister(websocket)
    
    async def start_server(self):
        """启动WebSocket服务器"""
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()  # 运行直到被取消
    
    def run(self):
        """运行WebSocket服务器"""
        if not self.db or not self.email_processor:
            raise ValueError("Database and EmailProcessor must be set before running")
        
        asyncio.run(self.start_server()) 