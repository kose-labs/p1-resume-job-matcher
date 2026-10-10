"""Upload limits and checks for the CV, enforced while the request arrives.

Privacy rule from the project plan: CVs live only in memory, never on disk.
"""

from fastapi import HTTPException, UploadFile
from fastapi.responses import JSONResponse
from starlette.formparsers import MultiPartParser
from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_CV_BYTES = 5 * 1024 * 1024
# Room for the job description (20,000 characters, up to 4 bytes each) and multipart framing.
MAX_REQUEST_BYTES = MAX_CV_BYTES + 128 * 1024
PDF_MAGIC = b"%PDF-"

FILE_TOO_LARGE = "The CV must be 5 MB or smaller."


class ApiError(HTTPException):
    """An error with a stable `code` the frontend can branch on, sent as {"detail": {...}}."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        """Build the error from an HTTP status, a stable code and a user-facing message."""
        super().__init__(status_code, detail={"code": code, "message": message})


def keep_uploads_in_memory() -> None:
    """Stop Starlette writing large uploads to a temporary file.

    Starlette spools any upload over 1 MB to disk by default. Raising the threshold to the request
    limit keeps every accepted CV in memory, as the privacy rule requires.
    """
    MultiPartParser.spool_max_size = MAX_REQUEST_BYTES


class BodySizeLimit:
    """ASGI middleware that rejects request bodies over `max_bytes` with 413.

    It checks the Content-Length header first, then counts bytes as they arrive, so a missing or
    false header can't get around the limit, and an oversized upload is cut off early instead of
    being read in full.
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        """Wrap `app`, allowing request bodies of at most `max_bytes`."""
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass the request on, with a byte-counting `receive`."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        length = dict(scope["headers"]).get(b"content-length", b"")
        if length.isdigit() and int(length) > self.max_bytes:
            response = JSONResponse(
                {"detail": {"code": "file_too_large", "message": FILE_TOO_LARGE}}, status_code=413
            )
            await response(scope, receive, send)
            return

        received = 0

        async def counting_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    # An HTTPException, so FastAPI's body parsing passes it through as a 413.
                    raise ApiError(413, "file_too_large", FILE_TOO_LARGE)
            return message

        await self.app(scope, counting_receive, send)


async def read_cv(upload: UploadFile) -> bytes:
    """Return the uploaded CV's bytes after checking its size and that it really is a PDF.

    The type check reads the file's first bytes, so a renamed image or document is still caught.
    """
    data = await upload.read(MAX_CV_BYTES + 1)
    if len(data) > MAX_CV_BYTES:
        raise ApiError(413, "file_too_large", FILE_TOO_LARGE)
    if not data.startswith(PDF_MAGIC):
        raise ApiError(415, "unsupported_file_type", "The CV must be a PDF file.")
    return data
