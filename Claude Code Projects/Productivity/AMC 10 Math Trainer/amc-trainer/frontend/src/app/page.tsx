import { getAllProblems, filterProblems, getFilterOptions } from '@/lib/problems';
import type { FilterState } from '@/lib/types';
import FilterSidebar from '@/components/FilterSidebar';
import ProblemGrid from '@/components/ProblemGrid';

interface PageProps {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export default async function HomePage({ searchParams }: PageProps) {
  const params = await searchParams;

  // Parse filter params from URL
  const yearsParam = typeof params.years === 'string' ? params.years : '';
  const topicsParam = typeof params.topics === 'string' ? params.topics : '';
  const difficultyParam = typeof params.difficulty === 'string' ? params.difficulty : '';
  const examParam = typeof params.exam === 'string' ? params.exam : '';

  const filterState: FilterState = {
    years: yearsParam ? yearsParam.split(',').map(Number).filter(Boolean) : [],
    topics: topicsParam ? topicsParam.split(',').filter(Boolean) : [],
    difficulties: difficultyParam ? [difficultyParam] : [],
    exams: examParam ? [examParam] : [],
  };

  const allProblems = getAllProblems();
  const filteredProblems = filterProblems(allProblems, filterState);
  const options = getFilterOptions(allProblems);

  return (
    <div className="flex h-screen overflow-hidden bg-zinc-950">
      {/* Left sidebar — fixed 280px */}
      <div className="w-[280px] shrink-0 h-full overflow-y-auto">
        <FilterSidebar options={options} current={filterState} />
      </div>

      {/* Right scrollable content */}
      <div className="flex-1 overflow-y-auto">
        <ProblemGrid problems={filteredProblems} filterState={filterState} />
      </div>
    </div>
  );
}
