from flask import Blueprint, request, jsonify, current_app, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
import json
import os
import numpy as np
from datetime import datetime
from app.models import now_bjt
from app.utils.database import db
from app.models import Paper, Question, User, PaperStudent, StudentScore, Class, ClassStudent, PaperPublish, ClassExam, ExamScoreRecord
from app.utils.pdf_generator import generate_paper_pdf, generate_latex_template, generate_answer_latex_template
from app.utils.pdf_preview_session import get_tex_path, cleanup_pdf_session
from app.routes.classes import get_exam_status

# 逻辑斯蒂函数
def logistic(x, a, b, c, d):
    """逻辑斯蒂函数: y = a + (b-a) / (1 + exp(-c*(x-d)))"""
    return a + (b - a) / (1 + np.exp(-c * (x - d)))


def build_difficulty_mapping(a, b, c, d):
    """根据拟合参数生成得分率→难度系数映射表"""
    score_rates = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
    mapping = []
    for sr in score_rates:
        try:
            # 反解逻辑斯蒂函数: x = d - ln((b-y)/(y-a))/c
            # 当 y 超出 (b, a) 范围时，clamp 到边界值
            y = np.clip(sr, min(a, b) + 0.001, max(a, b) - 0.001)
            difficulty = d - np.log((b - y) / (y - a)) / c
            difficulty = max(0.1, min(5.0, difficulty))
            mapping.append({
                'score_rate': int(sr * 100),
                'difficulty': round(float(difficulty), 2)
            })
        except (ValueError, ZeroDivisionError):
            mapping.append({
                'score_rate': int(sr * 100),
                'difficulty': None
            })
    return mapping

papers_bp = Blueprint('papers', __name__)


@papers_bp.route('', methods=['GET'])
@jwt_required()
def get_papers():
    """获取试卷列表"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    class_id = request.args.get('class_id', type=int)
    status = request.args.get('status', type=str)

    query = Paper.query

    # 按班级过滤
    if class_id:
        query = query.filter(Paper.class_id == class_id)

    # 按状态过滤
    if status:
        query = query.filter(Paper.status == status)

    # 学生只能看到已发布的试卷
    if current_user.role == 'student':
        query = query.filter(Paper.status == 'published')
    
    pagination = query.order_by(Paper.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'papers': [p.to_dict() for p in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })


@papers_bp.route('/<int:paper_id>', methods=['GET'])
@jwt_required()
def get_paper(paper_id):
    """获取试卷详情"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))
    
    paper = Paper.query.get(paper_id)
    
    if not paper:
        return jsonify({'error': '试卷不存在'}), 404
    
    # 学生只能查看分配给自己的试卷
    if current_user.role == 'student':
        assignment = PaperStudent.query.filter_by(paper_id=paper_id, student_id=current_user.id).first()
        if not assignment:
            return jsonify({'error': '权限不足'}), 403
        # 学生只能在考试后查看（状态为 finished）
        if paper.status != 'finished':
            return jsonify({'error': '考试尚未结束'}), 403
    
    # 获取完整的题目信息
    questions_data = json.loads(paper.questions_data) if paper.questions_data else []
    questions = []
    for item in questions_data:
        question = Question.query.get(item['question_id'])
        if question:
            questions.append({
                'question': question.to_dict(),
                'score': item.get('score', 10)
            })
    
    result = paper.to_dict()
    result['questions'] = questions
    
    # 获取考试学生列表（仅教师和管理员）
    if current_user.role in ['admin', 'teacher']:
        exam_students = []
        for ps in paper.exam_students:
            exam_students.append(ps.to_dict())
        result['exam_students'] = exam_students
    
    return jsonify({'paper': result})


