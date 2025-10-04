"""API class for communication with the R Volution Player via HTTP."""

import logging
from typing import Any, Optional
import aiohttp
import async_timeout
import xml.etree.ElementTree as ET
from .const import IR_CODES

_LOGGER = logging.getLogger(__name__)


class RVolutionPlayerClient:
    """Class for communication with the R Volution Player via HTTP."""

    def __init__(self, host: str, session: Optional[aiohttp.ClientSession | None] = None):
        """Initialize the API client."""
        self._host = host
        self._session = session  # Do not create session here
        self._base_url = f"http://{host}/cgi-bin/do"
        self._data = None

    async def close(self) -> None:
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def async_update_status(self) -> dict[str, Any]:
        """Asynchronously retrieves the player status from the remote server."""

        try:
            async with async_timeout.timeout(10), aiohttp.ClientSession() as session:
                response = await session.get(
                    f"{self._base_url}",
                    params={"cmd": "status", "result_syntax": "json"},
                )
                response.raise_for_status()
                self._data = await response.json()
                return self._data
        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.info("Error retrieving player status: %s", err)
            return {}
        except ET.ParseError as err:
            _LOGGER.error("Error parsing XML response: %s", err)
            return {}

    async def async_product_name(self) -> str:
        """Asynchronously retrieves the product name of the player.

        Returns:
            str: The product name of the player.

        """
        if self._data is None:
            await self.async_update_status()

        return self._data["product_name"]

    async def async_get_serial_number(self) -> str:
        """Asynchronously retrieves the serial number of the player.

        Returns:
            str: The serial number of the player.

        """
        if self._data is None:
            await self.async_update_status()

        return self._data["serial_number"]

    async def async_get_firmware_version(self) -> str:
        """Asynchronously retrieves the firmware version of the player.

        Returns:
            str: The firmware version of the player.

        """
        if self._data is None:
            await self.async_update_status()

        return self._data["firmware_version"]

    async def async_get_product_id(self) -> str | None:
        """Asynchronously retrieves the product ID of the player.

        Returns:
            str: The product ID of the player.

        """
        if self._data is None:
            await self.async_update_status()

        return self._data.get("product_id", None)

    async def async_play(self) -> bool:
        """Start playback."""
        return await self._send_ip_command(IR_CODES["play"])

    async def async_pause(self) -> bool:
        """Pause playback."""
        return await self._send_ip_command("pause")

    async def async_stop(self) -> bool:
        """Stop playback."""
        return await self._send_ip_command("stop")

    async def async_next_track(self) -> bool:
        """Skip to the next track."""
        return await self._send_ip_command("next")

    async def async_previous_track(self) -> bool:
        """Go back to the previous track."""
        return await self._send_ip_command("prev")

    async def async_mute(self, mute: bool = True) -> bool:
        """Toggle mute on or off."""
        return await self._send_ip_command("mute")

    async def async_volume_up(self, mute: bool = True) -> bool:
        """Increase the volume."""
        return await self._send_ip_command("volume_up")

    async def async_volume_down(self, mute: bool = True) -> bool:
        """Decrease the volume."""
        return await self._send_ip_command("volume_down")

    async def async_set_volume(self, volume: int) -> bool:
        """Set the volume to a specific level (0-100)."""
        try:
            async with async_timeout.timeout(10), aiohttp.ClientSession() as session:
                url = self._base_url
                query_params = {
                    "cmd": "set_playback_state",
                    "volume": str(volume),
                    "result_syntax": "json",
                }

                response = await session.get(url, params=query_params)
                response.raise_for_status()

                # Parse response to check success
                self._data = await response.json()
                return self._data.get("command_status", False) == "ok"

        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Error setting volume to %s: %s", volume, err)
            return False

    async def async_seek(self, position: int) -> bool:
        """Seek to a specific position in seconds."""
        try:
            async with async_timeout.timeout(10), aiohttp.ClientSession() as session:
                url = self._base_url
                query_params = {
                    "cmd": "set_playback_state",
                    "position": str(position),
                    "result_syntax": "json",
                }

                response = await session.get(url, params=query_params)
                response.raise_for_status()

                # Parse response to check success
                self._data = await response.json()
                return self._data.get("command_status", False) == "ok"

        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Error seeking to position %s: %s", position, err)
            return False

    async def async_power_off(self) -> bool:
        """Turn off the player."""
        return await self._send_ip_command("power_off")

    async def _send_ip_command(
        self, command: str, params: dict[str, Any] = None
    ) -> bool:
        """Send a command to the player."""
        try:
            async with async_timeout.timeout(10), aiohttp.ClientSession() as session:
                url = self._base_url
                query_params = {"cmd": "ir_code", "result_syntax": "json"}
                query_params["ir_code"] = IR_CODES.get(command, command)

                if params:
                    query_params.update(params)

                response = await session.get(url, params=query_params)
                response.raise_for_status()

                # Parse response to check success
                self._data = await response.json()
                return self._data.get("command_status", False) == "ok"

        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Error sending command %s: %s", command, err)
            return False

    async def async_select_audio_track(self, track_id: str) -> bool:
        """Select a specific audio track by ID."""
        try:
            async with async_timeout.timeout(10), aiohttp.ClientSession() as session:
                url = self._base_url
                query_params = {
                    "cmd": "set_playback_state",
                    "audio_track": track_id,
                    "result_syntax": "json",
                }

                response = await session.get(url, params=query_params)
                response.raise_for_status()

                # Parse response to check success
                self._data = await response.json()
                return self._data.get("command_status", False) == "ok"

        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Error selecting audio track %s: %s", track_id, err)
            return False

    async def async_select_subtitle_track(self, track_id: str) -> bool:
        """Select a specific subtitle track by ID."""
        try:
            async with async_timeout.timeout(10), aiohttp.ClientSession() as session:
                url = self._base_url
                query_params = {
                    "cmd": "set_playback_state",
                    "subtitles_track": track_id,
                    "result_syntax": "json",
                }

                response = await session.get(url, params=query_params)
                response.raise_for_status()

                # Parse response to check success
                self._data = await response.json()
                return self._data.get("command_status", False) == "ok"

        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Error selecting audio track %s: %s", track_id, err)
            return False

    async def async_set_playback_speed(
        self, speed: int
    ) -> bool:  # Korrigiert: "speed" statt "spped"
        """Set playback speed."""
        try:
            async with async_timeout.timeout(10), aiohttp.ClientSession() as session:
                url = self._base_url
                query_params = {
                    "cmd": "set_playback_state",
                    "speed": speed,
                    "result_syntax": "json",
                }

                response = await session.get(url, params=query_params)
                response.raise_for_status()

                # Parse response to check success
                self._data = await response.json()
                return self._data.get("command_status", False) == "ok"

        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error(
                "Error setting playback speed to %s: %s", speed, err
            )  # Korrigiert: "speed" statt "track_id"
            return False


