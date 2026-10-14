// Páginas públicas (feature 026, entrega 4): presentación y política de privacidad. Google las
// exige para publicar "Entrar con Google". El español es la referencia: en/pt con las MISMAS claves.
const CONTACT = "hello@staylever.com";
const PRIVACY = "privacy@staylever.com";

const es = {
  contact: CONTACT,
  privacyContact: PRIVACY,
  nav: { login: "Entrar", register: "Crear cuenta", privacy: "Privacidad", terms: "Términos", home: "Inicio", back: "Volver" },
  welcome: {
    title: "Precios inteligentes para tu apartamento turístico",
    lead:
      "StayLever ayuda a anfitriones con 1 a 5 apartamentos a fijar el precio de cada noche en " +
      "Booking.com y Airbnb: mira tu calendario, los eventos de tu ciudad y el mercado, y te " +
      "propone cambios que tú apruebas.",
    features: [
      {
        title: "Sugerencias de precio",
        text: "Cada día revisa las próximas semanas y propone subir o bajar noches concretas, con su explicación.",
      },
      {
        title: "Tú decides",
        text: "Nada se publica sin tu aprobación: aceptas, ajustas o descartas cada sugerencia.",
      },
      {
        title: "Eventos y mercado",
        text: "Tiene en cuenta conciertos, ferias y temporadas de tu ciudad, y los precios de la zona.",
      },
      {
        title: "Conectado a tu channel manager",
        text: "Funciona con Beds24: tus precios llegan a Booking.com y Airbnb sin tocar cada plataforma.",
      },
      {
        title: "Asistente y avisos",
        text: "Pregúntale en lenguaje natural por tu calendario y recibe avisos de reservas en el celular.",
      },
    ],
    beta: "StayLever está en beta por invitación.",
    cta: "Entrar",
    ctaRegister: "Tengo una invitación",
  },
  privacy: {
    title: "Política de privacidad",
    updated: "Última actualización: 14 de octubre de 2026",
    sections: [
      {
        title: "Quiénes somos",
        body: [
          "StayLever es una herramienta para anfitriones de alquiler vacacional que sugiere precios " +
            "por noche y los publica en su channel manager cuando el anfitrión lo aprueba. Esta " +
            "política explica qué datos tratamos y cómo, de acuerdo con la Ley 1581 de 2012 de " +
            `Colombia. Para cualquier asunto de privacidad escríbenos a ${PRIVACY}.`,
        ],
      },
      {
        title: "Qué datos tratamos",
        body: [
          "Tu cuenta: nombre, correo, la contraseña (guardada solo como hash, nunca legible) y, si " +
            "entras con Google, el identificador de tu cuenta de Google, tu nombre y tu correo. No " +
            "accedemos a tu Gmail, tus contactos ni otros datos de Google.",
          "Tu propiedad: lo que importamos de tu channel manager (Beds24) para hacer las " +
            "sugerencias: apartamentos, calendario, tarifas, disponibilidad y reservas (fechas, " +
            "precio y, si el canal lo envía, el nombre del huésped).",
          "Lo que haces en StayLever: tus preferencias, las sugerencias que apruebas o descartas, " +
            "las conversaciones con el asistente y los teléfonos registrados para avisos.",
          "Datos técnicos: registros de uso y de errores necesarios para operar y proteger el " +
            "servicio (sin contraseñas ni datos de huéspedes).",
        ],
      },
      {
        title: "Datos de tus huéspedes",
        body: [
          "Sobre los datos de tus huéspedes, tú eres el Responsable del tratamiento y StayLever " +
            "es el Encargado: los tratamos solo por tu cuenta y para prestarte el servicio. De " +
            "cada huésped guardamos únicamente el nombre que envía tu channel manager (nunca " +
            "teléfono, correo ni documento), lo ves solo tú dentro de tu cuenta y nadie más: " +
            "ni otras cuentas ni los administradores de StayLever. Nunca va a la IA ni a los " +
            "avisos del celular.",
        ],
      },
      {
        title: "Para qué los usamos",
        body: [
          "Solo para prestarte el servicio: identificarte, calcular y explicar sugerencias de " +
            "precio, publicar en tu channel manager lo que apruebes, enviarte correos de acceso y " +
            "avisos al celular, y mantener la seguridad. No vendemos tus datos, no hacemos " +
            "publicidad y no los usamos para entrenar modelos de IA propios.",
        ],
      },
      {
        title: "Con quién los compartimos",
        body: [
          "Con proveedores que nos ayudan a operar, solo en lo necesario: Railway (servidores) y " +
            "Neon (base de datos), en Estados Unidos; OpenAI (el asistente y las sugerencias: " +
            "recibe datos de calendario y precios, nunca nombres de huéspedes); Tavily (búsqueda " +
            "de eventos públicos de tu ciudad); Resend (correos); Google Firebase (avisos al " +
            "celular); Google (si eliges entrar con Google) y Beds24, tu channel manager.",
          "Al usar StayLever aceptas que tus datos se traten en servidores fuera de Colombia con " +
            "estos proveedores.",
        ],
      },
      {
        title: "Cuánto tiempo los guardamos",
        body: [
          "Los datos de tu cuenta, mientras esté activa. El nombre de cada huésped se borra " +
            "automáticamente 1 año después de la fecha de salida; la reserva se conserva sin él " +
            "(fechas, precio y canal) para las estadísticas de precios.",
          "Si borras tu cuenta desde Ajustes, eliminamos de inmediato todos sus datos; las copias " +
            "de seguridad de la base de datos desaparecen solas en un máximo de 7 días.",
        ],
      },
      {
        title: "Página pública e informe gratis",
        body: [
          "Para pedir el informe gratis no necesitas cuenta: guardamos el municipio y los precios " +
            "que escribes, sin tu nombre ni tu correo. Para limitar abusos usamos un código derivado " +
            "de tu IP que cambia cada día; no guardamos la IP. Contamos visitas e informes solo como " +
            "totales por día, sin cookies ni rastreo.",
          "Si te unes a la lista de espera, guardamos tu correo con tu autorización solo para " +
            "avisarte de la beta; lo borramos cuando te invitamos, si nos lo pides o a los 12 meses.",
        ],
      },
      {
        title: "Tus derechos",
        body: [
          "Puedes conocer, actualizar, rectificar y suprimir tus datos, y revocar tu autorización. " +
            "En Ajustes → Tus datos descargas una copia de todo o borras tu cuenta; tu nombre y el " +
            `de tu cuenta los cambias en Ajustes → Mi cuenta. Para lo demás escribe a ${PRIVACY}; ` +
            "respondemos en máximo 15 días hábiles.",
        ],
      },
      {
        title: "Seguridad",
        body: [
          "Las conexiones van cifradas (HTTPS), las credenciales de tu channel manager se guardan " +
            "cifradas, las contraseñas con Argon2id y cada cuenta está aislada de las demás.",
        ],
      },
      {
        title: "Cambios",
        body: [
          "Si cambiamos esta política, actualizaremos la fecha de arriba y te avisaremos por " +
            "correo cuando el cambio sea importante.",
        ],
      },
    ],
  },
};

