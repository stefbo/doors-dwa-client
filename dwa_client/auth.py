import re
import requests
import logging
from typing import Optional, Dict, Any

# Login endpoint types
ENDPOINT_SPRING = "spring"
ENDPOINT_ACEGI = "acegi"

logger = logging.getLogger(__name__)


class LoginSession:
    """
    Handles the *stateful* login handshake with DWA
    (JSESSIONID + DWA token).  Completely agnostic about
    how requests are later sent (Transport does that).

    Args:
        base_url: Base URL of the DWA server
        user: Username for authentication
        password: Password for authentication
        verify_ssl: Whether to verify SSL certificates
        login_endpoint: Login endpoint to use. None (default) for auto-detection,
                       ENDPOINT_SPRING for j_spring_security_check, or ENDPOINT_ACEGI for j_acegi_security_check
    """

    def __init__(
        self,
        base_url: str,
        user: str,
        password: str,
        verify_ssl: bool = True,
        login_endpoint: Optional[str] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.user = user
        self.password = password
        self._sess = requests.Session()
        self._sess.verify = verify_ssl
        self._dwa_token: Optional[str] = None
        self._login_endpoint = login_endpoint  # None=auto, "spring", or "acegi"

    # --- public helpers --------------------------------------------------
    @property
    def cookies(self):  # type: ignore[override]
        return self._sess.cookies

    @property
    def token(self) -> str:
        if self._dwa_token is None:
            raise RuntimeError("Call .login() first")
        return self._dwa_token

    def login(self) -> None:
        if self._login_endpoint == ENDPOINT_SPRING:
            logger.debug("Using spring endpoint (manual selection)")
            success = self._try_login(ENDPOINT_SPRING)
            if not success:
                raise RuntimeError("Login failed with spring endpoint")
        elif self._login_endpoint == ENDPOINT_ACEGI:
            logger.debug("Using acegi endpoint (manual selection)")
            success = self._try_login(ENDPOINT_ACEGI)
            if not success:
                raise RuntimeError("Login failed with acegi endpoint")
        else:
            # Auto-detection: try spring first, then acegi
            logger.debug("Auto-detecting login endpoint")
            if not self._try_login(ENDPOINT_SPRING):
                logger.debug("Spring endpoint failed, trying acegi")
                if not self._try_login(ENDPOINT_ACEGI):
                    raise RuntimeError("Login failed with both spring and acegi endpoints")

    def _try_login(self, endpoint_type: str) -> bool:
        """Try to login with specified endpoint type. Returns True on success."""
        if endpoint_type == ENDPOINT_SPRING:
            url = f"{self.base_url}/dwa/j_spring_security_check"
        elif endpoint_type == ENDPOINT_ACEGI:
            url = f"{self.base_url}/dwa/j_acegi_security_check"
        else:
            raise ValueError(f"Unknown endpoint type: {endpoint_type}")

        logger.debug(f"Attempting login with {endpoint_type} endpoint: {url}")
        data = {"j_username": self.user, "j_password": self.password, "loginButton": ""}
        try:
            r = self._sess.post(url, data=data, allow_redirects=True)
            r.raise_for_status()
            logger.debug(f"POST request successful, status code: {r.status_code}")
            m = re.search(
                r'function\s+getDWAToken\s*\([^)]*\)\s*{[^"\']*["\']([0-9a-f\-]{36})',
                r.text,
                re.I | re.S,
            )
            if m:
                self._dwa_token = m.group(1)
                logger.debug(f"Successfully authenticated with {endpoint_type} endpoint")
                return True
            else:
                logger.debug(f"DWA token not found in response from {endpoint_type} endpoint")
        except requests.RequestException as e:
            logger.debug(f"Login failed with {endpoint_type} endpoint: {e}")
        return False

    # --- used by HTTPTransport ------------------------------------------
    def prepare_headers(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        hdr = {"Dwa_token": self.token}
        if extra:
            hdr.update(extra)
        return hdr

    def raw_session(self) -> requests.Session:
        """Return the underlying `requests.Session` (cookies + SSL)."""
        return self._sess
