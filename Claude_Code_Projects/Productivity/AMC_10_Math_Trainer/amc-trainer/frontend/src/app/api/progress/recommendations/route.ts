import { readProgress, buildSummary } from '@/lib/progress';

export const dynamic = 'force-dynamic';

export async function GET() {
  if (!process.env.ANTHROPIC_API_KEY) {
    return Response.json({
      error: 'ANTHROPIC_API_KEY not configured. Add it to .env.local to enable AI recommendations.',
    });
  }

  const { default: Anthropic } = await import('@anthropic-ai/sdk');
  const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

  const data = readProgress();
  const summary = buildSummary(data);

  const progressSummaryText = JSON.stringify(
    {
      total_problems: summary.total_problems,
      overall_accuracy: Math.round(summary.overall_accuracy * 100) + '%',
      weak_topics: summary.weak_topics,
      strong_topics: summary.strong_topics,
      topic_stats: Object.fromEntries(
        Object.entries(summary.topic_stats).map(([topic, s]) => [
          topic,
          {
            attempted: s.attempted,
            accuracy: Math.round(s.accuracy * 100) + '%',
            avg_time_seconds: s.avg_time_seconds,
            trend: s.trend,
          },
        ])
      ),
      amc_equivalent_score: summary.amc_equivalent_score,
      days_until_exam: summary.days_until_exam,
    },
    null,
    2
  );

  try {
    const message = await client.messages.create({
      model: 'claude-sonnet-4-6',
      max_tokens: 1024,
      messages: [
        {
          role: 'user',
          content: `You are an AMC 10 math coach analyzing a student's practice data. Given this performance summary:

${progressSummaryText}

Provide specific, actionable recommendations:
1. Top 2 weak topics to focus on this week
2. Specific problem types to drill within each topic
3. Time management advice based on their avg solve times
4. Encouragement based on their improvement trend

Keep it concise, specific, and motivating.
Return as JSON only (no markdown):
{
  "weak_topics": ["topic1", "topic2"],
  "drill_recommendations": ["recommendation1", "recommendation2"],
  "time_management_tip": "...",
  "encouragement": "...",
  "predicted_amc_score": 90
}`,
        },
      ],
    });

    const rawText = message.content[0].type === 'text' ? message.content[0].text : '{}';

    let recommendations: Record<string, unknown>;
    try {
      const jsonMatch = rawText.match(/\{[\s\S]*\}/);
      recommendations = jsonMatch ? JSON.parse(jsonMatch[0]) : {};
    } catch {
      recommendations = { error: 'Failed to parse recommendations' };
    }

    return Response.json(recommendations);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return Response.json({ error: `API error: ${message}` }, { status: 500 });
  }
}
