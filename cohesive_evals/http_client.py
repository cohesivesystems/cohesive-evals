"""Standard-library HTTP transport for standalone fixture and evaluator checks."""
import http.client
import json
import urllib.error
import urllib.request

from .errors import AdapterError


class ConnectionDropped(AdapterError):
    """The peer disconnected before the client could read a complete response."""

    def __init__(self, detail):
        """Classify the interrupted exchange as an infrastructure failure."""
        super().__init__("infrastructure", detail)


class HttpClient:
    """Return public HTTP status/body observations; leave business interpretation to checks."""

    def __init__(self, url):
        """Bind the local host base URL."""
        self.url = url

    def request(self, method, path, body=None, raw=None):
        """Send JSON or exact bytes and decode the reply; malformed JSON is protocol failure."""
        status, payload = self.request_bytes(method, path, body, raw)
        try:
            return status, json.loads(payload) if payload else None
        except (ValueError, UnicodeError) as error:
            raise AdapterError("protocol", "HTTP response is not JSON") from error

    def request_bytes(self, method, path, body=None, raw=None, *, content_type="application/json"):
        """Return the status and exact response bytes, including bodies on HTTP errors."""
        data = (
            raw
            if raw is not None
            else json.dumps(body).encode() if body is not None else None
        )
        request = urllib.request.Request(
            self.url + path,
            data=data,
            method=method,
            headers={"Content-Type": content_type},
        )
        try:
            try:
                response = urllib.request.urlopen(request, timeout=20)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                return response.status, response.read()
        except (OSError, http.client.HTTPException) as error:
            reason = error.reason if isinstance(error, urllib.error.URLError) else error
            if isinstance(reason, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
                raise ConnectionDropped(str(error)) from error
            raise AdapterError("infrastructure", str(error)) from error
