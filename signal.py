# ============================================================
# SIGNAL PROCESSING
# ============================================================

import hashlib


def format_price(value):

    if value is None:
        return "Not detected"

    return f"{value:.2f}"


def make_signature(signal):

    parts = [
        signal.get("direction"),
        str(signal.get("entry")),
        str(signal.get("stop_loss")),
        str(signal.get("tp1")),
        str(signal.get("tp2")),
        str(signal.get("tp3"))
    ]

    raw = "|".join(parts)

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def build_message(signal):

    direction = signal["direction"]

    if direction == "BUY":
        emoji = "🟢"
    else:
        emoji = "🔴"

    message = (
        f"{emoji} XAUUSD {direction}\n\n"
        f"Entry: {format_price(signal.get('entry'))}\n"
        f"SL: {format_price(signal.get('stop_loss'))}\n"
        f"TP1: {format_price(signal.get('tp1'))}\n"
        f"TP2: {format_price(signal.get('tp2'))}\n"
        f"TP3: {format_price(signal.get('tp3'))}\n\n"
        "📺 Live Gold Trading Stream\n"
        "⚠️ Signal detected from livestream"
    )

    return message