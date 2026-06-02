from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
import json
import time
import uuid
import ast
from app.utils.database import db
from app.models import Question, User
from app.utils.upload_session import (
    cleanup_expired_upload_sessions,
    cleanup_upload_session,
    create_upload_session,
    get_persist_image_dir,
    get_session_dir,
    list_session_files,
    persist_images_from_session,
    read_session_meta,
    rewrite_images_field,
    session_file_path,
    start_periodic_cleanup_thread,
    validate_session_secret,
)

questions_bp = Blueprint('questions', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_pdf_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'


@questions_bp.route('/upload-session', methods=['POST'])
@jwt_required()
def create_session():
    """
    创建一个“上传会话”，用于批量导入/单题编辑时暂存 uploads 文件，
    以便在“提交/取消/超时/登出”时精确清理。
    """
    user_id = get_jwt_identity()
    sess = create_upload_session(current_app, user_id)
    return jsonify({
        "session_id": sess["session_id"],
        "secret": sess["secret"],
        "expires_in_seconds": 600
    })


@questions_bp.route('/upload-session/<session_id>/cleanup', methods=['POST'])
@jwt_required()
def cleanup_session_authed(session_id):
    """
    有鉴权清理：用户主动取消/跳转/提交成功后调用。
    """
    cleanup_upload_session(current_app, session_id)
    return jsonify({"message": "已清理"})


@questions_bp.route('/upload-session/cleanup', methods=['POST'])
def cleanup_session_no_auth():
    """
    无鉴权清理：用于“退出登录/登录过期”时，前端可能已没有可用 token。
    通过 session_id + secret 校验后清理。
    """
    data = request.get_json() or {}
    session_id = data.get("session_id")
    secret = data.get("secret")
    if not session_id or not secret:
        return jsonify({"error": "缺少session_id或secret"}), 400
    if not validate_session_secret(current_app, session_id, secret):
        # secret 不对：不给泄露是否存在
        return jsonify({"message": "已清理"}), 200
    cleanup_upload_session(current_app, session_id)
    return jsonify({"message": "已清理"})


@questions_bp.route('/tmp-images/<session_id>/<filename>', methods=['GET'])
def get_tmp_image(session_id, filename):
    """
    获取临时会话图片（无需认证，给 el-image / img 直接访问）。
    """
    session_dir = get_session_dir(current_app, session_id)
    return send_from_directory(session_dir, filename)


@questions_bp.route('', methods=['GET'])
@jwt_required()
def get_questions():
    """获取题目列表（按试卷分组）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # 筛选条件
    question_type = request.args.get('question_type')
    difficulty_min = request.args.get('difficultyMin', type=float)
    difficulty_max = request.args.get('difficultyMax', type=float)
    source_type = request.args.get('source_type')
    source_institute = request.args.get('source_institute')
    year = request.args.get('year', type=int)
    keyword = request.args.get('keyword')
    
    # 如果有关键词搜索，先找到匹配的试卷标题
    matched_paper_titles = set()
    if keyword:
        # 查找题目内容匹配关键词的题目，获取其试卷标题
        matched_questions = Question.query.filter(
            db.or_(
                Question.content.contains(keyword),
                Question.question_title.contains(keyword)
            )
        ).all()
        for q in matched_questions:
            paper_name = q.title or q.question_title or '未命名题目'
            matched_paper_titles.add(paper_name)
    
    query = Question.query
    
    if question_type:
        query = query.filter(Question.question_type == question_type)
    if difficulty_min is not None:
        query = query.filter(Question.difficulty >= difficulty_min)
    if difficulty_max is not None:
        query = query.filter(Question.difficulty <= difficulty_max)
    if source_type:
        query = query.filter(Question.source_type == source_type)
    if source_institute:
        query = query.filter(Question.source_institute == source_institute)
    if year:
        query = query.filter(Question.year == year)
    
    # 关键词搜索：匹配试卷标题或题目内容
    if keyword:
        query = query.filter(
            db.or_(
                Question.title.contains(keyword),
                Question.content.contains(keyword),
                Question.question_title.contains(keyword)
            )
        )
    
    pagination = query.order_by(Question.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # 收集所有需要返回的试卷标题
    paper_titles_to_include = set()
    for q in pagination.items:
        paper_name = q.title or q.question_title or '未命名题目'
        paper_titles_to_include.add(paper_name)
    
    # 如果有关键词搜索且匹配到题目内容，需要获取这些试卷的所有题目
    all_questions_for_papers = []
    if keyword and matched_paper_titles:
        # 获取匹配试卷的所有题目
        all_questions_for_papers = Question.query.filter(
            db.or_(
                Question.title.in_(matched_paper_titles),
                db.and_(Question.title.is_(None), Question.question_title.in_(matched_paper_titles))
            )
        ).all()
    
    # 合并题目：当前页的题目 + 匹配试卷的所有题目（去重）
    all_questions = list(pagination.items)
    existing_ids = {q.id for q in all_questions}

    # 分组展示时，分页命中的“试卷”必须补齐同一试卷下的全部题目。
    # 否则题库列表中的试卷难度只按当前页部分题目计算，
    # 会和试卷详情页按整套试卷计算出的难度不一致。
    original_paper_names = set()
    for q in pagination.items:
        paper_name = q.title or q.question_title or '未命名题目'
        original_paper_names.add(paper_name)

    paper_questions = []
    if original_paper_names:
        paper_questions = Question.query.filter(
            db.or_(
                Question.title.in_(original_paper_names),
                db.and_(Question.title.is_(None), Question.question_title.in_(original_paper_names))
            )
        ).order_by(Question.id.asc()).all()

    for q in paper_questions:
        if q.id not in existing_ids:
            all_questions.append(q)
            existing_ids.add(q.id)

    for q in all_questions_for_papers:
        if q.id not in existing_ids:
            all_questions.append(q)
            existing_ids.add(q.id)
    
    # 按 title（试卷标题）分组，无 title 的用题目标题作为试卷名
    groups = {}
    for q in all_questions:
        paper_name = q.title or q.question_title or '未命名题目'
        if paper_name not in groups:
            groups[paper_name] = {
                'paper_uuid': f"P{q.id}",  # 用第一个题目ID作为唯一识别码
                'paper_name': paper_name,
                'questions': [],
                'total_score': 0,
                'weighted_difficulty': 0
            }
        
        # 分配题号
        question_data = q.to_dict()
        question_data['question_number'] = len(groups[paper_name]['questions']) + 1
        
        # 累计难度计算
        score = q.default_score or 40
        difficulty = q.difficulty or 0
        groups[paper_name]['total_score'] += score
        groups[paper_name]['weighted_difficulty'] += score * difficulty
        groups[paper_name]['questions'].append(question_data)
    
    # 只保留原始分页中的试卷（避免添加太多额外试卷）
    # original_paper_names 已在补齐同试卷题目时计算
    
    # 计算每个试卷的难度系数，分配序号ID
    result_groups = []
    for idx, (paper_name, group) in enumerate(groups.items(), 1):
        # 只保留原始匹配的试卷
        if paper_name not in original_paper_names:
            continue
            
        # 计算加权平均难度
        if group['total_score'] > 0:
            difficulty = round(group['weighted_difficulty'] / group['total_score'], 2)
        else:
            difficulty = 0
        
        result_groups.append({
            'paper_id': idx,  # 序号ID
            'paper_uuid': group['paper_uuid'],
            'paper_name': group['paper_name'],
            'difficulty': difficulty,
            'question_count': len(group['questions']),
            'questions': group['questions']
        })
    
    return jsonify({
        'groups': result_groups,
        'total': len(result_groups),  # 按试卷数量计数
        'total_questions': pagination.total,  # 题目总数
        'pages': pagination.pages,
        'current_page': page
    })


@questions_bp.route('/<int:question_id>', methods=['GET'])
@jwt_required()
def get_question(question_id):
    """获取单个题目详情"""
    question = Question.query.get(question_id)
    
    if not question:
        return jsonify({'error': '题目不存在'}), 404
    
    return jsonify({'question': question.to_dict()})


@questions_bp.route('', methods=['POST'])
@jwt_required()
def create_question():
    """创建题目"""
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    
    # 只有教师和管理员可以创建题目
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({'error': '权限不足'}), 403
    
    data = request.get_json()
    
    if not data or not data.get('content') or not data.get('answer'):
        return jsonify({'error': '题干和答案不能为空'}), 400

    upload_session_id = data.get('upload_session_id')
    
    question = Question(
        title=data.get('title'),
        question_title=data.get('question_title'),
        content=data['content'],
        answer=data['answer'],
        question_type=data.get('question_type', 'theory'),  # theory（理论题）, experiment（实验理论题）
        difficulty=data.get('difficulty', 3.0),
        source_type=data.get('source_type'),
        source_institute=data.get('source_institute'),
        author=data.get('author'),
        year=data.get('year'),
        default_score=data.get('default_score', 40)
    )
    
    if data.get('content_images'):
        question.content_images = json.dumps(data['content_images'])
    if data.get('answer_images'):
        question.answer_images = json.dumps(data['answer_images'])
    
    db.session.add(question)
    db.session.commit()

    # 如果带了上传会话：将会话内引用到的图片迁移到永久目录，并清理会话目录
    if upload_session_id and (question.content_images or question.answer_images):
        filenames = []
        for field in [question.content_images, question.answer_images]:
            if not field:
                continue
            try:
                lst = json.loads(field) if isinstance(field, str) else field
            except Exception:
                try:
                    lst = ast.literal_eval(field)
                except Exception:
                    lst = []
            if isinstance(lst, list):
                for it in lst:
                    if isinstance(it, str):
                        filenames.append(it)
                    elif isinstance(it, dict) and it.get("filename"):
                        filenames.append(it["filename"])

        mapping = persist_images_from_session(current_app, upload_session_id, filenames)
        if mapping:
            question.content_images = rewrite_images_field(question.content_images, mapping)
            question.answer_images = rewrite_images_field(question.answer_images, mapping)
            db.session.commit()

        cleanup_upload_session(current_app, upload_session_id)
    
    question_dict = question.to_dict()
    question_dict.pop('created_by', None)
    question_dict.pop('status', None)
    return jsonify({'message': '创建成功', 'question': question_dict}), 201


@questions_bp.route('/batch-import', methods=['POST'])
@jwt_required()
def batch_import():
    """批量导入题目（AI导入）"""
    user_id = get_jwt_identity()
    current_user = User.query.get(int(user_id))
    
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({'error': '权限不足'}), 403
    
    data = request.get_json()
    
    if not data or not isinstance(data.get('questions'), list):
        return jsonify({'error': '请提供题目列表'}), 400
    
    questions_data = data['questions']
    upload_session_id = data.get('upload_session_id')
    if len(questions_data) == 0:
        return jsonify({'error': '题目列表不能为空'}), 400
    
    # 合法值自动修正
    valid_types = {'theory', 'experiment'}
    valid_sources = {'past_exam', 'mock'}
    
    def _strip_import_fields(question_dict: dict):
        """
        批量导入的返回结果不包含 created_by / status。
        """
        if not isinstance(question_dict, dict):
            return question_dict
        question_dict.pop('created_by', None)
        question_dict.pop('status', None)
        return question_dict

    created_questions = []
    referenced_filenames = []
    
    for i, q in enumerate(questions_data):
        # 自动修正字段
        q_type = q.get('question_type', 'theory')
        if q_type not in valid_types:
            q_type = 'theory'
        
        # 难度：0.0~5.0 数值
        difficulty = q.get('difficulty', 3.0)
        try:
            difficulty = float(difficulty)
            if difficulty < 0:
                difficulty = 0.0
            elif difficulty > 5.0:
                difficulty = 5.0
        except (ValueError, TypeError):
            difficulty = 3.0
        
        source_type = q.get('source_type')
        if source_type and source_type not in valid_sources:
            source_type = None
        
        # 分值
        score = q.get('score') or q.get('default_score') or 40
        
        # 年份
        year = q.get('year')
        if year is not None:
            try:
                year = int(year)
            except (ValueError, TypeError):
                year = None
        
        question = Question(
            title=q.get('title', ''),
            question_title=q.get('question_title', ''),
            content=q.get('content', ''),
            answer=q.get('answer', ''),
            question_type=q_type,
            difficulty=difficulty,
            source_type=source_type,
            source_institute=q.get('source_institute', ''),
            source_info=q.get('source_info', ''),
            author=q.get('author', ''),
            year=year,
            default_score=int(score)
        )
        
        content_imgs = q.get('content_images')
        if content_imgs and isinstance(content_imgs, list) and len(content_imgs) > 0:
            question.content_images = json.dumps(content_imgs)
            for it in content_imgs:
                if isinstance(it, str):
                    referenced_filenames.append(it)
                elif isinstance(it, dict) and it.get("filename"):
                    referenced_filenames.append(it["filename"])
        
        answer_imgs = q.get('answer_images')
        if answer_imgs and isinstance(answer_imgs, list) and len(answer_imgs) > 0:
            question.answer_images = json.dumps(answer_imgs)
            for it in answer_imgs:
                if isinstance(it, str):
                    referenced_filenames.append(it)
                elif isinstance(it, dict) and it.get("filename"):
                    referenced_filenames.append(it["filename"])
        
        db.session.add(question)
        created_questions.append(question)
    
    try:
        db.session.commit()

        # 导入成功：迁移会话内引用到的图片到永久目录，并更新字段；最后清理会话目录
        if upload_session_id and referenced_filenames:
            mapping = persist_images_from_session(current_app, upload_session_id, referenced_filenames)
            if mapping:
                for q in created_questions:
                    if q.content_images:
                        q.content_images = rewrite_images_field(q.content_images, mapping)
                    if q.answer_images:
                        q.answer_images = rewrite_images_field(q.answer_images, mapping)
                db.session.commit()

            cleanup_upload_session(current_app, upload_session_id)

        return jsonify({
            'message': f'成功导入 {len(created_questions)} 道题目',
            'count': len(created_questions),
            'questions': [_strip_import_fields(q.to_dict()) for q in created_questions]
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'导入失败：{str(e)}'}), 500


@questions_bp.route('/crop-with-boxes', methods=['POST'])
@jwt_required()
def crop_with_boxes():
    """根据用户画的框裁剪图片"""
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({'error': '权限不足'}), 403
    
    data = request.get_json()
    if not data or not data.get('crops'):
        return jsonify({'error': '请提供裁剪数据'}), 400
    
    crops = data['crops']  # [{filename: 'xxx.jpg', boxes: [{x, y, w, h}, ...]}, ...]
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({'error': '缺少upload session_id'}), 400
    upload_folder = get_session_dir(current_app, session_id)
    
    import cv2
    import uuid
    
    all_cropped = []
    
    for item in crops:
        fname = item.get('filename')
        boxes = item.get('boxes', [])
        
        if not fname or not boxes:
            continue
        
        file_path = os.path.join(upload_folder, fname)
        if not os.path.exists(file_path):
            continue
        
        try:
            from PIL import Image
            img = Image.open(file_path)
            img_cv = cv2.imread(file_path)
            if img_cv is None:
                continue
            
            img_width, img_height = img.size
            
            for box in boxes:
                x_pct = box.get('x', 0)
                y_pct = box.get('y', 0)
                w_pct = box.get('w', 0)
                h_pct = box.get('h', 0)
                
                x1 = int(x_pct * img_width)
                y1 = int(y_pct * img_height)
                x2 = int((x_pct + w_pct) * img_width)
                y2 = int((y_pct + h_pct) * img_height)
                
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(img_width, x2)
                y2 = min(img_height, y2)
                
                if x2 <= x1 or y2 <= y1:
                    continue
                
                cropped = img_cv[y1:y2, x1:x2]
                crop_name = f"crop_{uuid.uuid4().hex[:8]}.png"
                crop_path = os.path.join(upload_folder, crop_name)
                cv2.imwrite(crop_path, cropped)
                
                all_cropped.append({
                    'filename': crop_name,
                    'url': f'/api/questions/tmp-images/{session_id}/{crop_name}',
                    'source': fname,
                    'box': box
                })
        except Exception as e:
            print(f"[crop-with-boxes] Error: {e}")
            continue
    
    return jsonify({
        'message': f'裁剪完成，生成 {len(all_cropped)} 张图片',
        'images': all_cropped
    })


@questions_bp.route('/<int:question_id>', methods=['PUT'])
@jwt_required()
def update_question(question_id):
    """更新题目"""
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    
    question = Question.query.get(question_id)
    if not question:
        return jsonify({'error': '题目不存在'}), 404
    
    # 教师和管理员都有权限修改
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({'error': '权限不足'}), 403
    
    data = request.get_json()
    upload_session_id = data.get('upload_session_id')
    
    if 'title' in data:
        question.title = data['title']
    if 'question_title' in data:
        question.question_title = data['question_title']
    if data.get('content'):
        question.content = data['content']
    if data.get('answer'):
        question.answer = data['answer']
    if data.get('question_type'):
        question.question_type = data['question_type']
    if data.get('difficulty') is not None:
        question.difficulty = data['difficulty']
    if data.get('source_type'):
        question.source_type = data['source_type']
    if 'source_institute' in data:
        question.source_institute = data['source_institute']
    if 'author' in data:
        question.author = data['author']
    if data.get('content_images'):
        question.content_images = json.dumps(data['content_images'])
    if data.get('answer_images'):
        question.answer_images = json.dumps(data['answer_images'])
    if data.get('year'):
        question.year = data['year']
    if data.get('default_score'):
        question.default_score = data['default_score']
    
    db.session.commit()

    # 若带了上传会话：仅迁移“仍存在于会话目录”的图片（避免重复迁移旧图片）
    if upload_session_id and (question.content_images or question.answer_images):
        filenames = []
        for field in [question.content_images, question.answer_images]:
            if not field:
                continue
            try:
                lst = json.loads(field) if isinstance(field, str) else field
            except Exception:
                try:
                    lst = ast.literal_eval(field)
                except Exception:
                    lst = []
            if isinstance(lst, list):
                for it in lst:
                    if isinstance(it, str):
                        filenames.append(it)
                    elif isinstance(it, dict) and it.get("filename"):
                        filenames.append(it["filename"])

        mapping = persist_images_from_session(current_app, upload_session_id, filenames)
        if mapping:
            question.content_images = rewrite_images_field(question.content_images, mapping)
            question.answer_images = rewrite_images_field(question.answer_images, mapping)
            db.session.commit()

        cleanup_upload_session(current_app, upload_session_id)
    
    return jsonify({'message': '更新成功', 'question': question.to_dict()})


@questions_bp.route('/<int:question_id>', methods=['DELETE'])
@jwt_required()
def delete_question(question_id):
    """删除题目"""
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    
    question = Question.query.get(question_id)
    if not question:
        return jsonify({'error': '题目不存在'}), 404
    
    # 教师和管理员都有权限删除
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({'error': '权限不足'}), 403
    
    db.session.delete(question)
    db.session.commit()
    
    return jsonify({'message': '删除成功'})


@questions_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_image():
    """上传图片（自动压缩，支持尺寸选择）"""
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({'error': '权限不足'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    # 上传会话（批量导入/单题编辑用）
    session_id = request.form.get('session_id') or request.args.get('session_id')
    if not session_id:
        # 兼容：若前端没传 session_id，则自动创建一个会话（便于后续清理）
        sess = create_upload_session(current_app, user_id)
        session_id = sess["session_id"]

    # 获取尺寸参数，默认为 'medium'
    size = request.form.get('size', 'medium')
    
    # 定义尺寸对应的像素尺寸
    size_configs = {
        'large': (2000, 2800),   # 约 A4 200dpi
        'medium': (1500, 2100),  # 约 A4 150dpi
        'small': (1000, 1400)    # 约 A4 100dpi
    }
    
    # 验证尺寸参数
    if size not in size_configs:
        size = 'medium'
    
    max_w, max_h = size_configs[size]
    
    if file and allowed_file(file.filename):
        # 取消单文件 3MB 限制：
        # - 实际上已有 app.config['MAX_CONTENT_LENGTH']=16MB 的请求体上限
        # - 图片/PDF 后续还会进行缩放与压缩
        
        filename = secure_filename(file.filename)
        # 添加时间戳避免重名
        import time
        name, ext = os.path.splitext(filename)
        filename = f"{int(time.time())}_{name}{ext}"
        
        upload_folder = get_session_dir(current_app, session_id)
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # 如果是PDF，转换为图片
        if ext.lower() == '.pdf':
            result_filenames = []
            try:
                from PIL import Image
                import io
                # 尝试用 pdf2image 转换
                pil_images = []
                try:
                    from pdf2image import convert_from_path
                    pil_images = convert_from_path(file_path, dpi=200)
                except ImportError:
                    try:
                        import fitz  # PyMuPDF
                        pdf_doc = fitz.open(file_path)
                        for page_num in range(len(pdf_doc)):
                            page = pdf_doc[page_num]
                            pix = page.get_pixmap(dpi=200)
                            img_data = pix.tobytes("png")
                            from PIL import Image as PILImage
                            pil_images.append(PILImage.open(io.BytesIO(img_data)))
                        pdf_doc.close()
                    except ImportError:
                        # 尝试 pdfplumber
                        try:
                            import pdfplumber
                            with pdfplumber.open(file_path) as pdf:
                                for page in pdf.pages:
                                    img = page.to_image(resolution=200)
                                    pil_images.append(img.original.convert('RGB'))
                        except ImportError:
                            pass
                
                # 删除原始PDF（只保留拆页图片）
                os.remove(file_path)
                
                for page_idx, img in enumerate(pil_images):
                    page_filename = f"{int(time.time())}_{name}_p{page_idx+1}.jpg"
                    page_path = os.path.join(upload_folder, page_filename)
                    
                    # 转为 RGB（处理 RGBA/灰度图）
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    
                    # 按尺寸限制缩放（保持比例）
                    w, h = img.size
                    if w > max_w or h > max_h:
                        ratio = min(max_w / w, max_h / h)
                        new_w = int(w * ratio)
                        new_h = int(h * ratio)
                        img = img.resize((new_w, new_h), Image.LANCZOS)
                    
                    # 保存为 JPEG，质量 75-80
                    img.save(page_path, 'JPEG', quality=80, optimize=True)
                    result_filenames.append(page_filename)
                
                if result_filenames:
                    return jsonify({
                        'message': f'PDF上传成功，共 {len(result_filenames)} 页',
                        'files': [{'filename': f, 'url': f'/api/questions/tmp-images/{session_id}/{f}'} for f in result_filenames],
                        'filename': filename,
                        'size': size,
                        'session_id': session_id
                    })
                else:
                    return jsonify({'error': 'PDF转换失败，请安装pdf2image或PyMuPDF'}), 500
                    
            except Exception as e:
                return jsonify({'error': f'PDF处理失败：{str(e)}'}), 500
        
        # 普通图片：使用 Pillow 压缩
        try:
            from PIL import Image
            img = Image.open(file_path)
            
            # 转为 RGB（处理 RGBA/灰度图）
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # 按尺寸限制缩放（保持比例）
            w, h = img.size
            if w > max_w or h > max_h:
                ratio = min(max_w / w, max_h / h)
                new_w = int(w * ratio)
                new_h = int(h * ratio)
                img = img.resize((new_w, new_h), Image.LANCZOS)
            
            # 保存为 JPEG，质量 75-80
            output_path = os.path.splitext(file_path)[0] + '.jpg'
            img.save(output_path, 'JPEG', quality=80, optimize=True)
            
            # 如果原文件不是jpg，删除原文件，使用新文件名
            if ext.lower() not in ('.jpg', '.jpeg'):
                os.remove(file_path)
                filename = os.path.basename(output_path)
            
        except ImportError:
            pass
        except Exception:
            pass
        
        return jsonify({
            'message': '上传成功',
            'filename': filename,
            'url': f'/api/questions/tmp-images/{session_id}/{filename}',
            'size': size,
            'session_id': session_id
        })
    
    return jsonify({'error': '不支持的文件格式'}), 400


@questions_bp.route('/images/<path:filename>', methods=['GET'])
def get_image(filename):
    """获取图片"""
    # 新的永久目录优先
    persist_dir = get_persist_image_dir(current_app)
    # filename 可能包含日期子目录，如 20260601/qimg_xxx.jpg
    # send_from_directory 需要拆分为 directory + filename
    if '/' in filename or '\\' in filename:
        safe = filename.replace('\\', '/')
        # 基础防护：禁止目录穿越
        if '..' in safe or safe.startswith('/'):
            return jsonify({'error': '非法文件名'}), 400
        subdir, name = os.path.split(safe)
        candidate_dir = os.path.join(persist_dir, subdir)
        if os.path.exists(os.path.join(candidate_dir, name)):
            return send_from_directory(candidate_dir, name)
    else:
        if os.path.exists(os.path.join(persist_dir, filename)):
            return send_from_directory(persist_dir, filename)

    # 兼容旧数据：仍然从 uploads 根目录取
    upload_folder = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(upload_folder, filename)


@questions_bp.route('/resize-image', methods=['POST'])
@jwt_required()
def resize_image():
    """调整单张图片尺寸"""
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({'error': '权限不足'}), 403
    
    filename = request.args.get('filename')
    session_id = request.args.get('session_id')
    size = request.args.get('size', 'medium')
    
    if not filename:
        return jsonify({'error': '请提供文件名'}), 400
    
    # 优先在上传会话目录中找
    upload_folder = None
    if session_id:
        upload_folder = get_session_dir(current_app, session_id)
    else:
        upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, filename)
    
    if not os.path.exists(file_path):
        return jsonify({'error': '文件不存在'}), 404
    
    # 尺寸配置
    SIZE_CONFIG = {
        'large': (2000, 2800),
        'medium': (1500, 2100),
        'small': (1000, 1400),
    }
    
    max_w, max_h = SIZE_CONFIG.get(size, SIZE_CONFIG['medium'])
    
    try:
        from PIL import Image
        img = Image.open(file_path)
        
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        w, h = img.size
        if w > max_w or h > max_h:
            ratio = min(max_w / w, max_h / h)
            new_w = int(w * ratio)
            new_h = int(h * ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
        
        # 统一保存为 JPEG
        name, ext = os.path.splitext(filename)
        new_filename = f"{name}.jpg"
        new_path = os.path.join(upload_folder, new_filename)
        img.save(new_path, 'JPEG', quality=80, optimize=True)
        
        if new_filename != filename:
            os.remove(file_path)
        
        return jsonify({
            'message': '尺寸已更新',
            'filename': new_filename,
            'url': f'/api/questions/tmp-images/{session_id}/{new_filename}' if session_id else f'/api/questions/images/{new_filename}',
            'size': img.size
        })
    except Exception as e:
        return jsonify({'error': f'处理失败：{str(e)}'}), 500


@questions_bp.route('/compress-images', methods=['POST'])
@jwt_required()
def compress_images():
    """压缩指定图片为 200dpi JPEG，质量 75-80"""
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({'error': '权限不足'}), 403
    
    data = request.get_json()
    if not data or not data.get('filenames'):
        return jsonify({'error': '请提供要压缩的图片文件名列表'}), 400
    
    filenames = data['filenames']
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({'error': '缺少upload session_id'}), 400
    upload_folder = get_session_dir(current_app, session_id)
    
    # 200dpi A4 尺寸
    TARGET_DPI = 200
    MAX_W, MAX_H = 1654, 2339  # A4 @ 200dpi
    
    results = []
    
    for fname in filenames:
        file_path = os.path.join(upload_folder, fname)
        if not os.path.exists(file_path):
            results.append({'filename': fname, 'status': 'not_found'})
            continue
        
        try:
            from PIL import Image
            img = Image.open(file_path)
            
            # 转为 RGB
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # 按 200dpi 限制尺寸
            w, h = img.size
            if w > MAX_W or h > MAX_H:
                ratio = min(MAX_W / w, MAX_H / h)
                new_w = int(w * ratio)
                new_h = int(h * ratio)
                img = img.resize((new_w, new_h), Image.LANCZOS)
            
            # 保存为 JPEG，质量 75-80
            name, ext = os.path.splitext(fname)
            new_filename = f"{name}.jpg"
            new_path = os.path.join(upload_folder, new_filename)
            
            img.save(new_path, 'JPEG', quality=78, optimize=True)
            
            # 如果原文件不是 jpg 且文件名变了，删除原文件
            if new_filename != fname:
                os.remove(file_path)
            
            results.append({
                'filename': new_filename,
                'status': 'compressed',
                'original_size': f"{w}x{h}",
                'new_size': f"{img.size[0]}x{img.size[1]}"
            })
            
        except Exception as e:
            results.append({'filename': fname, 'status': 'error', 'error': str(e)})
    
    return jsonify({
        'message': f'压缩完成，成功 {len([r for r in results if r["status"] == "compressed"])} 张',
        'results': results
    })


@questions_bp.before_app_request
def _auto_cleanup_upload_sessions():
    """
    自动清理 uploads/sessions 中的过期会话目录：
    - 由前端“10分钟无交互自动退出”触发主动清理
    - 兜底：服务端每 5 分钟清理一次超过 10 分钟的会话
    """
    if not hasattr(_auto_cleanup_upload_sessions, "_started"):
        _auto_cleanup_upload_sessions._started = True
        try:
            cleanup_expired_upload_sessions(current_app, max_age_seconds=600)
            start_periodic_cleanup_thread(current_app, interval_seconds=300, max_age_seconds=600)
        except Exception:
            pass
