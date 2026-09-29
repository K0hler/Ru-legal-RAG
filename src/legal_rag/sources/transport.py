from time import monotonic, sleep


class RequestMeter:
    def __init__(self, request_interval: float = 0.0) -> None:
        if request_interval < 0:
            raise ValueError("request_interval must be non-negative")
        self.request_interval = request_interval
        self._last_request_at: float | None = None
        self.reset()

    def reset(self) -> None:
        self.request_count = 0
        self.bytes_received = 0

    def before_request(self) -> None:
        now = monotonic()
        if self._last_request_at is not None:
            delay = self.request_interval - (now - self._last_request_at)
            if delay > 0:
                sleep(delay)
        self._last_request_at = monotonic()
        self.request_count += 1

    def record_response(self, body: bytes) -> None:
        self.bytes_received += len(body)

    @property
    def metrics(self) -> dict[str, int]:
        return {
            "bytes_received": self.bytes_received,
            "request_count": self.request_count,
        }
