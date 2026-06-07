'use client';

import { useState } from 'react';
import MathText from './MathText';
import { cn } from '@/lib/utils';

interface Props {
  choices: Record<string, string>;
  correctAnswer: string | null;
  onSubmit: (answer: string, correct: boolean) => void;
}

const ANSWER_ORDER = ['A', 'B', 'C', 'D', 'E'];

export default function AnswerChoices({ choices, correctAnswer, onSubmit }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const handleSelect = (letter: string) => {
    if (submitted) return;
    setSelected(letter);
  };

  const handleSubmit = () => {
    if (!selected || submitted) return;
    const correct = selected === correctAnswer;
    setSubmitted(true);
    onSubmit(selected, correct);
  };

  const isCorrect = submitted && selected === correctAnswer;
  const isWrong = submitted && selected !== correctAnswer;

  function cardClass(letter: string): string {
    if (!submitted) {
      return selected === letter
        ? 'border-blue-500 bg-blue-500/10 text-zinc-100'
        : 'border-zinc-700 bg-zinc-800/50 text-zinc-300 hover:border-zinc-500 hover:bg-zinc-700/50';
    }
    // submitted
    if (letter === correctAnswer) {
      return 'border-green-500 bg-green-500/10 text-green-400';
    }
    if (letter === selected && selected !== correctAnswer) {
      return 'border-red-500 bg-red-500/10 text-red-400';
    }
    return 'border-zinc-700 bg-zinc-800/30 text-zinc-500';
  }

  return (
    <div className="space-y-3">
      {/* Choice cards */}
      <div className="space-y-2">
        {ANSWER_ORDER.filter((l) => choices[l] !== undefined).map((letter) => (
          <button
            key={letter}
            onClick={() => handleSelect(letter)}
            disabled={submitted}
            className={cn(
              'w-full text-left rounded-lg border-2 px-4 py-3 transition-colors flex items-start gap-3',
              cardClass(letter),
              !submitted && 'cursor-pointer',
              submitted && 'cursor-default'
            )}
          >
            <span className="font-bold text-sm shrink-0 mt-0.5">({letter})</span>
            <span className="text-sm leading-relaxed">
              <MathText text={choices[letter]} />
            </span>
          </button>
        ))}
      </div>

      {/* Submit button */}
      <button
        onClick={handleSubmit}
        disabled={!selected || submitted}
        className={cn(
          'mt-2 px-6 py-2.5 rounded-lg text-sm font-semibold transition-colors',
          selected && !submitted
            ? 'bg-blue-600 hover:bg-blue-500 text-white'
            : 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
        )}
      >
        Submit Answer
      </button>

      {/* Result message */}
      {submitted && (
        <div
          className={cn(
            'mt-2 text-sm font-medium flex items-center gap-2',
            isCorrect ? 'text-green-400' : 'text-red-400'
          )}
        >
          {isCorrect ? (
            <span>✓ Correct! +6 pts</span>
          ) : (
            <span>✗ Incorrect. The answer was ({correctAnswer})</span>
          )}
        </div>
      )}
    </div>
  );
}
