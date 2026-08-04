"""
Detects and redacts personally identifiable information (PII) — emails,
phone numbers, SSNs, credit card numbers — from text.

CRITICAL DESIGN RULE: redaction mappings (placeholder -> real value) are
NEVER stored in `messages`. They live in state["redacted_pii"] instead —
a separate field an LLM never sees directly. This is what "nothing round-
trips PII back into a prompt" means: the mapping exists so a human
reviewer or an internal tool could look up the real value later if truly
needed, but the AI itself only ever sees placeholders like [EMAIL_1].
"""
 
import re
from typing import Tuple
 
# re.compile means memorize the exact same pattern in case you see the same thing on scanning.
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# \b is used to match word boundaries.
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CREDIT_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
# Phone last, since credit card numbers can otherwise get mis-caught as phone numbers.
_PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
 
 
def redact_pii(text: str) -> Tuple[str, dict]:
    """Returns (redacted_text, mapping).
    mapping: {"[EMAIL_1]": "jane@example.com", ...} — keep this OUT of
    `messages`; store it in state["redacted_pii"] instead."""
    mapping = {}
    counters = {"EMAIL": 0, "SSN": 0, "CARD": 0, "PHONE": 0}
 
    def _redact_pattern(current_text: str, pattern: re.Pattern, label: str) -> str:
        def _sub(match: re.Match) -> str:  # sub se different different name aate hai like Email_1,Email_2 different id's ke liye
            counters[label] += 1
            placeholder = f"[{label}_{counters[label]}]"
            mapping[placeholder] = match.group(0)
            return placeholder
        return pattern.sub(_sub, current_text) # current_text me pattern search kro aur _sub lga do for getting different redacted names like email_1,email_2
 
    # Order matters: check card numbers before phone numbers, since a 16-digit
    # card number can otherwise get partially matched as a phone number.
    text = _redact_pattern(text, _EMAIL_RE, "EMAIL")
    text = _redact_pattern(text, _SSN_RE, "SSN")
    text = _redact_pattern(text, _CREDIT_CARD_RE, "CARD")
    text = _redact_pattern(text, _PHONE_RE, "PHONE")
 
    return text, mapping
 
 
def contains_pii(text: str) -> bool:
    """Quick yes/no check, no redaction — used by the output validator to
    catch PII that might have leaked into a generated response."""
    return any(p.search(text) for p in (_EMAIL_RE, _SSN_RE, _CREDIT_CARD_RE, _PHONE_RE))
 
 
def pii_ingest_node(state: dict) -> dict:
    """Redacts PII from the latest customer message. Run this FIRST in
    your graph — before triage, before any specialist ever sees the text."""
    messages = list(state.get("messages", []))
    if not messages:
        return {}
 
    role, content = messages[-1][0], messages[-1][1]
    redacted_text, new_mapping = redact_pii(content)
    messages[-1] = (role, redacted_text)
 
    merged_mapping = dict(state.get("redacted_pii", {}))
    merged_mapping.update(new_mapping)
 
    return {"messages": messages, "redacted_pii": merged_mapping}
 
 
if __name__ == "__main__":
    sample = ("Hi, my email is jane.doe@example.com and my card number is "
               "4111 1111 1111 1111, please help with my refund.")
    redacted, mapping = redact_pii(sample)
    print("Redacted:", redacted)
    print("Mapping:", mapping)
    print("contains_pii on redacted text:", contains_pii(redacted))
    