type Shape = typeof es;

const en: Shape = {
  contact: CONTACT,
  privacyContact: PRIVACY,
  nav: { login: "Sign in", register: "Sign up", privacy: "Privacy", terms: "Terms", home: "Home", back: "Back" },
  welcome: {
    title: "Smart pricing for your vacation rental",
    lead:
      "StayLever helps hosts with 1 to 5 apartments set the price of each night on Booking.com " +
      "and Airbnb: it looks at your calendar, local events and the market, and suggests changes " +
      "that you approve.",
    features: [
      {
        title: "Price suggestions",
        text: "Every day it reviews the coming weeks and suggests raising or lowering specific nights, with its reasoning.",
      },
      {
        title: "You decide",
        text: "Nothing is published without your approval: accept, adjust or dismiss each suggestion.",
      },
      {
        title: "Events and market",
        text: "It considers concerts, fairs and seasons in your city, and prices in your area.",
      },
      {
        title: "Connected to your channel manager",
        text: "Works with Beds24: your prices reach Booking.com and Airbnb without touching each platform.",
      },
      {
        title: "Assistant and alerts",
        text: "Ask about your calendar in plain language and get booking alerts on your phone.",
      },
    ],
    beta: "StayLever is in invite-only beta.",
    cta: "Sign in",
    ctaRegister: "I have an invitation",
  },
  privacy: {
    title: "Privacy policy",
    updated: "Last updated: October 14, 2026",
    sections: [
      {
        title: "Who we are",
        body: [
          "StayLever is a tool for vacation rental hosts that suggests nightly prices and publishes " +
            "them to their channel manager when the host approves. This policy explains which data " +
            "we process and how, in accordance with Colombia's Law 1581 of 2012. For any privacy " +
            `matter, write to ${PRIVACY}.`,
        ],
      },
      {
        title: "What data we process",
        body: [
          "Your account: name, email, your password (stored only as a hash, never readable) and, if " +
            "you sign in with Google, your Google account identifier, name and email. We do not " +
            "access your Gmail, contacts or any other Google data.",
          "Your property: what we import from your channel manager (Beds24) to make suggestions: " +
            "apartments, calendar, rates, availability and bookings (dates, price and, if the " +
            "channel sends it, the guest's name).",
          "What you do in StayLever: your preferences, the suggestions you approve or dismiss, " +
            "conversations with the assistant and the phones registered for alerts.",
          "Technical data: usage and error logs needed to run and protect the service (no " +
            "passwords or guest data).",
        ],
      },
      {
        title: "Your guests' data",
        body: [
          "For your guests' data, you are the Controller and StayLever is the Processor: we " +
            "process it only on your behalf and to provide the service. For each guest we keep " +
            "only the name your channel manager sends (never phone, email or ID), only you see " +
            "it inside your account and no one else: not other accounts nor StayLever's " +
            "administrators. It never goes to the AI or to phone alerts.",
        ],
      },
      {
        title: "How we use it",
        body: [
          "Only to provide the service: identify you, compute and explain price suggestions, " +
            "publish what you approve to your channel manager, send you sign-in emails and phone " +
            "alerts, and keep things secure. We do not sell your data, show ads, or use it to " +
            "train our own AI models.",
        ],
      },
      {
        title: "Who we share it with",
        body: [
          "With providers that help us operate, only as needed: Railway (servers) and Neon " +
            "(database), in the United States; OpenAI (the assistant and suggestions: it receives " +
            "calendar and price data, never guest names); Tavily (search for public events in " +
            "your city); Resend (email); Google Firebase (phone alerts); Google (if you choose to " +
            "sign in with Google) and Beds24, your channel manager.",
          "By using StayLever you agree that your data is processed on servers outside Colombia " +
            "by these providers.",
        ],
      },
      {
        title: "How long we keep it",
        body: [
          "Your account data, while the account is active. Each guest's name is erased " +
            "automatically 1 year after the check-out date; the booking stays without it (dates, " +
            "price and channel) for price statistics.",
          "If you delete your account in Settings, we erase all its data right away; database " +
            "backups disappear automatically within 7 days.",
        ],
      },
      {
        title: "Public page and free report",
        body: [
          "You don't need an account to request the free report: we keep the town and prices you " +
            "type, without your name or email. To limit abuse we use a code derived from your IP " +
            "that changes every day; we don't store the IP. We count visits and reports only as " +
            "daily totals, without cookies or tracking.",
          "If you join the waitlist, we keep your email with your consent only to tell you about " +
            "the beta; we delete it when we invite you, when you ask, or after 12 months.",
        ],
      },
      {
        title: "Your rights",
        body: [
          "You can access, update, correct and delete your data, and withdraw your consent. In " +
            "Settings → Your data you download a copy of everything or delete your account; you " +
            "change your name and your account's name in Settings → My account. For anything " +
            `else write to ${PRIVACY}; we reply within 15 business days.`,
        ],
      },
      {
        title: "Security",
        body: [
          "Connections are encrypted (HTTPS), your channel manager credentials are stored " +
            "encrypted, passwords with Argon2id, and each account is isolated from the others.",
        ],
      },
      {
        title: "Changes",
        body: [
          "If we change this policy, we will update the date above and notify you by email when " +
            "the change is significant.",
        ],
      },
    ],
  },
};

