// Enlaces externos para gestionar las "Ofertas de Booking" (deals visibles), que NO se
// gestionan por la API del Channel Manager (ver specs/009-booking-offers). Configurables.

export const EXTERNAL_LINKS = {
  // Panel de control de Beds24 (Channel Manager → Booking.com → Promotions).
  beds24Dashboard: "https://beds24.com/control3.php",
  // Página exacta de Deals de Booking.com en Beds24 (crear/activar/desactivar deals con
  // badge). Sincroniza con Booking; no gestionable por API (solo dashboard).
  beds24BookingPromotions:
    "https://beds24.com/control3.php?pagetype=syncroniserbookingcomxmlpromotions",
  // Extranet de Booking.com para Partners (Promociones / Oportunidades).
  bookingExtranet: "https://admin.booking.com/",
  // Calendario/precios del anuncio en Airbnb (descuentos semanal/mensual y promos del
  // anuncio se gestionan ahí; con la conexión API los precios los manda Beds24).
  airbnbMulticalendar: "https://www.airbnb.com/multicalendar",
  // Página de Promotions de Airbnb en Beds24 (Channel Manager → Airbnb → Promotions).
  beds24AirbnbPromotions:
    "https://beds24.com/control3.php?pagetype=syncroniserairbnbpromotions",
} as const;
