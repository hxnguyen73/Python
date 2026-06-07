"""
AMC 10 PDF Parser
Extracts problems and solutions from AMC 10 PDF collections into structured JSON.

Usage:
  python parse_amc.py [--pdf-dir PATH] [--out-dir PATH] [--year YEAR] [--exam EXAM]

By default, looks for PDFs in the directory two levels above this script
(the project root containing all the AMC PDFs).
"""

import fitz  # PyMuPDF
import json
import re
import os
import sys
import argparse
from pathlib import Path

# ── Single-exam years (no A/B split) ─────────────────────────────────────────
SINGLE_EXAM_YEARS = {2000, 2001}

# ── Filename patterns → (year, exam_variant, pdf_type) ───────────────────────
PROBLEMS_PATTERNS = [
    # "AMC 10 2023 Problems.pdf"
    (re.compile(r'^AMC 10 (\d{4}) Problems\.pdf$', re.IGNORECASE), lambda m: (int(m.group(1)), None)),
    # "2025 AMC 10A Problems - AoPS Wiki.pdf"
    (re.compile(r'^(\d{4}) AMC 10([AB]?) Problems', re.IGNORECASE), lambda m: (int(m.group(1)), m.group(2).upper() or None)),
]

SOLUTIONS_PATTERNS = [
    # "2000AMC10-solutions.pdf"
    (re.compile(r'^(\d{4})AMC10-solutions\.pdf$', re.IGNORECASE), lambda m: (int(m.group(1)), '')),
    # "2002AMC10-Asolutions.pdf", "2008-AMC10-Asolutions.pdf"
    (re.compile(r'^(\d{4})-?AMC10-([AB])solutions\.pdf$', re.IGNORECASE), lambda m: (int(m.group(1)), m.group(2).upper())),
    # "2011 AMC10-A solutions.pdf"
    (re.compile(r'^(\d{4}) AMC10-([AB]) solutions\.pdf$', re.IGNORECASE), lambda m: (int(m.group(1)), m.group(2).upper())),
    # "2012 AMC10A Solutions.pdf"
    (re.compile(r'^(\d{4}) AMC10([AB]) Solutions\.pdf$', re.IGNORECASE), lambda m: (int(m.group(1)), m.group(2).upper())),
    # "2013AMC10A_FinalS.pdf"
    (re.compile(r'^(\d{4})AMC10([AB])_FinalS\.pdf$', re.IGNORECASE), lambda m: (int(m.group(1)), m.group(2).upper())),
    # "2014_10A_Solutions.pdf", "2014_10B_Final_S.pdf"
    (re.compile(r'^(\d{4})_10([AB])(?:_Final)?_S(?:olutions)?\.pdf$', re.IGNORECASE), lambda m: (int(m.group(1)), m.group(2).upper())),
    # "2015AMC1012_10_B_Solutions.pdf"
    (re.compile(r'^(\d{4})AMC1012_10_([AB])_Solutions\.pdf$', re.IGNORECASE), lambda m: (int(m.group(1)), m.group(2).upper())),
    # "2015_AMC10A_Solutions.pdf", "2016_AMC10A_Solutions.pdf"
    (re.compile(r'^(\d{4})_AMC10([AB])_Solutions\.pdf$', re.IGNORECASE), lambda m: (int(m.group(1)), m.group(2).upper())),
    # "2017_AMC10A_Solutions.pdf"  (same as above, already handled)
    # "AMC 10A Solutions 2019.pdf", "AMC 10A Solutions 2021 Fall.pdf", "AMC 10A Solutions 2022.pdf"
    (re.compile(r'^AMC 10([AB]) Solutions (\d{4})(?:\s+Fall)?\.pdf$', re.IGNORECASE), lambda m: (int(m.group(2)), m.group(1).upper())),
]


def classify_pdf(filename: str) -> dict | None:
    """Return {year, variant, type} for a PDF filename, or None if unrecognized."""
    name = os.path.basename(filename)

    for pattern, extractor in PROBLEMS_PATTERNS:
        m = pattern.match(name)
        if m:
            year, variant = extractor(m)
            return {"year": year, "variant": variant, "type": "problems", "path": filename}

    for pattern, extractor in SOLUTIONS_PATTERNS:
        m = pattern.match(name)
        if m:
            year, variant = extractor(m)
            return {"year": year, "variant": variant or '', "type": "solutions", "path": filename}

    return None


