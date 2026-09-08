# ============================================================
# YOUTUBE LIVE STREAM FINDER
# ============================================================

import requests
import subprocess
import time

from config import (
    YOUTUBE_API_KEY,
    YOUTUBE_CHANNEL_ID,
    DIRECT_LIVE_URL
)


class YouTubeMonitor:

    def __init__(self):
        self.current_video_id = None

    def find_live_video(self):

        # ----------------------------------------------------
        # DIRECT URL MODE
        # ----------------------------------------------------

        if DIRECT_LIVE_URL.strip():

            video_id = self.extract_video_id(DIRECT_LIVE_URL)

            if video_id:
                return video_id

        # ----------------------------------------------------
        # YOUTUBE API MODE
        # ----------------------------------------------------

        if not YOUTUBE_API_KEY:
            return None

        url = "https://www.googleapis.com/youtube/v3/search"

        params = {
            "part": "snippet",
            "channelId": YOUTUBE_CHANNEL_ID,
            "eventType": "live",
            "type": "video",
            "maxResults": 10,
            "key": YOUTUBE_API_KEY
        }

        try:

            response = requests.get(
                url,
                params=params,
                timeout=20
            )

            response.raise_for_status()

            data = response.json()

            items = data.get("items", [])

            for item in items:

                video_id = item.get(
                    "id",
                    {}
                ).get("videoId")

                if video_id:
                    return video_id

        except Exception as e:

            print(
                "YouTube API error:",
                e
            )

        return None

    def extract_video_id(self, url):

        import re

        patterns = [
            r"youtube\.com/watch\?v=([^&]+)",
            r"youtu\.be/([^?]+)",
            r"youtube\.com/live/([^?]+)"
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                url
            )

            if match:
                return match.group(1)

        return None

    def get_stream_url(self, video_id):

        url = (
            "https://www.youtube.com/watch?v="
            + video_id
        )

        command = [
            "yt-dlp",
            "--no-warnings",
            "--quiet",
            "-f",
            "best[height<=720]/best",
            "--get-url",
            url
        ]

        try:

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60
            )

            stream_url = result.stdout.strip()

            if stream_url:
                return stream_url

        except Exception as e:

            print(
                "yt-dlp error:",
                e
            )

        return None