---
name: media-crawler-pro
description: >
  Crawl social media content (B站, 抖音, 小红书) into MySQL via MediaCrawlerPro and sync to Obsidian.
  Covers full pipeline: URL → MySQL → image download → ASR transcription → Obsidian notes.
  Use when user asks to: crawl/scrape/download B站/Bilibili video by BV号 or URL (bilibili.com/video/BV...),
  crawl/scrape/download 抖音/Douyin video by aweme_id or URL (douyin.com/video/...),
  crawl/scrape/download 小红书/XHS notes by note_id or URL (xiaohongshu.com/explore/...),
  sync crawled data to Obsidian, transcribe video/audio, add punctuation to transcripts.
  Skips for: general social media discussion, watching videos, or non-crawl tasks.
---

# MediaCrawlerPro — 社交媒体爬取与 Obsidian 同步

支持三平台：B站 (bilibili)、抖音 (douyin)、小红书 (xhs)。

## 1. Platform Routing

Determine the platform from the user's URL or keywords:

| Signal | Platform | Reference |
|---|---|---|
| `bilibili.com/video/BV...`, `BV` 号, B站 | bilibili | [platform_bilibili.md](references/platform_bilibili.md) |
| `douyin.com/video/...`, `modal_id`, 抖音, aweme_id | douyin | [platform_douyin.md](references/platform_douyin.md) |
| `xiaohongshu.com/explore/...`, 小红书, note_id, xhs | xhs | [platform_xhs.md](references/platform_xhs.md) |

Shared infrastructure (project paths, services, MySQL, Obsidian paths, ASR, LLM): [shared_infra.md](references/shared_infra.md).

## 2. Pre-flight Checklist

Before crawling, verify services are up:

```bash
echo "SignSrv: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8989 2>/dev/null || echo 'down'), CookieBridge: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8274 2>/dev/null || echo 'down')"
```

Start SignSrv if down:
```bash
cd g:/MediaCrawlerPro/MediaCrawlerPro-SignSrv && .venv/Scripts/python.exe app.py &
```

## 3. Crawl: URL → MySQL

### Step 3.1: Extract Platform ID

Parse the platform-specific ID from the user's URL. See the platform reference file for extraction rules.

### Step 3.2: Run Crawler

| Platform | CLI Flag | Table | ID Field |
|---|---|---|---|
| B站 | `--platform bili` | `bilibili_video` | `bvid` |
| 抖音 | `--platform dy` | `douyin_aweme` | `aweme_id` |
| 小红书 | `--platform xhs` | `xhs_note` | `note_id` |

Run the appropriate command from the platform reference. Crawler exits with `---CRAWL_SUMMARY: {..., "status": "completed"}---` on success.

### Step 3.3: Verify in MySQL

```bash
cd g:/MediaCrawlerPro/MediaCrawlerPro-Python
python -c "
import pymysql
conn = pymysql.connect(host='localhost', port=3306, user='root', password='Chijiewei.v587', database='media_crawler_pro', charset='utf8mb4')
cursor = conn.cursor()
cursor.execute('SELECT * FROM <table> WHERE <id_field>=\"<id>\"')
for row in cursor: print(row)
conn.close()
"
```

## 4. Sync: MySQL → Obsidian

### Unified Sync Flow

```
Query is_synced=0 records
  ↓
For each record:
  ├─ Download images → 05_Assets/{platform_id}_{seq}.webp
  ├─ If video type: download video → Bcut ASR transcribe → LLM add punctuation
  ├─ Generate Markdown with YAML frontmatter
  ├─ Write to 03_Resources/{nickname}_{date}_{title}.md
  └─ UPDATE is_synced=1
```

### 4.1 Automated Sync (小红书)

```bash
cd g:/MediaCrawlerPro/MediaCrawlerPro-Python && uv run python scripts/xhs_obsidian_sync.py
```

Video notes are auto-transcribed and punctuated during sync.

### 4.2 Manual Sync (B站 / 抖音)

Query unsynced records from MySQL, then for each record:

1. Download cover image to `05_Assets/{id}_1.webp`
2. If video: download audio → Bcut ASR transcribe → **LLM add punctuation**
   - **B站**: yt-dlp works → `yt-dlp -f "bestaudio[ext=m4a]" -o "<output>.m4a" "<url>"`
   - **抖音**: yt-dlp broken → use API-based download (see [platform_douyin.md](references/platform_douyin.md))
3. Generate `.md` file with YAML frontmatter and body (see template below)
4. Set `is_synced=1`

### 4.3 Unified Markdown Template

```markdown
---
title: 标题
{id_field}: ID值
author: 作者昵称
platform: B站 / 抖音 / 小红书
created: YYYY-MM-DD HH:mm:ss
video_url: 原始链接
... (platform-specific stat fields)
tags: [平台标签, 📥待处理]
type: normal / video
---

### 🖼️ 笔记图集 / 视频封面
![[cover.webp]]

---

### 🎬 视频笔记
> 直链：[点击跳转播放](url)

### 📋 视频转录文字
(transcript text)

---

### 📝 笔记正文
(body text)
```

See platform references for exact YAML fields per platform.

### 4.4 Video Transcription & Punctuation

ASR transcription → immediately add punctuation via MiniMax LLM → write to Obsidian. Both steps run automatically during sync for video-type notes.

**B站 / 小红书**: yt-dlp works for audio download.

```bash
# Download audio (B站 / XHS only — NOT Douyin)
yt-dlp -f "bestaudio[ext=m4a]" -o "<output>.m4a" "<video_url>"

# Transcribe via Bcut ASR
cd g:/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/backend && \
.venv/Scripts/python.exe -c "
from config import settings; settings.ASR_BACKEND = 'bcut'
from services.asr_service import ASRService
result = ASRService().transcribe('<audio_path>')
print(result.text)
"
```

**抖音**: yt-dlp is broken for Douyin. Use the API-based download method (fetch video via Douyin API with cookies → download with httpx → extract audio with ffmpeg → transcribe). See [platform_douyin.md](references/platform_douyin.md) for the full script.

### 4.5 Add Punctuation (Remedial / Batch)

> **标点自动添加已在同步流程中默认执行**，此脚本仅用于补加历史笔记标点。

```bash
cd g:/MediaCrawlerPro/MediaCrawlerPro-Python && uv run python scripts/add_punctuation_by_llm.py
```

Scans all `.md` files in `03_Resources/`，只对 `type: video` 且含转录文字的笔记批量添加标点（MiniMax-M2.7）。

### 4.6 Remedial Operations

Reset a note for re-sync:
```bash
cd g:/MediaCrawlerPro/MediaCrawlerPro-Python
uv run python -c "
import pymysql
conn = pymysql.connect(host='localhost', port=3306, user='root', password='Chijiewei.v587', database='media_crawler_pro')
cursor = conn.cursor()
cursor.execute('UPDATE <table> SET is_synced=0 WHERE <id_field>=\"<id>\"')
conn.commit()
"
```

Re-transcribe video notes by ID range (小红书):
```bash
cd g:/MediaCrawlerPro/MediaCrawlerPro-Python && uv run python scripts/xhs_video_transcribe.py --start-id 212 --end-id 275
```

Copy transcripts from wrong path to correct path (小红书):
```bash
cd g:/MediaCrawlerPro/MediaCrawlerPro-Python && uv run python scripts/copy_transcripts.py --start-id 212 --end-id 275
```

## 5. Troubleshooting

| Problem | Fix |
|---|---|
| SignSrv not responding (port 8989) | Start SignSrv: `cd g:/MediaCrawlerPro/MediaCrawlerPro-SignSrv && .venv/Scripts/python.exe app.py &` |
| CookieBridge not available (port 8274) | Ensure CookieBridge extension/service is running with valid login cookies |
| `time_util.py` datetime error | See [shared_infra.md](references/shared_infra.md) known bug fix |
| Checkpoint skip ("already crawled") | Delete `data/checkpoints/<platform>_detail_*.json` |
| XHS `xsec_token` expired | Re-copy full URL from browser |
| 抖音 cookie expired / account blocked | Refresh cookies via CookieBridge; crawler auto-rotates accounts |
