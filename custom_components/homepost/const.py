"""Constants for Homepost."""

DOMAIN = "homepost"
VERSION = "0.1.0"

CONF_PROVIDER = "provider"
CONF_IMAP_SERVER = "imap_server"
CONF_IMAP_PORT = "imap_port"
CONF_SMTP_SERVER = "smtp_server"
CONF_SMTP_PORT = "smtp_port"

OPT_NAME = "name"  # description of the account in the app ("Gmail", "Work"), like iOS "Description"
OPT_SENDER = "sender_name"  # your name as recipients see it, like iOS "Name"
OPT_COLOR = "color"
OPT_SIGNATURE = "signature"
OPT_SENT_FOLDER = "sent_folder"
OPT_USERS = "users"
OPT_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 60  # seconds

# provider -> (imap server, imap port, smtp server, smtp port)
PROVIDERS = {
    "gmail": ("imap.gmail.com", 993, "smtp.gmail.com", 465),
    "icloud": ("imap.mail.me.com", 993, "smtp.mail.me.com", 587),
    "outlook": ("outlook.office365.com", 993, "smtp-mail.outlook.com", 587),
    "other": ("", 993, "", 465),
}

COLORS = ["#0a84ff", "#ea4335", "#f5a623", "#34c759", "#af52de", "#ff2d55", "#8e8e93"]

EVENT_NEW_MAIL = "homepost_new_mail"
SIGNAL_UPDATE = "homepost_update"

URL_FILES = "/homepost-files"
PANEL_URL = "homepost"
PANEL_ELEMENT = "homepost-panel"

MAX_SENT_PER_HOUR = 20
