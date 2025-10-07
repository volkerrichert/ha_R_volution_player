"""Media Player implementation for the R Volution Player."""

import logging
from typing import Any, Concatenate
import asyncio
from collections.abc import Awaitable, Callable, Coroutine

import homeassistant
from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityDescription,
    MediaPlayerState,
    MediaType,
    MediaPlayerEntityFeature,
    BrowseMedia,
    MediaClass,
    RepeatMode,
    SearchMedia,
    SearchMediaQuery,
)

from homeassistant.core import (
    callback,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import AFTER_REQUEST_SLEEP, DOMAIN
from .coordinator import RVolutionCoordinator

_LOGGER = logging.getLogger(__name__)


def async_refresh_after[T: RVolutionPlayer, **P](
    func: Callable[Concatenate[T, P], Awaitable[None]],
) -> Callable[Concatenate[T, P], Coroutine[Any, Any, None]]:
    """Delay status update until after method execution."""

    async def _async_wrap(self: T, *args: P.args, **kwargs: P.kwargs) -> None:
        await func(self, *args, **kwargs)
        await asyncio.sleep(AFTER_REQUEST_SLEEP)
        await self.coordinator.async_refresh()

    return _async_wrap


async def async_setup_entry(hass, config_entry, async_add_entities):
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

    async_add_entities([player], True)


class RVolutionPlayerEntityDescription(MediaPlayerEntityDescription):
    """Description of the R Volution Player entity."""

    def __init__(self, key: str, translation_key: str, name: str, icon: str):
        """Initialize the entity description."""
        super().__init__(key, translation_key, name, icon)
        self.key = key
        self.translation_key = translation_key
        self.name = name
        self.icon = icon


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
        self._attr_volume_level = 1
        self._attr_volume_step = 0.04
        self._attr_is_volume_muted = False
        self._product_name = self.coordinator._model
        self._player_state = None
        self._product_id = self.coordinator._model_id
        self._serial_number = self.coordinator._serial_number
        self._attr_state = MediaPlayerState.OFF
        self._attr_supported_features = MediaPlayerEntityFeature.BROWSE_MEDIA
        if device_info is not None:
            self._attr_device_info = device_info
        else:
            self._attr_device_info = self.coordinator.device_info

        self._attr_name = f"{self._product_name} ({self._host})"
        self._update_data_from_coordinator()

    def _update_data_from_coordinator(self) -> None:
        """Update the entity's attributes based on the coordinator's data."""

        if data := self.coordinator.data:
            # self._product_name = data.get("product_name", None)
            # self._player_state = data.get("playback_state", None)
            # self._product_id = data.get("product_id", None)
            # self._serial_number = data.get("serial_number", None)

            # self._attr_app_id: str | None = None
            # self._attr_app_name: str | None = None

            self._attr_is_volume_muted = data.get("playback_mute", "0") == "1"

            if data.get("player_state", None) == "file_playback":
                media_info = self.coordinator.media_info
                value = data.get("playback_duration", None)
                self._attr_media_duration = int(value) if value else None
                value = data.get("playback_position", None)
                self._attr_media_position = int(value) if value else None
                self._attr_media_position_updated_at = (
                    homeassistant.util.dt.utcnow() if value else None
                )
                self._attr_media_title = media_info.get("Title", None)
                self._attr_media_image_url = media_info.get(
                    "BackgroundUrl", media_info.get("PosterUrl", None)
                )
                self._attr_media_episode = media_info.get("Episode", None)
                self._attr_media_series_title = media_info.get("TvShowName", None)
                self._attr_media_season = media_info.get("Season", None)
                self._attr_media_content_type = self.coordinator.media_info.get(
                    "Type", None
                )
                if self._attr_media_content_type == "TVShowEpisode":
                    self._attr_media_content_type = MediaType.TVSHOW
                elif self._attr_media_content_type == "Movie":
                    self._attr_media_content_type = MediaType.MOVIE
                else:
                    self._attr_media_content_type = None
                # self._attr_media_content_id = data.get("playback_url", None)

                if (
                    (
                        technical_info := self.coordinator.media_info.get(
                            "TechnicalInfo", None
                        )
                    )
                    and (
                        audio_tracks := technical_info.get(
                            "AudioTrackTechnicalInfos", None
                        )
                    )
                    and isinstance(audio_tracks, list)
                    and len(audio_tracks) > 0
                    and data.get("audio_track").isdigit()
                ):
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
                    # Set current sound mode to first track if available^
                    if sound_modes:
                        self._attr_sound_mode = sound_modes[
                            int(data.get("audio_track"))
                        ]
                    else:
                        self._attr_sound_mode_list = None
                        self._attr_sound_mode = None
                else:
                    self._attr_sound_mode_list = None
                    self._attr_sound_mode = None
            else:
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

            # self._attr_media_image_remotely_accessible: bool = False
            self._attr_shuffle = data.get("playback_shuffle", "0") == "1"
            match data.get("playback_repeat", "0"):
                case "0":
                    self._attr_repeat = RepeatMode.OFF
                case "1":
                    self._attr_repeat = RepeatMode.ALL
                case "2":
                    self._attr_repeat = RepeatMode.ONE
                case _:
                    self._attr_repeat = RepeatMode.OFF

            self._attr_state = self._get_player_state(data)

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
            if (
                self._collection_client
                and len(self._collection_client.get_collections()) > 0
            ):
                # TODO: Search seems to be unusable with custom API KEY
                self._attr_supported_features |= (
                    MediaPlayerEntityFeature.BROWSE_MEDIA
                #    | MediaPlayerEntityFeature.SEARCH_MEDIA
                )
            # TODO: check how to find next / prev episode
            # if (self.coordinator.media_info.get("Type", None) == "TVShowEpisode"):
            #    self._attr_supported_features |= MediaPlayerEntityFeature.NEXT_TRACK | MediaPlayerEntityFeature.PREVIOUS_TRACK
            # Add sound mode selection if audio tracks are available
            if self._attr_sound_mode_list and len(self._attr_sound_mode_list) > 1:
                self._attr_supported_features |= (
                    MediaPlayerEntityFeature.SELECT_SOUND_MODE
                )

            self._attr_volume_level = (
                int((self.coordinator.data or {}).get("playback_volume", "100")) / 100.0
            )
        else:
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

            self._attr_shuffle = None
            self._attr_repeat = RepeatMode.OFF
            self._attr_state = MediaPlayerState.OFF
            self._attr_supported_features = MediaPlayerEntityFeature(0)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_data_from_coordinator()
        self.async_write_ha_state()

    async def async_search_media(
        self,
        query: SearchMediaQuery,
    ) -> SearchMedia:
        """Search the media player."""
        if not self._collection_client:
            _LOGGER.warning("No collection client available for search")
            return SearchMedia(result=[])

        search_results = []
        search_query = query.search_query.lower()

        try:
            # Durchsuche alle verfügbaren Collections
            collections = self._collection_client.get_collections()

            for collection_id, _collection_name in collections.items():
                # Durchsuche verschiedene Kategorien
                categories = ["All", "Movies", "TVShows"]

                for category in categories:
                    try:
                        content = await self._collection_client.async_get_menu(
                            collection_id, category
                        )
                        if not content or "Buttons" not in content:
                            continue

                        for item in content["Buttons"]:
                            title = item.get("Text", "").lower()

                            # Erweiterte Suchlogik: exakte Übereinstimmung oder Wortteile
                            if (
                                search_query in title
                                or any(word in title for word in search_query.split())
                                or any(
                                    search_word in title
                                    for search_word in search_query.split()
                                    if len(search_word) > 2
                                )
                            ):
                                media_id = item.get("Id", "Unknown")
                                media_type = item.get("Type", "Unknown")
                                media_image_id = item.get("Icon", None)

                                (
                                    can_play,
                                    can_expand,
                                    media_class,
                                    media_content_type,
                                    thumbnail,
                                ) = self._determine_media_properties(
                                    collection_id=collection_id,
                                    media_image_id=media_image_id,
                                    type=media_type,
                                )

                                # Verhindere Duplikate
                                content_id = f"{collection_id}/{media_id}"
                                if not any(
                                    result.media_content_id == content_id
                                    for result in search_results
                                ):
                                    search_results.append(
                                        BrowseMedia(
                                            title=item.get("Text", "Unknown"),
                                            media_class=media_class,
                                            media_content_id=content_id,
                                            media_content_type=media_content_type,
                                            can_play=can_play,
                                            can_expand=can_expand,
                                            thumbnail=thumbnail,
                                        )
                                    )

                    except Exception as e:
                        _LOGGER.warning(
                            "Error searching category %s in collection %s: %s",
                            category,
                            collection_id,
                            e,
                        )
                        continue

            # Sortiere Ergebnisse nach Relevanz (exakte Treffer zuerst)
            search_results.sort(
                key=lambda x: (
                    search_query not in x.title.lower(),  # Exakte Treffer zuerst
                    x.title.lower(),  # Dann alphabetisch
                )
            )

            # Begrenze Ergebnisse auf die ersten 50
            search_results = search_results[:50]

            _LOGGER.info(
                "Search for '%s' returned %d results",
                query.search_query,
                len(search_results),
            )

        except Exception as e:
            _LOGGER.error("Error during media search: %s", e)

        return SearchMedia(result=search_results)

    def _get_player_state(self, data: dict) -> MediaPlayerState | None:
        """Update the player's state based on the provided player state string."""

        player_state = data.get("player_state", None)
        playback_state = data.get("playback_state", None)
        if player_state == "navigator":
            return MediaPlayerState.IDLE
        elif player_state == "file_playback":
            if playback_state == "playing":
                return MediaPlayerState.PLAYING
            elif playback_state == "paused":
                return MediaPlayerState.PAUSED
            elif playback_state == "buffering" or playback_state == "initializing":
                return MediaPlayerState.BUFFERING
        else:
            return MediaPlayerState.IDLE

    async def async_get_browse_image(
        self, media_content_type, media_content_id, media_image_id=None
    ):
        """Serve album art. Returns (content, content_type)."""
        image_url = (
            f"https://cdn.rvolution.com/pictures/480x720_100/{media_image_id}"
            if media_content_type == MediaType.MOVIE
            else f"http://rvolution-server-1-10.westeurope.cloudapp.azure.com/api/1.2/Picture?AuthKey={self.coordinator.collection_client._auth_key}&Collection={media_content_id}&Hash={media_image_id}&ApiKey={self.coordinator.apiKey}"
        )
        content = await self._async_fetch_image(image_url)
        return content

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
                        collection_id, name = media_content_id.split("/", 1)
                        return await self._async_get_browse_media_menu(
                            collection_id, name
                        )
                case MediaType.APP:
                    return await self._async_get_browse_media_collection(
                        media_content_id
                    )
                case MediaType.CHANNEL | MediaType.TVSHOW | MediaType.SEASON:
                    # Assuming media_content_id is in the format "collection_id/media_id"
                    collection_id, media_id = media_content_id.split("/", 1)
                    return await self._async_get_browse_media_custom_group(
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
                )
                for id, title in collections.items()
            ]

        return BrowseMedia(
            title="Collections",
            media_class=MediaClass.DIRECTORY,
            media_content_id="root",
            media_content_type=MediaType.CHANNELS,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_get_browse_media_collection(self, collection_id):
        """Return a BrowseMedia object for a specific collection."""
        collection = self._collection_client.get_collection(collection_id)
        if not collection:
            _LOGGER.error("Collection not found: %s", collection_id)
            return None

        children = [
            BrowseMedia(
                title="All Media",
                media_class=MediaClass.DIRECTORY,
                media_content_id=f"{collection_id}/All",
                media_content_type=MediaType.CHANNELS,
                can_play=False,
                can_expand=True,
            ),
            BrowseMedia(
                title="Movies",
                media_class=MediaClass.DIRECTORY,
                media_content_id=f"{collection_id}/Movies",
                media_content_type=MediaType.CHANNELS,
                can_play=False,
                can_expand=True,
            ),
            BrowseMedia(
                title="TV Shows",
                media_class=MediaClass.DIRECTORY,
                media_content_id=f"{collection_id}/TVShows",
                media_content_type=MediaType.CHANNELS,
                can_play=False,
                can_expand=True,
            ),
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

    async def _async_get_browse_media_menu(self, collection_id, name):
        """Return a BrowseMedia object for a specific menu."""

        content = await self._collection_client.async_get_menu(collection_id, name)
        children = self._get_media_children(collection_id, content.get("Buttons", []))

        return BrowseMedia(
            title=content.get("Name", name),
            media_class=MediaClass.DIRECTORY,
            media_content_id=f"{collection_id}/{name}",
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
            case "TVShowSeason":
                media_class = MediaClass.SEASON
                media_content_type = MediaType.SEASON
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
            title = item.get("Text", "Unknown")
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
                    media_content_id=f"{collection_id}/{id}",
                    media_content_type=media_content_type,
                    can_play=can_play,
                    can_expand=can_expand,
                    thumbnail=thumbnail,
                )
            )

        return children

    async def _async_get_browse_media_custom_group(self, collection_id, media_id):
        """Return a BrowseMedia object for a custom group."""
        collection = self._collection_client.get_collection(collection_id)
        if not collection:
            _LOGGER.error("Collection not found: %s", collection_id)
            return None

        media_item = await self._collection_client.async_get_items(
            collection_id, media_id
        )
        return BrowseMedia(
            title=collection,
            media_class=MediaClass.DIRECTORY,
            media_content_id=f"{collection_id}/{media_id}",
            media_content_type=MediaType.CHANNEL,
            can_play=False,
            can_expand=True,
            children=self._get_media_children(
                collection_id, media_item.get("Buttons", [])
            )
            if media_item
            else [],
            # thumbnail=self.get_browse_image_url(MediaType.CHANNEL, collection_id)
        )

    @async_refresh_after
    async def async_play_media(self, media_type, media_id, **kwargs) -> None:
        """Play the specified media."""
        # Implement this method if your player supports playing specific media
        _, mediaId = media_id.split("/", 1)
        if mediaId:
            self.media_content_id = media_id
            if self.coordinator.data.get("player_state", None) == "file_playback":
                await self._api.async_stop()
            await self._rvideo_client.async_start_video(mediaId)

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
    # @async_log_errors DenonaAVR
    @async_refresh_after
    async def async_volume_up(self) -> None:
        """Volume up the media player."""
        await self._api.async_volume_up()

    # @async_log_errors

    @async_refresh_after
    async def async_volume_down(self) -> None:
        """Volume down media player."""
        await self._api.async_volume_down()

    # @async_log_errors
    @async_refresh_after
    async def async_set_volume_level(self, volume: float) -> None:
        """Set the volume level of the media player."""
        # Convert float (0.0-1.0) to int (0-100)
        volume_int = int(volume * 100)
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