@papers_bp.route('', methods=['POST'])
@jwt_required()
def create_paper():
    """创建试卷"""
    user_id = get_jwt_identity()
    
    data = request.get_json()
    
    if not data or not data.get('title'):
        return jsonify({'error': '试卷标题不能为空'}), 400
    
    if not data.get('questions') or len(data['questions']) == 0:
        return jsonify({'error': '请选择至少一道题目'}), 400
    
    # 验证题目是否存在
    questions_data = []
    total_score = 0
    total_difficulty = 0  # 用于计算加权难度
    for item in data['questions']:
        question = Question.query.get(item['question_id'])
        if not question:
            return jsonify({'error': f'题目 {item["question_id"]} 不存在'}), 400
        score = item.get('score', 10)
        questions_data.append({
            'question_id': item['question_id'],
            'score': score
        })
        total_score += score
        # 加权难度：分数 × 题目难度
        q_difficulty = question.difficulty or 0
        total_difficulty += score * q_difficulty

    # 计算试卷难度系数（加权平均）
    paper_difficulty = total_difficulty / total_score if total_score > 0 else 0
    
    # 解析日期
    exam_date = None
    if data.get('exam_date'):
        try:
            exam_date = datetime.strptime(data['exam_date'], '%Y-%m-%d').date()
        except:
            pass
    
    # 读取或生成 tex 文件内容
    tex_content = None
    answer_tex_content = None
    preview_id = data.get('preview_id')
    answer_preview_id = data.get('answer_preview_id')
    pdf_session_id = data.get('pdf_session_id')
    
    # 构建完整的题目列表（包含 question 对象）
    full_questions = []
    for item in questions_data:
        question = Question.query.get(item['question_id'])
        if question:
            full_questions.append({
                'question': question,
                'score': item['score']
            })
    
    # 生成时间信息
    time_info = '（考试时间）'
    if data.get('exam_date'):
        try:
            from datetime import datetime
            exam_date = datetime.strptime(data['exam_date'][:10], '%Y-%m-%d')
            date_str = f"{exam_date.year}年{exam_date.month}月{exam_date.day}日"
            if data.get('start_time'):
                start_time = data['start_time'][:5]
                if data.get('end_time'):
                    end_time = data['end_time'][:5]
                    time_info = f"（{date_str}{start_time}-{end_time}）"
                else:
                    time_info = f"（{date_str}{start_time}）"
            else:
                time_info = f"（{date_str}）"
        except:
            pass
    
    if preview_id and pdf_session_id:
        # 从会话目录读取 tex 文件
        tex_path = get_tex_path(current_app._get_current_object(), pdf_session_id, preview_id)
        if tex_path:
            with open(tex_path, 'r', encoding='utf-8') as f:
                tex_content = f.read()
    else:
        # 用户未生成预览，系统自动生成试卷 tex
        tex_content = generate_latex_template(data['title'], time_info, full_questions)
    
    if answer_preview_id and pdf_session_id:
        answer_tex_path = get_tex_path(current_app._get_current_object(), pdf_session_id, answer_preview_id)
        if answer_tex_path:
            with open(answer_tex_path, 'r', encoding='utf-8') as f:
                answer_tex_content = f.read()
    else:
        # 用户未生成预览，系统自动生成答案 tex
        answer_tex_content = generate_answer_latex_template(data['title'], time_info, full_questions)
    
    paper = Paper(
        title=data['title'],
        exam_date=exam_date,
        start_time=data.get('start_time', ''),
        end_time=data.get('end_time', ''),
        class_id=data.get('class_id'),
        allow_view_after_exam=data.get('allow_view_after_exam', False),
        difficulty=paper_difficulty,
        duration=data.get('duration', 180),  # 默认180分钟
        total_score=data.get('total_score', total_score),
        questions_data=json.dumps(questions_data),
        tex_content=tex_content,
        answer_tex_content=answer_tex_content,
        status='draft',
        needs_review=data.get('needs_review', False),
        reviewer_id=data.get('reviewer_id'),
        review_note=data.get('review_note'),
        created_by=user_id
    )
    
    db.session.add(paper)
    
    # 更新题目使用次数
    for item in questions_data:
        question = Question.query.get(item['question_id'])
        if question:
            question.use_count += 1
    
    db.session.commit()
    
    # 创建成功后清理PDF预览会话
    if pdf_session_id:
        cleanup_pdf_session(current_app._get_current_object(), pdf_session_id)
    
    return jsonify({'message': '创建成功', 'paper': paper.to_dict()}), 201


