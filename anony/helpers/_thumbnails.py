# thumbnail.py
# FINAL CLEAN VERSION
# Apple Glassmorphism + Full Controls + Fixed Layout

import os
import math
import aiohttp

from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
    ImageOps
)

from anony import config

PURPLE = (124, 58, 237)
PURPLE_SOFT = (167, 139, 250)
WHITE = (255, 255, 255)
BG_DARK = (6, 3, 16)

SIZE = (1280, 720)


# ─────────────────────────────
# HELPERS
# ─────────────────────────────

def _linear_gradient(size, c1, c2, vertical=True):

    w, h = size

    img = Image.new("RGBA", size)

    draw = ImageDraw.Draw(img)

    if vertical:

        for y in range(h):

            t = y / h

            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)

            draw.line((0, y, w, y), fill=(r, g, b, 255))

    else:

        for x in range(w):

            t = x / w

            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)

            draw.line((x, 0, x, h), fill=(r, g, b, 255))

    return img


def _build_background(song_img):

    bg = ImageOps.fit(
        song_img.convert("RGB"),
        SIZE,
        method=Image.LANCZOS
    )

    bg = bg.filter(ImageFilter.GaussianBlur(12))

    bg = ImageEnhance.Brightness(bg).enhance(0.38)

    bg = ImageEnhance.Color(bg).enhance(1.25)

    bg = bg.convert("RGBA")

    overlay = Image.new(
        "RGBA",
        SIZE,
        (*BG_DARK, 130)
    )

    bg = Image.alpha_composite(bg, overlay)

    return bg


def _pill(base, x, y, w, h, fill, outline=None, radius=None):

    radius = radius or h // 2

    layer = Image.new(
        "RGBA",
        (w, h),
        (0, 0, 0, 0)
    )

    d = ImageDraw.Draw(layer)

    d.rounded_rectangle(
        (0, 0, w - 1, h - 1),
        radius=radius,
        fill=fill,
        outline=outline,
        width=1 if outline else 0
    )

    base.paste(layer, (x, y), layer)


def _gradient_text(base, draw, xy, text, font):

    tw = int(draw.textlength(text, font=font))

    th = font.size + 12

    grad = _linear_gradient(
        (tw + 10, th),
        WHITE,
        PURPLE_SOFT,
        vertical=False
    )

    alpha = Image.new(
        "RGBA",
        (tw + 10, th),
        (0, 0, 0, 0)
    )

    ImageDraw.Draw(alpha).text(
        (0, 0),
        text,
        font=font,
        fill=(255, 255, 255, 255)
    )

    grad.putalpha(alpha.getchannel("A"))

    base.paste(grad, xy, grad)


# ─────────────────────────────
# GLASS CARD
# ─────────────────────────────

def _draw_glass_card(base, x, y, w, h, radius=32):

    crop = base.crop((x, y, x + w, y + h))

    crop = crop.filter(ImageFilter.GaussianBlur(20))

    dark = Image.new(
        "RGBA",
        (w, h),
        (25, 25, 30, 85)
    )

    crop = Image.alpha_composite(crop, dark)

    mask = Image.new("L", (w, h), 0)

    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, w - 1, h - 1),
        radius=radius,
        fill=255
    )

    crop.putalpha(mask)

    base.paste(crop, (x, y), crop)

    border = Image.new(
        "RGBA",
        (w, h),
        (0, 0, 0, 0)
    )

    d = ImageDraw.Draw(border)

    d.rounded_rectangle(
        (0, 0, w - 1, h - 1),
        radius=radius,
        outline=(255, 255, 255, 45),
        width=1
    )

    base.paste(border, (x, y), border)


# ─────────────────────────────
# PLAYER ICONS
# ─────────────────────────────

