import asyncio
import logging
import time

from fastapi import FastAPI
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from pathlib import Path
from fastapi.responses import FileResponse

from rpi_ws281x import *

# LED strip configuration:
LED_COUNT      = (18 + 16) * 2 * 3 # Number of LED pixels.
LED_PIN        = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10      # DMA channel to use for generating a signal (try 10)
LED_BRIGHTNESS = 32      # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
LED_STRIP      = ws.WS2812_STRIP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LED Strip Daemon",
    version="0.1.0",
)

# Єдиний замок для всіх операцій над LED-стрічками
strips_lock = asyncio.Lock()

strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL, LED_STRIP)
strip.begin()

for led in range(0, 204):
    strip.setPixelColor(led, Color(255, 255, 255))
strip.show()

def set_all_brightness(brightness: int) -> None:
    """
    Встановити загальну яскравість усіх стрічок.

    brightness: 0..255
    """
    strip.setBrightness(brightness)
    strip.show()

def set_strip_color(
    strip: str,
    R: int,
    G: int,
    B: int,
) -> None:
    """
    Встановити колір конкретної стрічки.

    strip: унікальний ідентифікатор стрічки
    R, G, B: 0..255
    """
    logger.info(f"{strip}: {R},{G},{B}")

class BrightnessRequest(BaseModel):
    brightness: int = Field(strict=True, ge=0, le=255)


class StripColorRequest(BaseModel):
    strip: str = Field(min_length=1)
    R: int = Field(strict=True, ge=0, le=255)
    G: int = Field(strict=True, ge=0, le=255)
    B: int = Field(strict=True, ge=0, le=255)


@app.post("/api/brightness")
async def update_brightness(data: BrightnessRequest):
    async with strips_lock:
        await run_in_threadpool(
            set_all_brightness,
            data.brightness,
        )

    return {
        "status": "ok",
        "brightness": data.brightness,
    }


@app.post("/api/strip/color")
async def update_strip_color(data: StripColorRequest):
    async with strips_lock:
        await run_in_threadpool(
            set_strip_color,
            data.strip,
            data.R,
            data.G,
            data.B,
        )

    return {
        "status": "ok",
        "strip": data.strip,
        "R": data.R,
        "G": data.G,
        "B": data.B,
    }

@app.get("/")
async def index():
    html_path = Path(__file__).resolve().parent.parent / "index.html"
    return FileResponse(html_path)
