// racelink_transport_eth_emac.h -- RaceLink transport backend over the ESP32
// INTERNAL Ethernet MAC (EMAC) + RMII PHY, via WiFiUDP on the shared lwIP stack.
// Header-only, Arduino-friendly. No heap allocations on the hot path.
//
// This is the third transport backend, sibling to:
//   - racelink_transport_core.h     (LoRa / RadioLib)
//   - racelink_transport_eth.h      (Wiznet W5500 over SPI, own TCP/IP stack)
// It exposes the SAME `RaceLinkTransport::` namespace surface, selected at build
// time by -D RACELINK_ETH_EMAC (which also defines RACELINK_ETH so every
// medium-agnostic Ethernet code path in the usermod stays active).
//
// Why this is so much thinner than the W5500 backend: the GLEDOPTO GL-C-616WL is
// a classic ESP32 whose internal EMAC drives an external LAN8720 RMII PHY. WLED's
// own native Ethernet support (-D WLED_USE_ETHERNET -D WLED_ETH_DEFAULT=
// WLED_ETH_GLEDOPTO) brings the link up, runs DHCP through lwIP and reserves the
// RMII pins via PinManager. So this backend owns NO PHY/DHCP code at all -- it
// only opens a UDP socket on the shared lwIP stack and does the same medium-
// agnostic M2N/N2M framing translation as the W5500 backend (shared helpers in
// racelink_transport_common.h).
//
// Wire framing: identical to racelink_transport_eth.h (host speaks the same UDP
// datagrams regardless of which NIC the node uses). See
// memory `ethernet_block_e_wire_framing`.
//
// License: MIT
#pragma once

#include <Arduino.h>
#include <ETH.h>        // ESP32 internal-EMAC interface (global `ETH`); brought up by WLED
#include <WiFiUdp.h>    // UDP over the shared lwIP stack (works over the ETH netif)

#include "racelink_transport_common.h"  // address helpers, ETH framing helpers, RX stream templates

// -------------------- Build-flag configuration ------------------------------
// Only the UDP ports are configurable here. IP/subnet/gateway and DHCP-vs-static
// are owned by WLED's native Ethernet config, NOT by RACELINK_ETH_* flags.
#ifndef RACELINK_ETH_NODE_PORT
  #define RACELINK_ETH_NODE_PORT 5078
#endif
#ifndef RACELINK_ETH_HOST_PORT
  #define RACELINK_ETH_HOST_PORT 5079
#endif

namespace RaceLinkTransport {

// -------------------- PHY config (stub for source-compat) --------------------
// The LoRa backend's PhyCfg carries radio parameters; Ethernet has none.
struct PhyCfg {};

// -------------------- Callbacks (identical surface to the other backends) -----
struct Core;
struct Callbacks {
  void (*onRxPacket)(const uint8_t* pkt, uint8_t len, int16_t rssi, int8_t snr, void* ctx) = nullptr;
  void (*onTxStart)(void* ctx) = nullptr;
  void (*onTxDone)(void* ctx) = nullptr;
  void (*onRxWindowOpen)(uint16_t ms, void* ctx) = nullptr;
  void (*onRxWindowClosed)(uint16_t rxCountDelta, void* ctx) = nullptr;
  void (*onIdle)(void* ctx) = nullptr;
  void* ctx = nullptr;
};

// -------------------- Core state --------------------
// Same field layout as the W5500 Core (the usermod and the shared RX-reassembly
// templates read these names), except the transport member is a WiFiUDP socket
// instead of the self-contained W5500 driver.
struct Core {
  // --- identity ---
  uint8_t  myMac6[6]  = {0};
  uint8_t  myLast3[3] = {0};
  bool     macReadOK  = false;

  // --- Ethernet/UDP backend (internal EMAC via lwIP) ---
  WiFiUDP  udp;
  uint16_t nodePort   = RACELINK_ETH_NODE_PORT;
  uint8_t  hostIp[4]  = {0};        // learned host endpoint (reply target)
  uint16_t hostPort   = RACELINK_ETH_HOST_PORT;
  bool     hostKnown  = false;
  bool     netReady   = false;      // ETH has an IP and the UDP socket is bound
  bool     dhcpOk     = false;      // an address was acquired (DHCP or WLED static)
  uint8_t  ip[4]      = {0};        // own IP (snapshot of ETH.localIP())
  uint8_t  subnet[4]  = {0};
  uint8_t  gateway[4] = {0};

