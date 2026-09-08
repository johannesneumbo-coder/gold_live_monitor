# ============================================================
# GOLD XAUUSD LIVESTREAM → WHATSAPP MONITOR
# ============================================================

import os
import time
import cv2
import subprocess
import threading
from datetime import datetime

from config import (
    CAPTURE_INTERVAL,
    CONFIRMATIONS_REQUIRED,
    SCREENSHOT_FILE,
    SAVE_SCREENSHOTS
)

from youtube import YouTubeMonitor
from ocr_detector import SignalDetector
from database import SignalDatabase
from whatsapp import WhatsApp
from signal import (
    make_signature,
    build_message
)


class GoldMonitor:

    def __init__(self):

        self.youtube = YouTubeMonitor()
        self.detector = SignalDetector()
        self.database = SignalDatabase()
        self.whatsapp = WhatsApp()

        self.confirmation_cache = {}

        self.running = True

        self.ffmpeg_process = None

        self.current_video_id = None

    # --------------------------------------------------------
    # LOG
    # --------------------------------------------------------

    def log(self, message):

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        print(
            f"[{timestamp}] {message}"
        )

    # --------------------------------------------------------
    # CONFIRMATION
    # --------------------------------------------------------

    def confirm_signal(self, signal):

        signature = make_signature(
            signal
        )

        if signature in self.confirmation_cache:

            self.confirmation_cache[
                signature
            ] += 1

        else:

            self.confirmation_cache[
                signature
            ] = 1

        count = self.confirmation_cache[
            signature
        ]

        self.log(
            f"Signal confirmation "
            f"{count}/{CONFIRMATIONS_REQUIRED}"
        )

        if count < CONFIRMATIONS_REQUIRED:
            return False

        return True

    # --------------------------------------------------------
    # PROCESS SIGNAL
    # --------------------------------------------------------

    def process_signal(
        self,
        signal,
        video_id
    ):

        signature = make_signature(
            signal
        )

        # ----------------------------------------------------
        # DUPLICATE CHECK
        # ----------------------------------------------------

        if self.database.exists(
            signature
        ):

            self.log(
                "Duplicate signal ignored."
            )

            return

        # ----------------------------------------------------
        # CONFIRMATION CHECK
        # ----------------------------------------------------

        if not self.confirm_signal(
            signal
        ):

            return

        # ----------------------------------------------------
        # BUILD MESSAGE
        # ----------------------------------------------------

        message = build_message(
            signal
        )

        self.log(
            "NEW SIGNAL:"
        )

        self.log(
            message
        )

        # ----------------------------------------------------
        # SEND WHATSAPP
        # ----------------------------------------------------

        sent = self.whatsapp.send(
            message
        )

        # ----------------------------------------------------
        # SAVE SIGNAL
        # ----------------------------------------------------

        self.database.save_signal(
            signature=signature,
            direction=signal.get(
                "direction"
            ),
            entry=signal.get(
                "entry"
            ),
            stop_loss=signal.get(
                "stop_loss"
            ),
            tp1=signal.get(
                "tp1"
            ),
            tp2=signal.get(
                "tp2"
            ),
            tp3=signal.get(
                "tp3"
            ),
            video_id=video_id,
            sent=sent
        )

        if sent:

            self.log(
                "WhatsApp notification sent."
            )

        else:

            self.log(
                "WhatsApp notification failed."
            )

    # --------------------------------------------------------
    # CAPTURE STREAM
    # --------------------------------------------------------

    def capture_stream(
        self,
        stream_url,
        video_id
    ):

        command = [
            "ffmpeg",

            "-hide_banner",

            "-loglevel",
            "error",

            "-i",
            stream_url,

            "-vf",
            "fps=0.5",

            "-q:v",
            "3",

            "-f",
            "image2pipe",

            "-vcodec",
            "mjpeg",

            "-"
        ]

        try:

            self.ffmpeg_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8
            )

        except Exception as e:

            self.log(
                f"FFmpeg start error: {e}"
            )

            return

        buffer = b""

        while self.running:

            chunk = (
                self.ffmpeg_process.stdout.read(
                    4096
                )
            )

            if not chunk:
                break

            buffer += chunk

            start = buffer.find(
                b"\xff\xd8"
            )

            end = buffer.find(
                b"\xff\xd9"
            )

            if (
                start != -1
                and end != -1
                and end > start
            ):

                jpg = buffer[
                    start:end + 2
                ]

                buffer = buffer[
                    end + 2:
                ]

                self.process_frame(
                    jpg,
                    video_id
                )

        self.stop_ffmpeg()

    # --------------------------------------------------------
    # FRAME
    # --------------------------------------------------------

    def process_frame(
        self,
        jpg,
        video_id
    ):

        filename = SCREENSHOT_FILE

        try:

            with open(
                filename,
                "wb"
            ) as f:

                f.write(jpg)

            image = cv2.imdecode(
                __import__(
                    "numpy"
                ).frombuffer(
                    jpg,
                    dtype="uint8"
                ),
                cv2.IMREAD_COLOR
            )

            if image is None:
                return

            if SAVE_SCREENSHOTS:

                filename = (
                    "frames/"
                    + datetime.now().strftime(
                        "%Y%m%d_%H%M%S_%f"
                    )
                    + ".jpg"
                )

                os.makedirs(
                    "frames",
                    exist_ok=True
                )

                cv2.imwrite(
                    filename,
                    image
                )

            signal = self.detector.detect(
                image
            )

            if signal:

                self.log(
                    "Possible signal detected."
                )

                self.process_signal(
                    signal,
                    video_id
                )

        except Exception as e:

            self.log(
                f"Frame processing error: {e}"
            )

    # --------------------------------------------------------
    # STOP FFMPEG
    # --------------------------------------------------------

    def stop_ffmpeg(self):

        if self.ffmpeg_process:

            try:

                self.ffmpeg_process.kill()

            except:
                pass

            self.ffmpeg_process = None

    # --------------------------------------------------------
    # MAIN LOOP
    # --------------------------------------------------------

    def run(self):

        self.log(
            "================================"
        )

        self.log(
            "XAUUSD LIVE MONITOR STARTED"
        )

        self.log(
            "================================"
        )

        while self.running:

            try:

                video_id = (
                    self.youtube.find_live_video()
                )

                if not video_id:

                    self.log(
                        "No live XAUUSD stream found."
                    )

                    time.sleep(30)

                    continue

                if video_id != self.current_video_id:

                    self.log(
                        f"Live video detected: "
                        f"{video_id}"
                    )

                    self.current_video_id = (
                        video_id
                    )

                    # New livestream = new
                    # temporary confirmation cache.
                    self.confirmation_cache = {}

                stream_url = (
                    self.youtube.get_stream_url(
                        video_id
                    )
                )

                if not stream_url:

                    self.log(
                        "Unable to obtain stream URL."
                    )

                    time.sleep(20)

                    continue

                self.log(
                    "Starting livestream capture..."
                )

                self.capture_stream(
                    stream_url,
                    video_id
                )

                self.log(
                    "Livestream capture stopped."
                )

                time.sleep(5)

            except KeyboardInterrupt:

                self.running = False

            except Exception as e:

                self.log(
                    f"Main loop error: {e}"
                )

                time.sleep(10)

        self.stop_ffmpeg()

        self.log(
            "Monitor stopped."
        )


if __name__ == "__main__":

    monitor = GoldMonitor()

    monitor.run()