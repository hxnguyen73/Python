'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import type { StudentInfo } from '@/lib/progress';

export default function SettingsClient() {
  const [settings, setSettings] = useState<StudentInfo | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);

  useEffect(() => {
    fetch('/api/progress/settings')
      .then((r) => r.json())
      .then(setSettings);
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settings) return;
    setSaving(true);
    setSaved(false);
    await fetch('/api/progress/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleReset = async () => {
    setResetting(true);
    await fetch('/api/progress/settings', { method: 'DELETE' });
    setResetting(false);
    setConfirmReset(false);
    alert('Progress reset.');
  };

  const daysUntil = settings?.target_exam_date
    ? Math.max(0, Math.ceil((new Date(settings.target_exam_date).getTime() - Date.now()) / 86400000))
    : null;

  if (!settings) {
    return (
      <div className="flex-1 flex items-center justify-center text-zinc-500 text-sm">
        Loading settings...
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto">
      <div className="max-w-lg mx-auto px-6 py-10 space-y-8">
        <h1 className="text-xl font-bold text-zinc-100">Settings</h1>

        <form onSubmit={handleSave} className="space-y-5">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-1">Student Name</label>
            <input
              type="text"
              value={settings.name}
              onChange={(e) => setSettings({ ...settings, name: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-700 text-zinc-100 text-sm focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Target exam date */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-1">Target Exam Date</label>
            <input
              type="date"
              value={settings.target_exam_date}
              onChange={(e) => setSettings({ ...settings, target_exam_date: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-700 text-zinc-100 text-sm focus:outline-none focus:border-blue-500"
            />
            {daysUntil !== null && (
              <p className="mt-1 text-xs text-zinc-500">{daysUntil} days remaining</p>
            )}
          </div>

          {/* Daily goal */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-1">Daily Problem Goal</label>
            <input
              type="number"
              min={1}
              max={100}
              value={settings.daily_goal}
              onChange={(e) => setSettings({ ...settings, daily_goal: Number(e.target.value) })}
              className="w-24 px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-700 text-zinc-100 text-sm focus:outline-none focus:border-blue-500"
            />
            <span className="ml-2 text-xs text-zinc-500">problems per day</span>
          </div>

          {/* Show timer */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setSettings({ ...settings, show_timer: !settings.show_timer })}
              className={cn(
                'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                settings.show_timer ? 'bg-blue-600' : 'bg-zinc-700'
              )}
            >
              <span
                className={cn(
                  'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                  settings.show_timer ? 'translate-x-6' : 'translate-x-1'
                )}
              />
            </button>
            <span className="text-sm text-zinc-300">Show timer on problems</span>
          </div>

          <button
            type="submit"
            disabled={saving}
            className={cn(
              'px-6 py-2.5 rounded-lg text-sm font-semibold transition-colors',
              saving ? 'bg-zinc-800 text-zinc-500' : 'bg-blue-600 hover:bg-blue-500 text-white'
            )}
          >
            {saving ? 'Saving…' : saved ? '✓ Saved' : 'Save Settings'}
          </button>
        </form>

        {/* Danger zone */}
        <div className="border-t border-zinc-800 pt-6">
          <h2 className="text-sm font-semibold text-red-400 mb-3">Danger Zone</h2>
          {!confirmReset ? (
            <button
              onClick={() => setConfirmReset(true)}
              className="px-4 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm hover:bg-red-500/20 transition-colors"
            >
              Reset All Progress
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <span className="text-sm text-zinc-400">Are you sure? This cannot be undone.</span>
              <button
                onClick={handleReset}
                disabled={resetting}
                className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm hover:bg-red-500 transition-colors"
              >
                {resetting ? 'Resetting…' : 'Yes, Reset'}
              </button>
              <button
                onClick={() => setConfirmReset(false)}
                className="text-sm text-zinc-500 hover:text-zinc-300"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
