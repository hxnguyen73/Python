'use client';

import { useEffect, useRef, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import type { Problem } from '@/lib/types';
import type { ProblemTimerHandle } from '@/components/ProblemTimer';
import ProblemTimer from '@/components/ProblemTimer';
import MathText from '@/components/MathText';
import AnswerChoices from '@/components/AnswerChoices';
import SolutionPanel from '@/components/SolutionPanel';
import { cn } from '@/lib/utils';

interface Props {
  problem: Problem;
  filterParams: string;
  prevId: string | null;
  nextId: string | null;
  currentIndex: number;
  totalCount: number;
}

function ProblemDiagram({ id }: { id: string }) {
  const [exists, setExists] = useState(true);
  const src = `/images/${id}.png`;

  if (!exists) {
    return (
      <div className="mb-6 px-4 py-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 text-sm">
        [Diagram — refer to original PDF]
      </div>
    );
  }

  return (
    <div className="mb-6">
      <Image
        src={src}
        alt={`Diagram for ${id}`}
        width={765}
        height={400}
        className="rounded-lg border border-zinc-700 bg-white max-w-full h-auto"
        onError={() => setExists(false)}
        unoptimized
      />
    </div>
  );
}

const difficultyConfig: Record<string, { label: string; classes: string }> = {
  easy: { label: 'Easy', classes: 'bg-green-500/15 text-green-400 border border-green-500/30' },
  medium: { label: 'Medium', classes: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30' },
  hard: { label: 'Hard', classes: 'bg-red-500/15 text-red-400 border border-red-500/30' },
};

export default function ProblemViewClient({
  problem,
  filterParams,
  prevId,
  nextId,
  currentIndex,
  totalCount,
}: Props) {
  const router = useRouter();
  const timerRef = useRef<ProblemTimerHandle>(null);
  const startTimeRef = useRef<number>(Date.now());

  const [submitted, setSubmitted] = useState(false);
  const [solutionViewed, setSolutionViewed] = useState(false);
  const [earnedPoints, setEarnedPoints] = useState<number | null>(null);

  const backHref = filterParams ? `/?${filterParams}` : '/';
  const prevHref = prevId ? `/problem/${prevId}${filterParams ? `?${filterParams}` : ''}` : null;
  const nextHref = nextId ? `/problem/${nextId}${filterParams ? `?${filterParams}` : ''}` : null;

  const diff = difficultyConfig[problem.difficulty] ?? {
    label: problem.difficulty,
    classes: 'bg-zinc-700/50 text-zinc-400 border border-zinc-600',
  };

  // Reset state when problem changes
  useEffect(() => {
    setSubmitted(false);
    setSolutionViewed(false);
    setEarnedPoints(null);
    startTimeRef.current = Date.now();
  }, [problem.id]);

  // Keyboard navigation
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === 'ArrowLeft' && prevHref) router.push(prevHref);
      else if (e.key === 'ArrowRight' && nextHref) router.push(nextHref);
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [prevHref, nextHref, router]);

  const handleAnswerSubmit = (answer: string, correct: boolean) => {
    setSubmitted(true);
    timerRef.current?.stop();

    const timeSpent = Math.round((Date.now() - startTimeRef.current) / 1000);
    const isCorrect = correct;
    const sv = solutionViewed;

    let score = 0;
    if (isCorrect) {
      if (sv) score = 1;
      else score = 6;
    }
    setEarnedPoints(score);

    fetch('/api/progress/log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        problem_id: problem.id,
        is_morphed: false,
        topic: problem.topic,
        difficulty: problem.difficulty,
        time_spent_seconds: timeSpent,
        answer_selected: answer,
        correct_answer: problem.correct_answer ?? '',
        is_correct: isCorrect,
        hints_viewed: 0,
        solution_viewed: sv,
      }),
    }).catch(() => {});
  };

  const handleRevealSolution = () => {
    timerRef.current?.pause();
  };

  const handleSolutionViewed = () => {
    setSolutionViewed(true);
    if (submitted && earnedPoints !== null) {
      // downgrade points if solution viewed after submit
      setEarnedPoints(1);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col">
      {/* ── Sticky header ── */}
      <header className="sticky top-0 z-10 bg-zinc-950 border-b border-zinc-800">
        {/* Main header row */}
        <div className="flex items-center gap-4 px-6 py-3">
          {/* Left: back + title */}
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <Link
              href={backHref}
              className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors shrink-0 flex items-center gap-1"
            >
              ← Back
            </Link>
            <span className="text-zinc-700">|</span>
            <span className="text-sm font-semibold text-zinc-100 truncate">
              {problem.year} {problem.exam} — Problem {problem.question_number}
            </span>
          </div>

          {/* Center: badges */}
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-400 border border-blue-500/30">
              {problem.topic}
            </span>
            <span className={cn('text-xs px-2 py-0.5 rounded-full', diff.classes)}>
              {diff.label}
            </span>
          </div>

          {/* Right: timer */}
          <div className="shrink-0 ml-2">
            <ProblemTimer ref={timerRef} />
          </div>
        </div>

        {/* Navigation row */}
        <div className="flex items-center justify-between px-6 py-2 border-t border-zinc-800/60 text-xs text-zinc-500">
          <div>
            {prevHref ? (
              <Link href={prevHref} className="hover:text-zinc-300 transition-colors flex items-center gap-1">
                ← Previous
              </Link>
            ) : (
              <span className="opacity-40">← Previous</span>
            )}
          </div>
          <span>
            Problem {currentIndex + 1} of {totalCount}
          </span>
          <div>
            {nextHref ? (
              <Link href={nextHref} className="hover:text-zinc-300 transition-colors flex items-center gap-1">
                Next →
              </Link>
            ) : (
              <span className="opacity-40">Next →</span>
            )}
          </div>
        </div>
      </header>

      {/* ── Problem body ── */}
      <main className="max-w-3xl mx-auto w-full px-6 py-8 flex-1">
        {/* Problem text */}
        <div className="mb-8 text-zinc-100 text-base leading-relaxed">
          <MathText text={problem.problem_text} />
        </div>

        {/* Diagram image */}
        {problem.has_image && (
          <ProblemDiagram id={problem.id} />
        )}

        {/* Answer choices */}
        <AnswerChoices
          choices={problem.answer_choices}
          correctAnswer={problem.correct_answer}
          onSubmit={handleAnswerSubmit}
        />

        {/* Points earned */}
        {submitted && earnedPoints !== null && (
          <div className="mt-3 text-sm text-zinc-400">
            Points earned this attempt:{' '}
            <span className={cn(
              'font-bold',
              earnedPoints === 6 ? 'text-green-400' : earnedPoints >= 4 ? 'text-yellow-400' : earnedPoints === 1 ? 'text-orange-400' : 'text-red-400'
            )}>
              {earnedPoints} / 6
            </span>
            {solutionViewed && earnedPoints > 0 && (
              <span className="ml-2 text-zinc-500">(solution viewed)</span>
            )}
          </div>
        )}

        {/* Action buttons — only after submit */}
        {submitted && (
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              disabled
              title="Coming in Session 4"
              className="px-4 py-2 rounded-lg bg-zinc-800/50 border border-zinc-700/50 text-sm font-medium text-zinc-600 cursor-not-allowed"
            >
              🔀 Morph This Problem
            </button>
          </div>
        )}

        {/* Solution panel */}
        {submitted && (
          <SolutionPanel
            solutionText={problem.solution_text ?? null}
            correctAnswer={problem.correct_answer ?? null}
            onReveal={handleRevealSolution}
            onSolutionViewed={handleSolutionViewed}
          />
        )}
      </main>
    </div>
  );
}
