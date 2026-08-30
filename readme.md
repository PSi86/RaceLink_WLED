# RaceLink WLED Usermod

A custom WLED usermod for **RaceLink wireless nodes**.

This repository contains the RaceLink-specific WLED usermod code as well as ready-to-use **build profiles** for supported hardware variants. It is intended for users who want to build WLED firmware with RaceLink support **without depending on a custom WLED fork**.

In a typical setup:

- **RaceLink_WLED** provides the wireless node firmware
- **RaceLink_Gateway** sends commands to those nodes, receives their responses, and bridges the wireless link to USB
- **RaceLink_Host** communicates with the gateway over USB and provides higher-level control logic, integrations, and web interfaces

This repository is focused on the **WLED-based node side** of the RaceLink ecosystem. It does **not** contain the gateway firmware and it does **not** contain the host-side application.

> **Status:** Testing.

---

## What this repository provides

- the **RaceLink WLED usermod**
- ready-to-use **PlatformIO build profiles** for supported hardware variants
- board-specific compile-time settings such as:
  - wireless modem selection
  - SPI pin definitions
  - LED pin and strip configuration
  - selected WLED feature flags
  - battery usermod configuration
  - optional e-paper display support

At the moment, the hardware-specific pin mappings are still defined in the build profiles. In a future revision, these settings may be moved into the WLED usermod configuration UI.

---

## Role in the RaceLink ecosystem

RaceLink_WLED provides the wireless node firmware layer of the RaceLink system:

```text
RaceLink_Host  <--USB-->  RaceLink_Gateway  <--wireless-->  RaceLink nodes
                                                           ├─ RaceLink_WLED nodes
                                                           ├─ Startblocks
                                                           └─ Custom nodes
```

Typical responsibilities of the WLED-based node firmware include:

- receiving RaceLink packets over the wireless link
- applying control and configuration commands on the node
- driving one or more LED outputs through WLED
- participating in synchronization flows
- reporting node responses and device-specific status back through the gateway to the host
- optionally supporting battery monitoring and e-paper display features on supported hardware

---

## Current project structure

The repository currently contains the RaceLink WLED usermod sources plus build-profile files for supported hardware variants:

```text
RaceLink_WLED/
├─ build_profiles/          board profiles, one per hardware variant
├─ data/                    rf_channels.json, the channel plan the nodes share
├─ docs/                    design notes for individual features
├─ scripts/                 release tooling (staging, versioning, WLED patching)
├─ tests/                   static tests for that tooling
├─ library.json             PlatformIO manifest for the usermod
├─ wled_source.json         the pinned WLED ref and upstream patches
├─ version.json             the RaceLink_WLED release version
├─ racelink_wled.h/.cpp     the usermod itself
├─ racelink_proto.h         the RaceLink wire protocol
├─ racelink_transport_*.h   radio and Ethernet transports
├─ racelink_w5500_udp.h     W5500 UDP driver for the Ethernet node
├─ racelink_headless.h      headless-master mode
├─ racelink_indicators.h    LED feedback patterns
├─ racelink_epaper.h/.cpp   optional e-paper display support
├─ *_nvs.h                  persisted LED and radio configuration
└─ readme.md
```

This layout combines the usermod source itself with the hardware-specific PlatformIO override profiles required to build supported RaceLink node variants.

---

## Supported hardware profiles

Six profiles are built and published by every release:

- `RaceLink_Node_v1_c3_ct62.platformio_override.ini`
- `RaceLink_Node_v3_s2_llcc68.platformio_override.ini`
- `RaceLink_Node_v3_s2_llcc68_epaper.platformio_override.ini`
- `RaceLink_Node_v4_s3_llcc68.platformio_override.ini`
- `RaceLink_Node_v5_s3_eth.platformio_override.ini`
- `RaceLink_Node_v6_s3_heltec_wpaper.platformio_override.ini`

That list is `SHIPPING_PROFILE_FILENAMES` in `scripts/release_profiles.py`; a
profile that is not named there is not built, whatever else it is.

Two more files in the directory are not shipping profiles:

- `all_profiles.platformio_override.ini` — every environment in one file, for
  building several variants from a single checkout.
- `bak_RaceLink_Node_v3_s2_llcc68.platformio_override.ini` — a kept-around
  earlier revision of the v3 profile.

These profiles contain the required compile-time configuration for the currently supported RaceLink node hardware.

---

## Requirements

Before building, make sure you have:

- a local checkout of the official **WLED** repository
- **PlatformIO** installed  
  Either through **VS Code + PlatformIO extension** or a standalone PlatformIO installation
- a supported ESP32-based target board
- the matching RaceLink build profile for your hardware

---

## Quick start

### 1. Get the official WLED repository

Clone or download the official WLED repository, at the release this firmware is
built against (see **Which WLED version** below):

```bash
git clone --branch v16.0.1 https://github.com/wled/WLED.git
```

You can also fork it on GitHub first and then clone your fork.

### 2. Get this RaceLink repository

Clone or download this repository:

```bash
git clone https://github.com/PSi86/RaceLink_WLED.git
```

### 3. Select the matching build profile

Choose the `.platformio_override.ini` file that best matches your hardware from the `build_profiles` directory.

### 4. Copy it into the WLED root directory

Copy the selected profile into the root of your local WLED checkout and rename it to:

```text
platformio_override.ini
```

WLED loads this file automatically via its PlatformIO configuration.

### 5. Build the firmware

Run PlatformIO with the environment defined in the selected profile:

```bash
pio run -e <envname>
```

or build it directly from **VS Code / PlatformIO**.

---

## Example build commands

