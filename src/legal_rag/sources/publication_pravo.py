from datetime import UTC, datetime
import hashlib
import json
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


_RUSSIAN_MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}
_GOVERNMENT_DECREE_AMENDMENT = re.compile(
    r"О внесении изменений в постановление Правительства Российской Федерации от "
    r"(?P<day>\d{1,2}) (?P<month>[^ ]+) (?P<year>\d{4}) г\. № (?P<number>\d+)",
    re.IGNORECASE,
)


class PublicationPravoFailure(Exception):
    def __init__(
        self,
        reason: str,
        message: str,
        *,
        retryable: bool,
        http_status: int | None = None,
        source_url: str | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message
        self.retryable = retryable
        self.http_status = http_status
        self.source_url = source_url

    def as_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "message": self.message,
            "reason": self.reason,
            "retryable": self.retryable,
            "stage": "acquisition",
        }
        if self.http_status is not None:
            record["http_status"] = self.http_status
        if self.source_url is not None:
            record["source_url"] = self.source_url
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
                source_url=self.base_url,
            )

        query = urlencode({"eoNumber": eo_number})
        card_url = f"{self.base_url}/api/Document?{query}"
        card_bytes, card_transport = self._get(card_url, "application/json")
        try:
            card = json.loads(card_bytes.decode("utf-8-sig"))
            if not isinstance(card, dict) or card["eoNumber"] != eo_number:
                raise ValueError("card identity mismatch")
            for field in ("complexName", "documentDate", "eoNumber", "name", "number"):
                if not isinstance(card[field], str) or not card[field].strip():
                    raise ValueError(f"{field} must be a non-empty string")
            if not isinstance(card["pagesCount"], int):
                raise ValueError("pagesCount must be an integer")
            if not isinstance(card["documentType"], dict) or not isinstance(
                card["documentType"].get("name"), str
            ):
                raise ValueError("documentType.name must be a string")
            if not isinstance(card["signatoryAuthorities"], list) or any(
                not isinstance(authority, dict)
                or not isinstance(authority.get("name"), str)
                for authority in card["signatoryAuthorities"]
            ):
                raise ValueError("signatoryAuthorities must contain named objects")
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
                source_url=card_url,
            ) from None

        asset_url = f"{self.base_url}/File/Pdf?{query}"
        raw_bytes, asset_transport = self._get(asset_url, "application/pdf")
        if not raw_bytes.startswith(b"%PDF-"):
            raise PublicationPravoFailure(
                "invalid_asset",
                "document asset is not a PDF by content signature",
                retryable=False,
                source_url=asset_url,
            )

        asset_transport["card_request"] = {
            **card_transport,
            "sha256": hashlib.sha256(card_bytes).hexdigest(),
        }
        discovered_source_items, relation_claims = _discover_source_claims(
            card,
            card_url,
            self.source_system,
        )
        captured_at = _utc_now()
        return {
            "adapter_version": self.adapter_version,
            "captured_at": captured_at,
            "declared_act_identity": card["complexName"],
            "declared_edition_label": None,
            "declared_publication": declared_publication,
            "discovered_source_items": discovered_source_items,
            "external_id": eo_number,
            "item_kind": "publication",
            "label": f"Official publication: {card['complexName']}",
            "media_type": "application/pdf",
            "publication_card_bytes": card_bytes,
            "publication_card_transport_metadata": card_transport,
            "publication_card_url": card_url,
            "raw_bytes": raw_bytes,
            "request_cursor": eo_number,
            "relation_claims": relation_claims,
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
                source_url=url,
            ) from None
        except (TimeoutError, socket.timeout):
            raise PublicationPravoFailure(
                "timeout",
                "source request timed out",
                retryable=True,
                source_url=url,
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
                source_url=url,
            ) from None

        return body, {
            "headers": headers,
            "http_status": status,
            "request_url": url,
            "response_url": response_url,
        }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _discover_source_claims(
    card: dict[str, object],
    card_url: str,
    source_system: str,
) -> tuple[list[dict[str, str]], list[dict[str, object]]]:
    eo_number = card["eoNumber"]
    authority_names = [authority["name"] for authority in card["signatoryAuthorities"]]
    if (
        card["documentType"]["name"] == "Постановление"
        and "Правительство Российской Федерации" in authority_names
    ):
        act_external_id = (
            f"government-decree:{card['documentDate'][:10]}:{card['number']}"
        )
    else:
        act_external_id = f"{source_system}:{eo_number}"
    act_source_item = f"declared-act:{act_external_id}"
    title = card["complexName"]
    relation_claims = [
        {
            "asserted_by": source_system,
            "evidence_reference": {
                "locator": "$.eoNumber; $.complexName",
                "source_url": card_url,
            },
            "from_source_item": f"{source_system}:{eo_number}",
            "relation_type": "publishes",
            "to_candidates": [act_source_item],
        }
    ]
    amendment_title = card["name"].startswith("О внесении изменений")
    amendment_match = _GOVERNMENT_DECREE_AMENDMENT.search(card["name"])
    item_kind = "amendment" if amendment_title else "act"
    if amendment_match:
        month = _RUSSIAN_MONTHS.get(amendment_match["month"].lower())
        if month is None:
            raise PublicationPravoFailure(
                "invalid_card",
                "document card contains an unsupported Russian month name",
                retryable=False,
                source_url=card_url,
            )
        target_source_item = (
            "declared-act:government-decree:"
            f"{amendment_match['year']}-{month:02d}-{int(amendment_match['day']):02d}:"
            f"{amendment_match['number']}"
        )
        relation_claims.append(
            {
                "asserted_by": source_system,
                "evidence_reference": {
                    "locator": "$.name",
                    "source_url": card_url,
                },
                "from_source_item": act_source_item,
                "relation_type": "amends",
                "to_candidates": [target_source_item],
            }
        )
    elif amendment_title:
        relation_claims.append(
            {
                "asserted_by": source_system,
                "diagnostic_message": (
                    "The publication card declares amendments but does not identify "
                    "one supported target."
                ),
                "evidence_reference": {
                    "locator": "$.name",
                    "source_url": card_url,
                },
                "from_source_item": act_source_item,
                "relation_type": "amends",
                "to_candidates": [],
            }
        )
    return (
        [
            {
                "declared_act_identity": title,
                "external_id": act_external_id,
                "item_kind": item_kind,
                "label": title,
                "source_item": act_source_item,
                "source_system": "declared-act",
                "source_url": card_url,
            }
        ],
        relation_claims,
    )
