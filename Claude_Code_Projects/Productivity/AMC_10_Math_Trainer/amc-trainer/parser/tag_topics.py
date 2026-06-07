"""
AMC 10 Topic & Difficulty Tagger
Uses the Claude API to classify each problem's topic and difficulty,
then saves the enriched JSON back to data/parsed/.

Usage:
  python tag_topics.py [--parsed-dir PATH] [--batch-size N] [--year YEAR] [--exam EXAM]

Reads ANTHROPIC_API_KEY from environment.
"""

import anthropic
import json
import os
import sys
import time
import argparse
import glob
from pathlib import Path

TOPICS = [
    "Algebra",
    "Geometry",
    "Number Theory",
    "Combinatorics",
    "Probability",
    "Functions",
    "Sequences & Series",
    "Trigonometry",
    "Other",
]

SYSTEM_PROMPT = """You are classifying AMC 10 math competition problems by topic and difficulty.

For each problem provided, output a JSON object with exactly these fields:
- "topic": one of Algebra, Geometry, Number Theory, Combinatorics, Probability, Functions, Sequences & Series, Trigonometry, Other
- "difficulty": one of "easy", "medium", "hard"

Difficulty guidelines:
- easy: conceptually straightforward, Q1-Q8 range, one or two steps
- medium: moderate complexity, Q9-Q18 range, requires some insight or multi-step reasoning
- hard: challenging, Q19-Q25 range, non-obvious approach or heavy computation

Base difficulty primarily on the true conceptual challenge, not just the problem number.
If the problem text is incomplete or unclear, make your best guess.

Return ONLY a JSON array, one object per problem, in the same order as input."""

USER_PROMPT_TEMPLATE = """Classify each of these AMC 10 problems. Return a JSON array with one object per problem.

{problems}"""


def build_problem_entry(prob: dict) -> str:
    text = prob.get("problem_text", "").strip()[:500]  # truncate for API efficiency
    qnum = prob.get("question_number", "?")
    exam = prob.get("exam", "")
    year = prob.get("year", "")
    return f"[{year} {exam} Q{qnum}] {text}"


def tag_batch(client: anthropic.Anthropic, problems: list[dict]) -> list[dict]:
    """Send a batch of problems to Claude for classification. Returns list of {topic, difficulty}."""
    problem_entries = "\n\n".join(
        f"{i+1}. {build_problem_entry(p)}" for i, p in enumerate(problems)
    )
    user_prompt = USER_PROMPT_TEMPLATE.format(problems=problem_entries)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = response.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])

        results = json.loads(raw)
        if isinstance(results, list) and len(results) == len(problems):
            return results
        # If Claude returned a dict instead of list (single problem)
        if isinstance(results, dict) and len(problems) == 1:
            return [results]
    except Exception as e:
        print(f"  [WARN] API call failed: {e}", file=sys.stderr)

    return [{"topic": "Other", "difficulty": "medium"}] * len(problems)


def tag_file(client: anthropic.Anthropic, json_path: str, batch_size: int, delay: float) -> int:
    """Tag all untagged problems in a JSON file. Returns count of problems tagged."""
    with open(json_path, encoding="utf-8") as f:
        problems = json.load(f)

    # Find problems that need tagging
    to_tag = [(i, p) for i, p in enumerate(problems) if not p.get("topic")]
    if not to_tag:
        return 0

    print(f"  Tagging {len(to_tag)} problems in {os.path.basename(json_path)} ...")

    tagged = 0
    for batch_start in range(0, len(to_tag), batch_size):
        batch = to_tag[batch_start:batch_start + batch_size]
        indices = [i for i, _ in batch]
        probs = [p for _, p in batch]

        results = tag_batch(client, probs)

        for (orig_idx, _), result in zip(batch, results):
            if isinstance(result, dict):
                problems[orig_idx]["topic"] = result.get("topic", "Other")
                problems[orig_idx]["difficulty"] = result.get("difficulty", "medium")
                tagged += 1

        if batch_start + batch_size < len(to_tag):
            time.sleep(delay)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(problems, f, indent=2, ensure_ascii=False)

    return tagged


