"""Host capability helpers (Render 512MB vs local Docker)."""
import os


def is_low_memory_host() -> bool:
    """
    Render free/starter instances have 512MB RAM.
    Playwright Chromium + parallel pipelines exceed this and cause OOM kills.
    """
    if os.getenv("TENNIS_SKIP_PLAYWRIGHT", "").lower() in ("1", "true", "yes"):
        return True
    # Render automatically sets RENDER=true on web services
    if os.getenv("RENDER"):
        return True
    return False


def skip_playwright_on_this_host() -> bool:
    """Never launch Chromium on 512MB hosts — use bundled player JSON instead."""
    return is_low_memory_host()
