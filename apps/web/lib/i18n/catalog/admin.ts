// Panel del administrador de plataforma (feature 026). El español es la referencia.
const es = {
  nav: "Administración",
  title: "Administración de la plataforma",
  notAllowed: "Solo el administrador de la plataforma puede ver esta página.",
  invites: {
    title: "Invitaciones",
    description: "Crea un código para cada anfitrión beta. Se muestra una sola vez: cópialo y compártelo.",
    note: "Para quién (p. ej. Ana, Cartagena)",
    days: "Días de validez",
    create: "Crear código",
    created: "Código creado. Cópialo ahora: no se vuelve a mostrar.",
    copy: "Copiar",
    copyLink: "Copiar enlace de registro",
    copied: "Copiado",
    empty: "Aún no hay invitaciones.",
    revoke: "Revocar",
    revoked: "Invitación revocada",
    status: { active: "vigente", used: "usada", expired: "vencida", revoked: "revocada" } as Record<
      string,
      string
    >,
    expires: (d: string) => `vence ${d}`,
    usedBy: (name: string) => `usada por ${name}`,
  },
  accounts: {
    title: "Cuentas",
    description: "Anfitriones registrados. No incluye precios, reservas ni conversaciones.",
    owner: "Dueño",
    connected: "channel manager conectado",
    notConnected: "sin channel manager",
    properties: (n: number) => `${n} propiedad${n === 1 ? "" : "es"}`,
    lastSeen: (d: string) => `último uso ${d}`,
    never: "sin uso aún",
    disable: "Desactivar",
    enable: "Reactivar",
    disabled: "desactivada",
    confirmDisable: (name: string) =>
      `¿Desactivar la cuenta "${name}"? Sus sesiones se cierran y el escaneo la omite; los datos se conservan.`,
  },
  registration: {
    title: "Registro abierto",
    description:
      "Apagado: solo se registra quien tenga un código de invitación (beta). Encendido: cualquiera con un correo.",
    on: "Abierto",
    off: "Solo con invitación",
  },
};

type Shape = typeof es;

const en: Shape = {
  nav: "Administration",
  title: "Platform administration",
  notAllowed: "Only the platform administrator can see this page.",
  invites: {
    title: "Invitations",
    description: "Create one code per beta host. It is shown only once: copy it and share it.",
    note: "Who it's for (e.g. Ana, Cartagena)",
    days: "Days valid",
    create: "Create code",
    created: "Code created. Copy it now: it won't be shown again.",
    copy: "Copy",
    copyLink: "Copy sign-up link",
    copied: "Copied",
    empty: "No invitations yet.",
    revoke: "Revoke",
    revoked: "Invitation revoked",
    status: { active: "active", used: "used", expired: "expired", revoked: "revoked" },
    expires: (d: string) => `expires ${d}`,
    usedBy: (name: string) => `used by ${name}`,
  },
  accounts: {
    title: "Accounts",
    description: "Registered hosts. Prices, bookings and conversations are not included.",
    owner: "Owner",
    connected: "channel manager connected",
    notConnected: "no channel manager",
    properties: (n: number) => `${n} propert${n === 1 ? "y" : "ies"}`,
    lastSeen: (d: string) => `last used ${d}`,
    never: "not used yet",
    disable: "Disable",
    enable: "Re-enable",
    disabled: "disabled",
    confirmDisable: (name: string) =>
      `Disable the account "${name}"? Its sessions are closed and the scan skips it; data is kept.`,
  },
  registration: {
    title: "Open sign-up",
    description:
      "Off: only people with an invitation code can sign up (beta). On: anyone with an email.",
    on: "Open",
    off: "Invitation only",
  },
};

const pt: Shape = {
  nav: "Administração",
  title: "Administração da plataforma",
  notAllowed: "Só o administrador da plataforma pode ver esta página.",
  invites: {
    title: "Convites",
    description: "Crie um código para cada anfitrião beta. Ele aparece só uma vez: copie e compartilhe.",
    note: "Para quem (ex.: Ana, Cartagena)",
    days: "Dias de validade",
    create: "Criar código",
    created: "Código criado. Copie agora: ele não aparece de novo.",
    copy: "Copiar",
    copyLink: "Copiar link de cadastro",
    copied: "Copiado",
    empty: "Ainda não há convites.",
    revoke: "Revogar",
    revoked: "Convite revogado",
    status: { active: "válido", used: "usado", expired: "expirado", revoked: "revogado" },
    expires: (d: string) => `expira ${d}`,
    usedBy: (name: string) => `usado por ${name}`,
  },
  accounts: {
    title: "Contas",
    description: "Anfitriões cadastrados. Não inclui preços, reservas nem conversas.",
    owner: "Dono",
    connected: "channel manager conectado",
    notConnected: "sem channel manager",
    properties: (n: number) => `${n} propriedade${n === 1 ? "" : "s"}`,
    lastSeen: (d: string) => `último uso ${d}`,
    never: "sem uso ainda",
    disable: "Desativar",
    enable: "Reativar",
    disabled: "desativada",
    confirmDisable: (name: string) =>
      `Desativar a conta "${name}"? As sessões são encerradas e o escaneamento a ignora; os dados são mantidos.`,
  },
  registration: {
    title: "Cadastro aberto",
    description:
      "Desligado: só se cadastra quem tem um código de convite (beta). Ligado: qualquer pessoa com e-mail.",
    on: "Aberto",
    off: "Só com convite",
  },
};

const catalog = { es, en, pt };
export default catalog;
