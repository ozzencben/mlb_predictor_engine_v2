"""Host capability helpers (Render 512MB vs local Docker)."""
import os


def is_low_memory_host() -> bool:
    """
    Render free/starter instances have 512MB RAM.
    Playwright Chromium + API + MLB pipeline exceeds this and causes OOM kills.
  """
    if os.getenv("TENNIS_SKIP_PLAYWRIGHT", "").lower() in ("1", "true", "yes"):
        return True
    # Render automatically sets RENDER=true on web services
    if os.getenv("RENDER"):
        return True
    return False


def tennis_playwright_batch_size() -> int | None:
    """Max players to scrape per cycle on low-memory hosts. None = no limit."""
    if not is_low_memory_host():
        return None
    raw = os.getenv("TENNIS_PLAYWRIGHT_BATCH", "12")
    try:
        return max(int(raw), 1)
    except ValueError:
        return 12
