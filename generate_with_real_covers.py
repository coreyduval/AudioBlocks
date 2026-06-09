#!/usr/bin/env python3
"""
Run this script on your own computer to generate a version of the
mini-book wrap PDF using the real Audible cover artwork.

Requirements:
    pip install reportlab Pillow requests

Usage:
    python3 generate_with_real_covers.py ALE-spreadsheet-library.csv out.pdf

The script reads your Audible Library Exporter CSV, downloads all cover
images, and tiles full-wrap (back | spine | front) strips across pages
ready to print, cut, and glue onto your 3D-printed mini books.
"""

import sys, os, json, hashlib, re, argparse
import requests
import pandas as pd
from io import BytesIO
from PIL import Image
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth

# ── Physical dimensions ──────────────────────────────────────────────────────
# Calibrate these to your actual printed mini books once you have one in hand.
SCALE        = 60.0 / 22.0          # 60mm-tall books
BOOK_HEIGHT  = 22.0 * SCALE          # 60.0 mm — tall dimension
COVER_WIDTH  = 15.0 * SCALE          # 40.91 mm — front/back cover width
SPINE_BINS = [                       # (max_pages, spine_width_mm) — scaled
    (250,   4.0 * SCALE),
    (400,   6.0 * SCALE),
    (550,   8.5 * SCALE),
    (10**9, 11.0 * SCALE),
]
F          = SCALE   # font / inset scale factor
GAP        = 5.0     # mm — gap between wraps on the page
MARGIN     = 10.0    # mm — page margin
PRINT_DPI  = 300     # pixels per inch for embedded images

# ── Colour palette (deterministic per title) ─────────────────────────────────
PALETTE = [
    "#7A2E2E","#234E70","#3C6E47","#5B4B8A","#8A5A2B",
    "#2F4858","#86402E","#3E5641","#5E3A5C","#1F3A5F",
    "#704214","#2C5F5D","#6B2737","#324E3C","#46327E",
]

