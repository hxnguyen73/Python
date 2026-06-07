'use client';

import { Component, type ReactNode } from 'react';
import { InlineMath, BlockMath } from 'react-katex';
import { normalizeProblemText } from '@/lib/utils-text';
import { cn } from '@/lib/utils';

// ── Error Boundary ────────────────────────────────────────────────────────────

interface EBProps {
  expr: string;
  children: ReactNode;
}

interface EBState {
  hasError: boolean;
}

class MathErrorBoundary extends Component<EBProps, EBState> {
  constructor(props: EBProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): EBState {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <code className="text-xs font-mono bg-zinc-800 px-1 rounded text-zinc-400">
          {this.props.expr}
        </code>
      );
    }
    return this.props.children;
  }
}

// ── Segment parsing ───────────────────────────────────────────────────────────

type Segment =
  | { type: 'block'; expr: string }
  | { type: 'inline'; expr: string }
  | { type: 'text'; content: string };

function parseSegments(text: string): Segment[] {
  const segments: Segment[] = [];

  // Split on $$...$$ first
  const blockParts = text.split(/(\$\$[\s\S]*?\$\$)/g);

  for (const part of blockParts) {
    if (part.startsWith('$$') && part.endsWith('$$')) {
      segments.push({ type: 'block', expr: part.slice(2, -2) });
      continue;
    }

    // Only treat $…$ as a math block when the content contains \ or ^ —
    // real LaTeX markers. Monetary amounts like $28000 have neither.
    const inlineParts = part.split(/(\$(?=[^$]*[\\^_])[^$]+?\$)/g);
    for (const ip of inlineParts) {
      if (ip.startsWith('$') && ip.endsWith('$') && ip.length > 2) {
        segments.push({ type: 'inline', expr: ip.slice(1, -1) });
      } else if (ip) {
        segments.push({ type: 'text', content: ip });
      }
    }
  }

  return segments;
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  text: string;
  className?: string;
}

export default function MathText({ text, className }: Props) {
  const normalized = normalizeProblemText(text);
  const segments = parseSegments(normalized);

  return (
    <span className={cn('leading-relaxed', className)}>
      {segments.map((seg, i) => {
        if (seg.type === 'block') {
          return (
            <MathErrorBoundary key={i} expr={seg.expr}>
              <BlockMath math={seg.expr} />
            </MathErrorBoundary>
          );
        }
        if (seg.type === 'inline') {
          return (
            <MathErrorBoundary key={i} expr={seg.expr}>
              <InlineMath math={seg.expr} />
            </MathErrorBoundary>
          );
        }
        return (
          <span key={i} style={{ whiteSpace: 'pre-wrap' }}>
            {seg.content}
          </span>
        );
      })}
    </span>
  );
}
