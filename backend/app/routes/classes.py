import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.database import db
from app.utils.authz import require_user
from app.models import Class, ClassStudent, User, ClassExam, PaperPublish, Paper, Question, PaperStudent, ExamScoreRecord, now_bjt

classes_bp = Blueprint('classes', __name__)


@classes_bp.route('', methods=['GET'])
@jwt_required()
def get_classes():
    """获取班级列表"""
    user, err = require_user()
    if err:
        return err
    
    if user.role == 'teacher':
        # 教师可以看所有班级
        classes = Class.query.all()
        result = []
        for c in classes:
            class_data = c.to_dict()
            teacher_name = c.teacher.real_name if c.teacher else '未知教师'
            class_data['display_name'] = f"{teacher_name}-{c.name}"
            class_data['is_mine'] = c.teacher_id == user.id
            result.append(class_data)
        return jsonify({'classes': result})
    elif user.role == 'student':
        # 学生只能看已接受的班级
        memberships = ClassStudent.query.filter_by(student_id=user.id, status='accepted').all()
        class_ids = [m.class_id for m in memberships]
        classes = Class.query.filter(Class.id.in_(class_ids)).all()
        
        result = []
        for c in classes:
            class_data = c.to_dict()
            teacher_name = c.teacher.real_name if c.teacher else '未知教师'
            class_data['display_name'] = f"{teacher_name}-{c.name}"
            result.append(class_data)
        return jsonify({'classes': result})
    else:
        # 管理员可以看所有班级
        classes = Class.query.all()
        result = []
        for c in classes:
            class_data = c.to_dict()
            teacher_name = c.teacher.real_name if c.teacher else '未知教师'
            class_data['display_name'] = f"{teacher_name}-{c.name}"
            result.append(class_data)
        return jsonify({'classes': result})


@classes_bp.route('/<int:class_id>', methods=['GET'])
@jwt_required()
def get_class(class_id):
    """获取班级详情"""
    user, err = require_user()
    if err:
        return err
    
    class_ = Class.query.get(class_id)
    if not class_:
        return jsonify({'error': '班级不存在'}), 404
    
    # 学生只能查看已经加入的班级，待确认和已拒绝的邀请不能看名单
    if user.role == 'student':
        membership = ClassStudent.query.filter_by(
            class_id=class_id, student_id=user.id, status='accepted'
        ).first()
        if not membership:
            return jsonify({'error': '权限不足'}), 403
    
    # 获取学生列表（只显示已接受的）
    students = []
    for cs in class_.students:
        if cs.status == 'accepted':
            students.append({
                'id': cs.student.id,
                'username': cs.student.username,
                'real_name': cs.student.real_name,
                'joined_at': cs.joined_at.isoformat() if cs.joined_at else None
            })
    
    # 获取邀请列表（pending 和 rejected）
    invitations = []
    for cs in class_.students:
        if cs.status in ['pending', 'rejected']:
            invitations.append({
                'student_id': cs.student_id,
                'status': cs.status
            })
    
    result = class_.to_dict()
    result['students'] = students
    result['invitations'] = invitations
    
    return jsonify({'class': result})


@classes_bp.route('', methods=['POST'])
@jwt_required()
def create_class():
    """创建班级（仅教师）"""
    user, err = require_user()
    if err:
        return err
    
    if user.role not in ['admin', 'teacher']:
        return jsonify({'error': '权限不足'}), 403
    
    data = request.get_json() or {}
    if not data or not data.get('name'):
        return jsonify({'error': '班级名称不能为空'}), 400
    
    # 检查同一教师是否已有同名班级
    existing = Class.query.filter_by(name=data['name'], teacher_id=user.id).first()
    if existing:
        return jsonify({'error': '您已创建过同名班级，班级名称不能重复'}), 400
    
    class_ = Class(
        name=data['name'],
        teacher_id=user.id
    )
    
    db.session.add(class_)
    db.session.commit()
    
    return jsonify({'message': '创建成功', 'class': class_.to_dict()}), 201


