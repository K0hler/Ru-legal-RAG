from datetime import UTC, datetime
import hashlib
import json
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


_APPROVED_DOCUMENT_HASH = (
    "c0f54c3af0cc8f1b02f48f62483afb358baeb55269d4be8e00e69458ebd3a663"
)
_DOCUMENT_HASH = re.compile(r"[0-9a-f]{64}")
_ACT_EXTERNAL_ID = "government-decree:2011-05-06:354"
_TITLE = (
    "О предоставлении коммунальных услуг собственникам и пользователям помещений "
    "в многоквартирных домах и жилых домов"
)
_ADOPTION = "Постановление Правительства Российской Федерации от 06.05.2011 № 354"
_DECLARED_ACT_IDENTITY = f'{_ADOPTION} "{_TITLE}"'


class LegislationRussiaFailure(Exception):
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


class _SameOriginRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        redirected = super().redirect_request(
            request,
            file_pointer,
            code,
            message,
            headers,
            new_url,
        )
        if redirected is None:
            return None
        original = urlsplit(request.full_url)
        destination = urlsplit(redirected.full_url)
        if destination.scheme != "http" or destination.netloc != original.netloc:
            raise LegislationRussiaFailure(
                "blocked_redirect",
                f"source redirect is outside the HTTP origin: {redirected.full_url}",
                retryable=False,
                source_url=redirected.full_url,
            )
        return redirected


_OPENER = build_opener(_SameOriginRedirectHandler())


def urlopen(request: Request, timeout: float):
    return _OPENER.open(request, timeout=timeout)


