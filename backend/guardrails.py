"""
Output guardrails.

This is intentionally simple for the demo (keyword + rule based), but the
comments show where a production system would plug in something stronger
(a classifier model, a grounding/hallucination check against the retrieved
context, PII detection, etc). The point being demonstrated is the *pattern*:
never return raw model output straight to the customer without a checkable
gate in between.
"""

import re

BLOCKED_PATTERNS = [
    r"system prompt",
    r"ignore (all|previous) instructions",
    r"api[_ ]?key",
    r"internal (only|use only)",
    r"password",
]

# Fields that must never appear in a customer-facing response for another
# customer's account (very small demo guard against ID leakage).
SENSITIVE_ID_PATTERN = re.compile(r"\bC\d{5}\b")


def check_input_safety(user_message: str) -> tuple[bool, str]:
    """Returns (is_safe, reason)."""
    lowered = user_message.lower()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, lowered):
            return False, f"Input matched blocked pattern: {pattern}"
    return True, ""


def check_output_safety(response_text: str, expected_customer_id: str) -> tuple[bool, str]:
    """
    Very small demo-scope check: make sure the response doesn't leak a
    customer ID other than the one we expect to be talking about.
    In production this step would also verify the response is grounded in
    the retrieved account data (not hallucinated), and run PII/compliance
    filters relevant to the industry (e.g. telecom regulatory language).
    """
    found_ids = SENSITIVE_ID_PATTERN.findall(response_text)
    for fid in found_ids:
        if fid != expected_customer_id:
            return False, f"Response referenced unexpected customer id {fid}"
    return True, ""


FALLBACK_MESSAGE = (
    "I'm not able to help with that directly. "
    "I've flagged this conversation for a human agent to review."
)