def print_distribution(parsed_dir: str) -> None:
    """Print topic and difficulty distribution across all parsed files."""
    topic_counts: dict[str, int] = {}
    diff_counts: dict[str, int] = {}
    total = 0

    for f in glob.glob(os.path.join(parsed_dir, "*.json")):
        with open(f, encoding="utf-8") as fh:
            data = json.load(fh)
        for p in data:
            topic = p.get("topic") or "Untagged"
            diff = p.get("difficulty") or "Untagged"
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
            diff_counts[diff] = diff_counts.get(diff, 0) + 1
            total += 1

    print(f"\nTotal problems: {total}")
    print("\nTopic distribution:")
    for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1]):
        bar = "#" * (count // 5)
        print(f"  {topic:<22} {count:4d}  {bar}")

    print("\nDifficulty distribution:")
    for diff in ["easy", "medium", "hard", "Untagged"]:
        count = diff_counts.get(diff, 0)
        bar = "#" * (count // 5)
        print(f"  {diff:<10} {count:4d}  {bar}")


def simulate_tagging(problems: list[dict]) -> list[dict]:
    """
    Rule-based topic/difficulty classifier used by --dry-run.
    Not as accurate as Claude, but illustrates the tagging flow without API cost.
    """
    import re

    KEYWORD_MAP = [
        ("Geometry",         r'\b(triangle|circle|square|rectangle|polygon|angle|area|perimeter|radius|diameter|arc|chord|tangent|hexagon|octagon|cylinder|cone|sphere|prism|pyramid|volume|surface area|similar|congruent|parallel|perpendicular|coordinate|midpoint|slope|distance)\b'),
        ("Probability",      r'\b(probability|chance|random|dice|coin|cards|ball|box|bag|urn|expected|outcome|event|sample space|independent|conditional)\b'),
        ("Combinatorics",    r'\b(combination|permutation|arrange|choose|select|committee|ways|counting|handshake|path|route|digit|string|sequence|how many)\b'),
        ("Number Theory",    r'\b(prime|factor|divisor|divisible|remainder|modulo|gcd|lcm|integer|digit|units digit|even|odd|perfect square|perfect cube|Fibonacci)\b'),
        ("Sequences & Series", r'\b(sequence|series|arithmetic|geometric|sum of|term|progression|Fibonacci|recurrence)\b'),
        ("Functions",        r'\b(function|f\(|g\(|h\(|domain|range|inverse|composition|polynomial|root|zero|graph|asymptote|absolute value)\b'),
        ("Algebra",          r'\b(equation|variable|solve|system|expression|inequality|quadratic|linear|ratio|proportion|percent|rate|average|mean|median|work|speed|distance|time)\b'),
        ("Trigonometry",     r'\b(sin|cos|tan|sine|cosine|tangent|radian|degree|unit circle|law of sines|law of cosines)\b'),
    ]

    results = []
    for p in problems:
        text = (p.get("problem_text") or "").lower()
        topic = "Other"
        for t, pattern in KEYWORD_MAP:
            if re.search(pattern, text, re.IGNORECASE):
                topic = t
                break

        qnum = p.get("question_number", 13)
        if qnum <= 8:
            difficulty = "easy"
        elif qnum <= 18:
            difficulty = "medium"
        else:
            difficulty = "hard"

        results.append({"topic": topic, "difficulty": difficulty})
    return results


def tag_file(client: anthropic.Anthropic | None, json_path: str, batch_size: int, delay: float, dry_run: bool = False, force: bool = False) -> int:
    """Tag all untagged problems in a JSON file. Returns count of problems tagged."""
    with open(json_path, encoding="utf-8") as f:
        problems = json.load(f)

    if force:
        for p in problems:
            p["topic"] = None
            p["difficulty"] = None

    # Find problems that need tagging
    to_tag = [(i, p) for i, p in enumerate(problems) if not p.get("topic")]
    if not to_tag:
        return 0

    mode = "[DRY-RUN] " if dry_run else ""
    print(f"  {mode}Tagging {len(to_tag)} problems in {os.path.basename(json_path)} ...")

    tagged = 0
    for batch_start in range(0, len(to_tag), batch_size):
        batch = to_tag[batch_start:batch_start + batch_size]
        probs = [p for _, p in batch]

        if dry_run:
            results = simulate_tagging(probs)
        else:
            results = tag_batch(client, probs)  # type: ignore[arg-type]

        for (orig_idx, _), result in zip(batch, results):
            if isinstance(result, dict):
                problems[orig_idx]["topic"] = result.get("topic", "Other")
                problems[orig_idx]["difficulty"] = result.get("difficulty", "medium")
                tagged += 1

        if not dry_run and batch_start + batch_size < len(to_tag):
            time.sleep(delay)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(problems, f, indent=2, ensure_ascii=False)

    return tagged


def main():
    parser = argparse.ArgumentParser(description="Tag AMC 10 problems with topics and difficulty")
    parser.add_argument("--parsed-dir", default=None, help="Directory with JSON files")
    parser.add_argument("--batch-size", type=int, default=10, help="Problems per API call (default: 10)")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between API calls (default: 1.0)")
    parser.add_argument("--year", type=int, default=None, help="Only process this year")
    parser.add_argument("--exam", default=None, help="Only process this exam (e.g. AMC10A)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Use rule-based tagger (no API key needed) — for testing")
    parser.add_argument("--force", action="store_true",
                        help="Re-tag all problems, overwriting existing topic/difficulty")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    parsed_dir = args.parsed_dir or str(script_dir.parent / "data" / "parsed")

    client = None
    if not args.dry_run:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("Error: ANTHROPIC_API_KEY not set. Use --dry-run to test without the API.")
            sys.exit(1)
        client = anthropic.Anthropic(api_key=api_key)

    mode_label = "DRY-RUN (rule-based)" if args.dry_run else f"Claude API (batch={args.batch_size})"
    print(f"Mode          : {mode_label}")
    print(f"Parsed dir    : {parsed_dir}")
    if args.force:
        print(f"Force re-tag  : yes (overwriting existing topics)")
    print()

    json_files = sorted(glob.glob(os.path.join(parsed_dir, "*.json")))

    # Filter by year/exam if specified
    if args.year or args.exam:
        filtered = []
        for f in json_files:
            name = os.path.basename(f).replace(".json", "")
            if args.year and str(args.year) not in name:
                continue
            if args.exam and args.exam not in name:
                continue
            filtered.append(f)
        json_files = filtered

    total_tagged = 0
    for json_path in json_files:
        n = tag_file(client, json_path, args.batch_size, args.delay, dry_run=args.dry_run, force=args.force)
        if n > 0:
            total_tagged += n

    print(f"\nTagged {total_tagged} problems.")
    print_distribution(parsed_dir)


if __name__ == "__main__":
    main()
