// Textos de cuentas (feature 026). El español es la referencia: en/pt deben tener
// EXACTAMENTE las mismas claves.
const es = {
  loadingUnits: "Cargando tu propiedad…",
  emptyTitle: "Conecta tu channel manager",
  emptyText:
    "Esta cuenta aún no tiene propiedades. Conecta tu Beds24 en Ajustes y StayLever " +
    "importará tu apartamento, su calendario y sus reservas.",
  emptyCta: "Ir a Ajustes",
};

const en: typeof es = {
  loadingUnits: "Loading your property…",
  emptyTitle: "Connect your channel manager",
  emptyText:
    "This account has no properties yet. Connect your Beds24 in Settings and StayLever " +
    "will import your apartment, its calendar and its bookings.",
  emptyCta: "Go to Settings",
};

const pt: typeof es = {
  loadingUnits: "Carregando sua propriedade…",
  emptyTitle: "Conecte seu channel manager",
  emptyText:
    "Esta conta ainda não tem propriedades. Conecte seu Beds24 em Ajustes e o StayLever " +
    "importará seu apartamento, o calendário e as reservas.",
  emptyCta: "Ir para Ajustes",
};

const catalog = { es, en, pt };
export default catalog;
