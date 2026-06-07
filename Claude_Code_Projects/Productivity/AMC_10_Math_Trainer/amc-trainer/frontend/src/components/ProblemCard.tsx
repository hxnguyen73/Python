'use client';

import Link from 'next/link';
import { Camera } from 'lucide-react';
import type { Problem } from '@/lib/types';
import { truncateText } from '@/lib/utils-text';
import { cn } from '@/lib/utils';

interface Props {
  problem: Problem;
  filterParams: string;
}

const difficultyConfig: Record<string, { label: string; classes: string }> = {
  easy: { label: 'Easy', classes: 'bg-green-500/15 text-green-400 border border-green-500/30' },
  medium: { label: 'Medium', classes: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30' },
  hard: { label: 'Hard', classes: 'bg-red-500/15 text-red-400 border border-red-500/30' },
};

export default function ProblemCard({ problem, filterParams }: Props) {
  const href = `/problem/${problem.id}${filterParams ? `?${filterParams}` : ''}`;
  const preview = truncateText(problem.problem_text, 80);
  const diff = difficultyConfig[problem.difficulty] ?? {
    label: problem.difficulty,
    classes: 'bg-zinc-700/50 text-zinc-400 border border-zinc-600',
  };

  return (
    <Link
      href={href}
      className={cn(
        'block bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 rounded-xl p-4',
        'transition-transform hover:scale-[1.02] duration-150'
      )}
    >
      {/* Top row */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-bold text-zinc-100">Q{problem.question_number}</span>
        <span className="text-xs text-zinc-500">
          {problem.year} {problem.exam}
        </span>
      </div>

      {/* Badge row */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-400 border border-blue-500/30">
          {problem.topic}
        </span>
        <span className={cn('text-xs px-2 py-0.5 rounded-full', diff.classes)}>
          {diff.label}
        </span>
      </div>

      {/* Problem text preview */}
      <p className="text-sm text-zinc-300 line-clamp-2 leading-relaxed">{preview}</p>

      {/* Footer */}
      {problem.has_image && (
        <div className="mt-3 flex items-center gap-1 text-xs text-zinc-500">
          <Camera className="w-3 h-3" />
          <span>Has diagram</span>
        </div>
      )}
    </Link>
  );
}
