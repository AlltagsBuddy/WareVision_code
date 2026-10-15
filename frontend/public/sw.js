/*
 * WareVision Service Worker – macht die App am Handy installierbar („Zum Startbildschirm“).
 * Bewusst KEIN Zwischenspeichern von Daten: Kunden- und Auftragsdaten werden nie auf dem
 * Gerät abgelegt, alles kommt immer frisch vom Server.
 */
self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()))
self.addEventListener('fetch', () => {
  // Netzwerk wie gewohnt – nichts abfangen
})
