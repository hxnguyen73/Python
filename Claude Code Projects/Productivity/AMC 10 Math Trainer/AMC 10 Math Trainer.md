Suggested Claude Code Session order

Session 1: "Help me parse my AMC PDFs and extract 
            problems into a structured JSON database"

Session 2: "Build a Next.js dashboard that loads the 
            JSON and displays problems with filters 
            for topic, year, and difficulty"

Session 3: "Add a Show Solution toggle and integrate 
            KaTeX for math rendering"

Session 4: "Add the Problem Morpher using the 
            Anthropic API with a dedicated prompt"

Session 5: "Add progress tracking — log which problems 
            were attempted, score, and time taken"


_______________________________________



Before we begin, here's the full project context:
I'm building an AMC 10 Math Competition Trainer with:
- A problem browser dashboard (filter by topic/year/difficulty)
- PDF-parsed problem + solution database
- KaTeX math rendering
- A Problem Morpher that uses Claude API to alter 
  problem parameters and compute new solutions
- Progress tracking per student

We'll build this in sessions. Today is Session 1: 
PDF parsing and project setup.

-------------------------------

Prompt 1 - Project Setup

I'm building an AMC 10 Math Competition Trainer app. 
Let's start by setting up the project structure.

Create a Next.js project with Tailwind CSS called "amc-trainer" with this structure:

amc-trainer/
├── frontend/          # Next.js app
├── parser/            # Python PDF parser
├── data/
│   ├── raw/           # Original PDFs go here
│   ├── parsed/        # Extracted JSON output
│   └── progress/      # User progress logs
└── README.md

Set up the Next.js app with:
- Tailwind CSS
- KaTeX for math rendering (react-katex)
- shadcn/ui for components

Also set up the Python parser environment with:
- pdfplumber
- PyMuPDF (fitz)
- A requirements.txt file

-----------------------------------

Prompt 2 - PDF Parser (run after setup)

Now build the PDF parser. I have AMC 10 past exam PDFs 
where each PDF contains both problems and solutions.

The typical structure is:
- Problems are numbered 1–30
- Each problem has 5 answer choices (A–E)
- Solutions appear in the second half of the PDF
- Math expressions are formatted in LaTeX

Write a Python script parser/parse_amc.py that:

1. Takes a PDF file path and exam metadata (year, exam name) as arguments
2. Extracts each problem's:
   - Problem number
   - Full problem text (preserving LaTeX math)
   - Answer choices A through E
   - Correct answer (if listed)
   - Corresponding solution text
3. Detects if a problem contains an image/diagram 
   and flags it (has_image: true)
4. Outputs a structured JSON file to data/parsed/ 
   with this schema per problem:

{
  "id": "2023-AMC10A-Q14",
  "year": 2023,
  "exam": "AMC10A",
  "question_number": 14,
  "topic": null,
  "difficulty": null,
  "problem_text": "...",
  "answer_choices": {
    "A": "...", "B": "...", "C": "...", 
    "D": "...", "E": "..."
  },
  "correct_answer": "C",
  "solution_text": "...",
  "has_image": false
}

Test it against my PDF at: data/raw/[filename].pdf
Print a summary of how many problems were 
successfully extracted.

----------------------------------------

Prompt 3 - Auto Topic Tagger (Run after parser works)

The parsed JSON problems have topic: null. 

Write a Python script parser/tag_topics.py that:

1. Reads all JSON files from data/parsed/
2. For each problem, calls the Anthropic Claude API 
   (claude-sonnet-4-20250514) to classify the topic 
   and difficulty

Use this classification prompt:
- Topics: Algebra, Geometry, Number Theory, 
  Combinatorics, Probability, Functions, 
  Sequences & Series, Trigonometry, Other
- Difficulty: easy (Q1-10), medium (Q11-20), 
  hard (Q21-30) — but also use Claude to 
  assess true conceptual difficulty

3. Updates each problem's topic and difficulty fields
4. Saves the enriched JSON back to data/parsed/
5. Prints a topic distribution summary when done

Use batch processing with a small delay between 
API calls to avoid rate limits.

-------------------------------------------

Prompt 4 - Kick off the Dashboard (Session 2 Starter)

The PDF parsing is complete. I have structured JSON 
files in data/parsed/ with AMC problems and solutions.

Now build the main Dashboard in Next.js. It should have:

1. LEFT SIDEBAR:
   - Filter by Year (multi-select)
   - Filter by Topic (multi-select) 
   - Filter by Difficulty (easy/medium/hard)
   - Filter by Exam (AMC10A / AMC10B)

2. MAIN PANEL:
   - Problem cards in a grid
   - Each card shows: problem number, year, topic tag, 
     difficulty badge, and first 2 lines of problem text
   - Click a card to open the full problem view

3. PROBLEM VIEW (full screen modal or page):
   - Full problem text rendered with KaTeX
   - Answer choices A–E
   - [Show Solution] button — hidden until clicked
   - [Morph This Problem] button (placeholder for now)
   - [Mark as Done] toggle

Use shadcn/ui components and Tailwind. 
Make it clean, dark mode, and easy to read 
math-heavy content.

---------------------------

Prompt 4B - Solution reveal + KaTeX rendering (Session 3)

The Dashboard and Problem Browser are working. 
Now add the Solution Reveal system and proper 
math rendering with KaTeX across the entire app.

WHAT WE'RE ADDING:
1. KaTeX math rendering for all problem/solution text
2. Animated solution reveal panel
3. Step-by-step solution display
4. Answer choice selection UI
5. Problem view page/modal with full detail

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 1 — KATEX SETUP & MATH RENDERING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Install and configure KaTeX:
  npm install katex react-katex
  npm install rehype-katex remark-math

Create a reusable component components/MathText.tsx:

This component should:
1. Accept a string of text that may contain:
   - Inline math: $x^2 + y^2 = z^2$
   - Display math: $$\frac{a}{b} + \frac{c}{d}$$
   - Plain text mixed with both
2. Parse the string and split into math 
   and non-math segments
3. Render math segments using react-katex:
   - InlineMath for $...$ expressions
   - BlockMath for $$...$$ expressions
4. Render plain text segments as-is
5. Handle rendering errors gracefully —
   if KaTeX fails on an expression, show 
   the raw LaTeX in a monospace font rather 
   than crashing

Add to globals.css:
  @import 'katex/dist/katex.min.css';
  
  /* Dark mode fix */
  .katex { color: inherit; }
  
  /* Display math centering */
  .katex-display {
    margin: 1rem 0;
    overflow-x: auto;
    overflow-y: hidden;
  }

Test MathText with these expressions to verify
rendering works correctly:

  "If $x^2 - 5x + 6 = 0$, find all values of $x$"
  "The area is $$A = \pi r^2$$"
  "Let $\frac{a}{b} = \frac{3}{4}$ where $\gcd(a,b)=1$"
  "How many integers $n$ satisfy $1 \leq n \leq 100$?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 2 — PROBLEM VIEW PAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Create a full Problem View at /problem/[id]:

LAYOUT:
┌─────────────────────────────────────────────┐
│ ← Back    2023 AMC10A — Problem 14          │
│           [Geometry] [Medium]  ⏱️ 0:00      │
├─────────────────────────────────────────────┤
│                                             │
│  PROBLEM TEXT (rendered with MathText)      │
│                                             │
│  Let ABCD be a rectangle where              │
│  $AB = 2\sqrt{3}$ and $BC = 4$.             │
│  What is the area of triangle ABD?          │
│                                             │
├─────────────────────────────────────────────┤
│  ANSWER CHOICES                             │
│                                             │
│  ○ (A)  $4\sqrt{3}$                         │
│  ○ (B)  $6\sqrt{3}$                         │
│  ○ (C)  $8$                                 │
│  ○ (D)  $4\sqrt{6}$                         │
│  ○ (E)  $12$                                │
│                                             │
│  [Submit Answer]  (disabled until selected) │
├─────────────────────────────────────────────┤
│  [💡 Hint]  [📖 Show Solution]              │
│  [🔀 Morph This Problem]                    │
└─────────────────────────────────────────────┘

ANSWER CHOICE BEHAVIOR:
- Each choice is a clickable card
- Clicking selects it (highlighted border)
- Only one choice selectable at a time
- [Submit Answer] enables only after selection
- After submit:
  ✅ Correct → choice turns green, 
     show "Correct! +6 pts" message
  ❌ Wrong → choice turns red, 
     correct answer turns green,
     show "Incorrect. The answer was (C)" message