# ── Text extraction ────────────────────────────────────────────────────────────

# ── Superscript detection constants ──────────────────────────────────────────
_SUPER_SIZE_RATIO  = 0.85  # candidate must be ≤85% the size of the base char
_SUPER_BASELINE_EPS = 2.0  # pts — baseline tolerance for condition 1


def _is_superscript(candidate: dict, base: dict, in_sup_context: bool) -> bool:
    """
    Return True if `candidate` is a superscript character of `base`.

    Condition 1 (size decrease): candidate font ≤85% of base font AND baseline
        not lower than base baseline (with small tolerance).
    Condition 2 (same size, higher): candidate has the same font size as base
        but sits meaningfully higher on the page.  This fires ONLY when already
        inside a superscript context (parent_size was smaller), preventing false
        positives from body-level spaces that happen to share an exponent's y.
    """
    # Spaces/whitespace are never superscripts — they're separators, not math.
    if candidate["c"].isspace():
        return False
    ns, ny = candidate["size"], candidate["oy"]
    bs, by = base["size"], base["oy"]
    cond1 = ns > 0 and ns / bs <= _SUPER_SIZE_RATIO and ny <= by + _SUPER_BASELINE_EPS
    cond2 = in_sup_context and ns == bs and ny < by - _SUPER_BASELINE_EPS
    return cond1 or cond2


def _chars_to_text(chars: list, parent_size: float | None = None) -> str:
    """
    Recursively reconstruct text from per-character dicts {c, size, oy},
    wrapping superscript runs as ^{...}.

    parent_size: font size of the char whose superscript this list represents.
        None at the outermost call.  Used to enable condition-2 detection only
        when already inside a superscript (avoiding false positives in body text).
    """
    if not chars:
        return ""

    result = []
    i = 0
    while i < len(chars):
        ch = chars[i]
        c, size, oy = ch["c"], ch["size"], ch["oy"]

        # True when this character is already inside a superscript expression
        in_sup_ctx = parent_size is not None and size < parent_size

        if size > 0 and i + 1 < len(chars) and (c.isalnum() or c in ')}]'):
            nxt = chars[i + 1]
            if _is_superscript(nxt, ch, in_sup_ctx):
                # Collect all consecutive chars that qualify as superscripts
                # of this specific base character.
                sup = []
                j = i + 1
                while j < len(chars):
                    if _is_superscript(chars[j], ch, in_sup_ctx):
                        sup.append(chars[j])
                        j += 1
                    else:
                        break

                sup_text = _chars_to_text(sup, parent_size=size).strip()
                if sup_text:
                    result.append(c.rstrip())
                    result.append(f"^{{{sup_text}}}")
                    i = j
                    continue

        result.append(c)
        i += 1

    return "".join(result)


def _page_text_with_math(page) -> str:
    """
    Extract text from one page using per-character data (rawdict), so that
    nested superscript towers like 2^{2^{2^2}} are reconstructed correctly.
    Control characters from PDF font encoding are filtered out.
    """
    d = page.get_text("rawdict")
    lines = []
    for block in d.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            chars = []
            for span in line.get("spans", []):
                span_size = span.get("size", 0)
                for ch in span.get("chars", []):
                    c = ch.get("c", "")
                    if c and c.isprintable():
                        chars.append({
                            "c":    c,
                            "size": span_size,
                            "oy":   ch.get("origin", (0, 0))[1],
                        })
            if chars:
                lines.append(_chars_to_text(chars))
    return "\n".join(lines)


def pdf_text(path: str, math: bool = False) -> str:
    """Return full text of a PDF.  math=True uses span-level superscript detection."""
    doc = fitz.open(path)
    if math:
        pages = [_page_text_with_math(page) for page in doc]
    else:
        pages = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages)


