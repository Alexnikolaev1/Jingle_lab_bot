"""Общий aiohttp ClientSession для внешних API."""

import aiohttp

_session: aiohttp.ClientSession | None = None


def get_http_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=120),
            raise_for_status=False,
        )
    return _session


async def close_http_session() -> None:
    global _session
    if _session is not None and not _session.closed:
        await _session.close()
    _session = None