- After submitting, lock all choices (no re-selecting)
- Reveal [💡 Hint] and [📖 Show Solution] 
  buttons only after answer is submitted
  (prevents students from jumping to solution)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 3 — SOLUTION REVEAL PANEL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Below the answer choices add the Solution Panel:

DEFAULT STATE (hidden):
  [📖 Show Solution]  ← single button

ON CLICK — animate panel sliding down:
┌─────────────────────────────────────────────┐
│ 📖 SOLUTION                    [Hide ▲]     │
│ ─────────────────────────────────────────── │
│                                             │
│ STEP 1: Set up the problem                  │
│ Since ABCD is a rectangle, we know that     │
│ $AB = 2\sqrt{3}$ and $BC = 4$...            │
│                                             │
│ STEP 2: Apply the formula                   │
│ $$\text{Area} = \frac{1}{2} \times base     │
│ \times height$$                             │
│ $$= \frac{1}{2} \times 2\sqrt{3} \times 4$$│
│                                             │
│ STEP 3: Simplify                            │
│ $$= 4\sqrt{3}$$                             │
│                                             │
│ ✅ ANSWER: (A) $4\sqrt{3}$                  │
│                                             │
│ 💡 KEY INSIGHT:                             │
│ The diagonal of a rectangle divides it      │
│ into two equal triangles, each with half    │
│ the rectangle's area.                       │
└─────────────────────────────────────────────┘

SOLUTION PARSING:
The solution text from the PDF may be unstructured.
Use Claude API to reformat it into clean steps:

System prompt:
---
You are formatting an AMC math solution for display.
Take the raw solution text and restructure it into
clear numbered steps. Each step should have:
- A short title (3-5 words)
- 1-3 sentences of explanation
- The key math expression in LaTeX

Also identify the single KEY INSIGHT — the core
concept or trick that unlocks this problem.

Return ONLY valid JSON:
{
  "steps": [
    {
      "number": 1,
      "title": "Set up the equation",
      "explanation": "Since ABCD is a rectangle...",
      "math": "AB = 2\\sqrt{3}, BC = 4"
    }
  ],
  "final_answer": "A",
  "final_value": "4\\sqrt{3}",
  "key_insight": "The diagonal divides the rectangle 
                  into two congruent triangles"
}
---

Cache the formatted solution in the problem JSON
so Claude API is only called once per problem.

SOLUTION ANIMATIONS:
- Panel slides down smoothly (300ms ease-out)
- Steps appear one at a time with stagger delay
  (each step fades in 150ms after previous)
- Final answer pulses green on appearance
- Key insight box has subtle highlight background

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 4 — PROBLEM TIMER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Add a timer to Problem View using useEffect:

BEHAVIOR:
- Starts automatically when problem loads
- Counts up from 0:00
- Displays as MM:SS in top right of problem header
- Color coding:
  ⬜ White:  0:00 – 2:59  (on pace)
  🟡 Yellow: 3:00 – 4:59  (getting slow)
  🔴 Red:    5:00+         (over AMC pace)
- Pauses automatically when solution is revealed
- Stops and records final time on answer submit
- Show tooltip on hover: 
  "AMC pace = 2.5 min per problem"

TIMER COMPONENT: components/ProblemTimer.tsx
  - Accept onTimeUpdate callback prop
  - Expose pause() and stop() methods via useRef
  - Return elapsed seconds for progress logging

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 5 — NAVIGATION BETWEEN PROBLEMS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Add previous/next navigation to Problem View:

- [← Previous] and [Next →] buttons in header
- Navigate through currently filtered problem set
  (respects active filters from browser page)
