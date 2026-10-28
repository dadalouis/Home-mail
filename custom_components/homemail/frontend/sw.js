// Home-mail service worker. Receives web push from the HA html5 integration
// (payload: title, body, tag, data{message_id, unread}; or {dismiss: true, tag} to remove a notification).
// Tapping a notification opens the web app with that message.
const SCOPE = new URL(".", self.location.href).pathname;
const APP = SCOPE + "app.html";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("push", (e) => {
  let p = {};
  try { p = e.data ? e.data.json() : {}; } catch (_) { p = { title: "Home-mail", body: e.data ? e.data.text() : "" }; }
  const n = Number(p.data?.unread);
  const badge = Number.isFinite(n) && "setAppBadge" in navigator
    ? (n > 0 ? navigator.setAppBadge(n) : navigator.clearAppBadge()).catch(() => {}) : Promise.resolve();
  if (p.dismiss) {
    e.waitUntil(Promise.all([badge, self.registration.getNotifications(p.tag ? { tag: p.tag } : {}).then((l) => l.forEach((x) => x.close()))]));
    return;
  }
  e.waitUntil(Promise.all([badge, self.registration.showNotification(p.title || "Home-mail", {
    body: p.body || "",
    tag: p.tag,
    data: p.data || {},
    icon: SCOPE + "icon-180.png",
    badge: SCOPE + "icon-180.png",
    timestamp: p.timestamp,
  })]));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const id = e.notification.data?.message_id || "";
  const target = APP + (id ? "#mail=" + encodeURIComponent(id) : "");
  e.waitUntil((async () => {
    const wins = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    const open = wins.find((w) => new URL(w.url).pathname.startsWith(SCOPE));
    if (open) {
      open.postMessage({ type: "open-mail", message_id: id });
      return open.focus();
    }
    return self.clients.openWindow(target);
  })());
});
