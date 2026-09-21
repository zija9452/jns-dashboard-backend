"""
"Something changed, go refetch" signal via Firestore.

Replaces the old in-process SSEBroadcaster: browsers listen directly to a
Firestore document (Google's servers), so Cloud Run never holds a long-lived
connection open per client and can scale to zero between requests. Each
signal doc carries no data beyond a timestamp - listeners just refetch their
own count/list from our REST endpoints when it changes.
"""
import logging

from google.cloud import firestore

logger = logging.getLogger(__name__)

_client: firestore.AsyncClient | None = None


def _get_client() -> firestore.AsyncClient:
    global _client
    if _client is None:
        _client = firestore.AsyncClient()
    return _client


async def publish_signal(signal_id: str) -> None:
    """Best-effort ping. Never raises - the badge just falls back to its
    existing poll if this fails, but the caller's actual DB write must not
    be rolled back or 500 over a Firestore hiccup."""
    try:
        await _get_client().collection("signals").document(signal_id).set(
            {"ts": firestore.SERVER_TIMESTAMP}
        )
    except Exception:
        logger.warning("Failed to publish Firestore signal %r", signal_id, exc_info=True)