- Show problem counter: "Problem 14 of 47"
- Keyboard shortcuts: ← and → arrow keys
- Preserve filter context when navigating 
  (don't reset to full list on each problem)
- On last problem show: 
  "🎉 You've completed this set! 
   [Browse More Problems]"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 6 — INTEGRATION TEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After building, verify these work correctly:

1. Open any problem → confirm all math renders 
   without [object Object] or raw LaTeX showing
2. Select answer (A) → submit → verify 
   correct/incorrect state displays properly
3. Click Show Solution → verify panel animates 
   down and all steps render with KaTeX
4. Verify timer starts, turns yellow at 3:00,
   red at 5:00, and pauses when solution opens
5. Click Next → verify moves to next problem
   and timer resets to 0:00
6. Test with a problem containing display math 
   ($$...$$) → verify it renders centered
7. Test with a problem containing an image → 
   verify has_image flag shows placeholder:
   "[Diagram — refer to original PDF, Page X]"
8. Verify solution is cached after first load
   (second open should not call Claude API again)




----------------------------------------------

Prompt 5 - Problem Morpher (Session 4)

The dashboard is working with problems and solutions 
displaying correctly. Now add the Problem Morpher feature.

WHAT IT DOES:
Given an original AMC problem, the morpher:
1. Identifies the numerical/variable parameters in the problem
2. Swaps them with new values that keep the problem valid
3. Recomputes the full step-by-step solution
4. Displays the morphed problem + solution in the same 
   dashboard UI

BACKEND — create lib/morpher.ts:

Call the Anthropic API (claude-sonnet-4-20250514) 
with this system prompt:

---
You are an expert AMC 10 math competition problem writer. 
Given an original AMC problem, your job is to:

1. Identify all numerical parameters that can be changed
   (counts, dimensions, rates, values, probabilities, etc.)
2. Replace them with new values that:
   - Keep the problem mathematically valid and solvable
   - Preserve the same solution method and concept
   - Result in a clean, non-trivial answer
   - Match the original difficulty level
3. Rewrite the full problem with new parameters
4. Solve the new problem step-by-step showing all work
5. State the final answer clearly

Return ONLY valid JSON in this exact format:
{
  "morphed_problem": "Full problem text with new parameters",
  "answer_choices": {
    "A": "...", "B": "...", "C": "...", "D": "...", "E": "..."
  },
  "correct_answer": "B",
  "solution": {
    "steps": [
      { "step": 1, "explanation": "...", "math": "LaTeX expression" },
      { "step": 2, "explanation": "...", "math": "LaTeX expression" }
    ],
    "final_answer": "...",
    "key_insight": "One sentence describing the core concept tested"
  },
  "what_changed": "Brief description of what parameters were altered"
}
---

The user prompt should be:
"Here is the original AMC problem:

Problem: {problem_text}
Answer Choices: {answer_choices}
Original Solution: {solution_text}

Morph this problem by changing the parameters. 
Keep the same mathematical concept and difficulty."

FRONTEND — update the Problem View:

Add a [🔀 Morph This Problem] button that:
1. Shows a loading spinner while Claude generates
2. Displays the morphed problem in a side-by-side 
   or tabbed view next to the original
3. Has a [Show Morphed Solution] button (hidden by default)
4. When solution is shown, render each step with:
   - Step number and explanation text
   - Math expression rendered via KaTeX
   - Final answer highlighted
5. Shows a "What Changed" badge explaining the alteration
6. Has a [🔀 Morph Again] button to generate another variant
7. Has a [↩ Back to Original] button

DIFFICULTY VARIANTS — add 3 morph modes:
- [Easier] — simpler numbers, smaller values
- [Same Level] — equivalent difficulty, different numbers  
- [Harder] — more complex parameters, messier arithmetic

Pass the mode to the API call as an additional 
instruction in the prompt.

ERROR HANDLING:
- If Claude returns invalid JSON, retry once automatically
- If the morphed problem is identical to original, 
  retry automatically
- Show a friendly error if morph fails after 2 attempts

Make sure KaTeX renders correctly in both the 
morphed problem text and each solution step.

-----------------------------

Bonus Prompt - Morpher Test Prompt

Test the morpher with this sample AMC problem:

Problem: "A box contains 3 red balls and 5 blue balls. 
Two balls are drawn at random without replacement. 
What is the probability that both balls are red?"

Answer Choices: 
A) 1/8  B) 3/28  C) 3/14  D) 1/4  E) 3/8
Correct Answer: B
Solution: "P = C(3,2)/C(8,2) = 3/28"

Run the morpher in all 3 modes (Easier, Same Level, Harder)
and print the JSON output for each. Verify the 
solutions are mathematically correct.

------------------------------------

Prompt 6 - Progress Tracker

The Problem Morpher is working. Now add a Progress 
Tracking system so the student can monitor their 
performance over time.

WHAT IT TRACKS:
- Every problem attempted (original + morphed)
- Answer selected and whether it was correct
- Time spent on each problem
- Hints or solutions viewed (penalizes score)
- Performance by topic and difficulty over time

DATA SCHEMA — create lib/progress.ts:

Store progress in data/progress/progress.json:

