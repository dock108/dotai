"use client";

import * as React from "react";
import { cn } from "@/lib/utils/cn";

interface SwitchProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  checked?: boolean;
}

export const Switch = React.forwardRef<HTMLButtonElement, SwitchProps>(({ className, checked, ...props }, ref) => {
  return (
    <button
      ref={ref}
      role="switch"
      aria-checked={checked}
      className={cn(
        "relative inline-flex h-6 w-11 rounded-full border border-input transition",
        checked ? "bg-primary" : "bg-muted",
        className,
      )}
      {...props}
    >
      <span
        className={cn(
          "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition",
          checked ? "translate-x-5" : "translate-x-1",
        )}
      />
    </button>
  );
});
Switch.displayName = "Switch";

