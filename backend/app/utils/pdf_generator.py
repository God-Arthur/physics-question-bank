import os
import subprocess
import tempfile
import re
import shutil
import platform
import ast
import json
import logging


logger = logging.getLogger(__name__)

def find_xelatex():
    """查找 xelatex 可执行文件"""
    # 1. 尝试系统 PATH 中的 xelatex（Linux/macOS 原生）
    xelatex_path = shutil.which('xelatex')
    if xelatex_path:
        return xelatex_path

    # 2. 尝试 Windows texlive（通过 WSL 访问 D 盘）
    win_xelatex_paths = [
        '/mnt/d/texlive/2026/bin/windows/xelatex.exe',
        '/mnt/c/texlive/2026/bin/windows/xelatex.exe',
        '/mnt/d/texlive/2025/bin/windows/xelatex.exe',
        '/mnt/c/texlive/2025/bin/windows/xelatex.exe',
    ]
    for p in win_xelatex_paths:
        if os.path.exists(p):
            return p

    # 3. 尝试常见 Linux 路径
    linux_paths = [
        '/usr/bin/xelatex',
        '/usr/local/bin/xelatex',
        '/usr/texbin/xelatex',
    ]
    for p in linux_paths:
        if os.path.exists(p):
            return p

    return None

# 全局 xelatex 路径
XELATEX_PATH = find_xelatex()
if XELATEX_PATH:
    logger.info("找到 xelatex: %s", XELATEX_PATH)
else:
    logger.warning("未找到 xelatex，PDF 生成将不可用")

def escape_latex(text):
    """转义 LaTeX 特殊字符，并保留 $...$ / $$...$$ 公式。"""
    if not text:
        return ''

    formulas = []

    def save_formula(match):
        formulas.append(match.group(0))
        return f"\u0000FORMULA{len(formulas) - 1}\u0000"

    # 公式里的 < > 不能先被当成 HTML 标签删掉
    text = re.sub(r'\$\$[\s\S]+?\$\$', save_formula, text)
    text = re.sub(r'\$[^$\n]+?\$', save_formula, text)
    text = re.sub(r'<[^>]+>', '', text)

    parts = re.split(r'(\u0000FORMULA\d+\u0000)', text)
    escaped_parts = []
    replacements = (
        ('\\', '\u0000BS\u0000'),
        ('&', r'\&'),
        ('%', r'\%'),
        ('#', r'\#'),
        ('_', r'\_'),
        ('{', r'\{'),
        ('}', r'\}'),
        ('~', r'\textasciitilde{}'),
        ('^', r'\textasciicircum{}'),
        ('<', r'\textless{}'),
        ('>', r'\textgreater{}'),
    )
    for part in parts:
        if part.startswith('\u0000FORMULA'):
            escaped_parts.append(part)
            continue
        for char, escaped in replacements:
            part = part.replace(char, escaped)
        part = part.replace('\u0000BS\u0000', r'\textbackslash{}')
        escaped_parts.append(part)

    text = ''.join(escaped_parts)
    for index, formula in enumerate(formulas):
        text = text.replace(f"\u0000FORMULA{index}\u0000", formula)
    return text


def _static_image_path(img_path):
    """只允许读取 static 目录内的题目图片。"""
    if not img_path or not isinstance(img_path, str):
        return None
    normalized = img_path.replace('\\', '/')
    if normalized.startswith('/') or '..' in normalized.split('/'):
        return None
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_dir = os.path.realpath(os.path.join(backend_dir, 'static'))
    for relative in (
        os.path.join('question_images', img_path),
        os.path.join('uploads', img_path),
    ):
        full_path = os.path.realpath(os.path.join(static_dir, relative))
        if full_path.startswith(static_dir + os.sep) and os.path.isfile(full_path):
            return full_path
    return None


def _iter_images(raw_images):
    if not raw_images:
        return []
    images = raw_images
    if isinstance(raw_images, str):
        try:
            images = json.loads(raw_images)
        except (TypeError, ValueError):
            try:
                images = ast.literal_eval(raw_images)
            except (ValueError, SyntaxError):
                return []
    return images if isinstance(images, list) else []


