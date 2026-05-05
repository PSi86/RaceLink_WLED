#pragma once
#include <Arduino.h>

/*
  RaceLink ePaper helper (2.9\" BW, GxEPD2)

  All entry points are non-blocking: they queue work for a dedicated FreeRTOS
  worker task that owns the GxEPD2 display object. The worker runs on core 0
  (pinned) on ESP32-S3 and time-slices with the Arduino loop on single-core
  ESP32-S2.

  Public API:
    - void epaperInit();
        Spawns the worker task and queues a one-shot init request:
        SPI begin, display.init(), and the boot screen ("RaceLink Startblock"
        + WLED_RELEASE_NAME). Returns immediately; the panel will show the
        boot screen ~1 s later.

    - void setDisplayLayout(uint8_t numPilots);   // 1..4
        1: single row (nickname large, right full-height inverted bar)
        2..4: multi row (one row per slot, right inverted bar per row)

    - bool setPilotSlotData(const char* nickname, const char* raceLabel, uint8_t slot);
        Updates the stored data for the given slot (1..4) and starts / restarts
        a deferred refresh timer. The display is NOT updated immediately.
        Returns false if slot is out of range or exceeds the configured layout.

    - void service_epaper();
        Call this from loop(). When the deferred-refresh timer is due, it
        signals the worker task to render. Returns immediately; the actual
        render (~1 s on this panel) happens off the main loop.

  Notes:
    - SPI MOSI/SCK are configurable via build flags:
        -D RACELINK_EPAPER_SPI_MOSI=11
        -D RACELINK_EPAPER_SPI_SCK=12
      (MISO is typically unused; default -1)

    - Display control pins are configurable too:
        -D RACELINK_EPAPER_CS=...
        -D RACELINK_EPAPER_DC=...
        -D RACELINK_EPAPER_RST=...
        -D RACELINK_EPAPER_BUSY=...

    - WLED_RELEASE_NAME is printed on the start screen (fallback \"WLED\").
*/

void epaperInit();
void setDisplayLayout(uint8_t numPilots);
bool setPilotSlotData(const char* nickname, const char* raceLabel, uint8_t slot);
void service_epaper();

// Backwards-compatible name (kept to avoid breaking older sketches)
inline bool renderPilotScreen(const char* nickname, const char* raceLabel, uint8_t slot)
{
  return setPilotSlotData(nickname, raceLabel, slot);
}
