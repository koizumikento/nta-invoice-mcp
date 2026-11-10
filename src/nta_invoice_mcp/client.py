import logging
import os
from datetime import date
from typing import Annotated, Any

import httpx
from pydantic import Field, validate_call

API_URL = "https://web-api.invoice-kohyo.nta.go.jp/1/valid"
HISTORY_URL = "https://web-api.invoice-kohyo.nta.go.jp/1/num"
SOURCE_URL = "https://www.invoice-kohyo.nta.go.jp/"
Number = Annotated[str, Field(pattern=r"^T[0-9]{13}$")]
Numbers = Annotated[list[Number], Field(min_length=1, max_length=10)]
Day = Annotated[str, Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")]


def _redact_api_query(record: logging.LogRecord) -> bool:
    # HTTPX logs the URL at INFO, and this API requires the credential in its query.
    args = record.args
    if isinstance(args, tuple) and len(args) == 5 and isinstance(url := args[1], httpx.URL):
        base_url = url.copy_with(query=None)
        if base_url in (httpx.URL(API_URL), httpx.URL(HISTORY_URL)):
            record.args = (args[0], base_url, *args[2:])
    return True


logging.getLogger("httpx").addFilter(_redact_api_query)


async def _fetch_announcements(
    url: str, numbers: list[str], **conditions: str
) -> tuple[str, list[dict[str, Any]]]:
    app_id = os.environ.get("NTA_INVOICE_APP_ID", "").strip()
    if not app_id:
        raise ValueError("Set NTA_INVOICE_APP_ID to your registered NTA invoice API ID.")
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            response = await client.get(
                url,
                params={
                    "id": app_id,
                    "number": ",".join(dict.fromkeys(numbers)),
                    "type": "21",
                    **conditions,
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ValueError(
                f"NTA returned HTTP {exc.response.status_code}. Check the application ID, "
                "the lookup parameters, or the service availability."
            ) from None
        except httpx.RequestError:
            raise ValueError("NTA could not be reached. Retry later.") from None

    try:
        payload = response.json()
        count = int(payload["count"])
        rows = payload.get("announcement", [])
        last_updated = payload["lastUpdateDate"]
        if not isinstance(rows, list) or count != len(rows) or not isinstance(last_updated, str):
            raise ValueError
        if any(row["registratedNumber"] not in numbers for row in rows):
            raise ValueError
    except (ValueError, KeyError, TypeError, AttributeError):
        raise ValueError("NTA returned an unexpected invoice registration response.") from None
    return last_updated, rows


def _registration_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": row.get("name") or None,
        "registration_date": row.get("registrationDate") or None,
        "cancellation_date": row.get("disposalDate") or None,
        "expiration_date": row.get("expireDate") or None,
    }


def _dated_status(record: dict[str, Any] | None, reference_date: date) -> str:
    if record is None:
        return "no_record"
    try:
        ends = [
            date.fromisoformat(value)
            for value in (record["cancellation_date"], record["expiration_date"])
            if value
        ]
        registered = record["registration_date"]
        if not registered:
            return "unknown"
        if date.fromisoformat(registered) > reference_date or any(
            end <= reference_date for end in ends
        ):
            return "not_registered"
    except (ValueError, TypeError):
        raise ValueError("NTA returned an unexpected invoice registration response.") from None
    return "registered"


@validate_call
async def lookup_invoice_registrations(registration_numbers: Numbers, day: Day) -> dict[str, Any]:
    """Look up up to ten Japanese invoice registration numbers on one date (YYYY-MM-DD)."""
    try:
        reference_date = date.fromisoformat(day)
    except ValueError:
        raise ValueError("Provide a valid reference date in YYYY-MM-DD format.") from None

    last_updated, rows = await _fetch_announcements(API_URL, registration_numbers, day=day)
    records = {row["registratedNumber"]: _registration_record(row) for row in rows}
    if len(records) != len(rows):
        raise ValueError("NTA returned an unexpected invoice registration response.")
    items = []
    for number in registration_numbers:
        record = records.get(number)
        items.append(
            {
                "registration_number": number,
                "status": _dated_status(record, reference_date),
                "record": record,
            }
        )
    return {"day": day, "items": items, "last_updated": last_updated, "source_url": SOURCE_URL}


@validate_call
async def lookup_invoice_registration(registration_number: Number, day: Day) -> dict[str, Any]:
    """Look up one Japanese invoice registration number on a specified date (YYYY-MM-DD)."""
    result = await lookup_invoice_registrations([registration_number], day)
    item = result["items"][0]
    return {
        "registration_number": registration_number,
        "day": day,
        "status": item["status"],
        "record": item["record"],
        "last_updated": result["last_updated"],
        "source_url": result["source_url"],
    }


@validate_call
async def get_invoice_registration_history(registration_number: Number) -> dict[str, Any]:
    """Read published registration, cancellation and expiry history for one number."""
    last_updated, rows = await _fetch_announcements(HISTORY_URL, [registration_number], history="1")
    return {
        "registration_number": registration_number,
        "items": [
            {
                **_registration_record(row),
                "updated_date": row.get("updateDate") or None,
                "process_code": row.get("process") or None,
                "latest": row.get("latest") or None,
            }
            for row in rows
        ],
        "last_updated": last_updated,
        "source_url": SOURCE_URL,
    }
