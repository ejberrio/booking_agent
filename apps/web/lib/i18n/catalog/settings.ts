// Textos del área "settings" (feature 021). El español es la referencia: en/pt deben
// tener EXACTAMENTE las mismas claves (TypeScript falla si falta o sobra alguna).
const es = {
  title: "Configuración",
  beds24: {
    title: "Integración Beds24",
    description: "Estado de la conexión con el Channel Manager.",
    check: "Comprobar",
    status: {
      connected: "conectado",
      invalid: "credenciales inválidas",
      unconfigured: "sin configurar",
      error: "error",
    } as Record<string, string>,
  },
  webhooks: {
    title: "Avisos en tiempo real",
    description:
      "Beds24 avisa a StayLever cuando entra, cambia o se cancela una reserva, y el calendario se actualiza solo en ~1 minuto. La sincronización diaria sigue como respaldo.",
    states: {
      unconfigured: "sin configurar",
      never: "esperando el primer aviso",
      active: "funcionando",
      idle: "sin actividad (7+ días)",
    },
    lastNotice: "Último aviso:",
    noneYet: "todavía ninguno",
    stats: (accepted: number, rejected: number, failed: number) =>
      `7 días: ${accepted} aceptado${accepted !== 1 ? "s" : ""}, ${rejected} rechazado${rejected !== 1 ? "s" : ""}, ${failed} con error`,
    copyNow: "Copia esta línea ahora: no se volverá a mostrar.",
    lineCopied: "Línea copiada",
    generate: "Generar clave",
    generateNew: "Generar clave nueva",
    confirmRegenerate:
      "Ya hay una clave. Si generas otra, la anterior dejará de funcionar. ¿Continuar?",
    step1: "Genera la clave aquí y copia la línea que aparece.",
    step2Open: "En Beds24 abre",
    step2Section: ", sección",
    step5Paste: ": pega la línea copiada (empieza por",
    step5Press: "). Pulsa",
    step6: (active: string) => `Con el próximo cambio de una reserva, aquí verás "${active}".`,
    loadError: "No se pudo cargar el estado de los avisos.",
  },
  minPrice: {
    title: "Precio mínimo por noche",
    description:
      "Piso de las promociones que crean las sugerencias a la baja: el precio que paga el huésped, incluso con los descuentos del celular, nunca queda por debajo.",
    placeholder: "Ej.: 230000",
    current: (price: string) => `Actual: ${price}`,
    none: "Sin precio mínimo",
    remove: "Quitar",
    saved: "Precio mínimo guardado",
    removed: "Precio mínimo quitado",
  },
  offsets: {
    title: "Precio por canal",
    description:
      "Recargo/descuento porcentual por canal sobre el precio base (0% = mismo precio). Airbnb muestra el importe en la moneda del huésped (su margen cambiario no depende de nosotros).",
    inactive: "(inactivo)",
    basePrice: "precio base",
    basePriceHint: "Este canal vende al precio base; su ajuste no es configurable",
    range: "% (−50 a 100; 0 = quitar)",
    preview: "Ver propuesta",
    example: "ej.:",
    base: "base",
    apply: "Confirmar y aplicar",
    applied: (channel: string, pct: string) => `Ajuste de ${channel} aplicado: ${pct}%`,
    appliedUnverified: (issue: string) => `Aplicado, pero sin verificar: ${issue}`,
    checkIssues: "revisa incidencias",
    inactiveWarning: (channel: string) =>
      `el canal ${channel} está inactivo: el ajuste no tendrá efecto hasta reactivarlo`,
  },
  pois: {
    title: "Sitios de interés (POIs)",
    description:
      "Lugares cercanos que dirigen las búsquedas de eventos del escaneo (p. ej. un escenario nuevo con su fecha de inauguración).",
    always: "siempre relevante",
    inactive: "inactivo",
    deactivate: "Desactivar",
    reactivate: "Reactivar",
    remove: "Borrar",
    namePlaceholder: "Nombre (p. ej. Daviarena)",
    notePlaceholder: "Nota (distancia/contexto)",
    fromLabel: "Desde",
    toLabel: "Hasta",
    add: "Añadir sitio",
    added: "Sitio añadido — el próximo escaneo lo usará",
  },
  scan: {
    title: "Escaneo de eventos y mercado",
    effectiveZone: "Zona efectiva:",
    queriesPerRun: "consultas por corrida:",
    freeQuota: "(el proveedor gratis tiene ~1000 créditos/mes).",
    zonePlaceholder: "Zona (vacío = ciudad + dirección)",
    queriesPlaceholder: "Consultas por corrida",
    saved: "Configuración del escaneo guardada",
  },
  secrets: {
    title: "Secretos",
    description:
      "API keys y tokens de los servicios. Write-only: el valor nunca se muestra; pega uno nuevo para rotarlo. La rotación aplica de inmediato en la API; el escaneo diario la toma en su próxima corrida.",
    labels: {
      openai_api_key: "OpenAI API key",
      anthropic_api_key: "Anthropic API key",
      search_api_key: "Tavily API key",
      beds24_refresh_token: "Beds24 refresh token",
      beds24_webhook_key: "Clave de avisos de Beds24",
    },
    services: {
      openai_api_key: "Agente de chat y extracción de eventos",
      anthropic_api_key: "Agente de chat (proveedor alternativo)",
      search_api_key: "Escaneo de eventos y mercado",
      beds24_refresh_token: "Todo el canal (precios, reservas, disponibilidad)",
      beds24_webhook_key: "Reservas en tiempo real (avisos de Beds24)",
    },
    help: {
      openai_api_key:
        'platform.openai.com → Settings → API keys → "Create new secret key" (permisos: All). Empieza por "sk-" y solo se muestra una vez: cópiala y pégala aquí. Requiere saldo en Settings → Billing.',
      anthropic_api_key:
        'console.anthropic.com → Settings → API Keys → "Create Key". Empieza por "sk-ant-" y solo se muestra una vez. Requiere créditos en Settings → Billing. Opcional: solo se usa si eliges Anthropic como proveedor del chat.',
      search_api_key:
        'app.tavily.com → Overview → API Keys → copia la clave (o crea una con "+"). Empieza por "tvly-". El plan gratis (1.000 créditos/mes) alcanza para el escaneo diario.',
      beds24_webhook_key:
        'Se genera arriba, en la tarjeta "Avisos en tiempo real" → "Generar clave", y se pega en Beds24 (Booking Webhook → Custom Header). No hace falta pegarla aquí; para rotarla, genera una nueva allí.',
    },
    sourceUnreadable: "guardado ilegible — se usa la variable de entorno",
    sourceApp: "guardado en la app",
    sourceEnv: "por variable de entorno",
    notConfigured: "sin configurar",
    configured: (hint: string) => `configurado ${hint}`,
    newValuePlaceholder: "Pegar valor nuevo…",
    invitePlaceholder: "…o pegar código de invitación de Beds24",
    redeem: "Canjear",
    inviteHelp:
      'Beds24 → Settings → Marketplace → API → "Generate invite code". Permisos: READ en bookings, bookings-personal, inventory, properties y channels; WRITE solo en inventory y channels. Pega el código (vence en minutos) y pulsa Canjear. No es la "API Key" de Account Access: esa es la API antigua.',
    test: "Probar",
    remove: "Quitar",
    saved: "Secreto guardado — la rotación ya aplica",
    removed: "Valor guardado eliminado (se usa la variable de entorno si existe)",
    redeemed: "Código canjeado — Beds24 reconectado",
    newTokenSaved: "token nuevo guardado — pulsa Probar",
    recentChanges: "Últimos cambios",
    auditSet: (hint: string) => `guardado ${hint}`,
    auditDeleted: "eliminado",
  },
  llm: {
    title: "Modelo de LLM",
    description:
      "Modelos configurados en el servidor (.env): general para conversación y de acciones para escrituras. Las API keys se rotan en la tarjeta Secretos.",
  },
  prefs: {
    title: "Preferencias",
    activeUnit: (unit: number) => `Unidad activa: ${unit} (se ajusta en Conexión).`,
  },
};

