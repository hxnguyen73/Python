"""Apply all format fixes for AMC 2003 10A and 10B."""
import sys, json, re
sys.stdout.reconfigure(encoding='utf-8')

# ── 10A ────────────────────────────────────────────────────────────────────────
with open('amc-trainer/data/parsed/2003_AMC10A.json', encoding='utf-8') as f:
    a = json.load(f)
aq = {p['question_number']: p for p in a}

# Issue 1 – Q6: correct answer choices (inline text, not numbers)
aq[6]['answer_choices'] = {
    'A': 'x♡y = y♡x for all x and y',
    'B': '2(x♡y) = (2x)♡(2y) for all x and y',
    'C': 'x♡0 = x for all x',   # ♡0
    'D': 'x♡x = 0 for all x',
    'E': 'x♡y > 0 if x ≠ y',
}
# Use the actual heart symbol properly
aq[6]['answer_choices'] = {
    'A': 'x♡y = y♡x for all x and y',
    'B': '2(x♡y) = (2x)♡(2y) for all x and y',
    'C': 'x♡\x30 = x for all x',
    'D': 'x♡x = 0 for all x',
    'E': 'x♡y > 0 if x ≠ y',
}
# Simpler: just use the ♡ character directly from the problem text
aq[6]['answer_choices'] = {
    'A': 'x♡y = y♡x for all x and y',
    'B': '2(x♡y) = (2x)♡(2y) for all x and y',
    'C': 'x♡0 = x for all x',
    'D': 'x♡x = 0 for all x',
    'E': 'x♡y > 0 if x ≠ y',
}
aq[6]['correct_answer'] = 'C'

# Issue 2 – Q7: add missing problem
aq[7] = {
    'id': '2003-AMC10A-Q07',
    'year': 2003, 'exam': 'AMC10A', 'question_number': 7,
    'topic': 'Geometry', 'difficulty': 'easy',
    'problem_text': 'How many non-congruent triangles with perimeter 7 have integer side lengths?',
    'answer_choices': {'A': '1', 'B': '2', 'C': '3', 'D': '4', 'E': '5'},
    'correct_answer': 'B',
    'solution_text': None, 'has_image': False,
}

# Issue 3 – Q9: add missing problem (nested radicals)
aq[9] = {
    'id': '2003-AMC10A-Q09',
    'year': 2003, 'exam': 'AMC10A', 'question_number': 9,
    'topic': 'Algebra', 'difficulty': 'medium',
    'problem_text': 'Simplify $\\sqrt[3]{x\\sqrt[3]{x\\sqrt[3]{x\\sqrt{x}}}}$',
    'answer_choices': {
        'A': '$\\sqrt{x}$',
        'B': '$\\sqrt[3]{x^{2}}$',
        'C': '$\\sqrt[27]{x^{2}}$',
        'D': '$\\sqrt[54]{x}$',
        'E': '$\\sqrt[81]{x^{80}}$',
    },
    'correct_answer': 'A',
    'solution_text': None, 'has_image': False,
}

# Issue 4 – Q10: strip position labels, has_image
pt10 = aq[10]['problem_text']
pt10 = re.sub(r'\n1\n2\n.*$', '', pt10, flags=re.DOTALL).rstrip()
aq[10]['problem_text'] = pt10
aq[10]['has_image'] = True

# Issue 5 – Q15: E should be 18/25
aq[15]['answer_choices']['E'] = '$\\frac{18}{25}$'

# Issue 6 – Q17: fix A, B, D fractional answers
aq[17]['answer_choices']['A'] = '$\\frac{3\\sqrt{2}}{\\pi}$'
aq[17]['answer_choices']['B'] = '$\\frac{3\\sqrt{3}}{\\pi}$'
aq[17]['answer_choices']['D'] = '$\\frac{6}{\\pi}$'

# Issue 7 – Q18: fix problem text (fraction in equation)
aq[18]['problem_text'] = (
    'What is the sum of the reciprocals of the roots of the equation\n'
    '$\\dfrac{2003}{2004}x + 1 + \\dfrac{1}{x} = 0$?'
)

