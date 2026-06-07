"""
AMC 10 Diagram Extractor
Renders diagram regions from AMC problems PDFs into PNG files.

Strategy:
  For each problem on each page, we look for vector drawings in two regions:
    - BEFORE answer choices  (between problem text and (A)–(E))
    - AFTER  answer choices  (between (E) choice and start of next problem)
  Whichever region has the most drawing content is used.
  Problems in topics that often have diagrams are processed regardless of
  the has_image keyword flag.  The JSON files are updated in place.

Usage:
  python extract_images.py [--pdf-dir PATH] [--parsed-dir PATH] [--out-dir PATH]
                           [--year YEAR] [--topics TOPIC,TOPIC]
"""

import fitz
import json
import re
import os
import argparse
import glob
from pathlib import Path

# Topics where we always attempt diagram extraction even without has_image keyword
DIAGRAM_TOPICS = {"Geometry", "Combinatorics", "Other"}

# ── Filename → year ───────────────────────────────────────────────────────────
_PROBLEMS_RE = [
    re.compile(r'^AMC 10 (\d{4}) Problems\.pdf$', re.IGNORECASE),
    re.compile(r'^(\d{4}) AMC 10([AB]?) Problems.*\.pdf$', re.IGNORECASE),
]

def _year_from_filename(fname):
    for pat in _PROBLEMS_RE:
        m = pat.match(os.path.basename(fname))
        if m:
            return int(m.group(1))
    return None


# ── Block helpers ─────────────────────────────────────────────────────────────
def _first_token(block):
    return block[4].strip().split("\n")[0].strip()


def _alpha_words(text, skip_lines=0):
    """Return a list of lowercase alpha-only tokens, skipping the first N lines."""
    lines = text.strip().split("\n")
    body = "\n".join(lines[skip_lines:])
    return re.findall(r"[a-zA-Z]+", body.lower())


def _text_matches_problem(block_text, problem_text, n=5, threshold=3):
    """
    Confirm a PDF block belongs to the given parsed problem by comparing
    the first N alphabetic words (excluding the problem-number line).
    Returns True when at least `threshold` of the first N words match,
    or when the texts are too short to compare confidently.
    """
    pdf_words  = _alpha_words(block_text, skip_lines=1)[:n]
    prob_words = _alpha_words(problem_text)[:n]
    if not pdf_words or not prob_words:
        return True  # can't compare, allow through
    matches = sum(a == b for a, b in zip(pdf_words, prob_words))
    return matches >= min(threshold, len(pdf_words))


def _is_problem_start(block, num):
    """True if this block is the start of problem `num`."""
    text = block[4].strip()
    if text == str(num):
        return True
    if text.startswith(str(num) + "\n"):
        # Reject if block immediately contains answer choices — it's a diagram
        # label or answer value, not a problem header.
        rest = text[len(str(num)):].strip()
        if any(f"({c})" in rest for c in "ABCDE"):
            return False
        return True
    return False


def _drawing_count_in_band(page, y0, y1):
    """Count drawing path segments whose bounding box overlaps (y0, y1)."""
    count = 0
    for d in page.get_drawings():
        r = d.get("rect")
        if r and r.y1 > y0 and r.y0 < y1:
            count += 1
    return count


# ── Find problem regions on a page ────────────────────────────────────────────
def find_problem_region(page, q_num):
    """
    Return a dict with:
      start        – y of problem-number block top
      text_bottom  – y of problem-text block bottom
      before_top   – top of pre-answer diagram zone (= text_bottom)
      choices_top  – y where (A)-(E) block starts
      choices_bottom – y where (A)-(E) block ends
      after_bottom – y where next problem starts (or page bottom)
    Returns None if problem not found on this page.
    """
    blocks = page.get_text("blocks")

    # ── 1. Find problem start block ──
    start_idx = None
    for i, b in enumerate(blocks):
        if _is_problem_start(b, q_num):
            start_idx = i
            break
    if start_idx is None:
        return None

    prob_block = blocks[start_idx]
    prob_y0 = prob_block[1]   # top of problem block
    text_y1 = prob_block[3]   # bottom of problem-text block

    # ── 2. Scan forward to find answer choices and next problem ──
    choices_top    = None
    choices_bottom = None
    after_bottom   = page.rect.height - 30   # default: near page bottom

    CHOICE_RE = re.compile(r'^\s*\([ABCDE]\)')

    for b in blocks[start_idx + 1:]:
        text = b[4]
        y0, y1 = b[1], b[3]

        # Combined block: contains both "(A)" and "(E)"
        if choices_top is None and "(A)" in text and "(E)" in text:
            choices_top    = y0
            choices_bottom = y1
            continue

        # Individual choice line starting with (A)
        if choices_top is None and text.strip().startswith("(A)"):
            choices_top    = y0
            choices_bottom = y1
            continue

        # Subsequent individual choice lines (B)-(E) — extend choices_bottom
        if choices_top is not None and CHOICE_RE.match(text):
            choices_bottom = y1   # keep updating to the last choice line
            continue

        # Start of the NEXT problem → our after_bottom
        tok = _first_token(b)
        if tok.isdigit():
            n = int(tok)
            if 1 <= n <= 25 and n != q_num and len(text) > 15:
                after_bottom = y0
                break

    # If no choices found at all, treat entire post-text zone as "after"
    if choices_top is None:
        choices_top    = text_y1
        choices_bottom = text_y1

    if choices_bottom is None:
        choices_bottom = choices_top + 12

    return {
        "start":          prob_y0,
        "text_bottom":    text_y1,
        "choices_top":    choices_top,
        "choices_bottom": choices_bottom,
        "after_bottom":   after_bottom,
    }


