# ============================================================
# LIVE GOLD / XAUUSD YOUTUBE -> WHATSAPP MONITOR
# SIGNAL DETECTOR
# ============================================================

import hashlib
import logging
import re
from typing import Optional, Dict, Any, List, Tuple

import cv2
import numpy as np
import pytesseract

from pytesseract import Output

from config import (
    OCR_LANG,
    OCR_MIN_CONFIDENCE,
    MIN_PRICE,
    MAX_PRICE,
    REQUIRE_ENTRY_AND_SL,
)


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# PRICE REGEX
# ============================================================

PRICE_PATTERN = re.compile(
    r"(?<!\d)"
    r"(\d{1,5}(?:[.,]\d{1,3})?)"
    r"(?!\d)"
)


# ============================================================
# SIGNAL WORDS
# ============================================================

BUY_PATTERN = re.compile(
    r"\bBUY\b",
    re.IGNORECASE,
)

SELL_PATTERN = re.compile(
    r"\bSELL\b",
    re.IGNORECASE,
)

ENTRY_PATTERN = re.compile(
    r"\b(?:ENTRY|ENTER|OPEN)\b",
    re.IGNORECASE,
)

SL_PATTERN = re.compile(
    r"\b(?:S/?L|STOP\s*LOSS|STOPLOSS|STOP)\b",
    re.IGNORECASE,
)

TP1_PATTERN = re.compile(
    r"\b(?:TP\s*1|TP1|TAKE\s*PROFIT\s*1)\b",
    re.IGNORECASE,
)

TP2_PATTERN = re.compile(
    r"\b(?:TP\s*2|TP2|TAKE\s*PROFIT\s*2)\b",
    re.IGNORECASE,
)

TP3_PATTERN = re.compile(
    r"\b(?:TP\s*3|TP3|TAKE\s*PROFIT\s*3)\b",
    re.IGNORECASE,
)


# ============================================================
# OCR TEXT
# ============================================================

def clean_ocr_text(text: str) -> str:

    if not text:
        return ""

    text = text.replace("\n", " ")
    text = text.replace("\r", " ")

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


# ============================================================
# PRICE CONVERSION
# ============================================================

def parse_price(value: str) -> Optional[float]:

    if not value:
        return None

    value = value.strip()

    value = value.replace(",", ".")

    try:

        price = float(value)

    except ValueError:

        return None

    if price < MIN_PRICE:
        return None

    if price > MAX_PRICE:
        return None

    return round(price, 3)


# ============================================================
# EXTRACT PRICES
# ============================================================

def extract_prices(text: str) -> List[float]:

    prices = []

    if not text:
        return prices

    for match in PRICE_PATTERN.finditer(text):

        price = parse_price(
            match.group(1)
        )

        if price is None:
            continue

        if price not in prices:
            prices.append(price)

    return prices


# ============================================================
# IMAGE PREPARATION
# ============================================================

def prepare_image(
    frame: np.ndarray
) -> np.ndarray:

    if frame is None:
        return frame

    gray = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY,
    )

    gray = cv2.resize(
        gray,
        None,
        fx=2.0,
        fy=2.0,
        interpolation=cv2.INTER_CUBIC,
    )

    gray = cv2.GaussianBlur(
        gray,
        (3, 3),
        0,
    )

    processed = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY
        + cv2.THRESH_OTSU,
    )[1]

    return processed


# ============================================================
# OCR FULL IMAGE
# ============================================================

def run_ocr(
    frame: np.ndarray
) -> Tuple[str, List[Dict[str, Any]]]:

    if frame is None:
        return "", []

    processed = prepare_image(frame)

    try:

        data = pytesseract.image_to_data(
            processed,
            lang=OCR_LANG,
            config="--psm 11",
            output_type=Output.DICT,
        )

    except Exception as exc:

        logger.warning(
            "OCR failed: %s",
            exc,
        )

        return "", []

    words = []

    count = len(
        data.get("text", [])
    )

    for i in range(count):

        text = str(
            data["text"][i]
        ).strip()

        if not text:
            continue

        try:

            confidence = float(
                data["conf"][i]
            )

        except Exception:

            confidence = 0.0

        if confidence < OCR_MIN_CONFIDENCE:
            continue

        x = int(
            data["left"][i]
        )

        y = int(
            data["top"][i]
        )

        width = int(
            data["width"][i]
        )

        height = int(
            data["height"][i]
        )

        words.append(
            {
                "text": text,
                "confidence": confidence,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
            }
        )

    text = " ".join(
        item["text"]
        for item in words
    )

    return clean_ocr_text(text), words


# ============================================================
# FIND LABEL POSITION
# ============================================================

def find_label(
    words: List[Dict[str, Any]],
    pattern: re.Pattern
) -> Optional[Dict[str, Any]]:

    for word in words:

        if pattern.search(
            word["text"]
        ):

            return word

    return None