class RVolutionCollectionClient:
    """Class for communication with the R Volution Collection via HTTP."""

    def __init__(
        self,
        username: str,
        password: str,
        apiKey: str,
        session: Optional[aiohttp.ClientSession | None] = None,
    ):
        """Initialize the API client."""
        self._username = username
        self._password = password
        self._apiKey = apiKey
        self._session: aiohttp.ClientSession | None = session if session else None

    async def async_auth(self):
        """Authenticate with the R Volution Collection API."""

        session = await self.async_get_session()
        response = await session.post(
            "Auth",
            json={
                "Email": self._username,
                "Password": self._password,
                "ApiKey": self._apiKey,
            },
            ssl=False,
        )

        result = await response.json()
        self._auth_key = result.get("Key", None)
        if not self._auth_key:
            _LOGGER.error("Authentication failed, no AuthKey returned.")
            return None

        # Extract collections with Collection as key and Alias as value
        self._collections = {}
        for collection_info in result.get("CollectionInfos", []):
            collection_id = collection_info.get("Collection")
            alias = collection_info.get("Alias")
            if collection_id and alias:
                self._collections[collection_id] = alias

        return self

    def get_collections(self) -> dict[str, str]:
        """Get the collections."""
        if not self._collections:
            return {}

        return self._collections

    def get_collection(self, collection_id: str) -> str | None:
        """Get a specific collection by ID."""
        return self._collections.get(collection_id, None)

    async def async_get_menu(
        self, collection_id: str, name: str
    ) -> dict[str, Any] | None:
        """Get a specific module from the collection."""

        session = await self.async_get_session()
        try:
            with async_timeout.timeout(10):
                response = await session.post(
                    "Menu",
                    json={
                        "AuthKey": self._auth_key,
                        "Collection": collection_id,
                        "ByName": name,
                        "Type": "Menu",
                        "IsParentalControlActive": False,
                        "ApiKey": self._apiKey,
                    },
                    ssl=False,
                )

            decoded: dict[str, Any] = await response.json()
            return decoded.get("Menu", None)
        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Error retrieving menu %s: %s", name, err)
            return None

    async def async_get_items(
        self, collection_id: str, id: str
    ) -> dict[str, Any] | None:
        """Get a specific module from the collection."""

        session = await self.async_get_session()
        try:
            with async_timeout.timeout(10):
                response = await session.post(
                    "Menu",
                    json={
                        "AuthKey": self._auth_key,
                        "Collection": collection_id,
                        "ById": id,
                        "Type": "Item",
                        "IsParentalControlActive": False,
                        "ApiKey": self._apiKey,
                    },
                    ssl=False,
                )

            decoded: dict[str, Any] = await response.json()
            return decoded.get("Menu", None)
        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Error retrieving items %s: %s", id, err)
            return None

    async def async_get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None:
            try:
                async with (
                    aiohttp.ClientSession() as session,
                    session.get(
                        "https://rvolutiontoolsapi.azurewebsites.net/Swagger/GetApiEndPoint",
                        verify_ssl=False,
                    ) as resp,
                ):
                    result = await resp.json()
                    self._base_url = result["ApiUrl"]
                    await session.close()
                    self._session = aiohttp.ClientSession(base_url=self._base_url)
            except (TimeoutError, aiohttp.ClientError) as err:
                _LOGGER.error("Error getting base url: %s", err)
                raise ValueError(f"Error getting base url: {err}") from err

        return self._session

    async def async_get_collections(self) -> dict[str, Any]:
        """Get the R Volution Collection."""
        session = await self.async_get_session()
        assert self._base_url, "Base URL is not set."

        try:
            with async_timeout.timeout(10):
                response = await session.get(
                    f"{self._base_url}/api/Collection",
                    params={
                        "username": self._username,
                        "password": self._password,
                        "apiKey": self._apiKey,
                    },
                    ssl=False,
                )
                response.raise_for_status()
                return await response.json()

        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Error retrieving collection: %s", err)
            return {}

    async def close(self) -> None:
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None


