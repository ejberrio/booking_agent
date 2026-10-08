// Textos del área "connection" (feature 021). El español es la referencia: en/pt deben
// tener EXACTAMENTE las mismas claves (TypeScript falla si falta o sobra alguna).
const es = {
  title: "Conexión y onboarding",
  connect: {
    title: "1. Conectar Beds24",
    description: "Verifica que las credenciales del .env funcionan.",
    test: "Probar conexión",
    testing: "Probando…",
    status: "Estado:",
    failed: "No se pudo conectar a Beds24",
  },
  statuses: {
    connected: "conectado",
    invalid: "credenciales inválidas",
    unconfigured: "sin configurar",
  } as Record<string, string>,
  import: {
    title: "2. Importar datos",
    description: "Trae propiedades, precios y reservas desde Beds24.",
    run: "Importar ahora",
    running: "Importando…",
    done: (created: number, issues: number) =>
      `Importación: ${created} creado${created !== 1 ? "s" : ""}, ${issues} incidencia${issues !== 1 ? "s" : ""}`,
    failed: "Falló la importación",
  },
  unit: {
    title: "3. Propiedad activa",
    description: "Id de la unidad a gestionar (tras importar).",
    label: "Unidad",
    saved: "Unidad activa guardada",
  },
};

type Shape = typeof es;

const en: Shape = {
  title: "Connection and onboarding",
  connect: {
    title: "1. Connect Beds24",
    description: "Checks that the credentials in .env work.",
    test: "Test connection",
    testing: "Testing…",
    status: "Status:",
    failed: "Couldn't connect to Beds24",
  },
  statuses: {
    connected: "connected",
    invalid: "invalid credentials",
    unconfigured: "not configured",
  },
  import: {
    title: "2. Import data",
    description: "Pulls properties, prices and bookings from Beds24.",
    run: "Import now",
    running: "Importing…",
    done: (created: number, issues: number) =>
      `Import: ${created} created, ${issues} issue${issues !== 1 ? "s" : ""}`,
    failed: "Import failed",
  },
  unit: {
    title: "3. Active property",
    description: "ID of the unit to manage (after importing).",
    label: "Unit",
    saved: "Active unit saved",
  },
};

const pt: Shape = {
  title: "Conexão e onboarding",
  connect: {
    title: "1. Conectar o Beds24",
    description: "Verifica se as credenciais do .env funcionam.",
    test: "Testar conexão",
    testing: "Testando…",
    status: "Status:",
    failed: "Não foi possível conectar ao Beds24",
  },
  statuses: {
    connected: "conectado",
    invalid: "credenciais inválidas",
    unconfigured: "não configurado",
  },
  import: {
    title: "2. Importar dados",
    description: "Traz propriedades, preços e reservas do Beds24.",
    run: "Importar agora",
    running: "Importando…",
    done: (created: number, issues: number) =>
      `Importação: ${created} criado${created !== 1 ? "s" : ""}, ${issues} incidência${issues !== 1 ? "s" : ""}`,
    failed: "Falha na importação",
  },
  unit: {
    title: "3. Propriedade ativa",
    description: "ID da unidade a gerenciar (após importar).",
    label: "Unidade",
    saved: "Unidade ativa salva",
  },
};

const catalog = { es, en, pt };
export default catalog;
