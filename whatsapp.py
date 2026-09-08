# ============================================================
# WHATSAPP NOTIFICATIONS
# ============================================================

import requests

from config import (
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_RECIPIENT,
    WHATSAPP_API_VERSION
)


class WhatsApp:

    def __init__(self):

        self.url = (
            "https://graph.facebook.com/"
            + WHATSAPP_API_VERSION
            + "/"
            + WHATSAPP_PHONE_NUMBER_ID
            + "/messages"
        )

    def send(self, message):

        headers = {
            "Authorization":
                "Bearer "
                + WHATSAPP_ACCESS_TOKEN,

            "Content-Type":
                "application/json"
        }

        payload = {
            "messaging_product":
                "whatsapp",

            "recipient_type":
                "individual",

            "to":
                WHATSAPP_RECIPIENT,

            "type":
                "text",

            "text": {
                "preview_url":
                    False,

                "body":
                    message
            }
        }

        try:

            response = requests.post(
                self.url,
                headers=headers,
                json=payload,
                timeout=30
            )

            print(
                "WhatsApp:",
                response.status_code,
                response.text
            )

            return response.ok

        except Exception as e:

            print(
                "WhatsApp error:",
                e
            )

            return False