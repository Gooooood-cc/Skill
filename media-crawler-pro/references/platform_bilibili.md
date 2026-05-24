# Bilibili (B站) Platform Reference

## URL → BV号 Extraction

| Input | BV号 |
|---|---|
| `https://www.bilibili.com/video/BV1VSFAz2EKS/` | `BV1VSFAz2EKS` |
| `https://www.bilibili.com/video/BV1VSFAz2EKS/?spm_id_from=xxx` | `BV1VSFAz2EKS` |
| `BV1VSFAz2EKS` (raw) | `BV1VSFAz2EKS` |

## Crawl Command

```bash
cd g:/MediaCrawlerPro/MediaCrawlerPro-Python && \
.venv/Scripts/python.exe main.py \
  --platform bili \
  --type detail \
  --urls "BV1VSFAz2EKS" \
  --no-enable_comments \
  --no-enable_checkpoint
```

## CLI Flags

| Flag | Purpose |
|---|---|
| `--platform bili` | Target B站 (required) |
| `--type detail` | Crawl specific video by ID (required) |
| `--urls "BV号"` | One or more BV号s, comma-separated |
| `--no-enable_comments` | Skip comment crawling (faster) |
| `--no-enable_checkpoint` | Disable checkpoint/resume |

## MySQL Table: `bilibili_video`

| Column | Source (B站 API) |
|---|---|
| `video_id` | `aid` |
| `bvid` | `bvid` |
| `title` | `title` |
| `desc` | `desc` |
| `create_time` | `pubdate` (Unix → datetime) |
| `duration` | `duration` (seconds) |
| `video_play_count` | `stat.view` |
| `liked_count` | `stat.like` |
| `video_comment` | `stat.reply` |
| `video_danmaku` | `stat.danmaku` |
| `video_url` | Constructed from bvid |
| `video_cover_url` | `pic` |
| `user_id` / `nickname` / `avatar` | `owner.mid` / `owner.name` / `owner.face` |
| `is_synced` | `0` = not synced, `1` = synced to Obsidian |

> If `is_synced` column doesn't exist: `ALTER TABLE bilibili_video ADD COLUMN is_synced TINYINT DEFAULT 0;`

## YAML Frontmatter

```yaml
title: 视频标题
bvid: BVxxxxxxxxx
author: UP主昵称
platform: B站
created: 2025-01-01 12:00:00
video_url: https://www.bilibili.com/video/BVxxxxxxxxx
duration: 120
played: 1000
liked: 100
comment: 50
danmaku: 30
tags: [B站, 📥待处理]
type: video
```

## Notes

- B站 API uses `wbi` signing (handled by SignSrv)
- Cover image: download `video_cover_url` → `05_Assets/{bvid}_1.webp`
- Video download for transcription: `yt-dlp -f "bestaudio[ext=m4a]" -o "<output>.m4a" "<bilibili_url>"`
- B站 videos are always `type: video`
