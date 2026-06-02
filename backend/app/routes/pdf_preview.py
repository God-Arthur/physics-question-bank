import os
import shutil
import uuid
import threading
import time
from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.pdf_generator import generate_latex_template, generate_answer_latex_template, compile_latex_to_pdf
from app.utils.pdf_preview_session import (
    create_pdf_preview_session,
    get_pdf_session_dir,
    get_tex_path,
    cleanup_pdf_session,
    cleanup_expired_pdf_sessions,
    start_pdf_session_cleanup_thread
)
from app.models import Question

pdf_preview_bp = Blueprint('pdf_preview', __name__)


@pdf_preview_bp.route('/session/init', methods=['POST'])
@jwt_required()
def init_pdf_session():
    """初始化PDF预览会话"""
    user_id = get_jwt_identity()
    session_id = create_pdf_preview_session(current_app._get_current_object(), user_id)
    return jsonify({'session_id': session_id})


@pdf_preview_bp.route('/session/cleanup', methods=['POST'])
@jwt_required()
def cleanup_my_pdf_session():
    """清理当前用户的PDF预览会话"""
    data = request.get_json() or {}
    session_id = data.get('session_id')
    if session_id:
        cleanup_pdf_session(current_app._get_current_object(), session_id)
    return jsonify({'message': 'PDF预览会话已清理'})


@pdf_preview_bp.route('/session/cleanup-noauth', methods=['POST'])
def cleanup_pdf_session_noauth():
    """无鉴权清理PDF预览会话（用于登出/401场景）"""
    data = request.get_json() or {}
    session_id = data.get('session_id')
    if session_id:
        cleanup_pdf_session(current_app._get_current_object(), session_id)
    return jsonify({'message': 'PDF预览会话已清理'})


@pdf_preview_bp.route('/preview', methods=['POST'])
@jwt_required()
def create_preview():
    """创建临时预览（只生成 .tex，不编译 PDF）"""
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data or not data.get('questions'):
        return jsonify({'error': '没有选择题目'}), 400

    questions_data = data['questions']
    title = data.get('title', '试卷预览')
    time_info = data.get('time_info', '（考试时间）')
    session_id = data.get('session_id')

    app = current_app._get_current_object()

    # 如果没有传入 session_id，创建一个
    if not session_id:
        session_id = create_pdf_preview_session(app, user_id)

    session_dir = get_pdf_session_dir(app, session_id)
    if not session_dir:
        return jsonify({'error': '会话不存在'}), 400

    # 获取题目详情
    questions = []
    for item in questions_data:
        if isinstance(item, dict):
            question_id = None
            if item.get('question') and isinstance(item.get('question'), dict):
                question_id = item.get('question').get('id')
            if not question_id:
                question_id = item.get('id') or item.get('question_id')
            user_score = item.get('score')
        else:
            continue

        if question_id:
            question = Question.query.get(int(question_id))
            if question:
                if user_score is not None:
                    final_score = user_score
                else:
                    final_score = question.default_score or 40
                questions.append({
                    'question': question,
                    'score': final_score
                })

    if not questions:
        return jsonify({'error': '未找到有效题目'}), 400

    # 生成唯一的预览ID
    preview_id = str(uuid.uuid4())
    tex_path = os.path.join(session_dir, f'{preview_id}.tex')

    try:
        # 只生成 .tex 内容，不编译 PDF
        latex_content = generate_latex_template(title, time_info, questions)
        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(latex_content)

        return jsonify({
            'session_id': session_id,
            'preview_id': preview_id,
            'message': '预览生成成功'
        })
    except Exception as e:
        if os.path.exists(tex_path):
            os.remove(tex_path)
        return jsonify({'error': f'预览生成失败: {str(e)}'}), 500


@pdf_preview_bp.route('/preview/<session_id>/<preview_id>', methods=['GET'])
def get_preview(session_id, preview_id):
    """获取预览 PDF（实时编译 .tex → PDF）"""
    app = current_app._get_current_object()
    tex_path = get_tex_path(app, session_id, preview_id)

    if not tex_path:
        return jsonify({'error': '预览文件不存在或已过期'}), 404

    # 读取 .tex 内容
    with open(tex_path, 'r', encoding='utf-8') as f:
        latex_content = f.read()

    # 编译到临时 PDF（放在会话目录中）
    pdf_path = os.path.join(os.path.dirname(tex_path), f'{preview_id}_temp.pdf')

    if compile_latex_to_pdf(latex_content, pdf_path, tex_path):
        if os.path.exists(pdf_path):
            return send_file(pdf_path, mimetype='application/pdf')
        else:
            return jsonify({'error': 'PDF编译失败'}), 500
    else:
        return jsonify({'error': 'PDF编译失败，请检查 xelatex 是否安装'}), 500


@pdf_preview_bp.route('/answer-preview', methods=['POST'])
@jwt_required()
def create_answer_preview():
    """创建答案预览（只生成 .tex，不编译 PDF）"""
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data or not data.get('questions'):
        return jsonify({'error': '没有选择题目'}), 400

    questions_data = data['questions']
    title = data.get('title', '试卷预览')
    time_info = data.get('time_info', '（考试时间）')
    session_id = data.get('session_id')

    app = current_app._get_current_object()

    if not session_id:
        session_id = create_pdf_preview_session(app, user_id)

    session_dir = get_pdf_session_dir(app, session_id)
    if not session_dir:
        return jsonify({'error': '会话不存在'}), 400

    # 获取题目详情
    questions = []
    for item in questions_data:
        if isinstance(item, dict):
            question_id = None
            if item.get('question') and isinstance(item.get('question'), dict):
                question_id = item.get('question').get('id')
            if not question_id:
                question_id = item.get('id') or item.get('question_id')
            user_score = item.get('score')
        else:
            continue

        if question_id:
            question = Question.query.get(int(question_id))
            if question:
                if user_score is not None:
                    final_score = user_score
                else:
                    final_score = question.default_score or 40
                questions.append({
                    'question': question,
                    'score': final_score
                })

    if not questions:
        return jsonify({'error': '未找到有效题目'}), 400

    preview_id = str(uuid.uuid4())
    tex_path = os.path.join(session_dir, f'answer_{preview_id}.tex')

    try:
        latex_content = generate_answer_latex_template(title, time_info, questions)
        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(latex_content)

        return jsonify({
            'session_id': session_id,
            'preview_id': f'answer_{preview_id}',
            'message': '答案预览生成成功'
        })
    except Exception as e:
        if os.path.exists(tex_path):
            os.remove(tex_path)
        return jsonify({'error': f'答案预览生成失败: {str(e)}'}), 500


# 启动时自动清理过期会话
@pdf_preview_bp.before_app_request
def auto_cleanup_on_startup():
    """应用启动时自动清理过期PDF预览会话"""
    if not hasattr(auto_cleanup_on_startup, '_cleaned'):
        auto_cleanup_on_startup._cleaned = True
        try:
            app = current_app._get_current_object()
            count = cleanup_expired_pdf_sessions(app, max_age_seconds=600)
            if count > 0:
                print(f"[PDF Preview] 启动时清理了 {count} 个过期PDF预览会话")
            start_pdf_session_cleanup_thread(app, interval_seconds=300, max_age_seconds=600)
        except RuntimeError:
            # 应用上下文可能不可用，忽略
            pass
