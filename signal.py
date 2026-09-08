# ============================================================
# LIVE GOLD / XAUUSD YOUTUBE -> WHATSAPP MONITOR
# SIGNAL DETECTOR
# ============================================================

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import pytesseract

from config import (
    MAX_PRICE,
    MIN_PRICE,
    OCR_LANG,
    OCR_MIN_CONFIDENCE,
    REQUIRE_ENTRY_AND_SL,
)

logger = logging.getLogger(__name__)


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def clean_ocr_text(text: Any) -> str:
    if text is None:
        return ""

    text = str(text)

    replacements = {
        "\n": " ",
        "\r": " ",
        "\t": " ",
        "|": "I",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_label(text: Any) -> str:
    text = clean_ocr_text(text).upper()

    replacements = {
        "8UY": "BUY",
        "B U Y": "BUY",
        "5ELL": "SELL",
        "S E L L": "SELL",
        "ENTRV": "ENTRY",
        "ENTRV:": "ENTRY",
        "ENTR": "ENTRY",
        "ST0P": "STOP",
        "ST0PLOSS": "STOP LOSS",
        "SL.": "SL",
        "TPI": "TP1",
        "TP I": "TP1",
        "TP2.": "TP2",
        "TP3.": "TP3",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


# ============================================================
# PRICE PARSING
# ============================================================

def parse_price(value: Any) -> Optional[float]:
    if value is None:
        return None

    text = clean_ocr_text(value)

    if not text:
        return None

    text = text.replace(",", "")

    # Common OCR substitutions.
    text = text.replace("O", "0")
    text = text.replace("o", "0")

    matches = re.findall(r"\d+(?:\.\d+)?", text)

    if not matches:
        return None

    for item in matches:
        try:
            price = float(item)
        except ValueError:
            continue

        if MIN_PRICE <= price <= MAX_PRICE:
            return price

    return None


def extract_prices(text: Any) -> List[float]:
    if text is None:
        return []

    text = clean_ocr_text(text).replace(",", "")

    results: List[float] = []

    for match in re.findall(r"\d+(?:\.\d+)?", text):
        try:
            value = float(match)
        except ValueError:
            continue

        if MIN_PRICE <= value <= MAX_PRICE:
            results.append(value)

    return results


# ============================================================
# IMAGE PREPARATION
# ============================================================

def prepare_image(image: Any) -> Optional[np.ndarray]:
    if image is None:
        return None

    if isinstance(image, str):
        image = cv2.imread(image)

    if image is None:
        return None

    if not isinstance(image, np.ndarray):
        return None

    if len(image.shape) == 2:
        gray = image
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Upscale for OCR.
    height, width = gray.shape[:2]

    if width < 1600:
        scale = 2.0
    else:
        scale = 1.5

    gray = cv2.resize(
        gray,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_CUBIC,
    )

    # Improve contrast.
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    return gray


# ============================================================
# OCR
# ============================================================

def run_ocr(image: Any) -> Dict[str, Any]:
    prepared = prepare_image(image)

    if prepared is None:
        return {
            "text": "",
            "data": [],
        }

    try:
        data = pytesseract.image_to_data(
            prepared,
            lang=OCR_LANG,
            config="--psm 11",
            output_type=pytesseract.Output.DICT,
        )
    except Exception as exc:
        logger.warning("OCR failed: %s", exc)

        return {
            "text": "",
            "data": [],
        }

    words: List[Dict[str, Any]] = []

    count = len(data.get("text", []))

    for i in range(count):
        raw_text = data["text"][i]

        if raw_text is None:
            continue

        text = clean_ocr_text(raw_text)

        if not text:
            continue

        try:
            confidence = float(data["conf"][i])
        except Exception:
            confidence = 0.0

        if confidence < OCR_MIN_CONFIDENCE:
            continue

        try:
            left = int(data["left"][i])
            top = int(data["top"][i])
            width = int(data["width"][i])
            height = int(data["height"][i])
        except Exception:
            continue

        words.append(
            {
                "text": text,
                "normalized": normalize_label(text),
                "confidence": confidence,
                "left": left,
                "top": top,
                "width": width,
                "height": height,
                "center_x": left + width / 2,
                "center_y": top + height / 2,
            }
        )

    full_text = " ".join(item["text"] for item in words)

    return {
        "text": full_text,
        "data": words,
    }


# ============================================================
# OCR LABEL SEARCH
# ============================================================

def find_label(
    ocr_data: List[Dict[str, Any]],
    labels: Tuple[str, ...],
) -> List[Dict[str, Any]]:

    wanted = {normalize_label(label) for label in labels}

    found: List[Dict[str, Any]] = []

    for item in ocr_data:
        normalized = item.get("normalized", "")

        if normalized in wanted:
            found.append(item)

    return found


# ============================================================
# PRICE NEAR LABEL
# ============================================================

def find_nearest_price(
    label: Dict[str, Any],
    ocr_data: List[Dict[str, Any]],
    max_distance: float = 500.0,
) -> Optional[float]:

    label_x = float(label.get("center_x", 0))
    label_y = float(label.get("center_y", 0))

    candidates = []

    for item in ocr_data:
        if item is label:
            continue

        text = item.get("text", "")

        price = parse_price(text)

        if price is None:
            continue

        x = float(item.get("center_x", 0))
        y = float(item.get("center_y", 0))

        dx = abs(x - label_x)
        dy = abs(y - label_y)

        distance = (dx * dx + dy * dy) ** 0.5

        if distance > max_distance:
            continue

        # Prefer numbers horizontally aligned with the label.
        alignment_penalty = dy * 1.5

        score = distance + alignment_penalty

        candidates.append(
            (
                score,
                price,
            )
        )

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])

    return candidates[0][1]


def find_price_after_label(
    label: Dict[str, Any],
    ocr_data: List[Dict[str, Any]],
    max_x_distance: float = 700.0,
    max_y_distance: float = 120.0,
) -> Optional[float]:

    label_x = float(label.get("center_x", 0))
    label_y = float(label.get("center_y", 0))

    candidates = []

    for item in ocr_data:
        if item is label:
            continue

        price = parse_price(item.get("text", ""))

        if price is None:
            continue

        x = float(item.get("center_x", 0))
        y = float(item.get("center_y", 0))

        dx = x - label_x
        dy = abs(y - label_y)

        if dx < 0:
            continue

        if dx > max_x_distance:
            continue

        if dy > max_y_distance:
            continue

        candidates.append(
            (
                dx + dy * 2,
                price,
            )
        )

    if not candidates:
        return