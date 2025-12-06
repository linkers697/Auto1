# ⟶̽ जय श्री ༢།म > 𝟑🙏🚩
import os
import re
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from youtubesearchpython.__future__ import VideosSearch
from config import YOUTUBE_IMG_URL

# Cache directory
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Canvas dimensions
CANVAS_W, CANVAS_H = 1280, 720
LEFT_W = CANVAS_W // 2
RIGHT_W = CANVAS_W - LEFT_W

# Shadow/glow parameters
SHADOW_BLUR = 20
EDGE_GLOW_ALPHA = 30

# Font loader
def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()

title_font = load_font("RiteshMusic/assets/thumb/font2.ttf", 40)
meta_font = load_font("RiteshMusic/assets/thumb/font.ttf", 20)
duration_font = load_font("RiteshMusic/assets/thumb/font2.ttf", 28)

def clean_text(t):
    return re.sub(r"\s+", " ", (t or "")).strip()

def fit_and_fill(im, target_w, target_h):
    iw, ih = im.size
    target_ratio = target_w / target_h
    img_ratio = iw / ih
    if img_ratio > target_ratio:
        new_w = int(ih * target_ratio)
        left = (iw - new_w) // 2
        im = im.crop((left, 0, left + new_w, ih))
    else:
        new_h = int(iw / target_ratio)
        top = (ih - new_h) // 2
        im = im.crop((0, top, iw, top + new_h))
    return im.resize((target_w, target_h), Image.LANCZOS)

async def get_thumb(videoid: str) -> str:
    out_path = os.path.join(CACHE_DIR, f"{videoid}_final.png")
    if os.path.exists(out_path):
        return out_path

    # Fetch YouTube info
    try:
        results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
        data = await results.next()
        info = data.get("result", [{}])[0]

        title = clean_text(info.get("title", "Unknown Title"))
        thumb = info.get("thumbnails", [{}])[0].get("url", YOUTUBE_IMG_URL)
        duration = info.get("duration")
        views = info.get("viewCount", {}).get("short", "Unknown Views")
        channel = info.get("channel", {}).get("name", "")
    except:
        title = "Unknown Title"
        thumb = YOUTUBE_IMG_URL
        duration = None
        views = "Unknown Views"
        channel = ""

    is_live = not duration or str(duration).lower() in ["", "live", "live now"]
    duration_text = "LIVE" if is_live else (duration or "Unknown")

    # Download thumbnail
    temp_thumb = os.path.join(CACHE_DIR, f"temp_{videoid}.png")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumb) as resp:
                if resp.status == 200:
                    async with aiofiles.open(temp_thumb, "wb") as f:
                        await f.write(await resp.read())
    except:
        temp_thumb = None

    # Base canvas
    base = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))

    # RIGHT PANEL: Thumbnail
    if temp_thumb and os.path.exists(temp_thumb):
        right_img = Image.open(temp_thumb).convert("RGBA")
    else:
        right_img = Image.new("RGBA", (RIGHT_W, CANVAS_H), (30, 30, 30, 255))
    right_img = fit_and_fill(right_img, RIGHT_W, CANVAS_H)
    base.paste(right_img, (LEFT_W,0), right_img)

    # LEFT PANEL: Gradient info panel blending naturally
    left_panel = Image.new("RGBA", (LEFT_W, CANVAS_H), (0, 0, 0, 0))
    draw_left = ImageDraw.Draw(left_panel)
    for x in range(LEFT_W):
        ratio = x / LEFT_W
        sample_x = int(ratio * right_img.width)
        sample_y = CANVAS_H // 2
        r, g, b, a = right_img.getpixel((min(sample_x, right_img.width-1), sample_y))
        blended = int(r*0.6 + 20*0.4), int(g*0.6 + 20*0.4), int(b*0.6 + 20*0.4), 180
        draw_left.line([(x,0),(x,CANVAS_H)], fill=blended)
    base.paste(left_panel, (0,0), left_panel)

    draw = ImageDraw.Draw(base)
    padding = 48
    text_x = padding
    text_y = padding

    # Title wrap
    max_w = LEFT_W - padding*2
    words = title.split()
    lines = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        tw, _ = draw.textsize(test, font=title_font)
        if tw <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    lines = lines[:3]
    for line in lines:
        draw.text((text_x, text_y), line, font=title_font, fill=(255,255,255,255))
        text_y += title_font.getsize(line)[1] + 6
    text_y += 8

    # Channel
    if channel:
        draw.text((text_x, text_y), channel, font=meta_font, fill=(220,235,235,220))
        text_y += 30

    # Views
    draw.text((text_x, text_y), f"Views: {views}", font=meta_font, fill=(200,220,220,200))
    text_y += 34

    # Duration badge
    dur_w, dur_h = draw.textsize(duration_text, font=duration_font)
    badge_pad_x, badge_pad_y = 18, 8
    bx1, by1 = text_x, text_y
    bx2, by2 = bx1 + dur_w + badge_pad_x, by1 + dur_h + badge_pad_y
    badge = Image.new("RGBA", (bx2-bx1, by2-by1), (255,255,255,30))
    bd_draw = ImageDraw.Draw(badge)
    bd_draw.rounded_rectangle((0,0,bx2-bx1,by2-by1), radius=12, fill=(255,255,255,30))
    base.paste(badge, (bx1, by1), badge)
    draw.text((bx1+10, by1+6), duration_text, font=duration_font, fill=(255,255,255,230))

    # Outer glow (adaptive to thumbnail colors)
    edge_layer = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0,0,0,0))
    ed = ImageDraw.Draw(edge_layer)
    for i in range(CANVAS_W):
        for j in [0, CANVAS_H-1]:
            try:
                r, g, b, a = right_img.getpixel((min(i, right_img.width-1), min(j, right_img.height-1)))
            except:
                r,g,b = 255,255,255
            ed.point((i,j), fill=(r,g,b,EDGE_GLOW_ALPHA))
    for j in range(CANVAS_H):
        for i in [0, CANVAS_W-1]:
            try:
                r, g, b, a = right_img.getpixel((min(RIGHT_W-1, right_img.width-1), min(j, right_img.height-1)))
            except:
                r,g,b = 255,255,255
            ed.point((i,j), fill=(r,g,b,EDGE_GLOW_ALPHA))
    edge_layer = edge_layer.filter(ImageFilter.GaussianBlur(18))
    base = Image.alpha_composite(base, edge_layer)

    # Shadow layer
    shadow = base.copy().convert("RGBA").filter(ImageFilter.GaussianBlur(SHADOW_BLUR))
    final = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0,0,0,0))
    final.alpha_composite(shadow, (0,0))
    final.alpha_composite(base, (0,0))

    # Save
    try:
        final.save(out_path)
    except:
        final.convert("RGB").save(out_path)
    try:
        if temp_thumb and os.path.exists(temp_thumb):
            os.remove(temp_thumb)
    except:
        pass

    return out_path
