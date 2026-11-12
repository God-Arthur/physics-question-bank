"""当前登录用户解析。JWT identity 是字符串，统一转成整数主键。"""
from flask import jsonify
from flask_jwt_extended import get_jwt_identity

from app.models import User
from app.utils.database import db


def current_user():
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None
    return db.session.get(User, user_id)


def require_user():
    user = current_user()
    if not user:
        return None, (jsonify({'error': '用户不存在或登录已失效'}), 401)
    return user, None


def require_roles(*roles):
    user, err = require_user()
    if err:
        return None, err
    if user.role not in roles:
        return None, (jsonify({'error': '权限不足'}), 403)
    return user, None
