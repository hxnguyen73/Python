export interface Problem {
  id: string;
  year: number;
  exam: string;
  question_number: number;
  topic: string;
  difficulty: string;
  problem_text: string;
  answer_choices: Record<string, string>;
  correct_answer: string;
  solution_text: string;
  has_image: boolean;
}

export interface FilterState {
  years: number[];
  topics: string[];
  difficulties: string[];
  exams: string[];
}

export interface FilterOptions {
  years: number[];
  topics: string[];
  difficulties: string[];
  exams: string[];
}
