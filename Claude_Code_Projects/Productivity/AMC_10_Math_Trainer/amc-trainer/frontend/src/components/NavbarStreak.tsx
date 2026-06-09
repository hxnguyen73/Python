'use client';

import { useEffect, useState } from 'react';

export default function NavbarStreak() {
  const [streak, setStreak] = useState<number | null>(null);

  useEffect(() => {
    fetch('/api/progress/summary')
      .then((r) => r.json())
      .then((d) => setStreak(d.study_streak_days ?? 0))
      .catch(() => {});
  }, []);

  if (streak === null || streak === 0) return null;

  return (
    <span className="text-xs text-amber-400 font-semibold flex items-center gap-1">
      🔥 {streak} day streak
    </span>
  );
}
