"use client";

import { Plus, Trash2 } from "lucide-react";
import { useMemo } from "react";
import { Input } from "@/components/ui/input";
import { useI18n } from "@/lib/i18n";
import type { GuestData, GuestPerson } from "@/lib/types";
import { cn } from "@/lib/utils";

// Formulario de huéspedes (feature 046): lo usan el enlace público del huésped y el panel del anfitrión.
const COUNTRIES =
  "AD AE AF AG AL AM AO AR AT AU AW AZ BA BB BD BE BF BG BH BI BJ BM BN BO BR BS BT BW BY BZ CA CD CF CG CH CI CL CM CN CO CR CU CV CW CY CZ DE DJ DK DM DO DZ EC EE EG ER ES ET FI FJ FM FR GA GB GD GE GH GM GN GQ GR GT GW GY HK HN HR HT HU ID IE IL IN IQ IR IS IT JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MG MH MK ML MM MN MO MR MT MU MV MW MX MY MZ NA NE NG NI NL NO NP NR NZ OM PA PE PG PH PK PL PR PS PT PW PY QA RO RS RU RW SA SB SC SD SE SG SI SK SL SM SN SO SR SS ST SV SX SY SZ TD TG TH TJ TL TM TN TO TR TT TV TW TZ UA UG US UY UZ VA VC VE VN VU WS XK YE ZA ZM ZW".split(" ");
const DOCS = ["CC", "CE", "TI", "PA", "RC"];
const MAIN_DOCS = ["CC", "CE", "TI", "PA"];
const MAX_COMPANIONS = 15;

/** Enlace público de registro que se le comparte al huésped. */
export function checkinUrl(token: string): string {
  return `${typeof window === "undefined" ? "" : window.location.origin}/checkin/${token}`;
}

export const emptyPerson = (): GuestPerson => ({
  doc_type: "", doc_number: "", first_names: "", last_names: "", nationality: "", birth_date: null,
});
export const emptyGuests = (): GuestData => ({
  main: emptyPerson(), companions: [], motive: "", residence_city: "", origin_city: "", destination_city: null,
});

type Errors = Record<string, string[]> | undefined;

const select = "h-9 w-full rounded-md border border-input bg-background px-2 text-sm";

