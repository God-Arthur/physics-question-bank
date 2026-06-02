from datetime import datetime, timezone, timedelta
from app.utils.database import db
from werkzeug.security import generate_password_hash, check_password_hash

# 北京时区 UTC+8
BJT = timezone(timedelta(hours=8))

def now_bjt():
    return datetime.now(BJT)


class User(db.Model):
    """用户模型"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # admin, teacher, student
    real_name = db.Column(db.String(50))
    password_changed = db.Column(db.Boolean, default=False)  # 是否已修改过密码
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # 创建者ID
    created_at = db.Column(db.DateTime, default=now_bjt)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        # manager_name 用于学生显示管理者（教师或管理员）
        manager_name = None
        if self.created_by:
            manager = User.query.get(self.created_by)
            if manager and manager.role in ['teacher', 'admin']:
                manager_name = manager.real_name or manager.username
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'real_name': self.real_name,
            'password_changed': self.password_changed,
            'created_by': self.created_by,
            'manager_name': manager_name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Institute(db.Model):
    """出题机构模型"""
    __tablename__ = 'institutes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # 机构名称
    code = db.Column(db.String(3), unique=True, nullable=False)  # 机构代码（3位大写字母）
    created_at = db.Column(db.DateTime, default=now_bjt)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Question(db.Model):
    """题目模型"""
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)

    # 题目内容
    title = db.Column(db.String(200))  # 试卷标题
    question_title = db.Column(db.String(200))  # 题目标题
    content = db.Column(db.Text, nullable=False)  # 题干内容（支持LaTeX）
    answer = db.Column(db.Text, nullable=False)  # 答案内容（支持LaTeX）

    # 题目类型：theory（理论题）, experiment（实验理论题）
    question_type = db.Column(db.String(20), nullable=False, default='theory')

    # 分类
    difficulty = db.Column(db.Float, nullable=False, default=3.0)  # 0.0~5.0 难度值
    source_type = db.Column(db.String(20))  # past_exam, mock
    source_institute = db.Column(db.String(3))  # 机构代码（3位大写字母）
    source_info = db.Column(db.String(200))  # 来源详细信息
    author = db.Column(db.String(50))  # 作者
    year = db.Column(db.Integer)  # 年份

    # 分值（默认40分）
    default_score = db.Column(db.Integer, default=40)

    # 成绩数据统计（用于难度系数拟合）
    score_data_updated = db.Column(db.Boolean, default=False)  # 是否有新的成绩数据待处理
    total_attempts = db.Column(db.Integer, default=0)  # 总答题次数
    total_score_rate = db.Column(db.Float, default=0)  # 累计得分率（用于计算平均得分率）

    # 拟合函数参数（逻辑斯蒂函数）
    fit_param_a = db.Column(db.Float)  # 参数a
    fit_param_b = db.Column(db.Float)  # 参数b
    fit_param_c = db.Column(db.Float)  # 参数c
    fit_param_d = db.Column(db.Float)  # 参数d
    last_fitted_at = db.Column(db.DateTime)  # 上次拟合时间

    # 附件
    scan_image = db.Column(db.String(200))  # 扫描件图片路径
    content_images = db.Column(db.Text)  # 题干图片（JSON数组）
    answer_images = db.Column(db.Text)  # 答案图片（JSON数组）

    # 元数据
    created_at = db.Column(db.DateTime, default=now_bjt)
    updated_at = db.Column(db.DateTime, default=now_bjt, onupdate=now_bjt)
    use_count = db.Column(db.Integer, default=0)  # 使用次数

    def to_dict(self):
        # 获取机构名称
        source_institute_name = None
        if self.source_institute:
            from app.models import Institute
            institute = Institute.query.filter_by(code=self.source_institute).first()
            if institute:
                source_institute_name = institute.name
        
        return {
            'id': self.id,
            'title': self.title,
            'question_title': self.question_title,
            'content': self.content,
            'answer': self.answer,
            'question_type': self.question_type,
            'difficulty': self.difficulty,
            'source_type': self.source_type,
            'source_institute': self.source_institute,
            'source_institute_name': source_institute_name,
            'source_info': self.source_info,
            'author': self.author,
            'year': self.year,
            'default_score': self.default_score,
            'scan_image': self.scan_image,
            'content_images': self.content_images,
            'answer_images': self.answer_images,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'use_count': self.use_count,
            'score_data_updated': self.score_data_updated,
            'total_attempts': self.total_attempts,
            'avg_score_rate': (self.total_score_rate / self.total_attempts) if self.total_attempts > 0 else 0,
            'fit_param_a': self.fit_param_a,
            'fit_param_b': self.fit_param_b,
            'fit_param_c': self.fit_param_c,
            'fit_param_d': self.fit_param_d,
            'last_fitted_at': self.last_fitted_at.isoformat() if self.last_fitted_at else None
        }


class Paper(db.Model):
    """试卷模型"""
    __tablename__ = 'papers'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    exam_date = db.Column(db.Date)  # 考试日期
    start_time = db.Column(db.String(5))  # 开始时间 HH:mm
    end_time = db.Column(db.String(5))  # 结束时间 HH:mm
    duration = db.Column(db.Integer, default=180)  # 考试时长（分钟），默认180分钟
    total_score = db.Column(db.Integer)  # 总分

    # 试卷信息（JSON格式存储题目ID列表和分数）
    questions_data = db.Column(db.Text)  # JSON: [{"question_id": 1, "score": 10}, ...]
    
    # LaTeX 源文件内容（用于重新生成PDF）
    tex_content = db.Column(db.Text)  # 试卷LaTeX源文件
    answer_tex_content = db.Column(db.Text)  # 答案LaTeX源文件

    # 考试班级
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True)
    allow_view_after_exam = db.Column(db.Boolean, default=False)  # 考试结束后允许学生查看试卷

    # 难度系数（加权平均）
    difficulty = db.Column(db.Float, default=0)

    # 审核相关
    needs_review = db.Column(db.Boolean, default=False)  # 是否需要审核
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 审核者ID
    review_note = db.Column(db.Text)  # 给审核者的备注
    review_comment = db.Column(db.Text)  # 审核意见
    review_status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    reviewed_at = db.Column(db.DateTime)

    # 元数据
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=now_bjt)
    updated_at = db.Column(db.DateTime, default=now_bjt, onupdate=now_bjt)
    status = db.Column(db.String(20), default='draft')  # draft, published, finished

    # 关系
    creator = db.relationship('User', foreign_keys=[created_by], backref='papers')
    reviewer = db.relationship('User', foreign_keys=[reviewer_id], backref='reviewed_papers')
    exam_students = db.relationship('PaperStudent', backref='paper', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'exam_date': self.exam_date.isoformat() if self.exam_date else None,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'total_score': self.total_score,
            'questions_data': self.questions_data,
            'class_id': self.class_id,
            'allow_view_after_exam': self.allow_view_after_exam,
            'difficulty': self.difficulty,
            'status': self.status,
            'needs_review': self.needs_review,
            'reviewer_id': self.reviewer_id,
            'reviewer_name': self.reviewer.real_name if self.reviewer else None,
            'review_note': self.review_note,
            'review_comment': self.review_comment,
            'review_status': self.review_status,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Class(db.Model):
    """班级模型"""
    __tablename__ = 'classes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=now_bjt)

    # 关系
    teacher = db.relationship('User', backref='classes')
    students = db.relationship('ClassStudent', backref='class_', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        # 只计算已接受的学生
        accepted_count = self.students.filter_by(status='accepted').count()
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'teacher_id': self.teacher_id,
            'teacher_name': self.teacher.real_name if self.teacher else None,
            'student_count': accepted_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ClassStudent(db.Model):
    """班级学生关联模型"""
    __tablename__ = 'class_students'

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted
    joined_at = db.Column(db.DateTime, default=now_bjt)

    # 关系
    student = db.relationship('User', backref='class_memberships')

    __table_args__ = (db.UniqueConstraint('class_id', 'student_id', name='unique_class_student'),)


class ClassExam(db.Model):
    """班级考试记录（考试结束后的快照，锁定成绩和题目信息）"""
    __tablename__ = 'class_exams'

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    paper_id = db.Column(db.Integer, db.ForeignKey('papers.id'), nullable=True)  # 原试卷ID（可能已被删除）
    publish_id = db.Column(db.Integer, db.ForeignKey('paper_publishes.id'), nullable=True)  # 发布记录ID

    # 试卷快照数据
    paper_title = db.Column(db.String(200), nullable=False)
    paper_total_score = db.Column(db.Integer, default=0)
    paper_difficulty = db.Column(db.Float, default=0)
    exam_date = db.Column(db.Date)
    start_time = db.Column(db.String(10))
    end_time = db.Column(db.String(10))

    # 题目快照（JSON格式）
    questions_snapshot = db.Column(db.Text)  # [{question_id, title, max_score}, ...]

    # 学生成绩快照（JSON格式）
    scores_snapshot = db.Column(db.Text)  # [{student_id, student_name, scores, total_score}, ...]

    finished_at = db.Column(db.DateTime, default=now_bjt)
    finished_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    def to_dict(self):
        return {
            'id': self.id,
            'class_id': self.class_id,
            'paper_id': self.paper_id,
            'publish_id': self.publish_id,
            'title': self.paper_title,
            'total_score': self.paper_total_score,
            'difficulty': self.paper_difficulty,
            'exam_date': self.exam_date.isoformat() if self.exam_date else None,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'questions': json.loads(self.questions_snapshot) if self.questions_snapshot else [],
            'students': json.loads(self.scores_snapshot) if self.scores_snapshot else [],
            'finished_at': self.finished_at.isoformat() if self.finished_at else None
        }


class PaperPublish(db.Model):
    """试卷发布记录（支持发布到多个班级）"""
    __tablename__ = 'paper_publishes'

    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('papers.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    allow_view_after_exam = db.Column(db.Boolean, default=False)
    published_at = db.Column(db.DateTime, default=now_bjt)
    published_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    def to_dict(self):
        return {
            'id': self.id,
            'paper_id': self.paper_id,
            'class_id': self.class_id,
            'allow_view_after_exam': self.allow_view_after_exam,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'published_by': self.published_by
        }


class PaperStudent(db.Model):
    """试卷学生关联模型（考试分配）"""
    __tablename__ = 'paper_students'

    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('papers.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='assigned')  # assigned, submitted, graded
    assigned_at = db.Column(db.DateTime, default=now_bjt)
    submitted_at = db.Column(db.DateTime)
    total_score = db.Column(db.Integer)  # 总分

    # 关系
    student = db.relationship('User', backref='paper_assignments')
    scores = db.relationship('StudentScore', backref='paper_student', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (db.UniqueConstraint('paper_id', 'student_id', name='unique_paper_student'),)

    def to_dict(self):
        return {
            'id': self.id,
            'paper_id': self.paper_id,
            'student_id': self.student_id,
            'student_name': self.student.real_name if self.student else None,
            'status': self.status,
            'total_score': self.total_score,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None
        }


class StudentScore(db.Model):
    """学生各题得分模型"""
    __tablename__ = 'student_scores'

    id = db.Column(db.Integer, primary_key=True)
    paper_student_id = db.Column(db.Integer, db.ForeignKey('paper_students.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)  # 得分
    max_score = db.Column(db.Integer, nullable=False)  # 满分
    comment = db.Column(db.Text)  # 评语
    graded_at = db.Column(db.DateTime, default=now_bjt)
    graded_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # 关系
    question = db.relationship('Question')
    grader = db.relationship('User')

    __table_args__ = (db.UniqueConstraint('paper_student_id', 'question_id', name='unique_question_score'),)

    def to_dict(self):
        return {
            'id': self.id,
            'question_id': self.question_id,
            'question_content': self.question.content[:100] if self.question else None,
            'score': self.score,
            'max_score': self.max_score,
            'comment': self.comment,
            'graded_at': self.graded_at.isoformat() if self.graded_at else None
        }
