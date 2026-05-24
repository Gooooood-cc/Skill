# Douyin (抖音) Platform Reference

## URL → aweme_id Extraction

| Input | aweme_id |
|---|---|
| `https://www.douyin.com/video/7616613170573143162` | `7616613170573143162` |
| `https://www.douyin.com/user/self?modal_id=7616613170573143162&showTab=like` | `7616613170573143162` |
| `https://www.douyin.com/user/self?modal_id=7616613170573143162&showTab=post` | `7616613170573143162` |
| `7616613170573143162` (raw) | `7616613170573143162` |

The `modal_id` query parameter in `/user/self` URLs is the aweme_id.

## Crawl Commands

### Detail Mode (single video)

```bash
cd g:/MediaCrawlerPro/MediaCrawlerPro-Python && \
.venv/Scripts/python.exe main.py \
  --platform dy \
  --type detail \
  --urls "7616613170573143162" \
  --no-enable_comments \
  --no-enable_checkpoint
```

### Creator Mode (all videos from a creator)

```bash
cd g:/MediaCrawlerPro/MediaCrawlerPro-Python && \
.venv/Scripts/python.exe main.py \
  --platform dy \
  --type creator \
  --urls "MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE" \
  --no-enable_comments
```

The creator ID is a `sec_user_id` (base64-encoded string starting with `MS4w`).

## CLI Flags

| Flag | Purpose |
|---|---|
| `--platform dy` | Target 抖音 (required) |
| `--type detail` | Crawl specific video by ID |
| `--type creator` | Crawl all videos from a creator |
| `--urls "aweme_id"` | One or more IDs, comma-separated |
| `--no-enable_comments` | Skip comment crawling (faster) |
| `--no-enable_checkpoint` | Disable checkpoint/resume |

## MySQL Table: `douyin_aweme`

| Column | Source (抖音 API) |
|---|---|
| `aweme_id` | `aweme_detail.aweme_id` |
| `title` | `aweme_detail.title` (may be null) |
| `desc` | `aweme_detail.desc` |
| `create_time` | `aweme_detail.create_time` (Unix → datetime) |
| `duration` | `aweme_detail.video.duration` (milliseconds) |
| `video_play_count` | `aweme_detail.statistics.play_count` |
| `liked_count` | `aweme_detail.statistics.digg_count` |
| `comment_count` | `aweme_detail.statistics.comment_count` |
| `share_count` | `aweme_detail.statistics.share_count` |
| `collected_count` | `aweme_detail.statistics.collect_count` |
| `aweme_url` | `https://www.douyin.com/video/{aweme_id}` |
| `user_id` / `nickname` / `avatar` | `aweme_detail.author.uid` / `nickname` / `avatar_thumb.url_list[0]` |
| `is_synced` | `0` = not synced, `1` = synced to Obsidian |

> If `is_synced` column doesn't exist: `ALTER TABLE douyin_aweme ADD COLUMN is_synced TINYINT DEFAULT 0;`

## YAML Frontmatter

```yaml
title: 视频描述
aweme_id: "7616613170573143162"
author: 作者昵称
platform: 抖音
created: 2025-01-01 12:00:00
video_url: https://www.douyin.com/video/7616613170573143162
duration: 120
played: 1000
liked: 100
comment: 50
share: 10
collected: 5
tags: [抖音, 📥待处理]
type: video
```

## Video Download & Transcription

**yt-dlp does NOT work for Douyin** — the Douyin extractor fails with "Fresh cookies needed" even with valid cookies.

Use the MediaCrawlerPro API stack (CookieBridge + SignSrv) to fetch a fresh download URL, then download with httpx.

### Step-by-step

