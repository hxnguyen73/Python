'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from 'recharts';
import { cn } from '@/lib/utils';
import type { ProgressSummary } from '@/lib/progress';

type TopicStat = ProgressSummary['topic_stats'][string];

interface Recommendations {
  weak_topics?: string[];
  drill_recommendations?: string[];
  time_management_tip?: string;
  encouragement?: string;
  predicted_amc_score?: number;
  error?: string;
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="flex-1 min-w-[120px] bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex flex-col items-center gap-1">
      <div className="text-2xl font-bold text-zinc-100">{value}</div>
      <div className="text-xs text-zinc-400 text-center">{label}</div>
      {sub && <div className="text-xs text-zinc-600 text-center">{sub}</div>}
    </div>
  );
}

function topicColor(accuracy: number): string {
  if (accuracy < 0.6) return '#ef4444';
  if (accuracy < 0.8) return '#eab308';
  return '#22c55e';
}

function trendIcon(trend: string): string {
  if (trend === 'improving') return '↑';
  if (trend === 'declining') return '↓';
  return '→';
}

export default function ProgressDashboard() {
  const [summary, setSummary] = useState<ProgressSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [recs, setRecs] = useState<Recommendations | null>(null);
  const [recsLoading, setRecsLoading] = useState(false);

  const fetchSummary = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/progress/summary');
      setSummary(await res.json());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  const fetchRecs = async () => {
    setRecsLoading(true);
    try {
      const res = await fetch('/api/progress/recommendations');
      setRecs(await res.json());
    } finally {
      setRecsLoading(false);
    }
  };

  if (loading || !summary) {
    return (
      <div className="flex-1 flex items-center justify-center text-zinc-500 text-sm">
        Loading progress...
      </div>
    );
  }

  const topicEntries = Object.entries(summary.topic_stats) as [string, TopicStat][];
  const barData = topicEntries
    .sort((a, b) => a[1].accuracy - b[1].accuracy)
    .map(([topic, s]) => ({
      topic,
      accuracy: Math.round(s.accuracy * 100),
      attempted: s.attempted,
      trend: s.trend,
      fill: topicColor(s.accuracy),
    }));

  const radarData = topicEntries.map(([topic, s]) => ({
    topic: topic.length > 12 ? topic.slice(0, 12) + '…' : topic,
    current: Math.round(s.accuracy * 100),
    target: 80,
  }));

  const isEmpty = summary.total_problems === 0;

  return (
    <div className="flex-1 overflow-auto">
      <div className="max-w-5xl mx-auto px-6 py-8 space-y-8">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-zinc-100">Progress Dashboard</h1>
            {summary.days_until_exam > 0 && (
              <p className="text-sm text-zinc-500 mt-0.5">
                {summary.days_until_exam} days until exam
              </p>
            )}
          </div>
          <Link
            href="/settings"
            className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            ⚙ Settings
          </Link>
        </div>

        {/* Stats bar */}
        <div className="flex gap-3 flex-wrap">
          <StatCard label="Problems Attempted" value={String(summary.total_problems)} />
          <StatCard
            label="Overall Accuracy"
            value={isEmpty ? '—' : `${Math.round(summary.overall_accuracy * 100)}%`}
          />
          <StatCard
            label="Est. AMC Score"
            value={isEmpty ? '—' : `${summary.amc_equivalent_score}/150`}
            sub={isEmpty ? undefined : 'based on last 25'}
          />
          <StatCard
            label="Study Streak"
            value={`${summary.study_streak_days} day${summary.study_streak_days !== 1 ? 's' : ''}`}
          />
          <StatCard
            label="Training Points"
            value={isEmpty ? '—' : String(summary.training_score)}
            sub="6 pts per correct"
          />
        </div>

        {isEmpty ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-10 text-center text-zinc-500">
            <p className="text-4xl mb-3">📊</p>
            <p className="text-sm">No problems attempted yet.</p>
            <Link href="/" className="mt-3 inline-block text-sm text-blue-400 hover:text-blue-300">
              Start practicing →
            </Link>
          </div>
        ) : (
          <>
            {/* Topic performance bar chart */}
            <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
              <h2 className="text-sm font-semibold text-zinc-300 mb-4">Topic Performance</h2>
              {barData.length === 0 ? (
                <p className="text-zinc-500 text-sm">No topic data yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height={Math.max(200, barData.length * 36)}>
                  <BarChart data={barData} layout="vertical" margin={{ left: 0, right: 48, top: 0, bottom: 0 }}>
                    <XAxis type="number" domain={[0, 100]} tick={{ fill: '#71717a', fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
                    <YAxis
                      type="category"
                      dataKey="topic"
                      width={130}
                      tick={{ fill: '#a1a1aa', fontSize: 11 }}
                      tickFormatter={(v: string) => v.length > 16 ? v.slice(0, 16) + '…' : v}
                    />
                    <Tooltip
                      cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                      contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', borderRadius: 8, fontSize: 12 }}
                      formatter={(value, _name, props) => [
                        `${value}% (${(props.payload as { attempted?: number })?.attempted ?? 0} attempts) ${trendIcon((props.payload as { trend?: string })?.trend ?? 'stable')}`,
                        'Accuracy',
                      ]}
                    />
                    <Bar dataKey="accuracy" radius={[0, 4, 4, 0]} label={{ position: 'right', fill: '#71717a', fontSize: 11, formatter: (v: unknown) => `${v}%` }}>
                      {barData.map((entry, idx) => (
                        <Cell key={idx} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
              <div className="mt-3 flex items-center gap-4 text-xs text-zinc-500">
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-red-500 inline-block" /> &lt;60% weak</span>
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-yellow-500 inline-block" /> 60–80% ok</span>
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-green-500 inline-block" /> &gt;80% strong</span>
              </div>
            </section>

            {/* Two-column: radar + recent activity */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Radar chart */}
              <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                <h2 className="text-sm font-semibold text-zinc-300 mb-4">Topic Coverage Radar</h2>
                {radarData.length < 3 ? (
                  <p className="text-zinc-500 text-sm">Need at least 3 topics for radar view.</p>
                ) : (
                  <ResponsiveContainer width="100%" height={240}>
                    <RadarChart data={radarData}>
                      <PolarGrid stroke="#3f3f46" />
                      <PolarAngleAxis dataKey="topic" tick={{ fill: '#71717a', fontSize: 10 }} />
                      <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#52525b', fontSize: 9 }} />
                      <Radar name="Current" dataKey="current" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.25} />
                      <Radar name="Target" dataKey="target" stroke="#22c55e" fill="#22c55e" fillOpacity={0.1} strokeDasharray="4 2" />
                    </RadarChart>
                  </ResponsiveContainer>
                )}
                <div className="mt-2 flex items-center gap-4 text-xs text-zinc-500">
                  <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-blue-500 inline-block" /> You</span>
                  <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-green-500 inline-block" style={{ borderTop: '1px dashed #22c55e' }} /> Target (80%)</span>
                </div>
              </section>

              {/* Recent activity */}
              <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                <h2 className="text-sm font-semibold text-zinc-300 mb-4">Recent Activity</h2>
                {summary.recent_attempts.length === 0 ? (
                  <p className="text-zinc-500 text-sm">No recent attempts.</p>
                ) : (
                  <div className="space-y-2">
                    {summary.recent_attempts.map((a, i) => (
                      <Link
                        key={i}
                        href={`/problem/${a.problem_id}`}
                        className="flex items-center gap-2 text-xs py-1.5 px-2 rounded-lg hover:bg-zinc-800 transition-colors group"
                      >
                        <span className={a.is_correct ? 'text-green-400' : 'text-red-400'}>
                          {a.is_correct ? '✓' : '✗'}
                        </span>
                        <span className="text-zinc-300 flex-1 truncate group-hover:text-zinc-100">
                          {a.problem_id}
                        </span>
                        <span className="text-zinc-500 shrink-0">{a.topic}</span>
                        <span className="text-zinc-600 shrink-0">
                          {a.time_spent_seconds < 60
                            ? `${a.time_spent_seconds}s`
                            : `${Math.floor(a.time_spent_seconds / 60)}m${a.time_spent_seconds % 60}s`}
                        </span>
                        <span className={cn(
                          'shrink-0 font-semibold',
                          a.score_value === 6 ? 'text-green-400' :
                          a.score_value >= 4 ? 'text-yellow-400' :
                          a.score_value === 1 ? 'text-orange-400' : 'text-zinc-600'
                        )}>
                          {a.score_value}pt
                        </span>
                      </Link>
                    ))}
                  </div>
                )}
              </section>
            </div>

            {/* Weak / strong topic badges */}
            {(summary.weak_topics.length > 0 || summary.strong_topics.length > 0) && (
              <div className="flex gap-6 flex-wrap">
                {summary.weak_topics.length > 0 && (
                  <div>
                    <p className="text-xs text-zinc-500 mb-2">Needs work (&lt;60%)</p>
                    <div className="flex flex-wrap gap-2">
                      {summary.weak_topics.map((t) => (
                        <span key={t} className="text-xs px-2 py-0.5 rounded-full bg-red-500/15 text-red-400 border border-red-500/30">
                          🔴 {t}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {summary.strong_topics.length > 0 && (
                  <div>
                    <p className="text-xs text-zinc-500 mb-2">Strong (&gt;80%)</p>
                    <div className="flex flex-wrap gap-2">
                      {summary.strong_topics.map((t) => (
                        <span key={t} className="text-xs px-2 py-0.5 rounded-full bg-green-500/15 text-green-400 border border-green-500/30">
                          ✓ {t}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* AI Coach */}
            <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-zinc-300">AI Study Coach</h2>
                <button
                  onClick={fetchRecs}
                  disabled={recsLoading}
                  className={cn(
                    'px-4 py-1.5 rounded-lg text-sm font-medium transition-colors',
                    recsLoading
                      ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
                      : 'bg-blue-600 hover:bg-blue-500 text-white'
                  )}
                >
                  {recsLoading ? 'Analyzing…' : 'Get Study Recommendations'}
                </button>
              </div>

              {!recs && !recsLoading && (
                <p className="text-zinc-500 text-sm">
                  Click above to get personalized recommendations from Claude based on your performance.
                </p>
              )}

              {recs && !recs.error && (
                <div className="space-y-4 text-sm">
                  {recs.encouragement && (
                    <div className="px-4 py-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-300">
                      {recs.encouragement}
                    </div>
                  )}
                  {recs.weak_topics && recs.weak_topics.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-zinc-400 mb-1">Focus This Week</p>
                      <div className="flex gap-2 flex-wrap">
                        {recs.weak_topics.map((t) => (
                          <span key={t} className="text-xs px-2 py-0.5 rounded-full bg-red-500/15 text-red-400 border border-red-500/30">
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {recs.drill_recommendations && recs.drill_recommendations.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-zinc-400 mb-1">Drill Recommendations</p>
                      <ul className="space-y-1">
                        {recs.drill_recommendations.map((r, i) => (
                          <li key={i} className="text-zinc-300 text-sm flex items-start gap-2">
                            <span className="text-zinc-600 shrink-0">•</span>
                            {r}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {recs.time_management_tip && (
                    <div>
                      <p className="text-xs font-semibold text-zinc-400 mb-1">Time Management</p>
                      <p className="text-zinc-300">{recs.time_management_tip}</p>
                    </div>
                  )}
                  {recs.predicted_amc_score !== undefined && (
                    <p className="text-xs text-zinc-500">
                      Predicted AMC score: <span className="text-zinc-300 font-semibold">{recs.predicted_amc_score}/150</span>
                    </p>
                  )}
                </div>
              )}

              {recs?.error && (
                <p className="text-red-400 text-sm">{recs.error}</p>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}