def _draw_triangle(layer, cx, cy, size, direction="right", color=(255,255,255,230)):

    d = ImageDraw.Draw(layer)

    h = size

    w = int(size * 0.85)

    if direction == "right":

        pts = [
            (cx-w//2+2, cy-h//2),
            (cx-w//2+2, cy+h//2),
            (cx+w//2, cy)
        ]

    else:

        pts = [
            (cx+w//2-2, cy-h//2),
            (cx+w//2-2, cy+h//2),
            (cx-w//2, cy)
        ]

    d.polygon(pts, fill=color)


def _draw_double_triangle(layer, cx, cy, size, direction="right", color=(255,255,255,230)):

    gap = int(size * 0.28)

    if direction == "right":

        _draw_triangle(layer, cx-gap, cy, size, "right", color)

        _draw_triangle(layer, cx+gap, cy, size, "right", color)

    else:

        _draw_triangle(layer, cx+gap, cy, size, "left", color)

        _draw_triangle(layer, cx-gap, cy, size, "left", color)


def _draw_shuffle_icon(layer, cx, cy, size, color=(255,255,255,180)):

    d = ImageDraw.Draw(layer)

    s = size // 2

    lw = max(2, size // 8)

    x1,y1 = cx-s, cy-s//2
    x2,y2 = cx+s, cy+s//2

    d.line([(x1,y1),(x2,y2)], fill=color, width=lw)

    d.line([(x1,y2),(x2,y1)], fill=color, width=lw)


def _draw_repeat_icon(layer, cx, cy, size, color=(255,255,255,180)):

    d = ImageDraw.Draw(layer)

    r = size // 2

    lw = max(2, size // 8)

    d.arc(
        [cx-r, cy-r, cx+r, cy+r],
        start=40,
        end=320,
        fill=color,
        width=lw
    )


def _draw_volume_icon(layer, cx, cy, size, color=(255,255,255,180)):

    d = ImageDraw.Draw(layer)

    s = size // 2

    pts = [
        (cx-s,cy-s//3),
        (cx-s//3,cy-s//3),
        (cx,cy-s),
        (cx,cy+s),
        (cx-s//3,cy+s//3),
        (cx-s,cy+s//3)
    ]

    d.polygon(pts, fill=color)


# ─────────────────────────────
# PLAYER
# ─────────────────────────────

def _draw_player(base, x, y):

    BTN = 54

    PLAY = 74

    FG = (255,255,255,220)

    FG_DIM = (255,255,255,150)

    ICON = 15

    cx = x - 30

    def _btn(sz):

        return Image.new(
            "RGBA",
            (sz, sz),
            (0,0,0,0)
        )

    # SHUFFLE

    _pill(base, cx, y, BTN, BTN,
          (255,255,255,18),
          (255,255,255,40),
          BTN//2)

    sh = _btn(BTN)

    _draw_shuffle_icon(
        sh,
        BTN//2,
        BTN//2,
        ICON+2,
        FG_DIM
    )

    base.paste(sh, (cx,y), sh)

    cx += BTN + 12

    # PREVIOUS

    _pill(base, cx, y, BTN, BTN,
          (255,255,255,18),
          (255,255,255,40),
          BTN//2)

    pv = _btn(BTN)

    _draw_double_triangle(
        pv,
        BTN//2,
        BTN//2,
        ICON,
        "left",
        FG
    )

    base.paste(pv, (cx,y), pv)

    cx += BTN + 14

    # PLAY

    px = cx

    py = y - 10

    glow = Image.new(
        "RGBA",
        (PLAY+90, PLAY+90),
        (0,0,0,0)
    )

    gd = ImageDraw.Draw(glow)

    gd.ellipse(
        (45,45,PLAY+45,PLAY+45),
        fill=(*PURPLE,120)
    )

    glow = glow.filter(ImageFilter.GaussianBlur(35))

    base.paste(glow, (px-45, py-45), glow)

    _pill(base, px, py, PLAY, PLAY,
          (*PURPLE,255),
          (*PURPLE_SOFT,120),
          PLAY//2)

    pl = _btn(PLAY)

    _draw_triangle(
        pl,
        PLAY//2 + 5,
        PLAY//2,
        28,
        "right",
        WHITE
    )

    base.paste(pl, (px, py), pl)

    cx += PLAY + 16

    # NEXT

    _pill(base, cx, y, BTN, BTN,
          (255,255,255,18),
          (255,255,255,40),
          BTN//2)

    nx = _btn(BTN)

    _draw_double_triangle(
        nx,
        BTN//2,
        BTN//2,
        ICON,
        "right",
        FG
    )

    base.paste(nx, (cx,y), nx)

    cx += BTN + 12

    # REPEAT

    _pill(base, cx, y, BTN, BTN,
          (255,255,255,18),
          (255,255,255,40),
          BTN//2)

    rp = _btn(BTN)

    _draw_repeat_icon(
        rp,
        BTN//2,
        BTN//2,
        ICON+2,
        FG_DIM
    )

    base.paste(rp, (cx,y), rp)

    cx += BTN + 18

    # VOLUME

    vi = _btn(28)

    _draw_volume_icon(
        vi,
        14,
        14,
        12,
        FG_DIM
    )

    base.paste(vi, (cx, y+13), vi)

    cx += 42

    # SLIDER

    slider_w = 160

    slider = Image.new(
        "RGBA",
        (slider_w, 6),
        (0,0,0,0)
    )

    ImageDraw.Draw(slider).rounded_rectangle(
        (0,0,slider_w-1,5),
        radius=3,
        fill=(255,255,255,35)
    )

    base.paste(slider, (cx, y+24), slider)

    fill = _linear_gradient(
        (95,6),
        PURPLE,
        PURPLE_SOFT,
        vertical=False
    )

    base.paste(fill, (cx, y+24), fill)


# ─────────────────────────────
# PROGRESS
# ─────────────────────────────

def _draw_progress(base, draw, x, y, width, cur, end, font):

    draw.text(
        (x, y-24),
        cur,
        font=font,
        fill=(255,255,255,170)
    )

    rw = int(draw.textlength(end, font=font))

    draw.text(
        (x+width-rw, y-24),
        end,
        font=font,
        fill=(255,255,255,170)
    )

    track = Image.new(
        "RGBA",
        (width,5),
        (0,0,0,0)
    )

    ImageDraw.Draw(track).rounded_rectangle(
        (0,0,width-1,4),
        radius=3,
        fill=(255,255,255,35)
    )

    base.paste(track, (x,y), track)

    fw = int(width * 0.18)

    fill = Image.new(
        "RGBA",
        (fw,5),
        (255,255,255,220)
    )

    base.paste(fill, (x,y), fill)


# ─────────────────────────────
# MAIN CLASS
# ─────────────────────────────

class Thumbnail:

    def __init__(self):

        self.session = None

        base = "anony/helpers/"

        self.f_title = ImageFont.truetype(
            base + "Raleway-Bold.ttf",
            42
        )

        self.f_small = ImageFont.truetype(
            base + "Inter-Light.ttf",
            22
        )

        self.f_badge = ImageFont.truetype(
            base + "Inter-Light.ttf",
            18
        )

        self.f_brand = ImageFont.truetype(
            base + "Raleway-Bold.ttf",
            30
        )

        self.f_power = ImageFont.truetype(
            base + "Inter-Light.ttf",
            18
        )

    async def start(self):

        self.session = aiohttp.ClientSession()

    async def close(self):

        await self.session.close()

    async def save_thumb(self, path, url):

        async with self.session.get(url) as resp:

            with open(path, "wb") as f:

                f.write(await resp.read())

        return path

    async def generate(self, song):

        try:

            W, H = SIZE

            temp = f"cache/temp_{song.id}.jpg"

            output = f"cache/{song.id}.png"

            await self.save_thumb(temp, song.thumbnail)

            raw = Image.open(temp).convert("RGBA")

            base = _build_background(raw)

            draw = ImageDraw.Draw(base)

            # CARD

            CARD_X = 40
            CARD_Y = 90
            CARD_W = 1200
            CARD_H = 470

            _draw_glass_card(
                base,
                CARD_X,
                CARD_Y,
                CARD_W,
                CARD_H
            )

            # ART

            art = ImageOps.fit(
                raw,
                (420,420),
                method=Image.LANCZOS
            )

            mask = Image.new("L", (420,420), 0)

            ImageDraw.Draw(mask).rounded_rectangle(
                (0,0,419,419),
                radius=35,
                fill=255
            )

            art.putalpha(mask)

            base.paste(art, (70,115), art)

            tx = 520

            # BADGE

            badge = "▶ NOW PLAYING"

            bw = int(
                draw.textlength(
                    badge,
                    font=self.f_badge
                )
            ) + 40

            _pill(
                base,
                tx,
                140,
                bw,
                38,
                (*PURPLE,70),
                (*PURPLE_SOFT,90),
                19
            )

            draw.text(
                (tx+20,148),
                badge,
                font=self.f_badge,
                fill=(*PURPLE_SOFT,255)
            )

            # TITLE

            title = song.title.strip()

            max_width = 560

            original_title = title

            while draw.textlength(
                title,
                font=self.f_title
            ) > max_width:

                title = title[:-1]

                if len(title) <= 3:
                    break

            if title != original_title:

                title = title[:-3] + "..."

            _gradient_text(
                base,
                draw,
                (tx,210),
                title,
                self.f_title
            )

            # CHANNEL

            draw.text(
                (tx,310),
                song.channel_name[:35],
                font=self.f_small,
                fill=(255,255,255,190)
            )

            # CHIPS

            chip_y = 360

            chips = [
                f"{song.view_count}",
                "HD Audio",
                f"{song.duration}"
            ]

            cx = tx

            for c in chips:

                cw = int(
                    draw.textlength(
                        c,
                        font=self.f_badge
                    )
                ) + 40

                _pill(
                    base,
                    cx,
                    chip_y,
                    cw,
                    42,
                    (255,255,255,18),
                    (255,255,255,35),
                    21
                )

                draw.text(
                    (cx+20, chip_y+10),
                    c,
                    font=self.f_badge,
                    fill=(255,255,255,180)
                )

                cx += cw + 16

            # PLAYER

            _draw_player(
                base,
                tx + 35,
                430
            )

            # PROGRESS

            _draw_progress(
                base,
                draw,
                tx,
                500,
                700,
                "0:01",
                song.duration,
                self.f_badge
            )

            # WATERMARK

            wm1 = "CherryMusic"

            wm2 = "Powered by AlfaBots"

            w1 = int(
                draw.textlength(
                    wm1,
                    font=self.f_brand
                )
            )

            w2 = int(
                draw.textlength(
                    wm2,
                    font=self.f_power
                )
            )

            _gradient_text(
                base,
                draw,
                ((W - w1)//2, 620),
                wm1,
                self.f_brand
            )

            draw.text(
                ((W - w2)//2, 665),
                wm2,
                font=self.f_power,
                fill=(255,255,255,170)
            )

            base.save(output)

            try:
                os.remove(temp)
            except:
                pass

            return output

        except Exception:

            return config.DEFAULT_THUMB
