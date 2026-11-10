import httpx
import pytest
import respx

from nta_invoice_mcp import (
    get_invoice_registration_history,
    lookup_invoice_registration,
    lookup_invoice_registrations,
)
from nta_invoice_mcp.client import API_URL, HISTORY_URL


@pytest.mark.asyncio
@respx.mock
async def test_status_on_expiry_date_and_no_record(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("INFO", logger="httpx")
    monkeypatch.setenv("NTA_INVOICE_APP_ID", "fixture-app-id")
    number = "T0000000000000"
    route = respx.get(API_URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "lastUpdateDate": "2025-04-01",
                    "count": "1",
                    "announcement": [
                        {
                            "registratedNumber": number,
                            "name": "テスト",
                            "registrationDate": "2024-10-01",
                            "disposalDate": "",
                            "expireDate": "2025-04-01",
                        }
                    ],
                },
            ),
            httpx.Response(200, json={"lastUpdateDate": "2025-04-01", "count": "0"}),
            httpx.Response(404, text="fixture-app-id"),
        ]
    )
    result = await lookup_invoice_registration(number, "2025-04-01")
    assert dict(route.calls[0].request.url.params) == {
        "id": "fixture-app-id",
        "number": number,
        "day": "2025-04-01",
        "type": "21",
    }
    assert result["status"] == "not_registered"
    assert result["record"]["expiration_date"] == "2025-04-01"
    no_record = await lookup_invoice_registration(number, "2023-10-01")
    assert no_record["status"] == "no_record"
    assert no_record["record"] is None
    with pytest.raises(ValueError, match="HTTP 404") as error:
        await lookup_invoice_registration(number, "2023-10-01")
    assert "fixture-app-id" not in str(error.value)
    assert "HTTP Request" in caplog.text
    assert "fixture-app-id" not in caplog.text


@pytest.mark.asyncio
@respx.mock
async def test_batch_keeps_input_order_and_missing_records(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("INFO", logger="httpx")
    monkeypatch.setenv("NTA_INVOICE_APP_ID", "fixture-app-id")
    active, missing, cancelled = ("T0000000000000", "T0000000000001", "T0000000000002")
    route = respx.get(API_URL).respond(
        200,
        json={
            "count": "2",
            "lastUpdateDate": "2025-04-01",
            "announcement": [
                {
                    "registratedNumber": cancelled,
                    "registrationDate": "2024-10-01",
                    "disposalDate": "2025-04-01",
                },
                {"registratedNumber": active, "registrationDate": "2024-10-01"},
            ],
        },
    )
    numbers = [active, missing, cancelled, active]
    result = await lookup_invoice_registrations(numbers, "2025-04-01")
    assert route.call_count == 1
    assert dict(route.calls[0].request.url.params) == {
        "id": "fixture-app-id",
        "number": f"{active},{missing},{cancelled}",
        "type": "21",
        "day": "2025-04-01",
    }
    assert [item["registration_number"] for item in result["items"]] == numbers
    assert [item["status"] for item in result["items"]] == [
        "registered",
        "no_record",
        "not_registered",
        "registered",
    ]
    assert result["items"][1]["record"] is None
    assert result["last_updated"] == "2025-04-01"
    assert "fixture-app-id" not in caplog.text and active not in caplog.text


@pytest.mark.asyncio
@respx.mock
async def test_history_preserves_changes_and_redacts_request(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("INFO", logger="httpx")
    monkeypatch.setenv("NTA_INVOICE_APP_ID", "fixture-app-id")
    number = "T0000000000000"
    route = respx.get(HISTORY_URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "count": "2",
                    "lastUpdateDate": "2025-04-02",
                    "announcement": [
                        {
                            "registratedNumber": number,
                            "name": "テスト",
                            "registrationDate": "2024-10-01",
                            "updateDate": "2024-10-01",
                            "process": "01",
                            "latest": "0",
                        },
                        {
                            "registratedNumber": number,
                            "name": "テスト",
                            "registrationDate": "2024-10-01",
                            "disposalDate": "2025-04-01",
                            "updateDate": "2025-04-02",
                            "process": "04",
                            "latest": "1",
                        },
                    ],
                },
            ),
            httpx.Response(
                200, json={"count": "0", "lastUpdateDate": "2025-04-02", "announcement": []}
            ),
            httpx.Response(403, text=f"fixture-app-id {number}"),
        ]
    )
    result = await get_invoice_registration_history(number)
    assert dict(route.calls[0].request.url.params) == {
        "id": "fixture-app-id",
        "number": number,
        "type": "21",
        "history": "1",
    }
    assert result["registration_number"] == number
    assert result["last_updated"] == "2025-04-02"
    assert [item["latest"] for item in result["items"]] == ["0", "1"]
    assert result["items"][1] == {
        "name": "テスト",
        "registration_date": "2024-10-01",
        "cancellation_date": "2025-04-01",
        "expiration_date": None,
        "updated_date": "2025-04-02",
        "process_code": "04",
        "latest": "1",
    }
    assert (await get_invoice_registration_history(number))["items"] == []
    with pytest.raises(ValueError, match="HTTP 403") as error:
        await get_invoice_registration_history(number)
    assert "fixture-app-id" not in str(error.value) and number not in str(error.value)
    assert "HTTP Request" in caplog.text
    assert "fixture-app-id" not in caplog.text and number not in caplog.text
