# Feature 046: registro de huéspedes — TRA (MinCIT) y archivo SIRE (Migración Colombia)

**Issue:** #167 · **Rama:** `046-guest-registration` · **Depende de:** 028 (privacidad), 045 (mensajes), 025 (avisos), 042 (valor de la reserva)

## Por qué
Todo prestador de alojamiento con RNT, incluidas las viviendas turísticas, debe:
- registrar a cada huésped en la **Tarjeta de Registro de Alojamiento (TRA)** del MinCIT el día del check-in (Ley 2068 de 2020, art. 22; Res. 700 de 2021 y Res. 409 de 2022);
- reportar a los **extranjeros** en **SIRE** de Migración Colombia (Decreto 1067 de 2015, art. 2.2.1.11.5.8; Res. 2357 de 2020).

Hoy el anfitrión lo hace a mano en dos portales. StayLever le pide los datos al huésped, envía la TRA cuando el anfitrión confirma y genera el archivo de SIRE.

## Lo que permiten los sistemas (revisado el 11-nov-2026)
### TRA
- **API para PMS:**
  - `POST https://pms.mincit.gov.co/one/` registra al huésped principal y responde `{"code": N}`;
  - `POST /two/` registra cada acompañante, con `padre = N`.
- **Autenticación:** `Authorization: token …`, con un token por RNT.
  - El anfitrión lo pide en `pms.mincit.gov.co/token/`. El formulario tiene captcha y el token llega al correo del RNT.
  - StayLever **no** puede pedirlo por él: el anfitrión lo pega en StayLever.
- **Limitaciones:**
  - No hay ambiente de pruebas.
  - No hay operación para corregir ni anular: las correcciones se hacen a mano en la web del MinCIT.
  - No se documentan códigos de error.
- **Campos del huésped principal:**
  - `tipo_identificacion` (C.C, C.E, T.I o Pasaporte), `numero_identificacion`, `nombres`, `apellidos`;
  - `cuidad_residencia` y `cuidad_procedencia`, escritos así, con la errata del MinCIT;
  - `numero_habitacion` (se usa "1" para la vivienda completa), `motivo` (catálogo del MinCIT), `numero_acompanantes`;
  - `check_in` y `check_out` (AAAA-MM-DD), `tipo_acomodacion` (Apartamento, Casa o Finca);
  - `costo` (total en COP, con IVA y comisión de la plataforma);
  - `nombre_establecimiento` y `rnt_establecimiento`.
- **Campos de cada acompañante:** documento (también R.C), nombres, apellidos, ciudades, habitación, fechas y `padre`.
- **No pide** nacionalidad, fecha de nacimiento ni sexo.

### SIRE
- **No tiene API.** Se carga un archivo plano `.txt` en el portal (Alojamiento y Hospedaje → Cargar archivo), con las entradas y las salidas por separado.
- **Datos que exige:**
  - código del establecimiento y código de la ciudad;
  - tipo y número de documento, nacionalidad, primer apellido, segundo apellido y nombres;
  - tipo de movimiento (E o S) y fecha;
  - procedencia, destino y fecha de nacimiento.
- **Pendiente de confirmar** con el «Manual Usuario Sire Externo» oficial, que solo se descarga desde la página de entrada de SIRE (ver FR-009):
  - el orden exacto de los campos, el separador, la codificación y el formato de fecha;
  - las tablas de códigos.
- **Plazo:** para viviendas turísticas la norma es ambigua (el mismo día, o 5 días hábiles después de la entrega). StayLever recomienda la entrada el día del check-in y la salida el día del check-out.

## Historias
1. **(P1) Configurar:** en Ajustes → «Registro de huéspedes» escribo:
   - mi RNT y el nombre del establecimiento;
   - el tipo de alojamiento por unidad;
   - el token del MinCIT;
   - mi código y ciudad de SIRE.

   También autorizo a StayLever a enviar la TRA en mi nombre.
2. **(P1) Enlace para el huésped:** cada reserva próxima tiene un enlace de registro. Lo envío desde Mensajes (045) con un texto prellenado en el idioma del huésped, o lo copio.
3. **(P1) El huésped se registra:**
   - abre el enlace en el celular, sin cuenta;
   - acepta el aviso de privacidad;
   - llena sus datos y los de sus acompañantes (es, en o pt).

   Si es extranjero, se le piden además nacionalidad, fecha de nacimiento y destino.
4. **(P1) Revisar y enviar la TRA:**
   - veo el estado de cada reserva (sin enlace, enlace enviado, datos recibidos, TRA enviada o error);
   - reviso y corrijo los datos, o los lleno yo si el huésped no lo hizo;
   - pulso «Enviar TRA».
5. **(P2) Archivo SIRE:** descargo el `.txt` con las entradas o salidas de extranjeros de un día y lo subo al portal de SIRE. Marco la reserva como reportada.
6. **(P2) Recordatorios:** el día del check-in, si la TRA no se ha enviado, me llega un aviso al celular. Lo mismo para SIRE con extranjeros. Los avisos no llevan nombres.

## Requisitos
- **FR-001 Datos de registro:**
  - **Por reserva:** un registro con un token público aleatorio (≥ 32 bytes), el estado y los huéspedes (principal y acompañantes).
  - **Cifrado:** los datos de los huéspedes (documento, nombres, ciudades, nacionalidad, nacimiento y destino) se guardan **cifrados** en la base, con Fernet y una clave derivada por cuenta.
  - **Fuera de la base cifrada:** solo los estados, las fechas de envío y el código de respuesta del MinCIT quedan sin cifrar.
