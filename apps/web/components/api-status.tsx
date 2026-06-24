"use client";

import { useEffect, useState } from "react";
import { getHealth } from "@/lib/api";
import { cn } from "@/lib/utils";

export function ApiStatus() {
  const [up, setUp] = useState<boolean | null>(null);

  useEffect(() => {
    getHealth().then(setUp);
  }, []);

  const label = up === null ? "comprobando…" : up ? "API conectada" : "API sin conexión";

  return (
    <span className="inline-flex items-center gap-2 text-xs text-muted-foreground">
      <span
        className={cn(
          "h-2 w-2 rounded-full",
          up === null ? "bg-muted-foreground" : up ? "bg-green-500" : "bg-red-500",
        )}
      />
      {label}
    </span>
  );
}