Depending on the selected profile, typical build commands may look like this:

```bash
pio run -e RaceLink_Node_v1_c3_ct62
pio run -e RaceLink_Node_v3_s2_llcc68
pio run -e RaceLink_Node_v3_s2_llcc68_epaper
pio run -e RaceLink_Node_v4_s3_llcc68
```

---

## Build profile notes

The provided build profiles currently define hardware-specific values such as:

- modem type (`RACELINK_SX1262` or `RACELINK_LLCC68`)
- SPI pin mapping for the radio
- radio parameters such as frequency, bandwidth, spreading factor, and TX power
- LED data pins and bus configuration
- battery measurement settings
- optional e-paper display pin mapping

This means that users should **start with the closest matching profile** and then adjust it if their hardware differs.

---

## Which WLED version

`wled_source.json` names the WLED sources a RaceLink image is built from:

```json
{
  "ref": "v16.0.1",
  "patch_prs": [5521]
}
```

* `ref` — the wled/WLED tag to build against, or `"latest"` to resolve the
  newest published upstream release at build time.
* `patch_prs` — upstream pull requests applied on top of that tag, in order.
  `git apply` is strict here: a patch that no longer fits the tag fails the
  build rather than being fuzzed into place.

Both the compile-only build and the release read this file, so a pull request
is compiled against the same tree a release would ship. Both workflows still
take a `wled_ref` and a `wled_patch_prs` input for a one-off run; leaving them
empty uses the pinned values, and `latest` / `none` are the ways to ask for
something else explicitly.

Pinning is deliberate. Every build profile inherits its platform, toolchain and
NeoPixelBus version from WLED's shared `[esp32]`, `[esp32s2]`, `[esp32s3]` and
`[esp32c3]` sections. On WLED's `main` those sections have already moved from
ESP-IDF 4.4 to 5.5, so an unpinned build would adopt a new toolchain — and a
different OTA story — the day the next WLED release appears, with no commit
here to point at.

`patch_prs` currently carries **wled/WLED#5521**, which exports the battery
usermod's readings through `um_data`. Without it `getUMData(USERMOD_ID_BATTERY)`
never succeeds and a node reports no battery state; nothing fails, the lookup is
simply retried forever. The pull request is still open upstream, and
wled/WLED#5399 rewrites the same file — once that merges, this patch stops
applying and the dependency needs another answer.

---

## Using this repository as an external usermod source

The intended usage model is:

1. keep your local WLED checkout based on the **official WLED repository**
2. reference this repository through `custom_usermods`
3. keep all RaceLink-specific board settings inside `platformio_override.ini`

This avoids the need for a dedicated WLED fork just to build RaceLink-enabled firmware.

---

## Integration with other RaceLink repositories

This repository is usually used together with:

### RaceLink_Gateway

Contains the embedded firmware for the USB gateway that forwards wireless traffic between the host and RaceLink-compatible nodes.

Repository:  
`https://github.com/PSi86/RaceLink_Gateway`

### RaceLink_Host

Contains the host-side software that communicates with the gateway over USB and typically runs the higher-level control logic, integrations, and web interfaces.

Repository:  
`https://github.com/PSi86/RaceLink_Host`

### Official WLED

Provides the underlying WLED codebase that this repository extends through its usermod and build-profile workflow.

Repository:  
`https://github.com/wled/WLED`

---

## Typical system setup

A common deployment looks like this:

1. **RaceLink_WLED** firmware runs on wireless nodes
2. **RaceLink_Gateway** firmware runs on the USB-connected gateway hardware
3. **RaceLink_Host** runs on a Raspberry Pi, PC, or similar host system
4. The host communicates with the gateway over USB
5. The gateway exchanges wireless packets with the RaceLink nodes
6. Users interact with the system through the host integration and web interface layers

---

## Customizing for your own hardware

If your hardware differs from the provided profiles, you will most likely need to adjust:

- radio SPI pins
- modem type
- LED pin definitions
- button pin
- battery measurement pin and scaling
- optional e-paper pins
- selected WLED feature flags

For derived hardware, it is usually easiest to duplicate the closest matching profile and modify only the necessary values.

---

## Troubleshooting

### Build fails because the environment name does not exist

Make sure the environment name passed to `pio run -e ...` matches the `[env:...]` section inside the selected profile.

### Usermod is not found

Verify that the selected profile contains the correct `custom_usermods` entry and that the referenced repository or local path is available.

### Wrong pin mapping or non-working radio

Check the `RACELINK_PIN_*` definitions and modem selection in the chosen build profile.

### Wrong battery reading

Review the battery measurement pin and voltage multiplier settings in the profile.

### The firmware builds but does not behave as expected in the RaceLink system

Check that the node build profile matches the actual hardware and that the gateway and host components in the rest of the system are using compatible settings and firmware versions.

---

## Intended audience

This repository is mainly intended for:

- RaceLink node firmware builds
- custom WLED-based RaceLink hardware
- development and testing of RaceLink-compatible wireless nodes
- developers building complete RaceLink systems from host to gateway to node

---

## Related repositories

- RaceLink WLED nodes: `https://github.com/PSi86/RaceLink_WLED`
- RaceLink Gateway: `https://github.com/PSi86/RaceLink_Gateway`
- RaceLink Host: `https://github.com/PSi86/RaceLink_Host`
- Official WLED repository: `https://github.com/wled/WLED`

---

## Notes

This repository provides the **WLED-based wireless node layer** of the RaceLink project.

It does not replace the official WLED repository, but extends it with RaceLink-specific functionality and hardware profiles so that RaceLink-compatible wireless nodes can be built and integrated into the larger RaceLink system.
