<p align="center"><img src="custom_components/homemail/brand/icon@2x.png" width="128" alt=""><br><img src="docs/wordmark.svg" height="56" alt="Home-mail"></p>

# Home-mail

<p align="center">
  <a href="https://analytics.home-assistant.io/custom_integrations.json"><img src="https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.homemail.total" alt="Active installations"></a>
  <a href="https://github.com/dadalouis/Home-mail/releases"><img src="https://img.shields.io/github/v/release/dadalouis/Home-mail?include_prereleases" alt="Release"></a>
  <a href="https://hacs.xyz"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg" alt="HACS Custom"></a>
  <a href="https://github.com/dadalouis/Home-mail/actions/workflows/validate.yml"><img src="https://github.com/dadalouis/Home-mail/actions/workflows/validate.yml/badge.svg" alt="Validate"></a>
</p>

*Home + E-mail: the **E** of Home is the **E** of E-mail.*

> The install counter comes from Home Assistant's anonymous [analytics](https://analytics.home-assistant.io): it counts installations that have analytics turned on, updated once a day.

**Your mail, fetched by your own Home Assistant.** A clean, iOS-Mail-style mail app that lives inside Home Assistant: as a sidebar panel, as a dashboard card, and as a stand-alone web app you can put on your phone's home screen.

[Nederlands](README.nl.md)

## Why

- **Privacy** – your mail goes from your provider straight to your own Home Assistant. No third-party mail app, no cloud service in between, no tracking pixels (they are filtered out).
- **Battery** – the phone doesn't poll mail servers. Home Assistant does that at home; the phone only shows what's there.
- **Notifications right away** – Home Assistant fires an event for every new message, so you can notify any device, flash a light, or announce it on a speaker.
- **One place** – all your accounts (Gmail, iCloud, Outlook, your own domain) in one inbox, next to the rest of your home.

## Features

- All Inboxes, per-account inboxes and every folder (Drafts, Sent, Junk, Trash, Archive, custom folders) with counters
- Read messages safely: HTML is sanitised and shown in a sandbox without scripts; remote images on/off; tracking pixels removed
- Swipe actions like iOS: archive, delete, read/unread; flag; move back to the inbox
- Write, reply, reply all and forward (with attachments of the original), per-account signature and colour
- Address suggestions from your inbox and sent mail
- Search (server-side, Gmail search syntax works for Gmail)
- A sensor per account with the number of unread messages, and a `homemail_new_mail` event
- Per account you choose which Home Assistant users may use it (default: administrators only)
- English and Dutch

## Installation

### 1. Install with HACS

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dadalouis&repository=Home-mail&category=integration)

1. In Home Assistant open **HACS**, open the ⋮ menu → **Custom repositories**.
2. Add `https://github.com/dadalouis/Home-mail` with type **Integration**.
3. Search for **Home-mail**, click **Download**, then **restart Home Assistant**.

<details><summary>Manual installation</summary>

Copy `custom_components/homemail` into the `custom_components` folder of your Home Assistant configuration and restart.
</details>

### 2. Add a mail account

**Settings → Devices & services → Add integration → Home-mail.** Pick your provider and enter your address and password. Home-mail tests the login (receiving *and* sending) before it saves anything. Add more accounts the same way.

**Gmail and iCloud** no longer accept your normal password in other mail apps. They need a one-time *app password*; Home-mail shows the steps with direct links:

1. Turn on 2-Step Verification ([Google](https://myaccount.google.com/signinoptions/twosv)) – a confirmation on your phone is enough.
2. Create an app password ([Google](https://myaccount.google.com/apppasswords) / [Apple](https://account.apple.com/account/manage)), name it "Home Assistant".
3. Paste it into Home-mail. Spaces are fine.

Most other providers (your own domain, ISP mail) work with your normal password. Outlook/Hotmail often only allow modern sign-in; adding such an account may fail.

### 3. Open the app

- **Sidebar**: a **Home-mail** item appears in the sidebar.
- **Dashboard card**: add a card of type `custom:homemail-card` (best in a view of type *Panel*).
- **On your phone's home screen**: open `https://<your-home-assistant>/homemail-files/app.html` in Safari/Chrome, log in with your Home Assistant account, then *Share → Add to Home Screen*.

### 4. Notifications (optional)

- **Companion app**: import the blueprint
  [![Open your Home Assistant instance and show the blueprint import dialog.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fdadalouis%2FHome-mail%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fhomemail%2Fnew_mail_notification.yaml)
  and pick your phone.
- **Web push to the home-screen app**: set up the Home Assistant [HTML5 push](https://www.home-assistant.io/integrations/html5/) integration; the web app then offers a "Turn on" button and a red badge with the unread count.
- **Your own automations**: trigger on the event `homemail_new_mail`. Data: `account`, `account_name`, `account_email`, `uid`, `from_name`, `from_address`, `subject`, `preview`, `message_id`, `date`, `unread`.

## Multiple users, separate mailboxes

Every person in your household can have their own mailboxes, all on the same Home-mail installation and the same app address.

1. Give each person their own Home Assistant user (Settings → People → Users).
2. Add every mail account as its own Home-mail entry (Settings → Devices & services → Home-mail → **Add entry**).
3. Open an account's options and choose under **Users who may use this account** who may use it. Leave it empty and only administrators can use it.
4. Everyone opens the same app address and logs in with their own Home Assistant account. You only see the mailboxes you were given access to; other mailboxes do not appear at all.

Good to know:
- An account can be shared with several users, and a user can have several accounts.
- Once you pick users for an account, only those users get access. Administrators are not added automatically, so include yourself if you want to use it too.
- Personal settings (default account, blind copy to myself, load images) are stored per user. The signature and colour belong to the account. New messages get a default closing with the name of the logged-in Home Assistant user, until you set your own signature.

## Access from outside your home

Home-mail uses your normal Home Assistant address and login, so it works wherever Home Assistant works:

| How you reach Home Assistant | Reading & writing | Notifications, badge, home-screen app |
|---|---|---|
| Home Assistant Cloud (Nabu Casa) | ✅ | ✅ easiest |
| Your own domain with HTTPS (Cloudflare Tunnel, reverse proxy) | ✅ | ✅ |
| VPN (WireGuard, Tailscale, …) to an `https://` address | ✅ | ✅ |
| Only `http://<ip>:8123` at home | ✅ | ❌ browsers require HTTPS for these |

## How it works

- Each mail account is a config entry. The password is stored only in your Home Assistant (like any other integration) and is never logged.
- Messages are fetched on demand straight from the IMAP server; nothing is written to Home Assistant states or the database except the unread counter.
- The app talks to Home Assistant over the websocket API (`homemail/*` commands). Every command checks whether the logged-in Home Assistant user may use that account.
- Sending uses SMTP with the same login. For servers that don't keep a copy themselves, Home-mail saves one in the Sent folder.
- Every account's inbox is checked every 60 seconds (adjustable in the account options) with a single light-weight `STATUS` command.
- At most 20 messages can be sent per hour, as a safety net.

## About

Home-mail started as a personal project: a Home Assistant user wanted a mail app on the phone that didn't hand mail to another cloud service and didn't drain the battery, and built it together with Claude (Anthropic's AI assistant). It is shared here in the hope it is useful to others.

Feedback and pull requests are welcome via [issues](https://github.com/dadalouis/Home-mail/issues).

## License

MIT
