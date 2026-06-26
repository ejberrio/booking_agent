"use client";

import { useEffect, useState } from "react";

const KEY = "activeUnitTypeId";

/** Id de la unidad activa (el backend aún no expone listado de unidades; se guarda local). */
export function useActiveUnit(): [number, (id: number) => void] {
  const [id, setId] = useState<number>(1);

  useEffect(() => {
    const stored = typeof window !== "undefined" ? window.localStorage.getItem(KEY) : null;
    if (stored) setId(Number(stored));
  }, []);

  const update = (value: number) => {
    setId(value);
    if (typeof window !== "undefined") window.localStorage.setItem(KEY, String(value));
  };

  return [id, update];
}
