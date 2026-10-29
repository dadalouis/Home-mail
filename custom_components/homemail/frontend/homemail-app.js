// Home-mail app (iOS Mail style). Used by the sidebar panel, the Lovelace card and the stand-alone web app
// (app.html, attribute "standalone"). Talks to Home Assistant over the websocket (homemail/* commands);
// messages come straight from the IMAP server, nothing is stored in HA states.
// Screens: Mailboxes (all folders with counters) -> message list of a folder -> message (iframe without scripts).
const CSP_ON = "default-src 'none'; img-src https: data:; style-src 'unsafe-inline' https:; font-src https: data:";
const CSP_OFF = "default-src 'none'; img-src data:; style-src 'unsafe-inline'; font-src data:"; // remote images off
const IC = {
  back: "M15 6l-6 6 6 6", copy: "M9 9h11v11H9zM5 15H4V4h11v1", refresh: "M20 12a8 8 0 1 1-2.3-5.7M20 4v5h-5", search: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM21 21l-5-5",
  flag: "M5 21V4h12l-2 4 2 4H5", archive: "M3 4h18v4H3zM5 8v12h14V8M10 12h4", trashcan: "M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13",
  seen: "M3 8l9 6 9-6M3 8v10h18V8M3 8l9-5 9 5", clip: "M20 11l-8 8a5 5 0 0 1-7-7l9-9a3 3 0 0 1 4 4l-9 9a1 1 0 0 1-2-2l8-8",
  reply: "M10 9V5l-7 7 7 7v-4.1c5 0 8.5 1.6 11 5.1-1-5-4-10-11-11z", compose: "M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z",
  send: "M12 19V5M5 12l7-7 7 7", filter: "M4 6h16M7 12h10M10 18h4", next: "M9 6l6 6-6 6",
  inbox: "M3 13h5l1.5 3h5L16 13h5M5 5h14l2 8v6H3v-6z", drafts: "M7 3h7l5 5v13H7zM14 3v5h5",
  sent: "M21 3L10 14M21 3l-7 18-4-7-7-4z", junk: "M4 7h16l-2 13H6zM9 11l6 6M15 11l-6 6M3 4h18v3H3z",
  trash: "M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6", all: "M3 4h18v4H3zM5 8v12h14V8M10 12h4",
  archivefolder: "M3 4h18v4H3zM5 8v12h14V8M10 12h4", custom: "M3 6h6l2 2h10v11H3z", allinbox: "M3 13h5l1.5 3h5L16 13h5M5 5h14l2 8v6H3v-6zM8 9h8",
  open: "M6 9l6 6 6-6", menu: "M4 6h16M4 12h16M4 18h16",
};
IC.archive_folder = IC.archivefolder;

// ---------- translations ----------
const T = {
  en: {
    mailboxes: "Mailboxes", settings: "Settings", all_inboxes: "All Inboxes", loading: "Loading…", load_failed: "Loading failed",
    updated: "Updated just now", new_message: "New message", refresh: "Refresh", search: "Search", unread_only: "Unread only",
    inbox: "Inbox", drafts: "Drafts", sent: "Sent", junk: "Junk", trash: "Trash", archive: "Archive", all: "All Mail",
    nothing_found: "Nothing found", no_unread: "No unread messages", no_messages: "No messages", no_selection: "No message selected",
    delete: "Delete", erase: "Erase", unread: "Unread", read: "Read", no_subject: "(no subject)", yesterday: "Yesterday",
    delete_permanently: "Delete permanently?", back: "Back", flag: "Flag", mark_unread: "Mark as unread", mark_read: "Mark as read",
    move_inbox: "Move to Inbox", archive_it: "Archive", delete_it: "Delete", delete_perm: "Delete permanently", reply: "Reply",
    reply_all: "Reply All", forward: "Forward", to: "To", cc: "Cc", from: "From", subject: "Subject", cancel: "Cancel",
    send: "Send", attachment: "attachment", quote_forward: "The original message (with attachments) is included below.",
    quote_reply: "The original message is quoted below.", bcc_on: "Blind copy to yourself is on.", discard: "Discard draft?",
    need_recipient: "Enter at least one recipient.", no_subject_ok: "Send without a subject?", sending: "Sending…",
    not_sent: "Not sent: {e}", sent_ok: "Sent", deleted_perm: "Deleted permanently", to_trash: "Moved to Trash",
    to_inbox: "Moved to Inbox", archived: "Archived", action_failed: "Action failed: {e}", done: "Done", accounts: "Accounts",
    add_account: "Add Account", composing: "Composing", bcc_me: "Always Bcc Myself", load_images: "Load Remote Images",
    default_account: "Default Account", sender_name: "Sender Name",
    settings_note: "New messages without a chosen account are sent from the default account. With remote images off only embedded images are shown (no tracking pixels, nothing loaded from outside).",
    saved: "Saved", save_failed: "Saving failed", save: "Save", account: "Account", name: "Name", email: "Email", color: "Colour",
    app_title: "Mail app on your phone", app_note: "Open this link in Safari, tap Share, then Add to Home Screen.", app_note_http: "This address is not https: notifications and the red badge need https (Home Assistant Cloud, your own domain or a VPN).", copied: "Copied", copy: "Copy", older: "Load older mail", period: "Mail in this app", folders_app: "Folders in this app", folders_all: "All folders", folders_hidden: "{n} hidden", folders_note: "Hidden folders are not shown or counted in this app. They stay on the server and in your other apps.",
    notifications: "Notifications", notif_on: "Notifications", notif_note: "Home-mail notifies you about new mail on your Companion app and on the web app on your home screen. These settings are yours alone.",
    notif_accounts: "Accounts", notif_which: "Which mail", notif_all: "All mail", notif_vip: "Only from my VIP list", notif_vip_list: "VIP senders", notif_mute: "Never notify for",
    notif_list_note: "One email address or domain per line, for example anna@example.com or example.com.",
    notif_when: "When", notif_days: "Days", notif_quiet: "Quiet hours", notif_from: "From", notif_to: "Until", notif_quiet_note: "No notifications during quiet hours. The mail itself still arrives.",
    notif_show: "What you see", notif_preview: "Show message text", notif_sound: "Sound", notif_where: "Where", notif_app: "Companion app", notif_web: "Web app on home screen",
    notif_no_devices: "No Companion app is linked to your user.", notif_web_none: "Not turned on yet: open the web app on your phone and tap the notifications button.", notif_web_n: "device(s) registered",
    notif_test: "Send test notification", notif_test_sent: "Test notification sent", notif_test_none: "No device to send to", days: "Mon,Tue,Wed,Thu,Fri,Sat,Sun",
    attach_add: "Add attachment", tap_open: "tap to open", attach_failed: "Attachment failed: {e}", attach_big: "{n} is too big (max 20 MB)", attach_busy: "Wait until the attachments are uploaded.",
    notif_buttons: "Buttons in the notification", notif_buttons_note: "Mark as read, Archive, Delete and Reply right from the notification in the Companion app (on Android: Read, Archive and Reply).",
    discard_changes: "Discard your changes?", all_admins: "all administrators", new_mail: "New mail", push_on: "Instant (IMAP IDLE)", push_every: "Checked every {n} min",
    push_on_note: "The mail server tells Home-mail at once about new mail, and about mail read or deleted in another app. A regular check every 15 minutes is the safety net.",
    push_off_note: "Instant new mail (IMAP IDLE) is off for this account. Turn it on in the account options in Home Assistant.",
    push_unsupported: "This mail server or this Home Assistant (Python 3.14 needed) does not support instant new mail, so Home-mail checks regularly.",
    push_error: "Instant new mail lost its connection; Home-mail retries by itself and checks regularly meanwhile.",
    access: "Who may use this account", you: "you", access_note: "Only these users see this account and get notifications for it.",
    access_all_admins: "Nobody chosen: every administrator can read this account and gets its notifications. Choose who may use it.",
    access_lose: "You are not in the list, so you will no longer see this account. Continue?",
    notif_devices_note: "The devices logged in with your Home Assistant user. Below each one: when Home Assistant last handed a notification to Apple or Google (whether it is shown, the device decides). Tap an account to stop its notifications on that device only.", web_app: "web app",
    forget: "Forget", forget_confirm: "Stop sending notifications to this web app?", last_ok: "sent {t}", last_fail: "failed {t}: {e}", closing: "Kind regards,", signature: "Signature", signature_note: "The closing (for example 'Kind regards, Alex') added below new messages and replies from this account.",
    description: "Description", description_ph: "e.g. Work", your_name: "Your name",
    account_note: "Name: your name as recipients see it. Description: how this account is called in the app.",
    next: "Next", checking: "Checking…", password: "Password", required: "required", servers: "Servers",
    imap_server: "IMAP server", imap_port: "IMAP port", smtp_server: "SMTP server", smtp_port: "SMTP port",
    password_note: "The password is stored only in your Home Assistant, like your other integrations.",
    account_added: "Account added", admin_only: "Only administrators can add accounts (Settings > Devices & services > Home-mail).",
    no_access: "No mail accounts available for this user. An administrator can add one, or allow you in the account options.",
    hint_gmail: "Google no longer accepts your normal password in other mail apps, so an app password is needed (once).",
    hint_icloud: "Apple no longer accepts your normal password in other mail apps: account.apple.com → Sign-In and Security → App-Specific Passwords.",
    app_pw_title: "App password in 3 steps", app_pw_why: "Takes about a minute. A confirmation on your phone is enough for step 1.",
    app_pw_step1: "Turn on 2-Step Verification", app_pw_step2: "Create an app password ('Home Assistant')", app_pw_step3: "Paste it below (spaces are fine)",
    app_password: "App password",
    e_app_password_required: "The provider refused your normal password: an app password is required. Follow steps 1 and 2 above, then paste it.",
    hint_outlook: "Note: Microsoft often no longer allows signing in with only a password; adding may fail.",
    hint_other: "Enter your provider's servers (for example imap.example.com / smtp.example.com).",
    p_gmail: "Gmail", p_icloud: "iCloud", p_outlook: "Outlook, Hotmail and Live", p_other: "Other (own domain)",
    e_unauthorized: "No access", e_not_found: "Message not found", e_no_trash: "No Trash folder found",
    e_too_big: "Attachments are too big (max 25 MB in total)", e_attachment_missing: "An attachment is missing, add it again", e_rate_limit: "Limit of 20 messages per hour reached", e_invalid_address: "Invalid email address", e_no_recipient: "No recipient",
    e_original_not_found: "Original message not found", e_folder_not_found: "Folder not found",
    e_invalid_auth_imap: "Login failed (IMAP): check address and password.",
    e_invalid_auth_smtp: "Login failed for sending (SMTP): check the password.",
    e_cannot_connect_imap: "Cannot reach the IMAP server.", e_cannot_connect_smtp: "Cannot reach the SMTP server.",
    e_already_configured: "This account is already added.", e_disconnected: "Connection lost",
  },
  nl: {
    mailboxes: "Postbussen", settings: "Instellingen", all_inboxes: "Alle inkomende", loading: "Laden…", load_failed: "Laden mislukt",
    updated: "Zojuist bijgewerkt", new_message: "Nieuw bericht", refresh: "Verversen", search: "Zoek", unread_only: "Alleen ongelezen",
    inbox: "Inkomend", drafts: "Concepten", sent: "Verstuurd", junk: "Spam", trash: "Prullenmand", archive: "Archief", all: "Alle berichten",
    nothing_found: "Niets gevonden", no_unread: "Geen ongelezen berichten", no_messages: "Geen berichten", no_selection: "Geen bericht geselecteerd",
    delete: "Verwijder", erase: "Wis", unread: "Ongelezen", read: "Gelezen", no_subject: "(geen onderwerp)", yesterday: "Gisteren",
    delete_permanently: "Definitief verwijderen?", back: "Terug", flag: "Vlag", mark_unread: "Markeer als ongelezen", mark_read: "Markeer als gelezen",
    move_inbox: "Naar Inkomend", archive_it: "Archiveer", delete_it: "Verwijder", delete_perm: "Definitief verwijderen", reply: "Beantwoord",
    reply_all: "Allen beantwoorden", forward: "Stuur door", to: "Aan", cc: "Cc", from: "Van", subject: "Onderwerp", cancel: "Annuleer",
    send: "Verstuur", attachment: "bijlage", quote_forward: "Het originele bericht (met bijlagen) wordt eronder meegestuurd.",
    quote_reply: "Het originele bericht wordt eronder geciteerd.", bcc_on: "Blinde kopie naar jezelf staat aan.", discard: "Concept weggooien?",
    need_recipient: "Vul minstens één ontvanger in.", no_subject_ok: "Versturen zonder onderwerp?", sending: "Versturen…",
    not_sent: "Niet verzonden: {e}", sent_ok: "Verzonden", deleted_perm: "Definitief verwijderd", to_trash: "Naar prullenmand",
    to_inbox: "Naar Inkomend", archived: "Gearchiveerd", action_failed: "Actie mislukt: {e}", done: "Gereed", accounts: "Accounts",
    add_account: "Nieuwe account", composing: "E-mail schrijven", bcc_me: "Blinde kopie naar mij", load_images: "Laad afbeeldingen",
    default_account: "Standaardaccount", sender_name: "Naam afzender",
    settings_note: "Nieuwe berichten zonder gekozen account gaan via het standaardaccount. Met afbeeldingen uit worden alleen ingesloten plaatjes getoond (geen volgpixels, niets van buiten).",
    saved: "Bewaard", save_failed: "Bewaren mislukt", save: "Bewaar", account: "Account", name: "Naam", email: "E-mail", color: "Kleur",
    app_title: "Mail-app op je telefoon", app_note: "Open deze link in Safari, tik op Deel en kies Zet op beginscherm.", app_note_http: "Dit adres is geen https: meldingen en het rode getal werken alleen met https (Home Assistant Cloud, eigen domein of VPN).", copied: "Gekopieerd", copy: "Kopieer", older: "Oudere mail laden", period: "Mail in deze app", folders_app: "Mappen in deze app", folders_all: "Alle mappen", folders_hidden: "{n} verborgen", folders_note: "Verborgen mappen worden in deze app niet getoond of geteld. Ze blijven op de server en in je andere apps.",
    notifications: "Meldingen", notif_on: "Meldingen", notif_note: "Home-mail meldt nieuwe mail op je Companion-app en op de web-app op je beginscherm. Deze instellingen zijn alleen van jou.",
    notif_accounts: "Accounts", notif_which: "Welke mail", notif_all: "Alle mail", notif_vip: "Alleen van mijn VIP-lijst", notif_vip_list: "VIP-afzenders", notif_mute: "Nooit melden voor",
    notif_list_note: "Eén e-mailadres of domein per regel, bijvoorbeeld anna@voorbeeld.nl of voorbeeld.nl.",
    notif_when: "Wanneer", notif_days: "Dagen", notif_quiet: "Stille uren", notif_from: "Van", notif_to: "Tot", notif_quiet_note: "Geen meldingen tijdens de stille uren. De mail zelf komt gewoon binnen.",
    notif_show: "Wat je ziet", notif_preview: "Tekst van het bericht tonen", notif_sound: "Geluid", notif_where: "Waar", notif_app: "Companion-app", notif_web: "Web-app op beginscherm",
    notif_no_devices: "Er is geen Companion-app aan jouw gebruiker gekoppeld.", notif_web_none: "Nog niet aangezet: open de web-app op je telefoon en tik op de meldingenknop.", notif_web_n: "apparaat/apparaten aangemeld",
    notif_test: "Stuur testmelding", notif_test_sent: "Testmelding verstuurd", notif_test_none: "Geen apparaat om naar te sturen", days: "Ma,Di,Wo,Do,Vr,Za,Zo",
    attach_add: "Bijlage toevoegen", tap_open: "tik om te openen", attach_failed: "Bijlage mislukt: {e}", attach_big: "{n} is te groot (max 20 MB)", attach_busy: "Wacht tot de bijlagen zijn geüpload.",
    notif_buttons: "Knoppen in de melding", notif_buttons_note: "Gelezen, Archiveer, Verwijder en Beantwoord direct vanuit de melding in de Companion-app (op Android: Gelezen, Archiveer en Beantwoord).",
    discard_changes: "Wijzigingen weggooien?", all_admins: "alle beheerders", new_mail: "Nieuwe mail", push_on: "Direct (IMAP IDLE)", push_every: "Elke {n} min gecontroleerd",
    push_on_note: "De mailserver meldt nieuwe mail meteen aan Home-mail, net als mail die in een andere app gelezen of verwijderd is. Een gewone controle elke 15 minuten is het vangnet.",
    push_off_note: "Nieuwe mail direct (IMAP IDLE) staat uit voor dit account. Zet het aan in de accountopties in Home Assistant.",
    push_unsupported: "Deze mailserver of deze Home Assistant (Python 3.14 nodig) ondersteunt geen directe nieuwe mail, dus Home-mail controleert regelmatig.",
    push_error: "Directe nieuwe mail is de verbinding kwijt; Home-mail probeert het zelf opnieuw en controleert intussen regelmatig.",
    access: "Wie mag dit account gebruiken", you: "jij", access_note: "Alleen deze gebruikers zien dit account en krijgen er meldingen van.",
    access_all_admins: "Niemand gekozen: alle beheerders kunnen dit account lezen en krijgen de meldingen. Kies wie het mag gebruiken.",
    access_lose: "Je staat zelf niet in de lijst, dus je ziet dit account dan niet meer. Doorgaan?",
    notif_devices_note: "De apparaten die met jouw Home Assistant-gebruiker zijn ingelogd. Onder elk apparaat: wanneer Home Assistant de laatste melding aan Apple of Google gaf (of hij verschijnt, bepaalt het apparaat). Tik op een account om zijn meldingen alleen op dat apparaat uit te zetten.", web_app: "web-app",
    forget: "Vergeet", forget_confirm: "Geen meldingen meer naar deze web-app sturen?", last_ok: "verstuurd {t}", last_fail: "mislukt {t}: {e}", closing: "Vriendelijke groeten,", signature: "Handtekening", signature_note: "De afsluiting (bijv. 'Vriendelijke groet, Sanne') die automatisch onder nieuwe berichten en antwoorden vanaf dit account komt.",
    description: "Beschrijving", description_ph: "bijv. Werk", your_name: "Je naam",
    account_note: "Naam: je naam zoals ontvangers die zien. Beschrijving: hoe dit account in de app heet.",
    next: "Volgende", checking: "Controleren…", password: "Wachtwoord", required: "vereist", servers: "Servers",
    imap_server: "IMAP-server", imap_port: "IMAP-poort", smtp_server: "SMTP-server", smtp_port: "SMTP-poort",
    password_note: "Het wachtwoord wordt alleen in je eigen Home Assistant bewaard, net als bij je andere integraties.",
    account_added: "Account toegevoegd", admin_only: "Alleen beheerders kunnen accounts toevoegen (Instellingen > Apparaten en diensten > Home-mail).",
    no_access: "Geen mailaccounts voor deze gebruiker. Een beheerder kan er een toevoegen of je toestaan in de accountopties.",
    hint_gmail: "Google accepteert je gewone wachtwoord niet meer in andere mail-apps, daarom is er (eenmalig) een app-wachtwoord nodig.",
    hint_icloud: "Apple accepteert je gewone wachtwoord niet meer in andere mail-apps: account.apple.com → Inloggen en beveiliging → App-specifieke wachtwoorden.",
    app_pw_title: "App-wachtwoord in 3 stappen", app_pw_why: "Kost ongeveer een minuut. Voor stap 1 is een bevestiging op je telefoon genoeg.",
    app_pw_step1: "Zet verificatie in 2 stappen aan", app_pw_step2: "Maak een app-wachtwoord ('Home Assistant')", app_pw_step3: "Plak het hieronder (spaties mogen)",
    app_password: "App-wachtwoord",
    e_app_password_required: "De provider weigerde je gewone wachtwoord: er is een app-wachtwoord nodig. Volg stap 1 en 2 hierboven en plak het dan.",
    hint_outlook: "Let op: Microsoft staat inloggen met alleen een wachtwoord vaak niet meer toe; dan lukt toevoegen niet.",
    hint_other: "Vul de servers van je provider in (bijv. imap.provider.nl / smtp.provider.nl).",
    p_gmail: "Gmail", p_icloud: "iCloud", p_outlook: "Outlook, Hotmail en Live", p_other: "Andere (eigen domein)",
    e_unauthorized: "Geen toegang", e_not_found: "Mail niet (meer) gevonden", e_no_trash: "Geen prullenbak-map gevonden",
    e_too_big: "Bijlagen zijn te groot (max 25 MB samen)", e_attachment_missing: "Een bijlage ontbreekt, voeg hem opnieuw toe", e_rate_limit: "Limiet van 20 mails per uur bereikt", e_invalid_address: "Ongeldig e-mailadres", e_no_recipient: "Geen ontvanger",
    e_original_not_found: "Originele mail niet gevonden", e_folder_not_found: "Map niet gevonden",
    e_invalid_auth_imap: "Inloggen mislukt (IMAP): controleer adres en wachtwoord.",
    e_invalid_auth_smtp: "Inloggen voor verzenden mislukt (SMTP): controleer het wachtwoord.",
    e_cannot_connect_imap: "IMAP-server niet bereikbaar.", e_cannot_connect_smtp: "SMTP-server niet bereikbaar.",
    e_already_configured: "Dit account is al toegevoegd.", e_disconnected: "Verbinding verbroken",
  },
};

