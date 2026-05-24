"""
xhs_video_transcribe.py
根据 video_url 重新转录视频笔记，补充/更新现有 Obsidian 笔记中的转录文字。
跳过封面图下载，直接转录视频并更新已有笔记。

用法：
  # 使用 MediaCrawlerPro-Python 环境
  cd g:/MediaCrawlerPro/MediaCrawlerPro-Python && uv run python scripts/xhs_video_transcribe.py --start-id 212 --end-id 275

  # 或使用 backend 环境（推荐，避免依赖冲突）
  cd g:/MediaCrawlerPro/MediaCrawlerPro-Workspace/MediaCrawlerPro-ContentRemixAgent/backend && uv run python ../../MediaCrawlerPro-Python/scripts/xhs_video_transcribe.py --start-id 212 --end-id 275
"""

import json
import os
import re
import sys
import tempfile
import urllib.request

import pymysql

# ASR 模块 - 兼容两种环境
_bcut_backend = 'g:/MediaCrawlerPro/MediaCrawlerPro-Workspace/MediaCrawlerPro-ContentRemixAgent/backend'
if _bcut_backend not in sys.path:
    sys.path.insert(0, _bcut_backend)

import config as _config
_config.settings.ASR_BACKEND = "bcut"

from services.asr_service import ASRService

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'Chijiewei.v587',
    'database': 'media_crawler_pro',
    'charset': 'utf8mb4',
}

# Obsidian 路径 - 与 xhs_obsidian_sync.py 保持一致
OBSIDIAN_VAULT_DIR = r"G:\Obsidian\Evolution OS"
NOTE_DIR = os.path.join(OBSIDIAN_VAULT_DIR, "raw", "03_Resources")
ATTACHMENT_DIR = os.path.join(OBSIDIAN_VAULT_DIR, "raw", "05_Assets")

# 兼容：原脚本用 INBOX_DIR，新脚本用 NOTE_DIR
INBOX_DIR = NOTE_DIR


def format_transcript(text: str) -> str:
    """
    格式化转录文本，保留原始标点格式
    """
    if not text:
        return text
    return text


def get_safe_filename(title: str, max_length: int = 80) -> str:
    safe = re.sub(r'[\\/*?:"<>|\n\r\t]', "", str(title)).strip()
    return (safe or "无标题笔记")[:max_length]


def find_md_file(title: str, note_id: str, nickname: str) -> str | None:
    """根据笔记信息查找对应的 .md 文件"""
    safe_title = get_safe_filename(title)

    if nickname and nickname.strip():
        safe_nickname = get_safe_filename(nickname.strip())
        # 搜索模式：包含昵称的 md 文件，且标题匹配
        patterns = [
            f"**/{safe_nickname}_*_{safe_title}.md",  # 带日期格式
            f"**/{safe_nickname}_{safe_title}.md",
        ]
    else:
        patterns = [
            f"**/*_{safe_title}.md",
            f"**/{safe_title}.md",
        ]

    # Glob 递归搜索所有子目录
    import glob
    for pattern in patterns:
        matches = glob.glob(os.path.join(INBOX_DIR, pattern), recursive=True)
        if matches:
            return matches[0]
    return None


def update_md_transcript(filepath: str, transcript_text: str):
    """更新 .md 文件中的转录文字部分"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    transcript_section = (
        f"\n\n---\n\n"
        f"### 📋 视频转录文字\n\n"
        f"{transcript_text}\n"
    )

    # 检查是否已有转录部分，有则替换，无则追加
    pattern = r'\n*---\n*\n*### 📋 视频转录文字\n*.*?(?=\n*(?:---|\Z))'
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, transcript_section.strip(), content, flags=re.DOTALL)
    else:
        content = content.rstrip() + transcript_section

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def download_video_to_temp(video_url: str) -> str | None:
    """下载视频到临时文件，返回临时文件路径"""
    try:
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            tmp_path = tmp.name

        print(f"    [下载] 视频到临时文件...")
        urllib.request.urlretrieve(video_url, tmp_path)

        file_size = os.path.getsize(tmp_path)
        if file_size < 1024:
            print(f"    [错误] 下载文件过小: {file_size} bytes")
            os.unlink(tmp_path)
            return None

        print(f"    [下载完成] 大小: {file_size / 1024 / 1024:.1f} MB")
        return tmp_path
    except Exception as e:
        print(f"    [下载错误] {e}")
        return None


def transcribe_and_update(cursor, note_id: str, title: str, nickname: str, video_url: str, dry_run: bool = False):
    """转录单个视频并更新对应笔记"""
    print(f"  [转录] {title[:40]}...")
    print(f"         video_url: {video_url[:60]}...")

    if dry_run:
        print("    [模拟] 跳过实际转录")
        return True

    tmp_path = None
    try:
        # 1. 下载视频到临时文件
        tmp_path = download_video_to_temp(video_url)
        if not tmp_path:
            return False

        # 2. 转录
        print(f"    [转录中] 调用 Bcut ASR...")
        asr = ASRService()
        result = asr.transcribe(tmp_path)

        if result and result.text:
            # 使用 result.text（完整文本），按标点断句保持自然
            transcript_text = format_transcript(result.text)
            print(f"    [成功] 转录长度: {len(transcript_text)} 字符")

            # 3. 找到对应 .md 文件并更新
            md_file = find_md_file(title, note_id, nickname)
            if md_file:
                update_md_transcript(md_file, transcript_text)
                print(f"    [更新] {os.path.basename(md_file)}")
                return True
            else:
                print(f"    [警告] 未找到对应笔记文件")
                return False
        else:
            print(f"    [失败] 转录结果为空")
            return False
    except Exception as e:
        print(f"    [错误] {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理临时文件
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def main():
    import argparse
    parser = argparse.ArgumentParser(description='转录视频笔记并更新 Obsidian 笔记')
    parser.add_argument('--start-id', type=int, default=212, help='起始 ID')
    parser.add_argument('--end-id', type=int, default=275, help='结束 ID')
    parser.add_argument('--dry-run', action='store_true', help='仅显示，不执行转录')
    args = parser.parse_args()

    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT id, note_id, nickname, title, video_url, type
        FROM xhs_note
        WHERE id >= %s AND id <= %s AND type = 'video' AND video_url IS NOT NULL AND video_url != ''
        ORDER BY id ASC
    """, (args.start_id, args.end_id))

    rows = cursor.fetchall()
    print(f"📦 共找到 {len(rows)} 条视频笔记待转录\n")

    success_count = 0
    fail_count = 0

    for row in rows:
        print(f"▶ 处理 [{row['id']}] {row['title'][:50]}")

        success = transcribe_and_update(
            cursor, row['note_id'], row['title'],
            row['nickname'], row['video_url'],
            dry_run=args.dry_run
        )

        if success:
            success_count += 1
        else:
            fail_count += 1

        print()

    conn.close()

    print(f"🎉 完成！成功: {success_count}, 失败: {fail_count}")

    if args.dry_run:
        print("\n[提示] 这是模拟运行，使用 --dry-run 参数。如需实际执行，请去掉该参数。")


if __name__ == "__main__":
    main()