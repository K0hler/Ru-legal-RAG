"""Exercise urllib's real HTTP framing against an authored, socket-free peer."""
import hashlib
import io
import json
from pathlib import Path
import socket

import pytest

from legal_rag.sources.acquisition import acquire_publication
from legal_rag.sources.publication_pool import PublicationPoolConnector


EO = "0001202401010001"
PDF = b"%PDF-authored transport fixture"
CARD = {"eoNumber": EO, "name": None, "number": "1-р", "pagesCount": 1,
        "complexName": "Распоряжение Правительства Российской Федерации от 01.01.2024 № 1-р",
        "documentDate": "2024-01-01T00:00:00", "publishDateShort": "2024-01-01T00:00:00",
        "documentType": {"name": "Распоряжение"},
        "signatoryAuthorities": [{"name": "Правительство Российской Федерации"}]}


class TimeoutBody(io.BytesIO):
    def read(self, size=-1):
        raise TimeoutError("peer stalls after headers for Connection: close")


@pytest.fixture
def peer(monkeypatch):
    state = {"pdf_failure": None, "requests": []}

    class Socket:
        def __init__(self):
            self.request = b""

        def setsockopt(self, *args):
            pass

        def sendall(self, data):
            self.request += data

        def close(self):
            pass

        def makefile(self, mode):
            state["requests"].append(self.request)
            pdf = b"GET /File/Pdf?" in self.request
            body = PDF if pdf else json.dumps(CARD, ensure_ascii=False).encode()
            failure = state["pdf_failure"] if pdf else None
            status = 503 if failure == "http" else 200
            headers = [f"HTTP/1.1 {status} Authored fixture", "Connection: keep-alive",
                       "Content-Type: application/pdf" if pdf else "Content-Type: application/json"]
            if failure == "redirect":
                headers[0] = "HTTP/1.1 302 Found"
                headers.append("Location: https://example.invalid/other.pdf")
            headers.append(f"Content-Length: {len(body) + (1 if failure == 'truncated' else 0)}")
            raw = ("\r\n".join(headers) + "\r\n\r\n").encode() + body
            stalled = pdf and (b"Connection: close\r\n" in self.request or failure == "timeout")
            return TimeoutBody(raw) if stalled else io.BytesIO(raw)

    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: Socket())
    return state


def test_native_pdf_transport_completes_when_peer_stalls_on_connection_close(tmp_path, peer):
    connector = PublicationPoolConnector()
    first = acquire_publication(connector, EO, tmp_path)
    second = acquire_publication(connector, EO, tmp_path)
    assert (first["result"], second["result"]) == ("new", "unchanged")
    assert (tmp_path / "raw" / hashlib.sha256(PDF).hexdigest()).read_bytes() == PDF
    card_bytes = json.dumps(CARD, ensure_ascii=False).encode()
    assert (tmp_path / "raw" / hashlib.sha256(card_bytes).hexdigest()).read_bytes() == card_bytes
    assert len(peer["requests"]) == 4


@pytest.mark.parametrize("failure, reason", [("http", "http_error"), ("timeout", "timeout"),
                                           ("truncated", "network_error"), ("redirect", "blocked_redirect")])
def test_native_pdf_transport_failure_preserves_archive_and_writes_report(tmp_path, peer, failure, reason):
    connector = PublicationPoolConnector()
    assert acquire_publication(connector, EO, tmp_path)["result"] == "new"
    before = {p: p.read_bytes() for name in ("raw", "assets", "items") for p in (tmp_path / name).glob("*")}
    peer["pdf_failure"] = failure
    failed = acquire_publication(connector, EO, tmp_path)
    assert failed["result"] == "failed"
    report = json.loads(Path(failed["report"]).read_bytes())
    assert report["errors"][0]["reason"] == reason
    assert {p: p.read_bytes() for name in ("raw", "assets", "items") for p in (tmp_path / name).glob("*")} == before
