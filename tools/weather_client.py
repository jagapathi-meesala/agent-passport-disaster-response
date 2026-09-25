"""
External Weather Provider HTTP Client.

Responsible ONLY for communicating with configurable external weather endpoints
(e.g., Open-Meteo or custom weather services) via HTTP requests, applying timeouts,
handling network errors, and returning raw provider JSON payloads.
"""

import json
import socket
import urllib.request
import urllib.parse
import urllib.error
from typing import Any, Dict, Optional
from config.settings import get_settings


class WeatherProviderError(RuntimeError):
    """Exception raised when external weather provider encounters network/HTTP errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)


class WeatherProviderClient:
    """
    HTTP client for querying external weather services using dynamic runtime parameters.
    Does not contain decision logic, disaster risk evaluation, UI code, or framework dependencies.
    """

    def __init__(
        self,
        service_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        settings = get_settings()
        self.service_url = service_url or settings.weather_service_url
        self.api_key = api_key if api_key is not None else settings.weather_api_key
        self.timeout = timeout if timeout is not None else settings.weather_timeout_seconds

    def build_url(self, latitude: float, longitude: float) -> str:
        """Construct endpoint URL with query parameters for target coordinates."""
        params = {
            "latitude": str(latitude),
            "longitude": str(longitude),
            "current_weather": "true",
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
        }
        if self.api_key:
            params["apikey"] = self.api_key

        url_parts = list(urllib.parse.urlparse(self.service_url))
        query = dict(urllib.parse.parse_qsl(url_parts[4]))
        query.update(params)
        url_parts[4] = urllib.parse.urlencode(query)

        return urllib.parse.urlunparse(url_parts)

    def fetch_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Execute HTTP GET request to external weather service.
        Returns raw provider JSON dictionary or raises WeatherProviderError.
        """
        if not self.service_url:
            raise WeatherProviderError("Weather service URL is not configured.")

        target_url = self.build_url(latitude, longitude)
        req = urllib.request.Request(
            url=target_url,
            headers={"User-Agent": "DisasterResponseAgent-WeatherClient/1.0"}
        )

        kwargs = {}
        if self.timeout is not None:
            kwargs["timeout"] = self.timeout

        try:
            with urllib.request.urlopen(req, **kwargs) as response:
                status_code = response.getcode()
                if status_code != 200:
                    raise WeatherProviderError(
                        f"External weather service returned HTTP status {status_code}.",
                        status_code=status_code
                    )
                raw_bytes = response.read()
                try:
                    return json.loads(raw_bytes.decode("utf-8"))
                except Exception as e:
                    raise WeatherProviderError(f"Failed to parse provider JSON response: {str(e)}")

        except urllib.error.HTTPError as e:
            raise WeatherProviderError(f"HTTP Error querying weather provider: {e.code} {e.reason}", status_code=e.code)
        except urllib.error.URLError as e:
            raise WeatherProviderError(f"Network error connecting to weather provider: {str(e.reason)}")
        except (socket.timeout, TimeoutError):
            raise WeatherProviderError(f"Timeout of {self.timeout}s exceeded while connecting to weather provider.")
        except WeatherProviderError:
            raise
        except Exception as e:
            raise WeatherProviderError(f"Unexpected error communicating with weather provider: {str(e)}")
