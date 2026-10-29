// Home-mail stand-alone web app (app.html): its own Home Assistant login without external libraries.
// Login uses the normal HA login page (password + 2FA); afterwards only the refresh token is kept in
// localStorage (like the HA frontend itself). The page contains no data; everything comes over the websocket.
const V = new URL(import.meta.url).searchParams.get("v") || "0";
await import(`./homemail-app.js?v=${V}`);

const BASE = location.origin;
const CLIENT = BASE + "/";
const RETURN = BASE + location.pathname;
const KEY = "homemail_tokens";
const LANG = (navigator.language || "en").slice(0, 2).toLowerCase();
const TXT = {
  en: { reconnect: "Reconnecting…", offline: "No connection, retrying…", push: "Get mail notifications from this app", on: "Turn on", busy: "Busy…",
        denied: "Notifications not allowed in the system settings", refused: "Home Assistant refused the registration", retry: "Try again" },
  nl: { reconnect: "Opnieuw verbinden…", offline: "Geen verbinding, opnieuw proberen…", push: "Mailmeldingen via deze app", on: "Meldingen aan", busy: "Bezig…",
        denied: "Meldingen niet toegestaan in de systeeminstellingen", refused: "Home Assistant weigerde de aanmelding", retry: "Opnieuw proberen" },
};
const t = (k) => (TXT[LANG] || TXT.en)[k];

const read = () => { try { return JSON.parse(localStorage.getItem(KEY) || "null"); } catch (_) { return null; } };
const keep = (x) => { try { x ? localStorage.setItem(KEY, JSON.stringify(x)) : localStorage.removeItem(KEY); } catch (_) {} };
const status = (x) => { const s = document.getElementById("status"); s.textContent = x; s.hidden = !x; };

function toLogin() {
  const state = crypto.getRandomValues(new Uint32Array(2)).join("-");
  sessionStorage.setItem("homemail_state", state);
  location.href = `${BASE}/auth/authorize?response_type=code&client_id=${encodeURIComponent(CLIENT)}&redirect_uri=${encodeURIComponent(RETURN)}&state=${encodeURIComponent(state)}`;
}

async function tokenRequest(fields) {
  const r = await fetch(`${BASE}/auth/token`, { method: "POST", body: new URLSearchParams({ client_id: CLIENT, ...fields }) });
  if (!r.ok) throw Object.assign(new Error("token " + r.status), { status: r.status });
  const d = await r.json();
  return { ...read(), ...d, expires: Date.now() + (d.expires_in || 1800) * 1000 };
}

async function validToken() {
  let x = read();
  if (!x?.refresh_token) return null;
  if (x.access_token && x.expires > Date.now() + 60000) return x.access_token;
  try {
    x = await tokenRequest({ grant_type: "refresh_token", refresh_token: x.refresh_token });
    keep(x);
    return x.access_token;
  } catch (e) {
    if (e.status === 400 || e.status === 403) { keep(null); return null; } // revoked or expired
    throw e; // network error: try again later
  }
}

// Back from the login page with ?code=
const p = new URLSearchParams(location.search);
if (p.get("code")) {
  const ok = p.get("state") && p.get("state") === sessionStorage.getItem("homemail_state");
  sessionStorage.removeItem("homemail_state");
  history.replaceState(null, "", location.pathname);
  if (ok) {
    try { keep(await tokenRequest({ grant_type: "authorization_code", code: p.get("code") })); }
    catch (_) { keep(null); }
  }
}

const app = document.querySelector("homemail-app");
let ws = null, seq = 0, pending = new Map(), delay = 1000;
const subs = new Set(); // {msg, cb, id}: re-sent after every reconnect

// iOS closes the websocket while the app is in the background. A request made right after coming back
// waits (max 15 s) for the new connection instead of failing at once.
let ready = null, readyOk = null;
const waitReady = () => {
  if (ws?.readyState === 1 && authed) return Promise.resolve();
  if (!ws || ws.readyState > 1) { delay = 1000; connect(); }
  ready ??= new Promise((ok) => (readyOk = ok));
  return Promise.race([ready, new Promise((_, no) => setTimeout(() => no(new Error("disconnected")), 15000))]);
};
let authed = false;

const connection = {
  async sendMessagePromise(message) {
    await waitReady();
    return new Promise((ok, fail) => {
      const id = ++seq, sock = ws;
      // a socket iOS silently killed still says "open": no answer in 30 s = reconnect
      const timer = setTimeout(() => { if (pending.delete(id)) { fail(new Error("disconnected")); if (ws === sock) sock.close(); } }, 30000);
      pending.set(id, { ok: (r) => { clearTimeout(timer); ok(r); }, fail: (e) => { clearTimeout(timer); fail(e); } });
      sock.send(JSON.stringify({ ...message, id }));
    });
  },
  subscribeMessage(cb, msg) {
    const sub = { msg, cb, id: null };
    subs.add(sub);
    if (ws?.readyState === 1) sendSub(sub);
    return Promise.resolve(() => {
      subs.delete(sub);
      if (sub.id && ws?.readyState === 1) ws.send(JSON.stringify({ id: ++seq, type: "unsubscribe_events", subscription: sub.id }));
    });
  },
};
function sendSub(sub) {
  sub.id = ++seq;
  pending.set(sub.id, { ok() {}, fail() {}, sub });
  ws.send(JSON.stringify({ ...sub.msg, id: sub.id }));
}

