"""cvent tap class."""

from __future__ import annotations

from singer_sdk import Tap
from singer_sdk import typing as th  # JSON schema typing helpers

# TODO: Import your custom stream types here:
from tap_cvent import streams


class Tapcvent(Tap):
    """cvent tap class."""

    name = "tap-cvent"

    # TODO: Update this section with the actual config values you expect:
    config_jsonschema = th.PropertiesList(
        th.Property(
            "api_url",
            th.StringType,
            required=True,
            title="API URL",
            default="https://api-platform.cvent.com",
            description="The base URL for the Cvent API service",
        ),
        th.Property(
            "auth_endpoint",
            th.StringType,
            required=True,
            title="Auth Endpoint",
            description="The OAuth2 token endpoint URL",
        ),
        th.Property(
            "client_id",
            th.StringType,
            required=True,
            secret=True,  # Flag config as protected
            title="Client ID",
            description="OAuth2 client ID",
        ),
        th.Property(
            "client_secret",
            th.StringType,
            required=True,
            secret=True,  # Flag config as protected
            title="Client Secret",
            description="OAuth2 client secret",
        ),
        th.Property(
            "start_date",
            th.DateTimeType,
            description="The earliest record date to sync (format: YYYY-MM-DDTHH:MM:SS.sssZ)",
            default="2023-01-01T00:00:00.000Z",  # Added default value
        ),th.Property(
            "user_agent",
            th.StringType,
            description="A custom User-Agent header to send with each request",
        ),
    ).to_dict()

    def discover_streams(self) -> list[streams.cventStream]:
        """Return a list of discovered streams.

        Returns:
            A list of discovered streams.
        """
        return [
            streams.AdmissionItemsStream(self),
        ]


if __name__ == "__main__":
    Tapcvent.cli()
