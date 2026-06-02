import os
import datetime
from flask import Flask, request, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from app.utils.database import db, init_db
from app.routes.auth import auth_bp
from app.routes.questions import questions_bp
from app.routes.papers import papers_bp
from app.routes.classes import classes_bp
from app.routes.institutes import institutes_bp
from app.routes.pdf_preview import pdf_preview_bp

def create_app():
    app = Flask(__name__)
    
    # 配置 - 使用固定的强密钥
    app.config['SECRET_KEY'] = 'physics-question-bank-secret-key-2024-for-production-use-only'
    app.config['JWT_SECRET_KEY'] = 'jwt-secret-key-2024-for-physics-question-bank-system-long-enough'
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=24)
    app.config['JWT_ERROR_MESSAGE_KEY'] = 'error'
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    # 初始化扩展
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    jwt = JWTManager(app)
    
    # JWT 错误处理
    @jwt.unauthorized_loader
    def unauthorized_callback(reason):
        print(f"[JWT ERROR] 未授权: {reason}")
        return {'error': f'缺少认证令牌: {reason}'}, 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(reason):
        print(f"[JWT ERROR] 无效令牌: {reason}")
        return {'error': f'无效的令牌: {reason}'}, 401
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        print(f"[JWT ERROR] 令牌过期")
        return {'error': '令牌已过期'}, 401
    
    @jwt.needs_fresh_token_loader
    def needs_fresh_token_callback(jwt_header, jwt_payload):
        print(f"[JWT ERROR] 需要新鲜令牌")
        return {'error': '需要新鲜令牌'}, 401
    
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        print(f"[JWT ERROR] 令牌已撤销")
        return {'error': '令牌已撤销'}, 401
    
    # 请求日志
    @app.before_request
    def log_request():
        if request.path.startswith('/api/'):
            auth_header = request.headers.get('Authorization', 'None')
            print(f"[REQUEST] {request.method} {request.path}")
            print(f"[REQUEST] Authorization: {auth_header[:50]}..." if auth_header != 'None' else f"[REQUEST] Authorization: None")
    
    # 初始化数据库
    init_db(app)
    
    # 注册蓝图
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(questions_bp, url_prefix='/api/questions')
    app.register_blueprint(papers_bp, url_prefix='/api/papers')
    app.register_blueprint(classes_bp, url_prefix='/api/classes')
    app.register_blueprint(institutes_bp, url_prefix='/api/institutes')
    app.register_blueprint(pdf_preview_bp, url_prefix='/api/pdf')
    
    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # 静态文件服务 - 上传的图片
    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    print(f"[INIT] JWT_SECRET_KEY: {app.config['JWT_SECRET_KEY'][:30]}...")
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
