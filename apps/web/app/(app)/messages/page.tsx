"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { dateTime, dateWithYear, shortRange } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { Conversation, GuestMessage } from "@/lib/types";
import { cn } from "@/lib/utils";

// Mensajes de huéspedes (feature 045, #186). Se leen en vivo de Beds24; nada se envía solo.
const CHANNEL: Record<string, string> = { booking: "Booking.com", airbnb: "Airbnb", direct: "Directa" };
const MAX = 2000;

export default function MessagesPage() {
  return (
    <Suspense fallback={<Skeleton className="h-96" />}>
      <MessagesContent />
    </Suspense>
  );
}

function MessagesContent() {
  const { m, lang } = useI18n();
  const t = m.messages;
  const router = useRouter();
  const selected = useSearchParams().get("booking");
  const inbox = useQuery({ queryKey: ["messages"], queryFn: api.inbox, refetchInterval: 60_000 });

  const open = (ref: string | null) => router.replace(ref ? `/messages?booking=${encodeURIComponent(ref)}` : "/messages");

  if (inbox.isLoading) return <Skeleton className="h-96" />;
  if (inbox.isError) return <p className="text-sm text-red-600">{(inbox.error as Error).message}</p>;
  const data = inbox.data;
  if (!data) return null;

  if (!data.available) {
    return (
      <div className="mx-auto max-w-2xl space-y-3">
        <h1 className="text-xl font-semibold">{t.title}</h1>
        <Card className="space-y-3">
          <CardDescription>{t.unavailable}</CardDescription>
          <Link href="/onboarding"><Button>{t.connect}</Button></Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-semibold">{t.title}</h1>
          {data.unread > 0 && <Badge>{t.unread(data.unread)}</Badge>}
        </div>
        <p className="text-sm text-muted-foreground">{t.intro}</p>
      </div>
      <div className="grid gap-4 md:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
        <div className={cn("space-y-2", selected && "hidden md:block")}>
          {data.conversations.length === 0 && <p className="text-sm text-muted-foreground">{t.empty}</p>}
          {data.conversations.map((c) => (
            <ConversationRow key={c.booking} c={c} active={c.booking === selected} onClick={() => open(c.booking)} />
          ))}
        </div>
        <div className={cn(!selected && "hidden md:block")}>
          {selected ? (
            <ThreadView booking={selected} onBack={() => open(null)} />
          ) : (
            <Card><CardDescription>{t.pick}</CardDescription></Card>
          )}
        </div>
      </div>
    </div>
  );

  function ConversationRow({ c, active, onClick }: { c: Conversation; active: boolean; onClick: () => void }) {
    return (
      <button type="button" onClick={onClick}
        className={cn("w-full rounded-md border p-3 text-left text-sm transition-colors",
          active ? "border-primary bg-primary/5" : "border-border bg-card hover:bg-muted")}>
        <div className="flex items-center justify-between gap-2">
          <span className={cn("truncate", c.unread > 0 && "font-semibold")}>{c.guest_name || t.guest}</span>
          {c.unread > 0 && <Badge>{c.unread}</Badge>}
        </div>
        <p className="truncate text-xs text-muted-foreground">
          {CHANNEL[c.channel] ?? c.channel} · {c.unit ?? ""} · {shortRange(c.check_in, c.check_out, lang)}
        </p>
        <p className={cn("mt-1 line-clamp-2 text-xs", c.unread > 0 ? "text-foreground" : "text-muted-foreground")}>
          {c.last_source === "host" ? `${t.you}: ` : ""}{c.last_text}
        </p>
        {c.last_time && <p className="mt-1 text-[11px] text-muted-foreground">{dateTime(c.last_time, lang)}</p>}
      </button>
    );
  }
}

function ThreadView({ booking, onBack }: { booking: string; onBack: () => void }) {
  const { m, lang } = useI18n();
  const t = m.messages;
  const qc = useQueryClient();
  const [draft, setDraft] = useState("");
  const bottom = useRef<HTMLDivElement>(null);
  const thread = useQuery({ queryKey: ["messages", booking], queryFn: () => api.thread(booking) });

  // Abrir el hilo lo marca leído en Beds24: refresca la bandeja y el contador del menú.
  useEffect(() => {
    if (thread.data) qc.invalidateQueries({ queryKey: ["messages"], exact: true });
  }, [thread.data, qc]);
  useEffect(() => { setDraft(""); }, [booking]);
  useEffect(() => { bottom.current?.scrollIntoView({ block: "end" }); }, [thread.data?.messages.length]);

  const send = useMutation({
    mutationFn: () => api.sendMessage(booking, draft.trim()),
    onSuccess: (data) => {
      qc.setQueryData(["messages", booking], data);
      qc.invalidateQueries({ queryKey: ["messages"], exact: true });
      setDraft("");
      toast.success(t.sent);
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const suggest = useMutation({
    mutationFn: () => api.suggestReply(booking),
    onSuccess: (r) => setDraft(r.text),
    onError: (e: Error) => toast.error(e.message),
  });

  if (thread.isLoading) return <Skeleton className="h-96" />;
  if (thread.isError) return <p className="text-sm text-red-600">{(thread.error as Error).message}</p>;
  const d = thread.data;
  if (!d) return null;

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start gap-2">
        <button type="button" onClick={onBack} className="mt-0.5 md:hidden" aria-label={t.back}>
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div className="min-w-0">
          <CardTitle className="truncate">{d.guest_name || t.guest}</CardTitle>
          <CardDescription>
            {CHANNEL[d.channel] ?? d.channel} · {d.unit ?? ""} · {t.stay(dateWithYear(d.check_in, lang), dateWithYear(d.check_out, lang))}
          </CardDescription>
        </div>
      </div>

      <div className="max-h-[55vh] space-y-2 overflow-y-auto pr-1">
        {d.messages.map((msg, i) => <Bubble key={msg.id ?? i} msg={msg} />)}
        <div ref={bottom} />
      </div>

      {d.can_reply ? (
        <div className="space-y-2 border-t border-border pt-3">
          <textarea
            className="w-full rounded-md border border-border bg-background p-2 text-sm"
            rows={4}
            maxLength={MAX}
            placeholder={t.placeholder}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
          <div className="flex flex-wrap items-center gap-2">
            <Button onClick={() => send.mutate()} disabled={!draft.trim() || send.isPending}>
              {send.isPending ? t.sending : t.send}
            </Button>
            <Button className="bg-muted text-foreground" onClick={() => suggest.mutate()} disabled={suggest.isPending}>
              <Sparkles className="mr-1 h-4 w-4" />
              {suggest.isPending ? t.suggesting : t.suggest}
            </Button>
            <span className="ml-auto text-[11px] text-muted-foreground">{draft.length}/{MAX}</span>
          </div>
          <p className="text-[11px] text-muted-foreground">{t.suggestHint}</p>
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">{t.cantReply}</p>
      )}
    </Card>
  );

  function Bubble({ msg }: { msg: GuestMessage }) {
    const mine = msg.source === "host";
    const label = { guest: d!.guest_name || t.guest, host: t.you, system: t.system, internalNote: t.note }[msg.source];
    return (
      <div className={cn("flex", mine ? "justify-end" : "justify-start")}>
        <div className={cn("max-w-[85%] rounded-lg px-3 py-2 text-sm",
          mine ? "bg-primary text-primary-foreground"
            : msg.source === "guest" ? "bg-muted"
            : "border border-dashed border-border text-muted-foreground")}>
          <p className={cn("text-[11px] font-medium", mine ? "text-primary-foreground/80" : "text-muted-foreground")}>
            {label}{msg.time ? ` · ${dateTime(msg.time, lang)}` : ""}
          </p>
          <p className="whitespace-pre-wrap break-words">{msg.text}</p>
        </div>
      </div>
    );
  }
}
