// led_config_nvs.h -- Flash-time seed for the LED output configuration
// (data pin, chip type and pixel count per bus).
//
// Why this exists: DATA_PINS / LED_TYPES / PIXEL_COUNTS are compile-time
// defines, and WLED only consults them when no cfg.json exists yet
// (cfg.cpp, the `else if (fromFS)` branch of deserializeConfig). A
// strip that differs from what the profile was built with therefore
// needed either a rebuild or a trip through the WLED UI on every
// device. The web flasher writes this slot into the NVS partition of
// the image it is about to flash, so a node comes up on the right
// strip on its first boot -- exactly what rf_config_nvs.h does for the
// radio, and deliberately the same shape.
//
// Design:
//   * Header-only / inline, like rf_config_nvs.h, and for the same
//     reason: the NVS surface stays in one file. Preferences (NVS) has
//     its own CRC; the schema CRC16 here catches a slot written under
//     an older P_LedConfig layout, which a size match would hide.
//   * **The seed is consumed.** apply() wipes the slot once it has
//     taken effect, so it can act at most once per flash. That is what
//     makes it a *default* rather than an override: whoever edits the
//     LEDs in WLED's UI afterwards keeps their setting, because there
//     is nothing left to re-apply on the next boot. It also removes
//     the need for a boot-loop counter -- a config that fails to come
//     up cannot come back, because it is already gone.
//   * validate() is pure: structure, ranges and duplicate pins only.
//     Whether a pin is usable and whether a type is a one-pin digital
//     chip is decided at apply time against PinManager and Bus, which
//     are the authorities and need no list duplicated here.
//   * `version` is a schema handle. A bump makes every older slot
//     invalid, which is the correct outcome for a field layout change.
//
// This file is NOT one of the four shared protocol headers
// (racelink_proto.h, racelink_headless.h, racelink_indicators.h,
// racelink_transport_core.h) and, unlike rf_config_nvs.h, has no
// counterpart in RaceLink_Gateway: a gateway drives no LEDs. There is
// deliberately no wire opcode for it either -- the LED wiring is a
// property of how a node was built into its housing, set once when the
// hardware is commissioned, not something a gateway should be able to
// change over the air.

#pragma once

#include <Arduino.h>
#include <Preferences.h>

namespace LedConfigNvs {

// Bumped only for a P_LedConfig field-layout change. Every existing
// slot becomes invalid, and load() then returns false so the device
// falls back to its compile-time defaults.
static const uint16_t NVS_MAGIC = 0xA5C4;  // rf_config_nvs.h uses 0xA5C3

// Schema version inside the payload, independent of NVS_MAGIC so a
// reader can tell "not mine" from "mine, but newer than I understand".
static const uint8_t SCHEMA_VERSION = 1;

// Two, because every shipping profile sets WLED_MAX_BUSSES to 1 or 2.
// The real per-board cap is checked at apply time; this only bounds the
// wire struct.
static const uint8_t MAX_BUSES = 2;

// Upper bound on a single bus. Not a hardware limit -- WLED's own
// MAX_LED_MEMORY check decides what actually fits, and it knows the
// chip and the type. This is here so a corrupt count cannot ask for a
// multi-megabyte allocation before that check is reached.
static const uint16_t MAX_COUNT = 2048;

static const char* NVS_NAMESPACE = "rl_led";
static const char* KEY_MAGIC     = "magic";
static const char* KEY_CONFIG    = "cfg";
static const char* KEY_CRC       = "crc";

struct __attribute__((packed)) LedBus {
  uint8_t  pin;    // 1B -- GPIO carrying the data line
  uint8_t  type;   // 1B -- WLED TYPE_* (const.h); one-pin digital types only
  uint16_t count;  // 2B LE -- pixels on this bus
};  // 4B

struct __attribute__((packed)) P_LedConfig {
  uint8_t  version;    // 1B    -- SCHEMA_VERSION
  uint8_t  bus_count;  // 1B    -- 1..MAX_BUSES
  LedBus   bus[MAX_BUSES];  // 8B
  uint16_t reserved;   // 2B LE -- MUST be 0
};  // 12B

// CRC16-CCITT over the payload. Byte for byte the routine in
// rf_config_nvs.h; duplicated rather than shared because these two
// headers are independent and neither should have to include the other.
inline uint16_t crc16(const uint8_t* data, size_t n) {
  uint16_t crc = 0xFFFF;
  for (size_t i = 0; i < n; ++i) {
    crc ^= (uint16_t)data[i] << 8;
    for (uint8_t j = 0; j < 8; ++j) {
      crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021)
                           : (uint16_t)(crc << 1);
    }
  }
  return crc;
}