  // --- TX state (fire-and-forget: never actually pending) ---
  bool     txPending  = false;
  uint16_t txCount    = 0;
  uint32_t lastTxAtMs = 0;

  // --- RX telemetry (RF metrics are always 0 on Ethernet) ---
  int16_t  lastRssi      = 0;
  int8_t   lastSnr       = 0;
  uint16_t rxCountTotal  = 0;
  uint16_t rxCountFiltered = 0;
  uint32_t lastRxAtMs    = 0;

  // --- LoRa-only knobs kept as inert fields for source-compat ---
  bool     lbtEnable     = false;   // no LBT on a switched/wired medium
  uint32_t toaUsMaxPkt   = 0;       // no time-on-air concept
  uint16_t debug         = 0;

  // --- Stream state (shared RX reassembly; same layout as the other Cores) ---
  enum class StreamMode : uint8_t { None, Rx, Tx };
  StreamMode streamMode           = StreamMode::None;
  bool      streamActive          = false;
  bool      streamReady           = false;
  bool      streamLastScheduled   = false;
  uint8_t   streamBuf[128]        = {0};
  uint8_t   streamLen             = 0;
  uint8_t   streamOffset          = 0;
  uint8_t   streamLastPacketsLeft = 0;
  uint8_t   streamTotalPackets    = 0;
  uint8_t   streamIndex           = 0;
  uint16_t  streamPostRxMs        = 0;
  int8_t    streamPostRxNumWanted = -1;
  uint8_t   streamDst3[3]         = {0};
  uint8_t   streamSrc3[3]         = {0};
  uint8_t   streamType            = 0;
};

// -------------------- Config passed to beginCommon --------------------
// PHY/RMII pins are owned by WLED's initEthernet(); only the UDP node port is
// ours. Kept as a struct for source-compat with the W5500 backend's EthCfg.
struct EthCfg {
  uint16_t nodePort = RACELINK_ETH_NODE_PORT;
};

// -------------------- Helpers --------------------
// True once the EMAC link is up and lwIP has assigned an IP to the ETH netif.
inline bool ethHasAddress(uint8_t out[4]) {
  IPAddress ip = ETH.localIP();
  if ((ip[0] | ip[1] | ip[2] | ip[3]) == 0) return false;
  out[0] = ip[0]; out[1] = ip[1]; out[2] = ip[2]; out[3] = ip[3];
  return true;
}

// -------------------- Lifecycle --------------------
// WLED's native Ethernet (WLED_USE_ETHERNET + WLED_ETH_DEFAULT=WLED_ETH_GLEDOPTO)
// owns the PHY bring-up and DHCP, so there is nothing to init here but identity.
// service() opens the UDP socket once the ETH netif has an IP.
inline bool beginCommon(Core& rl, const EthCfg& cfg = EthCfg{}) {
  rl.nodePort = cfg.nodePort;
  // Identity from EFUSE (same source as the other backends). The NIC MAC is
  // owned by the EMAC/WLED, so we read EFUSE only for our 3-byte RaceLink id.
  if (readEfuseMac6(rl.myMac6)) {
    rl.macReadOK = true;
    last3FromMac6(rl.myLast3, rl.myMac6);
  }
  rl.netReady = false;  // flipped in service() once ETH has an IP + socket bound
  return true;
}

// LoRa ISR attach — no DIO1 on Ethernet. No-op for source-compat.
inline bool attachDio1(Core& /*rl*/) { return true; }

// LoRa "enter continuous RX" — Ethernet RX is always-on (polled in service()).
inline void setDefaultRxContinuous(Core& /*rl*/) {}

// -------------------- Send (N2M) --------------------
// Fire-and-forget. `buf` is the firmware-internal frame (Header7 + body) exactly
// as RaceLinkProto::build() produced it. jitterMaxMs is ignored (wired medium).
inline bool scheduleSend(Core& rl, const uint8_t* buf, uint8_t len, uint16_t /*jitterMaxMs*/ = 0) {
  if (!rl.netReady) return false;            // ETH not up yet

  uint8_t dg[1 + ETH_MAX_DGRAM];
  const uint8_t dgLen = buildN2M(buf, len, dg, sizeof(dg));
  if (dgLen == 0) return false;

  IPAddress dst;
  uint16_t  dport;
  if (rl.hostKnown) {
    dst   = IPAddress(rl.hostIp[0], rl.hostIp[1], rl.hostIp[2], rl.hostIp[3]);
    dport = rl.hostPort;
  } else {
    // Pre-discovery: directed subnet broadcast on the ETH interface (NOT the
    // limited 255.255.255.255 broadcast, whose egress is ambiguous on a multi-
    // netif lwIP stack while the WiFi AP is also up). 4-arg ctor avoids the
    // pinned-core IPAddress(int)/IPAddress(uint32_t) literal ambiguity.
    IPAddress lip = ETH.localIP();
    IPAddress msk = ETH.subnetMask();
    dst   = IPAddress((uint8_t)(lip[0] | (uint8_t)~msk[0]),
                      (uint8_t)(lip[1] | (uint8_t)~msk[1]),
                      (uint8_t)(lip[2] | (uint8_t)~msk[2]),
                      (uint8_t)(lip[3] | (uint8_t)~msk[3]));
    dport = (uint16_t)RACELINK_ETH_HOST_PORT;
  }

  bool ok = false;
  if (rl.udp.beginPacket(dst, dport)) {
    rl.udp.write(dg, dgLen);
    ok = (rl.udp.endPacket() == 1);
  }
  if (ok) { ++rl.txCount; rl.lastTxAtMs = millis(); }
  rl.txPending = false;  // never queued
  return ok;
}

// -------------------- Service (RX pump) --------------------
// Once ETH has an IP, bind the UDP socket; then drain inbound M2N datagrams,
// learn the host endpoint, and hand each one to cb.onRxPacket() as a
// reconstructed Header7 frame (identical handling to the W5500 backend).
inline void service(Core& rl, const Callbacks& cb) {
  if (!rl.netReady) {
    if (!ethHasAddress(rl.ip)) return;                 // link/DHCP not up yet
    IPAddress sn = ETH.subnetMask();
    IPAddress gw = ETH.gatewayIP();
    for (int i = 0; i < 4; ++i) { rl.subnet[i] = sn[i]; rl.gateway[i] = gw[i]; }
    if (!rl.udp.begin(rl.nodePort)) return;            // retry next tick on bind failure
    rl.dhcpOk   = true;                                // address acquired (DHCP or WLED static)
    rl.netReady = true;
  }

  for (int sz = rl.udp.parsePacket(); sz > 0; sz = rl.udp.parsePacket()) {
    uint8_t dg[ETH_MAX_DGRAM];
    int n = rl.udp.read(dg, sizeof(dg));
    if (n < 4) continue;                               // need at least type_full + recv3

    const uint8_t typeFull = dg[0];
    if ((typeFull & 0x80) != 0x00) continue;           // only M2N (DIR_M2N bit7 clear)

    // Learn the host endpoint for replies.
    IPAddress rip = rl.udp.remoteIP();
    rl.hostIp[0] = rip[0]; rl.hostIp[1] = rip[1]; rl.hostIp[2] = rip[2]; rl.hostIp[3] = rip[3];
    rl.hostPort  = rl.udp.remotePort();
    rl.hostKnown = true;

    // Reconstruct the firmware-internal Header7 frame.
    uint8_t frame[ETH_MAX_DGRAM];
    uint8_t flen = 0;
    if (!reconstructM2N(dg, n, frame, flen)) continue;

    ++rl.rxCountTotal;

    // Parity with the other backends: drop datagrams not addressed to us before
    // the callback (handlePacket re-checks, but filtering here matches LoRa/W5500).
    RaceLinkProto::Header7 h{};
    if (!RaceLinkProto::parseHeader(frame, flen, h)) continue;
    if (!receiverMatches(h.receiver, rl.myLast3)) continue;

    rl.lastRssi = 0;
    rl.lastSnr  = 0;
    rl.lastRxAtMs = millis();
    ++rl.rxCountFiltered;

    if (cb.onRxPacket) cb.onRxPacket(frame, flen, 0, 0, cb.ctx);
  }
}

} // namespace RaceLinkTransport
