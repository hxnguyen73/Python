import { notFound } from 'next/navigation';
import { getAllProblems, getProblemById, filterProblems } from '@/lib/problems';
import type { FilterState } from '@/lib/types';
import ProblemViewClient from './ProblemViewClient';

interface PageProps {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export default async function ProblemPage({ params, searchParams }: PageProps) {
  const { id } = await params;
  const sp = await searchParams;

  const problem = getProblemById(id);
  if (!problem) notFound();

  // Parse filter state from searchParams (same logic as home page)
  const yearsParam = typeof sp.years === 'string' ? sp.years : '';
  const topicsParam = typeof sp.topics === 'string' ? sp.topics : '';
  const difficultyParam = typeof sp.difficulty === 'string' ? sp.difficulty : '';
  const examParam = typeof sp.exam === 'string' ? sp.exam : '';

  const filterState: FilterState = {
    years: yearsParam ? yearsParam.split(',').map(Number).filter(Boolean) : [],
    topics: topicsParam ? topicsParam.split(',').filter(Boolean) : [],
    difficulties: difficultyParam ? [difficultyParam] : [],
    exams: examParam ? [examParam] : [],
  };

  const allProblems = getAllProblems();
  const filteredProblems = filterProblems(allProblems, filterState);

  const currentIndex = filteredProblems.findIndex((p) => p.id === id);
  const prevId = currentIndex > 0 ? filteredProblems[currentIndex - 1].id : null;
  const nextId = currentIndex < filteredProblems.length - 1 ? filteredProblems[currentIndex + 1].id : null;

  // Build filter params string to carry forward
  const filterParamParts = new URLSearchParams();
  if (filterState.years.length > 0) filterParamParts.set('years', filterState.years.join(','));
  if (filterState.topics.length > 0) filterParamParts.set('topics', filterState.topics.join(','));
  if (filterState.difficulties.length > 0) filterParamParts.set('difficulty', filterState.difficulties[0]);
  if (filterState.exams.length > 0) filterParamParts.set('exam', filterState.exams[0]);
  const filterParams = filterParamParts.toString();

  return (
    <ProblemViewClient
      problem={problem}
      filterParams={filterParams}
      prevId={prevId}
      nextId={nextId}
      currentIndex={currentIndex}
      totalCount={filteredProblems.length}
    />
  );
}
