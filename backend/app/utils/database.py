from flask_sqlalchemy import SQLAlchemy
import os


db = SQLAlchemy()


def init_db(app):
    """初始化数据库配置。

    优先使用环境变量 DATABASE_URL，便于 Docker/生产环境连接 PostgreSQL；
    未配置时回退到项目内 SQLite，保持本地开发行为不变。
    """
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'physics.db')
    database_url = os.environ.get('DATABASE_URL') or f'sqlite:///{db_path}'

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()