// Red badge on the home-screen icon (iOS 16.4+, only with notifications on): total unread of all accounts.
app.addEventListener("homemail-unread", (e) => {
  const n = Number(e.detail?.total) || 0;
  try { if ("setAppBadge" in navigator) (n > 0 ? navigator.setAppBadge(n) : navigator.clearAppBadge()).catch(() => {}); } catch (_) {}
});

async function connect() {
  let token;
  try { token = await validToken(); } catch (_) { return retry(); }
  if (!token) return toLogin();
  if (ws && ws.readyState <= 1) return; // already (re)connecting
  status(ws ? t("reconnect") : "");
  const s = new WebSocket(BASE.replace(/^http/, "ws") + "/api/websocket");
  ws = s;
  s.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.type === "auth_required") s.send(JSON.stringify({ type: "auth", access_token: token }));
    else if (m.type === "auth_invalid") { const x = read(); if (x) { x.expires = 0; keep(x); } s.close(); }
    else if (m.type === "auth_ok") {
      delay = 1000; status("");
      authed = true; readyOk?.(); ready = null; readyOk = null;
      app.hass = { connection, language: LANG, locale: { language: navigator.language || LANG } };
      for (const sub of subs) sendSub(sub);
    } else if (m.type === "event") {
      pending.get(m.id)?.sub?.cb(m.event);
    } else if (m.type === "result") {
      const w = pending.get(m.id); if (!w) return;
      if (!w.sub) pending.delete(m.id);
      m.success ? w.ok(m.result) : w.fail(Object.assign(new Error(m.error?.message || "error"), { code: m.error?.code }));
    }
  };
  s.onclose = () => {
    if (ws !== s) return;
    authed = false;
    for (const w of pending.values()) if (!w.sub) w.fail(new Error("disconnected"));
    pending.clear();
    retry();
  };
}
function retry() {
  status(t("offline"));
  setTimeout(connect, delay);
  delay = Math.min(delay * 2, 30000);
}
document.addEventListener("visibilitychange", () => { if (!document.hidden && (!ws || ws.readyState > 1)) { delay = 1000; connect(); } });
connect();

// ---------- notifications (web push via the HA html5 integration, optional) ----------
// iOS: only in the app on the home screen, and asking for permission is only allowed after a tap.
// After registering, HA gets a notify entity for this device; Home-mail remembers whose device it is.
const b64 = (s) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(s.length / 4) * 4, "=")), (c) => c.charCodeAt(0));

// Subscribe this device and tell HA (html5) and Home-mail about it. Needs notification permission already.
async function register(key) {
  const reg = await navigator.serviceWorker.ready;
  let sub = await reg.pushManager.getSubscription();
  if (!sub) sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64(key) });
  const name = "Home-mail " + Math.random().toString(36).slice(2, 8);
  const r = await fetch(`${BASE}/api/notify.html5`, {
    method: "POST",
    headers: { Authorization: `Bearer ${await validToken()}`, "Content-Type": "application/json" },
    body: JSON.stringify({ subscription: sub.toJSON(), browser: "chrome", name }),
  });
  if (!r.ok) throw new Error(`${t("refused")} (${r.status})`);
  await connection.sendMessagePromise({ type: "homemail/push_register", name }); // Home-mail now knows whose device this is
  try { localStorage.setItem("homemail_push2", sub.endpoint); } catch (_) {}
}

async function pushOn(btn, key) {
  btn.disabled = true; btn.textContent = t("busy");
  try {
    if ((await Notification.requestPermission()) !== "granted") throw new Error(t("denied"));
    await register(key);
    btn.closest("#push").remove();
  } catch (e) {
    btn.disabled = false; btn.textContent = t("retry");
    status(e.message || String(e));
  }
}

async function pushBar() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) return; // plain Safari: no push
  const reg = await navigator.serviceWorker.register("sw.js", { scope: new URL(".", location.href).pathname });
  const sub = await reg.pushManager.getSubscription().catch(() => null);
  let known = null; try { known = localStorage.getItem("homemail_push2"); } catch (_) {}
  if (sub && Notification.permission === "granted" && known === sub.endpoint) return;
  // Only offer it when the html5 integration is set up in HA.
  for (let i = 0; i < 20 && ws?.readyState !== 1; i++) await new Promise((r) => setTimeout(r, 500));
  let key;
  try { key = await connection.sendMessagePromise({ type: "notify/html5/appkey" }); } catch (_) { return; }
  if (!key) return;
  // Permission given before, but the subscription is gone (iOS drops it after a while): sign up again, no tap needed.
  if (Notification.permission === "granted" && known) {
    try { await register(key); return; } catch (_) { /* fall back to the button */ }
  }
  const bar = document.createElement("div");
  bar.id = "push";
  bar.innerHTML = `<span>${t("push")}</span><button>${t("on")}</button><button class="x" aria-label="Close">✕</button>`;
  document.body.appendChild(bar);
  bar.querySelector("button").onclick = (e) => pushOn(e.currentTarget, key);
  bar.querySelector(".x").onclick = () => bar.remove();
}
pushBar().catch(() => {});

// Open a message from a notification: via #mail=<Message-ID> (new window) or a message from the service worker.
const openFromNotification = (id) => { if (id) app.openByMessageId(id); };
const h = new URLSearchParams(location.hash.slice(1)).get("mail");
if (h) { history.replaceState(null, "", location.pathname); openFromNotification(h); }
navigator.serviceWorker?.addEventListener("message", (e) => { if (e.data?.type === "open-mail") openFromNotification(e.data.message_id); });
