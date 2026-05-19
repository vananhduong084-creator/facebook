"""
FB Reels Watcher - cloud version (runs on GitHub Actions every 5 min).

Reads recent Reels on a Facebook Page and posts a configured comment
on any Reel that doesn't already have it.

Required env vars (set as GitHub Secrets):
  PAGE_ID                 - Facebook Page ID (numeric string)
  PAGE_ACCESS_TOKEN       - Never-expire Page Access Token

Optional env vars:
  GRAPH_VERSION           - default 'v22.0'
  WATCHER_START_ISO       - ISO 8601 UTC, Reels older than this are skipped
                            (default: today at 00:00 UTC)
  REELS_LIMIT             - how many recent Reels to scan (default 10)
"""

import datetime
import os
import sys
from pathlib import Path

import requests


PAGE_ID = os.environ["PAGE_ID"]
TOKEN = os.environ["PAGE_ACCESS_TOKEN"]
GRAPH = os.environ.get("GRAPH_VERSION", "v22.0")
WATCHER_START = os.environ.get(
    "WATCHER_START_ISO",
    datetime.datetime.utcnow().strftime("%Y-%m-%dT00:00:00Z"),
)
REELS_LIMIT = int(os.environ.get("REELS_LIMIT", "10"))

COMMENT_PATH = Path(__file__).parent / "default-comment.txt"
COMMENT_TEXT = COMMENT_PATH.read_text(encoding="utf-8").strip()
if not COMMENT_TEXT:
    print("default-comment.txt is empty", file=sys.stderr)
    sys.exit(1)

# Detect a unique signature (URL line) for duplicate detection
_sig_lines = [
    line.strip()
    for line in COMMENT_TEXT.splitlines()
    if "http://" in line or "https://" in line
]
SIGNATURE = (
    _sig_lines[0]
    if _sig_lines
    else COMMENT_TEXT.splitlines()[0].strip()
)

GRAPH_BASE = f"https://graph.facebook.com/{GRAPH}"


def log(msg: str, level: str = "INFO") -> None:
    ts = datetime.datetime.utcnow().strftime("%H:%M:%S")
    print(f"{ts} [{level}] {msg}", flush=True)


def fb_get(path: str, params: dict) -> dict:
    p = dict(params)
    p["access_token"] = TOKEN
    r = requests.get(f"{GRAPH_BASE}/{path}", params=p, timeout=30)
    r.raise_for_status()
    return r.json()


def fb_post(path: str, data: dict) -> dict:
    d = dict(data)
    d["access_token"] = TOKEN
    r = requests.post(f"{GRAPH_BASE}/{path}", data=d, timeout=30)
    r.raise_for_status()
    return r.json()


def get_recent_reels() -> list:
    resp = fb_get(
        f"{PAGE_ID}/video_reels",
        {
            "fields": "id,post_id,description,permalink_url,created_time,status",
            "limit": REELS_LIMIT,
        },
    )
    return resp.get("data", [])


def has_my_comment(target_id: str) -> bool:
    resp = fb_get(
        f"{target_id}/comments",
        {"fields": "message,from", "limit": 100},
    )
    for c in resp.get("data", []):
        from_obj = c.get("from") or {}
        msg = c.get("message") or ""
        if from_obj.get("id") == PAGE_ID and SIGNATURE in msg:
            return True
    return False


def parse_fb_time(s: str) -> datetime.datetime:
    # FB returns e.g. "2026-05-19T13:45:00+0000"
    s = s.replace("+0000", "+00:00")
    return datetime.datetime.fromisoformat(s)


def main() -> None:
    log(f"=== Check Page {PAGE_ID} ===")
    log(f"Skip Reels older than: {WATCHER_START}")
    watcher_start_dt = parse_fb_time(
        WATCHER_START if "+" in WATCHER_START or "Z" not in WATCHER_START
        else WATCHER_START.replace("Z", "+00:00")
    )

    try:
        reels = get_recent_reels()
    except Exception as e:
        log(f"Error listing reels: {e}", "ERR")
        if hasattr(e, "response") and e.response is not None:
            log(e.response.text, "ERR")
        sys.exit(1)

    log(f"Found {len(reels)} recent Reels")
    new_count = 0
    skip_count = 0

    for reel in reels:
        rid = reel["id"]
        post_id = reel.get("post_id")
        target_id = post_id or rid

        created_str = reel.get("created_time", "")
        try:
            created_dt = parse_fb_time(created_str)
        except (ValueError, TypeError):
            log(f"Cannot parse created_time: {created_str!r}", "WARN")
            skip_count += 1
            continue

        if created_dt < watcher_start_dt:
            skip_count += 1
            continue

        status_obj = reel.get("status") or {}
        vstatus = status_obj.get("video_status")
        if vstatus and vstatus != "ready":
            log(f"Reel {rid} status={vstatus}, skip for now", "SKIP")
            continue

        try:
            already = has_my_comment(target_id)
        except Exception as e:
            log(f"Error checking comments on {target_id}: {e}", "WARN")
            continue

        if already:
            log(f"Reel {rid} already has my comment, skip", "SKIP")
            skip_count += 1
            continue

        try:
            res = fb_post(f"{target_id}/comments", {"message": COMMENT_TEXT})
            log(
                f"OK - commented on {target_id} "
                f"(comment_id={res.get('id')}, reel={rid})",
                "OK",
            )
            new_count += 1
        except Exception as e:
            log(f"FAIL - comment on {target_id}: {e}", "ERR")
            if hasattr(e, "response") and e.response is not None:
                log(e.response.text, "ERR")

    log(f"=== Done. New={new_count}, Skipped={skip_count} ===")


if __name__ == "__main__":
    main()