@papers_bp.route('/<int:paper_id>', methods=['PUT'])
@jwt_required()
def update_paper(paper_id):
    """更新试卷"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))
    
    paper = Paper.query.get(paper_id)
    if not paper:
        return jsonify({'error': '试卷不存在'}), 404
    
    # 只有创建者或管理员可以修改
    if current_user.role != 'admin' and paper.created_by != current_user.id:
        return jsonify({'error': '权限不足'}), 403
    
    data = request.get_json()
    
    if data.get('title'):
        paper.title = data['title']
    if data.get('exam_date'):
        try:
            paper.exam_date = datetime.strptime(data['exam_date'][:10], '%Y-%m-%d').date()
        except:
            pass
    if data.get('start_time') is not None:
        paper.start_time = data['start_time']
    if data.get('end_time') is not None:
        paper.end_time = data['end_time']
    if data.get('class_id') is not None:
        paper.class_id = data['class_id']
    if data.get('allow_view_after_exam') is not None:
        paper.allow_view_after_exam = data['allow_view_after_exam']
    if data.get('duration'):
        paper.duration = data['duration']
    if data.get('status'):
        paper.status = data['status']
    
    # 更新题目列表
    if data.get('questions'):
        questions_data = []
        total_score = 0
        total_difficulty = 0
        for item in data['questions']:
            question = Question.query.get(item['question_id'])
            if question:
                score = item.get('score', 10)
                questions_data.append({
                    'question_id': item['question_id'],
                    'score': score
                })
                total_score += score
                q_difficulty = question.difficulty or 0
                total_difficulty += score * q_difficulty
        
        paper.questions_data = json.dumps(questions_data)
        paper.total_score = data.get('total_score', total_score)
        paper.difficulty = total_difficulty / total_score if total_score > 0 else 0
        
        # 重新生成 tex 内容
        full_questions = []
        for item in questions_data:
            question = Question.query.get(item['question_id'])
            if question:
                full_questions.append({
                    'question': question,
                    'score': item['score']
                })
        
        # 生成时间信息
        time_info = '（考试时间）'
        if data.get('exam_date'):
            try:
                exam_date = datetime.strptime(data['exam_date'][:10], '%Y-%m-%d')
                date_str = f"{exam_date.year}年{exam_date.month}月{exam_date.day}日"
                if data.get('start_time'):
                    start_time = data['start_time'][:5]
                    if data.get('end_time'):
                        end_time = data['end_time'][:5]
                        time_info = f"（{date_str}{start_time}-{end_time}）"
                    else:
                        time_info = f"（{date_str}{start_time}）"
                else:
                    time_info = f"（{date_str}）"
            except:
                pass
        
        paper.tex_content = generate_latex_template(data.get('title', paper.title), time_info, full_questions)
        paper.answer_tex_content = generate_answer_latex_template(data.get('title', paper.title), time_info, full_questions)
    
    db.session.commit()
    
    return jsonify({'message': '更新成功', 'paper': paper.to_dict()})


@papers_bp.route('/<int:paper_id>', methods=['DELETE'])
@jwt_required()
def delete_paper(paper_id):
    """删除试卷"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))
    
    paper = Paper.query.get(paper_id)
    if not paper:
        return jsonify({'error': '试卷不存在'}), 404
    
    # 只有创建者或管理员可以删除
    if current_user.role != 'admin' and paper.created_by != current_user.id:
        return jsonify({'error': '权限不足'}), 403
    
    db.session.delete(paper)
    db.session.commit()
    
    return jsonify({'message': '删除成功'})


@papers_bp.route('/<int:paper_id>/export', methods=['GET'])
@jwt_required()
def export_paper_pdf(paper_id):
    """导出试卷PDF"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))
    
    paper = Paper.query.get(paper_id)
    if not paper:
        return jsonify({'error': '试卷不存在'}), 404
    
    # 学生只能导出分配给自己的试卷
    if current_user.role == 'student':
        assignment = PaperStudent.query.filter_by(paper_id=paper_id, student_id=current_user.id).first()
        if not assignment:
            return jsonify({'error': '权限不足'}), 403
    
    # 获取题目信息
    questions_data = json.loads(paper.questions_data) if paper.questions_data else []
    questions = []
    for item in questions_data:
        question = Question.query.get(item['question_id'])
        if question:
            questions.append({
                'question': question,
                'score': item.get('score', 10)
            })
    
    # 生成PDF
    include_answer = request.args.get('include_answer', 'true').lower() == 'true'
    
    pdf_path = generate_paper_pdf(paper, questions, include_answer)
    
    return send_file(pdf_path, as_attachment=True, download_name=f"{paper.title}.pdf")


# ==================== 考试学生管理 ====================

@papers_bp.route('/<int:paper_id>/students', methods=['GET'])
@jwt_required()
def get_paper_students(paper_id):
    """获取试卷的考试学生列表"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))
    
    paper = Paper.query.get(paper_id)
    if not paper:
        return jsonify({'error': '试卷不存在'}), 404
    
    # 只有创建者或管理员可以查看
    if current_user.role != 'admin' and paper.created_by != current_user.id:
        return jsonify({'error': '权限不足'}), 403
    
    students = []
    for ps in paper.exam_students:
        student_data = ps.to_dict()
        # 获取各题得分
        scores = [s.to_dict() for s in ps.scores]
        student_data['scores'] = scores
        students.append(student_data)
    
    return jsonify({'students': students})


