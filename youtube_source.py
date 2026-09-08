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
    "extract_flat": False,
    "noplaylist": True,
}


# ============================================================
# TARGET CHANNEL INFORMATION
# ============================================================

_target_channel_id: Optional[str] = None
_target_channel_url: Optional[str] = None


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(value: Any) -> str:
    """
    Convert any value to lowercase searchable text.
    """

    if value is None:
        return ""

    return str(value).strip().lower()


# ============================================================
# GOLD DETECTION
# ============================================================

def contains_gold(text: str) -> bool:
    """
    Returns True when the supplied text contains a Gold/XAUUSD
    reference.
    """

    text = normalize_text(text)

    for keyword in GOLD_KEYWORDS:
        if normalize_text(keyword) in text:
            return True

    return False


# ============================================================
# NON-GOLD DETECTION
# ============================================================

def contains_non_gold(text: str) -> bool:
    """
    Returns True when the supplied text clearly identifies
    another instrument that should not be monitored.
    """

    text = normalize_text(text)

    for keyword in NON_GOLD_KEYWORDS:
        if normalize_text(keyword) in text:
            return True

    return False


# ============================================================
# GET CHANNEL FROM START VIDEO
# ============================================================

def discover_target_channel() -> bool:
    """
    Uses the supplied starting YouTube video to identify the
    exact channel.

    After this succeeds, the monitor follows ONLY that channel.
    """

    global _target_channel_id
    global _target_channel_url

    try:

        logger.info("Discovering target YouTube channel...")

        options = dict(BASE_YDL_OPTIONS)

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                START_VIDEO_URL,
                download=False,
            )

        if not info:
            logger.error("Could not read starting YouTube video.")
            return False

        channel_id = (
            info.get("channel_id")
            or info.get("uploader_id")
        )

        channel_url = (
            info.get("channel_url")
            or info.get("uploader_url")
        )

        uploader = info.get("uploader") or info.get("channel")

        if not channel_id and not channel_url:
            logger.error(
                "Could not identify the YouTube channel."
            )
            return False

        _target_channel_id = channel_id

        if channel_url:
            _target_channel_url = channel_url.rstrip("/")
        elif channel_id:
            _target_channel_url = (
                f"https://www.youtube.com/channel/{channel_id}"
            )

        logger.info(
            "Target channel discovered: %s",
            uploader or "Unknown",
        )

        logger.info(
            "Channel ID: %s",
            _target_channel_id or "Unknown",
        )

        logger.info(
            "Channel URL: %s",
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
# GET TARGET CHANNEL
# ============================================================

def get_target_channel_url() -> Optional[str]:
    """
    Returns the exact channel URL discovered from the starting
    video.
    """

    global _target_channel_url

    if _target_channel_url:
        return _target_channel_url

    if discover_target_channel():
        return _target_channel_url

    return None


# ============================================================
# CHECK WHETHER VIDEO BELONGS TO TARGET CHANNEL
# ============================================================

def belongs_to_target_channel(
    info: Dict[str, Any]
) -> bool:
    """
    Ensures the discovered live video belongs to the exact
    channel we originally identified.
    """

    if not info:
        return False

    if _target_channel_id:

        video_channel_id = (
            info.get("channel_id")
            or info.get("uploader_id")
        )

        if video_channel_id:

            return (
                str(video_channel_id)
                == str(_target_channel_id)
            )

    if _target_channel_url:

        video_channel_url = (
            info.get("channel_url")
            or info.get("uploader_url")
        )

        if video_channel_url:

            return (
                video_channel_url.rstrip("/")
                == _target_channel_url.rstrip("/")
            )

    return False


# ============================================================
# CHECK WHETHER STREAM IS ACTUALLY LIVE
# ============================================================

def is_currently_live(
    info: Dict[str, Any]
) -> bool:
    """
    Only a currently active LIVE broadcast is accepted.

    Scheduled/upcoming videos and recorded videos are rejected.
    """

    if not info:
        return False

    is_live = info.get("is_live")

    if is_live is True:
        return True

    return False


# ============================================================
# GOLD STREAM FILTER
# ============================================================

def is_gold_stream(
    info: Dict[str, Any]
) -> bool:
    """
    Determines whether the current live broadcast is a
    Gold/XAUUSD broadcast.

    The title gets priority because descriptions may contain
    generic information about many markets.
    """

    if not info:
        return False

    title = normalize_text(
        info.get("title")
    )

    description = normalize_text(
        info.get("description")
    )

    uploader = normalize_text(
        info.get("uploader")
        or info.get("channel")
    )

    # --------------------------------------------------------
    # First inspect the title.
    # --------------------------------------------------------

    if contains_gold(title):

        # If the title explicitly says Gold/XAUUSD,
        # accept the stream.
        return True

    # --------------------------------------------------------
    # If title clearly identifies another market and does not
    # identify Gold, reject it.
    # --------------------------------------------------------

    if contains_non_gold(title):

        return False

    # --------------------------------------------------------
    # If the title does not identify the instrument, inspect
    # description.
    # --------------------------------------------------------

    if contains_gold(description):

        return True

    # --------------------------------------------------------
    # Otherwise reject.
    # --------------------------------------------------------

    return False


# ============================================================
# FIND CURRENT LIVE BROADCAST
# ============================================================

def find_current_live_gold() -> Optional[Dict[str, Any]]:
    """
    Searches ONLY the target channel's /live page.

    Returns the current LIVE Gold/XAUUSD broadcast.

    Returns None when:
        - the channel is not live
        - the broadcast is scheduled
        - the broadcast is recorded
        - the broadcast is not Gold/XAUUSD
        - the channel cannot be reached
    """

    channel_url = get_target_channel_url()

    if not channel_url:
        logger.error(
            "Target channel URL is unavailable."
        )
        return None

    live_url = channel_url.rstrip("/") + "/live"

    logger.info(
        "Checking target channel for current LIVE broadcast..."
    )

    try:

        options = dict(BASE_YDL_OPTIONS)

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                live_url,
                download=False,
            )

        if not info:
            logger.info(
                "No live broadcast information found."
            )
            return None

        # ----------------------------------------------------
        # Playlist/channel page handling
        # ----------------------------------------------------

        entries = info.get("entries")

        if entries:

            for entry in entries:

                if not entry:
                    continue

                video_id = entry.get("id")

                if not video_id:
                    continue

                try:

                    video_url = (
                        f"https://www.youtube.com/watch?v={video_id}"
                    )

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
                    "CURRENT LIVE GOLD STREAM FOUND: %s",
                    video_info.get("title", "Unknown"),
                )

                return video_info

            return None

        # ----------------------------------------------------
        # Direct video result
        # ----------------------------------------------------

        if not belongs_to_target_channel(info):
            return None

        if not is_currently_live(info):
            return None

        if not is_gold_stream(info):
            return None

        logger.info(
            "CURRENT LIVE GOLD STREAM FOUND: %s",
            info.get("title", "Unknown"),
        )

        return info

    except Exception as exc:

        logger.warning(
            "Unable to check YouTube live page: %s",
            exc,
        )

        return None


