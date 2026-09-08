# ============================================================
# XAUUSD LIVESTREAM OCR SIGNAL DETECTOR
# ============================================================

import re
import cv2
import pytesseract

from config import (
    MIN_GOLD_PRICE,
    MAX_GOLD_PRICE,
    OCR_CONFIDENCE
)


class SignalDetector:

    def __init__(self):
        pass

    def preprocess(self, image):

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        # Increase contrast
        gray = cv2.equalizeHist(gray)

        # Upscale OCR image
        gray = cv2.resize(
            gray,
            None,
            fx=2,
            fy=2,
            interpolation=cv2.INTER_CUBIC
        )

        # Light threshold
        _, threshold = cv2.threshold(
            gray,
            0,
            255,
            cv2.THRESH_BINARY +
            cv2.THRESH_OTSU
        )

        return threshold

    def read_text(self, image):

        processed = self.preprocess(image)

        config = (
            "--oem 3 "
            "--psm 11"
        )

        data = pytesseract.image_to_data(
            processed,
            config=config,
            output_type=pytesseract.Output.DICT
        )

        words = []

        for i in range(len(data["text"])):

            text = data["text"][i].strip()

            if not text:
                continue

            try:
                confidence = float(
                    data["conf"][i]
                )
            except:
                confidence = 0

            if confidence >= OCR_CONFIDENCE:

                words.append(text)

        return " ".join(words)

    def clean_number(self, value):

        if not value:
            return None

        value = value.replace(",", "")
        value = value.replace("O", "0")
        value = value.replace("o", "0")
        value = value.replace("I", "1")
        value = value.replace("l", "1")

        match = re.search(
            r"\d{3,5}(?:\.\d+)?",
            value
        )

        if not match:
            return None

        try:

            number = float(
                match.group(0)
            )

        except:
            return None

        if (
            number < MIN_GOLD_PRICE
            or number > MAX_GOLD_PRICE
        ):
            return None

        return number

    def find_price_after_label(
        self,
        text,
        labels
    ):

        for label in labels:

            pattern = (
                r"\b"
                + label
                + r"\b"
                r"[^0-9]{0,20}"
                r"(\d{3,5}(?:[.,]\d+)?)"
            )

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                return self.clean_number(
                    match.group(1)
                )

        return None

    def detect_direction(self, text):

        buy = re.search(
            r"\bBUY\b",
            text,
            re.IGNORECASE
        )

        sell = re.search(
            r"\bSELL\b",
            text,
            re.IGNORECASE
        )

        if buy and not sell:
            return "BUY"

        if sell and not buy:
            return "SELL"

        # If both appear, we don't guess.
        return None

    def detect(self, image):

        text = self.read_text(image)

        if not text:
            return None

        direction = self.detect_direction(text)

        if not direction:
            return None

        entry = self.find_price_after_label(
            text,
            [
                "ENTRY",
                "ENTER",
                "OPEN"
            ]
        )

        stop_loss = self.find_price_after_label(
            text,
            [
                "SL",
                "STOP",
                "STOPLOSS",
                "STOP-LOSS"
            ]
        )

        tp1 = self.find_price_after_label(
            text,
            [
                "TP1",
                "TP",
                "TARGET1",
                "TARGET"
            ]
        )

        tp2 = self.find_price_after_label(
            text,
            [
                "TP2",
                "TARGET2"
            ]
        )

        tp3 = self.find_price_after_label(
            text,
            [
                "TP3",
                "TARGET3"
            ]
        )

        # ----------------------------------------------------
        # Minimum safety requirement
        # ----------------------------------------------------

        # Direction alone is NOT enough.
        #
        # We require at least an entry or SL/TP information.

        if entry is None and stop_loss is None:
            return None

        return {
            "direction": direction,
            "entry": entry,
            "stop_loss": stop_loss,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3,
            "raw_text": text
        }