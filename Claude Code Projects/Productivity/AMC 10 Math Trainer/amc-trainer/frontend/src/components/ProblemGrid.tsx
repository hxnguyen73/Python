'use client';

import Link from 'next/link';
import type { Problem, FilterState } from '@/lib/types';
import ProblemCard from './ProblemCard';

interface Props {
  problems: Problem[];
  filterState: FilterState;
}

function buildFilterParams(filterState: FilterState): string {
  const p = new URLSearchParams();
  if (filterState.years.length > 0) p.set('years', filterState.years.join(','));
  if (filterState.topics.length > 0) p.set('topics', filterState.topics.join(','));
  if (filterState.difficulties.length > 0) p.set('difficulty', filterState.difficulties[0]);
  if (filterState.exams.length > 0) p.set('exam', filterState.exams[0]);
  return p.toString();
}

export default function ProblemGrid({ problems, filterState }: Props) {
  const filterParams = buildFilterParams(filterState);

  return (
    <div className="px-6 py-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-zinc-100">AMC 10 Problems</h1>
        <p className="text-sm text-zinc-500 mt-1">{problems.length} problems</p>
      </div>

      {/* Empty state */}
      {problems.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <p className="text-zinc-400 text-lg mb-3">No problems match your filters.</p>
          <p className="text-zinc-500 text-sm mb-6">Try adjusting the filters.</p>
          <Link
            href="/"
            className="text-sm text-blue-400 hover:text-blue-300 underline underline-offset-2 transition-colors"
          >
            Clear all filters
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {problems.map((problem) => (
            <ProblemCard
              key={problem.id}
              problem={problem}
              filterParams={filterParams}
            />
          ))}
        </div>
      )}
    </div>
  );
}
