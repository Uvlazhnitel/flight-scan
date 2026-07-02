"""Amadeus Self-Service flight provider integration."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation

import httpx

from weekend_radar.models import Destination, FlightOffer, WeekendWindow
from weekend_radar.providers.base import ProviderError

TOKEN_PATH = "/v1/security/oauth2/token"
FLIGHT_OFFERS_PATH = "/v2/shopping/flight-offers"


class AmadeusFlightProvider:
    """Fetch real flight offers from the Amadeus Self-Service API."""

    provider_name = "amadeus"

    def __init__(
        self,
        *,
        api_key: str,
        api_secret: str,
        base_url: str = "https://test.api.amadeus.com",
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport
        self.now_provider = now_provider or (lambda: datetime.now(UTC))
        self.logger = logging.getLogger("weekend_radar.providers.amadeus")
        self._access_token: str | None = None
        self._access_token_expires_at: datetime | None = None

    async def search_weekend_flights(
        self,
        origin: str,
        destination: Destination,
        weekend_window: WeekendWindow,
    ) -> list[FlightOffer]:
        """Search round-trip flight offers for one destination and one weekend window."""

        checked_at = self.now_provider()
        token = await self._get_access_token()
        request_params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination.code,
            "departureDate": weekend_window.depart_date.isoformat(),
            "returnDate": weekend_window.return_date.isoformat(),
            "adults": "1",
            "max": "20",
        }

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            transport=self.transport,
        ) as client:
            response = await self._request_with_retry(
                client,
                "GET",
                FLIGHT_OFFERS_PATH,
                headers={"Authorization": f"Bearer {token}"},
                params=request_params,
            )

        payload = response.json()
        offers: list[FlightOffer] = []
        skipped_malformed = 0
        skipped_non_eur = 0

        for item in payload.get("data", []):
            try:
                offer = self._normalize_offer(
                    item,
                    origin=origin,
                    destination_code=destination.code,
                    checked_at=checked_at,
                )
            except ValueError:
                skipped_malformed += 1
                continue

            if offer is None:
                skipped_non_eur += 1
                continue

            offers.append(offer)

        if skipped_malformed:
            self.logger.warning(
                "Skipped %s malformed Amadeus offers for %s -> %s",
                skipped_malformed,
                origin,
                destination.code,
            )
        if skipped_non_eur:
            self.logger.info(
                "Skipped %s non-EUR Amadeus offers for %s -> %s",
                skipped_non_eur,
                origin,
                destination.code,
            )

        return offers

    async def _get_access_token(self) -> str:
        """Reuse a cached bearer token or fetch a fresh one."""

        now = self.now_provider()
        if (
            self._access_token is not None
            and self._access_token_expires_at is not None
            and now < self._access_token_expires_at
        ):
            return self._access_token

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            transport=self.transport,
        ) as client:
            response = await self._request_with_retry(
                client,
                "POST",
                TOKEN_PATH,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.api_key,
                    "client_secret": self.api_secret,
                },
            )

        payload = response.json()
        access_token = payload.get("access_token")
        expires_in = payload.get("expires_in")
        if not isinstance(access_token, str) or not access_token:
            raise ProviderError("Amadeus token response did not include a usable access token.")
        if not isinstance(expires_in, int):
            raise ProviderError("Amadeus token response did not include a valid expires_in value.")

        self._access_token = access_token
        self._access_token_expires_at = now + timedelta(seconds=max(expires_in - 30, 1))
        return access_token

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        method: str,
        path: str,
        **kwargs: object,
    ) -> httpx.Response:
        """Perform one safe retry for transient request failures."""

        last_error: Exception | None = None

        for attempt in range(2):
            try:
                response = await client.request(method, path, **kwargs)
            except httpx.RequestError as exc:
                last_error = exc
                if attempt == 0:
                    await asyncio.sleep(0.1)
                    continue
                raise ProviderError(f"Amadeus request failed: {exc}") from exc

            if response.status_code >= 500:
                last_error = ProviderError(
                    f"Amadeus returned HTTP {response.status_code} for {path}."
                )
                if attempt == 0:
                    await asyncio.sleep(0.1)
                    continue
                raise last_error

            if response.status_code >= 400:
                raise ProviderError(
                    f"Amadeus returned HTTP {response.status_code}: {response.text}"
                )

            return response

        if last_error is None:
            raise ProviderError("Amadeus request failed for an unknown reason.")
        raise last_error

    def _normalize_offer(
        self,
        item: dict[str, object],
        *,
        origin: str,
        destination_code: str,
        checked_at: datetime,
    ) -> FlightOffer | None:
        """Convert one Amadeus response item into the internal offer model."""

        if not isinstance(item, dict):
            raise ValueError("offer must be an object")

        price = item.get("price")
        itineraries = item.get("itineraries")
        if not isinstance(price, dict) or not isinstance(itineraries, list) or len(itineraries) < 2:
            raise ValueError("offer is missing price or round-trip itineraries")

        currency = price.get("currency")
        total = price.get("total")
        if currency != "EUR":
            return None
        if not isinstance(total, str):
            raise ValueError("offer total price is missing")

        try:
            price_eur = int(Decimal(total).quantize(Decimal("1")))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("offer total price is invalid") from exc

        outbound = self._extract_itinerary(itineraries[0])
        inbound = self._extract_itinerary(itineraries[1])
        airline = self._extract_airline(item, outbound["segments"], inbound["segments"])
        total_stops = (len(outbound["segments"]) - 1) + (len(inbound["segments"]) - 1)

        return FlightOffer(
            provider=self.provider_name,
            origin=origin,
            destination=destination_code,
            depart_at=outbound["depart_at"],
            arrive_at=outbound["arrive_at"],
            return_depart_at=inbound["depart_at"],
            return_arrive_at=inbound["arrive_at"],
            price_eur=price_eur,
            currency="EUR",
            airline=airline,
            stops=total_stops,
            booking_url=None,
            checked_at=checked_at,
        )

    def _extract_itinerary(self, itinerary: object) -> dict[str, object]:
        """Extract the first departure, last arrival, and full segment list for one leg."""

        if not isinstance(itinerary, dict):
            raise ValueError("itinerary must be an object")

        segments = itinerary.get("segments")
        if not isinstance(segments, list) or not segments:
            raise ValueError("itinerary must include segments")

        first_segment = segments[0]
        last_segment = segments[-1]
        if not isinstance(first_segment, dict) or not isinstance(last_segment, dict):
            raise ValueError("segments must be objects")

        departure = first_segment.get("departure")
        arrival = last_segment.get("arrival")
        if not isinstance(departure, dict) or not isinstance(arrival, dict):
            raise ValueError("segment endpoints are missing")

        depart_at_raw = departure.get("at")
        arrive_at_raw = arrival.get("at")
        if not isinstance(depart_at_raw, str) or not isinstance(arrive_at_raw, str):
            raise ValueError("segment timestamps are missing")

        try:
            depart_at = datetime.fromisoformat(depart_at_raw)
            arrive_at = datetime.fromisoformat(arrive_at_raw)
        except ValueError as exc:
            raise ValueError("segment timestamps are invalid") from exc

        return {
            "depart_at": depart_at,
            "arrive_at": arrive_at,
            "segments": segments,
        }

    def _extract_airline(
        self,
        item: dict[str, object],
        outbound_segments: list[object],
        inbound_segments: list[object],
    ) -> str | None:
        """Prefer validating carrier code, then first segment carrier code."""

        validating_codes = item.get("validatingAirlineCodes")
        if isinstance(validating_codes, list) and validating_codes:
            first_code = validating_codes[0]
            if isinstance(first_code, str) and first_code:
                return first_code

        for segment in [*outbound_segments, *inbound_segments]:
            if isinstance(segment, dict):
                carrier_code = segment.get("carrierCode")
                if isinstance(carrier_code, str) and carrier_code:
                    return carrier_code

        return None
