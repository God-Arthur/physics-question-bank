"""
PDF预览会话管理模块

与 upload_session.py 类似的会话机制，用于管理PDF预览的临时文件。
特点：
- 只存储 .tex 文件，不存储 .pdf/.log/.aux 等编译产物
- 查看时实时编译 .tex → PDF
- 会话级清理（取消/跳转/超时/登出）
"""

import os
import shutil
import uuid
import threading
import time
import logging


logger = logging.getLogger(__name__)


def get_pdf_session_base(app):
    """获取PDF预览会话基础目录"""
    base = os.path.join(app.root_path, 'temp_pdf_sessions')
    os.makedirs(base, exist_ok=True)
    return base


def create_pdf_preview_session(app, user_id):
    """创建PDF预览会话，返回 session_id"""
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(get_pdf_session_base(app), session_id)
    os.makedirs(session_dir, exist_ok=True)
    # 记录元信息
    with open(os.path.join(session_dir, '.session_info'), 'w', encoding='utf-8') as f:
        f.write(f"user_id={user_id}\n")
        f.write(f"created_at={time.time()}\n")
    return session_id


def get_pdf_session_dir(app, session_id):
    """获取PDF预览会话目录，不存在返回 None"""
    session_dir = os.path.join(get_pdf_session_base(app), session_id)
    if os.path.isdir(session_dir):
        return session_dir
    return None


def get_tex_path(app, session_id, preview_id):
    """获取 .tex 文件路径"""
    session_dir = get_pdf_session_dir(app, session_id)
    if not session_dir:
        return None
    tex_path = os.path.join(session_dir, f'{preview_id}.tex')
    if os.path.exists(tex_path):
        return tex_path
    return None


def cleanup_pdf_session(app, session_id):
    """清理单个PDF预览会话"""
    session_dir = get_pdf_session_dir(app, session_id)
    if session_dir:
        shutil.rmtree(session_dir)
        return True
    return False


def cleanup_expired_pdf_sessions(app, max_age_seconds=600):
    """清理过期的PDF预览会话（默认10分钟）"""
    base = get_pdf_session_base(app)
    current_time = time.time()
    count = 0
    try:
        for name in os.listdir(base):
            session_dir = os.path.join(base, name)
            if not os.path.isdir(session_dir):
                continue
            info_path = os.path.join(session_dir, '.session_info')
            if os.path.exists(info_path):
                try:
                    with open(info_path, 'r', encoding='utf-8') as f:
                        info = {}
                        for line in f:
                            if '=' in line:
                                k, v = line.strip().split('=', 1)
                                info[k] = v
                    created_at = float(info.get('created_at', 0))
                    if current_time - created_at > max_age_seconds:
                        shutil.rmtree(session_dir)
                        count += 1
                except (ValueError, OSError):
                    # 无法读取元信息，直接清理
                    shutil.rmtree(session_dir)
                    count += 1
    except Exception:
        logger.exception("清理过期 PDF 预览会话失败")
    return count


def start_pdf_session_cleanup_thread(app, interval_seconds=300, max_age_seconds=600):
    """启动PDF预览会话定期清理线程"""
    def cleanup_loop():
        while True:
            time.sleep(interval_seconds)
            try:
                count = cleanup_expired_pdf_sessions(app, max_age_seconds)
                if count > 0:
                    logger.info("定期清理了 %s 个过期 PDF 预览会话", count)
            except Exception:
                logger.exception("定期清理 PDF 预览会话失败")

    thread = threading.Thread(target=cleanup_loop, daemon=True)
    thread.start()
    logger.info("PDF 预览会话定期清理线程已启动（每%s秒，%s秒过期）", interval_seconds, max_age_seconds)
