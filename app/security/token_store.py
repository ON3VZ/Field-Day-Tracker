"""
app/security/token_store.py
============================
Secure storage for the GitHub personal access token.

Security model
--------------
The token is encrypted with **Fernet** (AES-128-CBC + HMAC-SHA256) before
being stored in ``app_settings.json``.  The encryption key is derived
from machine-specific data (MAC address + hostname + OS username) using
PBKDF2-HMAC-SHA256.

Consequences
------------
- The token in the JSON file looks like a random base64 blob — not readable
  by anyone who just opens the file.
- The token can **only** be decrypted on the **same machine** by the **same
  OS user**.  Moving ``app_settings.json`` to another PC will not expose
  the token (it simply won't decrypt there).
- The encryption key is **never stored** — it is re-derived every time.
- If the machine changes (new PC, new user account) the token must be
  re-entered.  That is by design.

This is not enterprise-grade HSM security, but it is far better than
storing the token as plain text and appropriate for a field day tool.

Public API
----------
TokenStore.encrypt(plaintext_token)   → str   (store this in settings)
TokenStore.decrypt(ciphertext)        → str   ('' if wrong machine/corrupt)
TokenStore.is_encrypted(value)        → bool
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import platform
import uuid

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

log = logging.getLogger(__name__)

# Marker prefix stored with every encrypted token so we can detect them
_PREFIX = "enc:"


class TokenStore:
    """Stateless helper for encrypting/decrypting GitHub tokens."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def encrypt(cls, plaintext_token: str) -> str:
        """Encrypt *plaintext_token* and return a storable string.

        Parameters
        ----------
        plaintext_token:
            The raw GitHub token (e.g. ``ghp_...`` or ``github_pat_...``).

        Returns
        -------
        str
            Encrypted string with ``enc:`` prefix, safe to store in JSON.
            Returns ``''`` if the token is empty.
        """
        if not plaintext_token or not plaintext_token.strip():
            return ""
        try:
            f = cls._get_fernet()
            encrypted = f.encrypt(plaintext_token.strip().encode("utf-8"))
            return _PREFIX + encrypted.decode("ascii")
        except Exception as exc:  # noqa: BLE001
            log.error("Token encryption failed: %s", exc)
            return ""

    @classmethod
    def decrypt(cls, ciphertext: str) -> str:
        """Decrypt a previously encrypted token.

        Parameters
        ----------
        ciphertext:
            Value read from ``app_settings.json`` (must start with ``enc:``).

        Returns
        -------
        str
            The original plaintext token, or ``''`` if decryption fails
            (wrong machine, corrupt data, or empty input).
        """
        if not ciphertext:
            return ""
        if not ciphertext.startswith(_PREFIX):
            # Might be a legacy plain-text token — return as-is (migration)
            log.debug("Token does not have enc: prefix — treating as plaintext.")
            return ciphertext
        try:
            raw = ciphertext[len(_PREFIX):].encode("ascii")
            f = cls._get_fernet()
            return f.decrypt(raw).decode("utf-8")
        except InvalidToken:
            log.warning(
                "Token decryption failed — wrong machine/user or corrupt data."
            )
            return ""
        except Exception as exc:  # noqa: BLE001
            log.error("Unexpected decryption error: %s", exc)
            return ""

    @staticmethod
    def is_encrypted(value: str) -> bool:
        """Return True if *value* looks like an encrypted token."""
        return isinstance(value, str) and value.startswith(_PREFIX)

    @staticmethod
    def is_set(value: str) -> bool:
        """Return True if *value* is a non-empty token (encrypted or plain)."""
        return bool(value and value.strip() and value != _PREFIX)

    # ------------------------------------------------------------------
    # Key derivation (private)
    # ------------------------------------------------------------------

    @classmethod
    def _get_fernet(cls) -> Fernet:
        """Derive a machine-specific Fernet instance."""
        key = cls._derive_key()
        return Fernet(key)

    @classmethod
    def _derive_key(cls) -> bytes:
        """Derive a 32-byte Fernet key from machine-specific data.

        Sources used (all stable across reboots on the same machine):
        - Network MAC address (from uuid.getnode)
        - OS hostname
        - OS username

        These are combined as a UTF-8 password, then stretched with
        PBKDF2-HMAC-SHA256 using a fixed salt that incorporates the
        MAC address (so salt + password both change if machine changes).
        """
        try:
            mac = str(uuid.getnode())          # 48-bit MAC as integer string
            hostname = platform.node()          # e.g. "MYLAPTOP"
            username = _get_username()          # OS login name
        except Exception:  # noqa: BLE001
            # Fallback to a constant — better than crashing, worse than unique
            mac = "000000000000"
            hostname = "unknown"
            username = "user"

        # Password = MAC + hostname + username (all lower-cased for stability)
        password = f"{mac}:{hostname.lower()}:{username.lower()}".encode("utf-8")

        # Salt = SHA256 of MAC (16 bytes) — unique per machine, not secret
        salt = hashlib.sha256(mac.encode()).digest()[:16]

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,
        )
        raw_key = kdf.derive(password)
        return base64.urlsafe_b64encode(raw_key)


def _get_username() -> str:
    """Return the current OS username reliably across platforms."""
    for env_var in ("USERNAME", "USER", "LOGNAME"):
        val = os.environ.get(env_var, "")
        if val:
            return val
    try:
        import getpass
        return getpass.getuser()
    except Exception:  # noqa: BLE001
        return "unknown"