def pdf_has_raster_images(path: str) -> bool:
    """Check if any page has embedded images (suggests diagram problems)."""
    doc = fitz.open(path)
    result = any(doc[i].get_images() for i in range(len(doc)))
    doc.close()
    return result


# ── Problems PDF parsing ───────────────────────────────────────────────────────
# Header lines that appear between pages in the AoPS community PDFs
_AOPS_JUNK = re.compile(
    r'AoPS Community\n\d{4} AMC 10\n'
    r'|© \d{4} AoPS Incorporated\n\d+\n'
    r'|Art of Problem Solving is an ACS WASC Accredited School\.\n'
    r'|https?://\S+\s*\n',
    re.MULTILINE,
)

_IMAGE_KEYWORDS = re.compile(
    r'\b(?:shown below|as shown|figure|diagram|graph|see figure|below shows|the figure shows)\b',
    re.IGNORECASE,
)


def parse_problems_pdf(path: str, year: int) -> dict[str, list]:
    """
    Parse an AoPS Community problems PDF.
    Returns {exam_key: [problem_dict]} where exam_key is 'AMC10', 'AMC10A', or 'AMC10B'.
    """
    raw = pdf_text(path, math=True)
    cleaned = _AOPS_JUNK.sub('\n', raw)

    if year in SINGLE_EXAM_YEARS:
        return {"AMC10": _extract_problems_from_block(cleaned)}

    # Dual exam: split at the B section boundary
    text_a, text_b = _split_ab_sections(cleaned)
    result = {}
    if text_a:
        result["AMC10A"] = _extract_problems_from_block(text_a)
    if text_b:
        result["AMC10B"] = _extract_problems_from_block(text_b)
    if not result:
        result["AMC10A"] = _extract_problems_from_block(cleaned)
    return result


def _split_ab_sections(text: str) -> tuple[str, str]:
    """Split combined A+B exam text into two halves."""
    # The B section starts with a header like "– B –" or "B\nNovember"
    # It appears after problem 25 of A is complete
    b_header = re.compile(
        r'(?:\n–\s*\nB\s*\n–|\n–\s*B\s*–\n'
        r'|\nB\s*\nNovember|\nB\s*\nFall)',
        re.IGNORECASE,
    )
    m = b_header.search(text)
    if m:
        return text[:m.start()], text[m.start():]

    # Fallback: find where problem 1 appears a second time (after problem 25)
    pos_25 = None
    for m in re.finditer(r'\n(25)\n', text):
        pos_25 = m.end()
        break

    if pos_25:
        remainder = text[pos_25:]
        m2 = re.search(r'\n1\n', remainder)
        if m2:
            split = pos_25 + m2.start()
            return text[:split], text[split:]

    return text, ""


def _find_choice_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """
    Find (a_line_index, e_line_index) pairs marking complete answer choice blocks.
    A valid block has (A) followed by (B), (C), (D), (E) within 40 lines.
    (A) may appear anywhere in the line (start or mid-line / inline choices).
    """
    blocks = []
    n = len(lines)
    i = 0
    while i < n:
        stripped = lines[i].strip()
        if "(A)" not in stripped:
            i += 1
            continue
        # Verify (B)(C)(D)(E) follow within 40 lines
        found: dict[str, int | None] = {"B": None, "C": None, "D": None, "E": None}
        # Check for inline choices on the SAME line first
        for letter in "BCDE":
            if f"({letter})" in stripped:
                found[letter] = i
        # Then check following lines
        for j in range(i + 1, min(n, i + 40)):
            s = lines[j].strip()
            for letter in "BCDE":
                if found[letter] is None and s.startswith(f"({letter})"):
                    found[letter] = j
        if all(found[l] is not None for l in "BCDE"):
            e_line = max(found[l] for l in "BCDE")  # type: ignore[type-var]
            blocks.append((i, e_line))
            i = e_line + 1
        else:
            i += 1
    return blocks


