"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { SuggestionCard } from "@/components/suggestions/suggestion-card";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

export default function SuggestionsPage() {
  const qc = useQueryClient();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["suggestions"],
    queryFn: () => api.listSuggestions("proposed"),
  });

  const refresh = () => qc.invalidateQueries({ queryKey: ["suggestions"] });

  const apply = useMutation({
    mutationFn: (id: number) => api.applySuggestion(id),
    onSuccess: () => {
      toast.success("Sugerencia aplicada y publicada");
      refresh();
    },
    onError: () => toast.error("No se pudo aplicar"),
  });
  const approve = useMutation({
    mutationFn: (id: number) => api.approveSuggestion(id),
    onSuccess: refresh,
  });
  const reject = useMutation({
    mutationFn: (id: number) => api.rejectSuggestion(id),
    onSuccess: () => {
      toast("Sugerencia rechazada");
      refresh();
    },
  });

  const busy = apply.isPending || approve.isPending || reject.isPending;

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-xl font-semibold">Sugerencias</h1>
      <p className="text-sm text-muted-foreground">Qué te propongo, con su justificación.</p>

      {isError ? (
        <Card>
          <p className="text-sm text-red-500">No se pudieron cargar las sugerencias.</p>
        </Card>
      ) : isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : !data?.length ? (
        <Card>
          <p className="text-sm text-muted-foreground">
            No hay sugerencias pendientes. Ejecuta un escaneo de eventos para generarlas.
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {data.map((s) => (
            <SuggestionCard
              key={s.id}
              suggestion={s}
              busy={busy}
              onApply={() => apply.mutate(s.id)}
              onApprove={() => approve.mutate(s.id)}
              onReject={() => reject.mutate(s.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