class LegislationRussiaConnector:
    source_system = "pravo.gov.ru/legislation-russia"
    adapter_version = "legislation-russia/2"
    base_url = "http://ips.pravo.gov.ru"
    rights_status = "Official legal act; verify access terms before bulk acquisition"
    _api_base = f"{base_url}/api/ips/legislation"

    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = timeout

    def fetch(self, document_hash: str) -> dict[str, object]:
        if _DOCUMENT_HASH.fullmatch(document_hash) is None:
            raise LegislationRussiaFailure(
                "invalid_external_id",
                "document hash must contain 64 lowercase hexadecimal characters",
                retryable=False,
                source_url=self.base_url,
            )
        if document_hash != _APPROVED_DOCUMENT_HASH:
            raise LegislationRussiaFailure(
                "unsupported_document",
                "M0-06 supports only the approved Government-decree pilot document",
                retryable=False,
                source_url=self.base_url,
            )

        source_url = f"{self.base_url}/search/{document_hash}"
        card_url = f"{self._api_base}/document_card.json?" + urlencode(
            {"hash": document_hash}
        )
        card_bytes, card_transport = self._get(card_url)
        card = self._parse_json(card_bytes, "invalid_card", card_url)
        edition = self._validate_card(card, document_hash, card_url)

        text_url = f"{self._api_base}/documenttext?" + urlencode(
            {
                "nd": card["nd"],
                "rdk": edition["id"],
                "bpa": card["baseid"],
            }
        )
        text_bytes, text_transport = self._get(text_url)
        text = self._parse_json(text_bytes, "invalid_text", text_url)
        self._validate_text(text, card, edition, text_url)

        card_sha256 = hashlib.sha256(card_bytes).hexdigest()
        edition_date = datetime.strptime(edition["date"], "%d.%m.%Y").date().isoformat()
        act_source_item = f"declared-act:{_ACT_EXTERNAL_ID}"
        source_item = f"{self.source_system}:{document_hash}"

        return {
            "adapter_version": self.adapter_version,
            "captured_at": _utc_now(),
            "declared_act_identity": _DECLARED_ACT_IDENTITY,
            "declared_edition_label": edition["redname"],
            "declared_publication": None,
            "discovered_source_items": [
                {
                    "declared_act_identity": _DECLARED_ACT_IDENTITY,
                    "external_id": _ACT_EXTERNAL_ID,
                    "item_kind": "act",
                    "label": _DECLARED_ACT_IDENTITY,
                    "source_item": act_source_item,
                    "source_system": "declared-act",
                    "source_url": source_url,
                }
            ],
            "edition_claim": {
                "claimed_edition_date": edition_date,
                "claimed_edition_label": edition["redname"],
                "source_asset_sha256": card_sha256,
            },
            "external_id": document_hash,
            "item_kind": "edition_candidate",
            "label": f"Legislation Russia candidate: {_DECLARED_ACT_IDENTITY}",
            "media_type": "application/json",
            "raw_asset_role": "legislation_text",
            "raw_bytes": text_bytes,
            "relation_claims": [
                {
                    "asserted_by": self.source_system,
                    "evidence_reference": {
                        "locator": "$.hash; $.nd; $.adoption",
                        "source_asset_role": "legislation_card",
                        "source_asset_sha256": card_sha256,
                        "source_url": source_url,
                    },
                    "from_source_item": source_item,
                    "relation_type": "consolidates",
                    "to_candidates": [act_source_item],
                }
            ],
            "request_cursor": document_hash,
            "rights_status": self.rights_status,
            "source_system": self.source_system,
            "source_url": source_url,
            "supporting_assets": [
                {
                    "media_type": "application/json",
                    "raw_bytes": card_bytes,
                    "role": "legislation_card",
                    "source_url": source_url,
                    "transport_metadata": card_transport,
                }
            ],
            "temporal_coverage": {
                "status": "temporal_coverage_unknown",
                "valid_from": None,
                "valid_to": None,
            },
            "transport_metadata": text_transport,
            "unresolved_items": [
                {
                    "diagnostic_message": (
                        "The source-declared edition date is not verified "
                        "effective-date evidence."
                    ),
                    "reason": "temporal_coverage_unknown",
                    "source_asset_sha256": card_sha256,
                }
            ],
        }

    def _get(self, url: str) -> tuple[bytes, dict[str, object]]:
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "LegalRAG-M0/0.6",
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
                    in {"content-type", "content-length", "etag", "last-modified"}
                }
                declared_length = headers.get("content-length")
                if declared_length is not None:
                    try:
                        complete = int(declared_length) == len(body)
                    except ValueError:
                        complete = False
                    if not complete:
                        raise LegislationRussiaFailure(
                            "incomplete_response",
                            "source response length does not match Content-Length",
                            retryable=True,
                            source_url=url,
                        )
        except HTTPError as error:
            status = error.code
            reason = error.reason
            error.close()
            raise LegislationRussiaFailure(
                "http_error",
                f"HTTP {status}: {reason}",
                retryable=status == 429 or status >= 500,
                http_status=status,
                source_url=url,
            ) from None
        except (TimeoutError, socket.timeout):
            raise LegislationRussiaFailure(
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
            raise LegislationRussiaFailure(
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

    @staticmethod
    def _parse_json(
        raw_bytes: bytes,
        reason: str,
        source_url: str,
    ) -> dict[str, object]:
        try:
            value = json.loads(raw_bytes.decode("utf-8-sig"))
            if not isinstance(value, dict):
                raise ValueError("response must be an object")
            return value
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
            raise LegislationRussiaFailure(
                reason,
                f"source response is not valid JSON: {error}",
                retryable=False,
                source_url=source_url,
            ) from None

    @staticmethod
    def _validate_card(
        card: dict[str, object],
        document_hash: str,
        source_url: str,
    ) -> dict[str, object]:
        try:
            if card["hash"] != document_hash:
                raise ValueError("card identity mismatch")
            if card["adoption"] != _ADOPTION or card["type"] != "Постановление":
                raise ValueError("card adoption mismatch")
            if card["name"] != _TITLE:
                raise ValueError("card title mismatch")
            if not isinstance(card["nd"], str) or not card["nd"].isdigit():
                raise ValueError("card nd must be a numeric string")
            if not isinstance(card["baseid"], str) or not card["baseid"]:
                raise ValueError("card baseid is missing")
            if type(card["actualrdk"]) is not int:
                raise ValueError("card actualrdk must be an integer")
            redactions = card["redactions"]
            if not isinstance(redactions, list):
                raise ValueError("card redactions must be an array")
            selected = [
                edition
                for edition in redactions
                if isinstance(edition, dict) and edition.get("id") == card["actualrdk"]
            ]
            if len(selected) != 1:
                raise ValueError("card must expose exactly one selected edition")
            edition = selected[0]
            if (
                edition.get("actual") is not True
                or edition.get("completed") is not True
                or edition.get("status") != "актуальная"
            ):
                raise ValueError("selected edition is not complete and current")
            if not isinstance(edition.get("redname"), str) or not edition["redname"]:
                raise ValueError("selected edition label is missing")
            datetime.strptime(edition["date"], "%d.%m.%Y")
            return edition
        except (KeyError, TypeError, ValueError) as error:
            raise LegislationRussiaFailure(
                "invalid_card",
                f"Government-decree card is not valid: {error}",
                retryable=False,
                source_url=source_url,
            ) from None

    @staticmethod
    def _validate_text(
        text: dict[str, object],
        card: dict[str, object],
        edition: dict[str, object],
        source_url: str,
    ) -> None:
        try:
            if text["docid"] != card["nd"] or text["baseid"] != card["baseid"]:
                raise ValueError("document identity mismatch")
            if text["rdk"] != edition["id"]:
                raise ValueError("document edition mismatch")
            doctext = text["doctext"]
            if not isinstance(doctext, str) or "<html" not in doctext.casefold():
                raise ValueError("document HTML is missing")
        except (KeyError, TypeError, ValueError) as error:
            raise LegislationRussiaFailure(
                "invalid_text",
                f"Government-decree text is not valid: {error}",
                retryable=False,
                source_url=source_url,
            ) from None


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