def _extract_problems_from_block(text: str) -> list[dict]:
    """
    Extract all problems from a single exam's text block.

    Strategy: anchor on (A)-(E) choice blocks (which are unambiguous), then search
    backwards from each (A) to find the problem number and text.
    """
    lines = text.split('\n')
    choice_blocks = _find_choice_blocks(lines)

    problems = []
    for block_idx, (a_line, e_line) in enumerate(choice_blocks):
        # Determine the search window for the problem number:
        # start just after the previous choice block's E line (or 0)
        if block_idx > 0:
            prev_e = choice_blocks[block_idx - 1][1]
            search_start = prev_e + 1
        else:
            search_start = 0

        # Search backwards from a_line to find the problem number.
        # Require actual text (not just more numbers) between the candidate and (A),
        # so that diagram labels / fraction denominators are skipped.
        num = None
        num_line = None
        for j in range(a_line - 1, search_start - 1, -1):
            stripped = lines[j].strip()
            if not re.fullmatch(r'\d{1,2}', stripped):
                continue
            candidate = int(stripped)
            if not (1 <= candidate <= 25):
                continue
            # Verify there is at least one non-numeric, non-empty line between j and a_line
            has_text = any(
                lines[k].strip() and not re.fullmatch(r'[\d\.\-\+\s]+', lines[k].strip())
                for k in range(j + 1, a_line)
            )
            if has_text:
                num = candidate
                num_line = j
                break

        if num is None:
            continue

        # Problem text: lines from num_line+1 to a_line (exclusive),
        # PLUS any text before (A) on a_line itself (partial inline case)
        a_line_text = lines[a_line].strip()
        a_inline_pos = a_line_text.find("(A)")
        pre_a_fragment = a_line_text[:a_inline_pos].strip()
        text_lines = list(lines[num_line + 1:a_line])
        if pre_a_fragment:
            text_lines.append(pre_a_fragment)
        problem_text = _clean('\n'.join(text_lines))

        # Answer choices: from (A) on a_line through e_line + trailing E value lines
        choices_start = a_line_text[a_inline_pos:]  # from (A) onwards on a_line
        # Build the text on the (E) line itself (after the (E) marker).
        _e_line_val = re.sub(r'^\(E\)\s*', '', lines[e_line].strip())

        e_val_end = e_line
        for j in range(e_line + 1, min(len(lines), e_line + 8)):
            s = lines[j].strip()
            if not s:
                break
            # Stop at any line containing letters (problem text, choice labels, etc.)
            if re.search(r'[a-zA-Z]', s):
                break
            if re.fullmatch(r'\d{1,2}', s) and int(s) in range(1, 26):
                digit_val = int(s)
                # Only stop when this digit is exactly the NEXT problem's number —
                # that means we've crossed a page boundary, not found a denominator.
                # The old secondary heuristic (break on any digit >= 10 without √)
                # was incorrectly cutting off fraction denominators like 16, 25, etc.
                if num is not None and digit_val == num + 1:
                    break
            e_val_end = j

        choices_lines = [choices_start] + lines[a_line + 1:e_val_end + 1]
        choices_text = '\n'.join(choices_lines)
        choices = _parse_choices(choices_text)

        has_image = bool(_IMAGE_KEYWORDS.search(problem_text))
        problems.append({
            "question_number": num,
            "problem_text": problem_text,
            "answer_choices": choices,
            "has_image": has_image,
        })

    # Deduplicate by question number (keep first occurrence)
    seen: set[int] = set()
    result = []
    for p in sorted(problems, key=lambda x: x["question_number"]):
        if p["question_number"] not in seen:
            seen.add(p["question_number"])
            result.append(p)
    return result


def _parse_choices(choices_text: str) -> dict[str, str]:
    """Parse answer choices from a block starting with (A)."""
    choice_re = re.compile(r'\(([ABCDE])\)\s*')
    tokens = choice_re.split(choices_text)
    choices: dict[str, str] = {}
    i = 1
    while i + 1 < len(tokens):
        letter = tokens[i].strip()
        value = tokens[i + 1].strip()
        if letter in "ABCDE":
            choices[letter] = _clean(value)
        i += 2
    return choices


def _parse_body(body: str) -> tuple[str, dict]:
    """Split problem body into (problem_text, choices). Used by solutions parser."""
    a_pos = body.find("(A)")
    if a_pos == -1:
        return body.strip(), {}
    problem_text = body[:a_pos].strip()
    choices = _parse_choices(body[a_pos:])
    return problem_text, choices