@papers_bp.route('/<int:paper_id>/students', methods=['POST'])
@jwt_required()
def add_paper_student(paper_id):
    """添加考试学生"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))
    
    paper = Paper.query.get(paper_id)
    if not paper:
        return jsonify({'error': '试卷不存在'}), 404
    
    # 只有创建者或管理员可以添加
    if current_user.role != 'admin' and paper.created_by != current_user.id:
        return jsonify({'error': '权限不足'}), 403
    
    data = request.get_json()
    student_id = data.get('student_id')
    
    if not student_id:
        return jsonify({'error': '学生ID不能为空'}), 400
    
    # 检查学生是否存在
    student = User.query.get(student_id)
    if not student or student.role != 'student':
        return jsonify({'error': '学生不存在'}), 404
    
    # 检查是否已添加
    existing = PaperStudent.query.filter_by(paper_id=paper_id, student_id=student_id).first()
    if existing:
        return jsonify({'error': '该学生已添加'}), 400
    
    ps = PaperStudent(paper_id=paper_id, student_id=student_id)
    db.session.add(ps)
    db.session.commit()
    
    return jsonify({'message': '添加成功', 'student': ps.to_dict()})


@papers_bp.route('/<int:paper_id>/students/batch', methods=['POST'])
@jwt_required()
def add_paper_students_batch(paper_id):
    """批量添加考试学生（从班级）"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))
    
    paper = Paper.query.get(paper_id)
    if not paper:
        return jsonify({'error': '试卷不存在'}), 404
    
    # 只有创建者或管理员可以添加
    if current_user.role != 'admin' and paper.created_by != current_user.id:
        return jsonify({'error': '权限不足'}), 403
    
    data = request.get_json()
    class_id = data.get('class_id')
    
    if not class_id:
        return jsonify({'error': '班级ID不能为空'}), 400
    
    # 获取班级学生
    class_students = ClassStudent.query.filter_by(class_id=class_id).all()
    
    added_count = 0
    for cs in class_students:
        existing = PaperStudent.query.filter_by(paper_id=paper_id, student_id=cs.student_id).first()
        if not existing:
            ps = PaperStudent(paper_id=paper_id, student_id=cs.student_id)
            db.session.add(ps)
            added_count += 1
    
    db.session.commit()
    
    return jsonify({'message': f'成功添加 {added_count} 名学生'})


@papers_bp.route('/<int:paper_id>/students/<int:student_id>', methods=['DELETE'])
@jwt_required()
def remove_paper_student(paper_id, student_id):
    """移除考试学生"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))
    
    paper = Paper.query.get(paper_id)
    if not paper:
        return jsonify({'error': '试卷不存在'}), 404
    
    # 只有创建者或管理员可以移除
    if current_user.role != 'admin' and paper.created_by != current_user.id:
        return jsonify({'error': '权限不足'}), 403
    
    ps = PaperStudent.query.filter_by(paper_id=paper_id, student_id=student_id).first()
    if not ps:
        # 自动创建考试记录
        ps = PaperStudent(
            paper_id=paper_id,
            student_id=student_id,
            status='assigned'
        )
        db.session.add(ps)
        db.session.flush()  # 获取 ps.id
    
    db.session.delete(ps)
    db.session.commit()
    
    return jsonify({'message': '移除成功'})


# ==================== 成绩管理 ====================

@papers_bp.route('/<int:paper_id>/students/<int:student_id>/scores', methods=['POST'])
@jwt_required()
def submit_scores(paper_id, student_id):
    """提交学生各题得分"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))
    
    paper = Paper.query.get(paper_id)
    if not paper:
        return jsonify({'error': '试卷不存在'}), 404

    # 只有班级教师或管理员可以登记成绩
    if current_user.role != 'admin':
        # 检查是否是试卷关联班级的教师
        if paper.class_id:
            class_info = Class.query.get(paper.class_id)
            if not class_info or class_info.teacher_id != current_user.id:
                return jsonify({'error': '权限不足，只有班级教师或管理员可以登记成绩'}), 403
        else:
            return jsonify({'error': '权限不足'}), 403
    
    ps = PaperStudent.query.filter_by(paper_id=paper_id, student_id=student_id).first()
    if not ps:
        # 自动创建考试记录
        ps = PaperStudent(
            paper_id=paper_id,
            student_id=student_id,
            status='assigned'
        )
        db.session.add(ps)
        db.session.flush()  # 获取 ps.id
    
    data = request.get_json()
    scores_data = data.get('scores', [])
    
    total_score = 0
    for score_item in scores_data:
        question_id = score_item.get('question_id')
        score = score_item.get('score')
        max_score = score_item.get('max_score')
        comment = score_item.get('comment')
        
        # 检查是否已有记录
        existing = StudentScore.query.filter_by(
            paper_student_id=ps.id,
            question_id=question_id
        ).first()
        
        if existing:
            existing.score = score
            existing.max_score = max_score
            existing.comment = comment
            existing.graded_by = current_user.id
        else:
            ss = StudentScore(
                paper_student_id=ps.id,
                question_id=question_id,
                score=score,
                max_score=max_score,
                comment=comment,
                graded_by=current_user.id
            )
            db.session.add(ss)
        
        total_score += score
    
    # 更新总分
    ps.total_score = total_score
    ps.status = 'graded'
    
    # 更新题目统计数据（用于逻辑斯蒂拟合）
    for score_item in scores_data:
        question_id = score_item.get('question_id')
        score = score_item.get('score')
        max_score = score_item.get('max_score')
        if max_score and max_score > 0:
            question = Question.query.get(question_id)
            if question:
                question.total_attempts = (question.total_attempts or 0) + 1
                question.total_score_rate = (question.total_score_rate or 0) + (score / max_score)
                question.score_data_updated = True
    
    db.session.commit()
    
    return jsonify({'message': '成绩登记成功', 'total_score': total_score})


