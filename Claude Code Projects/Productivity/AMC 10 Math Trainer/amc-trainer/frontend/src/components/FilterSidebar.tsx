'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useCallback } from 'react';
import type { FilterOptions, FilterState } from '@/lib/types';
import { cn } from '@/lib/utils';

interface Props {
  options: FilterOptions;
  current: FilterState;
}

export default function FilterSidebar({ options, current }: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const buildParams = useCallback(
    (overrides: Partial<{ years: number[]; topics: string[]; difficulty: string; exam: string }>) => {
      const p = new URLSearchParams(searchParams.toString());

      if ('years' in overrides) {
        if (overrides.years && overrides.years.length > 0) {
          p.set('years', overrides.years.join(','));
        } else {
          p.delete('years');
        }
      }
      if ('topics' in overrides) {
        if (overrides.topics && overrides.topics.length > 0) {
          p.set('topics', overrides.topics.join(','));
        } else {
          p.delete('topics');
        }
      }
      if ('difficulty' in overrides) {
        if (overrides.difficulty) {
          p.set('difficulty', overrides.difficulty);
        } else {
          p.delete('difficulty');
        }
      }
      if ('exam' in overrides) {
        if (overrides.exam) {
          p.set('exam', overrides.exam);
        } else {
          p.delete('exam');
        }
      }

      return p.toString();
    },
    [searchParams]
  );

  const toggleYear = (year: number) => {
    const next = current.years.includes(year)
      ? current.years.filter((y) => y !== year)
      : [...current.years, year];
    router.push(`/?${buildParams({ years: next })}`);
  };

  const toggleTopic = (topic: string) => {
    const next = current.topics.includes(topic)
      ? current.topics.filter((t) => t !== topic)
      : [...current.topics, topic];
    router.push(`/?${buildParams({ topics: next })}`);
  };

  const setDifficulty = (diff: string) => {
    const next = current.difficulties.includes(diff) ? '' : diff;
    router.push(`/?${buildParams({ difficulty: next })}`);
  };

  const setExam = (exam: string) => {
    const next = current.exams.includes(exam) ? '' : exam;
    router.push(`/?${buildParams({ exam: next })}`);
  };

  const clearFilters = () => {
    router.push('/');
  };

  const hasAnyFilter =
    current.years.length > 0 ||
    current.topics.length > 0 ||
    current.difficulties.length > 0 ||
    current.exams.length > 0;

  // Group years by decade if more than 20
  const groupedYears =
    options.years.length > 20
      ? options.years.reduce<Record<string, number[]>>((acc, y) => {
          const decade = `${Math.floor(y / 10) * 10}s`;
          (acc[decade] ??= []).push(y);
          return acc;
        }, {})
      : null;

  return (
    <aside className="h-full bg-zinc-900 border-r border-zinc-800 flex flex-col">
      <div className="px-4 py-5 border-b border-zinc-800">
        <h2 className="text-sm font-semibold text-zinc-100 uppercase tracking-wider">Filters</h2>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
        {/* Year filter */}
        <section>
          <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">Year</h3>
          <div className="space-y-1 max-h-52 overflow-y-auto pr-1">
            {groupedYears
              ? Object.entries(groupedYears).map(([decade, years]) => (
                  <div key={decade}>
                    <p className="text-xs text-zinc-500 mt-2 mb-1">{decade}</p>
                    {years.map((year) => (
                      <YearCheckbox
                        key={year}
                        year={year}
                        checked={current.years.includes(year)}
                        onChange={() => toggleYear(year)}
                      />
                    ))}
                  </div>
                ))
              : options.years.map((year) => (
                  <YearCheckbox
                    key={year}
                    year={year}
                    checked={current.years.includes(year)}
                    onChange={() => toggleYear(year)}
                  />
                ))}
          </div>
        </section>

        {/* Topic filter */}
        <section>
          <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">Topic</h3>
          <div className="space-y-1">
            {options.topics.map((topic) => (
              <label
                key={topic}
                className="flex items-center gap-2 cursor-pointer group"
              >
                <input
                  type="checkbox"
                  className="accent-blue-500 w-3.5 h-3.5 rounded shrink-0"
                  checked={current.topics.includes(topic)}
                  onChange={() => toggleTopic(topic)}
                />
                <span
                  className={cn(
                    'text-sm transition-colors',
                    current.topics.includes(topic) ? 'text-blue-400' : 'text-zinc-400 group-hover:text-zinc-200'
                  )}
                >
                  {topic}
                </span>
              </label>
            ))}
          </div>
        </section>

        {/* Difficulty filter */}
        <section>
          <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">Difficulty</h3>
          <div className="space-y-1">
            {options.difficulties.map((diff) => (
              <label key={diff} className="flex items-center gap-2 cursor-pointer group">
                <input
                  type="radio"
                  name="difficulty"
                  className="accent-blue-500 w-3.5 h-3.5 shrink-0"
                  checked={current.difficulties.includes(diff)}
                  onChange={() => setDifficulty(diff)}
                />
                <span
                  className={cn(
                    'text-sm capitalize transition-colors',
                    current.difficulties.includes(diff)
                      ? 'text-blue-400'
                      : 'text-zinc-400 group-hover:text-zinc-200'
                  )}
                >
                  {diff}
                </span>
              </label>
            ))}
          </div>
        </section>

        {/* Exam filter */}
        <section>
          <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">Exam</h3>
          <div className="space-y-1">
            {options.exams.map((exam) => (
              <label key={exam} className="flex items-center gap-2 cursor-pointer group">
                <input
                  type="radio"
                  name="exam"
                  className="accent-blue-500 w-3.5 h-3.5 shrink-0"
                  checked={current.exams.includes(exam)}
                  onChange={() => setExam(exam)}
                />
                <span
                  className={cn(
                    'text-sm transition-colors',
                    current.exams.includes(exam)
                      ? 'text-blue-400'
                      : 'text-zinc-400 group-hover:text-zinc-200'
                  )}
                >
                  {exam}
                </span>
              </label>
            ))}
          </div>
        </section>
      </div>

      {/* Clear filters */}
      <div className="px-4 py-4 border-t border-zinc-800">
        <button
          onClick={clearFilters}
          disabled={!hasAnyFilter}
          className={cn(
            'w-full text-sm rounded-lg px-3 py-2 transition-colors font-medium',
            hasAnyFilter
              ? 'bg-zinc-800 text-zinc-200 hover:bg-zinc-700 hover:text-white'
              : 'bg-zinc-800/40 text-zinc-600 cursor-not-allowed'
          )}
        >
          Clear filters
        </button>
      </div>
    </aside>
  );
}

function YearCheckbox({
  year,
  checked,
  onChange,
}: {
  year: number;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <label className="flex items-center gap-2 cursor-pointer group">
      <input
        type="checkbox"
        className="accent-blue-500 w-3.5 h-3.5 rounded shrink-0"
        checked={checked}
        onChange={onChange}
      />
      <span
        className={cn(
          'text-sm transition-colors',
          checked ? 'text-blue-400' : 'text-zinc-400 group-hover:text-zinc-200'
        )}
      >
        {year}
      </span>
    </label>
  );
}
