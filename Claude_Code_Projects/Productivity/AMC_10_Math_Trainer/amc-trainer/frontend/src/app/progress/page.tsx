import type { Metadata } from 'next';
import ProgressDashboard from './ProgressDashboard';

export const metadata: Metadata = { title: 'Progress — AMC Trainer' };

export default function ProgressPage() {
  return <ProgressDashboard />;
}