# Issue 8 – Q19: fix answer choices to actual lune area expressions
aq[19]['answer_choices'] = {
    'A': '$\\frac{1}{6}\\pi - \\frac{\\sqrt{3}}{4}$',
    'B': '$\\frac{\\sqrt{3}}{4} - \\frac{1}{12}\\pi$',
    'C': '$\\frac{\\sqrt{3}}{4} - \\frac{1}{24}\\pi$',
    'D': '$\\frac{\\sqrt{3}}{4} + \\frac{1}{24}\\pi$',
    'E': '$\\frac{\\sqrt{3}}{4} + \\frac{1}{12}\\pi$',
}
aq[19]['correct_answer'] = 'C'

# Issue 9 – Q20: add missing problem
aq[20] = {
    'id': '2003-AMC10A-Q20',
    'year': 2003, 'exam': 'AMC10A', 'question_number': 20,
    'topic': 'Number Theory', 'difficulty': 'medium',
    'problem_text': (
        'A base-10 three-digit number n is selected at random. Which of the following is closest\n'
        'to the probability that the base-9 representation and the base-11 representation of n are\n'
        'both three-digit numerals?'
    ),
    'answer_choices': {'A': '0.3', 'B': '0.4', 'C': '0.5', 'D': '0.6', 'E': '0.7'},
    'correct_answer': 'E',
    'solution_text': None, 'has_image': False,
}

# Issue 10 – Q22: add missing problem (rectangle, GF length)
aq[22] = {
    'id': '2003-AMC10A-Q22',
    'year': 2003, 'exam': 'AMC10A', 'question_number': 22,
    'topic': 'Geometry', 'difficulty': 'hard',
    'problem_text': (
        'In rectangle ABCD, we have AB = 8, BC = 9, H is on BC with BH = 6, E is on AD with\n'
        'DE = 4, line EC intersects line AH at G, and F is on line AD with GF ⊥ AF. Find the\n'
        'length GF.'
    ),
    'answer_choices': {'A': '16', 'B': '20', 'C': '24', 'D': '28', 'E': '30'},
    'correct_answer': 'B',
    'solution_text': None, 'has_image': True,
}

# Issue 11/20 – Q23: strip row-label digits, has_image
pt23 = aq[23]['problem_text']
pt23 = re.sub(r'\n1\n2\n.*$', '', pt23, flags=re.DOTALL).rstrip()
aq[23]['problem_text'] = pt23
aq[23]['has_image'] = True

# Q25 E: trailing dash
aq[25]['answer_choices']['E'] = aq[25]['answer_choices']['E'].rstrip('–').strip()

out_a = [aq[q] for q in sorted(aq)]
with open('amc-trainer/data/parsed/2003_AMC10A.json', 'w', encoding='utf-8') as f:
    json.dump(out_a, f, indent=2, ensure_ascii=False)
print(f'10A written: {len(out_a)} problems')

# ── 10B ────────────────────────────────────────────────────────────────────────
with open('amc-trainer/data/parsed/2003_AMC10B.json', encoding='utf-8') as f:
    b = json.load(f)
bq = {p['question_number']: p for p in b}

# Issue 12 – Q1: fix problem text (big fraction)
bq[1]['problem_text'] = (
    'Which of the following is the same as\n'
    '$\\dfrac{2-4+6-8+10-12+14}{3-6+9-12+15-18+21}$?'
)

# Issue 13 – Q4: strip dimension labels, has_image already True
pt4 = bq[4]['problem_text']
pt4 = re.sub(r'\n\d.*$', '', pt4, flags=re.DOTALL).rstrip()
bq[4]['problem_text'] = pt4
bq[4]['has_image'] = True

# Issue 14 – Q6: strip diagram labels, has_image
pt6 = bq[6]['problem_text']
pt6 = re.sub(r'\nDiagonal.*$', '', pt6, flags=re.DOTALL).rstrip()
bq[6]['problem_text'] = pt6
bq[6]['has_image'] = True

# Issue 15 – Q9: fix problem text (fraction in equation)
bq[9]['problem_text'] = (
    'Find the value of x that satisﬁes the equation\n'
    '$25^{-2} = \\dfrac{5^{48/x}}{5^{26/x} \\cdot 25^{17/x}}$'
)

