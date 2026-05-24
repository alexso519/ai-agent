'use client';

import { cn } from '../lib/utils';

export interface StatusDotProps {
  status: 'idle' | 'running' | 'success' | 'failed' | 'waiting-human';
  className?: string;
}

const statusColors: Record<StatusDotProps['status'], string> = {
  idle: 'bg-slate-400',
  running: 'bg-blue-500 animate-pulse',
  success: 'bg-green-500',
  failed: 'bg-red-500',
  'waiting-human': 'bg-orange-500',
};

/**
 * Animated colored dot for node status indication.
 */
export function StatusDot({ status, className }: StatusDotProps) {
  return (
    <span
      className={cn(
        'inline-block h-2.5 w-2.5 rounded-full',
        'transition-colors duration-200',
        statusColors[status],
        className,
      )}
      aria-label={`Status: ${status}`}
    />
  );
}