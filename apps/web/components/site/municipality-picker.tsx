"use client";

import { useEffect, useRef, useState } from "react";
import { Input } from "@/components/ui/input";
import { useI18n } from "@/lib/i18n";

export type Municipality = { code: string; name: string; department: string; label: string };

/** Buscador de municipios de Colombia (lista oficial; sin texto libre). Feature 030. */
export function MunicipalityPicker({
  value,
  onChange,
}: {
  value: Municipality | null;
  onChange: (m: Municipality | null) => void;
}) {
  const { m } = useI18n();
  const t = m.pub.report;
  const [q, setQ] = useState(value?.label ?? "");
  const [items, setItems] = useState<Municipality[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (value && q === value.label) return;
    if (timer.current) clearTimeout(timer.current);
    if (q.trim().length < 2) {
      setItems([]);
      return;
    }
    timer.current = setTimeout(() => {
      fetch(`/api/public/municipalities?q=${encodeURIComponent(q.trim())}`)
        .then((r) => (r.ok ? r.json() : []))
        .then((d: Municipality[]) => {
          setItems(d);
          setActive(0);
          setOpen(true);
        })
        .catch(() => setItems([]));
    }, 200);
  }, [q, value]);

  function pick(item: Municipality) {
    onChange(item);
    setQ(item.label);
    setOpen(false);
  }

  return (
    <div className="relative">
      <Input
        value={q}
        placeholder={t.municipalityPh}
        aria-label={t.municipality}
        autoComplete="off"
        role="combobox"
        aria-expanded={open}
        onChange={(e) => {
          setQ(e.target.value);
          if (value) onChange(null);
        }}
        onFocus={() => items.length > 0 && setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={(e) => {
          if (!open || items.length === 0) return;
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setActive((a) => Math.min(a + 1, items.length - 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActive((a) => Math.max(a - 1, 0));
          } else if (e.key === "Enter") {
            e.preventDefault();
            pick(items[active]);
          }
        }}
      />
      {open && q.trim().length >= 2 && (
        <ul role="listbox"
          className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-md border border-border bg-card text-sm shadow-lg">
          {items.length === 0 ? (
            <li className="px-3 py-2 text-muted-foreground">{t.noMatch}</li>
          ) : (
            items.map((it, i) => (
              <li key={it.code} role="option" aria-selected={i === active}>
                <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={() => pick(it)}
                  className={`block w-full px-3 py-2 text-left hover:bg-muted ${i === active ? "bg-muted" : ""}`}>
                  <span className="font-medium">{it.name}</span>
                  <span className="text-muted-foreground">, {it.department}</span>
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
