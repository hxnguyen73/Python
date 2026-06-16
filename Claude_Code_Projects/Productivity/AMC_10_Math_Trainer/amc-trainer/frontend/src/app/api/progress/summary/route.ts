import { readProgress, buildSummary } from '@/lib/progress';

export const dynamic = 'force-dynamic';

export async function GET() {
  const data = await readProgress();
  const summary = buildSummary(data);
  return Response.json(summary);
}
