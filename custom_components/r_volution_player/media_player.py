"""Media Player-Implementierung für den R Volution Player."""
import logging
import voluptuous as vol
from typing import Any, Dict, List, Optional

from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    SUPPORT_PLAY,
    SUPPORT_PAUSE,
    SUPPORT_STOP,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_BROWSE_MEDIA,
    MediaPlayerEntityFeature
)
from homeassistant.const import (
    STATE_IDLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_OFF
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RVolutionPlayerClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Richte den R Volution Player aus einem Konfigurationseintrag ein."""
    host = config_entry.data["host"]
    session = async_get_clientsession(hass)

    # Erstelle die Entität
    player = RVolutionPlayer(host, session, config_entry.entry_id)

    # Initialisiere API-Client
    hass.data[DOMAIN][config_entry.entry_id] = player

    async_add_entities([player], True)

class RVolutionPlayer(MediaPlayerEntity):
    """Repräsentation des R Volution Players."""

    def __init__(self, host: str, session, entry_id: str):
        """Initialisiere den Player."""
        self._host = host
        self._entry_id = entry_id
        self._name = f"R Volution Player ({host})"
        self._state = None
        self._volume = 0
        self._attr_is_volume_muted = False
        self._api = RVolutionPlayerClient(host, session)
        self._product_name = None
        self._player_state = None

    @property
    def name(self):
        """Name des Geräts."""
        if self._product_name:
            return self._product_name
        return self._name

    @property
    def state(self):
        """Zustand des Players."""
        if self._player_state == "off":
            return STATE_OFF
        elif self._player_state == "playing":
            return STATE_PLAYING
        elif self._player_state == "paused":
            return STATE_PAUSED
        elif self._player_state == "navigator":
            return STATE_IDLE
        else:
            return STATE_OFF

    @property
    def volume_level(self):
        """Lautstärkepegel des Players (0..1)."""
        if self._volume is not None:
            return self._volume / 100
        return None

    @property
    def is_volume_muted(self):
        """Gibt an, ob der Player stummgeschaltet ist."""
        return self._muted

    @property
    def supported_features(self):
        """Flag unterstützte Player-Features."""
        return (
            MediaPlayerEntityFeature.PLAY_MEDIA |
            MediaPlayerEntityFeature.PAUSE |
            MediaPlayerEntityFeature.STOP |
            MediaPlayerEntityFeature.NEXT_TRACK |
            MediaPlayerEntityFeature.PREVIOUS_TRACK |
            MediaPlayerEntityFeature.VOLUME_STEP |
            MediaPlayerEntityFeature.VOLUME_MUTE |
            MediaPlayerEntityFeature.BROWSE_MEDIA |
            MediaPlayerEntityFeature.SEEK
        )

    async def async_update(self):
        """Aktualisiere die Player-Daten."""
        try:
            status = await self._api.get_status()

            if "state" in status:
                self._player_state = status["state"]

            if "volume" in status:
                self._volume = status["volume"]

            if "muted" in status:
                self._muted = status["muted"]

            if "product_name" in status:
                self._product_name = status["product_name"]

        except Exception as err:
            _LOGGER.error("Fehler beim Aktualisieren des Players: %s", err)

    async def async_play_media(self, media_type, media_id, **kwargs):
        """Spiele die angegebenen Medien ab."""
        # Implementiere diese Methode, falls dein Player das Abspielen von bestimmten Medien unterstützt
        pass

    async def async_media_play(self):
        """Sende Wiedergabebefehl."""
        await self._api.play()

    async def async_media_pause(self):
        """Sende Pausebefehl."""
        await self._api.pause()

    async def async_media_stop(self):
        """Sende Stoppbefehl."""
        await self._api.stop()

    async def async_media_next_track(self):
        """Sende nächster Titel-Befehl."""
        await self._api.next_track()

    async def async_media_previous_track(self):
        """Sende vorheriger Titel-Befehl."""
        await self._api.previous_track()

    async def async_set_volume_level(self, volume):
        """Setze Lautstärke (0..1)."""
        vol_int = int(volume * 100)
        await self._api.set_volume(vol_int)

    async def async_mute_volume(self, mute):
        """Stumm/Ton-Befehl."""
        await self._api.mute(mute)
        self._muted = mute
