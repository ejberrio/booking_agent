"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";

const KEY = "activeUnitTypeId";

/** Unidades de la cuenta de la sesión (feature 026: ya no se asume la unidad 1). */
export function useUnits() {
  return useQuery({ queryKey: ["units"], queryFn: api.listUnits, staleTime: 60_000 });
}

/** Unidad activa: la guardada si sigue siendo de la cuenta; si no, la primera. */
export function useActiveUnit(): [number, (id: number) => void] {
  const { data: units } = useUnits();
  const [stored, setStored] = useState<number | null>(null);

  useEffect(() => {
    const raw = typeof window !== "undefined" ? window.localStorage.getItem(KEY) : null;
    if (raw) setStored(Number(raw));
  }, []);

  const ids = units?.map((u) => u.id) ?? [];
  const id = stored !== null && ids.includes(stored) ? stored : (ids[0] ?? stored ?? 0);

  const update = (value: number) => {
    setStored(value);
    if (typeof window !== "undefined") window.localStorage.setItem(KEY, String(value));
  };

  return [id, update];
}