# ── Page counts from Goodreads / knowledge base ──────────────────────────────
PAGES = {
    "Foundation": 255,
    "The Meaning of Life: Perspectives from the World's Great Intellectual Traditions": 480,
    "The Great Ideas of Philosophy, 2nd Edition": 900,
    "Great Ancient Civilizations of Asia Minor": 480,
    "Reinforcement Learning": 150,
    "The Other Side of History: Daily Life in the Ancient World": 720,
    "Tress of the Emerald Sea: A Cosmere Novel": 461,
    "Yumi and the Nightmare Painter: A Cosmere Novel": 478,
    "21 Lessons for the 21st Century": 372,
    "Throne of Glass: Throne of Glass, Book 1": 404,
    "The Lost Metal: A Mistborn Novel": 873,
    "The Bands of Mourning": 448,
    "Shadows of Self": 383,
    "Heated Rivalry": 384,
    "The Alloy of Law: A Mistborn Novel": 332,
    "Wind and Truth: Book Five of the Stormlight Archive": 1327,
    "Rhythm of War: Book Four of the Stormlight Archive": 1232,
    "Dawnshard: Stormlight Archive": 172,
    "Edgedancer: Stormlight Archive": 226,
    "Oathbringer": 1220,
    "Words of Radiance: The Stormlight Archive, Book 2": 1087,
    "Elantris: Tenth Anniversary Special Edition": 496,
    "The Sunlit Man: A Cosmere Novel": 384,
    "The Shining": 447,
    "Warbreaker": 592,
    "Algospeak: How Social Media Is Transforming the Future of Language": 176,
    "Quicksilver: The Fae & Alchemy Series, Book 1": 464,
    "Mythos": 352,
    "Odyssey: The Greek Myths Reimagined": 352,
    "Nexus: A Brief History of Information Networks from the Stone Age to AI": 448,
    "The Data Detective: Ten Easy Rules to Make Sense of Statistics": 336,
    "The Wind Through the Keyhole: The Dark Tower": 309,
    "The Way of Kings: The Stormlight Archive, Book 1": 1007,
    "The Demon-Haunted World: Science as a Candle in the Dark": 457,
    "The Hero of Ages: Mistborn, Book 3": 748,
    "The Well of Ascension: Mistborn, Book 2": 781,
    "Love Triangle: How Trigonometry Shapes the World": 342,
    "The Dark Tower: The Dark Tower VII": 1072,
    "Song of Susannah: The Dark Tower VI": 432,
    "'Salem's Lot": 439,
    "Wolves of the Calla: Dark Tower V": 931,
    "Dark Tower IV: Wizard and Glass": 787,
    "Dark Tower III: The Waste Lands": 512,
    "Dark Tower II: The Drawing of the Three": 400,
    "Dark Tower I: The Gunslinger": 231,
    "Shape: The Hidden Geometry of Information, Biology, Strategy, Democracy, and Everything Else": 480,
    "The Return of the King: Lord of the Rings, Book 3": 416,
    "The Two Towers: Lord of the Rings, Book 2": 352,
    "The Two Towers: Book Two in the Lord of the Rings Trilogy": 352,
    "The Fellowship of the Ring: Lord of the Rings, Book 1": 423,
    "It": 1138,
    "Dopamine Nation: Finding Balance in the Age of Indulgence": 304,
    "The Girl with the Dragon Tattoo: A Lisbeth Salander Novel": 590,
    "Under the Dome: A Novel": 1074,
    "The Stand": 1153,
    "Fairy Tale": 608,
    "Lazarus: A novel": 416,
    "The History of Ancient Egypt": 720,
    "The Source of Self-Regard: Selected Essays, Speeches, and Meditations": 353,
    "Freakonomics: Revised Edition": 336,
    "The History of Ancient Rome": 600,
    "The Gene: An Intimate History": 592,
    "Unf*ck Your Brain: Using Science to Get over Anxiety, Depression, Anger, Freak-Outs, and Triggers": 224,
    "Dune Messiah: Book Two in the Dune Chronicles": 226,
    "The Song of the Cell: An Exploration of Medicine and the New Human": 464,
    "The Anthropocene Reviewed: Essays on a Human-Centered Planet": 304,
    "Troy: The Greek Myths Reimagined": 432,
    "I'm Glad My Mom Died": 320,
    "The Redemption of Time: A Three-Body Problem Novel": 384,
    "Ruination: A League of Legends Novel": 336,
    "Uninformed: Why People Know So Little About Politics and What We Can Do about It": 224,
    "Where the Crawdads Sing: Reese's Book Club": 384,
    "Heroes: The Greek Myths Reimagined": 448,
    "Guns, Germs and Steel: The Fate of Human Societies": 480,
    "Salt, Fat, Acid, Heat: Mastering the Elements of Good Cooking": 480,
    "The Membership Economy: Find Your Super Users, Master the Forever Transaction, and Build Recurring Revenue": 240,
    "The Great Experiment: Why Diverse Democracies Fall Apart and How They Can Endure": 352,
    "Option Volatility and Pricing: Advanced Trading Strategies and Techniques": 472,
    "Influence Is Your Superpower: The Science of Winning Hearts, Sparking Change, and Making Good Things Happen": 320,
    "The Voltage Effect: How to Make Good Ideas Great and Great Ideas Scale": 288,
    "The Left Hand of Darkness": 286,
    "Algorithms to Live By: The Computer Science of Human Decisions": 368,
    "The Chapo Guide to Revolution: A Manifesto Against Logic, Facts, and Reason": 288,
    "Our Revolution: A Future to Believe In": 464,
    "Forward: Notes on the Future of Our Democracy": 320,
    "Good Strategy/Bad Strategy: The Difference and Why It Matters": 336,
    "Project Hail Mary": 476,
    "Games People Play: The Basic Handbook of Transactional Analysis": 192,
    "The Infinite Game": 272,
    "Start with Why: How Great Leaders Inspire Everyone to Take Action": 256,
    "What the Dog Saw: And Other Adventures": 432,
    "The Bomber Mafia: A Dream, a Temptation, and the Longest Night of the Second World War": 256,
    "The Intelligent Investor Rev Ed.": 640,
    "Atomic Habits: An Easy & Proven Way to Build Good Habits & Break Bad Ones": 320,
    "David and Goliath: Underdogs, Misfits, and the Art of Battling Giants": 320,
    "How Not to Be Wrong: The Power of Mathematical Thinking": 480,
    "Heart of Darkness: A Signature Performance by Kenneth Branagh": 112,
    "Manufacturing Consent: The Political Economy of the Mass Media": 412,
    "Outliers: The Story of Success": 309,
    "Talking to Strangers: What We Should Know about the People We Don't Know": 400,
    "The Inner Game of Tennis: The Classic Guide to the Mental Side of Peak Performance": 196,
    "Death's End": 604,
    "Dune": 412,
    "The Martian": 369,
    "11-22-63: A Novel": 849,
    "Letters to a Young Scientist": 244,
    "The Dark Forest": 400,
    "The Three-Body Problem": 400,
    "Recursion: A Novel": 336,
    "Blink: The Power of Thinking Without Thinking": 296,
}

