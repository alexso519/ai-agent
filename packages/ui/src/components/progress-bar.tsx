'use client';

import { cn } from '../lib/utils';

export interface ProgressBarProps {
  value: number;
  max?: number;
  className?: string;
  size?: 'sm' | 'md';
  color?: 'blue' | 'green' | 'orange';
}

const sizeStyles = {
  sm: 'h-1',
  md: 'h-2',
};

const colorStyles = {
  blue: 'bg-blue-500',
  green: 'bg-green-500',
  orange: 'bg-orange-500',
};

/**
 * Thin progress bar for task nodes.
 */
export function ProgressBar({
  value,
  max = 100,
  className,
  size = 'sm',
  color = 'blue',
}: ProgressBarProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  return (
    <div
      className={cn('w-full overflow-hidden rounded-full bg-slate-200', sizeStyles[size], className)}
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={max}
    >
      <div
        className={cn(
          'h-full rounded-full transition-all duration-500 ease-out',
          colorStyles[color],
        )}
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
}