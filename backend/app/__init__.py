import os
import datetime
import logging
import secrets
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

    # 配置 - 生产环境通过环境变量注入密钥，本地开发自动生成临时密钥
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_urlsafe(32)
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY') or app.config['SECRET_KEY']
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=24)
    app.config['JWT_ERROR_MESSAGE_KEY'] = 'error'
    app.config['UPLOAD_FOLDER'] = os.environ.get(
        'UPLOAD_FOLDER',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
    )
    app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    app.config['DEBUG_API_LOGS'] = os.environ.get('DEBUG_API_LOGS', '').lower() in ('1', 'true', 'yes')

    log_level = os.environ.get('LOG_LEVEL', 'DEBUG' if app.config['DEBUG_API_LOGS'] else 'INFO').upper()
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
    app.logger.setLevel(getattr(logging, log_level, logging.INFO))

    # 初始化扩展
    cors_origins = os.environ.get('CORS_ORIGINS', '*')
    cors_origins = [origin.strip() for origin in cors_origins.split(',') if origin.strip()] or '*'
    CORS(app, resources={r"/api/*": {"origins": cors_origins}})
    jwt = JWTManager(app)
    
    # JWT 错误处理
    @jwt.unauthorized_loader
    def unauthorized_callback(reason):
        app.logger.warning("JWT 未授权: %s", reason)
        return {'error': f'缺少认证令牌: {reason}'}, 401

    @jwt.invalid_token_loader
    def invalid_token_callback(reason):
        app.logger.warning("JWT 无效令牌: %s", reason)
        return {'error': f'无效的令牌: {reason}'}, 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        app.logger.info("JWT 令牌过期")
        return {'error': '令牌已过期'}, 401

    @jwt.needs_fresh_token_loader
    def needs_fresh_token_callback(jwt_header, jwt_payload):
        app.logger.warning("JWT 需要新鲜令牌")
        return {'error': '需要新鲜令牌'}, 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        app.logger.warning("JWT 令牌已撤销")
        return {'error': '令牌已撤销'}, 401
    
    # 请求日志（默认关闭，避免输出敏感认证信息）
    @app.before_request
    def log_request():
        if app.config['DEBUG_API_LOGS'] and request.path.startswith('/api/'):
            has_auth = 'yes' if request.headers.get('Authorization') else 'no'
            app.logger.debug("API 请求: %s %s auth=%s", request.method, request.path, has_auth)
    
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
    
    if app.config['DEBUG_API_LOGS']:
        app.logger.debug("API 调试日志已开启")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