# ── Solutions PDF parsing ─────────────────────────────────────────────────────
def parse_solutions_pdf(path: str) -> dict[int, dict]:
    """
    Parse an MAA solutions PDF.  Three formats supported:
      - Format A (2007-2018): "N. Answer (X): solution..."
      - Format B (2001-2006): "N. (X) solution..."  (no 'Answer' keyword)
      - Format C (2021-2022): "Answer (X): solution..." (positional, no number)
    Returns {problem_number: {correct_answer, solution_text}}.
    """
    text = pdf_text(path)
    solutions: dict[int, dict] = {}

    # Format A: "N. Answer (X):"
    fmt_a = re.compile(
        r'(\d{1,2})\.\s+Answer\s+\(([A-E])\)\s*:?\s*(.*?)(?=\n\d{1,2}\.\s+Answer|\Z)',
        re.DOTALL | re.IGNORECASE,
    )
    matches_a = list(fmt_a.finditer(text))
    if len(matches_a) >= 10:
        for m in matches_a:
            num = int(m.group(1))
            solutions[num] = {"correct_answer": m.group(2).upper(), "solution_text": _clean(m.group(3))}
        return solutions

    # Format B: "N. (X) solution..." (no Answer keyword)
    fmt_b = re.compile(
        r'(\d{1,2})\.\s+\(([A-E])\)\s+(.*?)(?=\n\d{1,2}\.\s+\([A-E]\)|\Z)',
        re.DOTALL,
    )
    matches_b = list(fmt_b.finditer(text))
    if len(matches_b) >= 10:
        for m in matches_b:
            num = int(m.group(1))
            solutions[num] = {"correct_answer": m.group(2).upper(), "solution_text": _clean(m.group(3))}
        return solutions

    # Format C: positional "Answer (X):" (no number prefix, 2021-2022 MAA)
    fmt_c = re.compile(r'Answer\s+\(([A-E])\)\s*:?\s*(.*?)(?=Answer\s+\(|\Z)', re.DOTALL | re.IGNORECASE)
    matches_c = list(fmt_c.finditer(text))
    if matches_c:
        for i, m in enumerate(matches_c):
            solutions[i + 1] = {"correct_answer": m.group(1).upper(), "solution_text": _clean(m.group(2))}
        return solutions

    # Format D: "the answer is X" (Po-Shen Loh / LIVE format)
    fmt_d = re.compile(r'the\s+answer\s+is\s+([A-E])', re.IGNORECASE)
    matches_d = list(fmt_d.finditer(text))
    if matches_d:
        for i, m in enumerate(matches_d):
            solutions[i + 1] = {"correct_answer": m.group(1).upper(), "solution_text": ""}

    return solutions


# ── Utilities ─────────────────────────────────────────────────────────────────
def _clean(text: str) -> str:
    """Normalize whitespace and strip."""
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = '\n'.join(line.rstrip() for line in text.split('\n'))
    return text.strip()


def _merge_existing_metadata(output: list[dict], out_path: str) -> None:
    """
    If out_path already exists, copy topic/difficulty/correct_answer/solution_text
    and OR-merge has_image from existing records into the freshly-parsed output.
    This preserves tagger results and solution data across parser re-runs.
    """
    if not os.path.exists(out_path):
        return
    try:
        with open(out_path, encoding="utf-8") as f:
            existing = json.load(f)
    except Exception:
        return

    meta: dict[int, dict] = {
        p["question_number"]: p for p in existing
    }
    for rec in output:
        old = meta.get(rec["question_number"], {})
        if rec["topic"] is None and old.get("topic"):
            rec["topic"] = old["topic"]
        if rec["difficulty"] is None and old.get("difficulty"):
            rec["difficulty"] = old["difficulty"]
        if rec["correct_answer"] is None and old.get("correct_answer"):
            rec["correct_answer"] = old["correct_answer"]
        if not rec.get("solution_text") and old.get("solution_text"):
            rec["solution_text"] = old["solution_text"]
        # has_image: keep True if either old or new says True
        if old.get("has_image"):
            rec["has_image"] = True