{
  "student": {
    "name": "Student Name",
    "started": "2024-01-15",
    "target_exam_date": "2025-11-08"
  },
  "sessions": [
    {
      "session_id": "uuid",
      "date": "2024-01-15",
      "duration_minutes": 45,
      "problems_attempted": [
        {
          "problem_id": "2023-AMC10A-Q14",
          "is_morphed": false,
          "topic": "Geometry",
          "difficulty": "medium",
          "time_spent_seconds": 180,
          "answer_selected": "C",
          "correct_answer": "C",
          "is_correct": true,
          "hints_viewed": 0,
          "solution_viewed": false,
          "score_value": 6
        }
      ]
    }
  ],
  "topic_stats": {
    "Geometry": {
      "attempted": 24,
      "correct": 18,
      "accuracy": 0.75,
      "avg_time_seconds": 145,
      "trend": "improving"
    }
  }
}

SCORING SYSTEM:
- Correct answer, no hints, no solution viewed: 6 pts
- Correct answer, hint viewed: 4 pts
- Correct answer, solution viewed: 1 pt
- Wrong answer: 0 pts
- AMC actual scoring: +6 correct, 0 wrong (no penalty)
  show both the training score and AMC-equivalent score

BACKEND — create these API routes:

1. POST /api/progress/log
   - Logs a single problem attempt
   - Updates topic_stats automatically
   - Calculates running accuracy per topic

2. GET /api/progress/summary
   - Returns full progress summary
   - Includes weak topics (accuracy < 60%)
   - Includes strong topics (accuracy > 80%)
   - Estimates AMC score based on recent performance

3. GET /api/progress/recommendations
   - Calls Claude API to analyze progress data
   - Returns personalized study recommendations

Use this Claude prompt for recommendations:
---
You are an AMC 10 math coach analyzing a student's 
practice data. Given this performance summary:

{progress_summary}

Provide specific, actionable recommendations:
1. Top 2 weak topics to focus on this week
2. Specific problem types to drill within each topic
3. Time management advice based on their avg solve times
4. Encouragement based on their improvement trend

Keep it concise, specific, and motivating.
Return as JSON:
{
  "weak_topics": [...],
  "drill_recommendations": [...],
  "time_management_tip": "...",
  "encouragement": "...",
  "predicted_amc_score": 90
}
---

FRONTEND — add a Progress Dashboard page /progress:

1. HEADER STATS BAR:
   ┌──────────┬──────────┬──────────┬──────────┐
   │ Problems │ Overall  │ Est. AMC │  Study   │
   │ Attempted│ Accuracy │  Score   │  Streak  │
   │   142    │  71%     │  96/150  │  7 days  │
   └──────────┴──────────┴──────────┴──────────┘

2. TOPIC PERFORMANCE CHART:
   - Horizontal bar chart per topic
   - Shows accuracy % with color coding:
     Red < 60%, Yellow 60-80%, Green > 80%
   - Shows # of problems attempted per topic
   - Shows trend arrow (↑ improving, → stable, ↓ declining)
   Use recharts library for the chart

3. RECENT ACTIVITY FEED:
   - Last 10 problems attempted
   - Shows: problem ID, topic, result (✅/❌), time, score
   - Click to revisit any past problem

4. WEAKNESS RADAR CHART:
   - Spider/radar chart across all topics
   - Shows current level vs target level
   - Use recharts RadarChart component

5. AI COACH PANEL:
   - [Get Study Recommendations] button
   - Calls /api/progress/recommendations
   - Displays Claude's personalized advice in a 
     clean card with sections for each recommendation
   - Refreshes weekly automatically

6. PROBLEM TIMER:
   - Add a visible countdown timer to the Problem View
   - Starts when problem loads
   - Pauses when solution is revealed
   - Stops and logs time when answer is submitted
   - Shows color warning when > 3 minutes (AMC pace)

7. ANSWER SUBMISSION FLOW:
   Update Problem View so that:
   - Student clicks an answer choice (A-E) to select it
   - Clicks [Submit Answer] to confirm
   - Immediately shows ✅ correct or ❌ wrong + correct answer
   - Then reveals [Show Solution] button
   - Logs the attempt automatically to progress.json
   - Shows points earned for this attempt

NAVIGATION:
- Add a top navbar with:
  [📚 Problems] [📊 Progress] [⚙️ Settings]
- Show a small streak counter in the navbar
- Highlight weak topics with a 🔴 badge in the 
  sidebar filters on the Problems page