def best_diagram_region(page, region):
    """
    Return (y0, y1) for the best diagram crop, or None if no drawings found.
    Checks both before-choices and after-choices regions.
    """
    PAD = 8   # pts below text bottom before crop starts

    before_y0 = region["text_bottom"] + PAD
    before_y1 = region["choices_top"]
    after_y0  = region["choices_bottom"] + PAD
    after_y1  = region["after_bottom"] - 10

    before_h   = before_y1 - before_y0
    after_h    = after_y1  - after_y0
    before_drw = _drawing_count_in_band(page, before_y0, before_y1) if before_h > 20 else 0
    after_drw  = _drawing_count_in_band(page, after_y0,  after_y1)  if after_h  > 20 else 0

    MIN_DRAWINGS = 2
    MIN_HEIGHT   = 20   # pts

    has_before = before_drw >= MIN_DRAWINGS and before_h >= MIN_HEIGHT
    has_after  = after_drw  >= MIN_DRAWINGS and after_h  >= MIN_HEIGHT

    if not has_before and not has_after:
        return None

    if has_before and has_after:
        # prefer the taller / richer one
        return (before_y0, before_y1) if before_h >= after_h else (after_y0, after_y1)
    if has_before:
        return (before_y0, before_y1)
    return (after_y0, after_y1)


# ── Cross-page diagram detection ─────────────────────────────────────────────
def find_diagram_next_page(doc, page_num):
    """
    If a problem's text ended near the bottom of page_num, its diagram and
    answer choices may start at the top of the next page.  Return
    (next_page, y0, y1) if a diagram region is found there, else None.
    """
    if page_num + 1 >= len(doc):
        return None

    next_page = doc[page_num + 1]
    blocks = next_page.get_text("blocks")
    CHOICE_RE = re.compile(r"^\s*\([ABCDE]\)")
    HEADER_SKIP = 120  # pts — skip page header band

    choices_y = None
    for b in blocks:
        if b[1] < HEADER_SKIP:
            continue
        text = b[4]
        if ("(A)" in text and "(E)" in text) or text.strip().startswith("(A)") or CHOICE_RE.match(text):
            choices_y = b[1]
            break

    if choices_y is None:
        return None

    y0 = HEADER_SKIP
    y1 = choices_y - 4

    if y1 - y0 < 20:
        return None

    drw = _drawing_count_in_band(next_page, y0, y1)
    if drw < 1:
        return None

    return (next_page, y0, y1)


# ── Render ────────────────────────────────────────────────────────────────────
def render_crop(page, y0, y1, scale=2.5):
    clip = fitz.Rect(0, max(0, y0), page.rect.width, min(page.rect.height, y1))
    pix  = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, colorspace=fitz.csRGB)
    return pix


