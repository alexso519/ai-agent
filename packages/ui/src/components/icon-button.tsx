'use client';

import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { cn } from '../lib/utils';

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: ReactNode;
  label: string;
  variant?: 'ghost' | 'primary' | 'danger';
  size?: 'sm' | 'md';
}

const variantStyles = {
  ghost: 'text-slate-500 hover:bg-slate-100 hover:text-slate-700',
  primary: 'text-blue-600 hover:bg-blue-50 hover:text-blue-800',
  danger: 'text-red-500 hover:bg-red-50 hover:text-red-700',
};

const sizeStyles = {
  sm: 'h-7 w-7',
  md: 'h-8 w-8',
};

/**
 * Icon + tooltip button for toolbar actions.
 */
export function IconButton({
  icon,
  label,
  variant = 'ghost',
  size = 'md',
  className,
  disabled,
  ...props
}: IconButtonProps) {
  return (
    <button
      type="button"
      className={cn(
        'inline-flex items-center justify-center rounded-md',
        'transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-blue-400',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        variantStyles[variant],
        sizeStyles[size],
        className,
      )}
      aria-label={label}
      title={label}
      disabled={disabled}
      {...props}
    >
      {icon}
    </button>
  );
}