@classes_bp.route('/<int:class_id>', methods=['PUT'])
@jwt_required()
def update_class(class_id):
    """更新班级信息"""
    user, err = require_user()
    if err:
        return err
    
    class_ = Class.query.get(class_id)
    if not class_:
        return jsonify({'error': '班级不存在'}), 404
    
    # 只有创建者或管理员可以修改
    if user.role != 'admin' and class_.teacher_id != user.id:
        return jsonify({'error': '权限不足'}), 403
    
    data = request.get_json() or {}
    
    if data.get('name'):
        # 检查同一教师是否已有同名班级（排除当前班级）
        existing = Class.query.filter(
            Class.name == data['name'],
            Class.teacher_id == user.id,
            Class.id != class_id
        ).first()
        if existing:
            return jsonify({'error': '您已创建过同名班级，班级名称不能重复'}), 400
        class_.name = data['name']
    
    db.session.commit()
    
    return jsonify({'message': '更新成功', 'class': class_.to_dict()})


@classes_bp.route('/<int:class_id>', methods=['DELETE'])
@jwt_required()
def delete_class(class_id):
    """删除班级"""
    user, err = require_user()
    if err:
        return err
    
    class_ = Class.query.get(class_id)
    if not class_:
        return jsonify({'error': '班级不存在'}), 404
    
    # 只有创建者或管理员可以删除
    if user.role != 'admin' and class_.teacher_id != user.id:
        return jsonify({'error': '权限不足'}), 403

    publish_ids = [row.id for row in PaperPublish.query.filter_by(class_id=class_id).all()]
    if publish_ids:
        ExamScoreRecord.query.filter(ExamScoreRecord.publish_id.in_(publish_ids)).delete(synchronize_session=False)
    ClassExam.query.filter_by(class_id=class_id).delete(synchronize_session=False)
    PaperPublish.query.filter_by(class_id=class_id).delete(synchronize_session=False)
    Paper.query.filter_by(class_id=class_id).update({Paper.class_id: None}, synchronize_session=False)
    
    db.session.delete(class_)
    db.session.commit()
    
    return jsonify({'message': '删除成功'})


@classes_bp.route('/<int:class_id>/students', methods=['POST'])
@jwt_required()
def add_student(class_id):
    """添加学生到班级"""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    class_ = Class.query.get(class_id)
    if not class_:
        return jsonify({'error': '班级不存在'}), 404
    
    # 只有创建者或管理员可以添加学生
    if user.role != 'admin' and class_.teacher_id != user.id:
        return jsonify({'error': '权限不足'}), 403
    
    data = request.get_json()
    student_id = data.get('student_id')
    
    if not student_id:
        return jsonify({'error': '学生ID不能为空'}), 400
    
    # 检查学生是否存在
    student = User.query.get(student_id)
    if not student or student.role != 'student':
        return jsonify({'error': '学生不存在'}), 404
    
    # 检查是否已在班级中或已有待确认邀请
    existing = ClassStudent.query.filter_by(class_id=class_id, student_id=student_id).first()
    if existing:
        if existing.status == 'accepted':
            return jsonify({'error': '该学生已在班级中'}), 400
        if existing.status == 'pending':
            return jsonify({'error': '该学生已被邀请，等待确认中'}), 400
        # rejected 状态：删除旧记录，允许重新邀请
        db.session.delete(existing)
        db.session.commit()
    
    cs = ClassStudent(class_id=class_id, student_id=student_id, status='pending')
    db.session.add(cs)
    db.session.commit()
    
    return jsonify({'message': '邀请已发送，等待学生确认'})


