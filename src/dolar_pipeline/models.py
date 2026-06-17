from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


try:
    ARGENTINA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")
except ZoneInfoNotFoundError:
    ARGENTINA_TZ = timezone(timedelta(hours=-3))


@dataclass(frozen=True)
class DollarQuote:
    observed_date: str
    casa: str
    nombre: str
    moneda: str
    compra: float | None
    venta: float | None
    fecha_actualizacion: str
    payload_hash: str


def normalize_quotes(raw_quotes: list[dict[str, Any]]) -> list[DollarQuote]:
    return [normalize_quote(item) for item in raw_quotes]


def normalize_quote(item: dict[str, Any]) -> DollarQuote:
    required = {"casa", "nombre", "moneda", "fechaActualizacion"}
    missing = required - item.keys()
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"Quote is missing required fields: {missing_list}")

    casa = str(item["casa"]).strip().lower()
    if not casa:
        raise ValueError("Quote field 'casa' cannot be empty")

    fecha_actualizacion = str(item["fechaActualizacion"])
    observed_date = _date_in_argentina(fecha_actualizacion)

    normalized_payload = {
        "casa": casa,
        "nombre": str(item["nombre"]).strip(),
        "moneda": str(item["moneda"]).strip(),
        "compra": _to_optional_float(item.get("compra")),
        "venta": _to_optional_float(item.get("venta")),
        "fechaActualizacion": fecha_actualizacion,
    }

    return DollarQuote(
        observed_date=observed_date,
        casa=casa,
        nombre=normalized_payload["nombre"],
        moneda=normalized_payload["moneda"],
        compra=normalized_payload["compra"],
        venta=normalized_payload["venta"],
        fecha_actualizacion=fecha_actualizacion,
        payload_hash=_hash_payload(normalized_payload),
    )


def _to_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _date_in_argentina(value: str) -> str:
    parsed = _parse_datetime(value)
    return parsed.astimezone(ARGENTINA_TZ).date().isoformat()


def _parse_datetime(value: str) -> datetime:
    cleaned = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        parsed = datetime.now(tz=ARGENTINA_TZ)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ARGENTINA_TZ)
    return parsed


def _hash_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