// Structural and range checks only -- see the header note on why pin
// usability and chip type are not decided here.
inline bool validate(const P_LedConfig& c) {
  if (c.version != SCHEMA_VERSION) return false;
  if (c.reserved != 0) return false;
  if (c.bus_count < 1 || c.bus_count > MAX_BUSES) return false;
  for (uint8_t i = 0; i < c.bus_count; ++i) {
    if (c.bus[i].count < 1 || c.bus[i].count > MAX_COUNT) return false;
    // Two buses driving one pin is not a wiring mistake we should try to
    // interpret; it is a corrupt or mis-generated slot.
    for (uint8_t j = 0; j < i; ++j) {
      if (c.bus[i].pin == c.bus[j].pin) return false;
    }
  }
  return true;
}

// Persist a validated config. Re-runs validate() defensively; returns
// false if the caller skipped that step or NVS refused the write.
inline bool store(const P_LedConfig& c) {
  if (!validate(c)) return false;
  Preferences prefs;
  if (!prefs.begin(NVS_NAMESPACE, /*readOnly=*/false)) return false;
  bool ok = true;
  ok &= (prefs.putUShort(KEY_MAGIC, NVS_MAGIC) == sizeof(uint16_t));
  ok &= (prefs.putBytes(KEY_CONFIG, &c, sizeof(c)) == sizeof(c));
  const uint16_t crc = crc16(reinterpret_cast<const uint8_t*>(&c), sizeof(c));
  ok &= (prefs.putUShort(KEY_CRC, crc) == sizeof(uint16_t));
  prefs.end();
  return ok;
}

// Load a seeded config. True only if the slot is present, the magic
// matches, the size matches, the CRC verifies and validate() passes.
// Any other outcome means "no seed", and the caller keeps whatever WLED
// already decided -- cfg.json, or the compile-time defaults.
inline bool load(P_LedConfig& out) {
  Preferences prefs;
  if (!prefs.begin(NVS_NAMESPACE, /*readOnly=*/true)) return false;
  bool good = false;
  do {
    if (!prefs.isKey(KEY_MAGIC) || !prefs.isKey(KEY_CONFIG) || !prefs.isKey(KEY_CRC)) break;
    if (prefs.getUShort(KEY_MAGIC, 0) != NVS_MAGIC) break;
    if (prefs.getBytesLength(KEY_CONFIG) != sizeof(P_LedConfig)) break;
    P_LedConfig tmp{};
    if (prefs.getBytes(KEY_CONFIG, &tmp, sizeof(tmp)) != sizeof(tmp)) break;
    const uint16_t expected = prefs.getUShort(KEY_CRC, 0);
    const uint16_t actual   = crc16(reinterpret_cast<const uint8_t*>(&tmp), sizeof(tmp));
    if (expected != actual) break;
    if (!validate(tmp)) break;
    out = tmp;
    good = true;
  } while (false);
  prefs.end();
  return good;
}

// Drop the seed. Called once it has been applied -- see the header note
// on why the seed is consumed rather than re-read on every boot.
inline void wipe() {
  Preferences prefs;
  if (!prefs.begin(NVS_NAMESPACE, /*readOnly=*/false)) return;
  prefs.remove(KEY_MAGIC);
  prefs.remove(KEY_CONFIG);
  prefs.remove(KEY_CRC);
  prefs.end();
}

}  // namespace LedConfigNvs