@classes_bp.route('/<int:class_id>/students/<int:student_id>', methods=['DELETE'])
@jwt_required()
def remove_student(class_id, student_id):
    """从班级移除学生（教师/管理员移除 或 学生自己退出）"""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    class_ = Class.query.get(class_id)
    if not class_:
        return jsonify({'error': '班级不存在'}), 404
    
    # 权限检查：
    # 1. 管理员可以移除任何学生
    # 2. 班级创建者可以移除学生
    # 3. 学生可以自己退出班级（student_id 必须等于自己的 id）
    can_remove = (
        user.role == 'admin' or
        (user.role == 'teacher' and class_.teacher_id == user.id) or
        (user.role == 'student' and user.id == student_id)
    )
    
    if not can_remove:
        return jsonify({'error': '权限不足'}), 403
    
    cs = ClassStudent.query.filter_by(class_id=class_id, student_id=student_id).first()
    if not cs:
        return jsonify({'error': '该学生不在班级中'}), 404
    
    db.session.delete(cs)
    db.session.commit()
    
    return jsonify({'message': '移除成功'})


@classes_bp.route('/available-students', methods=['GET'])
@jwt_required()
def get_available_students():
    """获取可添加的学生列表"""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if user.role not in ['admin', 'teacher']:
        return jsonify({'error': '权限不足'}), 403
    
    # 获取所有学生
    students = User.query.filter_by(role='student').all()
    
    return jsonify({
        'students': [
            {
                'id': s.id,
                'username': s.username,
                'real_name': s.real_name
            }
            for s in students
        ]
    })


@classes_bp.route('/invitations', methods=['GET'])
@jwt_required()
def get_invitations():
    """学生获取待确认的班级邀请"""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if user.role != 'student':
        return jsonify({'error': '权限不足'}), 403
    
    invitations = ClassStudent.query.filter_by(student_id=user.id, status='pending').all()
    result = []
    for inv in invitations:
        class_ = Class.query.get(inv.class_id)
        if class_:
            teacher_name = class_.teacher.real_name if class_.teacher else '未知教师'
            result.append({
                'id': inv.id,
                'class_id': class_.id,
                'class_name': class_.name,
                'teacher_name': teacher_name,
                'created_at': inv.joined_at.isoformat() if inv.joined_at else None
            })
    
    return jsonify({'invitations': result})


@classes_bp.route('/invitations/<int:invitation_id>/accept', methods=['POST'])
@jwt_required()
def accept_invitation(invitation_id):
    """学生接受班级邀请"""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if user.role != 'student':
        return jsonify({'error': '权限不足'}), 403
    
    invitation = ClassStudent.query.get(invitation_id)
    if not invitation or invitation.student_id != user.id or invitation.status != 'pending':
        return jsonify({'error': '邀请不存在'}), 404
    
    invitation.status = 'accepted'
    db.session.commit()
    
    return jsonify({'message': '已加入班级'})


@classes_bp.route('/invitations/<int:invitation_id>/reject', methods=['POST'])
@jwt_required()
def reject_invitation(invitation_id):
    """学生拒绝班级邀请"""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if user.role != 'student':
        return jsonify({'error': '权限不足'}), 403
    
    invitation = ClassStudent.query.get(invitation_id)
    if not invitation or invitation.student_id != user.id or invitation.status != 'pending':
        return jsonify({'error': '邀请不存在'}), 404
    
    invitation.status = 'rejected'
    db.session.commit()
    
    return jsonify({'message': '已拒绝邀请'})