def _append_images(lines, raw_images):
    size_map = {'large': '0.9', 'medium': '0.45', 'small': '0.3'}
    for img_item in _iter_images(raw_images):
        if isinstance(img_item, dict):
            img_path = img_item.get('filename', '')
            size_tag = img_item.get('size', 'medium')
        else:
            img_path = img_item
            size_tag = 'medium'
        full_path = _static_image_path(img_path)
        if not full_path:
            continue
        img_width = size_map.get(size_tag, '0.45')
        lines.append(r'\begin{center}')
        lines.append(r'\includegraphics[width=' + img_width + r'\textwidth]{' + full_path + '}')
        lines.append(r'\end{center}')
        lines.append('')

def generate_latex_template(title, time_info, questions, include_answer=False):
    """生成 LaTeX 模板（简化版，确保兼容性）

    格式：
    - 标题：黑体三号居中
    - 时间：黑体四号居中
    - 考生须知标题：黑体四号居中
    - 考生须知内容：宋体五号，数字用 Times New Roman
    - 题目：宋体小四号
    """
    lines = []
    lines.append(r'\documentclass[12pt,a4paper]{article}')
    lines.append(r'\usepackage[fontset=fandol]{ctex}')
    lines.append(r'\ctexset{space=false}')
    lines.append(r'\usepackage{xeCJK}')
    lines.append(r'\xeCJKsetup{CJKecglue=}')
    lines.append(r'\setmainfont{texgyretermes-regular.otf}[BoldFont=texgyretermes-bold.otf,Path=/usr/share/texmf/fonts/opentype/public/tex-gyre/]')
    lines.append(r'\xeCJKsetcharclass{`0}{`9}{1}')
    lines.append(r'\xeCJKsetcharclass{"003A}{"003A}{1}')  # 冒号 : 使用西文字体
    lines.append(r'\xeCJKsetcharclass{"002D}{"002D}{1}')  # 减号 - 使用西文字体
    lines.append(r'\usepackage{amsmath,amssymb}')
    lines.append(r'\allowdisplaybreaks[4]')
    lines.append(r'\usepackage{microtype}')
    lines.append(r'\usepackage{graphicx}')
    lines.append(r'\usepackage{geometry}')
    lines.append(r'\usepackage{fancyhdr}')
    lines.append(r'\usepackage{lastpage}')
    lines.append('')
    # 页边距：上下 2.54cm，左右 3.00cm
    lines.append(r'\geometry{left=2.0cm,right=2.0cm,top=1.5cm,bottom=3.0cm}')
    lines.append(r'\geometry{footskip=1.0cm}')
    lines.append('')
    # 页脚设置：居中页码，小五号字，格式"第x页，共?页"
    lines.append(r'\pagestyle{fancy}')
    lines.append(r'\fancyhf{}')
    lines.append(r'\fancyfoot[C]{\zihao{-5}第\thepage{}页，共\pageref{lastpage}页}')
    lines.append(r'\renewcommand{\headrulewidth}{0pt}')
    lines.append(r'\renewcommand{\footrulewidth}{0pt}')
    lines.append('')
    lines.append(r'\begin{document}')
    lines.append(r'\sloppy')
    lines.append('')

    # 标题：宋体四号加粗
    lines.append(r'\begin{center}')
    lines.append(r'\zihao{4}\textbf{' + escape_latex(title or '') + r'}')
    lines.append(r'\end{center}')
    lines.append('')

    # 时间：宋体10pt
    lines.append(r'\begin{center}')
    lines.append(r'\fontsize{10pt}{14pt}\selectfont ' + escape_latex(time_info or ''))
    lines.append(r'\end{center}')
    lines.append('')

    # 考生须知标题：宋体11pt，居中
    lines.append(r'\begin{center}')
    lines.append(r'\fontsize{11pt}{15pt}\selectfont 考生须知')
    lines.append(r'\end{center}')
    lines.append('')

    # 考生须知内容：左顶格，序号Times New Roman五号不加粗，内容宋体10pt
    total_score = sum(q['score'] for q in questions)
    question_count = len(questions)

    lines.append(r'\noindent')
    lines.append(r'\rmfamily\fontsize{10.5pt}{14pt}\selectfont 1\songti\fontsize{10pt}{14pt}\selectfont 、考生考试前务必认真阅读本须知。\\')
    lines.append(r'\noindent')
    lines.append(r'\rmfamily\fontsize{10.5pt}{14pt}\selectfont 2\songti\fontsize{10pt}{14pt}\selectfont 、本试题共' + str(question_count) + r'道题，总分为' + str(total_score) + r'分。\\')
    lines.append(r'\noindent')
    lines.append(r'\rmfamily\fontsize{10.5pt}{14pt}\selectfont 3\songti\fontsize{10pt}{14pt}\selectfont 、如遇试题印刷不清楚的情况，请及时向监考老师提出。\\')
    lines.append(r'\noindent')
    lines.append(r'\rmfamily\fontsize{10.5pt}{14pt}\selectfont 4\songti\fontsize{10pt}{14pt}\selectfont 、需要阅卷老师评阅的内容一定要写在答题纸上；写在试题纸和草稿纸上的解答一律不给分。')
    lines.append('')

    # 题目列表（支持1-100）
    chinese_nums = [
        '一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
        '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
        '二十一', '二十二', '二十三', '二十四', '二十五', '二十六', '二十七', '二十八', '二十九', '三十',
        '三十一', '三十二', '三十三', '三十四', '三十五', '三十六', '三十七', '三十八', '三十九', '四十',
        '四十一', '四十二', '四十三', '四十四', '四十五', '四十六', '四十七', '四十八', '四十九', '五十',
        '五十一', '五十二', '五十三', '五十四', '五十五', '五十六', '五十七', '五十八', '五十九', '六十',
        '六十一', '六十二', '六十三', '六十四', '六十五', '六十六', '六十七', '六十八', '六十九', '七十',
        '七十一', '七十二', '七十三', '七十四', '七十五', '七十六', '七十七', '七十八', '七十九', '八十',
        '八十一', '八十二', '八十三', '八十四', '八十五', '八十六', '八十七', '八十八', '八十九', '九十',
        '九十一', '九十二', '九十三', '九十四', '九十五', '九十六', '九十七', '九十八', '九十九', '一百'
    ]

    for i, item in enumerate(questions, 1):
        question = item['question']
        score = item['score']
        num_chinese = chinese_nums[i - 1] if i <= len(chinese_nums) else str(i)

        # 题号左顶格：宋体10号，段前空行，格式：一、（10分）题目标题
        lines.append(r'\vspace{0.5\baselineskip}')
        lines.append(r'\noindent')
        lines.append(r'\fontsize{10pt}{14pt}\selectfont ' + num_chinese + r'、（' + str(score) + r'分）' + escape_latex(question.question_title or ''))
        lines.append('')

        # 题目内容：宋体10号
        content = question.content or ''
        lines.append(r'\fontsize{10pt}{14pt}\selectfont')
        lines.append(escape_latex(content))
        lines.append('')
        _append_images(lines, question.content_images)
        if include_answer:
            lines.append(r'\noindent\textbf{参考答案}')
            lines.append('')
            lines.append(escape_latex(question.answer or ''))
            lines.append('')
            _append_images(lines, question.answer_images)

    lines.append(r'\label{lastpage}')
    lines.append(r'\end{document}')

    return '\n'.join(lines)


