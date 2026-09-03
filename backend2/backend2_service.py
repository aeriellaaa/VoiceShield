import os
import hmac
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

# Fix Issue #25: Load HMAC key from environment with fallback
HMAC_SECRET_KEY = os.getenv("VOICESHIELD_HMAC_SECRET", "voiceshield_default_secret_2026").encode("utf-8")
AUDIT_LOG_FILE = os.getenv("AUDIT_LOG_FILE", "decision_audit.jsonl")

def log_decision(decision_obj: dict) -> str:
    """
    Fix Issue #27 & #25: Hashes decision payload with HMAC secret 
    and writes to a functional persistent local audit trail.
    """
    # Create canonical payload string for hashing
    payload_str = json.dumps(decision_obj, sort_keys=True)
    
    # Compute HMAC SHA-256 log hash
    log_hash = hmac.new(
        HMAC_SECRET_KEY, 
        payload_str.encode("utf-8"), 
        hashlib.sha256
    ).hexdigest()
    
    decision_obj["log_hash"] = log_hash
    
    # Write to local persistent audit store
    try:
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(decision_obj) + "\n")
    except Exception as e:
        logger.error(f"Failed to append to audit log file: {e}")

    return log_hash