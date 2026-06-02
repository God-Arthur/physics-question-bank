"""初始化脚本：清空所有业务数据，重置管理员密码"""
import sys
sys.path.insert(0, '/home/redaunt/physics-question-bank/backend')

from app import create_app
from app.utils.database import db
from app.models import User, Class, ClassStudent, Paper, PaperPublish, PaperStudent, StudentScore, ClassExam, Question

app = create_app()
with app.app_context():
    print("=" * 50)
    print("开始初始化...")
    print("=" * 50)

    # 1. 删除所有教师和学生账户（保留管理员）
    deleted_users = User.query.filter(User.role.in_(['teacher', 'student'])).delete()
    print(f"✓ 已删除 {deleted_users} 个教师/学生账户")

    # 2. 重置管理员密码为 admin1906，设置 password_changed = False
    admin = User.query.filter_by(role='admin').first()
    if admin:
        admin.set_password('admin1906')
        admin.password_changed = False
        print(f"✓ 管理员密码已重置为 admin1906，password_changed 已设为 False")
    else:
        print("⚠ 未找到管理员账户")

    # 3. 删除所有班级（ClassStudent 通过 cascade 自动删除）
    deleted_classes = Class.query.delete()
    print(f"✓ 已删除 {deleted_classes} 个班级")

    # 4. 删除所有已登记的考试成绩
    deleted_student_scores = StudentScore.query.delete()
    print(f"✓ 已删除 {deleted_student_scores} 条学生得分记录")

    deleted_paper_students = PaperStudent.query.delete()
    print(f"✓ 已删除 {deleted_paper_students} 条试卷学生关联")

    deleted_class_exams = ClassExam.query.delete()
    print(f"✓ 已删除 {deleted_class_exams} 条考试登记记录")

    deleted_publishes = PaperPublish.query.delete()
    print(f"✓ 已删除 {deleted_publishes} 条发布记录")

    # 5. 删除所有试卷
    deleted_papers = Paper.query.delete()
    print(f"✓ 已删除 {deleted_papers} 份试卷")

    # 6. 删除所有题目
    deleted_questions = Question.query.delete()
    print(f"✓ 已删除 {deleted_questions} 道题目")

    # 7. 清理逻辑斯蒂拟合参数（题目已全部删除，此步为冗余保障）
    # 题目已全部删除，拟合参数自然不存在

    db.session.commit()
    print("=" * 50)
    print("初始化完成！")
    print("=" * 50)