export function GuestForm({ value, onChange, errors, disabled }: {
  value: GuestData; onChange: (v: GuestData) => void; errors?: Errors; disabled?: boolean;
}) {
  const { m, lang } = useI18n();
  const t = m.registration;
  const countries = useMemo(() => {
    let names: Intl.DisplayNames | null = null;
    try { names = new Intl.DisplayNames([lang], { type: "region" }); } catch { /* sin soporte */ }
    return COUNTRIES.map((c) => ({ code: c, name: names?.of(c) ?? c }))
      .sort((a, b) => (a.code === "CO" ? -1 : b.code === "CO" ? 1 : a.name.localeCompare(b.name, lang)));
  }, [lang]);
  const foreign = [value.main, ...value.companions].some((p) => p.nationality && p.nationality !== "CO");

  const setPerson = (i: number, p: GuestPerson) =>
    onChange(i < 0 ? { ...value, main: p } : { ...value, companions: value.companions.map((c, j) => (j === i ? p : c)) });

  const person = (p: GuestPerson, i: number) => {
    const key = i < 0 ? "main" : `c${i}`;
    const bad = (f: string) => errors?.[key]?.includes(f);
    const set = (f: keyof GuestPerson, v: string) => setPerson(i, { ...p, [f]: v || (f === "birth_date" ? null : "") });
    return (
      <fieldset key={key} disabled={disabled} className="space-y-2 rounded-md border border-border p-3">
        <div className="flex items-center justify-between">
          <legend className="text-sm font-medium">{i < 0 ? t.form.main : t.form.companion(i + 1)}</legend>
          {i >= 0 && !disabled && (
            <button type="button" className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-red-600"
              onClick={() => onChange({ ...value, companions: value.companions.filter((_, j) => j !== i) })}>
              <Trash2 className="h-3 w-3" /> {t.form.remove}
            </button>
          )}
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          <Field label={t.form.nationality} bad={bad("nationality")} t={t.form.invalid}>
            <select className={select} value={p.nationality} onChange={(e) => set("nationality", e.target.value)}>
              <option value="">{t.form.pick}</option>
              {countries.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
            </select>
          </Field>
          <Field label={t.form.docType} bad={bad("doc_type")} t={t.form.invalid}>
            <select className={select} value={p.doc_type} onChange={(e) => set("doc_type", e.target.value)}>
              <option value="">{t.form.pick}</option>
              {(i < 0 ? MAIN_DOCS : DOCS).map((d) => <option key={d} value={d}>{t.docTypes[d]}</option>)}
            </select>
          </Field>
          <Field label={t.form.docNumber} bad={bad("doc_number")} t={t.form.invalid}>
            <Input value={p.doc_number} onChange={(e) => set("doc_number", e.target.value)} autoComplete="off"
              inputMode={["PA", "CE"].includes(p.doc_type) ? "text" : "numeric"} maxLength={24} />
          </Field>
          <Field label={t.form.birthDate} bad={bad("birth_date")} t={t.form.invalid}
            help={p.nationality && p.nationality !== "CO" ? t.form.birthHelp : undefined}>
            <Input type="date" value={p.birth_date ?? ""} onChange={(e) => set("birth_date", e.target.value)} />
          </Field>
          <Field label={t.form.firstNames} bad={bad("first_names")} t={t.form.invalid}>
            <Input value={p.first_names} onChange={(e) => set("first_names", e.target.value)} maxLength={60}
              autoComplete={i < 0 ? "given-name" : "off"} />
          </Field>
          <Field label={t.form.lastNames} bad={bad("last_names")} t={t.form.invalid}>
            <Input value={p.last_names} onChange={(e) => set("last_names", e.target.value)} maxLength={60}
              autoComplete={i < 0 ? "family-name" : "off"} />
          </Field>
        </div>
      </fieldset>
    );
  };

  const tripBad = (f: string) => errors?.trip?.includes(f);
  return (
    <div className="space-y-3">
      {person(value.main, -1)}
      {value.companions.map((c, i) => person(c, i))}
      {!disabled && value.companions.length < MAX_COMPANIONS && (
        <button type="button" className="inline-flex items-center gap-1 text-sm font-medium text-primary"
          onClick={() => onChange({ ...value, companions: [...value.companions, emptyPerson()] })}>
          <Plus className="h-4 w-4" /> {t.form.addCompanion}
        </button>
      )}
      <fieldset disabled={disabled} className="space-y-2 rounded-md border border-border p-3">
        <legend className="text-sm font-medium">{t.form.trip}</legend>
        <div className="grid gap-2 sm:grid-cols-2">
          <Field label={t.form.motive} bad={tripBad("motive")} t={t.form.invalid}>
            <select className={select} value={value.motive} onChange={(e) => onChange({ ...value, motive: e.target.value })}>
              <option value="">{t.form.pick}</option>
              {Object.entries(t.motives).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </Field>
          <Field label={t.form.residence} bad={tripBad("residence_city")} t={t.form.invalid}>
            <Input value={value.residence_city} maxLength={80}
              onChange={(e) => onChange({ ...value, residence_city: e.target.value })} />
          </Field>
          <Field label={t.form.origin} bad={tripBad("origin_city")} t={t.form.invalid}>
            <Input value={value.origin_city} maxLength={80}
              onChange={(e) => onChange({ ...value, origin_city: e.target.value })} />
          </Field>
          <Field label={t.form.destination} bad={tripBad("destination_city")} t={t.form.invalid}
            help={foreign ? t.form.destinationHelp : undefined}>
            <Input value={value.destination_city ?? ""} maxLength={80}
              onChange={(e) => onChange({ ...value, destination_city: e.target.value || null })} />
          </Field>
        </div>
      </fieldset>
    </div>
  );
}

function Field({ label, bad, t, help, children }: {
  label: string; bad?: boolean; t: string; help?: string; children: React.ReactNode;
}) {
  return (
    <label className={cn("block space-y-1 text-xs", bad && "text-red-600")}>
      <span className="font-medium">{label}</span>
      <div className={cn(bad && "rounded-md ring-1 ring-red-500")}>{children}</div>
      {bad ? <span>{t}</span> : help ? <span className="text-muted-foreground">{help}</span> : null}
    </label>
  );
}