type Shape = typeof es;

const en: Shape = {
  title: "Settings",
  beds24: {
    title: "Beds24 integration",
    description: "Connection status with the Channel Manager.",
    check: "Check",
    status: {
      connected: "connected",
      invalid: "invalid credentials",
      unconfigured: "not configured",
      error: "error",
    },
  },
  webhooks: {
    title: "Real-time notifications",
    description:
      "Beds24 notifies StayLever when a booking comes in, changes or is canceled, and the calendar updates on its own in ~1 minute. The daily sync stays on as a backup.",
    states: {
      unconfigured: "not configured",
      never: "waiting for the first notification",
      active: "working",
      idle: "no activity (7+ days)",
    },
    lastNotice: "Last notification:",
    noneYet: "none yet",
    stats: (accepted: number, rejected: number, failed: number) =>
      `7 days: ${accepted} accepted, ${rejected} rejected, ${failed} with errors`,
    copyNow: "Copy this line now: it won't be shown again.",
    lineCopied: "Line copied",
    generate: "Generate key",
    generateNew: "Generate new key",
    confirmRegenerate:
      "A key already exists. If you generate a new one, the old one will stop working. Continue?",
    step1: "Generate the key here and copy the line that appears.",
    step2Open: "In Beds24, open",
    step2Section: ", section",
    step5Paste: ": paste the copied line (it starts with",
    step5Press: "). Click",
    step6: (active: string) => `On the next booking change, you'll see "${active}" here.`,
    loadError: "Couldn't load the notification status.",
  },
  minPrice: {
    title: "Minimum price per night",
    description:
      "Floor for the promotions created from price-decrease suggestions: what the guest pays, even with mobile discounts, never goes below it.",
    placeholder: "e.g. 230000",
    current: (price: string) => `Current: ${price}`,
    none: "No minimum price",
    remove: "Remove",
    saved: "Minimum price saved",
    removed: "Minimum price removed",
  },
  offsets: {
    title: "Price per channel",
    description:
      "Percentage markup/discount per channel on top of the base price (0% = same price). Airbnb shows the amount in the guest's currency (its exchange margin is out of our hands).",
    inactive: "(inactive)",
    basePrice: "base price",
    basePriceHint: "This channel sells at the base price; its adjustment can't be configured",
    range: "% (−50 to 100; 0 = remove)",
    preview: "Preview",
    example: "e.g.:",
    base: "base",
    apply: "Confirm and apply",
    applied: (channel: string, pct: string) => `${channel} adjustment applied: ${pct}%`,
    appliedUnverified: (issue: string) => `Applied, but not verified: ${issue}`,
    checkIssues: "check the sync issues",
    inactiveWarning: (channel: string) =>
      `the ${channel} channel is inactive: the adjustment won't take effect until it's reactivated`,
  },
  pois: {
    title: "Places of interest (POIs)",
    description:
      "Nearby places that steer the scan's event searches (e.g. a new venue with its opening date).",
    always: "always relevant",
    inactive: "inactive",
    deactivate: "Deactivate",
    reactivate: "Reactivate",
    remove: "Delete",
    namePlaceholder: "Name (e.g. Daviarena)",
    notePlaceholder: "Note (distance/context)",
    fromLabel: "From",
    toLabel: "To",
    add: "Add place",
    added: "Place added — the next scan will use it",
  },
  scan: {
    title: "Event and market scan",
    effectiveZone: "Effective area:",
    queriesPerRun: "searches per run:",
    freeQuota: "(the free provider has ~1,000 credits/month).",
    zonePlaceholder: "Area (empty = city + address)",
    queriesPlaceholder: "Searches per run",
    saved: "Scan settings saved",
  },
  secrets: {
    title: "Secrets",
    description:
      "API keys and tokens for the services. Write-only: the value is never shown; paste a new one to rotate it. Rotation takes effect immediately in the API; the daily scan picks it up on its next run.",
    labels: {
      openai_api_key: "OpenAI API key",
      anthropic_api_key: "Anthropic API key",
      search_api_key: "Tavily API key",
      beds24_refresh_token: "Beds24 refresh token",
      beds24_webhook_key: "Beds24 notification key",
    },
    services: {
      openai_api_key: "Chat agent and event extraction",
      anthropic_api_key: "Chat agent (alternative provider)",
      search_api_key: "Event and market scan",
      beds24_refresh_token: "The whole channel (prices, bookings, availability)",
      beds24_webhook_key: "Real-time bookings (Beds24 notifications)",
    },
    help: {
      openai_api_key:
        'platform.openai.com → Settings → API keys → "Create new secret key" (permissions: All). It starts with "sk-" and is only shown once: copy it and paste it here. Requires a balance in Settings → Billing.',
      anthropic_api_key:
        'console.anthropic.com → Settings → API Keys → "Create Key". It starts with "sk-ant-" and is only shown once. Requires credits in Settings → Billing. Optional: only used if you pick Anthropic as the chat provider.',
      search_api_key:
        'app.tavily.com → Overview → API Keys → copy the key (or create one with "+"). It starts with "tvly-". The free plan (1,000 credits/month) is enough for the daily scan.',
      beds24_webhook_key:
        'It\'s generated above, in the "Real-time notifications" card → "Generate key", and pasted into Beds24 (Booking Webhook → Custom Header). No need to paste it here; to rotate it, generate a new one there.',
    },
    sourceUnreadable: "saved value unreadable — using the environment variable",
    sourceApp: "saved in the app",
    sourceEnv: "from environment variable",
    notConfigured: "not configured",
    configured: (hint: string) => `configured ${hint}`,
    newValuePlaceholder: "Paste new value…",
    invitePlaceholder: "…or paste a Beds24 invite code",
    redeem: "Redeem",
    inviteHelp:
      'Beds24 → Settings → Marketplace → API → "Generate invite code". Permissions: READ on bookings, bookings-personal, inventory, properties and channels; WRITE only on inventory and channels. Paste the code (it expires in minutes) and click Redeem. This is not the Account Access "API Key": that one is for the old API.',
    test: "Test",
    remove: "Remove",
    saved: "Secret saved — rotation is already in effect",
    removed: "Saved value removed (the environment variable is used if present)",
    redeemed: "Code redeemed — Beds24 reconnected",
    newTokenSaved: "new token saved — click Test",
    recentChanges: "Recent changes",
    auditSet: (hint: string) => `saved ${hint}`,
    auditDeleted: "removed",
  },
  llm: {
    title: "LLM model",
    description:
      "Models configured on the server (.env): a general one for conversation and an actions one for writes. API keys are rotated in the Secrets card.",
  },
  prefs: {
    title: "Preferences",
    activeUnit: (unit: number) => `Active unit: ${unit} (change it in Connection).`,
  },
};

