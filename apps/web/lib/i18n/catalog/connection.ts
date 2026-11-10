// Textos del área "connection" (features 021 y 044). El español es la referencia: en/pt deben
// tener EXACTAMENTE las mismas claves (TypeScript falla si falta o sobra alguna).
const es = {
  title: "Conectar Beds24",
  intro:
    "Conecta tu cuenta de Beds24 para que StayLever lea tus reservas y aplique precios en Booking y Airbnb. Toma unos 3 minutos.",
  steps: ["Generar el código", "Pegarlo", "Elegir qué conectar", "Importar"],
  step1: {
    title: "1. Genera un código de invitación en Beds24",
    open: "Abrir Beds24",
    path: "En Beds24: Settings → Marketplace → API → «Generate invite code».",
    perms: "Marca estos permisos (el resto déjalo sin marcar):",
    read: "Lectura (read)",
    write: "Escritura (write)",
    copy: "Copiar",
    copied: "Copiado",
    expires: "El código vence en pocos minutos: pégalo enseguida. No es la «API Key» de Account Access.",
    next: "Ya tengo el código",
  },
  step2: {
    title: "2. Pega el código",
    placeholder: "Código de invitación de Beds24",
    validate: "Conectar",
    validating: "Conectando…",
    back: "Volver",
  },
  step3: {
    title: "3. Elige qué conectar",
    hint: "Desmarca lo que no quieras gestionar con StayLever. Puedes cambiarlo después.",
    taken: "ya está conectada a otra cuenta de StayLever",
    units: (n: number) => `${n} unidad${n === 1 ? "" : "es"}`,
    none: "Elige al menos una habitación.",
    save: "Guardar e importar",
  },
  step4: {
    title: "4. Importando tus datos",
    running: "Trayendo reservas, precios y calendario… puede tardar un minuto.",
    done: (created: number) => `Listo: ${created} elemento${created === 1 ? "" : "s"} nuevo${created === 1 ? "" : "s"}.`,
    go: "Ir al tablero",
    failed: "Falló la importación. Intenta de nuevo en unos minutos.",
  },
  connected: {
    title: "Beds24 conectado",
    account: (name: string) => `Cuenta: ${name}`,
    since: (d: string) => `Verificado: ${d}`,
    change: "Cambiar qué conecto",
    reconnect: "Reconectar con un código nuevo",
    reimport: "Importar de nuevo",
  },
  manual: {
    title: "Tu cuenta está en modo sin conexión",
    body: "Pasar de «sin conexión» a Beds24 conservando tu historial llega en la próxima entrega. Mientras tanto, sigue usando StayLever sin conexión.",
  },
  sandbox: "Ambiente de pruebas: el canal es simulado. Escribe cualquier código para seguir el asistente.",
  banner: {
    lost: "Se perdió la conexión con Beds24: no vemos reservas nuevas ni aplicamos precios.",
    reconnect: "Reconectar",
  },
  guide: "¿Aún no conectas Airbnb y Booking a Beds24? Ver la guía de Beds24",
  statuses: {
    connected: "conectado",
    invalid: "conexión caída",
    unconfigured: "sin configurar",
  } as Record<string, string>,
};

type Shape = typeof es;