@classes_bp.route('/<int:class_id>/students/invite-status', methods=['GET'])
@jwt_required()
def get_students_invite_status(class_id):
    """获取所有学生在指定班级的邀请状态（用于创建/编辑班级时的学生选择）"""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if user.role not in ['admin', 'teacher']:
        return jsonify({'error': '权限不足'}), 403
    
    # 获取所有学生
    students = User.query.filter_by(role='student').all()
    
    # 预加载所有可能的创建者（管理者）信息
    creator_ids = [s.created_by for s in students if s.created_by]
    creators = {u.id: u for u in User.query.filter(User.id.in_(creator_ids)).all()} if creator_ids else {}
    
    # class_id 为 0 表示创建新班级，此时所有学生都是未邀请状态
    if class_id == 0:
        return jsonify({
            'students': [
                {
                    'id': s.id,
                    'username': s.username,
                    'real_name': s.real_name,
                    'manager_name': _get_manager_name(s, creators),
                    'invite_status': None  # 未邀请
                }
                for s in students
            ]
        })
    
    # 获取班级信息
    class_ = Class.query.get(class_id)
    if not class_:
        return jsonify({'error': '班级不存在'}), 404
    
    # 获取该班级的所有学生记录（包括 pending, accepted, rejected）
    class_students = {cs.student_id: cs.status for cs in ClassStudent.query.filter_by(class_id=class_id).all()}
    
    result = []
    for student in students:
        status = class_students.get(student.id)
        # 转换状态：如果 status 是 accepted/pending/rejected 直接返回，否则为 None
        invite_status = status if status in ['accepted', 'pending', 'rejected'] else None
        
        result.append({
            'id': student.id,
            'username': student.username,
            'real_name': student.real_name,
            'manager_name': _get_manager_name(student, creators),
            'invite_status': invite_status
        })
    
    return jsonify({'students': result})

def _get_manager_name(student, creators):
    """获取学生的管理者名称"""
    if not student.created_by:
        return None
    creator = creators.get(student.created_by)
    if creator and creator.role in ['teacher', 'admin']:
        return creator.real_name or creator.username
    return None