- **FR-002 Configuración de la cuenta:**
  - se guardan el RNT, el nombre del establecimiento, el tipo de alojamiento por unidad, el código y la ciudad de SIRE y la autorización (fecha y usuario);
  - el **token del MinCIT** es un secreto de cuenta (017/026): solo se escribe y nunca se muestra.
- **FR-003 Enlace público** (`/checkin/{token}`):
  - **Contenido:** no muestra el nombre del huésped, solo el nombre del alojamiento y las fechas.
  - **Vigencia:** desde que se crea hasta el día del check-out.
  - **Idioma:** es, en y pt, según el navegador o la elección del huésped.
  - **Acompañantes:** pide tantos como diga el huésped, hasta el máximo de la unidad.
  - **Consentimiento:** exige aceptar el aviso de privacidad (Ley 1581): el anfitrión es el Responsable, StayLever el Encargado, y los datos se usan para la TRA y SIRE.
  - **Validación:**
    - los documentos y fechas se validan;
    - el número de pasaporte admite letras;
    - el registro civil solo se acepta para acompañantes.
  - **Correcciones:** el huésped puede corregir sus datos mientras la TRA no se haya enviado.
  - **Abuso:** hay límite de envíos por IP y por token. Un token inválido responde lo mismo que uno vencido.
- **FR-004 Mensaje con el enlace:**
  - en el hilo de Mensajes (045), «Insertar enlace de registro» llena el borrador con un texto en es, en o pt;
  - el anfitrión lo edita y lo envía: no hay envío automático.
- **FR-005 Panel del anfitrión:** una página «Registro de huéspedes» con las reservas de los próximos 30 días y los últimos 7.
  - Por reserva muestra el estado de la TRA y de SIRE.
  - Permite copiar el enlace, editar los datos y enviar la TRA.
  - El costo se propone a partir del valor de la reserva (042) convertido a COP, y el anfitrión lo puede editar.
- **FR-006 Enviar TRA** (`POST /registration/{booking}/tra`):
  - **Requisitos previos:** configuración completa, autorización dada y datos completos.
  - **Orden:** primero el huésped principal y luego cada acompañante con `padre`.
  - **Resultado:** se guarda el código o el error, por persona.
  - **Reintento:** si fallan acompañantes, se reintentan solo los pendientes, sin duplicar al principal.
  - **Después de enviar:** los datos quedan bloqueados para el huésped, y se avisa que las correcciones van en la web del MinCIT.
  - **Auditoría:** queda quién envió, sin datos personales.
- **FR-007 Archivo SIRE** (`GET /registration/sire?date=…&movement=E|S`):
  - se genera un `.txt` con los extranjeros que entran o salen ese día, con el formato oficial (FR-009);
  - el anfitrión marca la reserva como «reportada en SIRE».
- **FR-008 Avisos:**
  - **Cuándo:** a las 8:00 del día del check-in, si falta la TRA o, con extranjeros, el reporte de entrada a SIRE; y el día del check-out para la salida de SIRE.
  - **Contenido:** el canal y las fechas, sin nombres.
  - Se usa la preferencia de avisos de reservas (025).
- **FR-009 Formato SIRE:** el formato del archivo sale del manual oficial que descarga el anfitrión desde el portal de SIRE.
  - Mientras tanto, se implementa con el formato conocido como hipótesis: tabulado, una línea por persona, 13 campos y fechas dd/mm/aaaa.
  - Se ajusta antes de producción.
- **FR-010 Privacidad y retención:**
  - **Acceso:**
    - solo la cuenta dueña ve los datos, nunca el administrador de plataforma;
    - nunca van a logs, a la IA ni a los avisos.
  - **Retención:** los datos de los huéspedes se borran **1 año después del check-out**, en la misma tarea diaria que borra el nombre (028). Solo quedan los estados.
  - **Exportación y borrado de cuenta:** la exportación de datos de la cuenta (028) incluye los registros, y el borrado de cuenta los elimina.
  - **Documentos legales:**
    - se actualizan la Política de privacidad y los Términos (es, en y pt): StayLever, como Encargado, recoge documentos de huéspedes para la TRA y SIRE;
    - **sube la versión legal**;
    - se actualiza `docs/data-inventory.md`.
- **FR-011 Ambiente de pruebas:**
  - en staging, el envío de la TRA usa un cliente simulado que devuelve códigos falsos;
  - en producción, la primera prueba es una reserva real del anfitrión.
- **FR-012 Modo sin conexión (029):** funciona igual con las reservas manuales o de iCal; el anfitrión copia el enlace en vez de enviarlo por Mensajes.

## Criterios de éxito
- **SC-001:** un huésped completa el registro desde el celular en menos de 3 minutos, con un acompañante.
- **SC-002:** el anfitrión envía la TRA de una reserva real con un clic, y la ve en la consulta de huéspedes del MinCIT.
- **SC-003:** ningún dato de documento aparece sin cifrar en la base, en los logs ni en las respuestas del panel de administración (prueba automática).
- **SC-004:** el archivo SIRE generado se carga sin errores en el portal (verificación manual del anfitrión).

## Fuera de alcance
- Cargar el archivo a SIRE automáticamente: no hay API, y usar las credenciales del anfitrión en el portal no es aceptable.
- Foto o escaneo del documento.
- Firma del contrato de hospedaje.
- Check-in con llaves o cerraduras.
- Corregir o anular TRA ya enviadas: no hay API para eso.
- Reportes al Viceministerio de Turismo distintos de la TRA.
