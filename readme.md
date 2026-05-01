# RaceLink_WLED

A custom [WLED](https://github.com/wled/WLED) usermod plus
ready-to-use PlatformIO build profiles for **RaceLink wireless
nodes**.

This repo extends an unmodified WLED checkout — there is no
forked WLED tree to maintain.

## Documentation

📚 **Full documentation lives at
[RaceLink_Docs](https://github.com/PSi86/RaceLink_Docs)**:

* **WLED node operator setup** — pairing, factory reset, default AP / OTA
* **Deterministic effects audit** — which effects sync under offset mode
* **Build profiles per hardware variant**

This README only covers what's specific to *this repository* —
build profiles, the release workflow. For the operator guide and
the deterministic-effects audit, follow the link above.

## Quick start

```bash
# 1. Clone the official WLED:
git clone https://github.com/wled/WLED.git

# 2. Clone this repo:
git clone https://github.com/PSi86/RaceLink_WLED.git

# 3. Pick the matching profile and copy it as platformio_override.ini
#    into the WLED checkout. Then build:
cd WLED
pio run -e RaceLink_Node_v4_s3_llcc68
```

For the full per-profile build instructions see
[WLED firmware](https://psi86.github.io/RaceLink_Docs/RaceLink_WLED/).

## Supported hardware profiles

| Profile | Hardware |
|---|---|
| `RaceLink_Node_v1_c3_ct62` | ESP32-C3 + SX1262 |
| `RaceLink_Node_v3_s2_llcc68` | ESP32-S2 + LLCC68 |
| `RaceLink_Node_v3_s2_llcc68_epaper` | … plus e-paper display |
| `RaceLink_Node_v4_s3_llcc68` | ESP32-S3 + LLCC68 |

Each profile contains the modem selection, SPI pins, LED
configuration and feature flags for that variant.

## GitHub release workflow

`.github/workflows/release.yml` checks out the official `wled/WLED`
source, stages the local usermod, builds every shipping profile,
and publishes a GitHub release with firmware binaries plus a
checksum manifest.

Inputs: `target_branch` (required), optional `version`,
optional `wled_ref`. Without `wled_ref`, the workflow resolves the
latest published WLED release.

## Repository structure

```text
RaceLink_WLED/
├── build_profiles/
│   ├── RaceLink_Node_v1_c3_ct62.platformio_override.ini
│   ├── RaceLink_Node_v3_s2_llcc68.platformio_override.ini
│   ├── RaceLink_Node_v3_s2_llcc68_epaper.platformio_override.ini
│   ├── RaceLink_Node_v4_s3_llcc68.platformio_override.ini
│   └── all_profiles.platformio_override.ini
├── racelink_proto.h            ← byte-identical to Host + Gateway
├── racelink_transport_core.h
├── racelink_wled.{cpp,h}       the usermod
├── racelink_epaper.{cpp,h}     optional e-paper module
├── version.json                release version
├── library.json
├── README.md
└── LICENSE
```

## Licence

See [`LICENSE`](LICENSE).
