# ==============================================================================
# TIMEZONE UTILITIES - HORA OFICIAL DE BOLIVIA (UTC-4, BOT)
# Proyecto: ECOMMERCE_TIENDA
# Ubicación: backend/app/core/timezone.py
# ==============================================================================

from datetime import datetime, timezone, timedelta
from typing import Optional, Any

# Zona horaria oficial de Bolivia: UTC-4 (sin cambio de horario de verano)
BOLIVIA_TZ = timezone(timedelta(hours=-4))


def get_bolivia_now() -> datetime:
    """
    Retorna la fecha y hora actual en la zona horaria oficial de Bolivia (UTC-4, BOT)
    como datetime 'naive' (sin tzinfo) para compatibilidad total con columnas
    'timestamp without time zone' en PostgreSQL.
    """
    return datetime.now(BOLIVIA_TZ).replace(tzinfo=None)


def to_bolivia_time(dt_val: Optional[Any]) -> Optional[datetime]:
    """
    Convierte cualquier objeto datetime o string ISO a la hora local de Bolivia.
    Si viene con indicación de zona UTC (como 'Z' o '+00:00'), realiza la conversión
    correspondiente a UTC-4 y devuelve datetime naive en hora boliviana.
    """
    if dt_val is None:
        return None

    if isinstance(dt_val, str):
        clean_str = dt_val.strip()
        if not clean_str:
            return get_bolivia_now()
        try:
            if clean_str.endswith("Z"):
                dt = datetime.fromisoformat(clean_str[:-1] + "+00:00")
                return dt.astimezone(BOLIVIA_TZ).replace(tzinfo=None)
            elif "+" in clean_str or clean_str.count("-") > 2:
                dt = datetime.fromisoformat(clean_str)
                if dt.tzinfo is not None:
                    return dt.astimezone(BOLIVIA_TZ).replace(tzinfo=None)
                return dt
            else:
                return datetime.fromisoformat(clean_str)
        except Exception:
            return get_bolivia_now()

    if isinstance(dt_val, datetime):
        if dt_val.tzinfo is not None:
            return dt_val.astimezone(BOLIVIA_TZ).replace(tzinfo=None)
        return dt_val

    return get_bolivia_now()
