import json
import os
import shutil
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, Iterable, Optional, Tuple


def _static_dir(app) -> str:
    """
    backend/app/static
    """
    return os.path.dirname(app.config["UPLOAD_FOLDER"])


def get_persist_image_dir(app) -> str:
    """
    新的图片永久存储目录：
    backend/app/static/question_images
    """
    base = os.path.join(_static_dir(app), "question_images")
    os.makedirs(base, exist_ok=True)
    return base


def get_session_root_dir(app) -> str:
    """
    临时上传会话根目录：
    backend/app/static/uploads/sessions
    """
    base = os.path.join(app.config["UPLOAD_FOLDER"], "sessions")
    os.makedirs(base, exist_ok=True)
    return base


def get_session_dir(app, session_id: str) -> str:
    return os.path.join(get_session_root_dir(app), session_id)


def _meta_path(session_dir: str) -> str:
    return os.path.join(session_dir, "meta.json")


def create_upload_session(app, user_id: str) -> Dict[str, str]:
    """
    创建一个上传会话目录，并写入 meta.json（用于无鉴权清理）。
    """
    session_id = uuid.uuid4().hex
    secret = uuid.uuid4().hex + uuid.uuid4().hex
    session_dir = get_session_dir(app, session_id)
    os.makedirs(session_dir, exist_ok=True)

    meta = {
        "session_id": session_id,
        "secret": secret,
        "user_id": str(user_id),
        "created_at": int(time.time()),
    }
    with open(_meta_path(session_dir), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)

    return {"session_id": session_id, "secret": secret}


def read_session_meta(app, session_id: str) -> Optional[dict]:
    session_dir = get_session_dir(app, session_id)
    meta_file = _meta_path(session_dir)
    if not os.path.exists(meta_file):
        return None
    try:
        with open(meta_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def cleanup_upload_session(app, session_id: str) -> bool:
    session_dir = get_session_dir(app, session_id)
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir, ignore_errors=True)
        return True
    return False


def validate_session_secret(app, session_id: str, secret: str) -> bool:
    meta = read_session_meta(app, session_id)
    if not meta:
        return False
    return str(meta.get("secret")) == str(secret)


def session_file_path(app, session_id: str, filename: str) -> str:
    return os.path.join(get_session_dir(app, session_id), filename)


def list_session_files(app, session_id: str) -> Iterable[str]:
    session_dir = get_session_dir(app, session_id)
    if not os.path.isdir(session_dir):
        return []
    return [f for f in os.listdir(session_dir) if os.path.isfile(os.path.join(session_dir, f))]


def _date_folder() -> str:
    return datetime.now().strftime("%Y%m%d")


def persist_images_from_session(
    app,
    session_id: str,
    filenames: Iterable[str],
) -> Dict[str, str]:
    """
    将指定 filenames（若存在于 session 目录）迁移到永久目录，并返回 old->new 映射。
    - 不存在于 session 目录的文件会被忽略（用于兼容“编辑题目时旧图片+新图片混用”）。
    """
    persist_root = get_persist_image_dir(app)
    date_dir = os.path.join(persist_root, _date_folder())
    os.makedirs(date_dir, exist_ok=True)

    mapping: Dict[str, str] = {}
    for old_name in set([f for f in filenames if f]):
        src = session_file_path(app, session_id, old_name)
        if not os.path.exists(src):
            continue
        _, ext = os.path.splitext(old_name)
        ext = ext.lower() or ".jpg"
        new_name = f"qimg_{uuid.uuid4().hex}{ext}"
        dst = os.path.join(date_dir, new_name)
        shutil.move(src, dst)
        mapping[old_name] = f"{_date_folder()}/{new_name}"

    return mapping


def rewrite_images_field(value, mapping: Dict[str, str]):
    """
    value: list[str] | list[dict] | json-string
    支持两种格式：
      - ["a.jpg", "b.jpg"]
      - [{"filename":"a.jpg","size":"medium"}, ...]
    """
    if value is None:
        return None

    data = value
    if isinstance(value, str):
        try:
            data = json.loads(value)
        except Exception:
            # 老数据可能是 python 字面量
            try:
                data = eval(value)
            except Exception:
                return value

    if not isinstance(data, list):
        return value

    new_list = []
    for item in data:
        if isinstance(item, str):
            new_list.append(mapping.get(item, item))
        elif isinstance(item, dict):
            old = item.get("filename") or ""
            item = dict(item)
            if old in mapping:
                item["filename"] = mapping[old]
            new_list.append(item)
        else:
            new_list.append(item)

    return json.dumps(new_list, ensure_ascii=False)


def cleanup_expired_upload_sessions(app, max_age_seconds: int = 600) -> int:
    """
    清理超过 max_age_seconds 的 uploads/sessions/<session_id> 目录。
    通过 meta.json 中 created_at 判定。
    """
    root = get_session_root_dir(app)
    now = int(time.time())
    deleted = 0

    try:
        for session_id in os.listdir(root):
            session_dir = os.path.join(root, session_id)
            if not os.path.isdir(session_dir):
                continue
            meta_file = _meta_path(session_dir)
            created_at = None
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        created_at = int(json.load(f).get("created_at") or 0)
                except Exception:
                    created_at = None

            # 没有 meta 的目录：用 mtime 兜底
            if created_at is None:
                created_at = int(os.path.getmtime(session_dir))

            if now - created_at > max_age_seconds:
                shutil.rmtree(session_dir, ignore_errors=True)
                deleted += 1
    except Exception:
        pass

    return deleted


def start_periodic_cleanup_thread(app, interval_seconds: int = 300, max_age_seconds: int = 600) -> None:
    """
    每 interval_seconds 秒清理一次过期上传会话。
    """

    def _worker():
        while True:
            time.sleep(interval_seconds)
            try:
                cleanup_expired_upload_sessions(app, max_age_seconds=max_age_seconds)
            except Exception:
                pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