@papers_bp.route('/<int:paper_id>/my-scores', methods=['GET'])
@jwt_required()
def get_my_scores(paper_id):
    """学生查看自己的成绩"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))
    
    if current_user.role != 'student':
        return jsonify({'error': '仅限学生使用'}), 403
    
    paper = Paper.query.get(paper_id)
    if not paper:
        return jsonify({'error': '试卷不存在'}), 404
    
    # 检查是否分配给自己
    ps = PaperStudent.query.filter_by(paper_id=paper_id, student_id=current_user.id).first()
    if not ps:
        return jsonify({'error': '权限不足'}), 403
    
    # 检查是否已评分
    if ps.status != 'graded':
        return jsonify({'error': '成绩尚未公布'}), 403
    
    scores = [s.to_dict() for s in ps.scores]
    
    return jsonify({
        'total_score': ps.total_score,
        'scores': scores
    })


# ==================== 我的考试 ====================

@papers_bp.route('/my-exams', methods=['GET'])
@jwt_required()
def get_my_exams():
    """学生查看自己参加的考试列表"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))

    if current_user.role != 'student':
        return jsonify({'error': '仅限学生使用'}), 403

    # 获取学生加入的所有班级
    class_students = ClassStudent.query.filter_by(
        student_id=current_user.id, status='accepted'
    ).all()
    class_ids = [cs.class_id for cs in class_students]

    if not class_ids:
        return jsonify({'exams': []})

    # 获取这些班级的所有发布记录
    publishes = PaperPublish.query.filter(
        PaperPublish.class_id.in_(class_ids)
    ).all()

    exams = []
    for p in publishes:
        paper = Paper.query.get(p.paper_id)
        if not paper:
            continue

        # 检查是否已结束登记
        exam = ClassExam.query.filter_by(
            class_id=p.class_id,
            publish_id=p.id
        ).first()

        # 判断考试状态
        status = get_exam_status(p)

        exams.append({
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
            'scoring_finished': exam is not None,
            'allow_view_after_exam': p.allow_view_after_exam
        })

    exams.sort(key=lambda x: x.get('published_at') or '', reverse=True)

    return jsonify({'exams': exams})