def generate_answer_latex_template(title, time_info, questions):
    """生成答案 LaTeX 模板

    格式与试卷相同，但内容为答案
    """
    lines = []
    lines.append(r'\documentclass[12pt,a4paper]{article}')
    lines.append(r'\usepackage[fontset=fandol]{ctex}')
    lines.append(r'\ctexset{space=false}')
    lines.append(r'\usepackage{xeCJK}')
    lines.append(r'\xeCJKsetup{CJKecglue=}')
    lines.append(r'\setmainfont{texgyretermes-regular.otf}[BoldFont=texgyretermes-bold.otf,Path=/usr/share/texmf/fonts/opentype/public/tex-gyre/]')
    lines.append(r'\xeCJKsetcharclass{`0}{`9}{1}')
    lines.append(r'\xeCJKsetcharclass{"003A}{"003A}{1}')  # 冒号
    lines.append(r'\xeCJKsetcharclass{"002D}{"002D}{1}')  # 减号
    lines.append(r'\usepackage{amsmath,amssymb}')
    lines.append(r'\allowdisplaybreaks[4]')
    lines.append(r'\usepackage{microtype}')
    lines.append(r'\usepackage{graphicx}')
    lines.append(r'\usepackage{geometry}')
    lines.append(r'\usepackage{fancyhdr}')
    lines.append(r'\usepackage{lastpage}')
    lines.append('')
    lines.append(r'\geometry{left=2.0cm,right=2.0cm,top=1.5cm,bottom=3.0cm}')
    lines.append(r'\geometry{footskip=1.0cm}')
    lines.append('')
    lines.append(r'\pagestyle{fancy}')
    lines.append(r'\fancyhf{}')
    lines.append(r'\fancyfoot[C]{\zihao{-5}第\thepage{}页，共\pageref{lastpage}页}')
    lines.append(r'\renewcommand{\headrulewidth}{0pt}')
    lines.append(r'\renewcommand{\footrulewidth}{0pt}')
    lines.append('')
    lines.append(r'\begin{document}')
    lines.append(r'\sloppy')
    lines.append('')

    # 标题：宋体四号加粗
    lines.append(r'\begin{center}')
    lines.append(r'\zihao{4}\textbf{' + escape_latex(title or '') + r'}')
    lines.append(r'\end{center}')
    lines.append('')

    # 副标题：参考答案与解析，四号不加粗
    lines.append(r'\begin{center}')
    lines.append(r'\zihao{4}参考答案与解析')
    lines.append(r'\end{center}')
    lines.append('')

    # 答案列表（支持1-100）
    chinese_nums = [
        '一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
        '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
        '二十一', '二十二', '二十三', '二十四', '二十五', '二十六', '二十七', '二十八', '二十九', '三十',
        '三十一', '三十二', '三十三', '三十四', '三十五', '三十六', '三十七', '三十八', '三十九', '四十',
        '四十一', '四十二', '四十三', '四十四', '四十五', '四十六', '四十七', '四十八', '四十九', '五十',
        '五十一', '五十二', '五十三', '五十四', '五十五', '五十六', '五十七', '五十八', '五十九', '六十',
        '六十一', '六十二', '六十三', '六十四', '六十五', '六十六', '六十七', '六十八', '六十九', '七十',
        '七十一', '七十二', '七十三', '七十四', '七十五', '七十六', '七十七', '七十八', '七十九', '八十',
        '八十一', '八十二', '八十三', '八十四', '八十五', '八十六', '八十七', '八十八', '八十九', '九十',
        '九十一', '九十二', '九十三', '九十四', '九十五', '九十六', '九十七', '九十八', '九十九', '一百'
    ]

    for i, item in enumerate(questions, 1):
        question = item['question']
        score = item['score']
        num_chinese = chinese_nums[i - 1] if i <= len(chinese_nums) else str(i)

        # 题号左顶格：宋体10号
        lines.append(r'\vspace{0.5\baselineskip}')
        lines.append(r'\noindent')
        lines.append(r'\fontsize{10pt}{14pt}\selectfont ' + num_chinese + r'、（' + str(score) + r'分）' + escape_latex(question.question_title or ''))
        lines.append('')

        # 答案内容：宋体10号
        answer = question.answer or ''
        if answer:
            lines.append(r'\fontsize{10pt}{14pt}\selectfont')
            lines.append(escape_latex(answer))
            lines.append('')

        _append_images(lines, question.answer_images)

    lines.append(r'\label{lastpage}')
    lines.append(r'\end{document}')

    return '\n'.join(lines)


