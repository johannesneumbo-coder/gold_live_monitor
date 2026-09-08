# ============================================================
# LIVE GOLD / XAUUSD YOUTUBE -> WHATSAPP MONITOR
# MAIN MONITOR
# ============================================================

import logging
import os
import subprocess
import tempfile
import time
from typing import Any, Dict, Optional

import cv2

from config import (
    CONFIRMATIONS_REQUIRED,
    DEBUG_FRAME_DIR,
    FRAME_INTERVAL_SECONDS,
    LATEST_FRAME_FILE,
    LOG_FILE,
    POLL_LIVE_EVERY_SECONDS,
    SAVE_DEBUG_FRAMES,
)

from youtube_source import (
    find_current_live_gold,
    get_current_title,
    get_current_video_id,
    get_stream_url,
    initialize_youtube_source,
    verify_live_stream,
)

from signal import (
    detect_signal,
    format_signal,
    signal_signature,
    signals_match,
)

from database import (
    already_sent,
    save,
)

from whatsapp import (
    send_whatsapp_message,
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            LOG_FILE,
            encoding="utf-8",
        ),
    ],
)

logger = logging.getLogger(__name__)


# ============================================================
# STATE
# ============================================================

last_video_id: Optional[str] = None

confirmed_signal: Optional[Dict[str, Any]] = None
confirmation_count = 0

last_processed_signature: Optional[str] = None

stream_process: Optional[subprocess.Popen] = None


# ============================================================
# RESET SIGNAL STATE
# ============================================================

def reset_signal_confirmation() -> None:
    global confirmed_signal
    global confirmation_count

    confirmed_signal = None
    confirmation_count = 0


# ============================================================
# RESET FOR NEW STREAM
# ============================================================

def reset_for_new_stream(video_id: str) -> None:
    global last_video_id
    global last_processed_signature

    last_video_id = video_id

    last_processed_signature = None

    reset_signal_confirmation()

    logger.info(
        "New LIVE Gold stream detected: %s",
        video_id,
    )


# ============================================================
# SAVE DEBUG FRAME
# ============================================================

def save_debug_frame(frame: Any) -> None:

    if not SAVE_DEBUG_FRAMES:
        return

    try:
        os.makedirs(
            DEBUG_FRAME_DIR,
            exist_ok=True,
        )

        filename = os.path.join(
            DEBUG_FRAME_DIR,
            f"frame_{int(time.time())}.jpg",
        )

        cv2.imwrite(
            filename,
            frame,
        )

    except Exception as exc:
        logger.warning(
            "Could not save debug frame: %s",
            exc,
        )


# ============================================================
# SAVE LATEST FRAME
# ============================================================

def save_latest_frame(frame: Any) -> None:

    try:
        cv2.imwrite(
            LATEST_FRAME_FILE,
            frame,
        )
    except Exception as exc:
        logger.warning(
            "Could not save latest frame: %s",
            exc,
        )


# ============================================================
# START FFMPEG FRAME STREAM
# ============================================================

def start_frame_process(
    stream_url: str,
) -> Optional[subprocess.Popen]:

    if not stream_url:
        return None

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-reconnect",
        "1",
        "-reconnect_streamed",
        "1",
        "-reconnect_delay_max",
        "10",
        "-i",
        stream_url,
        "-vf",
        "fps=1/{}".format(
            max(
                1,
                int(FRAME_INTERVAL_SECONDS),
            )
        ),
        "-f",
        "image2pipe",
        "-vcodec",
        "mjpeg",
        "-q:v",
        "5",
        "pipe:1",
    ]

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )

        logger.info(
            "FFmpeg frame capture started."
        )

        return process

    except FileNotFoundError:
        logger.error(
            "FFmpeg is not installed or not available in PATH."
        )

    except Exception as exc:
        logger.exception(
            "Could not start FFmpeg: %s",
            exc,
        )

    return None


# ============================================================
# READ JPEG FROM PIPE
# ============================================================

def read_jpeg_from_pipe(
    process: subprocess.Popen,
) -> Optional[Any]:

    if process.stdout is None:
        return None

    start_marker = b"\xff\xd8"
    end_marker = b"\xff\xd9"

    buffer = bytearray()

    while True:

        chunk = process.stdout.read(4096)

        if not chunk:
            return None

        buffer.extend(chunk)

        start = buffer.find(start_marker)

        if start == -1:
            if len(buffer) > 1000000:
                buffer.clear()

            continue

        end = buffer.find(
            end_marker,
            start + 2,
        )

        if end == -1:
            continue

        end += 2

        jpeg_data = bytes(
            buffer[start:end]
        )

        del buffer[:end]

        image_array = cv2.imdecode(
            __import__("numpy").frombuffer(
                jpeg_data,
                dtype=__