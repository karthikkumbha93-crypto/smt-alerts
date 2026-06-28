import os
import json
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="SMT Alert Server")

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TWILIO_SID       = os.getenv("TWILIO_SID", "")
TWILIO_TOKEN     = os.getenv("TWILIO_TOKEN", "")
TWILIO_FROM      = os.getenv("TWILIO_FROM", "")
SMS_TO           = os.getenv("SMS_TO", "")
WEBHOOK_SECRET   = os.getenv("WEBHOOK_SECRET", "")

USE_TELEGRAM = bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)
USE_SMS      = bool(TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM and SMS_TO)

async def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text})
        r.raise_for_status()

def format_message(payload: dict) -> str:
    signal = payload.get("signal", "UNKNOWN").upper()
    ticker = payload.get("ticker", "?")
    price  = payload.get("price", "?")
    tf     = payload.get("timeframe", "?")
    time_  = payload.get("time", "")
    emoji  = "🟢" if "BUY" in signal else "🔴" if "SELL" in signal else "⚪"
    lines  = [f"{emoji} SMT ALERT — {signal}", f"Ticker:    {ticker}", f"Price:     {price}", f"Timeframe: {tf}"]
    if time_:
        lines.append(f"Time:      {time_}")
    return "\n".join(lines)

@app.get("/")
async def health():
    return {"status": "ok", "telegram": USE_TELEGRAM, "sms": USE_SMS}

@app.post("/webhook")
async def webhook(request: Request):
    if WEBHOOK_SECRET:
        if request.headers.get("X-Secret", "") != WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Invalid secret")
    body = await request.body()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = {"signal": body.decode("utf-8")}
    message = format_message(payload)
    print(f"[ALERT] {message}")
    if USE_TELEGRAM:
        await send_telegram(message)
    return JSONResponse({"status": "sent"})