const pt: Shape = {
  contact: CONTACT,
  privacyContact: PRIVACY,
  nav: { login: "Entrar", register: "Criar conta", privacy: "Privacidade", terms: "Termos", home: "Início", back: "Voltar" },
  welcome: {
    title: "Preços inteligentes para o seu apartamento de temporada",
    lead:
      "O StayLever ajuda anfitriões com 1 a 5 apartamentos a definir o preço de cada noite no " +
      "Booking.com e no Airbnb: olha o seu calendário, os eventos da sua cidade e o mercado, e " +
      "sugere mudanças que você aprova.",
    features: [
      {
        title: "Sugestões de preço",
        text: "Todo dia revisa as próximas semanas e sugere subir ou baixar noites específicas, com a explicação.",
      },
      {
        title: "Você decide",
        text: "Nada é publicado sem a sua aprovação: aceite, ajuste ou descarte cada sugestão.",
      },
      {
        title: "Eventos e mercado",
        text: "Considera shows, feiras e temporadas da sua cidade, e os preços da região.",
      },
      {
        title: "Conectado ao seu channel manager",
        text: "Funciona com o Beds24: seus preços chegam ao Booking.com e ao Airbnb sem mexer em cada plataforma.",
      },
      {
        title: "Assistente e avisos",
        text: "Pergunte sobre o seu calendário em linguagem natural e receba avisos de reservas no celular.",
      },
    ],
    beta: "O StayLever está em beta por convite.",
    cta: "Entrar",
    ctaRegister: "Tenho um convite",
  },
  privacy: {
    title: "Política de privacidade",
    updated: "Última atualização: 14 de outubro de 2026",
    sections: [
      {
        title: "Quem somos",
        body: [
          "O StayLever é uma ferramenta para anfitriões de aluguel por temporada que sugere preços " +
            "por noite e os publica no seu channel manager quando o anfitrião aprova. Esta " +
            "política explica quais dados tratamos e como, de acordo com a Lei 1581 de 2012 da " +
            `Colômbia. Para qualquer assunto de privacidade, escreva para ${PRIVACY}.`,
        ],
      },
      {
        title: "Quais dados tratamos",
        body: [
          "Sua conta: nome, e-mail, a senha (guardada apenas como hash, nunca legível) e, se você " +
            "entra com o Google, o identificador da sua conta Google, seu nome e seu e-mail. Não " +
            "acessamos o seu Gmail, contatos nem outros dados do Google.",
          "Sua propriedade: o que importamos do seu channel manager (Beds24) para fazer as " +
            "sugestões: apartamentos, calendário, tarifas, disponibilidade e reservas (datas, " +
            "preço e, se o canal enviar, o nome do hóspede).",
          "O que você faz no StayLever: suas preferências, as sugestões que aprova ou descarta, " +
            "as conversas com o assistente e os telefones registrados para avisos.",
          "Dados técnicos: registros de uso e de erros necessários para operar e proteger o " +
            "serviço (sem senhas nem dados de hóspedes).",
        ],
      },
      {
        title: "Dados dos seus hóspedes",
        body: [
          "Sobre os dados dos seus hóspedes, você é o Responsável pelo tratamento e o StayLever " +
            "é o Encarregado (operador): tratamos esses dados apenas em seu nome e para prestar " +
            "o serviço. De cada hóspede guardamos somente o nome que o seu channel manager envia " +
            "(nunca telefone, e-mail ou documento), só você o vê dentro da sua conta e mais " +
            "ninguém: nem outras contas nem os administradores do StayLever. Ele nunca vai para " +
            "a IA nem para os avisos do celular.",
        ],
      },
      {
        title: "Para que os usamos",
        body: [
          "Apenas para prestar o serviço: identificar você, calcular e explicar sugestões de " +
            "preço, publicar no seu channel manager o que você aprovar, enviar e-mails de acesso " +
            "e avisos ao celular, e manter a segurança. Não vendemos seus dados, não fazemos " +
            "publicidade e não os usamos para treinar modelos de IA próprios.",
        ],
      },
      {
        title: "Com quem compartilhamos",
        body: [
          "Com fornecedores que nos ajudam a operar, só no necessário: Railway (servidores) e " +
            "Neon (banco de dados), nos Estados Unidos; OpenAI (o assistente e as sugestões: " +
            "recebe dados de calendário e preços, nunca nomes de hóspedes); Tavily (busca de " +
            "eventos públicos da sua cidade); Resend (e-mails); Google Firebase (avisos ao " +
            "celular); Google (se você escolher entrar com o Google) e Beds24, o seu channel manager.",
          "Ao usar o StayLever você aceita que seus dados sejam tratados em servidores fora da " +
            "Colômbia por esses fornecedores.",
        ],
      },
      {
        title: "Por quanto tempo os guardamos",
        body: [
          "Os dados da sua conta, enquanto ela estiver ativa. O nome de cada hóspede é apagado " +
            "automaticamente 1 ano após a data de saída; a reserva continua sem ele (datas, preço " +
            "e canal) para as estatísticas de preços.",
          "Se você excluir sua conta em Configurações, apagamos todos os seus dados na hora; as " +
            "cópias de segurança do banco de dados desaparecem sozinhas em até 7 dias.",
        ],
      },
      {
        title: "Página pública e relatório grátis",
        body: [
          "Para pedir o relatório grátis você não precisa de conta: guardamos o município e os " +
            "preços que você digita, sem seu nome nem seu e-mail. Para limitar abusos usamos um " +
            "código derivado do seu IP que muda todo dia; não guardamos o IP. Contamos visitas e " +
            "relatórios apenas como totais por dia, sem cookies nem rastreamento.",
          "Se você entrar na lista de espera, guardamos seu e-mail com sua autorização apenas para " +
            "avisar da beta; apagamos quando convidamos você, se pedir ou após 12 meses.",
        ],
      },
      {
        title: "Seus direitos",
        body: [
          "Você pode conhecer, atualizar, retificar e excluir seus dados, e revogar sua " +
            "autorização. Em Configurações → Seus dados você baixa uma cópia de tudo ou exclui sua " +
            "conta; seu nome e o da conta você muda em Configurações → Minha conta. Para o resto, " +
            `escreva para ${PRIVACY}; respondemos em até 15 dias úteis.`,
        ],
      },
      {
        title: "Segurança",
        body: [
          "As conexões são criptografadas (HTTPS), as credenciais do seu channel manager são " +
            "guardadas criptografadas, as senhas com Argon2id e cada conta é isolada das demais.",
        ],
      },
      {
        title: "Mudanças",
        body: [
          "Se mudarmos esta política, atualizaremos a data acima e avisaremos por e-mail quando a " +
            "mudança for importante.",
        ],
      },
    ],
  },
};

const catalog = { es, en, pt };
export default catalog;
