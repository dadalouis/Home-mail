### Next version (not released yet)

**New**
- **Own login screen** in the web app, in the Home-mail style, with two-step verification. The Home Assistant login page is still one tap away.
- **Notifications screen right after logging in**: one tap links this phone to your user. When a phone no longer gets notifications (for example after Forget, or a new home-screen app), it signs up again by itself.
- **Per device: which accounts notify**, under Settings → Notifications → *Where*. Web apps get recognisable names ("iPhone").
- **Copy button** next to the web app address.
- **How much mail the web app shows**: right after logging in you choose a period (a number of days, weeks, months or years, or all mail); change it later under Settings → *Mail in this app*. The web app then only loads that mail, and its red number only counts unread mail of that period. *Load older mail* at the bottom of a list shows the rest. Nothing is deleted, and the Companion app and the Home Assistant panel keep showing everything.
- **Which folders the web app shows**: Settings → *Folders in this app*. Hidden folders are not shown or counted there (less work for the mail server); they stay on the server and in your other apps.

**Fixed**
- **Web app notifications that stopped arriving on the iPhone.** Home-mail sent an invisible push to take a notification away whenever a message was read, also for messages that never had a notification. iOS stops delivering to a web app that gets such pushes. Web apps now only get visible notifications, sent with high priority.
- **A new web app registration got no notifications** until Home Assistant restarted. Home-mail now reloads the HTML5 integration after a registration, and signs up with a fresh subscription instead of reusing an old (possibly dead) one.
- "Last sent" now says *sent*: Home Assistant handed the notification to Apple or Google; whether it is shown is up to the device.

**Faster**
- All Inboxes loads every account at the same time.
- Only the newest messages of a folder are asked for, not the list of every message in it (big Gmail inboxes).
- Message summaries kept in memory have a limit.

- **No notifications on a Companion device whose name changed.** When a phone was renamed (for example "Anna's iPhone" became "iPhone Aaurence"), Home-mail looked for the old name, did not find it and skipped the phone without a word. It now uses the name the device has in Home Assistant, so the notification arrives. The device also shows up under Settings → Notifications → *Where* again.

**After updating**
- Restart Home Assistant.
