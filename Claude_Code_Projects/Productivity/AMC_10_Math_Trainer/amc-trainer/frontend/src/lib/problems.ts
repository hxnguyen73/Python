import fs from 'fs';
import path from 'path';
import type { Problem, FilterState, FilterOptions } from './types';

const DATA_DIR = path.join(process.cwd(), 'data', 'parsed');

export function getAllProblems(): Problem[] {
  let files: string[];
  try {
    files = fs.readdirSync(DATA_DIR).filter((f) => f.endsWith('.json'));
  } catch {
    console.error(`Could not read data directory: ${DATA_DIR}`);
    return [];
  }

  const all: Problem[] = [];

  for (const file of files) {
    try {
      const raw = fs.readFileSync(path.join(DATA_DIR, file), 'utf-8');
      const problems = JSON.parse(raw) as Problem[];
      all.push(...problems);
    } catch (err) {
      console.error(`Failed to parse ${file}:`, err);
    }
  }

  all.sort((a, b) => {
    if (a.year !== b.year) return a.year - b.year;
    if (a.exam < b.exam) return -1;
    if (a.exam > b.exam) return 1;
    return a.question_number - b.question_number;
  });

  return all;
}

export function getProblemById(id: string): Problem | null {
  const all = getAllProblems();
  return all.find((p) => p.id === id) ?? null;
}

export function getFilterOptions(problems: Problem[]): FilterOptions {
  const years = [...new Set(problems.map((p) => p.year))].sort((a, b) => a - b);
  const topics = [...new Set(problems.map((p) => p.topic))].sort();
  const difficulties = [...new Set(problems.map((p) => p.difficulty))].sort();
  const exams = [...new Set(problems.map((p) => p.exam))].sort();
  return { years, topics, difficulties, exams };
}

export function filterProblems(problems: Problem[], filter: FilterState): Problem[] {
  return problems.filter((p) => {
    if (filter.years.length > 0 && !filter.years.includes(p.year)) return false;
    if (filter.topics.length > 0 && !filter.topics.includes(p.topic)) return false;
    if (filter.difficulties.length > 0 && !filter.difficulties.includes(p.difficulty)) return false;
    if (filter.exams.length > 0 && !filter.exams.includes(p.exam)) return false;
    return true;
  });
}