SETTINGS PAGE /settings — simple form:
- Student name
- Target exam date (auto-calculates days remaining)
- Daily problem goal (default: 10)
- Show/hide timer
- Reset progress button (with confirmation)

----------------------------

Bonus Prompt - Session Wrap-up Test Prompt (run to verify everything connects)

Test the full progress tracking flow end to end:

1. Simulate attempting 5 problems with mixed results:
   - Q1 Algebra: correct, 90 seconds, no hints
   - Q7 Geometry: wrong, 240 seconds, hint viewed
   - Q12 Number Theory: correct, 150 seconds, solution viewed
   - Q18 Probability: wrong, 300 seconds, no hints
   - Q23 Combinatorics: correct, 200 seconds, no hints

2. Log all 5 to progress.json via the API
3. Verify topic_stats updates correctly
4. Call the recommendations endpoint and print 
   Claude's coaching advice
5. Confirm the Progress Dashboard renders all 
   5 attempts in the activity feed with correct scores

------------------------

Prompt 7 - Hint System & Final Polish

The Progress Tracker is working. This is the final 
session to add a smart Hint System and polish the 
entire app to production quality.

WHAT WE'RE ADDING:
1. AI-powered progressive hint system
2. Keyboard shortcuts for speed
3. Mobile responsive layout
4. Export/print features
5. Final UI polish across all pages

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 1 — PROGRESSIVE HINT SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Create lib/hints.ts with 3 progressive hint levels:

HINT LEVEL 1 — Nudge (free, no score penalty):
  "What concept or formula does this problem 
   likely use? Don't solve, just point the 
   student in the right direction in 1-2 sentences."

HINT LEVEL 2 — Setup (small penalty, -1pt):
  "Show the first step only — how to set up 
   the problem. Stop before any calculation. 
   Use LaTeX for any math expressions."

HINT LEVEL 3 — Worked Example (larger penalty, -2pts):
  "Solve 40% of the problem showing key steps, 
   then stop. Leave the final calculation for 
   the student. Use LaTeX."

Call Claude API for each level with this system prompt:
---
You are a patient AMC 10 math tutor. Your job is 
to give hints that guide without giving away answers.
Never state the final answer. Never skip steps.
Speak directly to the student ("you", "try", "notice").
Format all math expressions in LaTeX.
Keep hints concise — max 4 sentences per level.
---

User prompt for each level:
"Problem: {problem_text}
Correct Answer: {correct_answer}
Full Solution: {solution_text}

Give a Level {1|2|3} hint for this problem.
Level 1 = concept nudge only
Level 2 = problem setup only  
Level 3 = partial worked solution (40% only)"

HINT UI in Problem View:
- Replace single [Show Hint] with hint progression:

  [💡 Hint 1 — Free]
     ↓ (after viewing)
  [💡 Hint 2 — -1pt]  
     ↓ (after viewing)  
  [💡 Hint 3 — -2pts]
     ↓ (after viewing)
  [📖 Show Full Solution — +1pt only]

- Each hint expands inline below the problem
- Show score impact warning before revealing:
  "Viewing this hint will reduce your max 
   score for this problem to 4pts. Continue?"
- Hints are cached after first load (don't 
  re-call API if student revisits same problem)
- Log hint usage to progress tracker

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 2 — SIMILAR PROBLEMS FINDER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Add a [Find Similar Problems] button to Problem View:

Call Claude API with this prompt:
---
Given this AMC problem on {topic}:
{problem_text}

From this list of available problems:
{list_of_all_problem_ids_and_topics}

Identify the 3 most similar problems based on:
- Same core concept or technique
- Similar difficulty level
- Complementary skill (fills a gap)

Return JSON:
{
  "similar": [
    {
      "problem_id": "2022-AMC10A-Q11",
      "reason": "Same technique: complementary counting",
      "similarity": "high"
    }
  ]
}
---

Display results as clickable cards below the problem:
┌─────────────────────────────────┐
│ 📎 Similar Problems             │
│ ─────────────────────────────── │
│ 2022-AMC10A-Q11  Combinatorics  │
│ "Same technique: complementary  │
│  counting"              [Open]  │
│                                 │
│ 2021-AMC10B-Q8   Combinatorics  │
│ "Simpler version — good warmup" │
│                          [Open] │
└─────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 3 — KEYBOARD SHORTCUTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Add global keyboard shortcuts via useEffect hook:

Problem Browser:
  [N]        → Next problem
  [P]        → Previous problem
  [F]        → Toggle filters sidebar
  [/]        → Focus search bar

Problem View:
  [A][B][C][D][E] → Select answer choice
  [Enter]    → Submit selected answer
  [H]        → Show next hint level
  [S]        → Show solution (with confirmation)
  [M]        → Morph this problem
  [Esc]      → Back to problem browser
  [←] [→]   → Previous / Next problem

Progress Page:
  [R]        → Refresh recommendations
  [E]        → Export progress report

Show a keyboard shortcut cheatsheet modal:
  [?]        → Toggle shortcuts overlay

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 4 — EXPORT & PRINT FEATURES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Add export options to the Progress page:

1. EXPORT PROGRESS REPORT (PDF):
   Generate a clean PDF summary containing:
   - Student name + date range
   - Overall stats (accuracy, est. AMC score)
   - Topic performance table
   - Weak areas and recommendations
   - Last 20 problems attempted with results
   Use: jsPDF + html2canvas libraries

2. EXPORT PROBLEM SET:
   Let coach/teacher export a custom problem set:
   - Select topic + difficulty + count
   - Generates a clean printable PDF
   - Problems only (no answers) for use as worksheet
   - Separate answer key page at the end
   - Proper AMC formatting with LaTeX rendered

3. SHARE MORPHED PROBLEM:
   On morphed problem view add [📋 Copy Problem] 
   button that copies the morphed problem text 
   and solution to clipboard in clean markdown format

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 5 — FINAL UI POLISH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Polish these elements across the entire app:

LOADING STATES:
- Skeleton loaders for problem cards (not spinners)
- Streaming text effect for Claude AI responses
  (use ReadableStream from fetch API)
- Progress bar in navbar when navigating

EMPTY STATES:
- No problems match filters → 
  "No problems found. Try adjusting your filters."
  with [Clear Filters] button
- No progress yet → 
  "Start practicing to see your progress here!"
  with [Browse Problems] button

ERROR STATES:
- Claude API fails → friendly message +
  [Try Again] button, never show raw errors
- PDF parse fails → list which problems 
  failed with line numbers for debugging

ANIMATIONS (use Framer Motion):
- Problem cards fade in on load (staggered)
- Hint panels slide down smoothly
- Correct answer → green flash animation
- Wrong answer → red shake animation
- Score points → float up and fade (+6pts ✨)

TYPOGRAPHY & READABILITY:
- Math-heavy content needs generous line height
- Problem text: text-lg, line-height: 1.8
- Solution steps: monospace for calculations
- Use Inter for UI, use system-ui for math prose

DARK MODE POLISH:
- Ensure KaTeX renders correctly in dark mode
- Add .katex { color: inherit } to globals.css
- Test all chart colors in dark mode
- Syntax highlight solution steps with 
  subtle background: bg-slate-800/50

FINAL NAVBAR:
┌────────────────────────────────────────────────┐
│ 🧮 AMC Trainer  [Problems] [Progress] [Settings]│
│                              🔥7  ⭐96pts  👤   │
└────────────────────────────────────────────────┘
  - 🔥 = current streak
  - ⭐ = today's points earned
  - 👤 = student name dropdown

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 6 — FINAL INTEGRATION TEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After building all parts above, run this full 
end-to-end test to verify everything works together:

1. Load app → verify all problems display with 
   correct KaTeX rendering
2. Filter by Topic: Geometry, Difficulty: Hard →
   verify correct problems appear
3. Open a problem → start timer → select wrong 
   answer → submit → verify ❌ and 0pts logged
4. View Hint 1 → verify Claude response streams in
5. View Hint 2 → verify score warning appears first
6. Submit correct answer → verify ✅ and 4pts logged
   (penalized for hints)
7. Click Morph → Same Level → verify new problem 
   and solution render with KaTeX
8. Click Find Similar → verify 3 related problems appear
9. Navigate to Progress page → verify all stats 
   updated correctly
10. Click Get Recommendations → verify Claude 
    coaching advice appears
11. Export Progress Report → verify PDF downloads
12. Test keyboard shortcuts: A, Enter, H, M, Esc
13. Test on mobile viewport (375px) → verify 
    responsive layout holds

Fix any issues found before declaring done.