@classes_bp.route('/<int:class_id>/exams', methods=['GET'])
@jwt_required()
def get_class_exams(class_id):
    """获取班级考试列表（统一为未开始/进行中/已结束三种状态）"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))

    class_ = Class.query.get(class_id)
    if not class_:
        return jsonify({'error': '班级不存在'}), 404

    # 检查权限：班级教师、管理员、或班级学生
    is_teacher = current_user.role in ['admin', 'teacher'] and class_.teacher_id == current_user.id
    is_admin = current_user.role == 'admin'
    is_student = ClassStudent.query.filter_by(class_id=class_id, student_id=current_user.id, status='accepted').first() is not None

    if not (is_teacher or is_admin or is_student):
        return jsonify({'error': '权限不足'}), 403

    result = []

    # 获取已发布到该班级的试卷
    publishes = PaperPublish.query.filter_by(class_id=class_id).all()
    for p in publishes:
        paper = Paper.query.get(p.paper_id)
        if paper:
            # 根据考试日期和时间判断状态（从发布记录读取）
            status = get_exam_status(p)

            # 检查是否已结束登记
            exam = ClassExam.query.filter_by(
                class_id=class_id,
                paper_id=paper.id,
                publish_id=p.id
            ).first()

            result.append({
                'id': p.id,
                'paper_id': paper.id,
                'publish_id': p.id,
                'title': paper.title,
                'exam_date': p.exam_date.isoformat() if p.exam_date else None,
                'start_time': p.start_time,
                'end_time': p.end_time,
                'total_score': paper.total_score,
                'difficulty': paper.difficulty,
                'status': status,
                'published_at': p.published_at.isoformat() if p.published_at else None,
                'finished_at': exam.finished_at.isoformat() if exam and exam.finished_at else None,
                'scoring_finished': exam is not None
            })

    # 按发布时间排序（最新的在前）
    result.sort(key=lambda x: x.get('published_at') or '', reverse=True)

    return jsonify({
        'exams': result
    })


def get_exam_status(publish):
    """按北京时间判断考试状态。容器时区通常是 UTC，不能用 datetime.now()。"""
    if not publish or not publish.exam_date or not publish.end_time:
        return '未开始'

    now = now_bjt().replace(tzinfo=None)
    try:
        exam_start = datetime.strptime(
            f"{publish.exam_date.isoformat()} {publish.start_time or '00:00'}",
            '%Y-%m-%d %H:%M'
        )
        exam_end = datetime.strptime(
            f"{publish.exam_date.isoformat()} {publish.end_time}",
            '%Y-%m-%d %H:%M'
        )
    except ValueError:
        return '未开始'

    # 结束时间早于开始时间时视为跨天
    if publish.start_time and publish.end_time and publish.end_time < publish.start_time:
        exam_end += timedelta(days=1)

    if now < exam_start:
        return '未开始'
    if now > exam_end:
        return '已结束'
    return '进行中'

@classes_bp.route('/<int:class_id>/exams/<int:publish_id>/scores', methods=['GET'])
@jwt_required()
def get_exam_scores(class_id, publish_id):
    """获取考试成绩（优先从ClassExam快照读取，锁定数据）"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))

    class_ = Class.query.get(class_id)
    if not class_:
        return jsonify({'error': '班级不存在'}), 404

    # 检查权限：班级教师、管理员、或班级学生
    is_teacher = current_user.role in ['admin', 'teacher'] and class_.teacher_id == current_user.id
    is_admin = current_user.role == 'admin'
    is_student = ClassStudent.query.filter_by(class_id=class_id, student_id=current_user.id, status='accepted').first() is not None

    if not (is_teacher or is_admin or is_student):
        return jsonify({'error': '权限不足'}), 403

    # 通过 publish_id 获取发布记录
    publish = PaperPublish.query.get(publish_id)
    if not publish or publish.class_id != class_id:
        return jsonify({'error': '考试不存在'}), 404

    paper = Paper.query.get(publish.paper_id)
    if not paper:
        return jsonify({'error': '试卷不存在'}), 404

    # 检查是否已有考试快照（结束登记后）
    exam = ClassExam.query.filter_by(
        class_id=class_id,
        publish_id=publish_id
    ).first()

    if exam:
        # 从快照读取（锁定数据，不受班级人员变动影响）
        questions = json.loads(exam.questions_snapshot) if exam.questions_snapshot else []
        students = json.loads(exam.scores_snapshot) if exam.scores_snapshot else []

        return jsonify({
            'paper': {
                'id': paper.id,
                'title': paper.title,
                'total_score': paper.total_score,
                'difficulty': paper.difficulty,
                'finished_at': exam.finished_at.isoformat() if exam.finished_at else None
            },
            'questions': questions,
            'students': students,
            'from_snapshot': True
        })

    # 没有快照，从实时数据读取（登记中，动态拉取班级成员）
    # 获取试卷题目信息
    questions_data = json.loads(paper.questions_data) if paper.questions_data else []
    questions = []
    for item in questions_data:
        question = Question.query.get(item['question_id'])
        if question:
            questions.append({
                'question_id': question.id,
                'question_title': question.question_title or question.title,
                'max_score': item.get('score', 10)
            })

    # 获取班级中已接受的学生（动态拉取）
    class_students = ClassStudent.query.filter_by(
        class_id=class_id, status='accepted'
    ).all()

    students = []
    for cs in class_students:
        student = User.query.get(cs.student_id)
        if not student:
            continue

        # 获取该学生该发布记录的成绩
        ps = PaperStudent.query.filter_by(
            paper_id=paper.id, student_id=cs.student_id
        ).first()

        scores = {}
        total_score = 0
        if ps:
            total_score = ps.total_score or 0
            for ss in ps.scores:
                scores[str(ss.question_id)] = ss.score

        students.append({
            'student_id': student.id,
            'student_name': student.real_name or student.username,
            'scores': scores,
            'total_score': total_score
        })

    return jsonify({
        'paper': {
            'id': paper.id,
            'title': paper.title,
            'total_score': paper.total_score,
            'difficulty': paper.difficulty
        },
        'questions': questions,
        'students': students,
        'from_snapshot': False
    })
