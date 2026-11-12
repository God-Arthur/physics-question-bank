from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
import os


db = SQLAlchemy()


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute('PRAGMA foreign_keys=ON')
    cursor.close()


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
        if db.engine.dialect.name == 'sqlite' and not event.contains(
            db.engine, 'connect', _enable_sqlite_foreign_keys
        ):
            event.listen(db.engine, 'connect', _enable_sqlite_foreign_keys)
        db.create_all()
        from app.seed import ensure_seed_data
        ensure_seed_data()
