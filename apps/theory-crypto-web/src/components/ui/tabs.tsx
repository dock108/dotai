"use client";

import { cn } from "@/lib/utils/cn";

export type TabOption = {
  value: string;
  label: string;
};

interface TabsProps {
  options: TabOption[];
  value: string;
  onChange: (value: string) => void;
}

export function Tabs({ options, value, onChange }: TabsProps) {
  return (
    <div className="flex w-full flex-wrap gap-2 rounded-lg border border-border/60 bg-card/40 p-1">
      {options.map((option) => (
        <button
          key={option.value}
          onClick={() => onChange(option.value)}
          className={cn(
            "flex-1 rounded-md px-4 py-2 text-sm font-medium transition",
            value === option.value ? "bg-primary text-primary-foreground shadow" : "text-muted-foreground hover:bg-muted/50",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

