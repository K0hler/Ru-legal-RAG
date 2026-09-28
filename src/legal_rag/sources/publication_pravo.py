from datetime import UTC, datetime
import hashlib
import json
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class PublicationPravoFailure(Exception):
    def __init__(
        self,
        reason: str,
        message: str,
        *,
        retryable: bool,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message
        self.retryable = retryable
        self.http_status = http_status

    def as_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "message": self.message,
            "reason": self.reason,
            "retryable": self.retryable,
            "stage": "acquisition",
        }
        if self.http_status is not None:
            record["http_status"] = self.http_status
        return record


class PublicationPravoConnector:
    source_system = "publication.pravo.gov.ru"
    adapter_version = "publication-pravo/1"
    base_url = "http://publication.pravo.gov.ru"
    rights_status = "Official legal act; verify access terms before bulk acquisition"

    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = timeout

    def fetch(self, eo_number: str) -> dict[str, object]:
        if len(eo_number) != 16 or not eo_number.isdigit():
            raise PublicationPravoFailure(
                "invalid_external_id",
                "electronic publication number must contain 16 digits",
                retryable=False,
            )

        query = urlencode({"eoNumber": eo_number})
        card_url = f"{self.base_url}/api/Document?{query}"
        card_bytes, card_transport = self._get(card_url, "application/json")
        try:
            card = json.loads(card_bytes.decode("utf-8-sig"))
            if not isinstance(card, dict) or card["eoNumber"] != eo_number:
                raise ValueError("card identity mismatch")
            document_type = card["documentType"]["name"]
            authority_names = [authority["name"] for authority in card["signatoryAuthorities"]]
            declared_publication = {
                "document_date": card["documentDate"],
                "document_number": card["number"],
                "document_type": document_type,
                "electronic_publication_number": card["eoNumber"],
                "official_publication_url": f"{self.base_url}/document/{eo_number}",
                "pages_count": card["pagesCount"],
                "publication_date": card["publishDateShort"],
                "signatory_authorities": authority_names,
                "title": card["complexName"],
            }
        except (KeyError, TypeError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
            raise PublicationPravoFailure(
                "invalid_card",
                f"document card is not valid: {error}",
                retryable=False,
            ) from None

        asset_url = f"{self.base_url}/File/Pdf?{query}"
        raw_bytes, asset_transport = self._get(asset_url, "application/pdf")
        if not raw_bytes.startswith(b"%PDF-"):
            raise PublicationPravoFailure(
                "invalid_asset",
                "document asset is not a PDF by content signature",
                retryable=False,
            )

        asset_transport["card_request"] = {
            **card_transport,
            "sha256": hashlib.sha256(card_bytes).hexdigest(),
        }
        return {
            "adapter_version": self.adapter_version,
            "captured_at": _utc_now(),
            "declared_act_identity": card["complexName"],
            "declared_edition_label": None,
            "declared_publication": declared_publication,
            "external_id": eo_number,
            "media_type": "application/pdf",
            "raw_bytes": raw_bytes,
            "request_cursor": eo_number,
            "rights_status": self.rights_status,
            "source_system": self.source_system,
            "source_url": asset_url,
            "transport_metadata": asset_transport,
        }

    def _get(self, url: str, accept: str) -> tuple[bytes, dict[str, object]]:
        request = Request(
            url,
            headers={
                "Accept": accept,
                "User-Agent": "LegalRAG-M0/0.2",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read()
                status = response.status
                response_url = response.geturl()
                headers = {
                    name.lower(): value
                    for name, value in response.headers.items()
                    if name.lower()
                    in {"content-type", "content-length", "content-disposition", "etag", "last-modified"}
                }
        except HTTPError as error:
            status = error.code
            reason = error.reason
            error.close()
            raise PublicationPravoFailure(
                "http_error",
                f"HTTP {status}: {reason}",
                retryable=status == 429 or status >= 500,
                http_status=status,
            ) from None
        except (TimeoutError, socket.timeout):
            raise PublicationPravoFailure(
                "timeout",
                "source request timed out",
                retryable=True,
            ) from None
        except URLError as error:
            if isinstance(error.reason, (TimeoutError, socket.timeout)):
                reason = "timeout"
                message = "source request timed out"
            else:
                reason = "network_error"
                message = f"source request failed: {error.reason}"
            raise PublicationPravoFailure(
                reason,
                message,
                retryable=True,
            ) from None

        return body, {
            "headers": headers,
            "http_status": status,
            "request_url": url,
            "response_url": response_url,
        }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
