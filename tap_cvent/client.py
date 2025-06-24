"""REST client handling, including cventStream base class."""

from __future__ import annotations

import decimal
import typing as t
from functools import cached_property
from importlib import resources

from singer_sdk.helpers.jsonpath import extract_jsonpath
from singer_sdk.pagination import BaseAPIPaginator  
from singer_sdk.streams import RESTStream

from tap_cvent.auth import CventAuthenticator

if t.TYPE_CHECKING:
    import requests
    from singer_sdk.helpers.types import Auth, Context



SCHEMAS_DIR = resources.files(__package__) / "schemas"


class CventStream(RESTStream):
    
    records_jsonpath = "$.data[*]"  # Path to the data array in the response
    next_page_token_jsonpath = None  # We'll handle pagination manually

    @property
    def url_base(self) -> str:
        """Return the API URL root, configurable via tap settings."""
        return self.config["api_url"]

    @cached_property
    def authenticator(self) -> Auth:
        """Return a new authenticator object."""
        return CventAuthenticator.create_for_stream(self, )

    @property
    def http_headers(self) -> dict:
        """Return the http headers needed."""
        headers = {
            "Authorization": f"Bearer {self.authenticator.access_token}",
        }
        if self.config.get("user_agent"):
            headers["User-Agent"] = self.config.get("user_agent")
        return headers

    def get_next_page_token(
        self, response: requests.Response, previous_token: t.Any | None,  # noqa: ANN401
    ) -> t.Any | None:  # noqa: ANN401
        """Return a token for identifying next page or None if no more pages."""
        try:
            data = response.json()
        except ValueError as ex:
            self.logger.warning(f"Failed to parse response as JSON: {ex}")
            return None
        
        # Check if there's a paging token
        if "paging" not in data:
            self.logger.debug("No paging information in response")
            return None
            
        paging = data["paging"]
        
        # Check for next link in _links
        if "_links" in paging and "next" in paging["_links"]:
            next_href = paging["_links"]["next"]["href"]
            # Extract token from href - assuming format like "...?token=xyz"
            if "token=" in next_href:
                token = next_href.split("token=")[-1].split("&")[0]
                return token
            else:
                self.logger.warning(f"Next link found but no token parameter: {next_href}")
                return None
        
        # Fallback: check if we have more data based on currentToken and counts
        if "currentToken" in paging:
            total_count = paging.get("totalCount", 0)
            current_count = len(data.get("data", []))
            
            # If we've received all items, no more pages
            if current_count >= total_count:
                self.logger.debug(f"Reached end of data: {current_count}/{total_count}")
                return None
                
            # Otherwise use current token for next page
            return paging["currentToken"]
        
        self.logger.debug("No pagination token found")
        return None

    def get_url_params(
        self,
        context: Context | None,
        next_page_token: t.Any | None,  # noqa: ANN401
    ) -> dict[str, t.Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params: dict = {}
        
        # Add pagination token if available
        if next_page_token:
            params["token"] = next_page_token
        
        # Add start date filter using the "after" parameter
        if self.config.get("start_date"):
            params["after"] = self.config.get("start_date")
        
        # Add replication key params if needed
        if self.replication_key:
            params["sort"] = "asc"
            params["order_by"] = self.replication_key
        
        return params

    def prepare_request_payload(
        self,
        context: Context | None,
        next_page_token: t.Any | None,  
    ) -> dict | None:
        """Prepare the data payload for the REST API request."""
        # No payload needed for GET requests
        return None

    def parse_response(self, response: requests.Response) -> t.Iterable[dict]:
        """Parse the response and return an iterator of result records."""
        # Extract records from the data array
        data = response.json(parse_float=decimal.Decimal)
        yield from extract_jsonpath(
            self.records_jsonpath,
            input=data,
        )
    # Not needed for this stream, but can be overridden in subclasses
    def post_process(
        self,
        row: dict,
        context: Context | None = None,
    ) -> dict | None:
        """As needed, append or transform raw data to match expected structure."""
        return row