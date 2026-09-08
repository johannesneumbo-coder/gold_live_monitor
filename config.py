# ============================================================
# GOLD LIVE XAUUSD LIVESTREAM MONITOR
# CONFIGURATION
# ============================================================

# ------------------------------------------------------------
# YOUTUBE
# ------------------------------------------------------------

# Put the exact YouTube channel ID here.
# Example:
# YOUTUBE_CHANNEL_ID = "UCxxxxxxxxxxxxxxxxxxxxxx"

YOUTUBE_CHANNEL_ID = "PUT_CHANNEL_ID_HERE"

# YouTube Data API v3 key
YOUTUBE_API_KEY = "PUT_YOUTUBE_API_KEY_HERE"


# ------------------------------------------------------------
# OPTIONAL DIRECT LIVE URL
# ------------------------------------------------------------
# If you already know the channel's live-video URL, put it here.
#
# Example:
# DIRECT_LIVE_URL = "https://www.youtube.com/watch?v=XXXXXXXXXXX"
#
# Leave blank to automatically search the channel for a live
# broadcast using the YouTube API.

DIRECT_LIVE_URL = ""


# ------------------------------------------------------------
# MONITORING
# ------------------------------------------------------------

# Seconds between OCR screenshots.
CAPTURE_INTERVAL = 2

# A signal must normally be seen this many times before sending.
CONFIRMATIONS_REQUIRED = 2

# OCR confidence threshold.
OCR_CONFIDENCE = 45

# Maximum number of stored duplicate signatures.
MAX_SIGNAL_HISTORY = 5000


# ------------------------------------------------------------
# GOLD PRICE FILTER
# ------------------------------------------------------------

# This monitor is specifically intended for XAUUSD.
#
# Current Gold prices may vary by broker/data feed.
# These limits prevent random numbers from being interpreted
# as Gold prices.

MIN_GOLD_PRICE = 1000.0
MAX_GOLD_PRICE = 10000.0


# ------------------------------------------------------------
# WHATSAPP CLOUD API
# ------------------------------------------------------------

# Meta WhatsApp Business phone-number ID
WHATSAPP_PHONE_NUMBER_ID = "PUT_PHONE_NUMBER_ID_HERE"

# Meta access token
WHATSAPP_ACCESS_TOKEN = "PUT_ACCESS_TOKEN_HERE"

# Recipient WhatsApp number in international format.
# Example Namibia:
#
# 264XXXXXXXXX
#
# Do NOT put the + sign.

WHATSAPP_RECIPIENT = "264XXXXXXXXX"


# ------------------------------------------------------------
# WHATSAPP API VERSION
# ------------------------------------------------------------

WHATSAPP_API_VERSION = "v23.0"


# ------------------------------------------------------------
# FILES
# ------------------------------------------------------------

DATABASE_FILE = "signals.db"
LOG_FILE = "gold_monitor.log"
SCREENSHOT_FILE = "latest_frame.jpg"


# ------------------------------------------------------------
# DEBUG
# ------------------------------------------------------------

# True = save every processed screenshot.
# False = only keep the latest screenshot.

SAVE_SCREENSHOTS = False