# ============================================================
# FIND NEAREST PRICE
# ============================================================

def find_nearest_price(
    label: Dict[str, Any],
    words: List[Dict[str, Any]],
    used: Optional[List[int]] = None,
) -> Optional[float]:

    if not label:
        return None

    if used is None:
        used = []

    label_x = (
        label["x"]
        + label["width"] / 2
    )

    label_y = (
        label["y"]
        + label["height"] / 2
    )

    candidates = []

    for index, word in enumerate(words):

        if index in used:
            continue

        prices = extract_prices(
            word["text"]
        )

        if not prices:
            continue

        word_x = (
            word["x"]
            + word["width"] / 2
        )

        word_y = (
            word["y"]
            + word["height"] / 2
        )

        horizontal_distance = abs(
            word_x - label_x
        )

        vertical_distance = abs(
            word_y - label_y
        )

        # Prefer numbers beside the label.
        score = (
            horizontal_distance
            + vertical_distance * 1.5
        )

        candidates.append(
            (
                score,
                index,
                prices[0],
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item[0]
    )

    return candidates[0][2]


# ============================================================
# FIND PRICE AFTER LABEL IN OCR TEXT
# ============================================================

def find_price_after_label(
    text: str,
    patterns: List[re.Pattern],
) -> Optional[float]:

    if not text:
        return None

    for pattern in patterns:

        match = pattern.search(text)

        if not match:
            continue

        remaining = text[
            match.end():
        ]

        prices = extract_prices(
            remaining[:80]
        )

        if prices:
            return prices[0]

    return None


# ============================================================
# FIND DIRECTION
# ============================================================

def detect_direction(
    text: str
) -> Optional[str]:

    if not text:
        return None

    buy_matches = list(
        BUY_PATTERN.finditer(text)
    )

    sell_matches = list(
        SELL_PATTERN.finditer(text)
    )

    if not buy_matches and not sell_matches:
        return None

    if buy_matches and not sell_matches:
        return "BUY"

    if sell_matches and not buy_matches:
        return "SELL"

    # If both appear, choose the first occurrence.
    if buy_matches[0].start() < sell_matches[0].start():
        return "BUY"

    return "SELL"


# ============================================================
# GET SIGNAL VALUES
# ============================================================

def extract_signal_values(
    text: str,
    words: List[Dict[str, Any]],
) -> Dict[str, Optional[float]]:

    entry = None
    stop_loss = None
    tp1 = None
    tp2 = None
    tp3 = None

    used = []

    # --------------------------------------------------------
    # ENTRY
    # --------------------------------------------------------

    entry_label = find_label(
        words,
        ENTRY_PATTERN,
    )

    if entry_label:

        entry = find_nearest_price(
            entry_label,
            words,
            used,
        )

    if entry is None:

        entry = find_price_after_label(
            text,
            [
                ENTRY_PATTERN,
            ],
        )

    # --------------------------------------------------------
    # STOP LOSS
    # --------------------------------------------------------

    sl_label = find_label(
        words,
        SL_PATTERN,
    )

    if sl_label:

        stop_loss = find_nearest_price(
            sl_label,
            words,
            used,
        )

    if stop_loss is None:

        stop_loss = find_price_after_label(
            text,
            [
                SL_PATTERN,
            ],
        )

    # --------------------------------------------------------
    # TP1
    # --------------------------------------------------------

    tp1_label = find_label(
        words,
        TP1_PATTERN,
    )

    if tp1_label:

        tp1 = find_nearest_price(
            tp1_label,
            words,
            used,
        )

    if tp1 is None:

        tp1 = find_price_after_label(
            text,
            [
                TP1_PATTERN,
            ],
        )

    # --------------------------------------------------------
    # TP2
    # --------------------------------------------------------

    tp2_label = find_label(
        words,
        TP2_PATTERN,
    )

    if tp2_label:

        tp2 = find_nearest_price(
            tp2_label,
            words,
            used,
        )

    if tp2 is None:

        tp2 = find_price_after_label(
            text,
            [
                TP2_PATTERN,
            ],
        )

    # --------------------------------------------------------
    # TP3
    # --------------------------------------------------------

    tp3_label = find_label(
        words,
        TP3_PATTERN,
    )

    if tp3_label:

        tp3 = find_nearest_price(
            tp3_label,
            words,
            used,
        )

    if tp3 is None:

        tp3 = find_price_after_label(
            text,
            [
                TP3_PATTERN,
            ],
        )

    return {
        "entry": entry,
        "stop_loss": stop_loss,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
    }


# ============================================================
# BASIC SIGNAL VALIDATION
# ============================================================

def validate_signal(
    signal: Dict[str, Any]
) -> bool:

    if not signal:
        return False

    direction = signal.get(
        "direction"
    )

    if direction not in (
        "BUY",
        "SELL",
    ):
        return False

    entry = signal.get("entry")
    stop_loss = signal.get("stop_loss")

    if REQUIRE_ENTRY_AND_SL:

        if entry is None:
            return False

        if stop_loss is None:
            return False

    # If Entry exists, it must be a Gold price.
    if entry is not None:

        if not (
            MIN_PRICE
            <= entry
            <= MAX_PRICE
        ):
            return False

    # If SL exists, it must be a Gold price.
    if stop_loss is not None:

        if not (
            MIN_PRICE
            <= stop_loss
            <= MAX_PRICE
        ):
            return False

    # --------------------------------------------------------
    # Direction consistency.
    # --------------------------------------------------------

    if entry is not None and stop_loss is not None:

        if direction == "BUY":

            if stop_loss >= entry:
                return False

        if direction == "SELL":

            if stop_loss <= entry:
                return False

    # --------------------------------------------------------
    # TP direction consistency.
    # --------------------------------------------------------

    if entry is not None:

        targets = [
            signal.get("tp1"),
            signal.get("tp2"),
            signal.get("tp3"),
        ]

        targets = [
            value
            for value in targets
            if value is not None
        ]

        if direction == "BUY":

            for target in targets:

                if target <= entry:
                    return False

        if direction == "SELL":

            for target in targets:

                if target >= entry:
                    return False

    return True


# ============================================================
# DETECT SIGNAL FROM FRAME
# ============================================================

def detect_signal(
    frame: np.ndarray
) -> Optional[Dict[str, Any]]:

    if frame is None:
        return None

    text, words = run_ocr(frame)

    if not text:
        return None

    direction = detect_direction(
        text
    )

    if direction is None:
        return None

    values = extract_signal_values(
        text,
        words,
    )

    signal = {
        "direction": direction,
        "entry": values["entry"],
        "stop_loss": values["stop_loss"],
        "tp1": values["tp1"],
        "tp2": values["tp2"],
        "tp3": values["tp3"],
        "ocr_text": text,
    }

    if not validate_signal(signal):
        return None

    logger.info(
        "Potential %s signal detected: "
        "Entry=%s SL=%s TP1=%s TP2=%s TP3=%s",
        direction,
        signal["entry"],
        signal["stop_loss"],
        signal["tp1"],
        signal["tp2"],
        signal["tp3"],
    )

    return signal


# ============================================================
# PRICE TOLERANCE
# ============================================================

def prices_close(
    a: Optional[float],
    b: Optional[float],
    tolerance: float = 0.10,
) -> bool:

    if a is None or b is None:
        return a is None and b is None

    return abs(a - b) <= tolerance


# ============================================================
# SIGNAL MATCHING
# ============================================================

def signals_match(
    first: Optional[Dict[str, Any]],
    second: Optional[Dict[str, Any]],
    tolerance: float = 0.10,
) -> bool:

    if not first or not second:
        return False

    if first.get("direction") != second.get(
        "direction"
    ):
        return False

    fields = (
        "entry",
        "stop_loss",
        "tp1",
        "tp2",
        "tp3",
    )

    for field in fields:

        if not prices_close(
            first.get(field),
            second.get(field),
            tolerance,
        ):
            return False

    return True


# ============================================================
# SIGNAL SIGNATURE
# ============================================================

def signal_signature(
    signal: Dict[str, Any],
    video_id: str,
) -> str:

    def normalize_price(
        value: Optional[float]
    ) -> str:

        if value is None:
            return ""

        return f"{float(value):.2f}"

    raw = "|".join(
        [
            str(video_id or ""),
            str(
                signal.get("direction")
                or ""
            ),
            normalize_price(
                signal.get("entry")
            ),
            normalize_price(
                signal.get("stop_loss")
            ),
            normalize_price(
                signal.get("tp1")
            ),
            normalize_price(
                signal.get("tp2")
            ),
            normalize_price(
                signal.get("tp3")
            ),
        ]
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


# ============================================================
# FORMAT SIGNAL FOR LOGGING / WHATSAPP
# ============================================================

def format_signal(
    signal: Dict[str, Any]
) -> str:

    direction = signal.get(
        "direction",
        "UNKNOWN",
    )

    entry = signal.get("entry")
    stop_loss = signal.get("stop_loss")
    tp1 = signal.get("tp1")
    tp2 = signal.get("tp2")
    tp3 = signal.get("tp3")

    def fmt(
        value: Optional[float]
    ) -> str:

        if value is None:
            return "N/A"

        return f"{value:.2f}"

    return (
        f"XAUUSD {direction}\n"
        f"Entry: {fmt(entry)}\n"
        f"SL: {fmt(stop_loss)}\n"
        f"TP1: {fmt(tp1)}\n"
        f"TP2: {fmt(tp2)}\n"
        f"TP3: {fmt(tp3)}"
    )