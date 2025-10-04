# Home Assistant integration for R_volution players

[![hacs][hacs-shield]][hacs]
[![GitHub Release][releases-shield]][releases]
[![GitHub Prerelease][prereleases-shield]][releases]

![Project Maintenance][maintainer]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

<!-- [![BuyMeCoffee][buymecoffeebadge]][buymecoffee] -->
<!-- [![Discord][discord-shield]][discord] -->
[![Community Forum][forum-shield]][forum]

This integration will interface with the R_volution player series by
[R_volution](https://www.rvolution.com).
This repository delivers the latest features via HACS. You can use it for
testing until I can get the integration accepted to HA core (no timeline for
that, sorry).

If you encounter problems, please file an issue at the integrations issue
tracker. If possible, add a diagnostics dump always. This is important also for
enhancements if they target new data or information to be retrieved from the
unit to see what it has to offer. Always check that dump if you want to further
redact information in it. The MACs and the units serial number are redacted
already, but check for yourself! If you find information in the dump that you
consider private, please file a bug request so that I can update the anonymizing
code.

- [Disclaimer](#disclaimer)
- [Installation](#installation)
  - [HACS Installation](#hacs-installation)
  - [Manual Installation](#manual-installation)
- [Configuration](#configuration)
  - [RSCP configuration](#rscp-configuration)
  - [Probable causes of connection problems](#probable-causes-of-connection-problems)
    - [Password limitations](#password-limitations)
    - [Network restriction](#network-restriction)
  - [Unsupported features configuration schemes](#unsupported-features-configuration-schemes)
- [Actions](#actions)
  - [Set power limits](#set-power-limits)
  - [Clear current power limits](#clear-current-power-limits)
  - [Initate manual battery charging](#initate-manual-battery-charging)
  - [Set maximum wallbox charging current](#set-maximum-wallbox-charging-current)
- [Upstream source](#upstream-source)

## Disclaimer

This integration is provided without any warranty or support by R_volution
(unfortunately). I do not take responsibility for any problems it may cause in
all cases. Use it at your own risk.

## Installation

The recommend way to install this extension is using HACS. If you want more
control, use the manual installation method.

### HACS Installation

1. Go to *HACS -> Integrations*
1. Click the Triple-Dot menu on the top right and select *Custom Repositories*
1. Set `https://github.com/volkerrichert/ha_R_volution_player.git` as repository name for
   the category *Integrations*
1. Open the repository (it will be displayed by default), select *Download* and
   confirm it
1. Restart Home Assistant
1. In the HA UI go to *Configuration -> Integrations* click "+" and search for
   "R_volution Player"

### Manual Installation

1. Using the tool of choice open the directory (folder) for your HA
   configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need
   to create it.
1. In the `custom_components` directory (folder) create a new folder called
   `e3dc_rscp`.
1. Download *all* the files from the `custom_components/r_volution_player/` directory
   (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to *Configuration -> Integrations* click "+" and search for
   "R_volution Player"

## Configuration

Once you add the integration, you'll be asked to authenticate yourself for a
connection to your R_volution .

- **Username:** Your r_volution user name
- **Password:** Your r_volution password
- **Hostname:** The Hostname or IP address of the r_volution player
- **API key:** Your api key for R_volution api calls. It can be requested as decribed in the [first steps documentaion](https://rvolution.freshdesk.com/en/support/solutions/articles/103000316607-rvolution-api-first-steps)


***

[commits-shield]: https://img.shields.io/github/commit-activity/y/volkerrichert/ha_R_volution_player?style=for-the-badge&logo=git
[commits]: https://github.com/volkerrichert/ha_R_volution_player/commits/main
[forum-shield]: https://img.shields.io/badge/Community%20Forum-Home%20Assistant-blue?style=for-the-badge&logo=homeassistant
[hacs]: https://github.com/hacs/integration
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge&logo=homeassistantcommunitystore
[license-shield]: https://img.shields.io/github/license/torbennehmer/hacs-e3dc?style=for-the-badge&color=blue&logo=gnu
[maintainer]: https://img.shields.io/badge/Maintainer-Volker%20Richert-blue?style=for-the-badge&logo=github
[prereleases-shield]: https://img.shields.io/github/v/release/volkerrichert/ha_R_volution_player?include_prereleases&style=for-the-badge&logo=git
[releases-shield]: https://img.shields.io/github/v/release/volkerrichert/ha_R_volution_player?style=for-the-badge&logo=homeassistantcommunitystore
[releases]: https://github.com/volkerrichert/ha_R_volution_player/releases