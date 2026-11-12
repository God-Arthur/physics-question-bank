"""回归测试：覆盖这次修掉的后端行为。"""
import os
import tempfile
import unittest
from datetime import timedelta

_DB_PATH = tempfile.mktemp(suffix='.db')
os.environ['DATABASE_URL'] = 'sqlite:///' + _DB_PATH

from app import create_app
from app.models import ClassExam, Question, now_bjt
from app.utils.database import db
from app.utils.pdf_generator import escape_latex


class RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        cls.ctx.pop()
        if os.path.exists(_DB_PATH):
            os.remove(_DB_PATH)

    def login(self, username, password):
        res = self.client.post('/api/auth/login', json={'username': username, 'password': password})
        self.assertEqual(res.status_code, 200, res.get_json())
        token = res.get_json()['access_token']
        return {'Authorization': f'Bearer {token}'}

    def test_admin_seed_and_login(self):
        headers = self.login('admin', 'admin1906')
        me = self.client.get('/api/auth/me', headers=headers)
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.get_json()['user']['role'], 'admin')

    def test_register_is_not_anonymous_and_cannot_create_admin(self):
        open_reg = self.client.post('/api/auth/register', json={'real_name': '路人', 'role': 'admin'})
        self.assertEqual(open_reg.status_code, 401)

        admin = self.login('admin', 'admin1906')
        rejected = self.client.post('/api/auth/register', json={'real_name': '伪管理员', 'role': 'admin'}, headers=admin)
        self.assertEqual(rejected.status_code, 400)

        teacher = self.client.post(
            '/api/auth/register',
            json={'real_name': '张老师', 'role': 'teacher', 'created_by': 999},
            headers=admin,
        )
        self.assertEqual(teacher.status_code, 201, teacher.get_json())
        body = teacher.get_json()
        self.assertTrue(body['username'].startswith('1906'))
        self.assertEqual(body['user']['created_by'], 1)
        self.teacher_username = body['username']
        self.teacher_password = body['password']

    def test_question_bank_pagination_permissions_and_batch_delete(self):
        admin = self.login('admin', 'admin1906')
        student = self.client.post('/api/auth/register', json={'real_name': '李同学', 'role': 'student'}, headers=admin)
        self.assertEqual(student.status_code, 201, student.get_json())
        student_headers = self.login(student.get_json()['username'], student.get_json()['password'])
        forbidden = self.client.get('/api/questions', headers=student_headers)
        self.assertEqual(forbidden.status_code, 403)

        for index in range(25):
            created = self.client.post('/api/questions', json={
                'title': f'分页卷{index}',
                'question_title': f'第{index}题',
                'content': f'内容 {index} $a<b$',
                'answer': '答案',
            }, headers=admin)
            self.assertEqual(created.status_code, 201, created.get_json())

        page2 = self.client.get('/api/questions?page=2&per_page=10&keyword=分页卷', headers=admin)
        self.assertEqual(page2.status_code, 200)
        payload = page2.get_json()
        self.assertEqual(payload['total'], 25)
        self.assertEqual(len(payload['groups']), 10)
        self.assertEqual(payload['current_page'], 2)

        kept = self.client.post('/api/questions', json={
            'title': '保留卷',
            'content': '保留',
            'answer': '保留答案',
            'content_images': ['keep.jpg'],
        }, headers=admin)
        removed = self.client.post('/api/questions', json={
            'title': '删除卷',
            'content': '删除',
            'answer': '删除答案',
        }, headers=admin)
        self.assertEqual(kept.status_code, 201)
        question_id = kept.get_json()['question']['id']
        deleted = self.client.post('/api/questions/batch-delete', json={
            'paper_keys': ['删除卷'],
            'paper_ids': [1],
        }, headers=admin)
        self.assertEqual(deleted.status_code, 200)
        still_there = self.client.get('/api/questions?paper_uuid=P{}'.format(question_id), headers=admin)
        names = [group['paper_name'] for group in still_there.get_json()['groups']]
        self.assertIn('保留卷', names)
        self.assertNotIn('删除卷', names)

        cleared = self.client.put(f'/api/questions/{question_id}', json={'content_images': []}, headers=admin)
        self.assertEqual(cleared.status_code, 200)
        self.assertIsNone(cleared.get_json()['question']['content_images'])
        self.assertEqual(removed.status_code, 201)

    def test_exam_status_scoring_visibility_and_deletes(self):
        admin = self.login('admin', 'admin1906')
        teacher_res = self.client.post('/api/auth/register', json={'real_name': '王老师', 'role': 'teacher'}, headers=admin)
        other_res = self.client.post('/api/auth/register', json={'real_name': '其他老师', 'role': 'teacher'}, headers=admin)
        student_res = self.client.post('/api/auth/register', json={'real_name': '赵同学', 'role': 'student'}, headers=admin)
        self.assertEqual(teacher_res.status_code, 201)
        teacher = self.login(teacher_res.get_json()['username'], teacher_res.get_json()['password'])
        other = self.login(other_res.get_json()['username'], other_res.get_json()['password'])
        student_body = student_res.get_json()
        student = self.login(student_body['username'], student_body['password'])

        created_class = self.client.post('/api/classes', json={'name': '高二1班'}, headers=teacher)
        self.assertEqual(created_class.status_code, 201, created_class.get_json())
        class_id = created_class.get_json()['class']['id']
        other_class = self.client.post('/api/classes', json={'name': '无关班级'}, headers=other)
        self.assertEqual(other_class.status_code, 201)

        student_id = student_body['user']['id']
        invited = self.client.post(f'/api/classes/{class_id}/students', json={'student_id': student_id}, headers=teacher)
        self.assertEqual(invited.status_code, 200, invited.get_json())
        invitations = self.client.get('/api/classes/invitations', headers=student)
        invitation_id = invitations.get_json()['invitations'][0]['id']
        accepted = self.client.post(f'/api/classes/invitations/{invitation_id}/accept', headers=student)
        self.assertEqual(accepted.status_code, 200)

        question = self.client.post('/api/questions', json={
            'title': '考试题',
            'content': '题干 $x<1$',
            'answer': '标准答案',
            'difficulty': 2,
            'default_score': 10,
        }, headers=admin)
        question_id = question.get_json()['question']['id']
        paper = self.client.post('/api/papers', json={
            'title': '期中考试',
            'questions': [{'question_id': question_id, 'score': 10}],
        }, headers=admin)
        self.assertEqual(paper.status_code, 201, paper.get_json())
        paper_id = paper.get_json()['paper']['id']

        now = now_bjt().replace(tzinfo=None)
        published = self.client.post(f'/api/papers/{paper_id}/publish', json={
            'class_id': class_id,
            'exam_date': (now + timedelta(days=1)).date().isoformat(),
            'start_time': '09:00',
            'end_time': '11:00',
            'allow_view_after_exam': True,
        }, headers=admin)
        self.assertEqual(published.status_code, 200, published.get_json())
        publish_id = published.get_json()['publish_id']

        hidden = self.client.get(f'/api/papers/my-exams/{publish_id}', headers=student)
        self.assertEqual(hidden.status_code, 200, hidden.get_json())
        self.assertFalse(hidden.get_json()['show_questions'])
        self.assertEqual(hidden.get_json()['questions'], [])
        self.assertEqual(hidden.get_json()['status'], '未开始')

        denied = self.client.post(
            f'/api/papers/{paper_id}/students/{student_id}/scores',
            json={'scores': [{'question_id': question_id, 'score': 5, 'max_score': 10}]},
            headers=other,
        )
        self.assertEqual(denied.status_code, 403)

        saved = self.client.post(
            f'/api/papers/{paper_id}/students/{student_id}/scores',
            json={'scores': [{'question_id': question_id, 'score': 5, 'max_score': 10}]},
            headers=teacher,
        )
        self.assertEqual(saved.status_code, 200, saved.get_json())
        saved_again = self.client.post(
            f'/api/papers/{paper_id}/students/{student_id}/scores',
            json={'scores': [{'question_id': question_id, 'score': 8, 'max_score': 10}]},
            headers=teacher,
        )
        self.assertEqual(saved_again.status_code, 200)
        stored = db.session.get(Question, question_id)
        db.session.refresh(stored)
        self.assertEqual(stored.total_attempts, 1)
        self.assertAlmostEqual(stored.total_score_rate, 0.8)

        absent = self.client.post(
            f'/api/papers/{paper_id}/students/{student_id}/scores',
            json={'absent': True},
            headers=teacher,
        )
        self.assertEqual(absent.status_code, 200)
        db.session.refresh(stored)
        self.assertEqual(stored.total_attempts, 0)

        self.client.post(
            f'/api/papers/{paper_id}/students/{student_id}/scores',
            json={'scores': [{'question_id': question_id, 'score': 10, 'max_score': 10}]},
            headers=teacher,
        )
        removed_question = self.client.delete(f'/api/questions/{question_id}', headers=admin)
        self.assertEqual(removed_question.status_code, 200, removed_question.get_json())

        removed_class = self.client.delete(f'/api/classes/{class_id}', headers=teacher)
        self.assertEqual(removed_class.status_code, 200, removed_class.get_json())

        teacher_id = teacher_res.get_json()['user']['id']
        owned_paper = self.client.post('/api/papers', json={
            'title': '老师的卷',
            'questions': [{'question_id': self._any_question(), 'score': 10}],
        }, headers=teacher)
        self.assertEqual(owned_paper.status_code, 201, owned_paper.get_json())
        removed_teacher = self.client.delete(f'/api/auth/users/{teacher_id}', headers=admin)
        self.assertEqual(removed_teacher.status_code, 200, removed_teacher.get_json())

    def test_password_change_requires_old_password_after_first_change(self):
        admin = self.login('admin', 'admin1906')
        created = self.client.post('/api/auth/register', json={'real_name': '改密学生', 'role': 'student'}, headers=admin)
        body = created.get_json()
        headers = self.login(body['username'], body['password'])
        user_id = body['user']['id']
        first = self.client.put(f'/api/auth/users/{user_id}', json={'password': 'newpass1'}, headers=headers)
        self.assertEqual(first.status_code, 200, first.get_json())
        headers = self.login(body['username'], 'newpass1')
        rejected = self.client.put(f'/api/auth/users/{user_id}', json={'password': 'newpass2'}, headers=headers)
        self.assertEqual(rejected.status_code, 400)
        changed = self.client.put(
            f'/api/auth/users/{user_id}',
            json={'password': 'newpass2', 'old_password': 'newpass1'},
            headers=headers,
        )
        self.assertEqual(changed.status_code, 200, changed.get_json())

    def test_exam_status_uses_beijing_time(self):
        from app.routes.classes import get_exam_status

        now = now_bjt().replace(tzinfo=None)

        class Publish:
            pass

        yesterday = Publish()
        yesterday.exam_date = (now - timedelta(days=1)).date()
        yesterday.start_time = '00:00'
        yesterday.end_time = '01:00'
        self.assertEqual(get_exam_status(yesterday), '已结束')

        tomorrow = Publish()
        tomorrow.exam_date = (now + timedelta(days=1)).date()
        tomorrow.start_time = '00:00'
        tomorrow.end_time = '23:00'
        self.assertEqual(get_exam_status(tomorrow), '未开始')

    def test_class_exam_dict_and_latex_escape(self):
        exam = ClassExam(class_id=1, paper_title='快照', questions_snapshot='[]', scores_snapshot='[]')
        payload = exam.to_dict()
        self.assertEqual(payload['questions'], [])
        self.assertEqual(payload['students'], [])

        escaped = escape_latex(r'a\b & c_d')
        self.assertIn(r'\textbackslash{}', escaped)
        self.assertNotIn(r'\textbackslash\{', escaped)
        self.assertIn(r'\&', escaped)
        self.assertIn(r'\_', escaped)
        self.assertIn('$a<b$', escape_latex('前文 $a<b$ 后文'))

    def _any_question(self):
        question = Question.query.first()
        if question:
            return question.id
        created = self.client.post('/api/questions', json={
            'title': '兜底题',
            'content': '题',
            'answer': '答',
        }, headers=self.login('admin', 'admin1906'))
        return created.get_json()['question']['id']


if __name__ == '__main__':
    unittest.main()