# ── Per-PDF processing ────────────────────────────────────────────────────────
def process_pdf(pdf_path, year, parsed_dir, out_dir, topics_filter, scale=2.5):
    doc = fitz.open(pdf_path)
    os.makedirs(out_dir, exist_ok=True)

    # Load all parsed JSON for this year
    json_files = glob.glob(os.path.join(parsed_dir, f"{year}_*.json"))
    if not json_files:
        doc.close()
        return 0

    # Build index: (exam, q_num) → problem dict (we'll mutate it)
    all_problems = {}   # (exam, q_num) → problem dict
    json_data    = {}   # filename → list of problem dicts

    for jf in json_files:
        with open(jf, encoding="utf-8") as f:
            data = json.load(f)
        json_data[jf] = data
        for p in data:
            key = (p["exam"], p["question_number"])
            all_problems[key] = p

    # Filter to problems we care about
    def should_process(p):
        if p.get("has_image"):
            return True
        topic = p.get("topic") or ""
        return topic in topics_filter

    targets = {k: p for k, p in all_problems.items() if should_process(p)}
    if not targets:
        doc.close()
        return 0

    matched_ids  = set()
    extracted    = 0

    for page_num in range(len(doc)):
        page   = doc[page_num]
        blocks = page.get_text("blocks")

        # Collect candidate problem numbers and their start-block text on this page
        # (first occurrence of each number wins, preserving top-to-bottom order)
        q_num_text: dict[int, str] = {}
        for b in blocks:
            tok = _first_token(b)
            if tok.isdigit():
                n = int(tok)
                if 1 <= n <= 25 and n not in q_num_text:
                    if _is_problem_start(b, n):
                        q_num_text[n] = b[4]

        for q_num in sorted(q_num_text):
            block_text = q_num_text[q_num]
            # Try each exam variant
            for exam_key in ["AMC10A", "AMC10B", "AMC10"]:
                prob = targets.get((exam_key, q_num))
                if prob is None or prob["id"] in matched_ids:
                    continue

                # Confirm the block on this page matches the target problem text.
                # This guards against bundled A/B PDFs where Q_num appears twice
                # (once in the A section, once in the B section).
                if not _text_matches_problem(block_text, prob["problem_text"]):
                    continue

                pid      = prob["id"]
                out_path = os.path.join(out_dir, f"{pid}.png")

                region = find_problem_region(page, q_num)
                if region is None:
                    continue

                crop = best_diagram_region(page, region)
                render_page = page
                used_page_num = page_num

                # Cross-page fallback: problem text ends near page bottom with
                # no diagram found — check the top of the next page.
                if crop is None and region["text_bottom"] > page.rect.height * 0.6:
                    result = find_diagram_next_page(doc, page_num)
                    if result is not None:
                        render_page, y0, y1 = result
                        crop = (y0, y1)
                        used_page_num = page_num + 1

                if crop is None:
                    continue   # no diagram found here for this problem

                y0, y1 = crop
                if y1 - y0 < 15:
                    continue

                pix = render_crop(render_page, y0, y1, scale)
                pix.save(out_path)
                matched_ids.add(pid)
                extracted += 1

                # Update has_image in the problem dict if it wasn't already set
                prob["has_image"] = True

                print(f"  Saved {os.path.basename(out_path)}"
                      f"  ({pix.width}x{pix.height}px, page {used_page_num+1},"
                      f" y={y0:.0f}-{y1:.0f})")
                break   # found a match for this q_num, move on

    doc.close()

    # Persist updated JSON (has_image flags may have changed)
    for jf, data in json_data.items():
        with open(jf, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    return extracted


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Extract AMC 10 diagram images")
    parser.add_argument("--pdf-dir",    default=None)
    parser.add_argument("--parsed-dir", default=None)
    parser.add_argument("--out-dir",    default=None)
    parser.add_argument("--year",       type=int, default=None)
    parser.add_argument("--topics",     default="Geometry,Combinatorics,Other",
                        help="Comma-separated topics to scan even without has_image")
    parser.add_argument("--scale",      type=float, default=2.5)
    args = parser.parse_args()

    script_dir   = Path(__file__).parent
    pdf_dir      = args.pdf_dir    or str(script_dir.parent.parent)
    parsed_dir   = args.parsed_dir or str(script_dir.parent / "data" / "parsed")
    out_dir      = args.out_dir    or str(script_dir.parent / "frontend" / "public" / "images")
    os.makedirs(out_dir, exist_ok=True)

    topics_filter = set(args.topics.split(","))

    print(f"PDF dir   : {pdf_dir}")
    print(f"Parsed dir: {parsed_dir}")
    print(f"Image out : {out_dir}")
    print(f"Topics    : {topics_filter}")
    print(f"Scale     : {args.scale}x")
    print()

    grand_total = 0
    for fname in sorted(os.listdir(pdf_dir)):
        if not fname.lower().endswith(".pdf"):
            continue
        year = _year_from_filename(fname)
        if year is None:
            continue
        if args.year and year != args.year:
            continue

        pdf_path = os.path.join(pdf_dir, fname)
        print(f"Processing {year}  ({fname}) ...")
        n = process_pdf(pdf_path, year, parsed_dir, out_dir, topics_filter, args.scale)
        if n:
            print(f"  -> {n} images extracted")

    total_pngs = len(glob.glob(os.path.join(out_dir, "*.png")))
    print(f"\nDone. {total_pngs} PNG files in {out_dir}")


if __name__ == "__main__":
    main()