const svg = (d, cl = "") => `<svg class="ic ${cl}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="${d}"/></svg>`;
const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
const load = (k, std) => { try { const v = localStorage.getItem(k); return v === null ? std : JSON.parse(v); } catch (_) { return std; } };
const store = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) {} };
const clean = (t) => String(t || "").replace(/\(?https?:\/\/\S+/g, "").replace(/[*\-_=]{3,}/g, " ").replace(/\s+/g, " ").trim();
const addressList = (t) => String(t || "").split(/[,;]/).map((a) => a.trim()).filter(Boolean);
const FOLDER_ICON = { inbox: IC.inbox, drafts: IC.drafts, sent: IC.sent, junk: IC.junk, trash: IC.trash, archive: IC.archivefolder, all: IC.all, custom: IC.custom };

const CSS = `
:host { display:block; height:calc(100vh - var(--header-height, 56px)); color:var(--primary-text-color, #000); font-family:-apple-system,"SF Pro Text",system-ui,Roboto,sans-serif;
  --blue:#0a84ff; --card:var(--card-background-color, #fff); --bg:var(--primary-background-color, #f2f2f7); --grey:var(--secondary-text-color, #8e8e93);
  --line:var(--divider-color, #d1d1d6); --fill:var(--secondary-background-color, #e5e5ea); }
:host([standalone]), :host([panel]) { height:100dvh; }
* { box-sizing:border-box; }
.app { position:relative; display:flex; height:100%; background:var(--bg); overflow:hidden; }
.left { position:relative; width:390px; flex:none; border-right:1px solid var(--line); min-height:0; overflow:hidden; }
.pane { position:absolute; inset:0; display:flex; flex-direction:column; background:var(--card); min-height:0; }
.app:not(.mb) #mb { display:none; } .app.mb #lp { display:none; }
#mb { background:var(--bg); }
.reader { position:relative; flex:1; display:flex; flex-direction:column; min-width:0; background:var(--card); min-height:0; }
.reader.drag, .pane.drag { transition:none; } .reader.spring, .pane.spring { transition:transform .22s ease; }
.head { padding:6px 12px 8px; padding-top:max(6px, env(safe-area-inset-top)); }
.head .row1 { display:flex; align-items:center; min-height:44px; }
.head .row1 .fill { flex:1; }
.head h1 { margin:2px 4px 8px; font-size:32px; font-weight:700; letter-spacing:-.5px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.head .sub { margin:-6px 4px 8px; font-size:13px; color:var(--grey); }
.search { display:flex; align-items:center; gap:8px; background:var(--fill); border-radius:10px; padding:7px 10px; color:var(--grey); margin:0 4px; }
.search input { flex:1; border:0; outline:0; background:transparent; color:var(--primary-text-color, #000); font-size:16px; min-width:0; }
.tabs { display:flex; gap:6px; padding:8px 16px 10px; overflow-x:auto; }
.tab { border:0; border-radius:16px; padding:6px 13px; font-size:14px; background:var(--fill); color:var(--primary-text-color, #000); cursor:pointer; white-space:nowrap; display:inline-flex; align-items:center; gap:4px; }
.tab.on { background:var(--blue); color:#fff; }
.tab .ic { width:16px; height:16px; }
.rows, .scroll { flex:1; overflow-y:auto; overflow-x:hidden; -webkit-overflow-scrolling:touch; }
.swipe { position:relative; overflow:hidden; border-bottom:1px solid var(--line); }
.under { position:absolute; inset:0 0 0 auto; display:flex; }
.under button { border:0; color:#fff; font:600 14px/1 inherit; width:80px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:4px; cursor:pointer; }
.under .arch { background:#8e8e93; } .under .del { background:#ff3b30; } .under .inb { background:var(--blue); }
.under .ic, .over .ic { width:22px; height:22px; }
.over { position:absolute; inset:0; display:none; align-items:center; gap:6px; padding-left:18px; background:var(--blue); color:#fff; font:600 14px/1 inherit; }
.swipe.right .over { display:flex; } .swipe.right .under { display:none; }
.edge { display:none; position:absolute; left:0; top:0; bottom:0; width:24px; z-index:3; touch-action:none; }
.row { position:relative; display:block; width:100%; text-align:left; border:0; background:var(--card); color:inherit; font:inherit; padding:10px 16px 10px 30px; cursor:pointer; touch-action:pan-y; transition:transform .2s ease; user-select:none; -webkit-user-select:none; }
.row.drag { transition:none; }
.row.sel { background:var(--blue); color:#fff; }
.row.sel .from, .row.sel .t, .row.sel .subj, .row.sel .pv { color:#fff; }
.dot { position:absolute; left:11px; top:19px; width:10px; height:10px; border-radius:50%; background:var(--blue); }
.row.sel .dot { background:#fff; }
.arrow { position:absolute; left:9px; top:16px; color:var(--grey); } .arrow .ic { width:14px; height:14px; }
.r1 { display:flex; align-items:baseline; gap:8px; }
.from { flex:1; font-size:16px; font-weight:700; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.row.read .from { font-weight:600; }
.t { font-size:14px; color:var(--grey); flex:none; }
.subj { font-size:15px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; margin-top:1px; }
.row:not(.read) .subj { font-weight:600; }
.pv { font-size:14px; line-height:1.3; color:var(--grey); margin-top:2px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.mark { display:inline-flex; gap:5px; margin-left:6px; vertical-align:middle; } .mark .ic { width:14px; height:14px; color:#ff9f0a; }
.acc { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; }
.ic { width:20px; height:20px; flex:none; }
.bar { position:relative; display:flex; align-items:center; gap:4px; padding:8px 12px; padding-top:max(8px, env(safe-area-inset-top)); border-bottom:1px solid var(--line); color:var(--blue); }
.bar .fill { flex:1; }
.btn { border:0; background:transparent; color:var(--blue); border-radius:8px; padding:8px; cursor:pointer; display:inline-flex; align-items:center; gap:2px; font:inherit; font-size:17px; }
.btn:hover { background:var(--fill); } .btn.on { color:#ff9f0a; } .btn[disabled] { opacity:.4; }
.btn.pill { border-radius:20px; padding:8px 14px; background:var(--fill); color:var(--primary-text-color, #000); }
.back { display:none; }
/* sidebar panel: HA-style top bar (menu button with notification dot + title), like other HA screens */
:host([panel]) { display:flex; flex-direction:column; }
.toolbar { display:flex; align-items:center; gap:4px; flex:none; height:var(--header-height, 56px); box-sizing:content-box; padding:0 12px 0 4px;
  background:var(--app-header-background-color, var(--primary-background-color)); color:var(--app-header-text-color, var(--primary-text-color));
  border-bottom:var(--app-header-border-bottom, 1px solid var(--divider-color, #e0e0e0)); }
.toolbar .ttl { margin-left:20px; font-size:20px; font-weight:400; }
.toolbar .btn.pill { padding:6px 14px; font-size:16px; }
:host([panel]) #mb .head h1 { margin-top:8px; }
:host([panel]) .app { flex:1; height:auto; min-height:0; }
:host([panel]) .head, :host([panel]) .bar { padding-top:6px; } :host([panel]) .sbar { padding-top:10px; }
:host([panel]) .fab, :host([panel]) .toast { bottom:22px; }
/* stand-alone web app: no settings (they live in Home Assistant itself) */
:host([standalone]) #mb .row1 { display:none; } :host([standalone]) #mb .head h1 { margin-top:8px; }
.menu { position:absolute; right:12px; top:100%; z-index:5; background:var(--card); border-radius:12px; box-shadow:0 8px 30px rgba(0,0,0,.25); overflow:hidden; min-width:220px; }
.menu button { display:flex; width:100%; align-items:center; gap:10px; border:0; background:transparent; color:var(--primary-text-color, #000); font:inherit; font-size:16px; padding:13px 16px; cursor:pointer; text-align:left; border-bottom:1px solid var(--line); }
.menu button:last-child { border-bottom:0; }
.mhead { padding:14px 18px 10px; border-bottom:1px solid var(--line); }
.mhead .name { font-size:17px; font-weight:700; }
.mhead .adr, .mhead .to, .mhead .dat { font-size:13px; color:var(--grey); margin-top:2px; overflow-wrap:anywhere; }
.mhead .subject { font-size:19px; font-weight:700; margin-top:8px; }
.att { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }
.att span, .att button { display:inline-flex; align-items:center; gap:5px; font-size:13px; background:var(--fill); border:0; color:inherit; font-family:inherit; border-radius:8px; padding:5px 9px; } .att .ic { width:14px; height:14px; }
.att button { cursor:pointer; } .att button:disabled { opacity:.6; }
.attrow { flex-wrap:wrap; } .attrow .chip { display:inline-flex; align-items:center; gap:6px; font-size:13px; background:var(--fill); border-radius:8px; padding:5px 9px; }
.attrow .chip b { font-weight:400; color:var(--grey); } .attrow .chip .x { border:0; background:transparent; color:var(--grey); font-size:15px; padding:0 0 0 2px; cursor:pointer; }
.attrow .add { border:0; background:transparent; color:var(--blue); font:inherit; font-size:16px; cursor:pointer; padding:0; }
iframe { flex:1; width:100%; border:0; background:#fff; min-height:0; }
.older { display:block; margin:14px auto 24px; } .empty { flex:1; display:flex; align-items:center; justify-content:center; color:var(--grey); padding:24px; text-align:center; }
.note { padding:10px 16px; font-size:13px; color:var(--grey); }
.spin .ic { animation:sp 1s linear infinite; } @keyframes sp { to { transform:rotate(360deg); } }
.group { margin:0 16px 22px; background:var(--card); border-radius:14px; overflow:hidden; }
.ghead { display:flex; align-items:center; justify-content:space-between; margin:8px 20px 8px; font-size:21px; font-weight:700; cursor:pointer; }
.ghead .ic { color:var(--grey); transition:transform .2s; } .ghead.closed .ic { transform:rotate(-90deg); }
.gtitle { margin:8px 20px 6px; font-size:13px; text-transform:uppercase; color:var(--grey); }
.item { display:flex; align-items:center; gap:14px; width:100%; border:0; background:transparent; color:inherit; font:inherit; font-size:17px; text-align:left; padding:0 0 0 16px; cursor:pointer; }
.item > .ic { color:var(--blue); width:24px; height:24px; }
.item .text { flex:1; display:flex; align-items:center; gap:8px; min-height:48px; padding-right:14px; border-bottom:1px solid var(--line); overflow:hidden; }
.item:last-child .text { border-bottom:0; }
.item .name { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.item .sub2 { display:block; font-size:13px; color:var(--grey); }
.item .cnt { color:var(--grey); font-size:17px; } .item .chev { color:#c7c7cc; width:16px; height:16px; }
.item input[type=checkbox] { appearance:none; width:51px; height:31px; border-radius:16px; background:#e9e9eb; position:relative; cursor:pointer; flex:none; transition:background .2s; }
.item input[type=checkbox]::after { content:""; position:absolute; top:2px; left:2px; width:27px; height:27px; border-radius:50%; background:#fff; box-shadow:0 2px 4px rgba(0,0,0,.2); transition:left .2s; }
.item input[type=checkbox]:checked { background:#34c759; } .item input[type=checkbox]:checked::after { left:22px; }
.item select, .item input[type=text], .item input[type=email], .item input[type=password], .item input[type=number] { border:0; outline:0; background:transparent; color:var(--grey); font:inherit; font-size:17px; text-align:right; min-width:0; flex:1; }
.item textarea { flex:1; border:0; outline:0; resize:vertical; min-height:110px; padding:12px 0; font:16px/1.4 inherit; background:transparent; color:inherit; }
.item textarea#a-sig { min-height:240px; }
.item textarea.nl { min-height:70px; padding:10px 0; }
.item input[type=time] { border:0; outline:0; background:transparent; color:var(--grey); font:inherit; font-size:17px; }
.dayb { border:0; border-radius:16px; padding:6px 11px; background:#e9e9eb; color:inherit; font:inherit; font-size:15px; cursor:pointer; }
.dayb.on { background:var(--blue); color:#fff; }
.warn { color:#ff9500; }
.fab { position:absolute; right:18px; bottom:max(22px, env(safe-area-inset-bottom)); width:56px; height:56px; border-radius:50%; border:0; background:var(--card); color:var(--primary-text-color, #000); box-shadow:0 4px 18px rgba(0,0,0,.18); display:flex; align-items:center; justify-content:center; cursor:pointer; z-index:4; }
.fab .ic { width:26px; height:26px; }
.swatches { display:flex; gap:10px; flex-wrap:wrap; justify-content:flex-end; padding:8px 0; }
.sw { width:28px; height:28px; border-radius:50%; border:0; padding:0; cursor:pointer; box-shadow:0 0 0 2px var(--card); }
.sw.on { box-shadow:0 0 0 2px var(--card), 0 0 0 4px currentColor; color:var(--primary-text-color, #000); }
.explain { margin:-14px 22px 22px; font-size:13px; color:var(--grey); line-height:1.35; }
.error { color:#ff3b30; }
.veil { position:absolute; inset:0; z-index:10; background:rgba(0,0,0,.35); display:flex; align-items:center; justify-content:center; }
.sheet { width:min(680px, 94%); height:min(760px, 92%); background:var(--card); border-radius:14px; display:flex; flex-direction:column; overflow:hidden; box-shadow:0 10px 40px rgba(0,0,0,.3); }
.sheet.grey { background:var(--bg); }
.sbar { display:flex; align-items:center; padding:10px 12px; padding-top:max(10px, env(safe-area-inset-top)); border-bottom:1px solid var(--line); background:var(--card); }
.sbar b { flex:1; text-align:center; font-size:17px; }
.sendbtn { width:34px; height:34px; border-radius:50%; background:var(--blue); color:#fff; justify-content:center; padding:0; }
.sendbtn[disabled] { background:#8e8e93; }
.field { display:flex; align-items:center; gap:8px; padding:9px 16px; border-bottom:1px solid var(--line); font-size:16px; }
.field label { color:var(--grey); flex:none; min-width:74px; }
.field input, .field select { flex:1; border:0; outline:0; background:transparent; color:var(--primary-text-color, #000); font:inherit; font-size:16px; min-width:0; }
.sheet textarea.body { flex:1; border:0; outline:0; resize:none; padding:12px 16px; font:16px/1.45 -apple-system,system-ui,sans-serif; background:transparent; color:var(--primary-text-color, #000); }
.foot { padding:8px 16px; font-size:13px; color:var(--grey); border-top:1px solid var(--line); }
.toast { position:absolute; left:50%; bottom:max(24px, env(safe-area-inset-bottom)); transform:translateX(-50%); z-index:20; background:rgba(30,30,30,.9); color:#fff; border-radius:20px; padding:9px 18px; font-size:15px; pointer-events:none; }
@media (max-width:760px) {
  .left { width:100%; border-right:0; }
  .reader { display:none; }
  .app.open .left { display:none; }
  .app.open .reader { display:flex; }
  .back, .edge { display:inline-flex; } .edge { display:block; }
  .veil { background:transparent; }
  .sheet { width:100%; height:100%; border-radius:0; box-shadow:none; }
}
`;

class HomemailApp extends HTMLElement {
  constructor() {
    super();
    this._view = { account: "all", folder: "INBOX", kind: "inbox", name: null }; // current folder; name null = "All Inboxes"
    this._search = ""; this._msgs = []; this._sel = null; this._open = null; this._busy = false; this._errors = [];
    this._set = { accounts: {}, default: "", images: true }; this._mb = null; this._contacts = [];
    this._unreadOnly = load("homemail_unread_only", false);
    this._closed = load("homemail_closed", {}); // collapsed accounts on the Mailboxes screen
    this._hidden = load("homemail_hidden_folders", {}); // web app: folders not shown, per account
    // a property set before the upgrade would hide the setter
    for (const p of ["hass"]) if (Object.prototype.hasOwnProperty.call(this, p)) { const v = this[p]; delete this[p]; this[p] = v; }
  }
  set hass(h) {
    const first = !this._hass;
    this._hass = h;
    if (first || !this._lang) this._lang = String(h.locale?.language || h.language || navigator.language || "en").slice(0, 2).toLowerCase();
    if (!this._built) this._build();
    if (first || h.connection !== this._conn) this._subscribe();
    this._syncMenu();
    this._deepLink();
  }
  // The web app changed its period: counters and lists again
  setSince(since) {
    this.since = since || "";
    this._older = false; this._lists?.clear(); this._msgs = [];
    if (this._conn) this._subscribe();
    if (this._root) { this._load(); if (this._mbOpen()) this._loadMb(); }
  }
  // A tapped Companion app notification opens /homemail?mail=<Message-ID>: open that message.
  _deepLink() {
    if (!this.hasAttribute("panel")) return;
    const id = new URLSearchParams(location.search).get("mail");
    if (!id || id === this._linked) return;
    this._linked = id;
    history.replaceState(history.state, "", location.pathname);
    this.openByMessageId(id);
  }
  static get observedAttributes() { return ["narrow"]; }
  attributeChangedCallback() { this._syncMenu(); }
  _syncMenu() {
    if (!this._menuBtn) return;
    this._menuBtn.hass = this._hass;
    this._menuBtn.narrow = this.hasAttribute("narrow");
  }
  connectedCallback() { this._timer = setInterval(() => !document.hidden && this._load(true), 120000); }
  disconnectedCallback() { clearInterval(this._timer); this._unsub?.then((u) => u && u()).catch(() => {}); this._unsub = null; this._conn = null; }

  t(k, vars = {}) {
    let s = (T[this._lang] || T.en)[k] ?? T.en[k] ?? k;
    for (const [n, v] of Object.entries(vars)) s = s.replace(`{${n}}`, v);
    return s;
  }
  _locale() { return this._hass?.locale?.language || this._lang; }
  _time(iso) {
    if (!iso) return "";
    const d = new Date(iso), now = new Date(), L = this._locale();
    const day = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
    const diff = Math.round((day(now) - day(d)) / 864e5);
    if (diff <= 0) return d.toLocaleTimeString(L, { hour: "2-digit", minute: "2-digit" });
    if (diff === 1) return this.t("yesterday");
    if (diff < 7) return d.toLocaleDateString(L, { weekday: "long" });
    return d.toLocaleDateString(L, { day: "2-digit", month: "2-digit", year: "2-digit" });
  }
  _fullDate(iso) { return iso ? new Date(iso).toLocaleString(this._locale(), { weekday: "short", day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" }) : ""; }
  _errText(e) { const m = String(e?.message || e || ""); return (T[this._lang] || T.en)["e_" + m] || T.en["e_" + m] || m; }
  _color(acc) { return this._set.accounts[acc]?.color || "#8e8e93"; }
  _viewName() { return this._view.name || this.t("all_inboxes"); }
  _mbOpen() { return this._root?.getElementById("app").classList.contains("mb"); }

  // Live counters: homemail/subscribe pushes whenever an inbox changes; refresh the list then.
  _subscribe() {
    const c = this._hass?.connection; if (!c?.subscribeMessage) return;
    this._unsub?.then((u) => u && u()).catch(() => {});
    this._conn = c;
    let first = true;
    this._unsub = c.subscribeMessage((ev) => {
      this.dispatchEvent(new CustomEvent("homemail-unread", { detail: ev, bubbles: true, composed: true }));
      if (first) { first = false; return; }
      this._load(true); if (this._mbOpen()) this._loadMb();
    }, { type: "homemail/subscribe", ...(this.since ? { since: this.since } : {}) }).catch(() => null);
  }

  _build() {
    this._built = true;
    this._root = this.attachShadow({ mode: "open" });
    this._root.innerHTML = `<style>${CSS}</style>
      <div class="app" id="app">
        <section class="left">
          <div class="pane" id="mb">
            <div class="head"><div class="row1"><span class="fill"></span><button class="btn pill" id="settings">${this.t("settings")}</button></div><h1>${this.t("mailboxes")}</h1>
              <div class="sub" id="mbsub"></div></div>
            <div class="scroll" id="mbbody"><div class="empty">${this.t("loading")}</div></div>
            <button class="fab" id="new2" title="${this.t("new_message")}">${svg(IC.compose)}</button>
          </div>
          <div class="pane" id="lp">
            <div class="edge" id="lpedge"></div>
            <div class="head"><div class="row1"><button class="btn" id="tomb">${svg(IC.back)}${this.t("mailboxes")}</button><span class="fill"></span>
                <button class="btn" id="refresh" title="${this.t("refresh")}">${svg(IC.refresh)}</button>
                <button class="btn" id="new" title="${this.t("new_message")}">${svg(IC.compose)}</button></div>
              <h1 id="title">${esc(this._viewName())}</h1>
              <label class="search">${svg(IC.search)}<input id="search" type="search" placeholder="${this.t("search")}" enterkeyhint="search"></label></div>
            <div class="tabs"><button class="tab${this._unreadOnly ? " on" : ""}" id="filter">${svg(IC.filter)}${this.t("unread_only")}</button></div>
            <div class="rows" id="rows"></div>
          </div>
        </section>
        <section class="reader" id="reader"></section>
      </div>`;
    const $ = (i) => this._root.getElementById(i);
    $("filter").onclick = () => { this._unreadOnly = !this._unreadOnly; store("homemail_unread_only", this._unreadOnly); $("filter").classList.toggle("on", this._unreadOnly); this._renderList(); };
    $("search").onkeydown = (e) => { if (e.key === "Enter") { this._search = e.target.value.trim(); this._load(); } };
    $("search").oninput = (e) => { if (!e.target.value && this._search) { this._search = ""; this._load(); } };
    $("refresh").onclick = () => this._load();
    $("new").onclick = $("new2").onclick = () => this._compose("new");
    $("tomb").onclick = () => this._toMailboxes();
    $("settings").onclick = () => this._settings();
    if (this.hasAttribute("panel")) {
      // HA's own menu button (opens the sidebar, shows the notification dot) + title
      const bar = document.createElement("div");
      bar.className = "toolbar";
      this._menuBtn = document.createElement("ha-menu-button");
      const ttl = document.createElement("span");
      ttl.className = "ttl"; ttl.textContent = "Home-mail";
      const fill = document.createElement("span");
      fill.style.flex = "1";
      const row = $("settings").closest(".row1");
      bar.append(this._menuBtn, ttl, fill, $("settings")); // Settings moves into the top bar
      row.remove();
      this._root.insertBefore(bar, $("app"));
      this._syncMenu();
    }
    $("mbbody").onclick = (e) => this._mbClick(e);
    $("rows").onclick = (e) => {
      if (this._swipeClick) { this._swipeClick = false; return; }
      if (e.target.closest("[data-older]")) { this._older = true; this._msgs = []; this._load(); return; }
      const b = e.target.closest("[data-swipe]");
      if (b) { const m = this._msgs[+b.closest(".swipe").dataset.i]; this._swipeAction(m, b.dataset.swipe); return; }
      if (this._swipeOpen) { this._closeSwipe(); return; }
      const r = e.target.closest(".row"); if (r) this._openMsg(this._msgs[+r.closest(".swipe").dataset.i]);
    };
    this._swipes($("rows"));
    this._edgeSwipe($("lp"), $("lpedge"), () => this._toMailboxes());
    this._renderReader();
    this._load();
    this._loadSettings();
  }

  async _call(type, data = {}, retry = true) {
    try { return await this._hass.connection.sendMessagePromise({ type: "homemail/" + type, ...data }); }
    catch (e) {
      const msg = e?.message || e?.code || String(e);
      // connection hiccup (e.g. phone back from the background): try once more; real errors come straight through
      const hiccup = !e?.code || e.code === 3 /* HA frontend: ERR_CONNECTION_LOST */ || /disconnect|connection|lost|closed|timeout/i.test(msg);
      if (retry && hiccup && type !== "send" && type !== "add_account") {
        await new Promise((r) => setTimeout(r, 800));
        return this._call(type, data, false);
      }
      throw new Error(msg);
    }
  }
  async _loadSettings() {
    try { this._set = await this._call("settings"); } catch (_) {}
    if (!Object.keys(this._set.accounts || {}).length && this._msgs.length === 0) this._renderList();
  }

  // ---------- Mailboxes ----------
  _toMailboxes() {
    this._sel = null; this._closeReader();
    this._root.getElementById("app").classList.add("mb");
    if (!this._mb) this._root.getElementById("mbbody").innerHTML = `<div class="empty">${this.t("loading")}</div>`;
    else this._renderMb();
    this._loadMb();
  }
  async _loadMb() {
    if (!this._mb) { // last known state from Home Assistant first: instant
      try { const c = await this._call("mailboxes", { cached: true }); if (c.accounts && !this._mb) { this._mb = c; this._renderMb(); } } catch (_) {}
    }
    try { this._mb = await this._call("mailboxes", this._mbArgs()); this._renderMb(); }
    catch (e) { this._root.getElementById("mbbody").innerHTML = `<div class="empty">${this.t("load_failed")}</div>`; }
  }
  _hiddenOn() { return this.mailWindow ? this._hidden : {}; } // only the web app hides folders
  _mbArgs() {
    const skip = Object.fromEntries(Object.entries(this._hiddenOn()).filter(([, v]) => v.length));
    return { ...(this.since ? { since: this.since } : {}), ...(Object.keys(skip).length ? { skip } : {}) };
  }
  _renderMb() {
    const mb = this._mb; if (!mb) return;
    const hid = this._hiddenOn();
    const cnt = (n) => (n ? `<span class="cnt">${n}</span>` : "");
    const item = (data, icon, name, n) => `<button class="item" ${data}>${svg(icon)}<span class="text"><span class="name">${esc(name)}</span>${cnt(n)}${svg(IC.next, "chev")}</span></button>`;
    const inbox = (a) => a.folders.find((f) => f.kind === "inbox");
    const total = mb.accounts.reduce((s, a) => s + (inbox(a)?.unread || 0), 0);
    let h = `<div class="group">${item('data-acc="all" data-folder="INBOX" data-kind="inbox" data-name=""', IC.allinbox, this.t("all_inboxes"), total)}`;
    for (const a of mb.accounts) {
      const i = inbox(a); if (!i) continue;
      h += item(`data-acc="${esc(a.account)}" data-folder="${esc(i.folder)}" data-kind="inbox" data-name="${esc(a.name)}"`, IC.inbox, a.name, i.unread);
    }
    h += "</div>";
    for (const a of mb.accounts) {
      const closed = !!this._closed[a.account];
      h += `<div class="ghead${closed ? " closed" : ""}" data-fold="${esc(a.account)}"><span><span class="acc" style="background:${esc(this._color(a.account))}"></span>${esc(a.name)}</span>${svg(IC.open)}</div>`;
      if (closed) continue;
      h += '<div class="group">' + a.folders.filter((f) => f.kind === "inbox" || !(hid[a.account] || []).includes(f.folder)).map((f) => {
        const name = f.kind === "custom" ? f.name : this.t(f.kind);
        const n = f.kind === "drafts" || f.kind === "sent" ? f.total : f.unread; // like iOS: drafts count everything
        return item(`data-acc="${esc(a.account)}" data-folder="${esc(f.folder)}" data-kind="${f.kind}" data-name="${esc(f.kind === "inbox" ? a.name : name)}"`,
          FOLDER_ICON[f.kind] || IC.custom, name, n);
      }).join("") + "</div>";
    }
    if (!mb.accounts.length) h += `<div class="explain" style="margin-top:0">${this.t("no_access")}</div>`;
    if (mb.errors?.length) h += `<div class="note">⚠ ${esc(mb.errors.join(", "))}</div>`;
    this._root.getElementById("mbbody").innerHTML = h + '<div style="height:90px"></div>';
    this._root.getElementById("mbsub").textContent = this.t("updated");
  }
  _mbClick(e) {
    const k = e.target.closest("[data-fold]");
    if (k) { this._closed[k.dataset.fold] = !this._closed[k.dataset.fold]; store("homemail_closed", this._closed); this._renderMb(); return; }
    const b = e.target.closest("[data-folder]"); if (!b) return;
    this._view = { account: b.dataset.acc, folder: b.dataset.folder, kind: b.dataset.kind, name: b.dataset.name || null };
    this._msgs = []; this._sel = null; this._search = ""; this._older = false; this._root.getElementById("search").value = "";
    this._root.getElementById("title").textContent = this._viewName();
    this._root.getElementById("app").classList.remove("mb");
    this._renderList(); this._load();
  }

  // ---------- swiping in the list (iOS): left = archive/delete, right = read/unread ----------
  _swipes(list) {
    let st = null;
    list.addEventListener("pointerdown", (e) => {
      const row = e.target.closest(".row"); if (!row || e.button > 0) return;
      if (this._swipeOpen && this._swipeOpen !== row) this._closeSwipe();
      st = { x: e.clientX, y: e.clientY, row, base: row === this._swipeOpen ? -160 : 0, active: false };
    });
    list.addEventListener("pointermove", (e) => {
      if (!st) return;
      const dx = e.clientX - st.x, dy = e.clientY - st.y;
      if (!st.active) {
        if (Math.abs(dy) > 10 && Math.abs(dy) > Math.abs(dx)) { st = null; return; } // plain scrolling
        if (Math.abs(dx) < 10) return;
        st.active = true; st.row.classList.add("drag");
        try { st.row.setPointerCapture(e.pointerId); } catch (_) {}
      }
      const x = Math.min(110, st.base + dx);
      st.row.closest(".swipe").classList.toggle("right", x > 0);
      st.x2 = x; st.row.style.transform = `translateX(${x}px)`;
    });
    const end = () => {
      if (!st) return;
      const { row, active, x2 = 0 } = st; st = null;
      if (!active) return;
      this._swipeClick = true; setTimeout(() => (this._swipeClick = false), 300);
      row.classList.remove("drag");
      const width = row.offsetWidth, m = this._msgs[+row.closest(".swipe").dataset.i];
      if (x2 > 0) setTimeout(() => row.closest(".swipe")?.classList.remove("right"), 220);
      if (x2 > 70) { row.style.transform = ""; if (m) this._do(m, m.seen ? "unseen" : "seen"); }
      else if (x2 < -width * 0.6) {
        if (this._inTrash() && !confirm(this.t("delete_permanently"))) { row.style.transform = ""; return; }
        row.style.transform = `translateX(${-width}px)`;
        setTimeout(() => this._do(m, "delete"), 180);
        this._swipeOpen = null;
      } else if (x2 < -60) { row.style.transform = "translateX(-160px)"; this._swipeOpen = row; }
      else { row.style.transform = ""; if (this._swipeOpen === row) this._swipeOpen = null; }
    };
    list.addEventListener("pointerup", end);
    list.addEventListener("pointercancel", end);
  }
  _closeSwipe() { if (this._swipeOpen) this._swipeOpen.style.transform = ""; this._swipeOpen = null; }
  _inTrash() { return this._view.kind === "trash"; }
  _swipeAction(m, a) {
    if (a === "delete" && this._inTrash() && !confirm(this.t("delete_permanently"))) return;
    this._do(m, a);
  }

  // iOS gesture: swipe right from the left edge = back (phone layout only, .edge is visible there).
  _edgeSwipe(pane, edge, back) {
    let x0 = null;
    edge.onpointerdown = (e) => { x0 = e.clientX; pane.classList.add("drag"); try { edge.setPointerCapture(e.pointerId); } catch (_) {} };
    edge.onpointermove = (e) => { if (x0 !== null) pane.style.transform = `translateX(${Math.max(0, e.clientX - x0)}px)`; };
    const end = (e) => {
      if (x0 === null) return;
      const dx = e.clientX - x0; x0 = null;
      pane.classList.remove("drag"); pane.classList.add("spring");
      if (dx > pane.offsetWidth * 0.3) {
        pane.style.transform = `translateX(${pane.offsetWidth}px)`;
        setTimeout(() => { pane.classList.remove("spring"); pane.style.transform = ""; back(); }, 220);
      } else {
        pane.style.transform = "";
        setTimeout(() => pane.classList.remove("spring"), 230);
      }
    };
    edge.onpointerup = end; edge.onpointercancel = end;
  }

  // ---------- list ----------
  // The web app can show only recent mail (a period chosen on the phone): first day as "2026-10-15", "" = all.
  _since() { return this.since && !this._older && !this._search ? this.since : ""; }
  async _load(quiet = false) {
    if (!this._root) return;
    const src = { ...this._view };
    const since = this._since();
    const key = src.account + "|" + src.folder + "|" + this._search + "|" + since;
    if (this._busy && this._busyOn === key) return; // same folder already loading; another folder may pass
    this._busy = true; this._busyOn = key;
    const btn = this._root.getElementById("refresh");
    btn.classList.add("spin");
    const here = () => src.account === this._view.account && src.folder === this._view.folder && this._busyOn === key;
    // dates come with different time zones as text; sort on the real moment
    const show = (list) => {
      this._msgs = list.slice().sort((a, b) => (Date.parse(b.date) || 0) - (Date.parse(a.date) || 0));
      if (this._sel && !this._msgs.find((m) => this._key(m) === this._sel)) this._sel = null;
      if (!this._swipeOpen) this._renderList();
    };
    this._lists ??= new Map(); // folder -> last list, this session only: shown at once, then refreshed
    if (!this._msgs.length && this._lists.has(key)) show(this._lists.get(key));
    else if (!this._msgs.length && src.folder === "INBOX" && !this._search) {
      try { // preloaded by Home Assistant: instant
        const c = await this._call("list", { account: src.account, folder: "INBOX", cached: true, ...(since ? { since } : {}) });
        if (c.messages && here() && !this._msgs.length) show(c.messages);
      } catch (_) {}
    }
    try {
      const d = { account: src.account, folder: src.folder, limit: this._search ? 80 : 50 };
      if (this._search) d.search = this._search;
      if (since) d.since = since;
      const r = await this._call("list", d);
      if (src.account === this._view.account && src.folder === this._view.folder) {
        this._msgs = (r.messages || []).sort((a, b) => (Date.parse(b.date) || 0) - (Date.parse(a.date) || 0));
        this._errors = r.errors || [];
        if (this._sel && !this._msgs.find((m) => this._key(m) === this._sel)) this._sel = null;
        if (!this._search) this._lists.set(key, this._msgs);
      }
    } catch (e) {
      this._errors = [this._errText(e) || this.t("load_failed")];
    }
    if (this._busyOn !== key) return; // another folder was chosen meanwhile
    this._busy = false;
    btn.classList.remove("spin");
    if (!this._swipeOpen) this._renderList();
  }
  _key(m) { return m.account + ":" + (m.folder || "INBOX") + ":" + m.uid; }

  // From a notification: open the message with this Message-ID once the list is there (All Inboxes).
  async openByMessageId(id) {
    if (this._view.account !== "all" || this._view.folder !== "INBOX") {
      this._view = { account: "all", folder: "INBOX", kind: "inbox", name: null };
      if (this._built) { this._root.getElementById("title").textContent = this._viewName(); this._root.getElementById("app").classList.remove("mb"); }
      this._msgs = [];
    }
    for (let i = 0; i < 40; i++) { // the list may still be loading (also right after logging in)
      const m = this._msgs.find((x) => x.message_id === id);
      if (m) return this._openMsg(m);
      if (i === 0 && this._built && !this._busy) this._load(true);
      await new Promise((r) => setTimeout(r, 500));
    }
  }

  _renderList() {
    const rows = this._root.getElementById("rows");
    const top = rows.scrollTop;
    this._swipeOpen = null;
    const note = this._errors.length ? `<div class="note">⚠ ${esc(this._errors.join(", "))}</div>` : "";
    const older = this._since() && !this._busy ? `<button class="btn pill older" data-older>${this.t("older")}</button>` : "";
    // "unread only": the open message stays visible, also now it's read (like iOS)
    const shown = this._msgs.map((m, i) => [m, i]).filter(([m]) => !this._unreadOnly || !m.seen || this._sel === this._key(m));
    if (!shown.length) {
      const none = !this._busy && this._set && !Object.keys(this._set.accounts || {}).length && this._set.is_admin !== undefined;
      const txt = none ? this.t("no_access") : this._busy ? this.t("loading") : this._search ? this.t("nothing_found") : this._unreadOnly ? this.t("no_unread") : this.t("no_messages");
      rows.innerHTML = note + `<div class="empty">${esc(txt)}</div>` + older; return;
    }
    const out = this._view.kind === "junk" || this._view.kind === "trash";
    const under = out
      ? `<button class="inb" data-swipe="inbox">${svg(IC.inbox)}${this.t("inbox")}</button><button class="del" data-swipe="delete">${svg(IC.trashcan)}${this._inTrash() ? this.t("erase") : this.t("delete")}</button>`
      : `<button class="arch" data-swipe="archive">${svg(IC.archive)}${this.t("archive")}</button><button class="del" data-swipe="delete">${svg(IC.trashcan)}${this.t("delete")}</button>`;
    const multi = this._view.account === "all";
    rows.innerHTML = note + shown.map(([m, i]) => `
      <div class="swipe" data-i="${i}">
        <div class="over">${svg(IC.seen)}${m.seen ? this.t("unread") : this.t("read")}</div>
        <div class="under">${under}</div>
        <div class="row${m.seen ? " read" : ""}${this._sel === this._key(m) ? " sel" : ""}" role="button" tabindex="0">
          ${m.seen ? (m.answered ? `<span class="arrow">${svg(IC.reply)}</span>` : "") : '<span class="dot"></span>'}
          <div class="r1"><span class="from">${multi ? `<span class="acc" style="background:${esc(this._color(m.account))}"></span>` : ""}${esc(m.name)}</span>
            <span class="mark">${m.flagged ? svg(IC.flag).replace('fill="none"', 'fill="currentColor"') : ""}${m.attachment ? svg(IC.clip) : ""}</span><span class="t">${esc(this._time(m.date))}</span></div>
          <div class="subj">${esc(m.subject || this.t("no_subject"))}</div>
          <div class="pv">${esc(clean(m.preview))}</div>
        </div>
      </div>`).join("") + older;
    rows.scrollTop = top;
  }

  // ---------- reading ----------
  async _openMsg(m) {
    this._sel = this._key(m);
    this._open = { ...m, loading: true };
    this._root.getElementById("app").classList.add("open");
    if (!m.seen) m.seen = true;
    this._renderList(); this._renderReader();
    try {
      const r = await this._call("read", { account: m.account, uid: m.uid, folder: m.folder || "INBOX", mark: true });
      if (this._sel !== this._key(m)) return;
      this._open = { ...m, ...r, account: m.account, folder: m.folder, loading: false };
    } catch (e) {
      if (this._sel === this._key(m)) this._open = { ...m, error: this._errText(e) };
    }
    this._renderReader();
  }
  _size(n) { return n >= 1048576 ? (n / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(n / 1024)) + " kB"; }
  // Download an attachment piece by piece over the websocket, then open it (second tap, so the browser allows it).
  async _attachment(m, index, btn) {
    if (btn._url) { // already downloaded: open or save it
      const a = document.createElement("a");
      a.href = btn._url; a.download = btn._name; a.target = "_blank"; a.rel = "noopener";
      this._root.append(a); a.click(); a.remove();
      return;
    }
    if (btn.disabled) return;
    const label = btn.innerHTML;
    btn.disabled = true;
    try {
      const parts = []; let offset = 0, r;
      do {
        r = await this._call("attachment", { account: m.account, folder: m.folder || "INBOX", uid: m.uid, index, offset });
        const bin = atob(r.data), buf = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
        parts.push(buf); offset += buf.length;
        btn.textContent = `${r.name} · ${Math.min(100, Math.round((offset / Math.max(1, r.size)) * 100))}%`;
      } while (!r.eof);
      btn._url = URL.createObjectURL(new Blob(parts, { type: r.type }));
      btn._name = r.name;
      btn.innerHTML = label.replace(/·.*$/, "") + `· ${this.t("tap_open")}`;
    } catch (e) {
      btn.innerHTML = label;
      this._toast(this.t("attach_failed", { e: this._errText(e) }));
    }
    btn.disabled = false;
  }
  _closeReader() { this._open = null; this._root.getElementById("app").classList.remove("open"); this._renderReader(); }

  _renderReader() {
    const el = this._root.getElementById("reader"), m = this._open;
    if (!m) { el.innerHTML = `<div class="empty">${this.t("no_selection")}</div>`; return; }
    const att = (m.attachments || []).map((b, i) => `<button type="button" data-att="${i}">${svg(IC.clip)}${esc(b.name || this.t("attachment"))} · ${this._size(b.size)}</button>`).join("");
    const ready = !m.loading && !m.error;
    const out = this._view.kind === "junk" || this._view.kind === "trash";
    el.innerHTML = `
      <div class="edge" id="edge"></div>
      <div class="bar">
        <button class="btn back" id="back" title="${this.t("back")}">${svg(IC.back)}${esc(this._viewName())}</button><span class="fill"></span>
        <button class="btn${m.flagged ? " on" : ""}" data-a="flag" title="${this.t("flag")}">${svg(IC.flag)}</button>
        <button class="btn" data-a="seen" title="${m.seen ? this.t("mark_unread") : this.t("mark_read")}">${svg(IC.seen)}</button>
        ${out ? `<button class="btn" data-a="inbox" title="${this.t("move_inbox")}">${svg(IC.inbox)}</button>` : `<button class="btn" data-a="archive" title="${this.t("archive_it")}">${svg(IC.archive)}</button>`}
        <button class="btn" data-a="delete" title="${this._inTrash() ? this.t("delete_perm") : this.t("delete_it")}">${svg(IC.trashcan)}</button>
        <button class="btn" id="reply" title="${this.t("reply")}" ${ready ? "" : "disabled"}>${svg(IC.reply)}</button>
      </div>
      <div class="mhead"><div class="name">${esc(m.name)}</div><div class="adr">${esc(m.address || "")}</div>
        ${m.to ? `<div class="to">${this.t("to")}: ${esc(m.to)}</div>` : ""}<div class="dat">${esc(this._fullDate(m.date))}</div>
        <div class="subject">${esc(m.subject || this.t("no_subject"))}</div>${att ? `<div class="att">${att}</div>` : ""}</div>
      ${m.loading ? `<div class="empty">${this.t("loading")}</div>` : m.error ? `<div class="empty">${esc(m.error)}</div>` : '<iframe id="frame" sandbox="allow-popups allow-popups-to-escape-sandbox" referrerpolicy="no-referrer"></iframe>'}`;
    const back = () => { this._sel = null; this._closeReader(); this._renderList(); };
    el.querySelector("#back").onclick = back;
    this._edgeSwipe(el, el.querySelector("#edge"), back);
    el.querySelectorAll("[data-a]").forEach((b) => (b.onclick = () => this._toolbar(b.dataset.a)));
    el.querySelector("#reply").onclick = (e) => { e.stopPropagation(); this._replyMenu(el.querySelector(".bar")); };
    el.querySelectorAll("[data-att]").forEach((b) => (b.onclick = () => this._attachment(m, Number(b.dataset.att), b)));
    const frame = el.querySelector("#frame");
    if (frame) {
      const csp = this._set.images === false ? CSP_OFF : CSP_ON;
      frame.srcdoc = `<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="${csp}">
        <meta name="viewport" content="width=device-width,initial-scale=1"><base target="_blank">
        <style>html{background:#fff;color:#000}body{margin:0;padding:12px;font:16px/1.45 -apple-system,system-ui,sans-serif;overflow-wrap:anywhere}img{max-width:100%;height:auto}table{max-width:100%}</style>
        </head><body>${m.html}</body></html>`;
    }
  }

  _replyMenu(bar) {
    const old = bar.querySelector(".menu"); if (old) { old.remove(); return; }
    const menu = document.createElement("div");
    menu.className = "menu";
    menu.innerHTML = `<button data-s="reply">${svg(IC.reply)}${this.t("reply")}</button><button data-s="reply_all">${svg(IC.reply)}${this.t("reply_all")}</button><button data-s="forward">${svg(IC.send)}${this.t("forward")}</button>`;
    menu.onclick = (e) => { const b = e.target.closest("[data-s]"); if (b) { menu.remove(); this._compose(b.dataset.s, this._open); } };
    bar.appendChild(menu);
    setTimeout(() => this._root.addEventListener("click", () => menu.remove(), { once: true }), 0);
  }

  // ---------- compose: new / reply / reply_all / forward ----------
  async _loadContacts() {
    if (this._contactsAt && Date.now() - this._contactsAt < 600000) return;
    this._contactsAt = Date.now();
    try { this._contacts = (await this._call("contacts")).contacts || []; } catch (_) { this._contactsAt = 0; }
  }
  _compose(mode, m = null) {
    const accs = Object.keys(this._set.accounts || {});
    if (!accs.length) { this._toast(this.t("no_access")); return; }
    const account = m?.account || (this._view.account !== "all" ? this._view.account : this._set.default) || accs[0];
    const own = accs.map((a) => (this._set.accounts[a].address || "").toLowerCase());
    const sig = (a) => this._set.accounts[a]?.signature || `${this.t("closing")}\n\n${this._set.user_name || ""}`.trimEnd();
    let to = [], cc = [], subject = "";
    if (m && mode !== "forward") {
      to = [m.reply_to || m.address];
      if (mode === "reply_all") cc = [...(m.to_addresses || []), ...(m.cc_addresses || [])].filter((a) => a && !own.includes(a.toLowerCase()) && !to.includes(a));
      subject = /^re:/i.test(m.subject || "") ? m.subject : "Re: " + (m.subject || "");
    } else if (m) subject = /^(fwd?|doorst):/i.test(m.subject || "") ? m.subject : "Fwd: " + (m.subject || "");
    const veil = document.createElement("div");
    veil.className = "veil";
    const title = mode === "new" ? this.t("new_message") : mode === "forward" ? this.t("forward") : this.t("reply");
    veil.innerHTML = `
      <div class="sheet">
        <div class="sbar"><button class="btn" data-o="cancel">${this.t("cancel")}</button><b>${esc(title)}</b>
          <button class="btn sendbtn" data-o="send" title="${this.t("send")}">${svg(IC.send)}</button></div>
        <div class="field"><label>${this.t("to")}:</label><input id="c-to" type="email" multiple list="c-known" autocomplete="off" value="${esc(to.join(", "))}"></div>
        <div class="field"><label>${this.t("cc")}:</label><input id="c-cc" type="email" multiple list="c-known" autocomplete="off" value="${esc(cc.join(", "))}"></div>
        <div class="field"><label>${this.t("from")}:</label><select id="c-from">${accs.map((a) => `<option value="${esc(a)}"${a === account ? " selected" : ""}>${esc(this._set.accounts[a].address || a)}</option>`).join("")}</select></div>
        <div class="field"><label>${this.t("subject")}:</label><input id="c-subj" value="${esc(subject)}"></div>
        <div class="field attrow" id="c-atts"><button type="button" class="add" id="c-add">${svg(IC.clip)} ${this.t("attach_add")}</button><input type="file" id="c-file" multiple hidden></div>
        <textarea class="body" id="c-body"></textarea>
        <div class="foot" id="c-foot">${m ? (mode === "forward" ? this.t("quote_forward") : this.t("quote_reply")) : ""}${this._set.bcc_me ? " " + this.t("bcc_on") : ""}</div>
        <datalist id="c-known"></datalist>
      </div>`;
    this._root.getElementById("app").appendChild(veil);
    const $ = (s) => veil.querySelector(s);
    const fillKnown = () => {
      const seen = new Map();
      for (const c of this._contacts) seen.set(c.address, c.name);
      for (const x of this._msgs) if (x.address && !seen.has(x.address)) seen.set(x.address, x.name);
      $("#c-known").innerHTML = [...seen].slice(0, 1000).map(([a, n]) => `<option value="${esc(a)}">${esc(n || "")}</option>`).join("");
    };
    fillKnown();
    this._loadContacts().then(fillKnown);
    const body = $("#c-body");
    body.value = "\n\n" + sig(account);
    let prev = account;
    $("#c-from").onchange = (e) => { // the signature follows the account
      const s0 = sig(prev), s1 = sig(e.target.value);
      if (s0 && body.value.endsWith(s0)) body.value = body.value.slice(0, -s0.length) + s1;
      else if (!s0) body.value = body.value + s1;
      prev = e.target.value;
    };
    setTimeout(() => { (to.length ? body : $("#c-to")).focus(); body.setSelectionRange(0, 0); }, 50);
    const start = body.value;
    // attachments: sent to Home Assistant piece by piece as soon as they are picked, then referenced when sending
    const atts = [];
    const drawAtts = () => {
      veil.querySelectorAll("#c-atts .chip").forEach((c) => c.remove());
      atts.forEach((a, i) => $("#c-atts").insertBefore(Object.assign(document.createElement("span"), { className: "chip",
        innerHTML: `${esc(a.name)} <b>${a.done ? this._size(a.size) : a.error ? "!" : Math.round(a.pct) + "%"}</b><button type="button" class="x" data-rm="${i}">✕</button>` }), $("#c-add")));
      veil.querySelectorAll("[data-rm]").forEach((b) => (b.onclick = () => {
        const a = atts.splice(Number(b.dataset.rm), 1)[0]; a.removed = true;
        this._call("upload_remove", { file: a.id }).catch(() => {}); drawAtts();
      }));
    };
    const upload = async (file) => {
      const a = { id: Math.random().toString(36).slice(2) + Date.now().toString(36), name: file.name, size: file.size, pct: 0, done: false };
      if (file.size > 20 * 1024 * 1024) { this._toast(this.t("attach_big", { n: file.name })); return; }
      atts.push(a); drawAtts();
      try {
        const CH = 256 * 1024;
        for (let o = 0; o < file.size || o === 0; o += CH) {
          if (a.removed) return;
          const buf = new Uint8Array(await file.slice(o, o + CH).arrayBuffer());
          let bin = ""; for (let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
          await this._call("upload", { file: a.id, name: file.name, ctype: file.type || "application/octet-stream", data: btoa(bin), last: o + CH >= file.size });
          a.pct = Math.min(100, ((o + CH) / Math.max(1, file.size)) * 100); drawAtts();
        }
        a.done = true;
      } catch (e) {
        a.error = true; atts.splice(atts.indexOf(a), 1);
        this._toast(this.t("attach_failed", { e: this._errText(e) }));
      }
      drawAtts();
    };
    $("#c-add").onclick = () => $("#c-file").click();
    $("#c-file").onchange = (e) => { [...e.target.files].forEach(upload); e.target.value = ""; };
    veil.querySelector("[data-o=cancel]").onclick = () => {
      if ((body.value !== start || $("#c-to").value !== to.join(", ") || atts.length) && !confirm(this.t("discard"))) return;
      atts.forEach((a) => { a.removed = true; this._call("upload_remove", { file: a.id }).catch(() => {}); });
      veil.remove();
    };
    veil.querySelector("[data-o=send]").onclick = async (e) => {
      const btn = e.currentTarget, foot = $("#c-foot");
      const d = {
        account: $("#c-from").value, to: addressList($("#c-to").value), cc: addressList($("#c-cc").value),
        subject: $("#c-subj").value.trim(), body: body.value.replace(/^\n+/, ""), mode, language: this._lang,
      };
      if (!d.to.length) { foot.innerHTML = `<span class="error">${this.t("need_recipient")}</span>`; return; }
      if (atts.some((a) => !a.done)) { foot.innerHTML = `<span class="error">${this.t("attach_busy")}</span>`; return; }
      d.attachments = atts.map((a) => a.id);
      if (!d.subject && !confirm(this.t("no_subject_ok"))) return;
      if (m && m.account === d.account) { d.original_uid = m.uid; d.folder = m.folder || "INBOX"; }
      else if (m && mode === "forward") { d.mode = "new"; } // another account cannot fetch the original
      btn.disabled = true; foot.textContent = this.t("sending");
      try {
        await this._call("send", d);
      } catch (err) {
        btn.disabled = false; foot.innerHTML = `<span class="error">${esc(this.t("not_sent", { e: this._errText(err) }))}</span>`;
        return;
      }
      veil.remove();
      if (m && mode !== "forward") { m.answered = true; const r = this._msgs.find((x) => this._key(x) === this._key(m)); if (r) r.answered = true; this._renderList(); }
      this._toast(this.t("sent_ok"));
    };
  }

  _toast(text) {
    const t = document.createElement("div");
    t.className = "toast"; t.textContent = text;
    this._root.getElementById("app").appendChild(t);
    setTimeout(() => t.remove(), 2200);
  }

  // ---------- actions ----------
  _toolbar(a) {
    const m = this._open; if (!m || m.loading) return;
    let act = a;
    if (a === "flag") act = m.flagged ? "unflag" : "flag";
    if (a === "seen") act = m.seen ? "unseen" : "seen";
    if (a === "delete" && this._inTrash() && !confirm(this.t("delete_permanently"))) return;
    return this._do(m, act);
  }

  async _do(m, act) { // action on a message (list swipe or reader toolbar)
    if (!m) return;
    const k = this._key(m);
    const row = this._msgs.find((x) => this._key(x) === k);
    const btns = this._root.querySelectorAll(".bar .btn"); btns.forEach((b) => (b.disabled = true));
    const away = act === "archive" || act === "delete" || act === "inbox";
    if (away) { // straight out of the list, like iOS; on an error it comes back with the next refresh
      const i = this._msgs.indexOf(row); if (i >= 0) this._msgs.splice(i, 1);
      if (this._sel === k) { this._sel = null; this._closeReader(); }
      this._renderList();
    }
    try {
      const r = await this._call("action", { account: m.account, uid: m.uid, folder: m.folder || "INBOX", action: act });
      if (away) this._toast(r.permanent ? this.t("deleted_perm") : act === "delete" ? this.t("to_trash") : act === "inbox" ? this.t("to_inbox") : this.t("archived"));
    } catch (e) {
      btns.forEach((b) => (b.disabled = false));
      this._errors = [this.t("action_failed", { e: this._errText(e) })];
      if (away) this._load(true); else this._renderList();
      return;
    }
    if (away) return;
    const o = this._open && this._key(this._open) === k ? this._open : null;
    for (const x of [row, o]) if (x) {
      if (act === "flag" || act === "unflag") x.flagged = act === "flag";
      else x.seen = act === "seen";
    }
    this._renderList();
    if (o) this._renderReader();
  }

  // ---------- settings ----------
  async _settings() {
    await this._loadSettings();
    const veil = document.createElement("div");
    veil.className = "veil";
    this._root.getElementById("app").appendChild(veil);
    const close = () => { veil.remove(); this._loadMb(); };
    const show = () => {
      const s = this._set, accs = Object.keys(s.accounts || {});
      const appUrl = s.app_urls?.external || s.app_urls?.internal || location.origin + "/homemail-files/app.html";
      veil.innerHTML = `<div class="sheet grey">
        <div class="sbar"><span style="width:80px"></span><b>${this.t("settings")}</b><button class="btn" data-x style="width:80px;justify-content:flex-end">${this.t("done")}</button></div>
        <div class="scroll"><div class="gtitle" style="margin-top:18px">${this.t("accounts")}</div><div class="group">
          ${accs.map((a) => `<button class="item" data-acc="${esc(a)}"><span class="acc" style="background:${esc(s.accounts[a].color)};width:12px;height:12px;margin:0 6px"></span><span class="text"><span class="name">${esc(s.accounts[a].name)}<span class="sub2">${esc(s.accounts[a].address || "")}${s.is_admin && !(s.accounts[a].users || []).length ? ` · <span class="warn">${this.t("all_admins")}</span>` : ""}</span></span>${svg(IC.next, "chev")}</span></button>`).join("")}
          <button class="item" data-add><span style="width:24px"></span><span class="text"><span class="name">${this.t("add_account")}</span>${svg(IC.next, "chev")}</span></button></div>
          <div class="group"><button class="item" data-notif><span style="width:24px"></span><span class="text"><span class="name">${this.t("notifications")}</span>${svg(IC.next, "chev")}</span></button></div>
          <div class="gtitle">${this.t("composing")}</div><div class="group">
            <label class="item"><span class="text"><span class="name">${this.t("bcc_me")}</span><input type="checkbox" data-opt="bcc_me"${s.bcc_me ? " checked" : ""}></span></label>
            <label class="item"><span class="text"><span class="name">${this.t("load_images")}</span><input type="checkbox" data-opt="images"${s.images !== false ? " checked" : ""}></span></label>
            <label class="item"><span class="text"><span class="name">${this.t("default_account")}</span><select data-opt="default">${accs.map((a) => `<option value="${esc(a)}"${a === s.default ? " selected" : ""}>${esc(s.accounts[a].name)}</option>`).join("")}</select></span></label>
          </div>
          <div class="explain">${this.t("settings_note")}</div>
          ${this.mailWindow ? `<div class="group"><button class="item" data-period><span style="width:24px"></span><span class="text"><span class="name">${this.t("period")}<span class="sub2">${esc(this.mailWindow.label())}</span></span>${svg(IC.next, "chev")}</span></button>
            <button class="item" data-folders><span style="width:24px"></span><span class="text"><span class="name">${this.t("folders_app")}<span class="sub2">${esc(this._hiddenLabel())}</span></span>${svg(IC.next, "chev")}</span></button></div>` : ""}
          <div class="gtitle">${this.t("app_title")}</div><div class="group"><div class="item"><input type="text" id="app-url" readonly value="${esc(appUrl)}" style="flex:1;min-width:0;border:0;outline:0;background:transparent;color:inherit;font:inherit;padding:12px 0"><button type="button" class="btn" data-copy>${svg(IC.copy)}${this.t("copy")}</button></div></div>
          <div class="explain">${this.t("app_note")}${appUrl.startsWith("https:") ? "" : " " + this.t("app_note_http")}</div>
          ${s.version ? `<div class="explain" style="text-align:center;margin-top:28px">Home-mail ${esc(s.version)}</div>` : ""}
        </div></div>`;
      const url = veil.querySelector("#app-url");
      url.onfocus = () => url.select();
      url.onclick = () => url.select();
      veil.querySelector("[data-copy]").onclick = () => navigator.clipboard?.writeText(url.value).then(() => this._toast(this.t("copied")), () => url.select());
      veil.querySelector("[data-x]").onclick = close;
      veil.querySelector("[data-notif]").onclick = () => this._notifyScreen(veil, show);
      const per = veil.querySelector("[data-period]");
      if (per) per.onclick = () => this.mailWindow.edit().then(show);
      const fol = veil.querySelector("[data-folders]");
      if (fol) fol.onclick = () => this._foldersScreen(veil, show);
      veil.querySelectorAll("[data-acc]").forEach((b) => (b.onclick = () => this._accountScreen(veil, b.dataset.acc, show)));
      veil.querySelector("[data-add]").onclick = () => (s.is_admin ? this._addAccount(veil, show) : this._toast(this.t("admin_only")));
      veil.querySelectorAll("[data-opt]").forEach((el) => (el.onchange = () => {
        this._saveSettings({ [el.dataset.opt]: el.type === "checkbox" ? el.checked : el.value });
      }));
    };
    show();
  }
  _hiddenLabel() {
    const n = Object.values(this._hidden).reduce((s, v) => s + v.length, 0);
    return n ? this.t("folders_hidden", { n }) : this.t("folders_all");
  }
  // Web app: which folders it shows (the inbox always). Saved on the phone at once.
  async _foldersScreen(veil, back) {
    if (!this._mb?.accounts) { try { this._mb = await this._call("mailboxes", { cached: true }); } catch (_) {} }
    if (!this._mb?.accounts) { try { this._mb = await this._call("mailboxes"); } catch (_) {} }
    const accs = this._mb?.accounts || [];
    veil.innerHTML = `<div class="sheet grey">
      <div class="sbar"><button class="btn" data-back>${svg(IC.back)}${this.t("back")}</button><b>${this.t("folders_app")}</b><span style="width:80px"></span></div>
      <div class="scroll">${accs.map((a) => `<div class="gtitle" style="margin-top:18px">${esc(a.name)}</div><div class="group">${a.folders.map((f) =>
        `<label class="item"><span style="width:24px"></span><span class="text"><span class="name">${esc(f.kind === "custom" ? f.path : this.t(f.kind))}</span><input type="checkbox" data-hf="${esc(a.account)}" data-f="${esc(f.folder)}"${f.kind === "inbox" ? " checked disabled" : (this._hidden[a.account] || []).includes(f.folder) ? "" : " checked"}></span></label>`).join("")}</div>`).join("")}
      <div class="explain">${this.t("folders_note")}</div></div></div>`;
    veil.querySelector("[data-back]").onclick = () => { this._loadMb(); back(); };
    veil.querySelectorAll("[data-hf]").forEach((el) => (el.onchange = () => {
      const acc = el.dataset.hf, list = (this._hidden[acc] || []).filter((x) => x !== el.dataset.f);
      if (!el.checked) list.push(el.dataset.f);
      if (list.length) this._hidden[acc] = list; else delete this._hidden[acc];
      store("homemail_hidden_folders", this._hidden);
      this._renderMb();
    }));
  }
  _notifyScreen(veil, back, draft) {
    // changes are kept in a draft and only saved with the Save button
    const s = this._set, t = (k) => this.t(k);
    const saved = JSON.stringify(s.notify);
    const n = draft || JSON.parse(saved);
    const accs = Object.entries(s.accounts || {});
    const sw = (k, label, on = n[k]) => `<label class="item"><span class="text"><span class="name">${label}</span><input type="checkbox" data-n="${k}"${on ? " checked" : ""}></span></label>`;
    const rerender = (patch) => { Object.assign(n, patch); this._notifyScreen(veil, back, n); };
    n.device_accounts_off = n.device_accounts_off || {};
    // "Home-mail iPhone 4f2a" -> iPhone · web app · 4f2a (older registrations: "Home-mail ngelre" -> web app ngelre)
    const webLabel = (name) => {
      const rest = name.replace(/^Home-mail\s*/, ""), m = rest.match(/^(iPhone|iPad|Mac|Android|Windows|Browser) (\w{4})$/);
      return m ? { name: m[1], sub: `${t("web_app")} · ${m[2]}` } : { name: `${t("web_app")} ${rest}`.trim(), sub: "" };
    };
    // per device: which accounts notify there (only shown with more than one account)
    const devAccs = (key) => accs.length < 2 ? "" : `<div class="item"><span style="width:24px"></span><span class="text" style="flex-wrap:wrap;gap:6px;padding:4px 14px 10px 0">${accs.filter(([id]) => !n.accounts_off.includes(id)).map(([id, a]) =>
      `<button type="button" class="dayb${(n.device_accounts_off[key] || []).includes(id) ? "" : " on"}" data-dacc="${esc(key)}" data-acc-id="${esc(id)}">${esc(a.name)}</button>`).join("")}</span></div>`;
    const readText = () => veil.querySelectorAll("textarea[data-n]").forEach((el) => (n[el.dataset.n] = el.value)); // still being typed
    const dirty = () => { readText(); return JSON.stringify(n) !== saved; };
    veil.innerHTML = `<div class="sheet grey">
      <div class="sbar"><button class="btn" data-back>${svg(IC.back)}${t("back")}</button><b>${t("notifications")}</b><button class="btn" data-save style="width:80px;justify-content:flex-end">${t("save")}</button></div>
      <div class="scroll"><div class="group" style="margin-top:18px">${sw("on", t("notif_on"))}</div>
      <div class="explain">${t("notif_note")}</div>
      ${n.on ? `
      <div class="gtitle">${t("notif_accounts")}</div><div class="group">${accs.map(([id, a]) => `<label class="item"><span class="acc" style="background:${esc(a.color)};width:12px;height:12px;margin:0 6px"></span><span class="text"><span class="name">${esc(a.name)}<span class="sub2">${esc(a.address || "")}</span></span><input type="checkbox" data-accn="${esc(id)}"${n.accounts_off.includes(id) ? "" : " checked"}></span></label>`).join("")}</div>
      <div class="gtitle">${t("notif_which")}</div><div class="group">
        <label class="item"><span class="text"><span class="name">${t("notif_which")}</span><select data-n="only"><option value="all"${n.only === "all" ? " selected" : ""}>${t("notif_all")}</option><option value="vip"${n.only === "vip" ? " selected" : ""}>${t("notif_vip")}</option></select></span></label>
        ${n.only === "vip" ? `<div class="item"><span class="text"><span class="name">${t("notif_vip_list")}</span></span></div><div class="item"><textarea class="nl" data-n="vip">${esc(n.vip)}</textarea></div>` : ""}
        <div class="item"><span class="text"><span class="name">${t("notif_mute")}</span></span></div><div class="item"><textarea class="nl" data-n="mute">${esc(n.mute)}</textarea></div>
      </div>
      <div class="explain">${t("notif_list_note")}</div>
      <div class="gtitle">${t("notif_when")}</div><div class="group">
        <div class="item"><span class="text" style="flex-wrap:wrap;gap:6px;padding:10px 14px 10px 0">${t("days").split(",").map((d, i) => `<button type="button" class="dayb${n.days.includes(i) ? " on" : ""}" data-day="${i}">${d}</button>`).join("")}</span></div>
        ${sw("quiet_on", t("notif_quiet"))}
        ${n.quiet_on ? `<label class="item"><span class="text"><span class="name">${t("notif_from")}</span><input type="time" data-n="quiet_from" value="${esc(n.quiet_from)}"></span></label>
        <label class="item"><span class="text"><span class="name">${t("notif_to")}</span><input type="time" data-n="quiet_to" value="${esc(n.quiet_to)}"></span></label>` : ""}
      </div>
      <div class="explain">${t("notif_quiet_note")}</div>
      <div class="gtitle">${t("notif_show")}</div><div class="group">${sw("preview", t("notif_preview"))}${sw("sound", t("notif_sound"))}${sw("buttons", t("notif_buttons"))}</div>
      <div class="explain">${t("notif_buttons_note")}</div>
      <div class="gtitle">${t("notif_where")}</div><div class="group">
        ${sw("app", t("notif_app"))}
        ${n.app ? (s.notify_devices || []).map((d) => `<label class="item"><span style="width:24px"></span><span class="text"><span class="name">${esc(d.name)}<span class="sub2">${[d.os, this._lastSent(d.last)].filter(Boolean).map(esc).join(" · ")}</span></span><input type="checkbox" data-dev="${esc(d.name)}"${n.devices_off.includes(d.name) ? "" : " checked"}></span></label>${n.devices_off.includes(d.name) ? "" : devAccs(`app:${d.name}`)}`).join("") : ""}
        ${sw("web", t("notif_web"))}
        ${n.web ? (s.notify_web_devices || []).map((d) => { const w = webLabel(d.name); return `<div class="item"><span style="width:24px"></span><span class="text"><span class="name">${esc(w.name)}<span class="sub2">${[w.sub, this._lastSent(d.last)].filter(Boolean).map(esc).join(" · ")}</span></span><button type="button" class="btn" data-forget="${esc(d.name)}">${t("forget")}</button></span></div>${devAccs(`web:${d.name}`)}`; }).join("") : ""}
      </div>
      <div class="explain">${(s.notify_devices || []).length || (s.notify_web_devices || []).length ? t("notif_devices_note") : t("notif_no_devices")} ${(s.notify_web_devices || []).length ? "" : t("notif_web_none")}</div>
      <div class="group"><button class="item" data-test><span class="text"><span class="name" style="color:var(--blue)">${t("notif_test")}</span></span></button></div>` : ""}
      </div></div>`;
    veil.querySelector("[data-back]").onclick = () => { if (dirty() && !confirm(t("discard_changes"))) return; back(); };
    veil.querySelector("[data-save]").onclick = async () => { readText(); await this._saveSettings({ notify: n }); back(); };
    veil.querySelectorAll("[data-n]").forEach((el) => (el.onchange = () => {
      const patch = { [el.dataset.n]: el.type === "checkbox" ? el.checked : el.value };
      if (el.type === "checkbox" || el.tagName === "SELECT") rerender(patch); else Object.assign(n, patch);
    }));
    veil.querySelectorAll("[data-accn]").forEach((el) => (el.onchange = () => {
      n.accounts_off = [...veil.querySelectorAll("[data-accn]")].filter((x) => !x.checked).map((x) => x.dataset.accn);
    }));
    veil.querySelectorAll("[data-dev]").forEach((el) => (el.onchange = () => {
      n.devices_off = [...veil.querySelectorAll("[data-dev]")].filter((x) => !x.checked).map((x) => x.dataset.dev);
    }));
    veil.querySelectorAll("[data-dacc]").forEach((b) => (b.onclick = () => {
      const key = b.dataset.dacc, id = b.dataset.accId, off = n.device_accounts_off[key] || [];
      const next = off.includes(id) ? off.filter((x) => x !== id) : [...off, id];
      const map = { ...n.device_accounts_off, [key]: next };
      if (!next.length) delete map[key];
      rerender({ device_accounts_off: map });
    }));
    veil.querySelectorAll("[data-day]").forEach((b) => (b.onclick = () => {
      const d = Number(b.dataset.day), days = n.days.includes(d) ? n.days.filter((x) => x !== d) : [...n.days, d];
      rerender({ days });
    }));
    veil.querySelectorAll("[data-forget]").forEach((b) => (b.onclick = async () => {
      if (!confirm(t("forget_confirm"))) return;
      try { this._set = await this._call("push_remove", { name: b.dataset.forget }); } catch (_) { this._toast(t("save_failed")); return; }
      this._notifyScreen(veil, back, n);
    }));
    // the test uses what is on screen, saved or not
    const test = veil.querySelector("[data-test]");
    if (test) test.onclick = async () => {
      try {
        const r = await this._call("notify_test", { notify: n });
        this._toast(t(r.app + r.web ? "notif_test_sent" : "notif_test_none"));
        this._set = await this._call("settings"); // fresh results per device
        this._notifyScreen(veil, back, n);
      } catch (_) { this._toast(t("save_failed")); }
    };
  }
  _lastSent(last) { // "Last: 21:36" or "Failed 21:36: <reason>"
    if (!last) return "";
    const at = new Date(last.ts * 1000).toLocaleString(this._locale(), { weekday: "short", hour: "2-digit", minute: "2-digit" });
    return last.ok ? this.t("last_ok", { t: at }) : this.t("last_fail", { t: at, e: last.error.replace(/^.*?:\s*/, "").slice(0, 80) });
  }
  async _saveSettings(changes) {
    try { this._set = await this._call("settings", { changes }); this._toast(this.t("saved")); }
    catch (e) { this._toast(this.t("save_failed")); }
  }

  _accountScreen(veil, acc, back) {
    const a = this._set.accounts[acc];
    const colors = ["#0a84ff", "#ea4335", "#f5a623", "#34c759", "#af52de", "#ff2d55", "#8e8e93"];
    if (a.color && !colors.includes(a.color)) colors.push(a.color);
    veil.innerHTML = `<div class="sheet grey">
      <div class="sbar"><button class="btn" data-back>${svg(IC.back)}${this.t("back")}</button><b>${esc(a.name)}</b><button class="btn" data-save>${this.t("save")}</button></div>
      <div class="scroll"><div class="gtitle" style="margin-top:18px">${this.t("account")}</div><div class="group">
        <label class="item"><span class="text"><span class="name">${this.t("name")}</span><input type="text" id="a-sender" value="${esc(a.sender || "")}" placeholder="${this.t("your_name")}"></span></label>
        <div class="item"><span class="text"><span class="name">${this.t("email")}</span><span class="cnt">${esc(a.address || "")}</span></span></div>
        <label class="item"><span class="text"><span class="name">${this.t("description")}</span><input type="text" id="a-name" value="${esc(a.name)}"></span></label>
        <div class="item"><span class="text"><span class="name">${this.t("color")}</span><span class="swatches" id="a-color" data-v="${esc(a.color || colors[0])}">${colors.map((k) => `<button type="button" class="sw${k === (a.color || colors[0]) ? " on" : ""}" data-c="${k}" style="background:${k}" aria-label="${k}"></button>`).join("")}</span></span></div>
      </div>
      <div class="explain" style="margin-top:-14px">${this.t("account_note")}</div>
      <div class="gtitle">${this.t("signature")}</div><div class="group"><div class="item"><textarea id="a-sig">${esc(a.signature || `${this.t("closing")}\n\n${this._set.user_name || ""}`.trimEnd())}</textarea></div></div>
      <div class="explain">${this.t("signature_note")}</div>
      <div class="gtitle">${this.t("new_mail")}</div><div class="group"><div class="item"><span class="text"><span class="name">${
        a.push === "on" ? this.t("push_on") : this.t("push_every", { n: Math.round((a.interval || 60) / 60) || 1 })}</span></span></div></div>
      <div class="explain">${a.push === "on" ? this.t("push_on_note") : a.push === "unsupported" ? this.t("push_unsupported") : a.push === "error" ? this.t("push_error") : this.t("push_off_note")}</div>
      ${this._set.is_admin ? `<div class="gtitle">${this.t("access")}</div><div class="group">${(this._set.ha_users || []).map((u) => `<label class="item"><span class="text"><span class="name">${esc(u.name)}${u.id === this._set.user_id ? ` (${this.t("you")})` : ""}</span><input type="checkbox" data-user="${esc(u.id)}"${(a.users || []).includes(u.id) ? " checked" : ""}></span></label>`).join("")}</div>
      <div class="explain">${(a.users || []).length ? this.t("access_note") : `<span class="warn">${this.t("access_all_admins")}</span>`}</div>` : ""}
      </div></div>`;
    veil.querySelector("[data-back]").onclick = back;
    const sw = veil.querySelector("#a-color");
    sw.onclick = (e) => { // colour swatches like iOS
      const b = e.target.closest("[data-c]"); if (!b) return;
      sw.dataset.v = b.dataset.c;
      sw.querySelectorAll(".sw").forEach((x) => x.classList.toggle("on", x === b));
    };
    veil.querySelector("[data-save]").onclick = async () => {
      const users = [...veil.querySelectorAll("[data-user]")].filter((x) => x.checked).map((x) => x.dataset.user);
      if (this._set.is_admin && users.length && !users.includes(this._set.user_id) && !confirm(this.t("access_lose"))) return;
      await this._saveSettings({ accounts: { [acc]: { name: veil.querySelector("#a-name").value.trim() || a.name,
        sender: veil.querySelector("#a-sender").value.trim(),
        color: veil.querySelector("#a-color").dataset.v, signature: veil.querySelector("#a-sig").value,
        ...(this._set.is_admin ? { users: [...veil.querySelectorAll("[data-user]")].filter((x) => x.checked).map((x) => x.dataset.user) } : {}) } } });
      back();
    };
  }

  _addAccount(veil, back) {
    const PROVIDERS = ["gmail", "icloud", "outlook", "other"];
    const choose = () => {
      veil.innerHTML = `<div class="sheet grey">
        <div class="sbar"><button class="btn" data-back>${svg(IC.back)}${this.t("back")}</button><b>${this.t("add_account")}</b><span style="width:80px"></span></div>
        <div class="scroll"><div class="group" style="margin-top:22px">
          ${PROVIDERS.map((k) => `<button class="item" data-p="${k}"><span style="width:8px"></span><span class="text"><span class="name">${this.t("p_" + k)}</span>${svg(IC.next, "chev")}</span></button>`).join("")}
        </div></div></div>`;
      veil.querySelector("[data-back]").onclick = back;
      veil.querySelectorAll("[data-p]").forEach((b) => (b.onclick = () => form(b.dataset.p)));
    };
    const LINKS = { // step-by-step app password help: 1. turn on 2-step verification, 2. create an app password
      gmail: ["https://myaccount.google.com/signinoptions/twosv", "https://myaccount.google.com/apppasswords"],
      icloud: ["https://account.apple.com/account/manage", "https://account.apple.com/account/manage"],
    };
    const form = (provider) => {
      const other = provider === "other", hint = this.t("hint_" + provider), links = LINKS[provider];
      const steps = links ? `<div class="gtitle" style="margin-top:18px">${this.t("app_pw_title")}</div><div class="explain" style="margin:0 22px 8px">${this.t("app_pw_why")}</div><div class="group">
          ${links.map((u, i) => `<a class="item" href="${u}" target="_blank" rel="noopener" style="text-decoration:none">${svg(i ? IC.compose : IC.flag)}<span class="text"><span class="name">${i + 1}. ${this.t(i ? "app_pw_step2" : "app_pw_step1")}</span>${svg(IC.next, "chev")}</span></a>`).join("")}
          <div class="item">${svg(IC.clip)}<span class="text"><span class="name">3. ${this.t("app_pw_step3")}</span></span></div></div>` : "";
      veil.innerHTML = `<div class="sheet grey">
        <div class="sbar"><button class="btn" data-back>${this.t("cancel")}</button><b>${esc(this.t("p_" + provider))}</b><button class="btn" data-next>${this.t("next")}</button></div>
        <div class="scroll">${steps}<div class="group" style="margin-top:22px">
          <label class="item"><span class="text"><span class="name">${this.t("description")}</span><input type="text" id="n-name" placeholder="${this.t("description_ph")}"></span></label>
          <label class="item"><span class="text"><span class="name">${this.t("email")}</span><input type="email" id="n-email" autocomplete="off" autocapitalize="off" placeholder="name@example.com"></span></label>
          <label class="item"><span class="text"><span class="name">${links ? this.t("app_password") : this.t("password")}</span><input type="password" id="n-pw" autocomplete="new-password" placeholder="${this.t("required")}"></span></label>
        </div>
        ${other ? `<div class="gtitle">${this.t("servers")}</div><div class="group">
          <label class="item"><span class="text"><span class="name">${this.t("imap_server")}</span><input type="text" id="n-imap" autocapitalize="off" placeholder="imap.example.com"></span></label>
          <label class="item"><span class="text"><span class="name">${this.t("imap_port")}</span><input type="number" id="n-imapport" value="993"></span></label>
          <label class="item"><span class="text"><span class="name">${this.t("smtp_server")}</span><input type="text" id="n-smtp" autocapitalize="off" placeholder="smtp.example.com"></span></label>
          <label class="item"><span class="text"><span class="name">${this.t("smtp_port")}</span><input type="number" id="n-smtpport" value="465"></span></label>
        </div>` : ""}
        <div class="explain" id="n-note">${esc(hint)}<br><br>${this.t("password_note")}</div>
        </div></div>`;
      veil.querySelector("[data-back]").onclick = choose;
      veil.querySelector("[data-next]").onclick = async (e) => {
        const btn = e.currentTarget, $ = (s) => veil.querySelector(s), note = $("#n-note");
        const d = { provider, name: $("#n-name").value.trim(), email: $("#n-email").value.trim(), password: $("#n-pw").value };
        if (other) Object.assign(d, { imap_server: $("#n-imap").value.trim(), imap_port: +$("#n-imapport").value || 993,
          smtp_server: $("#n-smtp").value.trim(), smtp_port: +$("#n-smtpport").value || 465 });
        btn.disabled = true; btn.textContent = this.t("checking");
        try {
          await this._call("add_account", d);
          await this._loadSettings();
          this._toast(this.t("account_added")); this._mb = null; back();
        } catch (err) {
          btn.disabled = false; btn.textContent = this.t("next");
          note.innerHTML = `<span class="error">${esc(this._errText(err))}</span><br><br>${esc(hint)}`;
        }
      };
    };
    choose();
  }
}
if (!customElements.get("homemail-app")) customElements.define("homemail-app", HomemailApp);