def wsl_to_win_path(wsl_path):
    """将 WSL 路径转换为 Windows 可用的路径

    LaTeX 无法处理反斜杠路径，所以使用正斜杠格式给 xelatex
    """
    if wsl_path.startswith('/mnt/'):
        # /mnt/d/xxx -> d:/xxx
        parts = wsl_path.split('/')
        drive = parts[2].upper()
        rest = '/'.join(parts[3:])
        return f"{drive}:/{rest}"
    elif wsl_path.startswith('/home/'):
        # /home/xxx -> //wsl$/Ubuntu/home/xxx
        return f"//wsl$/Ubuntu{wsl_path.replace('/', '/')}"
    return wsl_path

def compile_latex_to_pdf(latex_content, output_path, tex_path=None):
    """使用 xelatex 编译 LaTeX 到 PDF

    参数:
        latex_content: LaTeX 内容
        output_path: PDF 输出路径
        tex_path: 可选，指定 .tex 文件保存路径
    """

    if not XELATEX_PATH:
        logger.warning("xelatex 未找到，无法生成 PDF")
        return False

    # 判断是否使用 Windows 的 xelatex.exe
    is_windows_exe = XELATEX_PATH.endswith('.exe')

    # 确定 .tex 文件路径
    if tex_path:
        # 使用指定的 tex_path
        tex_file = tex_path
        temp_dir = os.path.dirname(tex_path)
    else:
        # 创建临时目录（放在 backend 目录下）
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        temp_base = os.path.join(backend_dir, 'temp_pdf')
        os.makedirs(temp_base, exist_ok=True)
        temp_dir = tempfile.mkdtemp(dir=temp_base)
        tex_file = os.path.join(temp_dir, 'paper.tex')

    # 写入 .tex 文件
    with open(tex_file, 'w', encoding='utf-8') as f:
        f.write(latex_content)

    logger.debug("LaTeX 文件已写入: %s", tex_file)

    if is_windows_exe:
        # 方法1：通过 PowerShell 执行 xelatex
        # 使用 Windows 临时目录
        win_temp_dir = os.environ.get('TEMP', 'C:\\Temp')
        win_temp_dir = os.path.join(win_temp_dir, 'physics_pdf')
        os.makedirs(win_temp_dir, exist_ok=True)

        # 复制 .tex 文件到 Windows 临时目录
        win_tex_file = os.path.join(win_temp_dir, 'paper.tex')
        shutil.copy(tex_file, win_tex_file)

        # 使用 PowerShell 执行 xelatex（WSL 中调用 Windows 命令）
        # 先复制文件，然后通过 powershell.exe 执行
        xelatex_cmd = f'& "{XELATEX_PATH}" -interaction=nonstopmode -output-directory "{win_temp_dir}" "{win_tex_file}"'
        cmd = ['powershell.exe', '-NoProfile', '-Command', xelatex_cmd]

        logger.debug("执行命令: %s", ' '.join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            logger.debug("xelatex 返回码: %s", result.returncode)
            if result.stdout:
                logger.debug("xelatex stdout: %s", result.stdout[-500:])
            if result.stderr:
                logger.debug("xelatex stderr: %s", result.stderr[-500:])

            # 检查 PDF 是否生成
            win_pdf_file = os.path.join(win_temp_dir, 'paper.pdf')
            if os.path.exists(win_pdf_file):
                # 复制 PDF 到 WSL 输出路径
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                shutil.copy(win_pdf_file, output_path)
                logger.info("PDF 生成成功: %s", output_path)
                return True
            else:
                logger.error("PDF 文件未生成: %s", win_pdf_file)
                logger.debug("PDF 临时目录内容: %s", os.listdir(win_temp_dir))
                return False

        except subprocess.TimeoutExpired:
            logger.error("xelatex 编译超时")
            return False
        except Exception:
            logger.exception("xelatex 编译异常")
            return False
        finally:
            # 保留 .tex 文件，只清理 Windows 临时目录
            pass
    else:
        # Linux/macOS 原生 xelatex
        cmd = [
            XELATEX_PATH,
            '-interaction=nonstopmode',
            '-output-directory', temp_dir,
            tex_file
        ]

        logger.debug("执行命令: %s...", ' '.join(cmd[:3]))

        try:
            # 第一次编译
            result1 = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                encoding='utf-8',
                errors='replace'
            )
            logger.debug("第一次编译完成，返回码: %s", result1.returncode)

            # 第二次编译（为了正确显示总页数）
            result2 = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                encoding='utf-8',
                errors='replace'
            )
            logger.debug("第二次编译完成，返回码: %s", result2.returncode)

            # 检查 PDF 是否生成（即使有警告，xelatex 也可能成功生成 PDF）
            # PDF 文件名与 .tex 文件名相同（去掉 .tex 后缀加 .pdf）
            tex_basename = os.path.splitext(os.path.basename(tex_file))[0]
            pdf_file = os.path.join(temp_dir, f'{tex_basename}.pdf')
            if os.path.exists(pdf_file):
                if pdf_file != output_path:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    shutil.copy(pdf_file, output_path)
                    logger.info("PDF 生成成功: %s", output_path)
                else:
                    logger.info("PDF 生成成功: %s", output_path)
                return True

            # PDF 未生成，说明真正失败了
            if result2.returncode != 0:
                logger.error("xelatex 编译失败，返回码: %s", result2.returncode)
                # 尝试读取 log 文件
                log_file = os.path.join(temp_dir, f'{tex_basename}.log')
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                        log_content = f.read()
                        error_lines = [l for l in log_content.split('\n') if '!' in l or 'error' in l.lower()]
                        if error_lines:
                            logger.error("LaTeX 错误: %s", '; '.join(error_lines[-10:]))
                return False

            logger.error("PDF 文件未生成")
            return False

        except subprocess.TimeoutExpired:
            logger.error("xelatex 编译超时")
            return False
        except Exception:
            logger.exception("xelatex 编译异常")
            return False
        finally:
            # 保留 .tex 文件，不清理 temp_dir
            pass

