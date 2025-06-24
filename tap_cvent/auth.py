"""cvent Authentication."""

from __future__ import annotations

from singer_sdk.authenticators import OAuthAuthenticator, SingletonMeta
import base64
import requests
from singer_sdk.helpers._util import utc_now

# The SingletonMeta metaclass makes your streams reuse the same authenticator instance.
# If this behaviour interferes with your use-case, you can remove the metaclass.
class CventAuthenticator(OAuthAuthenticator, metaclass=SingletonMeta):
    """Authenticator class for cvent."""

    @property
    def oauth_request_body(self) -> dict:
        """Define the OAuth request body for the Cvent API.

        Returns:
            A dict with the request body
        """
        return {
            "grant_type": "client_credentials",
            "client_id": self.config["client_id"],
            "client_secret": self.config["client_secret"],
        }

    @classmethod
    def create_for_stream(cls, stream) -> CventAuthenticator:
        """Instantiate an authenticator for a specific Singer stream.

        Args:
            stream: The Singer stream instance.

        Returns:
            A new authenticator.
        """
        return cls(
            stream=stream,
            auth_endpoint=stream.config["auth_endpoint"],
        )

    def update_access_token(self) -> None:
        """Update `access_token` along with: `last_refreshed` and `expires_in`.

        Raises:
            RuntimeError: When OAuth login fails.
        """
        request_time = utc_now()
        querystring = {"grant_type": "client_credentials"}

        # Have to use different get request vs base implementation
        credentials = f"{self.client_id}:{self.client_secret}".encode()
        auth_token = base64.b64encode(credentials).decode("ascii")
        headers = {"Authorization": f"Basic {auth_token}","Content-Type": "application/x-www-form-urlencoded"}
        
        try:
            token_response = requests.post(
                self.auth_endpoint,
                headers=headers,
                params=querystring,
                timeout=60,
            )
        except requests.RequestException as ex:
            msg = f"Failed to connect to auth endpoint: {ex}"
            raise RuntimeError(msg) from ex

        try:
            token_response.raise_for_status()
        except requests.HTTPError as ex:
            try:
                error_detail = token_response.json()
                msg = f"Failed OAuth login (HTTP {token_response.status_code}): {error_detail}"
            except ValueError:
                msg = f"Failed OAuth login (HTTP {token_response.status_code}): {token_response.text}"
            raise RuntimeError(msg) from ex

        try:
            token_json = token_response.json()
        except ValueError as ex:
            msg = f"Invalid JSON response from auth endpoint: {ex}"
            raise RuntimeError(msg) from ex

        if "access_token" not in token_json:
            msg = f"No access_token in response: {token_json}"
            raise RuntimeError(msg)

        self.logger.info("OAuth authorization attempt was successful.")

        self.access_token = token_json["access_token"]
        expiration = token_json.get("expires_in", self._default_expiration)
        self.expires_in = int(expiration) if expiration else None
        if self.expires_in is None:
            self.logger.debug(
                "No expires_in received in OAuth response and no "
                "default_expiration set. Token will be treated as if it never "
                "expires.",
            )
        self.last_refreshed = request_time