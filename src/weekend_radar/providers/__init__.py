"""Provider boundaries for Weekend Radar."""

from weekend_radar.config import AppSettings
from weekend_radar.providers.amadeus import AmadeusFlightProvider
from weekend_radar.providers.base import FlightProvider, ProviderConfigurationError
from weekend_radar.providers.mock import MockFlightProvider


def build_provider(provider_name: str, settings: AppSettings) -> FlightProvider:
    """Instantiate the configured provider with any required local credentials."""

    if provider_name == "mock":
        return MockFlightProvider()

    if provider_name == "amadeus":
        if not settings.amadeus_api_key or not settings.amadeus_api_secret:
            raise ProviderConfigurationError(
                "Provider 'amadeus' requires AMADEUS_API_KEY and AMADEUS_API_SECRET."
            )
        return AmadeusFlightProvider(
            api_key=settings.amadeus_api_key,
            api_secret=settings.amadeus_api_secret,
        )

    raise ProviderConfigurationError(f"Unsupported provider '{provider_name}'.")


__all__ = [
    "AmadeusFlightProvider",
    "FlightProvider",
    "MockFlightProvider",
    "build_provider",
]