# ── Orchestrator ──────────────────────────────────────────────────────────────
def build_catalog(pdf_dir: str) -> dict:
    """
    Scan pdf_dir and build a mapping:
      catalog[(year, exam_key)] = {"problems": path, "solutions": path}
    where exam_key is like 'AMC10A', 'AMC10B', or 'AMC10'.
    """
    catalog: dict[tuple, dict] = {}

    for fname in os.listdir(pdf_dir):
        if not fname.lower().endswith(".pdf"):
            continue
        info = classify_pdf(fname)
        if info is None:
            continue

        year = info["year"]
        variant = info["variant"]  # '', 'A', or 'B', or None
        pdf_type = info["type"]

        # Normalize exam key
        if variant is None or variant == '':
            exam_key = "AMC10"
        else:
            exam_key = f"AMC10{variant}"

        key = (year, exam_key)
        if key not in catalog:
            catalog[key] = {"problems": None, "solutions": None}

        full_path = os.path.join(pdf_dir, fname)
        if pdf_type == "problems":
            catalog[key]["problems"] = full_path
        elif pdf_type == "solutions":
            catalog[key]["solutions"] = full_path

    return catalog


def process_year_exam(year: int, exam_key: str, entry: dict, out_dir: str) -> int:
    """
    Parse problems and solutions for a single year+exam combo.
    Returns the number of problems successfully extracted.
    """
    problems_path = entry.get("problems")
    solutions_path = entry.get("solutions")

    if not problems_path:
        print(f"  [SKIP] No problems PDF for {year} {exam_key}")
        return 0

    # Parse problems
    try:
        exams = parse_problems_pdf(problems_path, year)
    except Exception as e:
        print(f"  [ERROR] Problems parse failed for {year} {exam_key}: {e}")
        return 0

    # For dual-exam PDFs, pick the right section
    if exam_key in exams:
        problems = exams[exam_key]
    elif "AMC10" in exams and exam_key == "AMC10":
        problems = exams["AMC10"]
    elif len(exams) == 1:
        problems = list(exams.values())[0]
    else:
        # Try to match partial key (e.g., AMC10A from a dual PDF)
        problems = exams.get(exam_key, [])

    if not problems:
        print(f"  [WARN] No problems extracted for {year} {exam_key}")
        return 0

    # Parse solutions
    solutions: dict[int, dict] = {}
    if solutions_path:
        try:
            solutions = parse_solutions_pdf(solutions_path)
        except Exception as e:
            print(f"  [WARN] Solutions parse failed for {year} {exam_key}: {e}")

    # Merge
    output = []
    for prob in problems:
        qnum = prob["question_number"]
        sol_data = solutions.get(qnum, {})

        record = {
            "id": f"{year}-{exam_key}-Q{qnum:02d}",
            "year": year,
            "exam": exam_key,
            "question_number": qnum,
            "topic": None,
            "difficulty": None,
            "problem_text": prob["problem_text"],
            "answer_choices": prob.get("answer_choices", {}),
            "correct_answer": sol_data.get("correct_answer"),
            "solution_text": sol_data.get("solution_text"),
            "has_image": prob.get("has_image", False),
        }
        output.append(record)

    # Write JSON (preserving existing tagger metadata)
    out_path = os.path.join(out_dir, f"{year}_{exam_key}.json")
    _merge_existing_metadata(output, out_path)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return len(output)


