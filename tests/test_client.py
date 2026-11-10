import httpx
import pytest
import respx

from nta_invoice_mcp import lookup_invoice_registration
from nta_invoice_mcp.client import API_URL


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
