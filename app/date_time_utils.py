from datetime import datetime
from zoneinfo import ZoneInfo

BA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

def now_ba():
    """datetime aware en zona horaria Buenos Aires."""
    return datetime.now(BA_TZ)

def now_ba_iso():
    """ISO 8601 con offset -03:00, en BA."""
    return now_ba().isoformat(timespec="seconds")

def today_ba_str():
    """YYYY-MM-DD en BA."""
    return now_ba().date().isoformat()

def time_ba_str():
    """HH:MM en BA."""
    return now_ba().strftime("%H:%M")

def parse_any_iso_to_ba_naive(date_str: str) -> datetime:
    """
    Recibe:
      - '2025-12-02T02:30:24.334287Z' (UTC)
      - '2025-12-02T02:30:24.334287-03:00'
      - '2025-12-02T02:30:24.334287'
    Devuelve datetime SIN tz, pero en BA.
    """
    if not date_str:
        raise ValueError("Empty date")

    ds = date_str.replace("Z", "+00:00")

    dt = datetime.fromisoformat(ds)

    if dt.tzinfo is not None:
        return dt.astimezone(BA_TZ).replace(tzinfo=None)

    return dt