def process_dual_exam_pdf(year: int, problems_path: str, solutions: dict[str, str], out_dir: str) -> dict[str, int]:
    """Handle a combined A+B problems PDF with separate solution files."""
    try:
        exams = parse_problems_pdf(problems_path, year)
    except Exception as e:
        print(f"  [ERROR] Problems parse failed for {year}: {e}")
        return {}

    counts = {}
    for exam_key, problems in exams.items():
        sol_path = solutions.get(exam_key)
        sol_data: dict[int, dict] = {}
        if sol_path:
            try:
                sol_data = parse_solutions_pdf(sol_path)
            except Exception as e:
                print(f"  [WARN] Solutions parse failed for {year} {exam_key}: {e}")

        output = []
        for prob in problems:
            qnum = prob["question_number"]
            sd = sol_data.get(qnum, {})
            output.append({
                "id": f"{year}-{exam_key}-Q{qnum:02d}",
                "year": year,
                "exam": exam_key,
                "question_number": qnum,
                "topic": None,
                "difficulty": None,
                "problem_text": prob["problem_text"],
                "answer_choices": prob.get("answer_choices", {}),
                "correct_answer": sd.get("correct_answer"),
                "solution_text": sd.get("solution_text"),
                "has_image": prob.get("has_image", False),
            })

        out_path = os.path.join(out_dir, f"{year}_{exam_key}.json")
        _merge_existing_metadata(output, out_path)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        counts[exam_key] = len(output)

    return counts


def parse_single_file(
    problems_pdf: str,
    year: int,
    exam: str,
    solutions_pdf: str | None,
    out_dir: str,
) -> None:
    """
    Parse one problems PDF (and optional solutions PDF) directly.
    Used by the --file / --year / --exam CLI mode.
    """
    os.makedirs(out_dir, exist_ok=True)

    print(f"Problems PDF : {problems_pdf}")
    print(f"Solutions PDF: {solutions_pdf or '(none)'}")
    print(f"Exam         : {year} {exam}")
    print(f"Output       : {out_dir}")
    print()

    # Parse problems
    try:
        exams = parse_problems_pdf(problems_pdf, year)
    except Exception as e:
        print(f"[ERROR] Could not parse problems PDF: {e}")
        return

    # Pick the right section for the requested exam
    if exam in exams:
        problems = exams[exam]
    elif len(exams) == 1:
        problems = list(exams.values())[0]
    else:
        problems = exams.get(exam, [])

    # Parse solutions if provided
    solutions: dict[int, dict] = {}
    if solutions_pdf:
        try:
            solutions = parse_solutions_pdf(solutions_pdf)
        except Exception as e:
            print(f"[WARN] Could not parse solutions PDF: {e}")

    # Merge and build output records
    output = []
    for prob in problems:
        qnum = prob["question_number"]
        sd = solutions.get(qnum, {})
        output.append({
            "id": f"{year}-{exam}-Q{qnum:02d}",
            "year": year,
            "exam": exam,
            "question_number": qnum,
            "topic": None,
            "difficulty": None,
            "problem_text": prob["problem_text"],
            "answer_choices": prob.get("answer_choices", {}),
            "correct_answer": sd.get("correct_answer"),
            "solution_text": sd.get("solution_text"),
            "has_image": prob.get("has_image", False),
        })

    # Write JSON (preserving existing tagger metadata)
    out_path = os.path.join(out_dir, f"{year}_{exam}.json")
    _merge_existing_metadata(output, out_path)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # ── Summary ──────────────────────────────────────────────────────────────
    total = len(output)
    with_choices = sum(1 for p in output if p["answer_choices"])
    with_answer = sum(1 for p in output if p["correct_answer"])
    with_solution = sum(1 for p in output if p["solution_text"])
    has_image = sum(1 for p in output if p["has_image"])

    print(f"{'-'*48}")
    print(f"Extraction Summary -- {year} {exam}")
    print(f"{'-'*48}")
    print(f"  Problems extracted : {total}/25")
    print(f"  With answer choices: {with_choices}/{total}")
    print(f"  With correct answer: {with_answer}/{total}")
    print(f"  With solution text : {with_solution}/{total}")
    print(f"  Flagged has_image  : {has_image}")
    print(f"  Output JSON        : {out_path}")
    print()
    print("Sample records:")
    for p in output[:3]:
        choices_preview = {k: v[:30] for k, v in list(p["answer_choices"].items())[:3]}
        print(f"  Q{p['question_number']:2d} | answer={p['correct_answer']} | "
              f"image={p['has_image']} | choices={choices_preview}")