# ── Helpers ──────────────────────────────────────────────────────────────────
def spine_width_mm(pages):
    for cap, w in SPINE_BINS:
        if pages <= cap:
            return w
    return SPINE_BINS[-1][1]

def color_for(title):
    h = int(hashlib.md5(title.encode()).hexdigest(), 16)
    return PALETTE[h % len(PALETTE)]

def hex_to_rgb(hx):
    hx = hx.lstrip("#")
    return tuple(int(hx[i:i+2], 16)/255 for i in (0, 2, 4))

def luminance(hx):
    r, g, b = hex_to_rgb(hx)
    return 0.299*r + 0.587*g + 0.114*b

def text_color(bg):
    return (1,1,1) if luminance(bg) < 0.6 else (0.1,0.1,0.1)

def wrap_text(text, font, size, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if stringWidth(trial, font, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines

def page_count_for(title):
    for k, v in PAGES.items():
        if k.lower() == title.lower(): return v
    for k, v in PAGES.items():
        if k.lower() in title.lower() or title.lower() in k.lower(): return v
    return 350  # default

# ── Image download ────────────────────────────────────────────────────────────
def download_cover(url, cache_dir):
    """Download cover image, caching locally. Returns PIL Image or None."""
    if not url:
        return None
    # Strip all existing Amazon size modifiers then request 1500px
    url = re.sub(r'(\._[A-Za-z0-9_]+_)+(?=\.jpg)', '', url, flags=re.IGNORECASE)
    url = re.sub(r'\.jpg', '._SL1500_.jpg', url, count=1, flags=re.IGNORECASE)
    filename = re.sub(r'[^a-zA-Z0-9_\-.]', '_', url.split('/')[-1])
    path = os.path.join(cache_dir, filename)
    if os.path.exists(path):
        try:
            return Image.open(path).convert("RGB")
        except:
            pass
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 Chrome/120 Safari/537.36",
            "Referer": "https://www.audible.com/"
        }
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGB")
        img.save(path, quality=95)
        return img
    except Exception as e:
        print(f"  Warning: Could not download {url}: {e}")
        return None

def trim_whitespace(img, threshold=245):
    """Crop near-white borders from image edges."""
    gray = img.convert('L')
    bbox = gray.point(lambda p: 0 if p > threshold else 255).getbbox()
    if not bbox:
        return img
    w, h = img.size
    margin = max(2, int(min(w, h) * 0.005))
    return img.crop((max(0, bbox[0]-margin), max(0, bbox[1]-margin),
                     min(w, bbox[2]+margin), min(h, bbox[3]+margin)))

def scale_with_bars(img, target_w_pts, target_h_pts, bg_color=(0, 0, 0)):
    """Scale image to fit target PDF dimensions at print resolution, padding with bg_color."""
    px_per_pt = PRINT_DPI / 72.0
    tw = max(1, int(target_w_pts * px_per_pt))
    th = max(1, int(target_h_pts * px_per_pt))
    iw, ih = img.size
    scale = min(tw / iw, th / ih)
    new_w, new_h = max(1, int(iw * scale)), max(1, int(ih * scale))
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    result = Image.new("RGB", (tw, th), bg_color)
    result.paste(resized, ((tw - new_w) // 2, (th - new_h) // 2))
    return result

# ── Panel drawing ─────────────────────────────────────────────────────────────
def draw_generated_cover(c, x, y, w, h, title, author):
    bg = color_for(title)
    r, g, b = hex_to_rgb(bg)
    c.setFillColorRGB(r, g, b)
    c.rect(x, y, w, h, fill=1, stroke=0)
    tc = text_color(bg)
    c.setFillColorRGB(*tc)
    c.setStrokeColorRGB(*tc); c.setLineWidth(0.4)
    c.rect(x+1.2*F*mm, y+1.2*F*mm, w-2.4*F*mm, h-2.4*F*mm, fill=0, stroke=1)
    size, inner = 6.2*F, w - 4*F*mm
    lines = wrap_text(title, "Helvetica-Bold", size, inner)
    while len(lines) > 4 and size > 4*F:
        size -= 0.4*F
        lines = wrap_text(title, "Helvetica-Bold", size, inner)
    c.setFont("Helvetica-Bold", size)
    ty = y + h - 5*F*mm
    for ln in lines:
        c.drawCentredString(x + w/2, ty, ln); ty -= (size + 1.2*F)
    asize = 4.6*F
    c.setFont("Helvetica-Oblique", asize)
    for ln in wrap_text(author, "Helvetica-Oblique", asize, inner):
        c.drawCentredString(x + w/2, y + 3.2*F*mm, ln)

def draw_front(c, x, y, w, h, title, author, pil_img):
    if pil_img is not None:
        try:
            bg_rgb = tuple(int(v * 255) for v in hex_to_rgb(color_for(title)))
            scaled = scale_with_bars(trim_whitespace(pil_img), w, h, bg_rgb)
            c.drawImage(ImageReader(scaled), x, y, w, h, mask=None)
            return
        except Exception:
            pass
    draw_generated_cover(c, x, y, w, h, title, author)

def draw_spine(c, x, y, w, h, title):
    bg = color_for(title)
    r, g, b = hex_to_rgb(bg)
    c.setFillColorRGB(r*0.82, g*0.82, b*0.82)
    c.rect(x, y, w, h, fill=1, stroke=0)
    tc = text_color(bg)
    c.setFillColorRGB(*tc)
    size, label, maxlen = 5.0*F, title, h - 3*F*mm
    while stringWidth(label, "Helvetica-Bold", size) > maxlen and size > 3*F:
        size -= 0.3*F
    if stringWidth(label, "Helvetica-Bold", size) > maxlen:
        while stringWidth(label + "…", "Helvetica-Bold", size) > maxlen and len(label) > 1:
            label = label[:-1]
        label += "…"
    c.saveState()
    c.translate(x + w/2, y + h/2); c.rotate(-90)
    c.setFont("Helvetica-Bold", size)
    c.drawCentredString(0, -size*0.35, label)
    c.restoreState()

def draw_back(c, x, y, w, h, title, author, pages):
    bg = color_for(title)
    r, g, b = hex_to_rgb(bg)
    c.setFillColorRGB(r, g, b)
    c.rect(x, y, w, h, fill=1, stroke=0)
    tc = text_color(bg)
    c.setFillColorRGB(*tc)
    c.setStrokeColorRGB(*tc); c.setLineWidth(0.4)
    c.rect(x+1.2*F*mm, y+1.2*F*mm, w-2.4*F*mm, h-2.4*F*mm, fill=0, stroke=1)
    c.setFont("Helvetica-Oblique", 4.6*F)
    font_size = 4.6*F
    line_h = font_size * 1.2
    lines = wrap_text(author, "Helvetica-Oblique", font_size, w-4*F*mm)
    start_y = y + h/2 + (len(lines) - 1) * line_h / 2
    for i, ln in enumerate(lines):
        c.drawCentredString(x + w/2, start_y - i * line_h, ln)

def draw_wrap(c, x, y, book):
    title  = book["title"]
    author = book["author"]
    pages  = book["pages"]
    img    = book.get("pil_img")
    spine  = spine_width_mm(pages) * mm
    cw, h  = COVER_WIDTH*mm, BOOK_HEIGHT*mm
    total  = 2*cw + spine
    draw_back(c, x, y, cw, h, title, author, pages)
    draw_spine(c, x+cw, y, spine, h, title)
    draw_front(c, x+cw+spine, y, cw, h, title, author, img)
    # fold lines
    c.setStrokeColorRGB(1,1,1); c.setLineWidth(0.5); c.setDash(2*F, 2*F)
    for fx in (x+cw, x+cw+spine):
        c.line(fx, y, fx, y+h)
    c.setDash()
    # cut border + corner ticks
    c.setStrokeColorRGB(0.45,0.45,0.45); c.setLineWidth(0.4)
    c.rect(x, y, total, h, fill=0, stroke=1)
    tick = 2.2*F*mm
    c.setStrokeColorRGB(0.2,0.2,0.2); c.setLineWidth(0.5)
    for cx2, cy2 in [(x,y),(x+total,y),(x,y+h),(x+total,y+h)]:
        sx = -1 if cx2>x else 1; sy = -1 if cy2>y else 1
        c.line(cx2, cy2, cx2+sx*tick, cy2)
        c.line(cx2, cy2, cx2, cy2+sy*tick)
    return total

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv",  help="Path to ALE-spreadsheet-library.csv")
    ap.add_argument("out",  help="Output PDF path, e.g. covers.pdf")
    ap.add_argument("--page", default="letter", choices=["letter","a4"])
    ap.add_argument("--cache", default="./covers_cache",
                    help="Folder to cache downloaded cover images (default: ./covers_cache)")
    args = ap.parse_args()

    os.makedirs(args.cache, exist_ok=True)
    pagesize = letter if args.page == "letter" else A4
    pw, ph   = pagesize

    print("Reading library...")
    df = pd.read_csv(args.csv)
    books = []
    for _, row in df.iterrows():
        title  = row["Title"]
        author = str(row.get("Authors","")).split(",")[0].strip()
        pages  = page_count_for(title)
        url    = row.get("Cover","")
        books.append({"title": title, "author": author, "pages": pages, "cover_url": url})

    print(f"Downloading {len(books)} cover images (cached in {args.cache}/)")
    for i, b in enumerate(books):
        print(f"  [{i+1}/{len(books)}] {b['title'][:55]}", end="", flush=True)
        b["pil_img"] = download_cover(b["cover_url"], args.cache)
        print(" ok" if b["pil_img"] else " (generated)")

    print(f"\nBuilding PDF -> {args.out}")
    c = canvas.Canvas(args.out, pagesize=pagesize)
    m, gap, h = MARGIN*mm, GAP*mm, BOOK_HEIGHT*mm

    def header():
        c.setFillColorRGB(0.2,0.2,0.2); c.setFont("Helvetica-Bold", 11)
        c.drawString(m, ph-m+4, "Mini-book wrap covers — real covers edition")
        c.setFont("Helvetica", 7.5); c.setFillColorRGB(0.45,0.45,0.45)
        c.drawString(m, ph-m-8,
            "Print at 100% / Actual size (no scaling). Solid grey = cut. Dashed = fold around spine.")

    header()
    cell_w = h   # rotated 90deg: 60mm book height becomes the cell width
    x, top, row_max = m, ph - m - 20, 0.0
    for bk in books:
        spine = spine_width_mm(bk["pages"]) * mm
        total = 2*COVER_WIDTH*mm + spine          # wrap length -> rotated cell height
        if x + cell_w > pw - m:
            top -= (row_max + gap); x = m; row_max = 0.0
        if top - total < m:
            c.showPage(); header(); x = m; top = ph - m - 20; row_max = 0.0
        c.saveState()
        c.translate(x + cell_w, top - total)
        c.rotate(90)
        draw_wrap(c, 0, 0, bk)
        c.restoreState()
        row_max = max(row_max, total); x += cell_w + gap
    c.showPage(); c.save()
    print(f"Done! Open {args.out} and print at 100% with no page scaling.")

if __name__ == "__main__":
    main()
