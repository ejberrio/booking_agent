// Menú, login y elementos globales (feature 021). El español es la referencia.
const es = {
  nav: {
    dashboard: "Dashboard",
    calendar: "Calendario",
    chat: "Chat",
    suggestions: "Sugerencias",
    offers: "Ofertas",
    connection: "Conexión",
    settings: "Configuración",
  },
  menu: "Menú",
  home: "Ir al inicio",
  logout: "Cerrar sesión",
  toggleTheme: "Cambiar tema",
  login: {
    subtitle: "Ingresa la contraseña del host para continuar.",
    password: "Contraseña",
    submit: "Entrar",
    submitting: "Entrando…",
    failed: "No se pudo iniciar sesión",
    wrongPassword: "Contraseña incorrecta",
  },
};

type Shape = typeof es;

const en: Shape = {
  nav: {
    dashboard: "Dashboard",
    calendar: "Calendar",
    chat: "Chat",
    suggestions: "Suggestions",
    offers: "Offers",
    connection: "Connection",
    settings: "Settings",
  },
  menu: "Menu",
  home: "Go to home",
  logout: "Sign out",
  toggleTheme: "Toggle theme",
  login: {
    subtitle: "Enter the host password to continue.",
    password: "Password",
    submit: "Sign in",
    submitting: "Signing in…",
    failed: "Couldn't sign in",
    wrongPassword: "Wrong password",
  },
};

const pt: Shape = {
  nav: {
    dashboard: "Painel",
    calendar: "Calendário",
    chat: "Chat",
    suggestions: "Sugestões",
    offers: "Ofertas",
    connection: "Conexão",
    settings: "Configurações",
  },
  menu: "Menu",
  home: "Ir para o início",
  logout: "Sair",
  toggleTheme: "Alternar tema",
  login: {
    subtitle: "Digite a senha do anfitrião para continuar.",
    password: "Senha",
    submit: "Entrar",
    submitting: "Entrando…",
    failed: "Não foi possível entrar",
    wrongPassword: "Senha incorreta",
  },
};

const catalog = { es, en, pt };
export default catalog;
