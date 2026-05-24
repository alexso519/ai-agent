'use client';

import { cn } from '../lib/utils';

export interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeStyles = {
  sm: 'h-4 w-4 border-2',
  md: 'h-6 w-6 border-2',
  lg: 'h-8 w-8 border-3',
};

/**
 * Atomic loading spinner component.
 */
export function LoadingSpinner({ size = 'md', className }: LoadingSpinnerProps) {
  return (
    <div
      className={cn(
        'animate-spin rounded-full border-slate-300 border-t-blue-600',
        sizeStyles[size],
        className,
      )}
      role="status"
      aria-label="Loading"
    />
  );
}