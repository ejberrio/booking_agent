// Textos compartidos (feature 021). El español es la referencia.
const es = {
  save: "Guardar",
  cancel: "Cancelar",
  confirm: "Confirmar",
  close: "Cerrar",
  delete: "Eliminar",
  edit: "Editar",
  add: "Agregar",
  retry: "Reintentar",
  loading: "Cargando…",
  copy: "Copiar",
  copied: "Copiado",
  copyFailed: "No se pudo copiar; selecciónalo a mano",
  yes: "Sí",
  no: "No",
  done: "Listo",
  language: "Idioma",
  loadError: "No se pudo cargar.",
  nights: (n: number) => `${n} noche${n !== 1 ? "s" : ""}`,
};

type Shape = typeof es;

const en: Shape = {
  save: "Save",
  cancel: "Cancel",
  confirm: "Confirm",
  close: "Close",
  delete: "Delete",
  edit: "Edit",
  add: "Add",
  retry: "Retry",
  loading: "Loading…",
  copy: "Copy",
  copied: "Copied",
  copyFailed: "Couldn't copy; select it manually",
  yes: "Yes",
  no: "No",
  done: "Done",
  language: "Language",
  loadError: "Couldn't load.",
  nights: (n: number) => `${n} night${n !== 1 ? "s" : ""}`,
};

const pt: Shape = {
  save: "Salvar",
  cancel: "Cancelar",
  confirm: "Confirmar",
  close: "Fechar",
  delete: "Excluir",
  edit: "Editar",
  add: "Adicionar",
  retry: "Tentar novamente",
  loading: "Carregando…",
  copy: "Copiar",
  copied: "Copiado",
  copyFailed: "Não foi possível copiar; selecione manualmente",
  yes: "Sim",
  no: "Não",
  done: "Pronto",
  language: "Idioma",
  loadError: "Não foi possível carregar.",
  nights: (n: number) => `${n} noite${n !== 1 ? "s" : ""}`,
};

const catalog = { es, en, pt };
export default catalog;
