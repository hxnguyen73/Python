import { createClient } from '@supabase/supabase-js';

export interface ProblemAttempt {
  problem_id: string;
  is_morphed: boolean;
  topic: string;
  difficulty: string;
  time_spent_seconds: number;
  answer_selected: string;
  correct_answer: string;
  is_correct: boolean;
  hints_viewed: number;
  solution_viewed: boolean;
  score_value: number;
  timestamp: string;
}

export interface Session {
  session_id: string;
  date: string;
  duration_minutes: number;
  problems_attempted: ProblemAttempt[];
}

export interface TopicStat {
  attempted: number;
  correct: number;
  accuracy: number;
  avg_time_seconds: number;
  trend: 'improving' | 'stable' | 'declining';
  recent_scores: number[];
}

export interface StudentInfo {
  name: string;
  started: string;
  target_exam_date: string;
  daily_goal: number;
  show_timer: boolean;
}

export interface ProgressData {
  student: StudentInfo;
  sessions: Session[];
  topic_stats: Record<string, TopicStat>;
}

const PROGRESS_ID = 'default';

function defaultProgressData(): ProgressData {
  return {
    student: {
      name: 'Student',
      started: new Date().toISOString().slice(0, 10),
      target_exam_date: '2026-11-07',
      daily_goal: 10,
      show_timer: true,
    },
    sessions: [],
    topic_stats: {},
  };
}

function getSupabase() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) throw new Error('Supabase env vars not set (NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)');
  return createClient(url, key);
}

export async function readProgress(): Promise<ProgressData> {
  try {
    const supabase = getSupabase();
    const { data, error } = await supabase
      .from('progress')
      .select('data')
      .eq('id', PROGRESS_ID)
      .single();

    if (error || !data) return defaultProgressData();
    return data.data as ProgressData;
  } catch {
    return defaultProgressData();
  }
}

export async function writeProgress(progress: ProgressData): Promise<void> {
  const supabase = getSupabase();
  await supabase
    .from('progress')
    .upsert({ id: PROGRESS_ID, data: progress });
}

export function calcScore(attempt: Pick<ProblemAttempt, 'is_correct' | 'hints_viewed' | 'solution_viewed'>): number {
  if (!attempt.is_correct) return 0;
  if (attempt.solution_viewed) return 1;
  if (attempt.hints_viewed > 0) return 4;
  return 6;
}

export function updateTopicStats(
  stats: Record<string, TopicStat>,
  attempt: ProblemAttempt
): void {
  const topic = attempt.topic;
  if (!stats[topic]) {
    stats[topic] = {
      attempted: 0,
      correct: 0,
      accuracy: 0,
      avg_time_seconds: 0,
      trend: 'stable',
      recent_scores: [],
    };
  }
  const s = stats[topic];
  s.attempted += 1;
  if (attempt.is_correct) s.correct += 1;
  s.accuracy = s.correct / s.attempted;
  s.avg_time_seconds = Math.round(
    (s.avg_time_seconds * (s.attempted - 1) + attempt.time_spent_seconds) / s.attempted
  );
  s.recent_scores.push(attempt.is_correct ? 1 : 0);
  if (s.recent_scores.length > 10) s.recent_scores.shift();

  if (s.recent_scores.length >= 4) {
    const half = Math.floor(s.recent_scores.length / 2);
    const early = s.recent_scores.slice(0, half).reduce((a, b) => a + b, 0) / half;
    const late = s.recent_scores.slice(half).reduce((a, b) => a + b, 0) / (s.recent_scores.length - half);
    if (late - early > 0.15) s.trend = 'improving';
    else if (early - late > 0.15) s.trend = 'declining';
    else s.trend = 'stable';
  }
}

export interface ProgressSummary {
  student: StudentInfo;
  total_problems: number;
  total_correct: number;
  overall_accuracy: number;
  training_score: number;
  amc_equivalent_score: number;
  study_streak_days: number;
  topic_stats: Record<string, TopicStat>;
  weak_topics: string[];
  strong_topics: string[];
  recent_attempts: (ProblemAttempt & { session_date: string })[];
  days_until_exam: number;
}

export function buildSummary(data: ProgressData): ProgressSummary {
  const allAttempts: (ProblemAttempt & { session_date: string })[] = [];
  let totalProblems = 0;
  let totalCorrect = 0;
  let trainingScore = 0;

  for (const session of data.sessions) {
    for (const attempt of session.problems_attempted) {
      allAttempts.push({ ...attempt, session_date: session.date });
      totalProblems++;
      if (attempt.is_correct) totalCorrect++;
      trainingScore += attempt.score_value;
    }
  }

  const overall_accuracy = totalProblems > 0 ? totalCorrect / totalProblems : 0;

  const recent25 = allAttempts.slice(-25);
  const recent25Correct = recent25.filter((a) => a.is_correct).length;
  const amc_equivalent_score = recent25.length > 0
    ? Math.round((recent25Correct / recent25.length) * 150)
    : 0;

  const weak_topics = Object.entries(data.topic_stats)
    .filter(([, s]) => s.attempted >= 3 && s.accuracy < 0.6)
    .map(([t]) => t);
  const strong_topics = Object.entries(data.topic_stats)
    .filter(([, s]) => s.attempted >= 3 && s.accuracy > 0.8)
    .map(([t]) => t);

  const sessionDates = new Set(data.sessions.map((s) => s.date));
  let streak = 0;
  const now = new Date();
  for (let i = 0; ; i++) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().slice(0, 10);
    if (sessionDates.has(dateStr)) streak++;
    else break;
  }

  const targetDate = new Date(data.student.target_exam_date);
  const days_until_exam = Math.max(
    0,
    Math.ceil((targetDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
  );

  return {
    student: data.student,
    total_problems: totalProblems,
    total_correct: totalCorrect,
    overall_accuracy,
    training_score: trainingScore,
    amc_equivalent_score,
    study_streak_days: streak,
    topic_stats: data.topic_stats,
    weak_topics,
    strong_topics,
    recent_attempts: allAttempts.slice(-10).reverse(),
    days_until_exam,
  };
}
