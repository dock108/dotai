"use client";

import { cn } from "@/lib/utils/cn";

interface LoadingDotsProps {
  label?: string;
  className?: string;
}

export function LoadingDots({ label, className }: LoadingDotsProps) {
  return (
    <div className={cn("flex items-center gap-2 text-sm text-muted-foreground", className)}>
      <div className="flex items-center gap-1">
        <span className="h-2 w-2 animate-pulse rounded-full bg-primary" />
        <span className="h-2 w-2 animate-pulse rounded-full bg-primary delay-75" />
        <span className="h-2 w-2 animate-pulse rounded-full bg-primary delay-150" />
      </div>
      {label && <span>{label}</span>}
    </div>
  );
}

