### Home-mail 0.2.3

**New**
- **Buttons in the notification.** Mark as read, Archive, Delete and Reply right from a Companion app notification. Reply opens a text field and sends your answer with your signature, quoting the original. On Android: Read, Archive and Reply (Android shows at most three buttons). Turn them off under Settings → Notifications → *Buttons in the notification*.
- **Change an account without removing it.** In Home Assistant: Settings → Devices & services → Home-mail → ⋮ → *Reconfigure* to change the servers, ports or the password. All settings stay.
- **Repair notices** in Settings → Repairs when every administrator can read an account (nobody chosen), and when *Instant new mail* keeps failing for an account.
- **Diagnostics download** for when something goes wrong (passwords and addresses are left out).
- **Web app on the iPhone signs up for notifications again by itself** when iOS dropped the subscription after a while, as long as you allowed notifications before.

### Also in this version: everything from 0.2.2

**New**
- **New mail at once (IMAP IDLE).** Home-mail keeps one connection open per account and the mail server tells it right away when something changes: new mail, or mail read or deleted in another app. The regular check then runs only every 15 minutes as a safety net, which also means far fewer logins at Gmail and other providers. On by default; turn it off per account in the account options (*Instant new mail*). Needs Home Assistant on Python 3.14 (2026.x) and a mail server with IDLE; otherwise Home-mail keeps checking as before. The account screen in the app shows which one is active.
- **Tap a notification to open that message** in the Companion app (it used to open only the inbox).
- **Where do my notifications go?** Settings → Notifications lists every Companion app logged in with your user and every web app you turned on, each with when the last notification went through, or why it failed.
- **Forget old web apps** you no longer use, right there.
- **The red number on the app icon goes down** again when you read mail, in Home-mail or another app (iPhone, iPad, Mac). It now counts all your accounts together.
- **Save button for notification settings.** Changes stay on screen until you tap Save; going back with unsaved changes asks first. *Send test notification* uses what is on screen, so you can try before saving.
- **Who may use an account**, right in the app (administrators): pick the users in the account screen. An account you add in the app is yours alone until you share it.

**Changed**
- An account with nobody chosen can be read by **every administrator**, who also get its notifications. The app now warns about this; choose the users in the account screen to keep your mail to yourself.

**Fixed**
- An offline device (for example a wall tablet without local push) no longer fills the Home Assistant log with errors or holds up your other devices, and notification text no longer shows links.

**Under the hood**
- Automated tests (notification filters, quiet hours, attachments, IMAP IDLE against a test server) run on every change.

**After updating**
- Restart Home Assistant.
- Accounts with nobody chosen show a warning in the app and under Settings → Repairs: open the account and pick who may use it.