```bash
cd g:/MediaCrawlerPro/MediaCrawlerPro-Python && .venv/Scripts/python.exe -c "
import asyncio, json, httpx, urllib.request, urllib.parse
from media_platform.douyin.help import get_common_verify_params
from constant.douyin import DOUYIN_FIXED_USER_AGENT, DOUYIN_API_URL
from pkg.rpc.sign_srv_client import SignServerClient, DouyinSignRequest

AWAEME_ID = 'REPLACE_WITH_AWEME_ID'

async def main():
    # 1. Get cookies from CookieBridge
    resp = urllib.request.urlopen('http://localhost:8274/api/cookies/dy')
    data = json.loads(resp.read())
    cookies_str = data['data']['cookies']

    # 2. Get verify params (msToken, webid, verify_fp)
    params = await get_common_verify_params(DOUYIN_FIXED_USER_AGENT)

    # 3. Build API request and sign
    uri = '/aweme/v1/web/aweme/detail/'
    base_params = {
        'aweme_id': AWAEME_ID,
        'verifyFp': params.verify_fp, 'fp': params.verify_fp,
        'msToken': params.ms_token, 'webid': params.webid,
        'device_platform': 'webapp', 'aid': '6383', 'channel': 'channel_pc_web',
    }
    sign_client = SignServerClient()
    query_string = urllib.parse.urlencode(base_params)
    sign_req = DouyinSignRequest(uri=uri, query_params=query_string,
        user_agent=DOUYIN_FIXED_USER_AGENT, cookies=cookies_str)
    sign_resp = await sign_client.douyin_sign(sign_req)
    base_params['a_bogus'] = sign_resp.data.a_bogus

    headers = {
        'Cookie': cookies_str, 'user-agent': DOUYIN_FIXED_USER_AGENT,
        'referer': 'https://www.douyin.com/', 'origin': 'https://www.douyin.com',
    }

    # 4. Fetch video detail → get download URL
    async with httpx.AsyncClient() as c:
        r = await c.get(f'{DOUYIN_API_URL}{uri}', params=base_params, headers=headers)
        aweme = r.json().get('aweme_detail', {})
        video = aweme.get('video', {})
        duration = video.get('duration', 0)
        print(f'Title: {aweme.get(\"desc\", \"\")}')
        print(f'Duration: {duration}ms = {duration//1000}s')

        # Extract download URL (prefer play_addr_h264)
        for key in ['play_addr_h264', 'play_addr', 'play_addr_256']:
            url_list = video.get(key, {}).get('url_list', [])
            if url_list and len(url_list) >= 2:
                download_url = url_list[-1]
                break

        if not download_url: raise Exception('No download URL found')

        # 5. Download video with Range header (required)
        dl_headers = {
            'User-Agent': DOUYIN_FIXED_USER_AGENT,
            'Referer': f'https://www.douyin.com/video/{AWAEME_ID}',
            'Range': 'bytes=0-',
        }
        dl_r = await c.get(download_url, headers=dl_headers, timeout=120)
        out_path = f'downloads/{AWAEME_ID}.mp4'
        with open(out_path, 'wb') as f:
            f.write(dl_r.content)
        print(f'Saved: {out_path} ({len(dl_r.content)/1024/1024:.1f} MB)')

asyncio.run(main())
"
```

### Extract Audio

```bash
ffmpeg -y -i "g:/MediaCrawlerPro/MediaCrawlerPro-Python/downloads/{aweme_id}.mp4" \
  -vn -acodec libmp3lame -q:a 2 \
  "g:/MediaCrawlerPro/MediaCrawlerPro-Python/downloads/{aweme_id}.mp3"
```

### Transcribe via Bcut ASR

```bash
cd g:/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/backend && \
.venv/Scripts/python.exe -c "
from config import settings; settings.ASR_BACKEND = 'bcut'
from services.asr_service import ASRService
result = ASRService().transcribe('g:/MediaCrawlerPro/MediaCrawlerPro-Python/downloads/{aweme_id}.mp3')
print(result.text)
"
```

## Notes

- 抖音 API uses `a_bogus` signing (handled by SignSrv)
- `title` may be null — use `desc` as fallback for display
- Cover image: use `aweme_detail.video.cover.url_list[0]` → `05_Assets/{aweme_id}_1.webp`
- Video download: **yt-dlp is broken for Douyin** — use the API-based method above instead
- Download requires `Range: bytes=0-` header to get full video content (otherwise returns 0 bytes)
- 抖音 videos are always `type: video`
- Creator mode uses `DY_CREATOR_ID_LIST` internally (not `DY_SPECIFIED_ID_LIST`)
