import * as React from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "muted" | "success" | "warning";

const styles: Record<Variant, string> = {
  default: "bg-primary text-primary-foreground",
  muted: "bg-muted text-muted-foreground",
  success: "bg-green-500/15 text-green-600",
  warning: "bg-amber-500/15 text-amber-600",
};

export function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: Variant }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium",
        styles[variant],
        className,
      )}
      {...props}
    />
  );
}
