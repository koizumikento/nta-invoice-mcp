import logging
import os
from datetime import date
from typing import Annotated, Any

import httpx
from pydantic import Field, validate_call

API_URL = "https://web-api.invoice-kohyo.nta.go.jp/1/valid"
SOURCE_URL = "https://www.invoice-kohyo.nta.go.jp/"
Number = Annotated[str, Field(pattern=r"^T[0-9]{13}$")]
Day = Annotated[str, Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")]


def _redact_api_query(record: logging.LogRecord) -> bool:
    # HTTPX logs the URL at INFO, and this API requires the credential in its query.
    args = record.args
    if isinstance(args, tuple) and len(args) == 5 and isinstance(url := args[1], httpx.URL):
        base_url = url.copy_with(query=None)
        if base_url == httpx.URL(API_URL):
            record.args = (args[0], base_url, *args[2:])
    return True


logging.getLogger("httpx").addFilter(_redact_api_query)


@validate_call
async def lookup_invoice_registration(registration_number: Number, day: Day) -> dict[str, Any]:
    """Look up one Japanese invoice registration number on a specified date (YYYY-MM-DD)."""
    try:
        reference_date = date.fromisoformat(day)
    except ValueError:
        raise ValueError("Provide a valid reference date in YYYY-MM-DD format.") from None
    app_id = os.environ.get("NTA_INVOICE_APP_ID", "").strip()
    if not app_id:
        raise ValueError("Set NTA_INVOICE_APP_ID to your registered NTA invoice API ID.")
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            response = await client.get(
                API_URL,
                params={"id": app_id, "number": registration_number, "day": day, "type": "21"},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ValueError(
                f"NTA returned HTTP {exc.response.status_code}. Check the application ID, "
                "the reference date, or the service availability."
            ) from None
        except httpx.RequestError:
            raise ValueError("NTA could not be reached. Retry later.") from None

    try:
        payload = response.json()
        count = int(payload["count"])
        rows = payload.get("announcement", [])
        if not isinstance(rows, list) or count != len(rows) or count > 1:
            raise ValueError
        record = None
        status = "no_record"
        if rows:
            row = rows[0]
            if row["registratedNumber"] != registration_number:
                raise ValueError
            registered = row.get("registrationDate") or None
            cancelled = row.get("disposalDate") or None
            expired = row.get("expireDate") or None
            ends = [date.fromisoformat(value) for value in (cancelled, expired) if value]
            if not registered:
                status = "unknown"
            elif date.fromisoformat(registered) > reference_date or any(
                end <= reference_date for end in ends
            ):
                status = "not_registered"
            else:
                status = "registered"
            record = {
                "name": row.get("name") or None,
                "registration_date": registered,
                "cancellation_date": cancelled,
                "expiration_date": expired,
            }
        last_updated = payload["lastUpdateDate"]
    except (ValueError, KeyError, TypeError, AttributeError):
        raise ValueError("NTA returned an unexpected invoice registration response.") from None
    return {
        "registration_number": registration_number,
        "day": day,
        "status": status,
        "record": record,
        "last_updated": last_updated,
        "source_url": SOURCE_URL,
    }
