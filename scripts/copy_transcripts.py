"""
copy_transcripts.py
从错误路径复制转录文字到正确路径的笔记。
"""

import os
import re
import glob

# 错误路径（第一次转录写入的位置）
WRONG_DIR = r"G:\Obsidian\Source\Inbox"

# 正确路径
CORRECT_DIR = r"G:\Obsidian\Evolution OS\raw\03_Resources"


def get_safe_filename(title: str, max_length: int = 80) -> str:
    safe = re.sub(r'[\\/*?:"<>|\n\r\t]', "", str(title)).strip()
    return (safe or "无标题笔记")[:max_length]


def extract_transcript(filepath: str) -> str | None:
    """从笔记中提取转录文字部分"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配转录文字部分
    pattern = r'\n*---\n*\n*### 📋 视频转录文字\n*\n*(.*?)(?=\n*(?:---|\Z))'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def find_transcript_file(title: str, nickname: str) -> tuple[str, str] | None:
    """在错误路径中查找包含该标题转录文字的文件"""
    safe_title = get_safe_filename(title)

    if nickname and nickname.strip():
        safe_nickname = get_safe_filename(nickname.strip())
        patterns = [
            f"**/{safe_nickname}_*_{safe_title}.md",
            f"**/{safe_nickname}_{safe_title}.md",
        ]
    else:
        patterns = [
            f"**/*_{safe_title}.md",
            f"**/{safe_title}.md",
        ]

    for pattern in patterns:
        matches = glob.glob(os.path.join(WRONG_DIR, pattern), recursive=True)
        for match in matches:
            transcript = extract_transcript(match)
            if transcript:
                return match, transcript
    return None


def find_correct_file(title: str, nickname: str) -> str | None:
    """在正确路径中查找对应的笔记文件"""
    safe_title = get_safe_filename(title)

    if nickname and nickname.strip():
        safe_nickname = get_safe_filename(nickname.strip())
        patterns = [
            f"**/{safe_nickname}_*_{safe_title}.md",
            f"**/{safe_nickname}_{safe_title}.md",
        ]
    else:
        patterns = [
            f"**/*_{safe_title}.md",
            f"**/{safe_title}.md",
        ]

    for pattern in patterns:
        matches = glob.glob(os.path.join(CORRECT_DIR, pattern), recursive=True)
        if matches:
            return matches[0]
    return None


def copy_transcript_to_correct(filepath: str, transcript_text: str):
    """将转录文字复制到正确路径的笔记"""
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


def main():
    import pymysql
    import argparse

    parser = argparse.ArgumentParser(description='复制转录文字到正确路径')
    parser.add_argument('--start-id', type=int, default=212, help='起始 ID')
    parser.add_argument('--end-id', type=int, default=275, help='结束 ID')
    args = parser.parse_args()

    DB_CONFIG = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'Chijiewei.v587',
        'database': 'media_crawler_pro',
        'charset': 'utf8mb4',
    }

    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT id, note_id, nickname, title, video_url, type
        FROM xhs_note
        WHERE id >= %s AND id <= %s AND type = 'video' AND video_url IS NOT NULL AND video_url != ''
        ORDER BY id ASC
    """, (args.start_id, args.end_id))

    rows = cursor.fetchall()
    print(f"📦 共找到 {len(rows)} 条视频笔记\n")

    success_count = 0
    skip_count = 0
    fail_count = 0

    for row in rows:
        print(f"▶ 处理 [{row['id']}] {row['title'][:50]}")

        # 1. 在错误路径查找转录文字
        result = find_transcript_file(row['title'], row['nickname'])
        if not result:
            print(f"    [跳过] 错误路径中未找到转录")
            skip_count += 1
            continue

        wrong_file, transcript = result
        print(f"    [找到] {os.path.basename(wrong_file)}")

        # 2. 在正确路径查找对应文件
        correct_file = find_correct_file(row['title'], row['nickname'])
        if not correct_file:
            print(f"    [警告] 正确路径中未找到对应笔记")
            fail_count += 1
            continue

        # 3. 复制转录文字
        copy_transcript_to_correct(correct_file, transcript)
        print(f"    [复制] {os.path.basename(correct_file)}")
        success_count += 1
        print()

    conn.close()

    print(f"🎉 完成！成功: {success_count}, 跳过: {skip_count}, 失败: {fail_count}")


if __name__ == "__main__":
    main()