@papers_bp.route('/my-exams/<int:publish_id>', methods=['GET'])
@jwt_required()
def get_my_exam_detail(publish_id):
    """学生查看考试详情（题目列表、成绩、PDF）"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))

    if current_user.role != 'student':
        return jsonify({'error': '仅限学生使用'}), 403

    publish = PaperPublish.query.get(publish_id)
    if not publish:
        return jsonify({'error': '考试不存在'}), 404

    # 检查学生是否属于该班级
    is_in_class = ClassStudent.query.filter_by(
        class_id=publish.class_id, student_id=current_user.id, status='accepted'
    ).first() is not None

    if not is_in_class:
        return jsonify({'error': '权限不足'}), 403

    paper = Paper.query.get(publish.paper_id)
    if not paper:
        return jsonify({'error': '试卷不存在'}), 404

    # 检查是否已结束登记
    exam = ClassExam.query.filter_by(
        class_id=publish.class_id,
        publish_id=publish_id
    ).first()

    # 获取题目列表
    questions_data = json.loads(paper.questions_data) if paper.questions_data else []
    questions = []
    for item in questions_data:
        question = Question.query.get(item['question_id'])
        if question:
            questions.append({
                'question_id': question.id,
                'question_title': question.question_title or question.title,
                'content': question.content,
                'answer': question.answer,
                'content_images': question.content_images,
                'answer_images': question.answer_images,
                'max_score': item.get('score', 10),
                'difficulty': question.difficulty
            })

    # 获取学生成绩
    student_scores = {}
    has_scores = False
    if exam and exam.scores_snapshot:
        scores_list = json.loads(exam.scores_snapshot)
        for s in scores_list:
            if s['student_id'] == current_user.id:
                student_scores = s.get('scores', {})
                has_scores = True
                break

    # 判断是否允许查看
    can_view = False
    if exam and exam.finished_at:
        if publish.allow_view_after_exam:
            can_view = True

    return jsonify({
        'paper': {
            'id': paper.id,
            'title': paper.title,
            'total_score': paper.total_score,
            'difficulty': paper.difficulty,
            'exam_date': publish.exam_date.isoformat() if publish.exam_date else None,
            'start_time': publish.start_time,
            'end_time': publish.end_time,
            'allow_view_after_exam': publish.allow_view_after_exam
        },
        'questions': questions,
        'student_scores': student_scores,
        'has_scores': has_scores,
        'can_view': can_view,
        'scoring_finished': exam is not None
    })


@papers_bp.route('/<int:paper_id>/publish', methods=['POST'])
@jwt_required()
def publish_paper(paper_id):
    """发布试卷到班级，学生可以看到考试信息"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))

    paper = Paper.query.get(paper_id)
    if not paper:
        return jsonify({'error': '试卷不存在'}), 404

    data = request.get_json() or {}
    class_id = data.get('class_id')
    exam_date_str = data.get('exam_date')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    allow_view_after_exam = data.get('allow_view_after_exam', False)

    if not class_id:
        return jsonify({'error': '请先选择考试班级'}), 400

    # 检查班级是否存在
    class_ = Class.query.get(class_id)
    if not class_:
        return jsonify({'error': '班级不存在'}), 404

    # 只有创建者或管理员可以发布
    if current_user.role != 'admin' and paper.created_by != current_user.id:
        return jsonify({'error': '权限不足'}), 403

    # 解析考试日期
    exam_date = None
    if exam_date_str:
        try:
            exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    # 创建发布记录（每次发布创建一个独立的考试实例）
    publish = PaperPublish(
        paper_id=paper_id,
        class_id=class_id,
        exam_date=exam_date,
        start_time=start_time,
        end_time=end_time,
        allow_view_after_exam=allow_view_after_exam,
        published_by=current_user.id
    )
    db.session.add(publish)

    # 更新试卷状态（如果还没有发布过）
    if paper.status != 'published':
        paper.status = 'published'

    db.session.commit()

    return jsonify({
        'message': f'试卷已发布到班级 {class_.name}',
        'publish_id': publish.id
    })


# ==================== 审核功能 ====================

@papers_bp.route('/pending-review', methods=['GET'])
@jwt_required()
def get_pending_review_papers():
    """获取待审核的试卷列表（审核者使用）"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))
    
    # 只有教师和管理员可以作为审核者
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({'error': '权限不足'}), 403
    
    query = Paper.query.filter_by(needs_review=True, review_status='pending')
    
    # 非管理员只能看到指定自己审核的试卷
    if current_user.role != 'admin':
        query = query.filter_by(reviewer_id=current_user.id)
    
    papers = query.order_by(Paper.created_at.desc()).all()
    
    return jsonify({'papers': [p.to_dict() for p in papers]})


@papers_bp.route('/fit-difficulty-mapping', methods=['POST'])
@jwt_required()
def fit_difficulty_mapping():
    """对 ExamScoreRecord 中的所有数据进行逻辑斯蒂回归拟合"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))

    if current_user.role not in ['admin', 'teacher']:
        return jsonify({'error': '权限不足'}), 403

    # 从 ExamScoreRecord 获取所有数据点
    records = ExamScoreRecord.query.all()

    if not records:
        return jsonify({'message': '没有需要拟合的数据'}), 200

    from scipy.optimize import curve_fit

    # 收集所有数据点 (难度系数, 得分率)
    x_data = []  # 难度系数
    y_data = []  # 得分率

    for r in records:
        x_data.append(r.difficulty)
        y_data.append(r.score_rate)

    if len(x_data) < 4:
        return jsonify({'error': f'数据点不足，当前{len(x_data)}个，至少需要4个才能拟合'}), 400

    try:
        # 逻辑斯蒂函数: y = a + (b-a)/(1+exp(-c*(x-d)))
        # a: 高难度端得分率上限（接近1），b: 低难度端得分率下限（接近0）
        # c: 陡峭程度，d: 拐点（中间难度）
        p0 = [0.95, 0.05, 1.5, 2.5]
        bounds = ([0.7, 0.0, 0.1, 0.1], [1.0, 0.3, 10, 4.9])

        popt, _ = curve_fit(logistic, np.array(x_data), np.array(y_data), p0=p0, bounds=bounds, maxfev=10000)

        a, b, c, d = popt

        # 更新所有题目的拟合参数
        questions = Question.query.all()
        for q in questions:
            q.fit_param_a = float(a)
            q.fit_param_b = float(b)
            q.fit_param_c = float(c)
            q.fit_param_d = float(d)
            q.last_fitted_at = now_bjt()

        db.session.commit()

        # 生成映射表
        mapping = build_difficulty_mapping(a, b, c, d)

        return jsonify({
            'message': '拟合完成',
            'data_points': len(x_data),
            'params': {'a': float(a), 'b': float(b), 'c': float(c), 'd': float(d)},
            'mapping': mapping
        })

    except Exception as e:
        return jsonify({'error': f'拟合失败: {str(e)}'}), 500


