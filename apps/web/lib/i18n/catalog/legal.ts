// Feature 028: aceptación de documentos, "Tus datos" (exportar y borrar la cuenta).
// El español es la referencia: en/pt con las MISMAS claves.
const es = {
  accept: {
    before: "Acepto los ",
    terms: "Términos de uso",
    and: " y la ",
    privacy: "Política de privacidad",
    after: ".",
    required: "Debes aceptar los Términos de uso y la Política de privacidad.",
  },
  gate: {
    title: "Términos y privacidad",
    description:
      "Para seguir usando StayLever, lee y acepta los Términos de uso y la Política de " +
      "privacidad. Explican qué datos guardamos, por cuánto tiempo y cómo los protegemos.",
    updated: "Versión del {date}.",
    submit: "Aceptar y continuar",
    logout: "Cerrar sesión",
  },
  data: {
    title: "Tus datos",
    description:
      "Descarga una copia de todo lo que StayLever guarda de tu cuenta o borra la cuenta " +
      "con todos sus datos.",
    export: "Descargar copia (JSON)",
    exporting: "Preparando…",
    exported: "Copia descargada",
    deleteTitle: "Borrar mi cuenta",
    deleteWarning:
      "Se borran para siempre tus propiedades, reservas, sugerencias, conversaciones y " +
      "ajustes, y se cierran tus sesiones. Las copias de seguridad desaparecen solas en " +
      "máximo 7 días. No se puede deshacer.",
    typeName: (name: string) => `Escribe el nombre de la cuenta (${name}) para confirmar`,
    password: "Tu contraseña",
    sendCode: "Enviarme un código por correo",
    codeSent: "Te enviamos un código de 6 dígitos (vence en 15 minutos).",
    code: "Código de 6 dígitos",
    delete: "Borrar cuenta para siempre",
    deleting: "Borrando…",
    protected: "La cuenta principal de la plataforma no se puede borrar desde aquí.",
    nameMismatch: "El nombre de la cuenta no coincide.",
    invalid: "No pudimos confirmar que eres tú. Revisa la contraseña o el código.",
  },
  adminDeleted: "Eliminada por su dueño",
};

type Shape = typeof es;

const en: Shape = {
  accept: {
    before: "I accept the ",
    terms: "Terms of use",
    and: " and the ",
    privacy: "Privacy policy",
    after: ".",
    required: "You must accept the Terms of use and the Privacy policy.",
  },
  gate: {
    title: "Terms and privacy",
    description:
      "To keep using StayLever, read and accept the Terms of use and the Privacy policy. " +
      "They explain what data we keep, for how long and how we protect it.",
    updated: "Version of {date}.",
    submit: "Accept and continue",
    logout: "Sign out",
  },
  data: {
    title: "Your data",
    description:
      "Download a copy of everything StayLever keeps about your account, or delete the " +
      "account with all its data.",
    export: "Download copy (JSON)",
    exporting: "Preparing…",
    exported: "Copy downloaded",
    deleteTitle: "Delete my account",
    deleteWarning:
      "Your properties, bookings, suggestions, conversations and settings are deleted " +
      "forever and your sessions are closed. Backups disappear automatically within 7 days. " +
      "This cannot be undone.",
    typeName: (name: string) => `Type the account name (${name}) to confirm`,
    password: "Your password",
    sendCode: "Email me a code",
    codeSent: "We sent you a 6-digit code (it expires in 15 minutes).",
    code: "6-digit code",
    delete: "Delete account forever",
    deleting: "Deleting…",
    protected: "The platform's main account can't be deleted from here.",
    nameMismatch: "The account name doesn't match.",
    invalid: "We couldn't confirm it's you. Check the password or the code.",
  },
  adminDeleted: "Deleted by its owner",
};

const pt: Shape = {
  accept: {
    before: "Aceito os ",
    terms: "Termos de uso",
    and: " e a ",
    privacy: "Política de privacidade",
    after: ".",
    required: "Você deve aceitar os Termos de uso e a Política de privacidade.",
  },
  gate: {
    title: "Termos e privacidade",
    description:
      "Para continuar usando o StayLever, leia e aceite os Termos de uso e a Política de " +
      "privacidade. Eles explicam quais dados guardamos, por quanto tempo e como os protegemos.",
    updated: "Versão de {date}.",
    submit: "Aceitar e continuar",
    logout: "Sair",
  },
  data: {
    title: "Seus dados",
    description:
      "Baixe uma cópia de tudo o que o StayLever guarda da sua conta ou exclua a conta com " +
      "todos os seus dados.",
    export: "Baixar cópia (JSON)",
    exporting: "Preparando…",
    exported: "Cópia baixada",
    deleteTitle: "Excluir minha conta",
    deleteWarning:
      "Suas propriedades, reservas, sugestões, conversas e configurações são excluídas para " +
      "sempre e suas sessões são encerradas. As cópias de segurança desaparecem sozinhas em " +
      "até 7 dias. Não dá para desfazer.",
    typeName: (name: string) => `Digite o nome da conta (${name}) para confirmar`,
    password: "Sua senha",
    sendCode: "Enviar um código por e-mail",
    codeSent: "Enviamos um código de 6 dígitos (expira em 15 minutos).",
    code: "Código de 6 dígitos",
    delete: "Excluir conta para sempre",
    deleting: "Excluindo…",
    protected: "A conta principal da plataforma não pode ser excluída por aqui.",
    nameMismatch: "O nome da conta não confere.",
    invalid: "Não conseguimos confirmar que é você. Verifique a senha ou o código.",
  },
  adminDeleted: "Excluída pelo dono",
};

const catalog = { es, en, pt };
export default catalog;