def generate_preview_pdf(title, time_info, questions, output_path, tex_path=None):
    """生成预览 PDF（使用 xelatex）

    参数:
        title: 试卷标题
        time_info: 考试时间信息
        questions: 题目列表
        output_path: PDF 输出路径
        tex_path: 可选，指定 .tex 文件保存路径
    """

    latex_content = generate_latex_template(title or '试卷预览', time_info or '（考试时间）', questions)

    if compile_latex_to_pdf(latex_content, output_path, tex_path):
        return output_path
    else:
        # 如果 xelatex 失败，返回空
        return None

def generate_paper_pdf(paper, questions, include_answer=True):
    """生成试卷 PDF"""
    # 从 paper 对象获取标题和考试信息
    title = paper.title if hasattr(paper, 'title') else '试卷'

    # 生成时间信息
    time_info = ''
    if hasattr(paper, 'exam_date') and paper.exam_date:
        date_str = paper.exam_date.strftime('%Y年%m月%d日')
        duration = getattr(paper, 'duration', 180) or 180
        hours = duration // 60
        minutes = duration % 60
        if hours > 0 and minutes > 0:
            time_str = f'{hours}小时{minutes}分钟'
        elif hours > 0:
            time_str = f'{hours}小时'
        else:
            time_str = f'{minutes}分钟'
        time_info = f'（{date_str} {time_str}）'
    else:
        time_info = '（考试时间）'

    output_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'papers')
    os.makedirs(output_dir, exist_ok=True)

    pdf_path = os.path.join(output_dir, f'paper_{paper.id}.pdf')

    latex_content = generate_latex_template(title, time_info, questions, include_answer=include_answer)

    if compile_latex_to_pdf(latex_content, pdf_path):
        return pdf_path
    else:
        return None
