from datetime import UTC, datetime
from html.parser import HTMLParser
import hashlib
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


_DOCUMENT_ID = "102147807"
_ACT_EXTERNAL_ID = "government-decree:2011-05-06:354"
_TITLE = (
    "О предоставлении коммунальных услуг собственникам и пользователям помещений "
    "в многоквартирных домах и жилых домов"
)
_HEADING = "от 6 мая 2011 г. № 354"
_DECLARED_ACT_IDENTITY = (
    "Постановление Правительства Российской Федерации от 6 мая 2011 г. № 354 "
    f'"{_TITLE}"'
)


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


class _DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ignored_depth = 0
        self.in_title = False
        self.title_complete = False
        self.text: list[str] = []
        self.title: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.casefold() in {"script", "style"}:
            self.ignored_depth += 1
            return
        if tag.casefold() == "title" and not self.title_complete:
            self.in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in {"script", "style"}:
            self.ignored_depth = max(0, self.ignored_depth - 1)
            return
        if tag.casefold() == "title" and self.in_title:
            self.in_title = False
            self.title_complete = True

    def handle_data(self, data: str) -> None:
        if self.ignored_depth:
            return
        self.text.append(data)
        if self.in_title:
            self.title.append(data)


class LegislationRussiaConnector:
    source_system = "pravo.gov.ru/legislation-russia"
    adapter_version = "legislation-russia/1"
    base_url = "http://pravo.gov.ru"
    rights_status = "Official legal act; verify access terms before bulk acquisition"

    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = timeout

    def fetch(self, document_id: str) -> dict[str, object]:
        if document_id != _DOCUMENT_ID:
            raise LegislationRussiaFailure(
                "unsupported_document",
                "M0-06 supports only the approved Government-decree pilot document",
                retryable=False,
                source_url=self.base_url,
            )

        source_url = f"{self.base_url}/proxy/ips/?" + urlencode(
            {"doc_itself": "", "nd": document_id}
        )
        raw_bytes, transport = self._get(source_url)
        content_type = transport["headers"].get("content-type", "")
        charset_match = re.search(r"charset=([-\w]+)", content_type, re.IGNORECASE)
        try:
            if content_type.split(";", 1)[0].strip().casefold() != "text/html":
                raise ValueError("response is not HTML")
            if charset_match is None:
                raise ValueError("response charset is missing")
            document = raw_bytes.decode(charset_match[1])
            parser = _DocumentParser()
            parser.feed(document)
            title = _normalize(" ".join(parser.title))
            visible_text = _normalize(" ".join(parser.text))
            if title != _TITLE:
                raise ValueError("document title mismatch")
            for marker in (
                "ПРАВИТЕЛЬСТВО РОССИЙСКОЙ ФЕДЕРАЦИИ",
                "ПОСТАНОВЛЕНИЕ",
                _HEADING,
                _TITLE,
            ):
                if marker not in visible_text:
                    raise ValueError(f"document marker is missing: {marker}")
        except (LookupError, UnicodeDecodeError, ValueError) as error:
            raise LegislationRussiaFailure(
                "invalid_document",
                f"Government-decree document is not valid: {error}",
                retryable=False,
                source_url=source_url,
            ) from None

        raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        act_source_item = f"declared-act:{_ACT_EXTERNAL_ID}"
        source_item = f"{self.source_system}:{document_id}"
        captured_at = _utc_now()
        return {
            "adapter_version": self.adapter_version,
            "captured_at": captured_at,
            "declared_act_identity": _DECLARED_ACT_IDENTITY,
            "declared_edition_label": None,
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
                "claimed_edition_date": None,
                "claimed_edition_label": None,
                "source_asset_sha256": raw_sha256,
            },
            "external_id": document_id,
            "item_kind": "edition_candidate",
            "label": f"Legislation Russia candidate: {_DECLARED_ACT_IDENTITY}",
            "media_type": content_type,
            "raw_asset_role": "legislation_document",
            "raw_bytes": raw_bytes,
            "relation_claims": [
                {
                    "asserted_by": self.source_system,
                    "evidence_reference": {
                        "locator": "document title; government decree heading",
                        "source_asset_role": "legislation_document",
                        "source_asset_sha256": raw_sha256,
                        "source_url": source_url,
                    },
                    "from_source_item": source_item,
                    "relation_type": "consolidates",
                    "to_candidates": [act_source_item],
                }
            ],
            "request_cursor": document_id,
            "rights_status": self.rights_status,
            "source_system": self.source_system,
            "source_url": source_url,
            "temporal_coverage": {
                "status": "temporal_coverage_unknown",
                "valid_from": None,
                "valid_to": None,
            },
            "transport_metadata": transport,
            "unresolved_items": [
                {
                    "diagnostic_message": (
                        "The response does not expose a distinct source-declared edition date or label."
                    ),
                    "reason": "edition_metadata_absent",
                    "source_asset_sha256": raw_sha256,
                },
                {
                    "diagnostic_message": (
                        "The consolidated response is not verified effective-date evidence."
                    ),
                    "reason": "temporal_coverage_unknown",
                    "source_asset_sha256": raw_sha256,
                },
            ],
        }

    def _get(self, url: str) -> tuple[bytes, dict[str, object]]:
        request = Request(
            url,
            headers={
                "Accept": "text/html",
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


def _normalize(value: str) -> str:
    return " ".join(value.split())


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
