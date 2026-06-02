"""生成测试试卷和题目数据"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Question, User

app = create_app()

with app.app_context():
    # 获取一个教师用户作为创建者
    teacher = User.query.filter_by(role='teacher').first()
    if not teacher:
        teacher = User.query.filter_by(role='admin').first()
    
    if not teacher:
        print("没有找到教师或管理员用户，请先创建用户")
        exit(1)
    
    print(f"使用用户: {teacher.username} (ID: {teacher.id})")
    
    # 测试试卷数据
    test_papers = [
        {
            'title': '第42届全国中学生物理竞赛复赛',
            'questions': [
                {'question_title': '导电介质', 'content': '一无限大均匀导电介质平板，厚度为$d$，电导率为$\\sigma$，相对介电常数为$\\varepsilon_r$。一束频率为$\\omega$的电磁波垂直入射到平板上，求反射系数和透射系数。', 'answer': '根据麦克斯韦方程组和边界条件，可求得反射系数$R = \\left|\\frac{Z_2 - Z_1}{Z_2 + Z_1}\\right|^2$，其中$Z_2$为导电介质的波阻抗。', 'difficulty': 3.5, 'question_type': 'theory'},
                {'question_title': '带电粒子在磁场中的运动', 'content': '一质量为$m$、电荷量为$q$的粒子在均匀磁场$\\vec{B}$中运动。初始时刻粒子位于原点，速度为$v_0$，方向与磁场成$\\theta$角。求粒子的运动轨迹。', 'answer': '粒子做螺旋运动，回旋半径$r_c = \\frac{mv_0\\sin\\theta}{qB}$，螺距$h = \\frac{2\\pi mv_0\\cos\\theta}{qB}$。', 'difficulty': 2.5, 'question_type': 'theory'},
                {'question_title': '热力学过程', 'content': '一理想气体经历如下循环过程：先等温膨胀，再等压压缩，最后等容升温回到初态。设初态温度为$T_0$，体积为$V_0$，等温膨胀后体积变为$2V_0$。求循环效率。', 'answer': '循环效率$\\eta = 1 - \\frac{Q_c}{Q_h}$，其中$Q_h$为吸热，$Q_c$为放热。代入计算可得$\\eta = 1 - \\frac{\\ln 2 + \\frac{1}{2}}{\\ln 2 + 1}$。', 'difficulty': 3.0, 'question_type': 'theory'},
            ]
        },
        {
            'title': '第41届全国中学生物理竞赛复赛',
            'questions': [
                {'question_title': '光学干涉', 'content': '一束波长为$\\lambda$的单色光垂直入射到一薄膜上，薄膜折射率为$n$，厚度为$d$。求反射光干涉加强的条件。', 'answer': '反射光干涉加强条件：$2nd = (k + \\frac{1}{2})\\lambda$，其中$k = 0, 1, 2, ...$', 'difficulty': 2.0, 'question_type': 'theory'},
                {'question_title': '刚体转动', 'content': '一均匀圆盘质量为$M$，半径为$R$，可绕通过中心且垂直于盘面的轴自由转动。一质量为$m$的小虫从圆盘边缘沿半径方向爬向中心，求圆盘转过的角度。', 'answer': '由角动量守恒，$I_1\\omega_1 = I_2\\omega_2$。设小虫爬行时间为$t$，圆盘转角$\\phi = \\int_0^t \\omega \\, dt$。', 'difficulty': 3.5, 'question_type': 'theory'},
            ]
        },
        {
            'title': '兰阶物理竞赛模拟卷一',
            'questions': [
                {'question_title': '电场中的导体', 'content': '一导体球半径为$R$，带有电荷$Q$。在距球心$d > R$处放置一点电荷$q$。求导体球的电势。', 'answer': '导体球电势$V = \\frac{Q}{4\\pi\\varepsilon_0 R}$，与点电荷位置无关。', 'difficulty': 2.5, 'question_type': 'theory'},
                {'question_title': '简谐振动', 'content': '一弹簧振子，弹簧劲度系数为$k$，振子质量为$m$。初始时刻振子位于平衡位置，速度为$v_0$。求振子的运动方程。', 'answer': '运动方程$x(t) = A\\sin(\\omega t)$，其中$A = \\frac{v_0}{\\omega}$，$\\omega = \\sqrt{\\frac{k}{m}}$。', 'difficulty': 1.5, 'question_type': 'theory'},
                {'question_title': '流体力学', 'content': '一圆柱形容器中装有密度为$\\rho$的液体，液面高度为$h$。容器底部有一小孔，液体从小孔流出。求液体流出的速度。', 'answer': '由托里拆利定理，$v = \\sqrt{2gh}$。', 'difficulty': 2.0, 'question_type': 'theory'},
            ]
        },
        {
            'title': '独立题目',
            'questions': [
                {'question_title': '相对论效应', 'content': '一飞船以速度$v = 0.8c$相对于地球运动。飞船上有一尺子，静止长度为$L_0$。求地球上观测者测得的尺子长度。', 'answer': '由洛伦兹收缩，$L = L_0\\sqrt{1 - \\frac{v^2}{c^2}} = 0.6L_0$。', 'difficulty': 2.5, 'question_type': 'theory'},
            ]
        }
    ]
    
    created_count = 0
    for paper in test_papers:
        for q in paper['questions']:
            # 检查是否已存在相同题目
            existing = Question.query.filter_by(
                title=paper['title'],
                question_title=q['question_title']
            ).first()
            
            if not existing:
                question = Question(
                    title=paper['title'],
                    question_title=q['question_title'],
                    content=q['content'],
                    answer=q['answer'],
                    difficulty=q['difficulty'],
                    question_type=q['question_type'],
                    source_type='past_exam' if '全国' in paper['title'] else 'mock',
                    year=2024 if '全国' in paper['title'] else None,
                    source_institute='LAN' if '兰阶' in paper['title'] else None,
                    default_score=40,
                    created_by=teacher.id,
                    status='approved'
                )
                db.session.add(question)
                created_count += 1
                print(f"创建题目: {paper['title']} - {q['question_title']}")
    
    db.session.commit()
    print(f"\n完成！共创建 {created_count} 道题目")
