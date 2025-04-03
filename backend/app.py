import os
import sys
import logging
import threading
import argparse
import datetime
import jwt
from functools import wraps
from flask import Flask, send_from_directory, jsonify, request, Response, make_response
from flask_cors import CORS
from database.db import Database
from utils.email_utils import EmailBatchProcessor
from ws_server.handler import WebSocketHandler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("huohuo_email_assistant.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('huohuo-email-assistant')

# 确保数据目录存在
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(data_dir, exist_ok=True)

# 初始化Flask应用
app = Flask(__name__)
CORS(app, supports_credentials=True)  # 允许跨域请求和凭据

# JWT密钥
JWT_SECRET = os.environ.get('JWT_SECRET_KEY', 'huohuo_email_secret_key')
# 是否允许注册新用户
ALLOW_REGISTER = os.environ.get('ALLOW_REGISTER', 'false').lower() == 'true'

# 初始化数据库
db = Database()

# 初始化邮件处理器
email_processor = EmailBatchProcessor(db)

# 初始化WebSocket处理器
ws_handler = WebSocketHandler()
ws_handler.set_dependencies(db, email_processor)

# 用户认证装饰器
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # 从请求头或Cookie获取token
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
        elif request.cookies.get('token'):
            token = request.cookies.get('token')
        
        if not token:
            return jsonify({'error': '未认证，请先登录'}), 401
        
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            current_user = db.get_user_by_id(data['user_id'])
            if not current_user:
                return jsonify({'error': '无效的用户令牌'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': '令牌已过期，请重新登录'}), 401
        except Exception as e:
            logger.error(f"令牌验证失败: {str(e)}")
            return jsonify({'error': '无效的令牌'}), 401
        
        # 将当前用户信息添加到kwargs
        kwargs['current_user'] = current_user
        return f(*args, **kwargs)
    
    return decorated

# 管理员权限装饰器
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        current_user = kwargs.get('current_user')
        if not current_user or not current_user['is_admin']:
            return jsonify({'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    
    return decorated

# 认证相关API
@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    user = db.authenticate_user(username, password)
    if not user:
        return jsonify({'error': '用户名或密码错误'}), 401
    
    # 生成JWT令牌
    token = jwt.encode({
        'user_id': user['id'],
        'username': user['username'],
        'is_admin': user['is_admin'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }, JWT_SECRET, algorithm="HS256")
    
    # 创建响应
    response = make_response(jsonify({
        'token': token,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'is_admin': user['is_admin']
        }
    }))
    
    # 设置Cookie
    response.set_cookie(
        'token', 
        token, 
        httponly=True, 
        max_age=7*24*60*60,  # 7天
        secure=False,  # 开发环境设为False，生产环境设为True
        samesite='Lax'
    )
    
    return response

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """用户登出"""
    response = make_response(jsonify({'message': '已成功登出'}))
    response.delete_cookie('token')
    return response

@app.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册"""
    # 检查是否允许注册
    if not ALLOW_REGISTER:
        return jsonify({'error': '注册功能已禁用'}), 403
    
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    # 用户名格式验证
    if len(username) < 3 or len(username) > 20:
        return jsonify({'error': '用户名长度必须在3-20个字符之间'}), 400
    
    # 密码强度验证
    if len(password) < 6:
        return jsonify({'error': '密码长度必须至少为6个字符'}), 400
    
    # 创建用户
    success = db.create_user(username, password)
    if not success:
        return jsonify({'error': '用户名已存在'}), 409
    
    return jsonify({'message': '注册成功', 'username': username})

@app.route('/api/auth/user', methods=['GET'])
@token_required
def get_current_user(current_user):
    """获取当前用户信息"""
    return jsonify({
        'id': current_user['id'],
        'username': current_user['username'],
        'is_admin': current_user['is_admin']
    })

@app.route('/api/auth/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    """更改当前用户密码"""
    data = request.json
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({'error': '旧密码和新密码不能为空'}), 400
    
    # 验证旧密码
    user = db.authenticate_user(current_user['username'], old_password)
    if not user:
        return jsonify({'error': '旧密码不正确'}), 401
    
    # 密码强度验证
    if len(new_password) < 6:
        return jsonify({'error': '新密码长度必须至少为6个字符'}), 400
    
    # 更新密码
    success = db.update_user_password(current_user['id'], new_password)
    if not success:
        return jsonify({'error': '密码更新失败'}), 500
    
    return jsonify({'message': '密码已成功更新'})

# 用户管理API
@app.route('/api/users', methods=['GET'])
@token_required
@admin_required
def get_all_users(current_user):
    """获取所有用户 (仅管理员)"""
    users = db.get_all_users()
    return jsonify([dict(user) for user in users])

@app.route('/api/users', methods=['POST'])
@token_required
@admin_required
def create_user(current_user):
    """创建新用户 (仅管理员)"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    is_admin = data.get('is_admin', False)
    
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    # 用户名格式验证
    if len(username) < 3 or len(username) > 20:
        return jsonify({'error': '用户名长度必须在3-20个字符之间'}), 400
    
    # 密码强度验证
    if len(password) < 6:
        return jsonify({'error': '密码长度必须至少为6个字符'}), 400
    
    # 创建用户
    success = db.create_user(username, password, is_admin)
    if not success:
        return jsonify({'error': '用户名已存在'}), 409
    
    return jsonify({
        'message': '用户创建成功', 
        'username': username,
        'is_admin': is_admin
    })

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_user(current_user, user_id):
    """删除用户 (仅管理员)"""
    # 检查是否是当前用户
    if user_id == current_user['id']:
        return jsonify({'error': '不能删除自己的账户'}), 400
    
    # 删除用户
    success = db.delete_user(user_id)
    if not success:
        return jsonify({'error': '删除用户失败'}), 500
    
    return jsonify({'message': f'用户ID {user_id} 已删除'})

@app.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
@token_required
@admin_required
def reset_user_password(current_user, user_id):
    """重置用户密码 (仅管理员)"""
    data = request.json
    new_password = data.get('new_password')
    
    if not new_password:
        return jsonify({'error': '新密码不能为空'}), 400
    
    # 密码强度验证
    if len(new_password) < 6:
        return jsonify({'error': '新密码长度必须至少为6个字符'}), 400
    
    # 更新密码
    success = db.update_user_password(user_id, new_password)
    if not success:
        return jsonify({'error': '密码重置失败'}), 500
    
    return jsonify({'message': f'用户ID {user_id} 的密码已重置'})

# 修改现有API以加入用户认证和授权
@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({'status': 'ok', 'message': '花火邮箱助手服务正在运行'})

@app.route('/api/emails', methods=['GET'])
@token_required
def get_all_emails(current_user):
    """获取当前用户的所有邮箱"""
    # 普通用户只能获取自己的邮箱，管理员可以获取所有邮箱
    if current_user['is_admin']:
        emails = db.get_all_emails()
    else:
        emails = db.get_all_emails(current_user['id'])
    
    return jsonify([dict(email) for email in emails])

@app.route('/api/emails', methods=['POST'])
@token_required
def add_email(current_user):
    """添加新邮箱"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    client_id = data.get('client_id')
    refresh_token = data.get('refresh_token')
    
    if not all([email, password, client_id, refresh_token]):
        return jsonify({'error': '所有字段都是必需的'}), 400
    
    success = db.add_email(current_user['id'], email, password, client_id, refresh_token)
    if success:
        return jsonify({'message': f'邮箱 {email} 添加成功'})
    else:
        return jsonify({'error': f'邮箱 {email} 已存在'}), 409

@app.route('/api/emails/<int:email_id>', methods=['DELETE'])
@token_required
def delete_email(current_user, email_id):
    """删除邮箱"""
    # 获取邮箱信息
    email_info = db.get_email_by_id(email_id, None if current_user['is_admin'] else current_user['id'])
    if not email_info:
        return jsonify({'error': f'邮箱ID {email_id} 不存在或您没有权限'}), 404
    
    # 停止正在处理的邮箱
    if email_processor.is_email_being_processed(email_id):
        email_processor.stop_processing(email_id)
    
    # 管理员可以删除任何邮箱，普通用户只能删除自己的邮箱
    db.delete_email(email_id, None if current_user['is_admin'] else current_user['id'])
    return jsonify({'message': f'邮箱 ID {email_id} 已删除'})

@app.route('/api/emails/batch_delete', methods=['POST'])
@token_required
def batch_delete_emails(current_user):
    """批量删除邮箱"""
    data = request.json
    email_ids = data.get('email_ids', [])
    
    if not email_ids:
        return jsonify({'error': '未提供邮箱ID'}), 400
    
    # 停止正在处理的邮箱
    for email_id in email_ids:
        if email_processor.is_email_being_processed(email_id):
            email_processor.stop_processing(email_id)
    
    # 管理员可以删除任何邮箱，普通用户只能删除自己的邮箱
    db.delete_emails(email_ids, None if current_user['is_admin'] else current_user['id'])
    return jsonify({'message': f'已删除 {len(email_ids)} 个邮箱'})

@app.route('/api/emails/<int:email_id>/check', methods=['POST'])
@token_required
def check_email(current_user, email_id):
    """检查单个邮箱的邮件"""
    # 获取邮箱信息
    email_info = db.get_email_by_id(email_id, None if current_user['is_admin'] else current_user['id'])
    if not email_info:
        logger.warning(f"尝试检查不存在的邮箱ID: {email_id} (用户ID: {current_user['id']})")
        return jsonify({'error': f'邮箱 ID {email_id} 不存在或您没有权限'}), 404
    
    if email_processor.is_email_being_processed(email_id):
        logger.info(f"邮箱 ID {email_id} 正在处理中，拒绝重复请求")
        # 返回当前进度信息而不是错误
        return jsonify({
            'message': f'邮箱 ID {email_id} 正在处理中',
            'status': 'processing'
        }), 409
    
    # 启动邮件检查线程
    logger.info(f"开始检查邮箱 ID {email_id}: {email_info['email']} (用户ID: {current_user['id']})")
    
    # 自定义进度回调
    def progress_callback(email_id, progress, message):
        logger.info(f"邮箱 ID {email_id} 处理进度: {progress}%, 消息: {message}")
    
    email_processor.check_emails([email_id], progress_callback)
    return jsonify({'message': f'开始检查邮箱 ID {email_id}', 'email': email_info['email']})

@app.route('/api/emails/batch_check', methods=['POST'])
@token_required
def batch_check_emails(current_user):
    """批量检查邮箱邮件"""
    data = request.json
    email_ids = data.get('email_ids', [])
    
    if not email_ids:
        # 如果没有提供 ID，则获取当前用户拥有的所有邮箱
        if current_user['is_admin']:
            emails = db.get_all_emails()
        else:
            emails = db.get_all_emails(current_user['id'])
            
        email_ids = [email['id'] for email in emails]
    else:
        # 如果提供了ID，验证用户权限
        if not current_user['is_admin']:
            # 获取该用户拥有的邮箱
            owned_emails = db.get_all_emails(current_user['id'])
            owned_ids = [email['id'] for email in owned_emails]
            # 过滤出用户有权限的邮箱ID
            email_ids = [id for id in email_ids if id in owned_ids]
    
    if not email_ids:
        logger.warning(f"批量检查邮件：未找到邮箱 (用户ID: {current_user['id']})")
        return jsonify({'error': '没有找到邮箱或您没有权限'}), 404
    
    # 过滤掉已经在处理的邮箱ID
    processing_ids = []
    valid_ids = []
    for email_id in email_ids:
        if email_processor.is_email_being_processed(email_id):
            processing_ids.append(email_id)
        else:
            valid_ids.append(email_id)
    
    if processing_ids:
        logger.info(f"批量检查：跳过正在处理的邮箱IDs: {processing_ids}")
    
    if not valid_ids:
        logger.warning("批量检查邮件：所有选择的邮箱都在处理中")
        return jsonify({
            'message': '所有选择的邮箱都在处理中',
            'processing_ids': processing_ids
        }), 409
    
    # 记录有效的邮箱ID
    valid_emails = [db.get_email_by_id(email_id)['email'] for email_id in valid_ids if db.get_email_by_id(email_id)]
    logger.info(f"批量检查开始处理 {len(valid_ids)} 个邮箱: {valid_emails} (用户ID: {current_user['id']})")
    
    # 自定义进度回调
    def progress_callback(email_id, progress, message):
        logger.info(f"邮箱 ID {email_id} 处理进度: {progress}%, 消息: {message}")
    
    # 启动邮件检查线程
    email_processor.check_emails(valid_ids, progress_callback)
    
    return jsonify({
        'message': f'开始检查 {len(valid_ids)} 个邮箱',
        'skipped': len(processing_ids),
        'total': len(email_ids)
    })

@app.route('/api/emails/<int:email_id>/mail_records', methods=['GET'])
@token_required
def get_mail_records(current_user, email_id):
    """获取指定邮箱的邮件记录"""
    # 获取邮箱信息
    email_info = db.get_email_by_id(email_id, None if current_user['is_admin'] else current_user['id'])
    if not email_info:
        return jsonify({'error': f'邮箱 ID {email_id} 不存在或您没有权限'}), 404
    
    mail_records = db.get_mail_records(email_id)
    return jsonify([dict(record) for record in mail_records])

@app.route('/api/emails/import', methods=['POST'])
@token_required
def import_emails(current_user):
    """批量导入邮箱"""
    data = request.json
    import_data = data.get('data', '')
    
    if not import_data:
        return jsonify({'error': '未提供数据'}), 400
    
    lines = import_data.strip().split('\n')
    success_count = 0
    failed_lines = []
    
    for line_number, line in enumerate(lines, 1):
        parts = line.strip().split('----')
        if len(parts) != 4:
            failed_lines.append({'line': line_number, 'content': line, 'reason': '格式无效'})
            continue
        
        email, password, client_id, refresh_token = parts
        if not all([email, password, client_id, refresh_token]):
            failed_lines.append({'line': line_number, 'content': line, 'reason': '缺少必需字段'})
            continue
        
        success = db.add_email(current_user['id'], email, password, client_id, refresh_token)
        if success:
            success_count += 1
        else:
            failed_lines.append({'line': line_number, 'content': line, 'reason': '邮箱已存在'})
    
    return jsonify({
        'total': len(lines),
        'success': success_count,
        'failed': len(failed_lines),
        'failed_details': failed_lines
    })

# 前端静态文件服务
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """提供前端静态文件"""
    # 确定前端构建目录的路径
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend', 'dist')
    
    # 如果路径为空或者是根路径，则返回 index.html
    if not path or path == '/':
        return send_from_directory(frontend_dir, 'index.html')
    
    # 检查请求的文件是否存在
    file_path = os.path.join(frontend_dir, path)
    if os.path.isfile(file_path):
        return send_from_directory(frontend_dir, path)
    else:
        # 如果文件不存在，返回 index.html 让前端路由处理
        return send_from_directory(frontend_dir, 'index.html')

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='花火邮箱助手')
    parser.add_argument('--host', default='0.0.0.0', help='主机地址')
    parser.add_argument('--port', type=int, default=5000, help='HTTP端口')
    parser.add_argument('--ws-port', type=int, default=8765, help='WebSocket端口')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    return parser.parse_args()

def start_websocket_server():
    """启动WebSocket服务器"""
    try:
        logger.info("启动WebSocket服务器")
        ws_handler.run()
    except Exception as e:
        logger.error(f"WebSocket服务器异常: {e}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        args = parse_args()
        
        # 设置WebSocket端口
        ws_handler.port = args.ws_port
        
        # 启动WebSocket服务器
        ws_thread = threading.Thread(target=start_websocket_server)
        ws_thread.daemon = True
        ws_thread.start()
        
        # 启动Flask应用
        logger.info(f"花火邮箱助手启动于 http://{args.host}:{args.port}")
        app.run(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        logger.info("程序被用户中断，正在关闭...")
    except Exception as e:
        logger.error(f"程序启动异常: {e}")
    finally:
        # 清理资源
        if db:
            db.close()
        logger.info("程序已关闭") 