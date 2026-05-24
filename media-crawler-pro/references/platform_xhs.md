# Xiaohongshu (小红书) Platform Reference

## URL Requirements

小红书 URL must carry `xsec_token` and `xsec_source` (time-sensitive, copy full URL from browser address bar):

```
https://www.xiaohongshu.com/explore/{note_id}?xsec_token=xxx&xsec_source=pc_feed
```

## Crawl Command

```bash
cd g:/MediaCrawlerPro/MediaCrawlerPro-Python

# Single note (MySQL storage, no comments)
DB_TYPE=mysql ACCOUNT_POOL_SAVE_TYPE=cookie_bridge \
  uv run main.py \
  --platform xhs --type detail \
  --urls "https://www.xiaohongshu.com/explore/{note_id}?xsec_token=xxx&xsec_source=pc_feed"

# Batch (multiple URLs comma-separated)
DB_TYPE=mysql ACCOUNT_POOL_SAVE_TYPE=cookie_bridge \
  uv run main.py \
  --platform xhs --type detail \
  --urls "URL1,URL2,URL3"
```

## Cookie Check

```bash
curl -s http://localhost:8274/api/cookies/xhs | python -c "import sys,json; d=json.load(sys.stdin); print('Cookie OK' if d.get('isok') and d.get('data',{}).get('cookies') else 'Cookie MISSING')"
```

## Verify Crawl Result

```bash
cd g:/MediaCrawlerPro/MediaCrawlerPro-Python
python -c "
import pymysql
conn = pymysql.connect(host='localhost', port=3306, user='root', password='Chijiewei.v587', database='media_crawler_pro', charset='utf8mb4')
cursor = conn.cursor()
cursor.execute(\"SELECT note_id, title, type, nickname, is_synced FROM xhs_note WHERE note_id='your_note_id'\")
for row in cursor: print(row)
conn.close()
"
```

## MySQL Table: `xhs_note`

| Column | Type | Description |
|---|---|---|
| `id` | int | Auto-increment PK |
| `note_id` | varchar | Note unique ID |
| `user_id` | varchar | Author ID |
| `nickname` | varchar | Author nickname |
| `title` | varchar | Note title |
| `desc` | text | Note body text |
| `type` | varchar | `normal` or `video` |
| `video_url` | varchar | Video URL (video type only) |
| `image_list` | text | Image URLs (comma-separated) |
| `local_images` | text | Local image filenames |
| `tag_list` | varchar | Tags (comma-separated) |
| `note_url` | varchar | Original URL |
| `liked_count` | int | Likes |
| `collected_count` | int | Collections |
| `comment_count` | int | Comments |
| `share_count` | int | Shares |
| `time` | datetime | Publish time |
| `ip_location` | varchar | IP location |
| `is_synced` | tinyint | `0`=not synced, `1`=synced |
| `source_keyword` | varchar | Source keyword |

## YAML Frontmatter

```yaml
title: 笔记标题
note_id: 笔记ID
author: 作者昵称
ip_location: IP属地
platform: 小红书
created: 2025-01-01 12:00:00
note_url: https://www.xiaohongshu.com/explore/xxx
source_keyword: 来源关键词
liked: 100
collected: 50
comment: 20
share: 10
tags: [小红书, 📥待处理, 原标签...]
type: normal / video
```

## Sync Scripts

All located in `g:/MediaCrawlerPro/MediaCrawlerPro-Python/scripts/`:

| Script | Purpose |
|---|---|
| `xhs_obsidian_sync.py` | Main sync: MySQL → Obsidian (with image download + video transcription) |
| `add_punctuation_by_llm.py` | Add natural punctuation to transcripts via MiniMax LLM |
| `xhs_video_transcribe.py` | Re-transcribe video notes by ID range, update Obsidian |
| `copy_transcripts.py` | Copy transcripts from wrong path to correct path (remedial) |

Skill-bundled copies in `scripts/` are for reference; actual execution uses MediaCrawlerPro-Python copies.

## Common Issues

| Issue | Cause | Fix |
|---|---|---|
| `Note xxx is already crawled, skip` | Checkpoint recorded | Delete `data/checkpoints/xhs_detail_*.json` |
| `账号池中没有可用的账号` | Cookie expired/missing | Re-login to 小红书 in browser, check CookieBridge |
| `xsec_token` expired | Token time-sensitive | Re-copy full URL from browser |
