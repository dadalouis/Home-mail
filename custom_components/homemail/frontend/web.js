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
        denied: "Notifications not allowed in the system settings", refused: "Home Assistant refused the registration", retry: "Try again",
        login_sub: "Log in with your Home Assistant account", user: "Username", pass: "Password", keep: "Stay logged in", login: "Log in",
        mfa_sub: "Enter the code from your authenticator app", confirm: "Confirm", back: "Back", own_page: "Log in on the Home Assistant page",
        bad_login: "Wrong username or password", bad_code: "Wrong code, try again", login_err: "Logging in failed", private: "Your mail stays in your own Home Assistant",
        n_title: "Notifications for new mail", n_text: "This {d} will be linked to <b>{u}</b>. Afterwards you choose per account what you want to hear about.",
        n_on: "Turn on notifications", n_later: "Later", n_foot: "iOS asks for permission once after this", made: "Made by dadalouis",
        p_title: "How much mail?", p_text: "This app shows the mail of the last:", p_all: "All mail", p_next: "Continue", p_save: "Save",
        p_foot: "Nothing is deleted: older mail stays on the server and in your other apps. You can change this later in Settings.",
        u_d: ["day", "days"], u_w: ["week", "weeks"], u_m: ["month", "months"], u_y: ["year", "years"], last: "last {n}" },
  nl: { reconnect: "Opnieuw verbinden…", offline: "Geen verbinding, opnieuw proberen…", push: "Mailmeldingen via deze app", on: "Meldingen aan", busy: "Bezig…",
        denied: "Meldingen niet toegestaan in de systeeminstellingen", refused: "Home Assistant weigerde de aanmelding", retry: "Opnieuw proberen",
        login_sub: "Log in met je Home Assistant-account", user: "Gebruikersnaam", pass: "Wachtwoord", keep: "Ingelogd blijven", login: "Inloggen",
        mfa_sub: "Vul de code uit je authenticator-app in", confirm: "Bevestigen", back: "Terug", own_page: "Inloggen via de pagina van Home Assistant",
        bad_login: "Verkeerde gebruikersnaam of wachtwoord", bad_code: "Verkeerde code, probeer opnieuw", login_err: "Inloggen mislukt", private: "Je mail blijft in je eigen Home Assistant",
        n_title: "Meldingen bij nieuwe mail", n_text: "Deze {d} wordt gekoppeld aan <b>{u}</b>. Je kiest daarna per account wat je wilt horen.",
        n_on: "Meldingen aanzetten", n_later: "Later", n_foot: "iOS vraagt hierna één keer om toestemming", made: "Made by dadalouis",
        p_title: "Hoeveel mail?", p_text: "Deze app toont de mail van de laatste:", p_all: "Alle mail", p_next: "Verder", p_save: "Bewaar",
        p_foot: "Er wordt niets verwijderd: oudere mail blijft op de server en in je andere apps. Je kunt dit later aanpassen in Instellingen.",
        u_d: ["dag", "dagen"], u_w: ["week", "weken"], u_m: ["maand", "maanden"], u_y: ["jaar", "jaar"], last: "laatste {n}" },
};
const esc = (x) => String(x ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
// What kind of device this is, for the name of its notification registration ("Home-mail iPhone 4f2a")
const DEVICE = /iPad/.test(navigator.userAgent) || (/Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1) ? "iPad"
  : /iPhone/.test(navigator.userAgent) ? "iPhone" : /Android/.test(navigator.userAgent) ? "Android"
  : /Macintosh/.test(navigator.userAgent) ? "Mac" : /Windows/.test(navigator.userAgent) ? "Windows" : "Browser";
const REPO = "https://github.com/dadalouis/Home-mail" + (LANG === "nl" ? "/blob/main/README.nl.md" : "#readme");
const t = (k) => (TXT[LANG] || TXT.en)[k];

// "Stay logged in" off: the tokens live in sessionStorage only and are gone when the app is closed.
const store = () => { try { return sessionStorage.getItem(KEY) ? sessionStorage : localStorage; } catch (_) { return localStorage; } };
const read = () => { try { return JSON.parse(store().getItem(KEY) || "null"); } catch (_) { return null; } };
const keep = (x, where) => {
  try {
    const st = where || store();
    (st === localStorage ? sessionStorage : localStorage).removeItem(KEY);
    x ? st.setItem(KEY, JSON.stringify(x)) : st.removeItem(KEY);
  } catch (_) {}
};
const status = (x) => { const s = document.getElementById("status"); s.textContent = x; s.hidden = !x; };

// ---------- login: our own screen over the HA login flow (/auth/login_flow, the same API the HA frontend uses) ----------
const AUTH = { user: "", keep: true };
async function flow(path, body) {
  const r = await fetch(`${BASE}/auth/login_flow${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_id: CLIENT, ...body }) });
  if (!r.ok) throw Object.assign(new Error("flow " + r.status), { status: r.status });
  return r.json();
}
function screen(html) {
  let el = document.getElementById("hm-screen");
  if (!el) { el = document.createElement("div"); el.id = "hm-screen"; document.body.appendChild(el); }
  el.innerHTML = html;
  const c = getComputedStyle(el).backgroundColor; // the colour behind the status bar follows this screen too
  document.documentElement.style.background = document.body.style.background = c;
  return el;
}
const closeScreen = () => { document.getElementById("hm-screen")?.remove(); matchTop(); };
const logo = `<img class="hm-icon" src="icon-180.png" alt=""><div class="hm-word">Hom<b>E</b>-mail</div>`;
const made = `<a class="hm-made" href="${REPO}" target="_blank" rel="noopener"><svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>${t("made")}</a>`;

async function loginScreen() {
  let f;
  try { f = await flow("", { handler: ["homeassistant", null], redirect_uri: RETURN }); }
  catch (_) { return toLogin(); } // no local users (only another login method): the normal HA page
  const ask = (err) => {
    const mfa = f.step_id !== "init";
    const el = screen(`<form class="hm-c" autocomplete="on">${logo}
      <div class="hm-sub">${esc(mfa ? t("mfa_sub") : t("login_sub"))}</div>
      ${mfa ? `<input class="hm-code" name="code" inputmode="numeric" autocomplete="one-time-code" maxlength="8" required>`
        : `<div class="hm-card"><label>${t("user")}<input name="username" autocomplete="username" autocapitalize="none" required value="${esc(AUTH.user)}"></label>
           <label>${t("pass")}<input name="password" type="password" autocomplete="current-password" required></label></div>
           <label class="hm-row">${t("keep")}<input type="checkbox" name="keep"${AUTH.keep ? " checked" : ""}></label>`}
      <div class="hm-err">${esc(err || "")}</div>
      <button class="hm-btn">${mfa ? t("confirm") : t("login")}</button>
      ${mfa ? `<button type="button" class="hm-btn hm-link" data-back>${t("back")}</button>` : `<button type="button" class="hm-btn hm-link" data-page>${t("own_page")}</button>`}
      <div class="hm-foot">${t("private")}<br>${esc(location.host)}<br>${made}</div></form>`);
    el.querySelector("input:not([value]), input[name=password], input[name=code]")?.focus();
    el.querySelector("[data-page]")?.addEventListener("click", toLogin);
    el.querySelector("[data-back]")?.addEventListener("click", loginScreen);
    el.querySelector("form").onsubmit = async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target), btn = e.target.querySelector(".hm-btn");
      btn.disabled = true;
      let body;
      if (mfa) body = { code: String(fd.get("code") || "").trim() };
      else { AUTH.user = String(fd.get("username") || ""); AUTH.keep = !!fd.get("keep"); body = { username: AUTH.user, password: fd.get("password") }; }
      try {
        const r = await flow("/" + f.flow_id, body);
        if (r.type === "create_entry") {
          keep(await tokenRequest({ grant_type: "authorization_code", code: r.result }), AUTH.keep ? localStorage : sessionStorage);
          closeScreen(); connect(); afterLogin(); return;
        }
        if (r.type === "form") { const again = r.step_id === f.step_id; f = r; return ask(again ? t(mfa ? "bad_code" : "bad_login") : ""); }
        return ask(r.reason || t("login_err")); // abort (e.g. too many attempts)
      } catch (_) {
        if (mfa) return loginScreen(); // flow expired: start over
        ask(t("login_err"));
      }
    };
  };
  ask("");
}

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

// ---------- period: how much mail this web app shows (per device, kept on the phone; HA gets it for the red number) ----------
const WKEY = "homemail_window";
const getWindow = () => { try { return JSON.parse(localStorage.getItem(WKEY) || "null"); } catch (_) { return null; } }; // null = not chosen yet
function sinceDate(w, today = new Date()) { // same rules as notify.since_date in Home Assistant
  if (!w || w.all || !["d", "w", "m", "y"].includes(w.unit)) return "";
  const n = Math.max(0, Math.min(Number(w.n) || 0, 36500)), d = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  if (w.unit === "d" || w.unit === "w") d.setDate(d.getDate() - n * (w.unit === "w" ? 7 : 1));
  else {
    const day = d.getDate();
    d.setDate(1); d.setMonth(d.getMonth() - (w.unit === "y" ? 12 * n : n));
    d.setDate(Math.min(day, new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate()));
  }
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
const windowLabel = (w = getWindow()) => !w || w.all ? t("p_all") : t("last").replace("{n}", `${w.n} ${t("u_" + w.unit)[w.n === 1 ? 0 : 1]}`);
app.since = sinceDate(getWindow());
// The period and hidden folders of this web app are kept in Home Assistant (per registration), so they can be
// changed from any device; the phone keeps a copy to start fast. HA's copy wins once this phone is registered.
async function myEndpoint() {
  try { return (await (await navigator.serviceWorker?.getRegistration())?.pushManager.getSubscription())?.endpoint || ""; } catch (_) { return ""; }
}
function applyDevice(r) {
  if (!r?.name) return;
  app.mailWindow.name = r.name;
  if (r.window) { try { localStorage.setItem(WKEY, JSON.stringify(r.window)); } catch (_) {} }
  app._hidden = r.hidden || {};
  try { localStorage.setItem("homemail_hidden_folders", JSON.stringify(app._hidden)); } catch (_) {}
  const since = sinceDate(getWindow());
  if (since !== app.since) app.setSince(since); else if (app._mbOpen?.()) app._loadMb();
  else app._renderMb?.();
}
async function syncWindow() { // tell HA what was chosen on this phone (first login, or before it was registered)
  const endpoint = await myEndpoint();
  if (!endpoint || !getWindow()) return;
  try { applyDevice(await connection.sendMessagePromise({ type: "homemail/web_device", endpoint, window: getWindow(), hidden: app._hidden || {} })); } catch (_) {}
}
async function loadDevice() { // on opening: take over what was changed on another device
  const endpoint = await myEndpoint();
  if (!endpoint) return;
  try {
    const r = await connection.sendMessagePromise({ type: "homemail/web_device", endpoint });
    if (r?.name && !r.window && getWindow()) return syncWindow(); // registered before periods were kept in HA
    applyDevice(r);
  } catch (_) {}
}
// Choose the period: after the first login, and from Settings. Resolves when saved (true) or closed (false).
function windowScreen(first) {
  return new Promise((done) => {
    const w = getWindow() || { n: 2, unit: "w" };
    const el = screen(`<form class="hm-c">
      <div class="hm-bell hm-cal"><svg width="46" height="46" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"><rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/></svg></div>
      <div class="hm-word hm-title">${t("p_title")}</div>
      <div class="hm-sub">${t("p_text")}</div>
      <div class="hm-period"><input name="n" type="number" inputmode="numeric" min="1" max="999" value="${Number(w.n) || 2}">
        <div class="hm-seg">${["d", "w", "m", "y"].map((u) => `<label><input type="radio" name="unit" value="${u}"${(w.unit || "w") === u ? " checked" : ""}><span>${t("u_" + u)[1]}</span></label>`).join("")}</div></div>
      <label class="hm-row">${t("p_all")}<input type="checkbox" name="all"${w.all ? " checked" : ""}></label>
      <button class="hm-btn">${first ? t("p_next") : t("p_save")}</button>
      ${first ? "" : `<button type="button" class="hm-btn hm-link" data-back>${t("back")}</button>`}
      <div class="hm-foot">${t("p_foot")}</div></form>`);
    const form = el.querySelector("form"), all = form.elements.all;
    const sync = () => form.querySelector(".hm-period").classList.toggle("off", all.checked);
    all.onchange = sync; sync();
    el.querySelector("[data-back]")?.addEventListener("click", () => { closeScreen(); done(false); });
    form.onsubmit = (e) => {
      e.preventDefault();
      const nw = all.checked ? { all: true } : { n: Math.max(1, Math.min(999, parseInt(form.elements.n.value, 10) || 1)), unit: form.elements.unit.value };
      try { localStorage.setItem(WKEY, JSON.stringify(nw)); } catch (_) {}
      app.setSince(sinceDate(nw));
      syncWindow();
      closeScreen(); done(true);
    };
  });
}
app.mailWindow = { name: "", label: () => windowLabel(), edit: () => windowScreen(false), apply: applyDevice };

// iOS shows the page colour behind the status bar (and fades it over the top of the app): keep it the colour of
// the screen that is open, white for a list, grey for Mailboxes, so there is no grey-to-white band at the top.
const theme = document.querySelector('meta[name="theme-color"]');
function matchTop() {
  const r = app.shadowRoot, box = r?.getElementById("app");
  if (!box) return;
  const pane = r.querySelector(box.classList.contains("mb") ? "#mb" : "#lp");
  const c = pane && getComputedStyle(pane).backgroundColor;
  if (!c || c === "rgba(0, 0, 0, 0)") return;
  document.documentElement.style.background = document.body.style.background = c;
  theme?.setAttribute("content", c);
}
const watchTop = () => {
  const box = app.shadowRoot?.getElementById("app");
  if (!box) return setTimeout(watchTop, 200); // the app builds itself on the first connection
  new MutationObserver(matchTop).observe(box, { attributes: true, attributeFilter: ["class"] });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", matchTop);
  matchTop();
};
watchTop();
// back in the app: changes made on another device, and the period moves with the calendar (a new day, a new first day)
document.addEventListener("visibilitychange", () => {
  if (document.hidden) return;
  if (app.since && sinceDate(getWindow()) !== app.since) app.setSince(sinceDate(getWindow()));
  if (read()?.refresh_token) waitReady().then(loadDevice, () => {});
});

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
  if (!token) return loginScreen();
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
// Always a fresh subscription: an old one may be dead (iOS stops delivering to it) and html5 would file it
// under its old name. The old registration is removed from HA first.
async function register(key) {
  const reg = await navigator.serviceWorker.ready;
  const auth = { Authorization: `Bearer ${await validToken()}`, "Content-Type": "application/json" };
  const old = await reg.pushManager.getSubscription().catch(() => null);
  if (old) {
    await fetch(`${BASE}/api/notify.html5`, { method: "DELETE", headers: auth, body: JSON.stringify({ subscription: old.toJSON() }) }).catch(() => {});
    await old.unsubscribe().catch(() => {});
  }
  const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64(key) });
  const name = `Home-mail ${DEVICE} ${Math.random().toString(36).slice(2, 6)}`;
  const r = await fetch(`${BASE}/api/notify.html5`, { method: "POST", headers: auth, body: JSON.stringify({ subscription: sub.toJSON(), browser: "chrome", name }) });
  if (!r.ok) throw new Error(`${t("refused")} (${r.status})`);
  // Home-mail now knows whose device this is
  await connection.sendMessagePromise({ type: "homemail/push_register", name, endpoint: sub.endpoint });
  try { localStorage.setItem("homemail_push2", sub.endpoint); } catch (_) {}
  await syncWindow();
}

async function pushOn(btn, key) {
  btn.disabled = true; btn.textContent = t("busy");
  try {
    if ((await Notification.requestPermission()) !== "granted") throw new Error(t("denied"));
    await register(key);
    return true;
  } catch (e) {
    btn.disabled = false; btn.textContent = t("retry");
    status(e.message || String(e));
    return false;
  }
}

// Right after logging in (and whenever this device gets no notifications): a full screen asking to turn them on.
async function pushScreen(key) {
  let set = {};
  try { set = await connection.sendMessagePromise({ type: "homemail/settings" }); } catch (_) {}
  const accs = Object.values(set.accounts || {});
  const el = screen(`<div class="hm-c">
    <div class="hm-bell"><svg width="48" height="48" viewBox="0 0 24 24" fill="#fff"><path d="M12 22a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22Zm7-6V11a7 7 0 0 0-5.5-6.84V3.5a1.5 1.5 0 0 0-3 0v.66A7 7 0 0 0 5 11v5l-2 2v1h18v-1l-2-2Z"/></svg></div>
    <div class="hm-word hm-title">${t("n_title")}</div>
    <div class="hm-sub">${t("n_text").replace("{d}", esc(DEVICE)).replace("{u}", esc(set.user_name || ""))}</div>
    ${accs.length ? `<div class="hm-list">${accs.map((a) => `<div><span style="background:${esc(a.color)}">${esc((a.name || "?")[0].toUpperCase())}</span>${esc(a.name)}</div>`).join("")}</div>` : ""}
    <button class="hm-btn" data-on>${t("n_on")}</button>
    <button class="hm-btn hm-link" data-later>${t("n_later")}</button>
    <div class="hm-foot">${t("n_foot")}</div></div>`);
  el.querySelector("[data-on]").onclick = async (e) => { if (await pushOn(e.currentTarget, key)) closeScreen(); };
  el.querySelector("[data-later]").onclick = () => { try { localStorage.setItem("homemail_push_later", String(Date.now())); } catch (_) {} closeScreen(); };
}

function pushBarSmall(key) {
  const bar = document.createElement("div");
  bar.id = "push";
  bar.innerHTML = `<span>${t("push")}</span><button>${t("on")}</button><button class="x" aria-label="Close">✕</button>`;
  document.body.appendChild(bar);
  bar.querySelector("button").onclick = async (e) => { if (await pushOn(e.currentTarget, key)) bar.remove(); };
  bar.querySelector(".x").onclick = () => bar.remove();
}

async function afterLogin() {
  await waitReady().catch(() => {});
  await loadDevice(); // a period set for this phone from another device: no need to ask
  if (!getWindow()) await windowScreen(true);
  await pushSetup().catch(() => {});
  loadDevice();
}

let pushBusy = false;
async function pushSetup() {
  if (pushBusy || !read()?.refresh_token) return; // not logged in yet: runs again after logging in
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) return; // plain Safari: no push
  pushBusy = true;
  try { await pushCheck(); } finally { pushBusy = false; }
}
async function pushCheck() {
  const reg = await navigator.serviceWorker.register("sw.js", { scope: new URL(".", location.href).pathname });
  const sub = await reg.pushManager.getSubscription().catch(() => null);
  await waitReady().catch(() => {});
  // Only offer it when the html5 integration is set up in HA.
  let key;
  try { key = await connection.sendMessagePromise({ type: "notify/html5/appkey" }); } catch (_) { return; }
  if (!key) return;
  if (sub && Notification.permission === "granted") {
    // does Home Assistant still send to this subscription, for this user?
    try { if ((await connection.sendMessagePromise({ type: "homemail/push_check", endpoint: sub.endpoint })).ok) return; } catch (_) { return; }
  }
  // Permission given before, but no working registration: sign up again, no tap needed.
  if (Notification.permission === "granted") {
    try { await register(key); return; } catch (_) { /* fall back to asking */ }
  }
  if (Notification.permission === "denied") return;
  let later = 0; try { later = Number(localStorage.getItem("homemail_push_later")) || 0; } catch (_) {}
  if (later) pushBarSmall(key); else pushScreen(key);
}
if (read()?.refresh_token) afterLogin(); // logged in before: still choose the period once (older versions had none)

// Open a message from a notification: via #mail=<Message-ID> (new window) or a message from the service worker.
const openFromNotification = (id) => { if (id) app.openByMessageId(id); };
const h = new URLSearchParams(location.hash.slice(1)).get("mail");
if (h) { history.replaceState(null, "", location.pathname); openFromNotification(h); }
navigator.serviceWorker?.addEventListener("message", (e) => { if (e.data?.type === "open-mail") openFromNotification(e.data.message_id); });
