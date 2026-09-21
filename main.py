import hashlib
import hmac
import json
import os
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse

load_dotenv()

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID", "")
TWITCH_EVENTSUB_SECRET = os.getenv("TWITCH_EVENTSUB_SECRET", "")
TWITCH_BROADCASTER_ID = os.getenv("TWITCH_BROADCASTER_ID", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

TELEGRAM_API = "https://api.telegram.org"


def required_settings() -> list[str]:
    settings = {
        "TWITCH_CLIENT_ID": TWITCH_CLIENT_ID,
        "TWITCH_EVENTSUB_SECRET": TWITCH_EVENTSUB_SECRET,
        "TWITCH_BROADCASTER_ID": TWITCH_BROADCASTER_ID,
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
    }
    return [name for name, value in settings.items() if not value]


def verify_twitch_signature(
    message_id: str,
    timestamp: str,
    body: bytes,
    signature: str,
) -> bool:
    message = message_id.encode() + timestamp.encode() + body
    digest = hmac.new(
        TWITCH_EVENTSUB_SECRET.encode(),
        message,
        hashlib.sha256,
    ).hexdigest()

    expected = f"sha256={digest}"
    return hmac.compare_digest(expected, signature)


async def send_telegram_message(text: str) -> None:
    url = f"{TELEGRAM_API}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "disable_web_page_preview": False,
            },
        )

    response.raise_for_status()


@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = required_settings()
    if missing:
        print("WARNING: Missing environment variables:")
        for name in missing:
            print(f"  - {name}")
    yield


app = FastAPI(title="Twitch Telegram Notifier", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook")
async def twitch_webhook(
    request: Request,
    twitch_eventsub_message_id: str = Header(alias="Twitch-Eventsub-Message-Id"),
    twitch_eventsub_message_timestamp: str = Header(
        alias="Twitch-Eventsub-Message-Timestamp"
    ),
    twitch_eventsub_message_signature: str = Header(
        alias="Twitch-Eventsub-Message-Signature"
    ),
    twitch_eventsub_message_type: str = Header(
        alias="Twitch-Eventsub-Message-Type"
    ),
):
    body = await request.body()

    if not verify_twitch_signature(
        twitch_eventsub_message_id,
        twitch_eventsub_message_timestamp,
        body,
        twitch_eventsub_message_signature,
    ):
        raise HTTPException(status_code=403, detail="Invalid Twitch signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if twitch_eventsub_message_type == "webhook_callback_verification":
        # Twitch sends a challenge when creating the EventSub subscription.
        challenge = payload.get("challenge")
        if not challenge:
            raise HTTPException(status_code=400, detail="Missing challenge")
        return PlainTextResponse(challenge)

    if twitch_eventsub_message_type == "notification":
        subscription = payload.get("subscription", {})
        event = payload.get("event", {})
        event_type = subscription.get("type")

        if event_type == "stream.online":
            broadcaster_name = event.get(
                "broadcaster_user_name",
                event.get("broadcaster_user_login", "unknown"),
            )

            message = (
                "ð´ Ð¡ÑÑÐ¸Ð¼ Ð½Ð°ÑÐ°Ð»ÑÑ!\n\n"
                f"ðº {broadcaster_name}\n"
                f"ð https://twitch.tv/{broadcaster_name}"
            )

            await send_telegram_message(message)

        elif event_type == "stream.offline":
            print("Twitch stream went offline")

    return {"ok": True}
