### Next version (not released yet)

**Fixed**
- **No notifications on a Companion device whose name changed.** When a phone was renamed (for example "Laurence's iPhone" became "iPhone Laurence"), Home-mail looked for the old name, did not find it and skipped the phone without a word. It now uses the name the device has in Home Assistant, so the notification arrives. The device also shows up under Settings → Notifications → *Where* again.

**After updating**
- Restart Home Assistant.
