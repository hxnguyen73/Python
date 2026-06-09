import { readProgress, writeProgress, calcScore, updateTopicStats } from '@/lib/progress';
import type { ProblemAttempt, Session } from '@/lib/progress';

export const dynamic = 'force-dynamic';

function todayString(): string {
  return new Date().toISOString().slice(0, 10);
}

function newSessionId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export async function POST(request: Request) {
  const body = await request.json() as {
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
  };

  const score_value = calcScore({
    is_correct: body.is_correct,
    hints_viewed: body.hints_viewed,
    solution_viewed: body.solution_viewed,
  });

  const attempt: ProblemAttempt = {
    ...body,
    score_value,
    timestamp: new Date().toISOString(),
  };

  const data = readProgress();
  const today = todayString();

  let session = data.sessions.find((s) => s.date === today);
  if (!session) {
    session = {
      session_id: newSessionId(),
      date: today,
      duration_minutes: 0,
      problems_attempted: [],
    } satisfies Session;
    data.sessions.push(session);
  }

  session.problems_attempted.push(attempt);
  session.duration_minutes = Math.round(
    session.problems_attempted.reduce((sum, a) => sum + a.time_spent_seconds, 0) / 60
  );

  updateTopicStats(data.topic_stats, attempt);
  writeProgress(data);

  return Response.json({ ok: true, score_value });
}