# ============================================================
# GET DIRECT STREAM URL
# ============================================================

def get_stream_url(
    live_info: Dict[str, Any]
) -> Optional[str]:
    """
    Extracts the direct media stream URL used by FFmpeg/OpenCV.
    """

    if not live_info:
        return None

    video_id = live_info.get("id")

    if not video_id:
        return None

    try:

        video_url = (
            f"https://www.youtube.com/watch?v={video_id}"
        )

        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,

            # Prefer a video stream suitable for frame capture.
            "format": (
                "bestvideo[ext=mp4]/"
                "best[ext=mp4]/"
                "best"
            ),
        }

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                video_url,
                download=False,
            )

        if not info:
            return None

        # ----------------------------------------------------
        # Make absolutely sure it is still live.
        # ----------------------------------------------------

        if not is_currently_live(info):

            logger.warning(
                "Stream is no longer LIVE."
            )

            return None

        if not belongs_to_target_channel(info):

            logger.warning(
                "Stream does not belong to target channel."
            )

            return None

        if not is_gold_stream(info):

            logger.warning(
                "Stream is no longer identified as Gold/XAUUSD."
            )

            return None

        # ----------------------------------------------------
        # Direct URL.
        # ----------------------------------------------------

        stream_url = info.get("url")

        if stream_url:
            return stream_url

        # ----------------------------------------------------
        # Search formats if direct URL was not supplied.
        # ----------------------------------------------------

        formats = info.get("formats") or []

        preferred = []

        for fmt in formats:

            url = fmt.get("url")

            if not url:
                continue

            video_codec = fmt.get("vcodec")

            if not video_codec or video_codec == "none":
                continue

            preferred.append(fmt)

        if not preferred:
            return None

        # Highest resolution available.
        preferred.sort(
            key=lambda x: (
                x.get("height") or 0,
                x.get("width") or 0,
                x.get("tbr") or 0,
            ),
            reverse=True,
        )

        return preferred[0].get("url")

    except Exception as exc:

        logger.warning(
            "Unable to obtain direct stream URL: %s",
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
# GET CURRENT LIVE TITLE
# ============================================================

def get_current_title(
    live_info: Optional[Dict[str, Any]]
) -> str:

    if not live_info:
        return ""

    return str(
        live_info.get("title") or ""
    )


# ============================================================
# VERIFY LIVE STREAM
# ============================================================

def verify_live_stream(
    video_id: str
) -> Optional[Dict[str, Any]]:
    """
    Re-checks a video ID before capturing frames.

    This prevents the monitor from continuing to process a
    stream after it has ended or changed.
    """

    if not video_id:
        return None

    try:

        video_url = (
            f"https://www.youtube.com/watch?v={video_id}"
        )

        options = dict(BASE_YDL_OPTIONS)

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                video_url,
                download=False,
            )

        if not info:
            return None

        if not belongs_to_target_channel(info):
            return None

        if not is_currently_live(info):
            return None

        if not is_gold_stream(info):
            return None

        return info

    except Exception as exc:

        logger.warning(
            "Live verification failed: %s",
            exc,
        )

        return None


# ============================================================
# STARTUP CHECK
# ============================================================

def initialize_youtube_source() -> bool:
    """
    Initializes the YouTube source engine.
    """

    logger.info(
        "Initializing YouTube live source..."
    )

    if not discover_target_channel():

        logger.error(
            "YouTube source initialization failed."
        )

        return False

    logger.info(
        "YouTube source initialized successfully."
    )

    return True