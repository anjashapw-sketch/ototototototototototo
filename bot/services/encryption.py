"""
Encryption service using Fernet (AES-128).
Encrypts session strings, 2FA passwords.
"""

from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from bot.config import settings
from bot.utils.logger import log


class EncryptionService:
    """
    Service for encrypting/decrypting
    sensitive data.
    """

    def __init__(self, key: str):
        """
        Initialize with Fernet key.

        Args:
            key: Base64-encoded 32-byte key
        """
        try:
            self._fernet = Fernet(key.encode())
        except (ValueError, TypeError) as e:
            log.critical(
                f"❌ Invalid encryption key: {e}"
            )
            raise ValueError(
                "Invalid ENCRYPTION_KEY. "
                "Generate with: "
                "python scripts/generate_key.py"
            )

    def encrypt(
        self, plaintext: str
    ) -> str:
        """
        Encrypt plain text.

        Args:
            plaintext: Data to encrypt

        Returns:
            Base64 encrypted string
        """
        if not plaintext:
            return ""

        encrypted_bytes = self._fernet.encrypt(
            plaintext.encode("utf-8")
        )
        return encrypted_bytes.decode("utf-8")

    def decrypt(
        self, ciphertext: str
    ) -> Optional[str]:
        """
        Decrypt encrypted text.

        Args:
            ciphertext: Encrypted string

        Returns:
            Decrypted text or None on failure
        """
        if not ciphertext:
            return None

        try:
            decrypted_bytes = self._fernet.decrypt(
                ciphertext.encode("utf-8")
            )
            return decrypted_bytes.decode("utf-8")
        except (InvalidToken, ValueError) as e:
            log.error(
                f"❌ Decryption failed: {e}"
            )
            return None

    def encrypt_safe(
        self, plaintext: str
    ) -> str:
        """Encrypt with error handling."""
        try:
            return self.encrypt(plaintext)
        except Exception as e:
            log.error(
                f"❌ Encryption error: {e}"
            )
            return ""


# ━━━ SINGLETON INSTANCE ━━━
encryption_service = EncryptionService(
    settings.encryption_key
)