const pt: Shape = {
  title: "Configurações",
  beds24: {
    title: "Integração Beds24",
    description: "Status da conexão com o Channel Manager.",
    check: "Verificar",
    status: {
      connected: "conectado",
      invalid: "credenciais inválidas",
      unconfigured: "não configurado",
      error: "erro",
    },
  },
  webhooks: {
    title: "Avisos em tempo real",
    description:
      "O Beds24 avisa o StayLever quando uma reserva entra, muda ou é cancelada, e o calendário se atualiza sozinho em ~1 minuto. A sincronização diária continua como reserva de segurança.",
    states: {
      unconfigured: "não configurado",
      never: "aguardando o primeiro aviso",
      active: "funcionando",
      idle: "sem atividade (7+ dias)",
    },
    lastNotice: "Último aviso:",
    noneYet: "nenhum ainda",
    stats: (accepted: number, rejected: number, failed: number) =>
      `7 dias: ${accepted} aceito${accepted !== 1 ? "s" : ""}, ${rejected} rejeitado${rejected !== 1 ? "s" : ""}, ${failed} com erro`,
    copyNow: "Copie esta linha agora: ela não será exibida novamente.",
    lineCopied: "Linha copiada",
    generate: "Gerar chave",
    generateNew: "Gerar nova chave",
    confirmRegenerate:
      "Já existe uma chave. Se você gerar outra, a anterior deixará de funcionar. Continuar?",
    step1: "Gere a chave aqui e copie a linha que aparece.",
    step2Open: "No Beds24, abra",
    step2Section: ", seção",
    step5Paste: ": cole a linha copiada (começa com",
    step5Press: "). Clique em",
    step6: (active: string) => `Na próxima alteração de uma reserva, você verá "${active}" aqui.`,
    loadError: "Não foi possível carregar o status dos avisos.",
  },
  minPrice: {
    title: "Preço mínimo por noite",
    description:
      "Piso das promoções criadas pelas sugestões de redução: o preço que o hóspede paga, mesmo com os descontos de celular, nunca fica abaixo dele.",
    placeholder: "Ex.: 230000",
    current: (price: string) => `Atual: ${price}`,
    none: "Sem preço mínimo",
    remove: "Remover",
    saved: "Preço mínimo salvo",
    removed: "Preço mínimo removido",
  },
  offsets: {
    title: "Preço por canal",
    description:
      "Acréscimo/desconto percentual por canal sobre o preço base (0% = mesmo preço). O Airbnb mostra o valor na moeda do hóspede (a margem cambial dele não depende de nós).",
    inactive: "(inativo)",
    basePrice: "preço base",
    basePriceHint: "Este canal vende pelo preço base; o ajuste dele não é configurável",
    range: "% (−50 a 100; 0 = remover)",
    preview: "Ver proposta",
    example: "ex.:",
    base: "base",
    apply: "Confirmar e aplicar",
    applied: (channel: string, pct: string) => `Ajuste do ${channel} aplicado: ${pct}%`,
    appliedUnverified: (issue: string) => `Aplicado, mas sem verificação: ${issue}`,
    checkIssues: "revise as incidências",
    inactiveWarning: (channel: string) =>
      `o canal ${channel} está inativo: o ajuste não terá efeito até reativá-lo`,
  },
  pois: {
    title: "Pontos de interesse (POIs)",
    description:
      "Locais próximos que orientam as buscas de eventos da varredura (ex.: uma nova casa de shows com a data de inauguração).",
    always: "sempre relevante",
    inactive: "inativo",
    deactivate: "Desativar",
    reactivate: "Reativar",
    remove: "Excluir",
    namePlaceholder: "Nome (ex.: Daviarena)",
    notePlaceholder: "Nota (distância/contexto)",
    fromLabel: "De",
    toLabel: "Até",
    add: "Adicionar local",
    added: "Local adicionado — a próxima varredura vai usá-lo",
  },
  scan: {
    title: "Varredura de eventos e mercado",
    effectiveZone: "Zona efetiva:",
    queriesPerRun: "consultas por execução:",
    freeQuota: "(o provedor gratuito tem ~1.000 créditos/mês).",
    zonePlaceholder: "Zona (vazio = cidade + endereço)",
    queriesPlaceholder: "Consultas por execução",
    saved: "Configuração da varredura salva",
  },
  secrets: {
    title: "Segredos",
    description:
      "API keys e tokens dos serviços. Somente escrita: o valor nunca é exibido; cole um novo para fazer a rotação. A rotação vale imediatamente na API; a varredura diária a aplica na próxima execução.",
    labels: {
      openai_api_key: "OpenAI API key",
      anthropic_api_key: "Anthropic API key",
      search_api_key: "Tavily API key",
      beds24_refresh_token: "Beds24 refresh token",
      beds24_webhook_key: "Chave de avisos do Beds24",
    },
    services: {
      openai_api_key: "Agente de chat e extração de eventos",
      anthropic_api_key: "Agente de chat (provedor alternativo)",
      search_api_key: "Varredura de eventos e mercado",
      beds24_refresh_token: "Todo o canal (preços, reservas, disponibilidade)",
      beds24_webhook_key: "Reservas em tempo real (avisos do Beds24)",
    },
    help: {
      openai_api_key:
        'platform.openai.com → Settings → API keys → "Create new secret key" (permissões: All). Começa com "sk-" e só é exibida uma vez: copie e cole aqui. Exige saldo em Settings → Billing.',
      anthropic_api_key:
        'console.anthropic.com → Settings → API Keys → "Create Key". Começa com "sk-ant-" e só é exibida uma vez. Exige créditos em Settings → Billing. Opcional: só é usada se você escolher a Anthropic como provedor do chat.',
      search_api_key:
        'app.tavily.com → Overview → API Keys → copie a chave (ou crie uma com "+"). Começa com "tvly-". O plano gratuito (1.000 créditos/mês) basta para a varredura diária.',
      beds24_webhook_key:
        'É gerada acima, no cartão "Avisos em tempo real" → "Gerar chave", e colada no Beds24 (Booking Webhook → Custom Header). Não é preciso colá-la aqui; para fazer a rotação, gere uma nova lá.',
    },
    sourceUnreadable: "valor salvo ilegível — usando a variável de ambiente",
    sourceApp: "salvo no app",
    sourceEnv: "por variável de ambiente",
    notConfigured: "não configurado",
    configured: (hint: string) => `configurado ${hint}`,
    newValuePlaceholder: "Colar novo valor…",
    invitePlaceholder: "…ou colar código de convite do Beds24",
    redeem: "Resgatar",
    inviteHelp:
      'Beds24 → Settings → Marketplace → API → "Generate invite code". Permissões: READ em bookings, bookings-personal, inventory, properties e channels; WRITE só em inventory e channels. Cole o código (expira em minutos) e clique em Resgatar. Não é a "API Key" de Account Access: essa é da API antiga.',
    test: "Testar",
    remove: "Remover",
    saved: "Segredo salvo — a rotação já está valendo",
    removed: "Valor salvo removido (usa-se a variável de ambiente, se existir)",
    redeemed: "Código resgatado — Beds24 reconectado",
    newTokenSaved: "novo token salvo — clique em Testar",
    recentChanges: "Últimas alterações",
    auditSet: (hint: string) => `salvo ${hint}`,
    auditDeleted: "removido",
  },
  llm: {
    title: "Modelo de LLM",
    description:
      "Modelos configurados no servidor (.env): um geral para conversa e um de ações para escritas. As API keys são trocadas no cartão Segredos.",
  },
  prefs: {
    title: "Preferências",
    activeUnit: (unit: number) => `Unidade ativa: ${unit} (ajuste em Conexão).`,
  },
};

const catalog = { es, en, pt };
export default catalog;