# Issue 16 – Q15: fix answer choices to text, and add Q16
bq[15]['answer_choices'] = {
    'A': 'a prime number',
    'B': 'divisible by 2',
    'C': 'divisible by 5',
    'D': 'divisible by 7',
    'E': 'divisible by 11',
}
bq[15]['correct_answer'] = 'E'

bq[16] = {
    'id': '2003-AMC10B-Q16',
    'year': 2003, 'exam': 'AMC10B', 'question_number': 16,
    'topic': 'Combinatorics', 'difficulty': 'medium',
    'problem_text': (
        'A restaurant offers three desserts, and exactly twice as many appetizers as main courses.\n'
        'A dinner consists of an appetizer, a main course, and a dessert. What is the least number\n'
        'of main courses that the restaurant should offer so that a customer could have a different\n'
        'dinner each night in the year 2003?'
    ),
    'answer_choices': {'A': '4', 'B': '5', 'C': '6', 'D': '7', 'E': '8'},
    'correct_answer': 'E',
    'solution_text': None, 'has_image': False,
}

# Issue 17 – Q19: fix answer choices C, D, E
bq[19]['answer_choices'] = {
    'A': '$\\pi - \\sqrt{3}$',
    'B': '$\\pi - \\sqrt{2}$',
    'C': '$\\frac{\\pi + \\sqrt{2}}{2}$',
    'D': '$\\frac{\\pi + \\sqrt{3}}{2}$',
    'E': '$\\frac{7}{6}\\pi - \\frac{\\sqrt{3}}{2}$',
}
bq[19]['correct_answer'] = 'E'

# Issue 18 – Q20: strip diagram labels, has_image
pt20 = bq[20]['problem_text']
# Problem should end after "△AEB."
pt20 = re.sub(r'(△AEB\.?).*$', r'\1', pt20, flags=re.DOTALL).rstrip()
bq[20]['problem_text'] = pt20
bq[20]['has_image'] = True

# Issue 19 – Q21: E should be 7/16
bq[21]['answer_choices']['E'] = '$\\frac{7}{16}$'

# Q25 E: trailing dash
bq[25]['answer_choices']['E'] = bq[25]['answer_choices']['E'].rstrip('–').strip()

out_b = [bq[q] for q in sorted(bq)]
with open('amc-trainer/data/parsed/2003_AMC10B.json', 'w', encoding='utf-8') as f:
    json.dump(out_b, f, indent=2, ensure_ascii=False)
print(f'10B written: {len(out_b)} problems')

# ── Verify ─────────────────────────────────────────────────────────────────────
with open('amc-trainer/data/parsed/2003_AMC10A.json', encoding='utf-8') as f:
    av = json.load(f)
avq = {p['question_number']: p for p in av}
print('\n10A spot checks:')
print('Q nums:', sorted(avq))
print('Q6 choices:', list(avq[6]['answer_choices'].values()))
print('Q7 present:', 7 in avq)
print('Q9 present:', 9 in avq)
print('Q10 has_image:', avq[10]['has_image'])
print('Q15 E:', avq[15]['answer_choices']['E'])
print('Q17 A:', avq[17]['answer_choices']['A'])
print('Q18 text snippet:', avq[18]['problem_text'][:60])
print('Q19 A:', avq[19]['answer_choices']['A'])
print('Q20 present:', 20 in avq)
print('Q22 present:', 22 in avq)
print('Q23 has_image:', avq[23]['has_image'])

with open('amc-trainer/data/parsed/2003_AMC10B.json', encoding='utf-8') as f:
    bv = json.load(f)
bvq = {p['question_number']: p for p in bv}
print('\n10B spot checks:')
print('Q nums:', sorted(bvq))
print('Q1 text:', bvq[1]['problem_text'][:60])
print('Q4 has_image:', bvq[4]['has_image'])
print('Q6 has_image:', bvq[6]['has_image'])
print('Q9 text snippet:', bvq[9]['problem_text'][:80])
print('Q15 choices:', list(bvq[15]['answer_choices'].values()))
print('Q16 present:', 16 in bvq)
print('Q19 E:', bvq[19]['answer_choices']['E'])
print('Q20 has_image:', bvq[20]['has_image'])
print('Q21 E:', bvq[21]['answer_choices']['E'])
