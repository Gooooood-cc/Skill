"""
add_punctuation_by_llm.py
使用 MiniMax API 为转录文字添加自然标点
"""

import os
import re
import glob
import httpx


CORRECT_DIR = r"G:\Obsidian\Evolution OS\raw\03_Resources"

API_KEY = "sk-cp-R1rQgPgSfvmEfahWzBTITZVf-XzMjL7Er8FFUK2CnphBCOMuQRG1LrM0tmQq7ZkLVcrIy-rQuheVwxqLKe2ByjYjm9ZBxBWhfKI8dJHgS5gn2WDa-UAfWgY"
BASE_URL = "https://api.minimaxi.com/anthropic"
MODEL = "MiniMax-M2.7"


def add_punctuation_by_llm(text: str) -> str:
    """使用 MiniMax API 为文本添加自然标点"""
    if not text:
        return text

    prompt = f"""请为以下转录文字添加自然的标点符号（句号、逗号、问号、感叹号等），使文章通顺易读。

要求：
1. 保持原文的意思不变
2. 添加适当的标点，使句子自然流畅
3. 不要添加额外的解释或说明
4. 直接返回添加标点后的文本

原文：
{text}

添加标点后的文本："""

    try:
        with httpx.Client(timeout=300) as client:
            response = client.post(
                f"{BASE_URL}/v1/messages",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4000,
                },
            )
            response.raise_for_status()
            result = response.json()
            if "content" in result:
                for block in result["content"]:
                    if block.get("type") == "text":
                        return block["text"].strip()
            return text
    except Exception as e:
        print(f"API 错误: {e}")
        return text


def extract_transcript(content):
    pattern = r'### 📋 视频转录文字\n+\n*(.*?)(?=\n*---|\Z)'
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else None


def update_transcript(content, new_text):
    pattern = r'\n*---\n*\n*### 📋 视频转录文字\n*.*?(?=\n*---|\Z)'
    new_section = f'\n\n---\n\n### 📋 视频转录文字\n\n{new_text}\n'
    if re.search(pattern, content, re.DOTALL):
        return re.sub(pattern, new_section, content, flags=re.DOTALL)
    return content


def main():
    print("使用 MiniMax API 添加自然标点\n")

    md_files = list(glob.glob(f"{CORRECT_DIR}/**/*.md", recursive=True))
    print(f"共找到 {len(md_files)} 条笔记待处理\n")

    count = 0
    for md_file in md_files:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        old_text = extract_transcript(content)
        if not old_text:
            continue

        print(f"处理: {os.path.basename(md_file)}")

        new_text = add_punctuation_by_llm(old_text)
        if new_text and new_text != old_text:
            content = update_transcript(content, new_text)
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(content)
            count += 1
            print(f"  ✅ 已更新 ({len(new_text)} 字符)")
        else:
            print(f"  ⏭️  跳过")

    print(f"\n完成！共更新 {count} 条笔记")


if __name__ == "__main__":
    main()