@papers_bp.route('/difficulty-mapping', methods=['GET'])
@jwt_required()
def get_difficulty_mapping():
    """获取当前难度映射表"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))

    if current_user.role not in ['admin', 'teacher']:
        return jsonify({'error': '权限不足'}), 403

    # 获取任意一个已拟合的题目参数（所有题目参数相同）
    question = Question.query.filter(Question.fit_param_a.isnot(None)).first()

    if not question:
        return jsonify({'message': '尚未进行拟合', 'mapping': [], 'need_fit': True}), 200

    a, b, c, d = question.fit_param_a, question.fit_param_b, question.fit_param_c, question.fit_param_d

    # 检查是否有数据需要重新拟合
    need_fit = Question.query.filter(Question.score_data_updated == True).count() > 0

    # 生成映射表
    mapping = build_difficulty_mapping(a, b, c, d)

    return jsonify({
        'mapping': mapping,
        'params': {'a': float(a), 'b': float(b), 'c': float(c), 'd': float(d)},
        'need_fit': need_fit,
        'last_fitted_at': question.last_fitted_at.isoformat() if question.last_fitted_at else None
    })


@papers_bp.route('/<int:paper_id>/class-scores', methods=['GET'])
@jwt_required()
def get_paper_class_scores(paper_id):
    """获取试卷关联班级的学生成绩（用于成绩登记页面）"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))

    paper = Paper.query.get(paper_id)
    if not paper:
        return jsonify({'error': '试卷不存在'}), 404

    if current_user.role != 'admin' and paper.created_by != current_user.id:
        return jsonify({'error': '权限不足'}), 403

    if not paper.class_id:
        return jsonify({'error': '该试卷未关联班级'}), 400

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

    # 获取班级中已接受的学生
    class_students = ClassStudent.query.filter_by(
        class_id=paper.class_id, status='accepted'
    ).all()

    students = []
    for cs in class_students:
        student = User.query.get(cs.student_id)
        if not student:
            continue

        # 获取该学生该试卷的成绩
        ps = PaperStudent.query.filter_by(
            paper_id=paper_id, student_id=cs.student_id
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
        'students': students
    })


