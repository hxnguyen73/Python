'use client';

import { useState } from 'react';
import MathText from './MathText';
import { cn } from '@/lib/utils';

interface Props {
  solutionText: string | null;
  correctAnswer: string | null;
  onReveal?: () => void;
}

export default function SolutionPanel({ solutionText, correctAnswer, onReveal }: Props) {
  const [isOpen, setIsOpen] = useState(false);

  const handleShow = () => {
    setIsOpen(true);
    onReveal?.();
  };

  const handleHide = () => {
    setIsOpen(false);
  };

  return (
    <div className="mt-4">
      {!isOpen && (
        <button
          onClick={handleShow}
          className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-sm font-medium text-zinc-200 transition-colors"
        >
          Show Solution
        </button>
      )}

      {/* Animated panel */}
      <div
        className={cn(
          'bg-zinc-800/50 border border-zinc-700 rounded-xl overflow-hidden transition-all duration-300 ease-out',
          isOpen ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0 border-0'
        )}
      >
        {isOpen && (
          <div className="p-6">
            {/* Panel header */}
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold text-zinc-100">Solution</h3>
              <button
                onClick={handleHide}
                className="text-xs text-zinc-400 hover:text-zinc-200 transition-colors flex items-center gap-1"
              >
                Hide ▲
              </button>
            </div>

            {/* Correct answer callout */}
            {correctAnswer && (
              <div className="mb-4 flex items-center gap-2 text-green-400 text-sm font-medium">
                <span>✓</span>
                <span>Answer: ({correctAnswer})</span>
              </div>
            )}

            {/* Solution text */}
            {solutionText ? (
              <div className="text-zinc-300 text-sm leading-relaxed">
                <MathText text={solutionText} />
              </div>
            ) : (
              <p className="text-zinc-500 text-sm italic">
                Solution not available for this problem.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
