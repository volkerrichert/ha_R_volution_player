"""API class for communication with the R Volution Player via HTTP."""
import asyncio
import logging
import aiohttp
import async_timeout
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional, Union, Tuple

from custom_components.r_volution_player.const import IR_CODES

_LOGGER = logging.getLogger(__name__)

class RVolutionPlayerClient:
    """Class for communication with the R Volution Player via HTTP."""

    def __init__(self, host: str, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the API client."""
        self._host = host
        self._session = session or aiohttp.ClientSession()
        self._base_url = f"http://{host}/cgi-bin/do"

    async def close(self) -> None:
        """Close the session."""
        if self._session:
            await self._session.close()

    async def get_status(self) -> Dict[str, Any]:
        """Get the player status."""
        try:
            with async_timeout.timeout(10):
                response = await self._session.get(f"{self._base_url}", params={'cmd': 'status'})
                response.raise_for_status()
                xml_text = await response.text()
                result, _ = self._parse_xml_response(xml_text)
                return result
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.error("Error retrieving player status: %s", err)
            return {}
        except ET.ParseError as err:
            _LOGGER.error("Error parsing XML response: %s", err)
            return {}

    async def play(self) -> bool:
        """Start playback."""
        return await self._send_ip_command("play")

    async def pause(self) -> bool:
        """Pause playback."""
        return await self._send_ip_command("pause")

    async def stop(self) -> bool:
        """Stop playback."""
        return await self._send_ip_command("stop")

    async def next_track(self) -> bool:
        """Skip to the next track."""
        return await self._send_ip_command("next")

    async def previous_track(self) -> bool:
        """Go back to the previous track."""
        return await self._send_ip_command("prev")

    async def set_volume(self, volume: int) -> bool:
        """Set volume (0-100)."""
        return await self._send_ip_command("volume", {"level": volume})

    async def mute(self, mute: bool = True) -> bool:
        """Toggle mute on or off."""
        return await self._send_ip_command("mute")

    async def _send_ip_command(self, command: str, params: Dict[str, Any] = None) -> bool:
        """Send a command to the player."""
        try:
            with async_timeout.timeout(10):
                url = f"{self._base_url}"
                query_params = {"cmd": "ir_code"}

                if command in IR_CODES:
                    query_params["ir_code"] = IR_CODES[command]
                else:
                    query_params["ir_code"] = command

                if params:
                    query_params.update(params)

                response = await self._session.get(url, params=query_params)
                response.raise_for_status()

                # Parse response to check success
                xml_text = await response.text()
                _, success = self._parse_xml_response(xml_text)
                return success

        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.error("Error sending command %s: %s", command, err)
            return False

    def _parse_xml_response(self, xml_text: str) -> Tuple[Dict[str, Any], bool]:
        """Parse the XML response and extract data and success status."""
        try:
            root = ET.fromstring(xml_text)
            result = {}
            success = True

            # Check if the player response is valid
            if root.tag != 'command_result':
                return {}, False

            # Extract parameters from XML
            for param in root.findall('.//param'):
                name = param.get('name')
                value = param.get('value')

                if name and value:
                    # Special parameters for status
                    if name == "player_state":
                        result['state'] = value
                    elif name == "playback_volume":
                        try:
                            result['volume'] = int(value)
                        except (ValueError, TypeError):
                            result['volume'] = 0
                    elif name == "playback_mute":
                        result['muted'] = value == "1"
                    elif name == "product_name":
                        result['product_name'] = value
                    # Error detection
                    elif name == "error" and value:
                        _LOGGER.error("Player error: %s", value)
                        success = False
                    # Generic storage for all other parameters
                    else:
                        result[name] = value

            return result, success
        except Exception as err:
            _LOGGER.error("Error parsing XML response: %s", err)
            return {}, False
