import { readProgress, writeProgress } from '@/lib/progress';
import type { StudentInfo } from '@/lib/progress';

export const dynamic = 'force-dynamic';

export async function GET() {
  const data = await readProgress();
  return Response.json(data.student);
}

export async function POST(request: Request) {
  const body = await request.json() as Partial<StudentInfo>;
  const data = await readProgress();
  data.student = { ...data.student, ...body };
  await writeProgress(data);
  return Response.json({ ok: true, student: data.student });
}

export async function DELETE() {
  const data = await readProgress();
  data.sessions = [];
  data.topic_stats = {};
  await writeProgress(data);
  return Response.json({ ok: true });
}
