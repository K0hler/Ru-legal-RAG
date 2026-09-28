from datetime import UTC, datetime
import hashlib
import json
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


_DOCUMENT_HASH = re.compile(r"[0-9a-f]{64}")


class ActualPravoFailure(Exception):
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


class _HttpOnlyRedirectHandler(HTTPRedirectHandler):
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
            raise ActualPravoFailure(
                "blocked_redirect",
                f"source redirect is outside the HTTP origin: {redirected.full_url}",
                retryable=False,
                source_url=redirected.full_url,
            )
        return redirected


_HTTP_ONLY_OPENER = build_opener(_HttpOnlyRedirectHandler())


def urlopen(request: Request, timeout: float):
    return _HTTP_ONLY_OPENER.open(request, timeout=timeout)


class ActualPravoConnector:
    source_system = "actual.pravo.gov.ru"
    adapter_version = "actual-pravo/1"
    base_url = "http://actual.pravo.gov.ru"
    rights_status = (
        "Official consolidated-text candidate; verify access terms before bulk acquisition"
    )
    _api_base = "http://actual.pravo.gov.ru:8000/api/ebpi"

    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = timeout

    def fetch(self, document_hash: str) -> dict[str, object]:
        if _DOCUMENT_HASH.fullmatch(document_hash) is None:
            raise ActualPravoFailure(
                "invalid_external_id",
                "document hash must contain 64 lowercase hexadecimal characters",
                retryable=False,
                source_url=self.base_url,
            )

        source_url = f"{self.base_url}/list.html#hash={document_hash}&bpa=ebpi"
        card_url = self._url("card/", {"hash": document_hash})
        card_bytes, card_transport = self._get(card_url)
        card = self._parse_json(card_bytes, "invalid_card", card_url)
        adoption = self._validate_card(card, document_hash, card_url)

        redactions_url = self._url(
            "redactions/",
            {"hash": document_hash, "ttl": 4},
        )
        redactions_bytes, redactions_transport = self._get(redactions_url)
        redactions = self._parse_json(
            redactions_bytes,
            "invalid_redactions",
            redactions_url,
        )
        edition = self._select_edition(
            redactions,
            card["docid"],
            document_hash,
            redactions_url,
        )

        redtext_url = (
            f"{self._api_base}/redtext?"
            + urlencode({"bpa": "ebpi", "t": edition["redid"], "ttl": 0})
        )
        redtext_bytes, redtext_transport = self._get(redtext_url)
        redtext = self._parse_json(redtext_bytes, "invalid_text", redtext_url)
        if (
            redtext.get("error") is not None
            or not isinstance(redtext.get("redtext"), str)
            or "<html" not in redtext["redtext"].lower()
        ):
            raise ActualPravoFailure(
                "invalid_text",
                "consolidated-text response does not contain HTML text",
                retryable=False,
                source_url=redtext_url,
            )

        adopted_at = datetime.strptime(adoption["odate"], "%d.%m.%Y").date().isoformat()
        act_external_id = f"federal-law:{adopted_at}:{adoption['onumber']}"
        act_source_item = f"declared-act:{act_external_id}"
        source_item = f"{self.source_system}:{document_hash}"
        act_label = f"{card['docpassing']} \"{card['docname']}\""
        card_sha256 = hashlib.sha256(card_bytes).hexdigest()
        edition_date = datetime.strptime(edition["reddate"], "%Y%m%d").date().isoformat()
        captured_at = _utc_now()

        return {
            "adapter_version": self.adapter_version,
            "captured_at": captured_at,
            "declared_act_identity": act_label,
            "declared_edition_label": edition["redcaption"],
            "declared_publication": None,
            "discovered_source_items": [
                {
                    "declared_act_identity": act_label,
                    "external_id": act_external_id,
                    "item_kind": "act",
                    "label": act_label,
                    "source_item": act_source_item,
                    "source_system": "declared-act",
                    "source_url": source_url,
                }
            ],
            "edition_claim": {
                "claimed_edition_date": edition_date,
                "claimed_edition_label": edition["redcaption"],
                "source_asset_sha256": hashlib.sha256(redactions_bytes).hexdigest(),
            },
            "external_id": document_hash,
            "item_kind": "edition_candidate",
            "label": f"Consolidated-text candidate: {act_label}",
            "media_type": "application/json",
            "raw_bytes": redtext_bytes,
            "relation_claims": [
                {
                    "asserted_by": self.source_system,
                    "evidence_reference": {
                        "locator": "$.dochash; $.adoptions[0]",
                        "source_asset_role": "actual_card",
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
                    "role": "actual_card",
                    "source_url": source_url,
                    "transport_metadata": card_transport,
                },
                {
                    "media_type": "application/json",
                    "raw_bytes": redactions_bytes,
                    "role": "declared_editions",
                    "source_url": source_url,
                    "transport_metadata": redactions_transport,
                },
            ],
            "temporal_coverage": {
                "status": "temporal_coverage_unknown",
                "valid_from": None,
                "valid_to": None,
            },
            "transport_metadata": redtext_transport,
            "unresolved_items": [
                {
                    "diagnostic_message": (
                        "The source-declared edition date is not verified effective-date evidence."
                    ),
                    "reason": "temporal_coverage_unknown",
                    "source_asset_sha256": hashlib.sha256(redactions_bytes).hexdigest(),
                }
            ],
        }

    def _url(self, endpoint: str, payload: dict[str, object]) -> str:
        return f"{self._api_base}/{endpoint}?" + urlencode(
            {
                "bpa": "ebpi",
                "t": json.dumps(payload, separators=(",", ":")),
            }
        )

    def _get(self, url: str) -> tuple[bytes, dict[str, object]]:
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "LegalRAG-M0/0.5",
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
                    if name.lower() in {"content-type", "content-length", "etag", "last-modified"}
                }
        except HTTPError as error:
            status = error.code
            reason = error.reason
            error.close()
            raise ActualPravoFailure(
                "http_error",
                f"HTTP {status}: {reason}",
                retryable=status == 429 or status >= 500,
                http_status=status,
                source_url=url,
            ) from None
        except (TimeoutError, socket.timeout):
            raise ActualPravoFailure(
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
            raise ActualPravoFailure(
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
    def _parse_json(raw_bytes: bytes, reason: str, source_url: str) -> dict[str, object]:
        try:
            value = json.loads(raw_bytes.decode("utf-8-sig"))
            if not isinstance(value, dict):
                raise ValueError("response must be an object")
            return value
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
            raise ActualPravoFailure(
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
    ) -> dict[str, str]:
        try:
            if card.get("error"):
                raise ValueError(f"source returned an error: {card['error']}")
            if card["dochash"] != document_hash:
                raise ValueError("card identity mismatch")
            if type(card["docid"]) is not int or card["docid"] <= 0:
                raise ValueError("docid must be a positive integer")
            for field in ("docname", "docpassing", "docstate"):
                if not isinstance(card[field], str) or not card[field].strip():
                    raise ValueError(f"{field} must be a non-empty string")
            if not isinstance(card["adoptions"], list) or len(card["adoptions"]) != 1:
                raise ValueError("exactly one adoption record is required")
            adoption = card["adoptions"][0]
            if not isinstance(adoption, dict):
                raise ValueError("adoption must be an object")
            for field in ("odate", "onumber", "type"):
                if not isinstance(adoption.get(field), str) or not adoption[field].strip():
                    raise ValueError(f"adoption {field} must be a non-empty string")
            datetime.strptime(adoption["odate"], "%d.%m.%Y")
            if adoption["type"] != "Федеральный закон":
                raise ValueError(f"unsupported act type: {adoption['type']}")
            return adoption
        except (KeyError, TypeError, ValueError) as error:
            raise ActualPravoFailure(
                "invalid_card",
                f"document card is not valid: {error}",
                retryable=False,
                source_url=source_url,
            ) from None

    @staticmethod
    def _select_edition(
        response: dict[str, object],
        docid: int,
        document_hash: str,
        source_url: str,
    ) -> dict[str, object]:
        try:
            if response.get("error"):
                raise ValueError(f"source returned an error: {response['error']}")
            if response["docid"] != docid or response["dochash"] != document_hash:
                raise ValueError("redactions identity mismatch")
            if not isinstance(response["redactions"], list):
                raise ValueError("redactions must be a list")
            candidates = [
                edition
                for edition in response["redactions"]
                if isinstance(edition, dict)
                and edition.get("actual") is True
                and edition.get("redofficial") is True
                and edition.get("redcompleted") is True
                and edition.get("hascontent") is True
                and edition.get("contentcomplete") is True
            ]
            if len(candidates) != 1:
                raise ValueError("exactly one complete official current edition is required")
            edition = candidates[0]
            if type(edition.get("redid")) is not int or edition["redid"] <= 0:
                raise ValueError("redid must be a positive integer")
            if not isinstance(edition.get("redcaption"), str) or not edition[
                "redcaption"
            ].strip():
                raise ValueError("redcaption must be a non-empty string")
            if (
                not isinstance(edition.get("reddate"), str)
                or len(edition["reddate"]) != 8
                or not edition["reddate"].isdigit()
            ):
                raise ValueError("reddate must use YYYYMMDD")
            datetime.strptime(edition["reddate"], "%Y%m%d")
            return edition
        except (KeyError, TypeError, ValueError) as error:
            raise ActualPravoFailure(
                "invalid_redactions",
                f"redactions response is not valid: {error}",
                retryable=False,
                source_url=source_url,
            ) from None


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