class RVideoClient:
    """Class for communication with the R Volution Video API."""

    def __init__(self, host: str, session: Optional[aiohttp.ClientSession | None] = None):
        """Initialize the API client."""

        self._host = host
        self._session = session  # Do not create session here
        self._base_url = f"http://{host}:8990"

    async def async_get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(base_url=self._base_url)
        return self._session

    async def close(self) -> None:
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def async_start_video(self, media_id: str) -> None:
        """Start the video client and fetch the base URL."""

        try:
            async with (
                async_timeout.timeout(10),
                await self.async_get_session() as session,
            ):
                resp = await session.post(
                    "/StartVideo", json={"MediaId": media_id}, verify_ssl=False
                )
                result = await resp.json(content_type=None)
                if result.get("ErrorCode") != "None":
                    raise ValueError(
                        f"Error starting video client: {result.get('ErrorMessage', 'Unknown error')}"
                    )

        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Error starting video client: %s", err)
            raise ValueError(f"Error starting video client: {err}") from err

    async def async_get_media_info(self) -> dict[str, Any]:
        """Get the last media info from the R Video API."""
        try:
            async with (
                async_timeout.timeout(10),
                await self.async_get_session() as session,
            ):
                resp = await session.get("/LastMedia", verify_ssl=False)
                result = await resp.json(content_type=None)
                return (
                    result.get("Media", {}) if result.get("ErrorCode") == "None" else {}
                )

        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Error retrieving last media info: %s", err)
            return {}