def main():
    parser = argparse.ArgumentParser(
        description="Parse AMC 10 PDFs into JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single-file mode (problems PDF + optional solutions PDF):
  python parse_amc.py --file "AMC 10 2023 Problems.pdf" --year 2023 --exam AMC10A
  python parse_amc.py --file "AMC 10 2018 Problems.pdf" --year 2018 --exam AMC10A \\
                      --solutions "2018_AMC10A_Solutions.pdf"

  # Batch mode (process entire directory):
  python parse_amc.py
  python parse_amc.py --year 2017
""",
    )
    parser.add_argument("--file", default=None,
                        help="Single problems PDF to parse (enables single-file mode)")
    parser.add_argument("--solutions", default=None,
                        help="Solutions PDF to pair with --file")
    parser.add_argument("--pdf-dir", default=None,
                        help="Directory containing AMC PDFs (batch mode)")
    parser.add_argument("--out-dir", default=None,
                        help="Output directory for JSON files")
    parser.add_argument("--year", type=int, default=None, help="Exam year (required with --file)")
    parser.add_argument("--exam", default=None, help="Exam name, e.g. AMC10A (required with --file)")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    out_dir = args.out_dir or str(script_dir.parent / "data" / "parsed")

    # ── Single-file mode ──────────────────────────────────────────────────────
    if args.file:
        if not args.year or not args.exam:
            parser.error("--file requires both --year and --exam")
        if not os.path.isfile(args.file):
            parser.error(f"File not found: {args.file}")
        parse_single_file(
            problems_pdf=args.file,
            year=args.year,
            exam=args.exam.upper(),
            solutions_pdf=args.solutions,
            out_dir=out_dir,
        )
        return

    # ── Batch mode ────────────────────────────────────────────────────────────
    pdf_dir = args.pdf_dir or str(script_dir.parent.parent)
    os.makedirs(out_dir, exist_ok=True)

    print(f"PDF directory: {pdf_dir}")
    print(f"Output directory: {out_dir}")
    print()

    catalog = build_catalog(pdf_dir)

    # Collect all years to process
    all_years = sorted(set(year for year, _ in catalog.keys()))
    if args.year:
        all_years = [y for y in all_years if y == args.year]

    processed_problems_paths: set[str] = set()
    total_problems = 0
    total_exams = 0

    for year in all_years:
        # Collect all entries for this year
        year_entries = {ek: entry for (y, ek), entry in catalog.items() if y == year}

        # Find the problems PDF(s) for this year
        # The combined problems PDF may be registered under "AMC10" even for dual years
        problems_by_path: dict[str, list[str]] = {}
        for ek, entry in year_entries.items():
            pp = entry.get("problems")
            if pp:
                problems_by_path.setdefault(pp, []).append(ek)

        for problems_path, registered_keys in problems_by_path.items():
            if problems_path in processed_problems_paths:
                continue
            processed_problems_paths.add(problems_path)

            # Determine solutions map: exam_key → solutions_path
            # For a combined problems PDF registered under "AMC10", look for A and B solutions
            solutions_map: dict[str, str] = {}
            for ek in ["AMC10", "AMC10A", "AMC10B"]:
                sol = year_entries.get(ek, {}).get("solutions")
                if sol:
                    solutions_map[ek] = sol

            print(f"Processing {year} (problems: {os.path.basename(problems_path)}) ...")

            if args.exam:
                # Single exam mode
                if args.exam not in solutions_map and "AMC10" in solutions_map:
                    solutions_map[args.exam] = solutions_map["AMC10"]

            if year in SINGLE_EXAM_YEARS:
                entry = {"problems": problems_path, "solutions": solutions_map.get("AMC10")}
                n = process_year_exam(year, "AMC10", entry, out_dir)
                if n > 0:
                    print(f"  {year} AMC10: {n} problems extracted")
                    total_problems += n
                    total_exams += 1
            else:
                counts = process_dual_exam_pdf(year, problems_path, solutions_map, out_dir)
                for ek, cnt in counts.items():
                    if args.exam and ek != args.exam:
                        continue
                    print(f"  {year} {ek}: {cnt} problems extracted")
                    total_problems += cnt
                    total_exams += 1

    print()
    print(f"Done. Extracted {total_problems} problems across {total_exams} exams.")
    print(f"JSON files saved to: {out_dir}")


if __name__ == "__main__":
    main()
