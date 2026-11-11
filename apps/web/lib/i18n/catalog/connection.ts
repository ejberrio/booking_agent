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
  link: {
    title: "Asocia tus apartamentos",
    hint: "Hoy usas StayLever sin conexión. Elige a qué habitación de Beds24 corresponde cada apartamento: conservas su historial (precios, sugerencias, notas y rentabilidad) y las reservas que llegaron por iCal se concilian con las de Beds24.",
    pick: "Elige la habitación…",
    missing: "Asocia cada apartamento con una habitación elegida.",
  },
  guideTitle: "Guía: conectar Airbnb y Booking a Beds24",
  guideItems: [
    "Airbnb: en Beds24, Channel Manager → Airbnb → conectar con la cuenta del DUEÑO del anuncio (un co-anfitrión no puede). Asigna cada anuncio a su habitación e importa las reservas.",
    "Airbnb solo admite un software de precios por cuenta: desconecta otro channel manager antes. Apaga los Precios Inteligentes (Smart Pricing) de Airbnb para que manden los de StayLever.",
    "Booking.com: en la Extranet, Cuenta → Proveedor de conectividad → busca «Beds24» y acepta. Luego en Beds24, Channel Manager → Booking.com, escribe tu Hotel ID y asigna habitaciones y planes de tarifa.",
    "Booking.com solo permite un proveedor de conectividad por propiedad, y al conectarlo desaparece el iCal de la Extranet.",
    "Después revisa en cada plataforma que precios y disponibilidad coincidan con Beds24.",
  ],
  guideLinks: { airbnb: "Ayuda de Beds24 para Airbnb", booking: "Ayuda de Beds24 para Booking.com" },
  sandbox: "Ambiente de pruebas: el canal es simulado. Escribe cualquier código para seguir el asistente.",
  banner: {
    lost: "Se perdió la conexión con Beds24: no vemos reservas nuevas ni aplicamos precios.",
    reconnect: "Reconectar",
  },
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
  link: {
    title: "Link your apartments",
    hint: "You use StayLever offline today. Choose which Beds24 room each apartment is: you keep its history (prices, suggestions, notes and profitability) and the bookings that came by iCal are reconciled with Beds24's.",
    pick: "Choose the room…",
    missing: "Link each apartment to a chosen room.",
  },
  guideTitle: "Guide: connect Airbnb and Booking to Beds24",
  guideItems: [
    "Airbnb: in Beds24, Channel Manager → Airbnb → connect with the listing OWNER's account (a co-host can't). Map each listing to its room and import bookings.",
    "Airbnb allows only one pricing software per account: disconnect any other channel manager first. Turn off Airbnb Smart Pricing so StayLever's prices apply.",
    "Booking.com: in the Extranet, Account → Connectivity provider → search “Beds24” and accept. Then in Beds24, Channel Manager → Booking.com, enter your Hotel ID and map rooms and rate plans.",
    "Booking.com allows one connectivity provider per property, and once connected the Extranet iCal disappears.",
    "Afterwards, check on each platform that prices and availability match Beds24.",
  ],
  guideLinks: { airbnb: "Beds24 help for Airbnb", booking: "Beds24 help for Booking.com" },
  sandbox: "Test environment: the channel is simulated. Type any code to go through the wizard.",
  banner: {
    lost: "The connection with Beds24 was lost: we can't see new bookings or apply prices.",
    reconnect: "Reconnect",
  },
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
  link: {
    title: "Associe seus apartamentos",
    hint: "Hoje você usa o StayLever sem conexão. Escolha a qual quarto do Beds24 corresponde cada apartamento: você mantém o histórico (preços, sugestões, notas e rentabilidade) e as reservas que chegaram por iCal são conciliadas com as do Beds24.",
    pick: "Escolha o quarto…",
    missing: "Associe cada apartamento a um quarto escolhido.",
  },
  guideTitle: "Guia: conectar o Airbnb e o Booking ao Beds24",
  guideItems: [
    "Airbnb: no Beds24, Channel Manager → Airbnb → conecte com a conta do DONO do anúncio (um coanfitrião não pode). Associe cada anúncio ao seu quarto e importe as reservas.",
    "O Airbnb aceita só um software de preços por conta: desconecte outro channel manager antes. Desligue os Preços Inteligentes (Smart Pricing) do Airbnb para valerem os do StayLever.",
    "Booking.com: na Extranet, Conta → Provedor de conectividade → procure «Beds24» e aceite. Depois no Beds24, Channel Manager → Booking.com, informe seu Hotel ID e associe quartos e planos de tarifa.",
    "O Booking.com permite um provedor de conectividade por propriedade, e ao conectar o iCal da Extranet desaparece.",
    "Depois confira em cada plataforma se preços e disponibilidade batem com o Beds24.",
  ],
  guideLinks: { airbnb: "Ajuda do Beds24 para o Airbnb", booking: "Ajuda do Beds24 para o Booking.com" },
  sandbox: "Ambiente de testes: o canal é simulado. Digite qualquer código para seguir o assistente.",
  banner: {
    lost: "A conexão com o Beds24 caiu: não vemos novas reservas nem aplicamos preços.",
    reconnect: "Reconectar",
  },
  statuses: {
    connected: "conectado",
    invalid: "conexão caída",
    unconfigured: "não configurado",
  },
};

const catalog = { es, en, pt };
export default catalog;
