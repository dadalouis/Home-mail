### What's new
- **Built-in notifications.** Home-mail now notifies you about new mail itself, on your Companion app and on the web app on your home screen. No blueprint or automation needed any more (the blueprint is removed). Tapping a notification opens the message, the icon shows the unread count, and the notification disappears when you read or delete the message.
- **Per user settings** under Settings → Notifications: which accounts notify, all mail or only your VIP senders, senders that never notify, days of the week, quiet hours, message text on/off, sound on/off, which Companion devices, and a test notification button. Other users never see your settings, and only get notifications for accounts they may use.
- The `homemail_new_mail` event is still fired for your own automations.

### Good to know
- Restart Home Assistant after updating.
- If you used the Home-mail blueprint, delete that automation or you will be notified twice.
- Web app users: tap **Turn on** in the app once more, so Home-mail knows which device is yours.
