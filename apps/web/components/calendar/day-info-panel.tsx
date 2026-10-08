"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { BookingView, CalendarNote } from "@/lib/types";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

interface Props {
  unitTypeId: number;
  selection: { from: string; to: string };
  bookings: BookingView[]; // reservas cuya noche cae en el día seleccionado (solo si es un día)
  notes: CalendarNote[]; // notas que cubren la selección
}

/** Detalle del día/rango seleccionado (feature 016): reservas (solo lectura) y
 *  notas del host (memoria local — nunca tocan el Channel Manager). */
export function DayInfoPanel({ unitTypeId, selection, bookings, notes }: Props) {
  const { m } = useI18n();
  const CHANNEL_NAMES: Record<string, string> = {
    booking: "Booking.com",
    airbnb: "Airbnb",
    direct: m.calendar.channelDirect,
  };
  const qc = useQueryClient();
  const refresh = () => qc.invalidateQueries({ queryKey: ["calendar-notes"] });
  const onError = (e: Error) => toast.error(e.message);

  const [draft, setDraft] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editText, setEditText] = useState("");

  const create = useMutation({
    mutationFn: () =>
      api.createCalendarNote({
        unit_type_id: unitTypeId,
        date_from: selection.from,
        date_to: selection.to,
        text: draft,
      }),
    onSuccess: () => {
      toast.success(m.calendar.noteSaved);
      setDraft("");
      refresh();
    },
    onError,
  });
  const update = useMutation({
    mutationFn: (id: number) => api.updateCalendarNote(id, { text: editText }),
    onSuccess: () => {
      setEditingId(null);
      refresh();
    },
    onError,
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.deleteCalendarNote(id),
    onSuccess: () => {
      toast(m.calendar.noteDeleted);
      refresh();
    },
    onError,
  });

  const singleDay = selection.from === selection.to;
  const rangeLabel = singleDay ? selection.from : `${selection.from} → ${selection.to}`;

  return (
    <Card>
      {singleDay && bookings.length > 0 && (
        <div className="mb-3">
          <p className="mb-2 text-xs font-medium">
            {m.calendar.bookingsHeader(bookings.length)} · {selection.from}
          </p>
          <div className="space-y-2">
            {bookings.map((b) => (
              <div key={b.id} className="space-y-0.5 rounded-md border border-border p-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-medium">
                    {b.guest_name ?? <span className="text-muted-foreground">{m.calendar.noGuestName}</span>}
                  </span>
                  <Badge variant="muted">{CHANNEL_NAMES[b.channel] ?? b.channel}</Badge>
                </div>
                <p className="text-muted-foreground">
                  {b.check_in} → {b.check_out} · {m.common.nights(b.nights)}
                </p>
                <p className="text-[10px] text-muted-foreground">
                  {m.calendar.bookingStatus[b.status] ?? b.status}
                  {b.external_ref ? ` · ${m.calendar.ref} ${b.external_ref}` : ""}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="mb-2 text-xs font-medium">{m.calendar.notesHeader} · {rangeLabel}</p>
      {notes.length > 0 && (
        <div className="mb-2 space-y-2">
          {notes.map((n) => (
            <div key={n.id} className="space-y-1 rounded-md border border-border p-2 text-xs">
              {editingId === n.id ? (
                <>
                  <textarea
                    className="w-full rounded-md border border-border bg-background p-2 text-xs"
                    rows={2}
                    maxLength={500}
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                  />
                  <div className="flex gap-2">
                    <Button onClick={() => update.mutate(n.id)} disabled={update.isPending}>
                      {m.common.save}
                    </Button>
                    <Button
                      className="bg-muted text-foreground"
                      onClick={() => setEditingId(null)}
                    >
                      {m.common.cancel}
                    </Button>
                  </div>
                </>
              ) : (
                <>
                  <p>{n.text}</p>
                  <p className="text-[10px] text-muted-foreground">
                    {n.date_from === n.date_to ? n.date_from : `${n.date_from} → ${n.date_to}`}
                  </p>
                  <div className="flex gap-1">
                    <Button
                      className="bg-transparent px-2 text-muted-foreground hover:bg-muted"
                      onClick={() => {
                        setEditingId(n.id);
                        setEditText(n.text);
                      }}
                    >
                      {m.common.edit}
                    </Button>
                    <Button
                      className="bg-transparent px-2 text-muted-foreground hover:bg-muted"
                      onClick={() => remove.mutate(n.id)}
                      disabled={remove.isPending}
                    >
                      {m.calendar.deleteNote}
                    </Button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
      <textarea
        className="w-full rounded-md border border-border bg-background p-2 text-xs"
        rows={2}
        maxLength={500}
        placeholder={m.calendar.notePlaceholder(rangeLabel)}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
      />
      <Button
        className="mt-2"
        onClick={() => create.mutate()}
        disabled={create.isPending || !draft.trim()}
      >
        {m.calendar.saveNote}
      </Button>
    </Card>
  );
}
