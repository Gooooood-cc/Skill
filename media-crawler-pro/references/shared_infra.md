# Shared Infrastructure

All three platforms share the same MediaCrawlerPro stack.

## Project Paths (Windows)

| Component | Path |
|---|---|
| Python Project Root | `g:/MediaCrawlerPro/MediaCrawlerPro-Python` |
| Python Interpreter | `g:/MediaCrawlerPro/MediaCrawlerPro-Python/.venv/Scripts/python.exe` |
| Sign Service Root | `g:/MediaCrawlerPro/MediaCrawlerPro-SignSrv` |
| Sign Service Interpreter | `g:/MediaCrawlerPro/MediaCrawlerPro-SignSrv/.venv/Scripts/python.exe` |
| Sign Service Entry | `g:/MediaCrawlerPro/MediaCrawlerPro-SignSrv/app.py` |
| ContentRemixAgent Backend | `g:/MediaCrawlerPro/MediaCrawlerPro-Workspace/MediaCrawlerPro-ContentRemixAgent/backend` |

## Services Required

| Service | Port | Health Check | Purpose |
|---|---|---|---|
| SignSrv | 8989 | `curl http://localhost:8989` (404=Tornado=OK) | Request signing |
| CookieBridge | 8274 | `curl http://localhost:8274` | Login cookie provider |
| MySQL | 3306 | `mysql -u root -pChijiewei.v587 -e "SELECT 1"` | Data storage |

## Quick Health Check

```bash
echo "SignSrv: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8989 2>/dev/null || echo 'down'), CookieBridge: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8274 2>/dev/null || echo 'down')"
```

## MySQL Configuration

| Setting | Value |
|---|---|
| Host | `localhost` |
| Port | `3306` |
| User | `root` |
| Password | `Chijiewei.v587` |
| Database | `media_crawler_pro` |

## Obsidian Configuration

| Setting | Value |
|---|---|
| Vault Path | `G:\Obsidian\Evolution OS` |
| Note Directory | `G:\Obsidian\Evolution OS\raw\03_Resources` |
| Attachment Directory | `G:\Obsidian\Evolution OS\raw\05_Assets` |
| File Naming | `{nickname}_{date}_{title}.md` |
| Image Naming | `{platform_id}_{seq}.webp` |

## ASR Configuration

| Setting | Value |
|---|---|
| Engine | Bcut ASR (B站必剪云端 API) |
| Backend Path | `g:/MediaCrawlerPro/MediaCrawlerPro-Workspace/MediaCrawlerPro-ContentRemixAgent/backend` |

```python
import sys
sys.path.insert(0, 'g:/MediaCrawlerPro/MediaCrawlerPro-Workspace/MediaCrawlerPro-ContentRemixAgent/backend')
import config as _config
_config.settings.ASR_BACKEND = "bcut"
from services.asr_service import ASRService
result = ASRService().transcribe(video_path)
# result.text: full transcript; result.segments: list of Segment(start, end, text)
```

## LLM Configuration (Punctuation)

| Setting | Value |
|---|---|
| API | MiniMax Anthropic-compatible |
| Base URL | `https://api.minimaxi.com/anthropic` |
| Model | `MiniMax-M2.7` |

## Known Bug Fix

File: `MediaCrawlerPro-Python/pkg/tools/time_util.py`

`get_time_str_from_unix_time` and `get_date_str_from_unix_time`:
`unixtime = int(unixtime)` must be placed **before** the `if int(unixtime) > 1000000000000:` check, otherwise `time.localtime()` throws `'str' object cannot be interpreted as an integer` when the value is not > 1e12.
