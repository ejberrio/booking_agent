import * as React from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "muted" | "success" | "warning" | "danger";

const styles: Record<Variant, string> = {
  default: "bg-primary-subtle text-primary",
  muted: "bg-muted text-muted-foreground",
  success: "bg-success-subtle text-success",
  warning: "bg-accent-subtle text-accent",
  danger: "bg-danger-subtle text-danger",
};

export function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: Variant }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-bold",
        styles[variant],
        className,
      )}
      {...props}
    />
  );
}
