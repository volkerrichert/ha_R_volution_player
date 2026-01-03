"""Media Player implementation for the R Volution Player."""
import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
import ssl
from collections.abc import Awaitable, Callable, Coroutine
from contextlib import suppress
from http import HTTPStatus
from os import getcwd
from typing import Any, Concatenate

import aiofiles
import async_timeout

import homeassistant
from homeassistant.components.media_player import (
    BrowseMedia,
    MediaClass,
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityDescription,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    RepeatMode,
    SearchMedia,
    SearchMediaQuery,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import AFTER_REQUEST_SLEEP, DOMAIN, DEFAULT_COLLECTION_MENU
from .coordinator import RVolutionCoordinator

_LOGGER = logging.getLogger(__name__)

# Timeout and delay constants
TIMEOUT_IMAGE_FETCH = 10  # Seconds to wait for image fetch
DELAY_BEFORE_VIDEO_START = 1  # Seconds to wait before starting video
DELAY_BEFORE_RETRY = 2  # Seconds to wait before retry after error
MAX_SEARCH_RESULTS = 50  # Maximum number of search results to return

# Playback state string values
BOOLEAN_TRUE = "1"
BOOLEAN_FALSE = "0"
PLAYER_STATE_NAVIGATOR = "navigator"
PLAYER_STATE_FILE_PLAYBACK = "file_playback"
PLAYBACK_STATE_PLAYING = "playing"
PLAYBACK_STATE_PAUSED = "paused"
PLAYBACK_STATE_BUFFERING = "buffering"
PLAYBACK_STATE_INITIALIZING = "initializing"

# Repeat mode values
REPEAT_MODE_OFF = "0"
REPEAT_MODE_ALL = "1"
REPEAT_MODE_ONE = "2"

# Volume constants
DEFAULT_VOLUME_LEVEL = 1.0
DEFAULT_VOLUME_STEP = 0.04
VOLUME_PERCENTAGE_FACTOR = 100.0


def async_refresh_after[T: RVolutionPlayer, **P](
    func: Callable[Concatenate[T, P], Awaitable[None]],
) -> Callable[Concatenate[T, P], Coroutine[Any, Any, None]]:
    """Delay status update until after method execution."""

    async def _async_wrap(self: T, *args: P.args, **kwargs: P.kwargs) -> None:
        await func(self, *args, **kwargs)
        await asyncio.sleep(AFTER_REQUEST_SLEEP)
        await self.coordinator.async_refresh()

    return _async_wrap


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize media player Platform."""
    assert isinstance(config_entry.unique_id, str)
    coordinator: RVolutionCoordinator = hass.data[DOMAIN][config_entry.unique_id]
    player = RVolutionPlayer(
        coordinator,
        RVolutionPlayerEntityDescription(
            key="media_player",
            translation_key="system-media_player-percent",
            icon="mdi:media-player",
        ),
        config_entry.entry_id,
    )

    await player.async_setup()
    async_add_entities([player], True)


@dataclass
class RVolutionPlayerEntityDescription(MediaPlayerEntityDescription):
    """Description of the R Volution Player entity.
    
    Extends MediaPlayerEntityDescription for potential future custom attributes.
    """
    # Custom attributes can be added here in the future
    # Example: custom_attribute: str | None = None


class RVolutionPlayer(CoordinatorEntity, MediaPlayerEntity):
    """Representation of the R Volution Player."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = MediaPlayerDeviceClass.RECEIVER

    def __init__(
        self,
        coordinator: RVolutionCoordinator,
        description: RVolutionPlayerEntityDescription,
        entry_id: str,
        device_info: DeviceInfo | None = None,
    ) -> None:
        """Initialize the R Volution Player entity."""

        super().__init__(coordinator)

        self.hass = coordinator.hass
        self.coordinator = coordinator
        self.entity_description: RVolutionPlayerEntityDescription = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

        self._api = coordinator.api
        self._collection_client = coordinator.collection_client
        self._rvideo_client = coordinator.rvideo_client

        self._attr_device_info = coordinator.device_info
        self._entry_id = entry_id
        self._host = coordinator.host
        self._attr_volume_level = DEFAULT_VOLUME_LEVEL
        self._attr_volume_step = DEFAULT_VOLUME_STEP
        self._attr_is_volume_muted = False
        self._product_name = self.coordinator._model
        self._player_state = None
        self._product_id = self.coordinator._model_id
        self._serial_number = self.coordinator._serial_number
        self._attr_state = MediaPlayerState.OFF
        self._attr_supported_features = None
        if device_info is not None:
            self._attr_device_info = device_info
        else:
            self._attr_device_info = self.coordinator.device_info

        self._attr_name = f"{self._product_name} ({self._host})"

        self._update_data_from_coordinator()

    async def async_setup(self) -> None:
        """Set up the entity and load translations."""
        self._translations = await async_get_translations(
            self.hass, self.hass.config.language, "entity_component", {DOMAIN}
        )

    def translate(self, key: str, default: str | None = None) -> str:
        """Translate a given key using the loaded translations."""
        return self._translations.get(
            f"component.{DOMAIN}.entity_component._.{key.lower()}",
            default if default is not None else key,
        )

    def _clear_media_attributes(self) -> None:
        """Clear all media-related attributes."""
        self._attr_media_duration = None
        self._attr_media_position = None
        self._attr_media_position_updated_at = None
        self._attr_media_title = None
        self._attr_media_content_id = None
        self._attr_media_image_url = None
        self._attr_media_episode = None
        self._attr_media_series_title = None
        self._attr_media_season = None
        self._attr_media_content_type = None
        self._attr_sound_mode_list = None
        self._attr_sound_mode = None

    def _update_media_info(self, data: dict) -> None:
        """Update media information attributes from coordinator data."""
        media_info = self.coordinator.media_info
        
        # Update playback position and duration
        value = data.get("playback_duration", None)
        self._attr_media_duration = int(value) if value else None
        value = data.get("playback_position", None)
        self._attr_media_position = int(value) if value else None
        self._attr_media_position_updated_at = (
            homeassistant.util.dt.utcnow() if value else None
        )
        
        # Update media metadata
        self._attr_media_title = media_info.get("Title", None)
        self._attr_media_image_url = media_info.get(
            "BackgroundUrl", media_info.get("PosterUrl", None)
        )
        self._attr_media_episode = media_info.get("Episode", None)
        self._attr_media_series_title = media_info.get("TvShowName", None)
        self._attr_media_season = media_info.get("Season", None)
        
        # Determine and set media content type
        self._attr_media_content_type = self.coordinator.media_info.get("Type", None)
        if self._attr_media_content_type == "TVShowEpisode":
            self._attr_media_content_type = MediaType.TVSHOW
        elif self._attr_media_content_type == "Movie":
            self._attr_media_content_type = MediaType.MOVIE
        else:
            self._attr_media_content_type = None

    def _update_sound_modes(self, data: dict) -> None:
        """Update sound mode list and current sound mode from audio tracks."""
        if not (
            (technical_info := self.coordinator.media_info.get("TechnicalInfo", None))
            and (audio_tracks := technical_info.get("AudioTrackTechnicalInfos", None))
            and isinstance(audio_tracks, list)
            and len(audio_tracks) > 0
            and data.get("audio_track").isdigit()
        ):
            self._attr_sound_mode_list = None
            self._attr_sound_mode = None
            return

        # Create sound mode list from available audio tracks
        sound_modes = []
        for track in audio_tracks:
            format_commercial = track.get("FormatCommercial", "")
            language = track.get("Language", "")

            # Create a combined string: "FormatCommercial (Language)"
            if format_commercial and language:
                sound_mode = f"{format_commercial} ({language})"
            elif format_commercial:
                sound_mode = format_commercial
            elif language:
                sound_mode = language
            else:
                sound_mode = f"Track {track.get('Index', 'Unknown')}"

            sound_modes.append(sound_mode)

        self._attr_sound_mode_list = sound_modes if sound_modes else None
        
        # Set current sound mode based on active audio track
        if sound_modes:
            self._attr_sound_mode = sound_modes[int(data.get("audio_track"))]
        else:
            self._attr_sound_mode_list = None
            self._attr_sound_mode = None

    def _update_playback_controls(self, data: dict) -> None:
            """Update playback control attributes (shuffle, repeat, volume, mute)."""
            # Shuffle
            self._attr_shuffle = data.get("playback_shuffle", BOOLEAN_FALSE) == BOOLEAN_TRUE
            
            # Repeat mode
            match data.get("playback_repeat", REPEAT_MODE_OFF):
                case "0":
                    self._attr_repeat = RepeatMode.OFF
                case "1":
                    self._attr_repeat = RepeatMode.ALL
                case "2":
                    self._attr_repeat = RepeatMode.ONE
                case _:
                    self._attr_repeat = RepeatMode.OFF
            
            # Volume
            self._attr_is_volume_muted = data.get("playback_mute", BOOLEAN_FALSE) == BOOLEAN_TRUE
            self._attr_volume_level = (
                int(data.get("playback_volume", "100")) / VOLUME_PERCENTAGE_FACTOR
            )

    def _update_supported_features(self) -> None:
        """Calculate and set supported features based on current state."""
        self._attr_supported_features = (
            MediaPlayerEntityFeature.PLAY_MEDIA
            | MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.SEEK
            | MediaPlayerEntityFeature.REPEAT_SET
        )
        
        # Add browse media if collections are available
        if (
            self._collection_client
            and len(self._collection_client.get_collections()) > 0
        ):
            # TODO: Search seems to be unusable with custom API KEY
            self._attr_supported_features |= MediaPlayerEntityFeature.BROWSE_MEDIA | MediaPlayerEntityFeature.SEARCH_MEDIA
        
        # TODO: check how to find next / prev episode for TVShowEpisode
        # Add sound mode selection if audio tracks are available
        if self._attr_sound_mode_list and len(self._attr_sound_mode_list) > 1:
            self._attr_supported_features |= MediaPlayerEntityFeature.SELECT_SOUND_MODE

    def _update_data_from_coordinator(self) -> None:
        """Update the entity's attributes based on the coordinator's data."""
        if data := self.coordinator.data:
            if data.get("player_state", None) == PLAYER_STATE_FILE_PLAYBACK:
                self._update_media_info(data)
                self._update_sound_modes(data)
            else:
                self._clear_media_attributes()

            self._update_playback_controls(data)
            self._attr_state = self._get_player_state(data)
            self._update_supported_features()
        else:
            self._clear_media_attributes()
            self._attr_shuffle = None
            self._attr_repeat = RepeatMode.OFF
            self._attr_state = MediaPlayerState.OFF
            self._attr_supported_features = MediaPlayerEntityFeature(0)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        self._update_data_from_coordinator()
        self.async_write_ha_state()

    def _get_player_state(self, data: dict) -> MediaPlayerState | None:
        """Update the player's state based on the provided player state string."""

        player_state = data.get("player_state", None)
        playback_state = data.get("playback_state", None)
        if player_state == PLAYER_STATE_NAVIGATOR:
            return MediaPlayerState.IDLE
        elif player_state == PLAYER_STATE_FILE_PLAYBACK:
            if playback_state == PLAYBACK_STATE_PLAYING:
                return MediaPlayerState.PLAYING
            elif playback_state == PLAYBACK_STATE_PAUSED:
                return MediaPlayerState.PAUSED
            elif playback_state == PLAYBACK_STATE_BUFFERING or playback_state == PLAYBACK_STATE_INITIALIZING:
                return MediaPlayerState.BUFFERING
        else:
            return MediaPlayerState.IDLE

    def _get_icon_path(self, icon_path: str) -> Path:
        """Get the full path to a local icon file."""
        # Get the directory where this file (media_player.py) is located
        integration_dir = Path(__file__).parent
        return integration_dir / f"{icon_path}" / "icon.png"

    async def async_get_browse_image(
        self, media_content_type, media_content_id, media_image_id=None
    ):
        content = None
        match media_content_type:
            case MediaType.MOVIE:
                content = await self._async_fetch_image(
                    f"https://cdn.rvolution.com/pictures/480x720_100/{media_image_id}"
                )
            case MediaType.GENRE:
                icon_path = self._get_icon_path(media_image_id.lower())
                _LOGGER.warning("dir: %s", icon_path)
                try:
                    async with aiofiles.open(icon_path, 'rb') as file:
                        content = await file.read()
                        return content, 'image/png'
                except FileNotFoundError:
                    _LOGGER.warning("Icon file not found: %s", icon_path)
                    return None, None
                except Exception as e:
                    _LOGGER.error("Error loading icon file %s: %s", media_image_id, e)
                    return None, None
            case _:
                content = await self._async_fetch_image(
                    f"{self._collection_client._base_url}Picture?AuthKey={self.coordinator.collection_client._auth_key}&Collection={media_content_id}&Hash={media_image_id}&ApiKey={self.coordinator.apiKey}"
                )

        return content

    async def _async_fetch_image(self, url: str) -> tuple[bytes | None, str | None]:
        """Retrieve an image.

        R_volution uses self-signed / wrong certificates, thus we need to use an empty
        SSLContext to bypass validation errors if url starts with https.

        THX to "thecode" using a similar approach for WebOS TV:
        """
        content = None
        ssl_context = None
        if url.startswith("https"):
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        websession = async_get_clientsession(self.hass)
        with suppress(asyncio.TimeoutError), async_timeout.timeout(TIMEOUT_IMAGE_FETCH):
            response = await websession.get(url, ssl=ssl_context)
            if response.status == HTTPStatus.OK:
                content = await response.read()
                content_type = response.content_type

        if content is None:
            _LOGGER.warning("Error retrieving proxied image from %s", url)
            return None, None

        return content, content_type

    async def async_search_media(
            self,
            query: SearchMediaQuery,
        ) -> SearchMedia:
            """Search the media player."""

            return SearchMedia(result=[])
    
    async def async_browse_media(self, media_content_type=None, media_content_id=None):
        """Return a BrowseMedia object describing media sources."""

        if media_content_type is None or media_content_id is None:
            return await self._async_get_browse_media_root()
        else:
            match media_content_type:
                case MediaType.CHANNELS:
                    if "/" not in media_content_id:
                        return await self._async_get_browse_media_collection(
                            media_content_id
                        )
                    else:
                        action, collection_id, id = media_content_id.split("/", 2)
                        match action:
                            case "Home" | "StartMenu":
                                return await self._async_get_browse_media_menu(
                                    collection_id, type="Menu", id=id
                                )
                            case "StartMenuByName":
                                return await self._async_get_browse_media_menu(
                                    collection_id, type="Menu", name=id
                                )
                            case "StartCategory":
                                return await self._async_get_browse_media_menu(
                                    collection_id, type="Category", id=id
                                )
                            case _:
                                return []

                case MediaType.APP:
                    return await self._async_get_browse_media_collection(
                        media_content_id
                    )
                case MediaType.CHANNEL | MediaType.TVSHOW | MediaType.SEASON:
                    # Assuming media_content_id is in the format "collection_id/media_id"
                    action, collection_id, media_id = media_content_id.split("/", 2)
                    return await self._async_get_browse_media_menu(
                        collection_id, type="Item", id=media_id
                    )
                case MediaType.GENRE:
                    # Assuming media_content_id is in the format "collection_id/media_id"
                    _, collection_id, media_id = media_content_id.split("/", 2)
                    return await self._async_get_browse_media_category(
                        collection_id, media_id
                    )
                case _:
                    _LOGGER.error(
                        "Unsupported media content type: %s", media_content_type
                    )
                    return None

    async def _async_get_browse_media_root(self):
        """Return the root BrowseMedia object."""
        collections = (
            self._collection_client.get_collections()
            if self._collection_client
            else None
        )

        if not collections:
            _LOGGER.error("No collections found in the collection client.")
            return None

        if len(collections) == 1:
            return await self._async_get_browse_media_collection(
                next(iter(collections))
            )  # Get the first collection
        else:
            # If multiple collections, return a directory listing of collections
            children = [
                BrowseMedia(
                    title=title,
                    media_class=MediaClass.DIRECTORY,
                    media_content_id=id,
                    media_content_type=MediaType.CHANNELS,
                    can_play=False,
                    can_expand=True,
                    can_search=True,
                )
                for id, title in collections.items()
            ]

        return BrowseMedia(
            title=self.translate("Collections"),
            media_class=MediaClass.DIRECTORY,
            media_content_id="root",
            media_content_type=MediaType.CHANNELS,
            can_play=False,
            can_expand=True,
            can_search=True,
            children=children,
        )

    async def _async_get_browse_media_collection(self, collection_id):
        """Return a BrowseMedia object for a specific collection."""
        collection = self._collection_client.get_collection(collection_id)
        if not collection:
            _LOGGER.error("Collection not found: %s", collection_id)
            return None

        # modules = await self._collection_client.async_get_modules(collection_id)

        # Alternative implementation using modules (currently not used):
        # children = [
        #     BrowseMedia(
        #         title=f"{item.get("Text")}",
        #         media_class=MediaClass.DIRECTORY,
        #         media_content_id=f"{item.get("Action")}/{collection_id}/{item.get("Id")}",
        #         media_content_type=MediaType.CHANNELS,
        #         can_play=False,
        #         can_expand=True,
        #         can_search=True,
        #     )
        #     for item in modules
        # ]

        children = [
            BrowseMedia(
                title=self.translate(item["Title"]),
                media_class=MediaClass.DIRECTORY,
                media_content_id=f"StartMenuByName/{collection_id}/{item.get('ByName')}",
                media_content_type=MediaType.CHANNELS,
                can_play=False,
                can_expand=True,
                can_search=True,
            )
            for item in DEFAULT_COLLECTION_MENU
        ]

        return BrowseMedia(
            title=collection,
            media_class=MediaClass.DIRECTORY,
            media_content_id=collection_id,
            media_content_type=MediaType.APP,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_get_browse_media_menu(
        self, collection_id, type: str, id: str = None, name: str = None
    ):
        """
        Return a BrowseMedia object for a specific menu.

        Args:
            collection_id: The identifier of the collection to browse.
            type: The type of menu to retrieve.
            id: Optional identifier for the specific menu item.
            name: Optional name for the menu item.

        Returns:
            BrowseMedia: A BrowseMedia object containing the menu structure with:
                - Translated title from content
                - Media class set to DIRECTORY
                - Media content ID formatted as "{collection_id}/{id}"
                - Media content type set to CHANNELS
                - Can expand but cannot play directly
                - Children parsed from content buttons

        Raises:
            Any exceptions raised by _collection_client.async_get_menu() or
            _get_media_children() will propagate up.
        """
        content = await self._collection_client.async_get_menu(
            collection_id, type=type, id=id, name=name
        )
        children = self._get_media_children(collection_id, content.get("Buttons", []))

        return BrowseMedia(
            title=self.translate(content.get("Title", content.get("Name", "Unknown"))),
            media_class=MediaClass.DIRECTORY,
            media_content_id=f"{collection_id}/{id}",
            media_content_type=MediaType.CHANNELS,
            can_play=False,
            can_expand=True,
            children=children,
        )

    def _determine_media_properties(
        self, collection_id: str, type: str, media_image_id=None
    ) -> tuple[bool, bool, MediaClass, MediaType, str | None]:
        """Determine media properties based on the type."""
        media_class = MediaClass.MOVIE
        media_content_type = MediaType.MOVIE
        can_play = False
        can_expand = True
        thumbnail = None

        match type:
            case "Movie":
                media_class = MediaClass.MOVIE
                media_content_type = MediaType.MOVIE
                can_play = True
                can_expand = False
                thumbnail = (
                    self.get_browse_image_url(
                        media_content_type, collection_id, media_image_id
                    )
                    if media_image_id
                    else None
                )
            case "TVShow":
                media_class = MediaClass.TV_SHOW
                media_content_type = MediaType.TVSHOW
                thumbnail = (
                    self.get_browse_image_url(
                        media_content_type, collection_id, media_image_id
                    )
                    if media_image_id
                    else None
                )
            case "TVShowSeason":
                media_class = MediaClass.SEASON
                media_content_type = MediaType.SEASON
                thumbnail = (
                    self.get_browse_image_url(
                        media_content_type, collection_id, media_image_id
                    )
                    if media_image_id
                    else None
                )
            case "TVShowEpisode":
                media_class = MediaClass.EPISODE
                media_content_type = MediaType.EPISODE
                can_play = True
                can_expand = False
                thumbnail = (
                    self.get_browse_image_url(
                        media_content_type, collection_id, media_image_id
                    )
                    if media_image_id
                    else None
                )
            case "CustomGroup":
                media_class = MediaClass.DIRECTORY
                media_content_type = MediaType.CHANNEL
                thumbnail = (
                    self.get_browse_image_url(
                        media_content_type, collection_id, media_image_id
                    )
                    if media_image_id
                    else None
                )
            case "Category":
                media_class = MediaClass.DIRECTORY
                media_content_type = MediaType.GENRE
                thumbnail = (
                   self.get_browse_image_url(
                       media_content_type, collection_id, media_image_id
                   )
                    if media_image_id
                   else None
                )

        return can_play, can_expand, media_class, media_content_type, thumbnail

    def _get_media_children(
        self,
        collection_id: str,
        content: dict[str, Any],
    ) -> list[BrowseMedia]:
        """Get children for a specific media type and ID."""
        children = []

        for item in content:
            id = item.get("Id", "Unknown")
            media_image_id = item.get("Icon", None)
            text = item.get("Text", "Unknown")

            title = self.translate(text, text)
            can_play, can_expand, media_class, media_content_type, thumbnail = (
                self._determine_media_properties(
                    collection_id=collection_id,
                    media_image_id=media_image_id,
                    type=item.get("Type", "Unknown"),
                )
            )

            children.append(
                BrowseMedia(
                    title=title,
                    media_class=media_class,
                    media_content_id=f"{item.get('Type', 'Unknown')}/{collection_id}/{id}",
                    media_content_type=media_content_type,
                    can_play=can_play,
                    can_expand=can_expand,
                    thumbnail=thumbnail,
                    can_search=True,
                )
            )

        return children

    async def _async_get_browse_media_category(self, collection_id, media_id):
        """Return a BrowseMedia object for a category."""
        collection = self._collection_client.get_collection(collection_id)
        if not collection:
            _LOGGER.error("Collection not found: %s", collection_id)
            return None

        media_item = await self._collection_client.async_get_category(
            collection_id, media_id
        )
        return BrowseMedia(
            title=self.translate(
                media_item.get("Title", media_item.get("Name", "Unknown"))
            ),
            media_class=MediaClass.DIRECTORY,
            media_content_id=f"{collection_id}/{media_id}",
            media_content_type=MediaType.CHANNEL,
            can_play=False,
            can_expand=True,
            children=(
                self._get_media_children(collection_id, media_item.get("Buttons", []))
                if media_item
                else []
            ),
        )

    @async_refresh_after
    async def async_play_media(self, media_type, media_id, **kwargs) -> None:
        """Play the specified media."""
        # Implement this method if your player supports playing specific media
        _, _, mediaId = media_id.split("/", 2)
        if mediaId:
            self.media_content_id = media_id
            if self.coordinator.data.get("player_state", None) == PLAYER_STATE_FILE_PLAYBACK:
                await self._api.async_stop()
            try:
                await asyncio.sleep(DELAY_BEFORE_VIDEO_START)
                await self._rvideo_client.async_start_video(mediaId)
            except TimeoutError as e:
                _LOGGER.error("Error starting video: %s", e)
                ### R_Video seems to be busy, try again after a short delay
                await self._api.async_home()
                await asyncio.sleep(DELAY_BEFORE_RETRY)
                await self._api.async_r_video()

    ## Media Control Methods ##
    @async_refresh_after
    async def async_media_play(self) -> None:
        """Send play command."""
        await self._api.async_play()

    @async_refresh_after
    async def async_media_pause(self) -> None:
        """Send pause command."""
        await self._api.async_pause()

    @async_refresh_after
    async def async_media_stop(self) -> None:
        """Send stop command."""
        await self._api.async_stop()

    @async_refresh_after
    async def async_media_next_track(self) -> None:
        """Send next track command."""
        await self._api.async_next_track()

    @async_refresh_after
    async def async_media_previous_track(self) -> None:
        """Send previous track command."""
        await self._api.async_previous_track()

    ### Volume Control Methods ###
    @async_refresh_after
    async def async_volume_up(self) -> None:
        """Volume up the media player."""
        await self._api.async_volume_up()

    @async_refresh_after
    async def async_volume_down(self) -> None:
        """Volume down media player."""
        await self._api.async_volume_down()

    @async_refresh_after
    async def async_set_volume_level(self, volume: float) -> None:
        """Set the volume level of the media player."""
        # Convert float (0.0-1.0) to int (0-100)
        volume_int = int(volume * VOLUME_PERCENTAGE_FACTOR)
        await self._api.async_set_volume(volume_int)

    @async_refresh_after
    async def async_mute_volume(self, mute) -> None:
        """Mute/unmute command."""
        await self._api.async_mute(mute)

    @async_refresh_after
    async def async_media_seek(self, position: float) -> None:
        """Seek to a specific position in the media."""
        # Convert float position to int seconds
        position_seconds = int(position)
        await self._api.async_seek(position_seconds)

    @async_refresh_after
    async def async_turn_off(self) -> None:
        """Turn off the media player."""
        await self._api.async_power_off()

    ### Sound Mode Control Methods ###
    @async_refresh_after
    async def async_select_sound_mode(self, sound_mode: str) -> None:
        """Select sound mode (audio track)."""
        if (
            not self._attr_sound_mode_list
            or sound_mode not in self._attr_sound_mode_list
        ):
            _LOGGER.warning("Sound mode '%s' not available", sound_mode)
            return

        # Find the index of the selected sound mode
        sound_mode_index = self._attr_sound_mode_list.index(sound_mode)

        # Get the audio tracks from technical info
        if (
            (technical_info := self.coordinator.media_info.get("TechnicalInfo", None))
            and (audio_tracks := technical_info.get("AudioTrackTechnicalInfos", None))
            and isinstance(audio_tracks, list)
            and len(audio_tracks) > sound_mode_index
        ):
            track = audio_tracks[sound_mode_index]
            track_index = track.get("Index", 0)

            # Send audio track selection command to the API
            # Note: You'll need to implement this method in your API class
            try:
                await self._api.async_select_audio_track(track_index)
                self._attr_sound_mode = sound_mode
                _LOGGER.info("Selected audio track %d: %s", track_index, sound_mode)
            except Exception as e:
                _LOGGER.error("Failed to select audio track %d: %s", track_index, e)
