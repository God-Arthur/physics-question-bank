from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError
from app.utils.database import db
from app.utils.authz import current_user as resolve_current_user
from app.models import User


auth_bp = Blueprint('auth', __name__)

def _next_username(prefix):
    """优先复用已删除释放的序号，否则用最大序号 + 1。"""
    existing = User.query.filter(User.username.startswith(prefix)).all()
    used_seqs = set()
    for existing_user in existing:
        tail = existing_user.username[len(prefix):]
        if tail.isdigit():
            used_seqs.add(int(tail))
    seq = 1
    while seq in used_seqs:
        seq += 1
    return f"{prefix}{str(seq).zfill(4)}"


@auth_bp.route('/register', methods=['POST'])
@jwt_required()
def register():
    """由管理员或教师创建账号。不开放匿名注册，也不能把角色设成管理员。"""
    operator = resolve_current_user()
    if not operator or operator.role not in ('admin', 'teacher'):
        return jsonify({'error': '权限不足'}), 403

    data = request.get_json() or {}
    real_name = (data.get('real_name') or '').strip()
    if not real_name:
        return jsonify({'error': '姓名不能为空'}), 400

    role = data.get('role', 'student')
    if role not in ('student', 'teacher'):
        return jsonify({'error': '无效的角色'}), 400
    if operator.role == 'teacher' and role != 'student':
        return jsonify({'error': '权限不足'}), 403

    prefix = '1906' if role == 'teacher' else '1026'
    user = None
    password = None
    for _ in range(5):
        username = _next_username(prefix)
        password = username
        user = User(
            username=username,
            role=role,
            real_name=real_name,
            created_by=operator.id,
            password_changed=False,
        )
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
            break
        except IntegrityError:
            db.session.rollback()
            user = None
    if user is None:
        return jsonify({'error': '账号分配失败，请重试'}), 500

    return jsonify({
        'message': '注册成功',
        'user': user.to_dict(),
        'username': user.username,
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

        user = resolve_current_user()

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
    current_user = resolve_current_user()
    if not current_user:
        return jsonify({'error': '用户不存在或登录已失效'}), 401
    
    if current_user.role == 'admin':
        users = User.query.all()
        return jsonify({'users': [u.to_dict() for u in users]})
    elif current_user.role == 'teacher':
        # 教师可以看到所有学生
        from app.models import Class, ClassStudent
        all_students = User.query.filter_by(role='student').all()
        # 计算教师班级内的学生ID
        class_ids = [c.id for c in Class.query.filter_by(teacher_id=current_user.id).all()]
        class_student_ids = set()
        if class_ids:
            class_student_ids = set(
                cs.student_id for cs in ClassStudent.query.filter(
                    ClassStudent.class_id.in_(class_ids),
                    ClassStudent.status == 'accepted'
                ).all()
            )
        result = []
        for u in all_students:
            d = u.to_dict()
            d['can_edit'] = u.created_by == current_user.id or u.id in class_student_ids
            result.append(d)
        return jsonify({'users': result})
    else:
        return jsonify({'error': '权限不足'}), 403


@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """更新用户信息"""
    current_user = resolve_current_user()
    if not current_user:
        return jsonify({'error': '用户不存在或登录已失效'}), 401
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404

    data = request.get_json() or {}

    # 只有管理员或用户本人可以修改基本信息
    if current_user.role == 'admin':
        pass
    elif current_user.role == 'teacher':
        # 教师只能修改自己创建的学生或自己班级内学生的密码
        if current_user.id != user.id:
            if user.role != 'student':
                return jsonify({'error': '权限不足'}), 403
            # 检查是否是自己创建的或已加入自己班级的学生
            from app.models import Class, ClassStudent
            is_created = user.created_by == current_user.id
            class_ids = [c.id for c in Class.query.filter_by(teacher_id=current_user.id).all()]
            is_in_class = False
            if class_ids:
                is_in_class = ClassStudent.query.filter(
                    ClassStudent.class_id.in_(class_ids),
                    ClassStudent.student_id == user_id,
                    ClassStudent.status == 'accepted'
                ).first() is not None
            if not is_created and not is_in_class:
                return jsonify({'error': '权限不足'}), 403
            # 教师只能重置密码，不能修改姓名
            if data.get('real_name'):
                return jsonify({'error': '权限不足'}), 403
    else:
        if current_user.id != user.id:
            return jsonify({'error': '权限不足'}), 403

    if data.get('real_name'):
        user.real_name = data['real_name'].strip()
    
    if data.get('password'):
        changing_self = current_user.id == user.id
        # 首次登录的强制改密不要求旧密码；之后改自己的密码必须验证旧密码
        if changing_self and (user.password_changed or data.get('old_password')):
            if not user.check_password(data.get('old_password') or ''):
                return jsonify({'error': '当前密码错误'}), 400
        user.set_password(data['password'])
        # 管理员重置密码时传 reset_password=true，标记为需要改密码
        if data.get('reset_password'):
            user.password_changed = False
        else:
            user.password_changed = True
    
    # 只有管理员可以修改角色
    if current_user.role == 'admin' and data.get('role'):
        if data['role'] not in ('admin', 'teacher', 'student'):
            return jsonify({'error': '无效的角色'}), 400
        user.role = data['role']
    
    # 只有管理员可以修改学生的管理者（created_by）
    if current_user.role == 'admin' and data.get('manager_id') is not None:
        manager = User.query.get(data['manager_id'])
        if manager and manager.role in ['teacher', 'admin']:
            user.created_by = data['manager_id']
    
    db.session.commit()
    
    return jsonify({'message': '更新成功', 'user': user.to_dict()})


def _release_user_references(user, admin_id):
    """删除用户前解除外键，避免 PostgreSQL 上直接删除失败。"""
    from app.models import (
        Class, ClassExam, ClassStudent, ExamScoreRecord, Paper,
        PaperPublish, PaperStudent, StudentScore,
    )

    admin_id = int(admin_id)
    if user.role == 'teacher':
        admin_user_obj = db.session.get(User, admin_id)
        admin_name = (admin_user_obj.real_name or admin_user_obj.username) if admin_user_obj else '管理员'
        teacher_name = user.real_name or user.username
        suffix = f'-{teacher_name}'
        for class_ in Class.query.filter_by(teacher_id=user.id).all():
            class_.teacher_id = admin_id
            if class_.name.endswith(suffix):
                class_.name = class_.name[:-len(suffix)] + f'-{admin_name}'

    ClassStudent.query.filter_by(student_id=user.id).delete(synchronize_session=False)
    ExamScoreRecord.query.filter_by(student_id=user.id).delete(synchronize_session=False)
    for paper_student in PaperStudent.query.filter_by(student_id=user.id).all():
        db.session.delete(paper_student)
    Paper.query.filter_by(created_by=user.id).update(
        {Paper.created_by: admin_id}, synchronize_session=False
    )
    Paper.query.filter_by(reviewer_id=user.id).update(
        {Paper.reviewer_id: None}, synchronize_session=False
    )
    PaperPublish.query.filter_by(published_by=user.id).update(
        {PaperPublish.published_by: admin_id}, synchronize_session=False
    )
    ClassExam.query.filter_by(finished_by=user.id).update(
        {ClassExam.finished_by: None}, synchronize_session=False
    )
    StudentScore.query.filter_by(graded_by=user.id).update(
        {StudentScore.graded_by: None}, synchronize_session=False
    )
    User.query.filter_by(created_by=user.id).update(
        {User.created_by: admin_id}, synchronize_session=False
    )
    db.session.flush()


@auth_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """删除用户"""
    current_user = resolve_current_user()
    if not current_user:
        return jsonify({'error': '用户不存在或登录已失效'}), 401
    
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    
    if current_user.role == 'admin':
        pass  # 管理员可以删除任何非管理员用户
    elif current_user.role == 'teacher':
        # 教师只能删除自己创建的学生
        if user.role != 'student' or user.created_by != current_user.id:
            return jsonify({'error': '权限不足'}), 403
    else:
        return jsonify({'error': '权限不足'}), 403
    
    # 不能删除管理员
    if user.role == 'admin':
        return jsonify({'error': '不能删除管理员'}), 403
    
    admin_user = User.query.filter_by(role='admin').first()
    admin_id = admin_user.id if admin_user else current_user.id
    _release_user_references(user, admin_id)

    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'message': '删除成功'})
