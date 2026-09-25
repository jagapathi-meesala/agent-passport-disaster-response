"""
External Resource Provider HTTP Client.

Responsible ONLY for communicating with configurable external resource endpoints
via HTTP requests, applying timeouts, handling network errors, and returning raw provider JSON payloads.
"""

import json
import socket
import urllib.request
import urllib.parse
import urllib.error
from typing import Any, Dict, Optional
from config.settings import get_settings


class ResourceProviderError(RuntimeError):
    """Exception raised when external resource provider encounters network or HTTP errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)


class ResourceProviderClient:
    """
    HTTP client for querying external resource services using dynamic runtime parameters.
    Does not contain decision logic, UI code, or framework dependencies.
    """

    def __init__(
        self,
        service_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        settings = get_settings()
        self.service_url = service_url or settings.resource_service_url
        self.api_key = api_key if api_key is not None else settings.resource_api_key
        self.timeout = timeout if timeout is not None else settings.resource_timeout_seconds

    def build_url(self, resource_type: str, latitude: float, longitude: float, radius: float) -> str:
        """Construct endpoint URL with query parameters for target resource query."""
        params = {
            "type": resource_type,
            "latitude": str(latitude),
            "longitude": str(longitude),
            "radius": str(radius)
        }
        if self.api_key:
            params["apikey"] = self.api_key

        url_parts = list(urllib.parse.urlparse(self.service_url))
        query = dict(urllib.parse.parse_qsl(url_parts[4]))
        query.update(params)
        url_parts[4] = urllib.parse.urlencode(query)

        return urllib.parse.urlunparse(url_parts)

    def fetch_resources(
        self,
        resource_type: str,
        latitude: float,
        longitude: float,
        radius: float,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute HTTP request to external resource service.
        Returns raw provider JSON dictionary or raises ResourceProviderError.
        """
        if not self.service_url:
            raise ResourceProviderError("Resource service URL is not configured. Please set RESOURCE_SERVICE_URL in environment configuration.")

        target_url = self.build_url(resource_type, latitude, longitude, radius)
        req = urllib.request.Request(
            url=target_url,
            headers={"User-Agent": "DisasterResponseAgent-ResourceClient/1.0"}
        )

        kwargs = {}
        if self.timeout is not None:
            kwargs["timeout"] = self.timeout

        try:
            with urllib.request.urlopen(req, **kwargs) as response:
                status_code = response.getcode()
                if status_code != 200:
                    raise ResourceProviderError(
                        f"External resource service returned HTTP status {status_code}.",
                        status_code=status_code
                    )
                raw_bytes = response.read()
                try:
                    return json.loads(raw_bytes.decode("utf-8"))
                except Exception as e:
                    raise ResourceProviderError(f"Failed to parse resource provider JSON response: {str(e)}")

        except urllib.error.HTTPError as e:
            raise ResourceProviderError(f"HTTP Error querying resource provider: {e.code} {e.reason}", status_code=e.code)
        except urllib.error.URLError as e:
            raise ResourceProviderError(f"Network error connecting to resource provider: {str(e.reason)}")
        except (socket.timeout, TimeoutError):
            raise ResourceProviderError(f"Timeout of {self.timeout}s exceeded while connecting to resource provider.")
        except ResourceProviderError:
            raise
        except Exception as e:
            raise ResourceProviderError(f"Unexpected error communicating with resource provider: {str(e)}")
