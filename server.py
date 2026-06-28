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
WEBHOOK_SECRET   = os.getenv("WEBHOOK_SECRET", "")

USE_TELEGRAM = bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)

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
    if "BUY" in signal:
        emoji = "GREEN"
    elif "SELL" in signal:
        emoji = "RED"
    else:
        emoji = "ALERT"
    lines = [f"{emoji} SMT ALERT - {signal}", f"Ticker: {ticker}", f"Price: {price}", f"Timeframe: {tf}"]
    if time_:
        lines.append(f"Time: {time_}")
    return "\n".join(lines)

@app.get("/")
async def health():
    return {"status": "ok", "telegram": USE_TELEGRAM}

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
