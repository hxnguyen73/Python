'use client';

import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from 'react';
import { cn } from '@/lib/utils';

export interface ProblemTimerHandle {
  pause(): void;
  resume(): void;
  stop(): void;
  getSeconds(): number;
}

interface Props {
  onTimeUpdate?: (seconds: number) => void;
}

function formatTime(seconds: number): string {
  const mm = Math.floor(seconds / 60).toString().padStart(2, '0');
  const ss = (seconds % 60).toString().padStart(2, '0');
  return `${mm}:${ss}`;
}

const ProblemTimer = forwardRef<ProblemTimerHandle, Props>(function ProblemTimer(
  { onTimeUpdate },
  ref
) {
  const [seconds, setSeconds] = useState(0);
  const [running, setRunning] = useState(true);
  const secondsRef = useRef(0);

  useImperativeHandle(ref, () => ({
    pause() {
      setRunning(false);
    },
    resume() {
      setRunning(true);
    },
    stop() {
      setRunning(false);
    },
    getSeconds() {
      return secondsRef.current;
    },
  }));

  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      setSeconds((prev) => {
        const next = prev + 1;
        secondsRef.current = next;
        onTimeUpdate?.(next);
        return next;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [running, onTimeUpdate]);

  const colorClass =
    seconds >= 300
      ? 'text-red-400'
      : seconds >= 180
      ? 'text-yellow-400'
      : 'text-zinc-100';

  return (
    <div
      className="relative group cursor-default select-none"
      title="AMC pace: 2.5 min/problem"
    >
      <span className={cn('font-mono text-sm font-semibold tabular-nums', colorClass)}>
        {formatTime(seconds)}
      </span>
      {/* Tooltip */}
      <div className="absolute right-0 top-full mt-1 z-50 hidden group-hover:block whitespace-nowrap">
        <span className="text-xs bg-zinc-800 border border-zinc-700 text-zinc-300 rounded px-2 py-1">
          AMC pace: 2.5 min/problem
        </span>
      </div>
    </div>
  );
});

export default ProblemTimer;
