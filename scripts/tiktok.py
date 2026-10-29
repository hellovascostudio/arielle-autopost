"""TikTok support: turn a post's slides into a 9:16 video and publish it via Postiz.

Why a video: TikTok's AI-generated label can only be set on video posts through the API,
and Arielle's posts must always carry that label.

Render (needs ffmpeg; run after scripts/render.py):
    python scripts/tiktok.py posts/queue/2026-11-03-some-post   # one post
    python scripts/tiktok.py --all                              # every queued post with a "tiktok" block

A post goes to TikTok only when its post.json has:
    "tiktok": {"caption": "short TikTok caption with #hashtags ... ✦ AI-generated creator"}

Publishing is done by scripts/publish.py (via publish_tiktok below) using the Postiz CLI
and the POSTIZ_API_KEY secret. Without that secret TikTok is skipped and Instagram works as before.
"""
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent
BRAND = json.loads((ROOT / "brand" / "style.json").read_text(encoding="utf-8"))
TW, TH = 1080, 1920
SECONDS = {"cover": 3.5, "quote": 4.0, "cta": 3.0}  # other slide types: 5 s (time to read)


def render_video(folder):
    folder = Path(folder)
    post = json.loads((folder / "post.json").read_text(encoding="utf-8"))
    imgs = sorted(folder.glob("[0-9][0-9].jpg"))
    if not imgs:
        sys.exit(f"{folder}: no slides yet, run scripts/render.py first")
    bg = BRAND["colors"]["background"]
    with tempfile.TemporaryDirectory() as tmp:
        lines = []
        for i, p in enumerate(imgs):
            kind = post["slides"][i].get("type", "text") if i < len(post["slides"]) else "text"
            slide = Image.open(p).convert("RGB")  # 1080x1350, centred on the tall canvas
            if kind == "photo":  # photos: blurred, darkened copy of the photo fills the bars
                frame = ImageOps.fit(slide, (TW, TH)).filter(ImageFilter.GaussianBlur(40))
                frame = Image.blend(frame, Image.new("RGB", (TW, TH), (0, 0, 0)), 0.25)
            else:
                frame = Image.new("RGB", (TW, TH), bg)
            frame.paste(slide, (0, (TH - slide.height) // 2))
            f = Path(tmp) / f"{i:02d}.png"
            frame.save(f)
            lines += [f"file '{f}'", f"duration {SECONDS.get(kind, 5.0)}"]
        lines.append(f"file '{f}'")  # concat demuxer needs the last frame repeated
        (Path(tmp) / "list.txt").write_text("\n".join(lines))
        out = folder / "tiktok.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(Path(tmp) / "list.txt"),
             "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
             "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)],
            check=True)
    print(f"rendered {out}")
    return out


# ---------- publishing via Postiz ----------

def _postiz(*args):
    r = subprocess.run(["postiz", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"postiz {args[0]} failed: {(r.stderr or r.stdout).strip()[:500]}")
    return r.stdout


def _json(text):
    """The CLI may print a status line before the JSON; parse from the first bracket."""
    starts = [i for i in (text.find("["), text.find("{")) if i >= 0]
    return json.loads(text[min(starts):]) if starts else None


def tiktok_integration_id():
    if os.environ.get("POSTIZ_TIKTOK_ID"):
        return os.environ["POSTIZ_TIKTOK_ID"]
    items = _json(_postiz("integrations:list")) or []
    tiktok = [i for i in items if "tiktok" in str(i.get("identifier", "")).lower() and not i.get("disabled")]
    if len(tiktok) != 1:
        raise RuntimeError(f"expected 1 TikTok channel in Postiz, found {len(tiktok)}; set POSTIZ_TIKTOK_ID")
    return tiktok[0]["id"]


def check():
    """Print the TikTok channel and its settings rules (run via the workflow's 'check' mode)."""
    iid = tiktok_integration_id()
    print(f"Postiz TikTok channel: {iid}")
    print(_postiz("integrations:settings", iid)[:4000])


def publish_tiktok(folder, post):
    video = Path(folder) / "tiktok.mp4"
    if not video.exists():
        raise RuntimeError("tiktok.mp4 missing; run scripts/tiktok.py")
    iid = tiktok_integration_id()
    url = (_json(_postiz("upload", str(video))) or {}).get("path")
    if not url:
        raise RuntimeError("postiz upload returned no path")
    settings = {
        "privacy_level": "PUBLIC_TO_EVERYONE",
        "content_posting_method": "DIRECT_POST",
        "video_made_with_ai": True,   # TikTok AI-generated content label: always on for Arielle
        "duet": False, "stitch": False, "comment": True,
        "brand_content_toggle": False, "brand_organic_toggle": False,
    }
    when = (datetime.now(timezone.utc) + timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = _postiz("posts:create", "-c", post["tiktok"]["caption"], "-m", url, "-s", when,
                  "--settings", json.dumps(settings), "-i", iid)
    res = _json(out)
    if isinstance(res, list) and res:
        res = res[0]
    return (res or {}).get("postId") or (res or {}).get("id") or "scheduled"


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    if args[0] == "--all":
        for d in sorted((ROOT / "posts" / "queue").glob("*/")):
            pj = d / "post.json"
            if pj.exists() and "tiktok" in json.loads(pj.read_text(encoding="utf-8")):
                render_video(d)
    else:
        for a in args:
            render_video(a)
