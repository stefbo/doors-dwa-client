import re, requests
from typing import Optional, Dict, Any


class LoginSession:
    """
    Handles the *stateful* login handshake with DWA
    (JSESSIONID + DWA token).  Completely agnostic about
    how requests are later sent (Transport does that).
    """

    def __init__(
        self, base_url: str, user: str, password: str, verify_ssl: bool = True
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.user = user
        self.password = password
        self._sess = requests.Session()
        self._sess.verify = verify_ssl
        self._dwa_token: Optional[str] = None

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
        url = f"{self.base_url}/dwa/j_acegi_security_check"
        data = {"j_username": self.user, "j_password": self.password, "loginButton": ""}
        r = self._sess.post(url, data=data, allow_redirects=True)
        r.raise_for_status()
        m = re.search(
            r'function\s+getDWAToken\s*\([^)]*\)\s*{[^"\']*["\']([0-9a-f\-]{36})',
            r.text,
            re.I | re.S,
        )
        if not m:
            raise RuntimeError("DWA token not found after login")
        self._dwa_token = m.group(1)

    # --- used by HTTPTransport ------------------------------------------
    def prepare_headers(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        hdr = {"Dwa_token": self.token}
        if extra:
            hdr.update(extra)
        return hdr

    def raw_session(self) -> requests.Session:
        """Return the underlying `requests.Session` (cookies + SSL)."""
        return self._sess
