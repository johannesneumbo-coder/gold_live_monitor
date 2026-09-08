# ============================================================
# LIVE GOLD / XAUUSD YOUTUBE -> WHATSAPP MONITOR
# YOUTUBE SOURCE ENGINE
# ============================================================

import logging
from typing import Optional, Dict, Any

import yt_dlp

from config import (
    START_VIDEO_URL,
    GOLD_KEYWORDS,
    NON_GOLD_KEYWORDS,
)


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# YT-DLP OPTIONS
# ============================================================

BASE_YDL_OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "noplaylist": True,
    "extract_flat": False,
}


# ============================================================
# TARGET CHANNEL
# ============================================================

_target_channel_id: Optional[str] = None
_target_channel_url: Optional[str] = None


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip().lower()


# ============================================================
# GOLD KEYWORD CHECK
# ============================================================

def contains_gold(text: str) -> bool:

    text = normalize_text(text)

    for keyword in GOLD_KEYWORDS:

        keyword = normalize_text(keyword)

        if keyword and keyword in text:
            return True

    return False


# ============================================================
# NON-GOLD KEYWORD CHECK
# ============================================================

def contains_non_gold(text: str) -> bool:

    text = normalize_text(text)

    for keyword in NON_GOLD_KEYWORDS:

        keyword = normalize_text(keyword)

        if keyword and keyword in text:
            return True

    return False


# ============================================================
# DISCOVER TARGET CHANNEL
# ============================================================

def discover_target_channel() -> bool:

    global _target_channel_id
    global _target_channel_url

    try:

        logger.info(
            "Discovering target YouTube channel..."
        )

        options = dict(BASE_YDL_OPTIONS)

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                START_VIDEO_URL,
                download=False,
            )

        if not info:

            logger.error(
                "Unable to read the starting YouTube video."
            )

            return False

        channel_id = (
            info.get("channel_id")
            or info.get("uploader_id")
        )

        channel_url = (
            info.get("channel_url")
            or info.get("uploader_url")
        )

        uploader = (
            info.get("uploader")
            or info.get("channel")
            or "Unknown"
        )

        if not channel_id and not channel_url:

            logger.error(
                "Unable to identify the target YouTube channel."
            )

            return False

        _target_channel_id = (
            str(channel_id)
            if channel_id
            else None
        )

        if channel_url:

            _target_channel_url = (
                str(channel_url).rstrip("/")
            )

        elif channel_id:

            _target_channel_url = (
                "https://www.youtube.com/channel/"
                + str(channel_id)
            )

        logger.info(
            "Target channel: %s",
            uploader,
        )

        logger.info(
            "Target channel ID: %s",
            _target_channel_id or "Unknown",
        )

        logger.info(
            "Target channel URL: %s",
            _target_channel_url or "Unknown",
        )

        return True

    except Exception as exc:

        logger.exception(
            "Failed to discover target channel: %s",
            exc,
        )

        return False


# ============================================================
# GET TARGET CHANNEL URL
# ============================================================

def get_target_channel_url() -> Optional[str]:

    global _target_channel_url

    if _target_channel_url:
        return _target_channel_url

    if discover_target_channel():
        return _target_channel_url

    return None


# ============================================================
# CHECK TARGET CHANNEL
# ============================================================

def belongs_to_target_channel(
    info: Dict[str, Any]
) -> bool:

    if not info:
        return False

    video_channel_id = (
        info.get("channel_id")
        or info.get("uploader_id")
    )

    if (
        _target_channel_id
        and video_channel_id
    ):

        return (
            str(video_channel_id)
            == str(_target_channel_id)
        )

    video_channel_url = (
        info.get("channel_url")
        or info.get("uploader_url")
    )

    if (
        _target_channel_url
        and video_channel_url
    ):

        return (
            str(video_channel_url).rstrip("/")
            == str(_target_channel_url).rstrip("/")
        )

    return False


# ============================================================
# CHECK CURRENT LIVE STATUS
# ============================================================

def is_currently_live(
    info: Dict[str, Any]
) -> bool:

    if not info:
        return False

    return info.get("is_live") is True


# ============================================================
# CHECK GOLD / XAUUSD STREAM
# ============================================================

def is_gold_stream(
    info: Dict[str, Any]
) -> bool:

    if not info:
        return False

    title = normalize_text(
        info.get("title")
    )

    description = normalize_text(
        info.get("description")
    )

    # --------------------------------------------------------
    # TITLE IS THE PRIMARY FILTER.
    # --------------------------------------------------------

    if contains_gold(title):

        return True

    # --------------------------------------------------------
    # If the title explicitly identifies another market,
    # reject it.
    # --------------------------------------------------------

    if contains_non_gold(title):

        return False

    # --------------------------------------------------------
    # If the title does not identify the market, allow the
    # description to identify Gold/XAUUSD.
    # --------------------------------------------------------

    if contains_gold(description):

        return True

    return False


# ============================================================
# FIND CURRENT LIVE GOLD STREAM
# ============================================================

def find_current_live_gold(
) -> Optional[Dict[str, Any]]:

    channel_url = get_target_channel_url()

    if not channel_url:

        logger.error(
            "Target channel URL is unavailable."
        )

        return None

    live_url = (
        channel_url.rstrip("/")
        + "/live"
    )

    logger.info(
        "Checking target channel for current LIVE Gold stream..."
    )

    try:

        options = dict(BASE_YDL_OPTIONS)

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                live_url,
                download=False,
            )

            if not info:
                return None

            # ------------------------------------------------
            # Sometimes /live returns a playlist-like object.
            # ------------------------------------------------

            entries = info.get("entries")

            if entries:

                for entry in entries:

                    if not entry:
                        continue

                    video_id = entry.get("id")

                    if not video_id:
                        continue

                    video_url = (
                        "https://www.youtube.com/watch?v="
                        + str(video_id)
                    )

                    try:

                        video_info = ydl.extract_info(
                            video_url,
                            download=False,
                        )

                    except Exception:

                        continue

                    if not video_info:
                        continue

                    if not belongs_to_target_channel(
                        video_info
                    ):
                        continue

                    if not is_currently_live(
                        video_info
                    ):
                        continue

                    if not is_gold_stream(
                        video_info
                    ):
                        continue

                    logger.info(
                        "LIVE GOLD STREAM FOUND: %s",
                        video_info.get(
                            "title",
                            "Unknown",
                        ),
                    )

                    return video_info

                return None

            # ------------------------------------------------
            # Direct video result.
            # ------------------------------------------------

            if not belongs_to_target_channel(info):
                return None

            if not is_currently_live(info):
                return None

            if not is_gold_stream(info):
                return None

            logger.info(
                "LIVE GOLD STREAM FOUND: %s",
                info.get(
                    "title",
                    "Unknown",
                ),
            )

            return info

    except Exception as exc:

        logger.warning(
            "YouTube live check failed: %s",
            exc,
        )

        return None


# ============================================================
# GET CURRENT VIDEO ID
# ============================================================

def get_current_video_id(
    live_info: Optional[Dict[str, Any]]
) -> Optional[str]:

    if not live_info:
        return None

    video_id = live_info.get("id")

    if video_id:
        return str(video_id)

    return None


# ============================================================
# GET CURRENT VIDEO TITLE
# ============================================================

def get_current_title(
    live_info: Optional[Dict[str, Any]]
) -> str:

    if not live_info