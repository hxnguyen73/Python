/**
 * Normalizes PDF-extracted problem text into KaTeX-ready form.
 *
 * The parser (parse_amc.py) emits ^{...} for superscripts via character-level
 * font-size and y-position analysis.  Fraction bars arrive as bare \n line
 * breaks.  This function handles both, plus ligatures and control characters.
 */

/**
 * Walk `text` from position `i`, counting braces to find the matching `}` for
 * the `{` that was just opened.  Returns the index AFTER the closing `}`.
 */
function closingBrace(text: string, i: number): number {
  let depth = 1;
  while (i < text.length && depth > 0) {
    if (text[i] === '{') depth++;
    else if (text[i] === '}') depth--;
    i++;
  }
  return i;
}

/**
 * Wrap every `base^{exp}` token in $…$ (for KaTeX), using brace counting so
 * nested towers like 2^{2^{2^{2}}} are captured as a single expression.
 * Only operates on text outside existing $…$ regions.
 */
function wrapSuperscripts(text: string): string {
  let out = '';
  let i = 0;
  while (i < text.length) {
    const caret = text.indexOf('^{', i);
    if (caret === -1) { out += text.slice(i); break; }

    // Walk left over alphanumeric chars to collect the base
    let base = caret;
    while (base > i && /[a-zA-Z0-9]/.test(text[base - 1])) base--;

    if (base === caret) {
      // No alphanumeric base before ^{ — skip this caret
      out += text.slice(i, caret + 1);
      i = caret + 1;
      continue;
    }

    // Append everything before the base
    out += text.slice(i, base);

    // Consume base + all consecutive ^{...} using brace counting
    let j = caret;
    while (j < text.length && text[j] === '^' && text[j + 1] === '{') {
      j = closingBrace(text, j + 2); // skip past ^{ then count braces
    }

    out += '$' + text.slice(base, j) + '$';
    i = j;
  }
  return out;
}

