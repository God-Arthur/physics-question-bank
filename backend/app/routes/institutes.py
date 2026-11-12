"""
机构管理路由
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.database import db
from app.models import User, Institute

institutes_bp = Blueprint('institutes', __name__)


@institutes_bp.route('/', methods=['GET'])
@jwt_required()
def get_institutes():
    """获取所有机构"""
    institutes = Institute.query.order_by(Institute.code).all()
    return jsonify({
        'institutes': [i.to_dict() for i in institutes]
    })


@institutes_bp.route('/', methods=['POST'])
@jwt_required()
def create_institute():
    """创建机构（管理员）"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))
    
    if not current_user or current_user.role not in ('admin', 'teacher'):
        return jsonify({'error': '权限不足'}), 403
    
    data = request.get_json()
    
    name = data.get('name', '').strip()
    code = data.get('code', '').strip().upper()
    
    if not name or not code:
        return jsonify({'error': '机构名称和代码不能为空'}), 400
    
    if len(code) != 3 or not code.isalpha():
        return jsonify({'error': '机构代码必须是3位大写字母'}), 400
    
    # 检查代码是否重复
    existing = Institute.query.filter_by(code=code).first()
    if existing:
        return jsonify({'error': f'机构代码 {code} 已存在'}), 400
    
    institute = Institute(name=name, code=code)
    db.session.add(institute)
    db.session.commit()
    
    return jsonify({
        'message': '机构创建成功',
        'institute': institute.to_dict()
    }), 201


@institutes_bp.route('/<int:institute_id>', methods=['PUT'])
@jwt_required()
def update_institute(institute_id):
    """更新机构（管理员）"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))
    
    if not current_user or current_user.role not in ('admin', 'teacher'):
        return jsonify({'error': '权限不足'}), 403
    
    institute = Institute.query.get(institute_id)
    if not institute:
        return jsonify({'error': '机构不存在'}), 404
    
    data = request.get_json()
    
    if 'name' in data:
        institute.name = data['name'].strip()
    
    if 'code' in data:
        code = data['code'].strip().upper()
        if len(code) != 3 or not code.isalpha():
            return jsonify({'error': '机构代码必须是3位大写字母'}), 400
        existing = Institute.query.filter(Institute.code == code, Institute.id != institute_id).first()
        if existing:
            return jsonify({'error': f'机构代码 {code} 已存在'}), 400
        institute.code = code
    
    db.session.commit()
    
    return jsonify({
        'message': '机构更新成功',
        'institute': institute.to_dict()
    })


@institutes_bp.route('/<int:institute_id>', methods=['DELETE'])
@jwt_required()
def delete_institute(institute_id):
    """删除机构（管理员）"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))
    
    if not current_user or current_user.role not in ('admin', 'teacher'):
        return jsonify({'error': '权限不足'}), 403
    
    institute = Institute.query.get(institute_id)
    if not institute:
        return jsonify({'error': '机构不存在'}), 404
    
    db.session.delete(institute)
    db.session.commit()
    
    return jsonify({'message': '机构删除成功'})


@institutes_bp.route('/codes', methods=['GET'])
@jwt_required()
def get_institute_codes():
    """获取所有机构代码（用于Prompt模板）"""
    institutes = Institute.query.order_by(Institute.code).all()
    return jsonify({
        'codes': [{'code': i.code, 'name': i.name} for i in institutes]
    })
