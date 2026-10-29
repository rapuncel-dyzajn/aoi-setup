import asyncio
import logging
import time

from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from rpi_ws281x import ws, PixelStrip, Color

# LED strip configuration:
STRIP_LEDS     = (18 + 16) * 2
LED_COUNT      = STRIP_LEDS * 3 # Number of LED pixels.
LED_PIN        = 10             # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ    = 800000         # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10             # DMA channel to use for generating a signal (try 10)
LED_BRIGHTNESS = 16             # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False          # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    = 0              # set to '1' for GPIOs 13, 19, 41, 45 or 53
LED_STRIP      = ws.WS2812_STRIP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

strips = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL, LED_STRIP)
strips.begin()
strips_lock = asyncio.Lock()

def strips_init() -> None:
    for led in range(0, STRIP_LEDS):
        strips.setPixelColor(led, Color(167, 255, 63))
    for led in range(STRIP_LEDS, STRIP_LEDS * 2):
        strips.setPixelColor(led, Color(255, 178, 30))
    for led in range(STRIP_LEDS *2, STRIP_LEDS * 3):
        strips.setPixelColor(led, Color(53, 156, 255))
    strips.show()

def strips_shutdown() -> None:
    for led in range(0, LED_COUNT):
        strips.setPixelColor(led, Color(0, 0, 0))
    strips.show()

def set_brightness(brightness: int) -> None:
    strips.setBrightness(brightness)
    strips.show()

def set_strip_color(
    strip: int,
    R: int,
    G: int,
    B: int,
) -> None:
    logger.info(f"{strip}: {R},{G},{B}")

    for led in range(STRIP_LEDS * strip, STRIP_LEDS * (strip + 1)):
        strips.setPixelColor(led, Color(R, G, B))
    strips.show()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Run: turning on LEDs")
    yield

    logger.info("Shutting down: turning off LEDs")

    try:
        async with strips_lock:
            await run_in_threadpool(strips_shutdown)
        logger.info("All LEDs turned off")

    except Exception:
        logger.exception("Failed to turn off LEDs")

app = FastAPI(
    title="LED Strip Daemon",
    version="0.1.0",
    lifespan=lifespan,
)

app.frontend("/", directory="dist", fallback="index.html")
strips_init()

class BrightnessRequest(BaseModel):
    brightness: int = Field(strict=True, ge=0, le=255)


class StripColorRequest(BaseModel):
    strip: int = Field(strict=True, ge=0, le=255)
    R: int = Field(strict=True, ge=0, le=255)
    G: int = Field(strict=True, ge=0, le=255)
    B: int = Field(strict=True, ge=0, le=255)

@app.get("/api/brightness")
async def get_brightness():
    async with strips_lock:
        return {"brightness": strips.getBrightness()}

@app.post("/api/brightness")
async def update_brightness(data: BrightnessRequest):
    async with strips_lock:
        await run_in_threadpool(
            set_brightness,
            data.brightness,
        )

    return {
        "status": "ok",
        "brightness": data.brightness,
    }

@app.get("/api/strip/color")
async def get_strip_color(strip: int = 0):
    async with strips_lock:
        if strip > 3:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown strip: {strip}",
            )

        RGB = strips.getPixelColorRGB(STRIP_LEDS * strip)
        logger.info(f"{strip}: {RGB.r},{RGB.g},{RGB.b}")

        return {
            "strip": strip,
            "R": RGB.r,
            "G": RGB.g,
            "B": RGB.b,
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
