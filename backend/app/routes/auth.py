from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.utils.database import db
from app.models import User


auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()
    
    if not data or not data.get('real_name'):
        return jsonify({'error': '姓名不能为空'}), 400
    
    role = data.get('role', 'student')
    prefix = '1906' if role == 'teacher' else '1026'
    
    # 自动分配账号：优先复用已删除释放的序号，否则用最大序号+1
    existing = User.query.filter(User.username.startswith(prefix)).all()
    used_seqs = set()
    for u in existing:
        try:
            used_seqs.add(int(u.username[4:]))
        except (ValueError, IndexError):
            pass
    
    seq = 1
    while seq in used_seqs:
        seq += 1
    
    username = f"{prefix}{str(seq).zfill(4)}"
    password = username  # 初始密码与账号相同
    
    user = User(
        username=username,
        role=role,
        real_name=data.get('real_name'),
        created_by=data.get('created_by')
    )
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'message': '注册成功',
        'user': user.to_dict(),
        'password': password
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': '用户名或密码错误'}), 401
    
    access_token = create_access_token(identity=str(user.id))
    if current_app.config.get('DEBUG_API_LOGS'):
        current_app.logger.debug("登录成功，用户ID: %s", user.id)

    return jsonify({
        'message': '登录成功',
        'access_token': access_token,
        'user': user.to_dict()
    })


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """获取当前用户信息"""
    try:
        # 获取 JWT 信息
        user_id = get_jwt_identity()

        if current_app.config.get('DEBUG_API_LOGS'):
            current_app.logger.debug("/me 请求 - 用户ID: %s", user_id)

        user = User.query.get(user_id)

        if not user:
            if current_app.config.get('DEBUG_API_LOGS'):
                current_app.logger.debug("/me 请求 - 用户不存在: %s", user_id)
            return jsonify({'error': '用户不存在'}), 404

        if current_app.config.get('DEBUG_API_LOGS'):
            current_app.logger.debug("/me 请求 - 成功: %s", user.username)
        return jsonify({'user': user.to_dict()})
    except Exception as e:
        current_app.logger.exception("/me 请求异常")
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500


@auth_bp.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    """获取用户列表"""
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    
    if current_user.role == 'admin':
        users = User.query.all()
        return jsonify({'users': [u.to_dict() for u in users]})
    elif current_user.role == 'teacher':
        # 教师可以看到所有学生
        from app.models import Class, ClassStudent
        all_students = User.query.filter_by(role='student').all()
        # 计算教师班级内的学生ID
        class_ids = [c.id for c in Class.query.filter_by(teacher_id=current_user.id).all()]
        class_student_ids = set(
            cs.student_id for cs in ClassStudent.query.filter(
                ClassStudent.class_id.in_(class_ids),
                ClassStudent.status == 'accepted'
            ).all()
        )
        result = []
        for u in all_students:
            d = u.to_dict()
            d['can_edit'] = u.created_by == int(user_id) or u.id in class_student_ids
            result.append(d)
        return jsonify({'users': result})
    else:
        return jsonify({'error': '权限不足'}), 403


@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """更新用户信息"""
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404

    data = request.get_json() or {}

    # 只有管理员或用户本人可以修改基本信息
    if current_user.role == 'admin':
        pass
    elif current_user.role == 'teacher':
        # 教师只能修改自己创建的学生或自己班级内学生的密码
        if int(current_user_id) != int(user_id):
            if user.role != 'student':
                return jsonify({'error': '权限不足'}), 403
            # 检查是否是自己创建的或班级内的学生
            from app.models import Class, ClassStudent
            is_created = user.created_by == int(current_user_id)
            class_ids = [c.id for c in Class.query.filter_by(teacher_id=int(current_user_id)).all()]
            is_in_class = ClassStudent.query.filter(
                ClassStudent.class_id.in_(class_ids),
                ClassStudent.student_id == user_id
            ).first() is not None
            if not is_created and not is_in_class:
                return jsonify({'error': '权限不足'}), 403
            # 教师只能重置密码，不能修改姓名
            if data.get('real_name'):
                return jsonify({'error': '权限不足'}), 403
    else:
        if int(current_user_id) != int(user_id):
            return jsonify({'error': '权限不足'}), 403

    if data.get('real_name'):
        user.real_name = data['real_name']
    
    if data.get('password'):
        user.set_password(data['password'])
        # 管理员重置密码时传 reset_password=true，标记为需要改密码
        if data.get('reset_password'):
            user.password_changed = False
        else:
            user.password_changed = True
    
    # 只有管理员可以修改角色
    if current_user.role == 'admin' and data.get('role'):
        user.role = data['role']
    
    # 只有管理员可以修改学生的管理者（created_by）
    if current_user.role == 'admin' and data.get('manager_id') is not None:
        manager = User.query.get(data['manager_id'])
        if manager and manager.role in ['teacher', 'admin']:
            user.created_by = data['manager_id']
    
    db.session.commit()
    
    return jsonify({'message': '更新成功', 'user': user.to_dict()})


@auth_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """删除用户"""
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    
    if current_user.role == 'admin':
        pass  # 管理员可以删除任何非管理员用户
    elif current_user.role == 'teacher':
        # 教师只能删除自己创建的学生
        if user.role != 'student' or user.created_by != int(current_user_id):
            return jsonify({'error': '权限不足'}), 403
    else:
        return jsonify({'error': '权限不足'}), 403
    
    # 不能删除管理员
    if user.role == 'admin':
        return jsonify({'error': '不能删除管理员'}), 403
    
    # 获取管理员ID（用于转移创建者）
    admin_user = User.query.filter_by(role='admin').first()
    admin_id = admin_user.id if admin_user else current_user_id
    
    if user.role == 'teacher':
        # 教师账号被删除时
        from app.models import Class, ClassStudent
        # 1. 该教师所有的班级转移给管理员，并修改班级名字
        classes = Class.query.filter_by(teacher_id=user.id).all()
        for class_ in classes:
            class_.teacher_id = admin_id
            # 修改班级名字：原名字-原教师姓名 -> 原名字-管理员
            admin_user_obj = User.query.get(admin_id)
            admin_name = admin_user_obj.real_name or admin_user_obj.username if admin_user_obj else '管理员'
            teacher_name = user.real_name or user.username
            if class_.name.endswith(f'-{teacher_name}'):
                class_.name = class_.name[:-len(f'-{teacher_name}')] + f'-{admin_name}'
        # 2. 该教师创建的学生账号的创建者改为管理员
        students_created = User.query.filter_by(created_by=user.id, role='student').all()
        for student in students_created:
            student.created_by = admin_id
    elif user.role == 'student':
        # 学生账号被删除时，自动退出所有班级
        from app.models import ClassStudent
        ClassStudent.query.filter_by(student_id=user.id).delete()
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'message': '删除成功'})