export function normalizeProblemText(text: string): string {
  let t = text.trimEnd();

  // ── Square-root recovery (must run BEFORE trailing-digit stripping) ────────
  //
  // In PDFs the √ glyph and its radicand sit at slightly different y-positions,
  // so PyMuPDF emits them on separate lines.  Join them NOW so that the
  // trailing-digit stripper does not accidentally eat the radicand/denominator.
  //
  // "√\n<digits>" → "\sqrt{digits}"  (separate-line radicand)
  // "√<digits>"   → "\sqrt{digits}"  (same-line radicand)
  // lone "√"       → "\sqrt{}"       (radicand missing — wrapped later)
  t = t.replace(/√\n(\d+)/g, (_, d) => `\\sqrt{${d}}`);
  t = t.replace(/√(\d+)/g, (_, d) => `\\sqrt{${d}}`);
  t = t.replace(/√(?!\d)/g, '\\sqrt{}');

  // Strip trailing diagram-label artifacts: multiple standalone numbers at end
  // (e.g. "\n1\n2\n6" from dimension labels).  Requires 2+ occurrences so that
  // a legitimate single-line denominator like "\n9" in "4\n9" is not stripped.
  t = t.replace(/(\n[\d\s]+){2,}$/, '').trimEnd();

  // Strip PDF control/encoding artifacts (non-printable chars, keep \n)
  t = t.replace(/[\x00-\x09\x0b-\x1f\x7f]/g, '');

  // Fix common PDF ligature code-points
  t = t
    .replace(/ﬀ/g, 'ff')
    .replace(/ﬁ/g, 'fi')
    .replace(/ﬂ/g, 'fl')
    .replace(/ﬃ/g, 'ffi')
    .replace(/ﬄ/g, 'ffl');

  // Step 2: join a partial numerator that ends on one line with a \sqrt{...}
  // that begins the next line — both belong to the same stacked-fraction numerator.
  // e.g. "2+\n\sqrt{6}" → "2+\sqrt{6}"  and  "3\n\sqrt{5}" → "3\sqrt{5}"
  t = t.replace(
    /([\d][^{\n]*)\n(\\sqrt{[^}]*})/g,
    '$1$2'
  );

  // Step 3b (runs first): fraction where a digit-starting numerator contains a \sqrt:
  //   "2+\sqrt{6}\n3" → "$\frac{2+\sqrt{6}}{3}$"
  // Must run BEFORE 3a so the \n isn't consumed before the full numerator is captured.
  // Lookbehind prevents starting inside a \sqrt{…} brace (e.g. matching "5}" in "\sqrt{65}").
  // Blocks positions preceded by letter, digit, brace, or backslash.
  t = t.replace(
    /(?<![a-zA-Z0-9{}\\])([\d][\d +\-*/().^{}\\a-zA-Z]*) *\n *(\d+)( +[a-zA-Z]|\s*$)/g,
    (_, num, den, tail) => `$\\frac{${num.trim()}}{${den.trim()}}$${tail}`
  );

  // Step 3a (fallback): fraction where the full numerator is a lone \sqrt expression:
  //   "\sqrt{X}\nN" → "$\frac{\sqrt{X}}{N}$"
  t = t.replace(
    /(\\sqrt{[^}]*}) *\n *(\d+)( +[a-zA-Z]|\s*$)/g,
    (_, num, den, tail) => `$\\frac{${num}}{${den}}$${tail}`
  );

  // ── Fraction recovery (non-sqrt) ───────────────────────────────────────────
  //
  // Multi-term arithmetic fraction with plain digits / superscript notation.
  //   "10^{2000} + 10^{2002}\n10^{2001} + 10^{2001} is closest to"
  //   → "$\frac{10^{2000} + 10^{2002}}{10^{2001} + 10^{2001}}$ is closest to"
  t = t.replace(
    /(\d[\d +\-*/().^{}]*) *\n *(\d[\d +\-*/().^{}]*?)( +[a-zA-Z]|\s*$)/g,
    (_, num, den, tail) => `$\\frac{${num.trim()}}{${den.trim()}}$${tail}`
  );

  // Single-CHARACTER letter fractions: "a\nb" → "$\frac{a}{b}$"
  // Restricted to letters (not digits) to avoid false positives such as
  // "= 2\n2^{exp}" (equation continuation) being mistaken for 2/2.
  t = t.replace(
    /(?<![a-zA-Z0-9])([a-zA-Z])\n([a-zA-Z])(?![a-zA-Z0-9])/g,
    (_, n, d) => `$\\frac{${n}}{${d}}$`
  );

  // Variable-expression over digit: "m\n2", "m^{2}\n4" → "$\frac{m}{2}$" etc.
  // Handles polynomials like P(m) = m/2 + m^2/4 + ... where the PDF places
  // numerator and denominator on separate lines.
  // Lookahead: denominator must be followed by a non-alphanumeric char or
  // end-of-string so we don't fire inside a larger expression.
  t = t.replace(
    /(?<![a-zA-Z0-9{}\\])([a-zA-Z][a-zA-Z0-9^{}\\.]*) *\n *(\d+)(?= *[^a-zA-Z0-9]|$)/g,
    (_, num, den) => `$\\frac{${num.trim()}}{${den.trim()}}$`
  );

  // ── Superscript wrapping ───────────────────────────────────────────────────
  //
  // Wrap base^{exp} expressions in $…$ using brace counting so that nested
  // towers like 2^{2^{2^{2}}} are captured as one expression.
  // Also wrap standalone \sqrt{...} not yet inside $…$.
  // Only applied to text outside existing $…$ regions (split/rejoin approach).
  // Only treat $…$ as a math block when the content contains \ or ^ —
  // the markers of real LaTeX. This prevents monetary amounts like $28000
  // from accidentally pairing with another $28000 to form a fake math block.
  t = t.split(/(\$(?=[^$]*[\\^_])[^$]+\$)/g).map((part, idx) => {
    if (idx % 2 === 1) return part; // already inside $…$
    let p = wrapSuperscripts(part);
    // Wrap any remaining \sqrt{...} in $…$
    p = p.replace(/\\sqrt\{[^}]*\}/g, '$$$&$');
    return p;
  }).join('');

  // Preserve newlines before bullet points ("- ") so condition lists stay readable.
  // All other remaining newlines become spaces; collapse duplicate spaces.
  t = t.replace(/\n(?=[^\-])/g, ' ').replace(/ {2,}/g, ' ');

  return t.trim();
}

/**
 * Normalize then truncate to `chars` characters for plain-text previews.
 * Strips $…$ math wrappers so markup doesn't appear raw in grid cards.
 */
export function truncateText(text: string, chars: number): string {
  const normalized = normalizeProblemText(text);
  const plain = normalized
    .replace(/\$\\frac\{([^}]+)\}\{([^}]+)\}\$/g, '$1/$2')
    .replace(/\$([^$]+)\$/g, '$1');
  if (plain.length <= chars) return plain;
  return plain.slice(0, chars) + '…';
}
