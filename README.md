# AudioBlocks — Mini Audiobook Cover Generator

Generate print-ready wrap covers for 3D-printed miniature audiobook props, using your real Audible cover art.

Each wrap is a single strip — **back cover | spine | front cover** — sized to fold around one of the four STL mini-book models. Print, cut, fold, and glue.

---

## What you need

| Item | Where to get it |
|------|----------------|
| Python 3.8+ | [python.org](https://www.python.org/downloads/) |
| Python packages | `pip install -r requirements.txt` |
| Audible Library CSV | Instructions below |
| 3D-printed mini books | [AudioBlocks on MakerWorld](https://makerworld.com/en/models/2908214-audioblocks) |

---

## Getting your Audible Library CSV

1. Install the free **Audible Library Exporter (ALE)** browser extension
   - [Chrome Web Store](https://chrome.google.com/webstore) — search *Audible Library Exporter*
   - [Firefox Add-ons](https://addons.mozilla.org) — search *Audible Library Exporter*

2. Go to **audible.com/library/titles** and log in.

3. Click the ALE extension icon → **Export to CSV** → save the file.

---

## Install & run

```bash
# 1 — Install dependencies (one time)
pip install -r requirements.txt

# 2 — Run the script
python audiobook_covers.py
```

The script will walk you through everything interactively:
- Paste/drag in the path to your CSV
- Choose Letter or A4 paper

Output is saved automatically to **~/Desktop/AudioBlocks/audiobook_covers.pdf**.

---

## Printing

- Open the PDF in Adobe Acrobat, Preview, or your browser's PDF viewer.
- Set scale to **Actual Size / 100%** — do NOT use "fit to page."
- **Solid grey line** = cut here.
- **Dashed white line** = fold here (spine edges).
- Wrap around the 3D-printed book and glue or tape in place.

**Pro tip:** After cutting, apply a [Scotch self-sealing laminating pouch](https://www.amazon.com/Scotch-Self-Sealing-Laminating-Pouches-LS854-10G/dp/B00004TS60) to the outside of the printed paper before wrapping. It adds a thin adhesive plastic layer that closely matches the finish of a real hardcover book.

---

## STL files

Four spine widths are available on MakerWorld to match any audiobook length:

| Model | Spine | Best for |
|-------|-------|----------|
| `book_thin` | 4 mm | ≤ 250 pages |
| `book_medium` | 6 mm | 251–400 pages |
| `book_thick` | 8.5 mm | 401–550 pages |
| `book_chonky` | 11 mm | 551+ pages |

Download them at [makerworld.com/en/models/2908214-audioblocks](https://makerworld.com/en/models/2908214-audioblocks).

---

## How covers are chosen

The script downloads your actual Audible cover art directly from Amazon at high resolution and caches it in `~/Desktop/AudioBlocks/covers_cache/`. Books without a cover URL in the CSV get a colour-coded generated cover instead.

Page counts are used to pick the right spine width. The script has a built-in lookup table for common titles; unknown titles default to 350 pages (medium spine).

---

## Credits

Built with assistance from [Claude](https://claude.ai) by [Anthropic](https://anthropic.com).