@papers_bp.route('/<int:paper_id>/finish-scoring', methods=['POST'])
@jwt_required()
def finish_scoring(paper_id):
    """结束登记：创建考试快照，保存得分记录到 ExamScoreRecord"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))

    paper = Paper.query.get(paper_id)
    if not paper:
        return jsonify({'error': '试卷不存在'}), 404

    data = request.get_json()
    publish_id = data.get('publish_id')

    if not publish_id:
        return jsonify({'error': '缺少发布记录ID'}), 400

    publish = PaperPublish.query.get(publish_id)
    if not publish:
        return jsonify({'error': '发布记录不存在'}), 404

    class_id = publish.class_id

    if not class_id:
        return jsonify({'error': '试卷未关联班级'}), 400

    # 检查权限：只有班级教师或管理员可以结束登记
    if current_user.role != 'admin':
        class_info = Class.query.get(class_id)
        if not class_info or class_info.teacher_id != current_user.id:
            return jsonify({'error': '权限不足'}), 403

    # 检查是否已有快照
    existing_exam = ClassExam.query.filter_by(
        class_id=class_id,
        publish_id=publish_id
    ).first()
    if existing_exam:
        return jsonify({'error': '该考试已结束登记，无法重复操作'}), 400

    # 获取试卷题目信息
    questions_data = json.loads(paper.questions_data) if paper.questions_data else []
    questions_snapshot = []
    for item in questions_data:
        question = Question.query.get(item['question_id'])
        if question:
            questions_snapshot.append({
                'question_id': question.id,
                'title': question.question_title or question.title,
                'max_score': item.get('score', 10)
            })

    # 获取班级中已接受的学生及其成绩
    class_students = ClassStudent.query.filter_by(
        class_id=class_id, status='accepted'
    ).all()

    scores_snapshot = []
    for cs in class_students:
        student = User.query.get(cs.student_id)
        if not student:
            continue

        # 获取该学生该试卷的成绩
        ps = PaperStudent.query.filter_by(
            paper_id=paper_id, student_id=cs.student_id
        ).first()

        scores = {}
        total_score = 0
        if ps:
            total_score = ps.total_score or 0
            for ss in ps.scores:
                scores[str(ss.question_id)] = ss.score

        scores_snapshot.append({
            'student_id': student.id,
            'student_name': student.real_name or student.username,
            'scores': scores,
            'total_score': total_score
        })

    # 创建考试快照
    exam = ClassExam(
        class_id=class_id,
        paper_id=paper_id,
        publish_id=publish_id,
        paper_title=paper.title,
        paper_total_score=paper.total_score,
        paper_difficulty=paper.difficulty,
        exam_date=publish.exam_date,
        start_time=publish.start_time,
        end_time=publish.end_time,
        questions_snapshot=json.dumps(questions_snapshot, ensure_ascii=False),
        scores_snapshot=json.dumps(scores_snapshot, ensure_ascii=False),
        finished_by=current_user.id
    )
    db.session.add(exam)

    # 保存得分记录到 ExamScoreRecord（用于逻辑斯蒂拟合）
    # 每条记录 = (题目难度系数, 学生得分率)
    absent_student_ids = set(data.get('absent_student_ids', []) or [])
    score_records_count = 0
    for cs in class_students:
        if cs.student_id in absent_student_ids:
            continue  # 跳过未参加考试的学生
        student = User.query.get(cs.student_id)
        if not student:
            continue
        ps = PaperStudent.query.filter_by(
            paper_id=paper_id, student_id=cs.student_id
        ).first()
        if not ps:
            continue
        for ss in ps.scores:
            question = Question.query.get(ss.question_id)
            if question and question.difficulty is not None and ss.max_score > 0:
                score_rate = ss.score / ss.max_score
                record = ExamScoreRecord(
                    publish_id=publish_id,
                    question_id=ss.question_id,
                    student_id=cs.student_id,
                    difficulty=question.difficulty,
                    score_rate=score_rate
                )
                db.session.add(record)
                score_records_count += 1

    db.session.commit()

    return jsonify({
        'message': '登记已结束',
        'exam_id': exam.id,
        'score_records_saved': score_records_count
    })


@papers_bp.route('/<int:paper_id>/review', methods=['POST'])
@jwt_required()
def review_paper(paper_id):
    """审核试卷"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))
    
    paper = Paper.query.get(paper_id)
    if not paper:
        return jsonify({'error': '试卷不存在'}), 404
    
    # 检查权限
    if current_user.role != 'admin':
        if paper.reviewer_id != current_user.id:
            return jsonify({'error': '您不是该试卷的指定审核者'}), 403
    
    data = request.get_json()
    review_status = data.get('review_status')  # approved, rejected
    review_comment = data.get('review_comment')
    
    if review_status not in ['approved', 'rejected']:
        return jsonify({'error': '无效的审核状态'}), 400
    
    paper.review_status = review_status
    paper.review_comment = review_comment
    paper.reviewed_at = now_bjt()
    
    db.session.commit()
    
    return jsonify({
        'message': '审核完成',
        'review_status': review_status,
        'paper': paper.to_dict()
    })


@papers_bp.route('/my-reviews', methods=['GET'])
@jwt_required()
def get_my_reviews():
    """获取我审核过的试卷"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))
    
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({'error': '权限不足'}), 403
    
    papers = Paper.query.filter(
        Paper.reviewer_id == current_user.id,
        Paper.review_status != 'pending'
    ).order_by(Paper.reviewed_at.desc()).all()
    
    return jsonify({'papers': [p.to_dict() for p in papers]})
