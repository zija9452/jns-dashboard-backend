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


def branch_signal_id(signal_id: str) -> str:
    """Light House keeps the original doc ids (existing listeners keep working);
    other branches get their own doc, e.g. "shop_order_updates__karimabad"."""
    from ..config.branches import current_branch, DEFAULT_BRANCH
    branch = current_branch.get()
    return signal_id if branch == DEFAULT_BRANCH else f"{signal_id}__{branch}"


# Payments Record badges (per branch): sales/admin listen to REVIEW (something new to
# approve, or an approval done by someone else), the cashier to CASHIER (a reject, or
# an online payment missing its screenshot).
PAYMENTS_REVIEW_SIGNAL = "payments_record_review"
PAYMENTS_CASHIER_SIGNAL = "payments_record_cashier"


async def publish_signals(*signal_ids: str) -> None:
    for signal_id in signal_ids:
        await publish_signal(signal_id)


async def publish_signal(signal_id: str) -> None:
    """Best-effort ping. Never raises - the badge just falls back to its
    existing poll if this fails, but the caller's actual DB write must not
    be rolled back or 500 over a Firestore hiccup."""
    try:
        await _get_client().collection("signals").document(branch_signal_id(signal_id)).set(
            {"ts": firestore.SERVER_TIMESTAMP}
        )
    except Exception:
        logger.warning("Failed to publish Firestore signal %r", signal_id, exc_info=True)