const en: Shape = {
  title: "Connect Beds24",
  intro:
    "Connect your Beds24 account so StayLever can read your bookings and apply prices on Booking and Airbnb. It takes about 3 minutes.",
  steps: ["Generate the code", "Paste it", "Choose what to connect", "Import"],
  step1: {
    title: "1. Generate an invite code in Beds24",
    open: "Open Beds24",
    path: "In Beds24: Settings → Marketplace → API → “Generate invite code”.",
    perms: "Tick these permissions (leave the rest unticked):",
    read: "Read",
    write: "Write",
    copy: "Copy",
    copied: "Copied",
    expires: "The code expires in a few minutes: paste it right away. It is not the Account Access “API Key”.",
    next: "I have the code",
  },
  step2: {
    title: "2. Paste the code",
    placeholder: "Beds24 invite code",
    validate: "Connect",
    validating: "Connecting…",
    back: "Back",
  },
  step3: {
    title: "3. Choose what to connect",
    hint: "Untick what you don't want to manage with StayLever. You can change it later.",
    taken: "already connected to another StayLever account",
    units: (n: number) => `${n} unit${n === 1 ? "" : "s"}`,
    none: "Choose at least one room.",
    save: "Save and import",
  },
  step4: {
    title: "4. Importing your data",
    running: "Bringing bookings, prices and calendar… it may take a minute.",
    done: (created: number) => `Done: ${created} new item${created === 1 ? "" : "s"}.`,
    go: "Go to dashboard",
    failed: "The import failed. Try again in a few minutes.",
  },
  connected: {
    title: "Beds24 connected",
    account: (name: string) => `Account: ${name}`,
    since: (d: string) => `Verified: ${d}`,
    change: "Change what I connect",
    reconnect: "Reconnect with a new code",
    reimport: "Import again",
  },
  manual: {
    title: "Your account is in offline mode",
    body: "Moving from offline to Beds24 while keeping your history arrives in the next release. Meanwhile, keep using StayLever offline.",
  },
  sandbox: "Test environment: the channel is simulated. Type any code to go through the wizard.",
  banner: {
    lost: "The connection with Beds24 was lost: we can't see new bookings or apply prices.",
    reconnect: "Reconnect",
  },
  guide: "Haven't connected Airbnb and Booking to Beds24 yet? See the Beds24 guide",
  statuses: {
    connected: "connected",
    invalid: "connection lost",
    unconfigured: "not configured",
  },
};

const pt: Shape = {
  title: "Conectar o Beds24",
  intro:
    "Conecte sua conta do Beds24 para que o StayLever leia suas reservas e aplique preços no Booking e no Airbnb. Leva uns 3 minutos.",
  steps: ["Gerar o código", "Colar", "Escolher o que conectar", "Importar"],
  step1: {
    title: "1. Gere um código de convite no Beds24",
    open: "Abrir o Beds24",
    path: "No Beds24: Settings → Marketplace → API → «Generate invite code».",
    perms: "Marque estas permissões (deixe o resto desmarcado):",
    read: "Leitura (read)",
    write: "Escrita (write)",
    copy: "Copiar",
    copied: "Copiado",
    expires: "O código expira em poucos minutos: cole logo. Não é a «API Key» do Account Access.",
    next: "Já tenho o código",
  },
  step2: {
    title: "2. Cole o código",
    placeholder: "Código de convite do Beds24",
    validate: "Conectar",
    validating: "Conectando…",
    back: "Voltar",
  },
  step3: {
    title: "3. Escolha o que conectar",
    hint: "Desmarque o que não quiser gerenciar com o StayLever. Pode mudar depois.",
    taken: "já está conectada a outra conta do StayLever",
    units: (n: number) => `${n} unidade${n === 1 ? "" : "s"}`,
    none: "Escolha pelo menos um quarto.",
    save: "Salvar e importar",
  },
  step4: {
    title: "4. Importando seus dados",
    running: "Trazendo reservas, preços e calendário… pode levar um minuto.",
    done: (created: number) => `Pronto: ${created} item${created === 1 ? "" : "s"} novo${created === 1 ? "" : "s"}.`,
    go: "Ir para o painel",
    failed: "A importação falhou. Tente de novo em alguns minutos.",
  },
  connected: {
    title: "Beds24 conectado",
    account: (name: string) => `Conta: ${name}`,
    since: (d: string) => `Verificado: ${d}`,
    change: "Mudar o que conecto",
    reconnect: "Reconectar com um código novo",
    reimport: "Importar de novo",
  },
  manual: {
    title: "Sua conta está no modo sem conexão",
    body: "Passar de «sem conexão» para o Beds24 mantendo seu histórico chega na próxima entrega. Enquanto isso, continue usando o StayLever sem conexão.",
  },
  sandbox: "Ambiente de testes: o canal é simulado. Digite qualquer código para seguir o assistente.",
  banner: {
    lost: "A conexão com o Beds24 caiu: não vemos novas reservas nem aplicamos preços.",
    reconnect: "Reconectar",
  },
  guide: "Ainda não conectou o Airbnb e o Booking ao Beds24? Veja o guia do Beds24",
  statuses: {
    connected: "conectado",
    invalid: "conexão caída",
    unconfigured: "não configurado",
  },
};

const catalog = { es, en, pt };
export default catalog;
