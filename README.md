# Home Assistant integration for R_volution players

[![Marketplace][marketplace-shield]][marketplace]
[![GitHub Release][releases-shield]][releases]
[![GitHub Prerelease][prereleases-shield]][releases]

![Project Maintenance][maintainer]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

<!-- [![BuyMeCoffee][buymecoffeebadge]][buymecoffee] -->
<!-- [![Discord][discord-shield]][discord] -->
<!-- [![Community Forum][forum-shield]][forum] -->

This integration will interface with the R_volution player series by
[R_volution](https://www.rvolution.com).
It is distributed through the Home Assistant Marketplace. You can use it until
the integration is accepted into HA core (no timeline for that, sorry).

If you encounter problems, please file an issue at the integration's
[issue tracker][issues]. Enable debug logging for
`custom_components.r_volution_player` and attach the relevant log lines.

- [Disclaimer](#disclaimer)
- [Installation](#installation)
  - [Marketplace Installation](#marketplace-installation)
  - [Manual Installation](#manual-installation)
- [Configuration](#configuration)

## Disclaimer

This integration is provided without any warranty or support by R_volution
(unfortunately). I do not take responsibility for any problems it may cause in
all cases. Use it at your own risk.

## Installation

The recommended way to install this integration is the Home Assistant
Marketplace. If you want more control, use the manual installation method.

### Marketplace Installation

1. Open the *Marketplace* in the Home Assistant sidebar
1. Add `https://github.com/volkerrichert/ha_R_volution_player` as a custom
   repository of the type *Integration*
1. Open the repository, select *Download* and confirm it
1. Restart Home Assistant
1. Go to *Settings -> Devices & services*, click *Add integration* and search
   for "R_volution Player"

If you installed the integration with HACS before, the Marketplace takes over
that installation; there is nothing to do.

### Manual Installation

1. Using the tool of choice open the directory (folder) for your HA
   configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need
   to create it.
1. In the `custom_components` directory (folder) create a new folder called
   `r_volution_player`.
1. Download *all* the files from the `custom_components/r_volution_player/`
   directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. Go to *Settings -> Devices & services*, click *Add integration* and search
   for "R_volution Player"

## Configuration

When you add the integration, you are asked for:

- **Host:** The hostname or IP address of the R_volution player

The player can be controlled without anything else. To browse your movie and TV
show collection in the media browser, open the integration's *Configure*
dialog and enter the e-mail, password and API key of your R_volution account.
R_volution no longer issues new API keys, so this only works if you already
have one; otherwise leave the fields empty.

***

[commits-shield]: https://img.shields.io/github/commit-activity/y/volkerrichert/ha_R_volution_player?style=for-the-badge&logo=git
[commits]: https://github.com/volkerrichert/ha_R_volution_player/commits/dev
[forum-shield]: https://img.shields.io/badge/Community%20Forum-Home%20Assistant-blue?style=for-the-badge&logo=homeassistant
[issues]: https://github.com/volkerrichert/ha_R_volution_player/issues
[license-shield]: https://img.shields.io/github/license/volkerrichert/ha_R_volution_player?style=for-the-badge&color=blue&logo=gnu
[maintainer]: https://img.shields.io/badge/Maintainer-Volker%20Richert-blue?style=for-the-badge&logo=github
[marketplace]: https://www.home-assistant.io/integrations/marketplace
[marketplace-shield]: https://img.shields.io/badge/Marketplace-Custom-41BDF5.svg?style=for-the-badge&logo=homeassistant
[prereleases-shield]: https://img.shields.io/github/v/release/volkerrichert/ha_R_volution_player?include_prereleases&style=for-the-badge&logo=git
[releases-shield]: https://img.shields.io/github/v/release/volkerrichert/ha_R_volution_player?style=for-the-badge&logo=homeassistant
[releases]: https://github.com/volkerrichert/ha_R_volution_player/releases
