---
title: "CCNA 1.1 Roles and functions of network components"
date: 2026-06-27 00:00:00 -0300
categories: [CCNA, Network Fundamentals]
tags: [ccna]
---
# CCNA 200-301 v1.1 — Topic 1.1
# Explain the Role and Function of Network Components

> **Exam domain:** 1.0 Network Fundamentals (20% of the exam)
> **Blueprint items covered:**
> - 1.1.a Routers
> - 1.1.b Layer 2 and Layer 3 switches
> - 1.1.c Next-generation firewalls and IPS
> - 1.1.d Access points
> - 1.1.e Controllers (Cisco DNA Center / Catalyst Center and WLC)
> - 1.1.f Endpoints
> - 1.1.g Servers
> - 1.1.h PoE

---

## Table of Contents

1. [Big Picture: How the Components Fit Together](#1-big-picture-how-the-components-fit-together)
2. [Quick Review: OSI and TCP/IP Layers](#2-quick-review-osi-and-tcpip-layers)
3. [Collision Domains and Broadcast Domains](#3-collision-domains-and-broadcast-domains)
4. [Routers](#4-routers)
5. [Layer 2 Switches](#5-layer-2-switches)
6. [Layer 3 Switches (Multilayer Switches)](#6-layer-3-switches-multilayer-switches)
7. [Firewalls and Next-Generation Firewalls (NGFW)](#7-firewalls-and-next-generation-firewalls-ngfw)
8. [IDS and IPS](#8-ids-and-ips)
9. [Access Points (APs)](#9-access-points-aps)
10. [Wireless LAN Controllers (WLC)](#10-wireless-lan-controllers-wlc)
11. [Cisco DNA Center / Catalyst Center (SDN Controller)](#11-cisco-dna-center--catalyst-center-sdn-controller)
12. [Endpoints](#12-endpoints)
13. [Servers](#13-servers)
14. [Power over Ethernet (PoE)](#14-power-over-ethernet-poe)
15. [Legacy Devices You Should Still Recognize](#15-legacy-devices-you-should-still-recognize)
16. [Master Comparison Tables](#16-master-comparison-tables)
17. [Useful CLI Commands](#17-useful-cli-commands)
18. [Exam Tips and Common Traps](#18-exam-tips-and-common-traps)
19. [Key Terms Glossary](#19-key-terms-glossary)
20. [Practice Questions (with Answers)](#20-practice-questions-with-answers)

---

## 1. Big Picture: How the Components Fit Together

A typical small/medium enterprise network:

```
                         INTERNET
                            |
                     [ ISP / WAN link ]
                            |
                       +---------+
                       | ROUTER  |  <- connects different networks (LAN <-> WAN), NAT, routing
                       +---------+
                            |
                     +-------------+
                     |    NGFW     |  <- stateful filtering, app control, IPS, URL filtering
                     +-------------+
                            |
               +---------------------------+
               |  L3 CORE/DISTRIBUTION SW  |  <- inter-VLAN routing at wire speed
               +---------------------------+
                  /          |            \
          +--------+    +--------+     +-----------+
          | L2 SW  |    | L2 SW  |     |  SERVERS  | <- DHCP, DNS, file, web, AD...
          | (PoE)  |    | (PoE)  |     +-----------+
          +--------+    +--------+
          /   |    \        |   \
       [PC] [IP   [AP]   [PC] [Printer]          +------+      +-----------------+
            Phone] ))                            | WLC  |      | Catalyst Center |
                   ))  wireless clients          +------+      |  (DNA Center)   |
                       (laptops, phones)          manages APs   +-----------------+
                                                  via CAPWAP    manages the whole
                                                                network (SDN)
```

**Mental model:**

| Component | One-sentence job |
|---|---|
| Endpoint | Generates and consumes data (the "user" of the network). |
| Server | Provides services/resources to endpoints. |
| L2 switch | Connects devices **within the same LAN/VLAN** using MAC addresses. |
| L3 switch | L2 switch + routing between VLANs/subnets in hardware. |
| Router | Connects **different networks** and forwards packets using IP addresses. |
| Firewall / NGFW | Controls which traffic is **allowed** between security zones. |
| IPS | Inspects traffic inline and **blocks** malicious traffic. |
| Access Point | Connects **wireless** clients to the wired network. |
| WLC | Centrally manages/controls many APs. |
| Catalyst Center (DNA Center) | Centrally manages/automates/monitors the **entire** network (SDN controller). |
| PoE | Delivers **electrical power** over the Ethernet cable to devices like APs, phones and cameras. |

---

## 2. Quick Review: OSI and TCP/IP Layers

Knowing the layer each device operates at is critical for this topic.

| OSI Layer | Name | PDU | Address / Info | Typical devices |
|---|---|---|---|---|
| 7 | Application | Data | — | NGFW (app awareness), servers, endpoints |
| 6 | Presentation | Data | — | — |
| 5 | Session | Data | — | — |
| 4 | Transport | Segment (TCP) / Datagram (UDP) | Port numbers | Stateful firewalls |
| 3 | Network | Packet | IP address | **Routers, L3 switches** |
| 2 | Data Link | Frame | MAC address | **Switches, bridges, APs**, NICs |
| 1 | Physical | Bits | Signals, cables, connectors | Hubs, repeaters, cables, transceivers |

TCP/IP model (as used in Cisco material): **Application – Transport – Network (Internet) – Data Link – Physical** (5-layer "updated" model) or 4-layer (Application, Transport, Internet, Link).

Encapsulation order (sender): Data → Segment → Packet → Frame → Bits.

---

## 3. Collision Domains and Broadcast Domains

| Device | Breaks collision domains? | Breaks broadcast domains? |
|---|---|---|
| Hub / repeater | ❌ No (all ports share one collision domain) | ❌ No |
| Bridge | ✅ Yes (each port) | ❌ No |
| L2 switch | ✅ Yes (**each port = its own collision domain**) | ❌ No (unless VLANs are used — **each VLAN = one broadcast domain**) |
| Router | ✅ Yes | ✅ Yes (**each interface = its own broadcast domain**) |
| L3 switch | ✅ Yes | ✅ Yes (between VLANs/routed ports) |

- **Collision domain:** a segment where two simultaneous transmissions collide. Only relevant for half-duplex (hubs). Full-duplex switch ports have **no collisions**, and CSMA/CD is effectively disabled.
- **Broadcast domain:** the set of devices that receive a Layer 2 broadcast (destination MAC `FFFF.FFFF.FFFF`) sent by any one of them. **Routers do not forward broadcasts by default.**

> **Classic exam counting question:** "A router connects two switches; each switch has 4 PCs (no VLANs). How many broadcast domains?" → **2** (one per router interface). Collision domains → count switch ports in use plus the router links.

---

## 4. Routers

### 4.1 Role

A router is a **Layer 3** device that **forwards packets between different IP networks (subnets)**. It is the boundary between networks, and is the device that connects a LAN to the WAN/Internet.

### 4.2 Main functions

1. **Path determination:** choosing the best path to a destination using the **routing table**.
2. **Packet forwarding (switching):** moving the packet from the ingress interface to the correct egress interface.
3. **Separating broadcast domains:** every router interface is a separate broadcast domain and a separate subnet.
4. **Re-encapsulation at each hop:** the router strips the incoming L2 frame, inspects the L3 header, decrements the **TTL**, recomputes the IPv4 header checksum, and builds a **new L2 frame** (new source/destination MAC) for the next hop. **IP addresses stay the same end-to-end (without NAT); MAC addresses change at each hop.**
5. **Additional services** (common on enterprise/branch routers):
   - NAT/PAT
   - DHCP server or DHCP relay (`ip helper-address`)
   - ACLs (basic packet filtering)
   - VPNs (IPsec, GRE, DMVPN)
   - QoS
   - WAN connectivity (Ethernet WAN, serial, MPLS, LTE/5G)
   - First Hop Redundancy (HSRP, VRRP, GLBP)

### 4.3 How a router builds its routing table

| Source | Code in `show ip route` | Administrative Distance (AD) |
|---|---|---|
| Directly connected | `C` | 0 |
| Local (the interface's own /32 address) | `L` | 0 |
| Static | `S` | 1 |
| eBGP | `B` | 20 |
| EIGRP (internal) | `D` | 90 |
| OSPF | `O` | 110 |
| IS-IS | `i` | 115 |
| RIP | `R` | 120 |
| EIGRP (external) | `D EX` | 170 |
| iBGP | `B` | 200 |
| Unusable | — | 255 |

### 4.4 Route selection logic (order matters!)

1. **Longest prefix match** — the most specific route wins (a /28 beats a /24 beats a /0).
2. If prefixes are identical from different sources → **lowest AD** wins.
3. If same source/protocol → **lowest metric** wins.
4. If metrics tie → load balancing (ECMP).

### 4.5 Forwarding methods (Cisco)

- **Process switching:** CPU handles every packet (slow).
- **Fast switching:** first packet process-switched, result cached.
- **CEF (Cisco Express Forwarding):** default today. Uses the **FIB** (built from the routing table) and the **adjacency table** (L2 rewrite info). Fast and scalable.

### 4.6 Router types you may see referenced

- **Branch / edge / ISR routers** (e.g., Cisco ISR 1000/4000, Catalyst 8200/8300).
- **Aggregation / core routers** (ASR, Catalyst 8500).
- **Virtual routers** (Catalyst 8000V, formerly CSR1000v) in the cloud.

---

## 5. Layer 2 Switches

### 5.1 Role

A Layer 2 switch connects end devices in the **same LAN / same VLAN**, forwarding **frames** based on **destination MAC addresses**. It is the primary access-layer device in a modern LAN.

### 5.2 The three actions of a switch

| Action | What happens |
|---|---|
| **Learn** | Reads the **source MAC** of every incoming frame and records `MAC → port (VLAN)` in the **MAC address table** (CAM table). |
| **Forward / Filter** | Looks up the **destination MAC**. If known: forward **only** out the associated port (*known unicast*). If the destination is on the same port it came from: **filter** (drop). |
| **Flood** | Sends the frame out **all ports in the same VLAN except the incoming port** when the destination is: **unknown unicast**, **broadcast** (`FFFF.FFFF.FFFF`), or **multicast** (without IGMP snooping). |

- MAC table entries **age out** after **300 seconds (5 minutes)** of inactivity by default.
- The MAC table is stored in **CAM** (Content Addressable Memory) for fast lookups.

### 5.3 Switching methods

| Method | Behavior | Latency | Error checking |
|---|---|---|---|
| **Store-and-forward** | Receives the entire frame, checks the **FCS (CRC)**, then forwards | Highest | ✅ Drops bad frames |
| **Cut-through** | Forwards after reading the **destination MAC** (first 6 bytes after preamble) | Lowest | ❌ Forwards errored frames |
| **Fragment-free** | Reads the first **64 bytes** (collisions happen in that window) | Medium | Partial |

Most Cisco Catalyst switches use **store-and-forward**.

### 5.4 Key L2 switch features (related to other blueprint topics)

- **VLANs** (logical segmentation; each VLAN = one broadcast domain and normally one IP subnet)
- **Trunking** with **802.1Q** (tags frames with the VLAN ID; native VLAN untagged)
- **STP / RSTP** (prevents Layer 2 loops)
- **EtherChannel** (LACP/PAgP — bundles links)
- **Port security**, DHCP snooping, DAI (security)
- **CDP / LLDP** (neighbor discovery)
- **PoE** on access switches (powers phones, APs, cameras)

### 5.5 Important: an L2 switch still has an IP address

A pure L2 switch does **not** route, but it is normally given an IP address on an **SVI** (e.g., `interface vlan 1` or a management VLAN) **only for management** (SSH, SNMP, syslog). It also needs a **default gateway** (`ip default-gateway x.x.x.x`) to be reached from other subnets.

```
Switch(config)# interface vlan 99
Switch(config-if)# ip address 192.168.99.10 255.255.255.0
Switch(config-if)# no shutdown
Switch(config)# ip default-gateway 192.168.99.1
```

---

## 6. Layer 3 Switches (Multilayer Switches)

### 6.1 Role

A Layer 3 switch performs **all L2 switching functions** plus **IP routing**, typically to route **between VLANs** inside the campus. It routes in **hardware (ASICs)** at wire speed, using CEF.

### 6.2 L3 interfaces on a multilayer switch

| Interface type | Description |
|---|---|
| **SVI (Switched Virtual Interface)** | Virtual interface for a VLAN (`interface vlan 10`). Acts as the **default gateway** for hosts in that VLAN. |
| **Routed port** | Physical port converted to L3 with `no switchport`. Behaves like a router interface (no VLAN association). Used for point-to-point links to routers or other L3 switches. |
| **L3 EtherChannel** | Port-channel configured with `no switchport`. |

```
Switch(config)# ip routing                     ! enables routing (off by default on many models)
Switch(config)# interface vlan 10
Switch(config-if)# ip address 10.10.10.1 255.255.255.0
Switch(config)# interface gigabitEthernet1/0/48
Switch(config-if)# no switchport
Switch(config-if)# ip address 10.0.0.1 255.255.255.252
```

### 6.3 L3 switch vs. router

| Characteristic | Layer 3 switch | Router |
|---|---|---|
| Primary use | Campus LAN, inter-VLAN routing (distribution/core) | WAN edge, Internet edge, branch |
| Forwarding | Hardware (ASICs), very high throughput, low latency | Software/hardware; generally lower port density |
| Port density | High (24/48 Ethernet ports) | Low |
| WAN interfaces | Usually Ethernet only | Ethernet, serial, LTE/5G, DSL, etc. |
| Advanced features (NAT, VPN, deep QoS, BGP full tables) | Limited | Rich |
| Cost per port | Low | High |

### 6.4 Inter-VLAN routing options (for context)

1. **Router with one physical interface per VLAN** (legacy, does not scale).
2. **Router-on-a-stick (ROAS):** one trunk to the router, with **subinterfaces** using `encapsulation dot1q <vlan>`.
3. **Layer 3 switch with SVIs** — the **preferred** modern approach.

---

## 7. Firewalls and Next-Generation Firewalls (NGFW)

### 7.1 Role of a firewall

A firewall **enforces security policy** by controlling which traffic is permitted between **security zones** (e.g., *inside*, *outside*, *DMZ*). Default behavior on the classic Cisco ASA model: traffic from a higher-security zone to a lower-security zone is allowed, return traffic is allowed automatically (stateful), and unsolicited traffic from outside is **denied**.

### 7.2 Evolution of firewalls

| Generation | Inspects | Notes |
|---|---|---|
| **Packet filter (stateless)** | L3/L4 header fields (IP, protocol, port) per packet | Like a router ACL; no session awareness. Return traffic must be explicitly permitted. |
| **Stateful firewall** | L3/L4 + **connection state table** | Tracks sessions (e.g., TCP handshake). Automatically allows return traffic for permitted sessions. Example: Cisco ASA. |
| **Application-layer / proxy firewall** | Up to L7 for specific protocols | Acts as an intermediary. |
| **Next-Generation Firewall (NGFW)** | L3 → **L7**, plus threat intelligence | Stateful **+** application awareness **+** integrated IPS **+** malware and URL filtering. Example: **Cisco Secure Firewall (Firepower) / FTD**. |

### 7.3 Security zones (typical)

```
   OUTSIDE (Internet)  -----[ FIREWALL ]-----  INSIDE (trusted LAN)
                                |
                               DMZ  (public-facing servers: web, mail, DNS)
```

- **Inside:** trusted users.
- **Outside:** untrusted (Internet).
- **DMZ (Demilitarized Zone):** semi-trusted zone for servers that must be reachable from the Internet, isolated from the inside network.

### 7.4 What makes a firewall "next-generation"

| NGFW capability | What it does |
|---|---|
| **Traditional stateful inspection** | Baseline L3/L4 filtering and NAT. |
| **Application Visibility and Control (AVC)** | Identifies applications by their behavior/signatures, **not just port numbers** (e.g., blocks BitTorrent or Facebook games even on port 443/80). |
| **Integrated NGIPS** | Inline intrusion prevention (Cisco: Snort-based). |
| **URL filtering** | Permits/blocks websites by **category** and **reputation**. |
| **Advanced Malware Protection (AMP) / Secure Malware Defense** | File reputation, sandboxing, retrospective detection. |
| **Identity awareness** | Policies based on **user/group** (e.g., integration with AD or Cisco ISE), not only IP. |
| **TLS/SSL decryption** | Inspects encrypted traffic. |
| **Threat intelligence feeds** | Cisco **Talos** keeps signatures and reputation up to date. |

Cisco products: **Cisco Secure Firewall (formerly Firepower)** running **FTD (Firepower Threat Defense)**, managed by **FMC (Firepower/Secure Firewall Management Center)** or FDM (local). The legacy **ASA** is a classic stateful firewall (ASA with FirePOWER Services added NGFW features).

### 7.5 Router ACL vs. stateful firewall vs. NGFW

| Feature | Router ACL | Stateful FW | NGFW |
|---|---|---|---|
| Filters on IP/port | ✅ | ✅ | ✅ |
| Tracks connection state | ❌ (reflexive ACLs aside) | ✅ | ✅ |
| Application identification (L7) | ❌ | ❌/limited | ✅ |
| IPS | ❌ | ❌ | ✅ |
| URL filtering / malware | ❌ | ❌ | ✅ |
| User identity | ❌ | ❌ | ✅ |

---

## 8. IDS and IPS

### 8.1 Definitions

| | **IDS — Intrusion Detection System** | **IPS — Intrusion Prevention System** |
|---|---|---|
| Placement | **Out-of-band / promiscuous**: receives a **copy** of traffic (SPAN port or network TAP) | **Inline**: traffic physically flows **through** it |
| Action | **Detects and alerts** (logs, notifies, may send TCP resets) | **Detects and blocks** in real time (drops packets, resets connections, blocks sources) |
| Impact on traffic | None (no added latency; failure doesn't break the network) | Adds some latency; a failure can impact traffic (fail-open vs. fail-closed) |
| Stops the first malicious packet? | ❌ No | ✅ Yes |

### 8.2 Detection methods

| Method | How it works | Pros / Cons |
|---|---|---|
| **Signature-based** | Matches traffic against a database of known attack patterns | Accurate for known threats; can't detect **zero-day** attacks; requires updates |
| **Anomaly-based (statistical/behavioral)** | Learns a baseline of "normal" and flags deviations | Can catch new attacks; more **false positives** |
| **Policy-based** | Alerts on violations of a defined policy | Requires careful policy definition |
| **Reputation-based** | Uses threat intel about known-bad IPs/domains | Depends on intel quality |

### 8.3 Alert terminology (good to know)

| Term | Meaning |
|---|---|
| **True positive** | Real attack, correctly alerted ✅ |
| **True negative** | Normal traffic, correctly not alerted ✅ |
| **False positive** | Normal traffic **wrongly** flagged as an attack (annoying) |
| **False negative** | Real attack **not** detected (**most dangerous**) |

### 8.4 NGIPS and integration

Modern IPS is typically **integrated into the NGFW** (Cisco Secure Firewall/FTD uses **Snort**). Standalone NGIPS appliances exist as well (Cisco Secure IPS). NGIPS adds **context awareness** (knowing which OS/apps are on the hosts being targeted), reducing irrelevant alerts.

---

## 9. Access Points (APs)

### 9.1 Role

An Access Point connects **wireless (IEEE 802.11) clients** to the **wired (IEEE 802.3) network**. It operates primarily at **Layer 2**, acting as a **bridge** between the two media and translating 802.11 frames into 802.3 frames (and vice-versa).

### 9.2 Key wireless terms

| Term | Meaning |
|---|---|
| **SSID** | Service Set Identifier — the human-readable network name. |
| **BSS** | Basic Service Set — one AP and its associated clients. |
| **BSSID** | The AP radio's MAC address that identifies the BSS. |
| **BSA** | Basic Service Area — the AP's coverage area (cell). |
| **ESS** | Extended Service Set — multiple APs with the same SSID, connected by a wired distribution system, enabling **roaming**. |
| **DS** | Distribution System — the wired network that connects APs. |
| **IBSS** | Independent BSS — ad hoc, client-to-client, no AP. |
| **Half-duplex / CSMA/CA** | Wireless is a shared medium; clients use **CSMA/CA** (Collision Avoidance) instead of CSMA/CD. |

### 9.3 AP deployment architectures

| Architecture | Description | Management | Example |
|---|---|---|---|
| **Autonomous AP** | Standalone, fully configured individually; handles all functions itself | Each AP individually (CLI/GUI) | Small sites; legacy Cisco Aironet IOS APs |
| **Lightweight AP (LAP)** | Works with a **WLC**; uses **split-MAC** architecture; tunnels traffic over **CAPWAP** | Centrally via the WLC | Enterprise campuses |
| **Cloud-based AP** | Managed from a cloud dashboard; data traffic stays local | Cloud (e.g., **Cisco Meraki** Dashboard) | Distributed organizations, branch offices |

**Autonomous AP switch-port config:** typically a **trunk** (to serve multiple SSIDs/VLANs locally).
**Lightweight AP (local mode) switch-port config:** typically an **access port** (all client traffic is tunneled in CAPWAP to the WLC).

### 9.4 Lightweight AP modes (Cisco) — useful for the wireless topics

| Mode | Purpose |
|---|---|
| **Local** | Default. Serves clients; tunnels traffic to the WLC via CAPWAP. |
| **FlexConnect** | Can switch client traffic **locally** at the branch and keep working if the WLC link fails. |
| **Monitor** | Doesn't serve clients; scans for rogues/IDS/location. |
| **Sniffer** | Captures 802.11 frames and sends them to an analyzer (e.g., Wireshark). |
| **Rogue detector** | Detects rogue devices on the wired network. |
| **Bridge / Mesh** | Point-to-point/point-to-multipoint wireless links between APs. |
| **SE-Connect** | Spectrum analysis (spectrum expert). |

### 9.5 Powering APs

APs are usually **powered via PoE** from the access switch (see section 14). Modern Wi-Fi 6/6E/7 APs often require **PoE+ (802.3at)** or **UPOE/802.3bt** for full functionality.

---

## 10. Wireless LAN Controllers (WLC)

### 10.1 Role

A WLC **centrally manages, configures and controls lightweight APs**. Instead of configuring 200 APs one by one, you configure WLANs (SSIDs), security and RF policy once on the controller.

### 10.2 Split-MAC architecture

The 802.11 MAC functions are **split** between the AP and the WLC:

| Lightweight AP handles (**real-time** functions) | WLC handles (**management** functions) |
|---|---|
| Sending/receiving 802.11 frames | Client **authentication** (802.1X/RADIUS integration) |
| Beacons and probe responses | **Association/reassociation** (roaming) |
| Frame acknowledgments and retransmissions | **Security** policy management |
| MAC-layer data **encryption/decryption** | **QoS** policies |
| Frame queuing and packet prioritization | **RF management** (RRM — automatic channel & power assignment) |
| | Bridging 802.11 to 802.3 / mapping SSIDs to VLANs |

### 10.3 CAPWAP

**CAPWAP (Control And Provisioning of Wireless Access Points)** — standards-based protocol (RFC 5415) between LAP and WLC. It creates **two tunnels**:

| Tunnel | UDP port | Encrypted? |
|---|---|---|
| **Control** (management/config) | **UDP 5246** | ✅ Yes, by default (DTLS) |
| **Data** (client traffic) | **UDP 5247** | ❌ Not by default (optional DTLS) |

> CAPWAP replaced Cisco's earlier **LWAPP**. Because CAPWAP runs over UDP/IP, the AP and the WLC can be in **different subnets** (it's an L3 tunnel).

AP discovery of the WLC: broadcast in the local subnet, **DHCP option 43**, **DNS** (`CISCO-CAPWAP-CONTROLLER.<local-domain>`), previously learned/primed controllers.

### 10.4 WLC deployment models

| Model | Where the WLC lives | Typical scale |
|---|---|---|
| **Unified / centralized** | Dedicated hardware appliance in the data center/core (e.g., **Catalyst 9800-40/80**) | Large campuses, thousands of APs |
| **Cloud-based** | WLC as a VM in a public/private cloud (**Catalyst 9800-CL**) | Flexible, scalable |
| **Embedded** | WLC function running **inside a switch** (e.g., Catalyst 9300/9400) | Small campuses/branches |
| **Mobility Express / EWC (Embedded Wireless Controller on AP)** | WLC function runs **on one of the APs** | Small sites (~100 APs or less) |

### 10.5 WLC ports and interfaces (AireOS terminology — appears in CCNA material)

- **Ports (physical):** service port (out-of-band management), distribution system ports (connect to switch, usually trunk / LAG), console, redundancy port.
- **Interfaces (logical):** management interface (in-band mgmt + CAPWAP), dynamic interfaces (map WLANs to VLANs), virtual interface (DHCP relay/web-auth, e.g., 192.0.2.1), service-port interface, redundancy management.
- WLC distribution ports are commonly bundled with **LAG** (static EtherChannel — **mode on**, no LACP/PAgP on AireOS).

---

## 11. Cisco DNA Center / Catalyst Center (SDN Controller)

> **Naming note:** In 2023 Cisco renamed **Cisco DNA Center** to **Cisco Catalyst Center**. The exam blueprint text says "Cisco DNA Center"; treat both names as the same product.

### 11.1 Role

Catalyst Center is Cisco's **enterprise SDN controller and network management platform**. It centralizes **design, policy, provisioning and assurance** for the campus/branch network (switches, routers, WLCs, APs). It is the foundation of Cisco's **Intent-Based Networking (IBN)** and **SD-Access**.

### 11.2 Traditional vs. controller-based networking

| Traditional | Controller-based (SDN) |
|---|---|
| Each device has its own **control plane** and **management plane**; configured box-by-box via CLI | A controller centralizes management (and in some designs, part of the control plane) |
| Distributed, manual, error-prone | Centralized, automated, consistent |
| Changes take time; configuration drift | Policy defined once, pushed everywhere |

**Planes:**
- **Data (forwarding) plane:** forwards traffic (frames/packets).
- **Control plane:** builds the tables used for forwarding (routing protocols, STP, ARP, MAC learning).
- **Management plane:** configuring and monitoring devices (SSH, SNMP, syslog, NETCONF).

### 11.3 Controller interfaces (APIs)

```
          +---------------------------+
          |  Apps / scripts / ITSM    |   (Python, Ansible, ServiceNow...)
          +---------------------------+
                      ^
                      |  NORTHBOUND API  (REST API, JSON/HTTPS)
          +---------------------------+
          |     CATALYST CENTER       |
          |   (SDN CONTROLLER)        |
          +---------------------------+
                      |
                      v  SOUTHBOUND API / protocols
         (SSH/CLI, SNMP, NETCONF/YANG, RESTCONF, OpenFlow*, OpFlex*)
                      |
       +-------+  +-------+  +-------+  +-----+
       |Switch |  |Router |  |  WLC  |  | AP  |
       +-------+  +-------+  +-------+  +-----+
```
\*OpenFlow/OpFlex are generic SDN southbound examples; Catalyst Center primarily uses SSH, SNMP and NETCONF.

- **Northbound Interface (NBI):** between the controller and applications/administrators — **REST API**.
- **Southbound Interface (SBI):** between the controller and network devices.

### 11.4 Main functions/workflows of Catalyst Center

| Area | Function |
|---|---|
| **Design** | Define network hierarchy (sites, buildings, floors), IP pools, DHCP/DNS settings, wireless settings, image repository. |
| **Policy** | Define intent-based policies (group-based access control, QoS, application policies). |
| **Provision** | Automate device onboarding (**Plug and Play / zero-touch**), push configurations and templates, upgrade software images (SWIM). |
| **Assurance** | Monitor network and client **health scores**, AI/ML-driven analytics, **path trace**, root-cause analysis, suggested remediation. |
| **Platform** | REST APIs, integrations (ITSM, ISE, third-party). |

Other capabilities: **SD-Access** fabric automation (with **Cisco ISE** for identity/policy), compliance checks, topology views, software image management.

### 11.5 WLC vs. Catalyst Center (common confusion)

| | WLC | Catalyst Center |
|---|---|---|
| Scope | Wireless only (APs, WLANs, RF) | Entire enterprise network (wired + wireless, routers, switches, WLCs) |
| Function | Controls and manages lightweight APs (split-MAC, CAPWAP) | SDN controller: automation, policy, assurance, APIs |
| In the data path? | Yes (local-mode traffic is tunneled through it) | **No** — management/control platform, not forwarding user traffic |

---

## 12. Endpoints

### 12.1 Definition

**Endpoints** (end devices / hosts) are the **source or final destination** of data on the network. They are where users or applications interact with the network.

### 12.2 Examples

- Desktops, laptops, workstations
- Smartphones and tablets
- IP phones (VoIP)
- Printers and scanners
- IP cameras (CCTV)
- **IoT devices**: sensors, smart thermostats, badge readers, medical devices, industrial controllers
- Point-of-sale (POS) terminals
- Virtual machines acting as clients

### 12.3 Characteristics

- Have a **NIC** with a unique **MAC address**.
- Require **IP configuration**: IP address, subnet mask, **default gateway**, DNS server (static or via DHCP / SLAAC for IPv6).
- Often the **most vulnerable** part of the network → protected by endpoint security (antivirus/EDR, Cisco Secure Endpoint), **802.1X/NAC** (Cisco ISE), and posture assessment.
- Many endpoints (phones, cameras, APs, IoT) are **powered by PoE**.

### 12.4 Viewing host IP configuration (good for troubleshooting topics)

| OS | Command |
|---|---|
| Windows | `ipconfig /all`, `arp -a`, `route print` |
| Linux | `ip address`, `ip route`, `ip neigh` |
| macOS | `ifconfig`, `netstat -rn`, `networksetup` |

---

## 13. Servers

### 13.1 Definition

A **server** is a computer (physical, virtual or containerized) running software that **provides services or resources to other devices (clients)**. "Server" describes a **role**, not specific hardware — any host can be a server if it runs server software.

### 13.2 Client-server vs. peer-to-peer

| Model | Description | Pros | Cons |
|---|---|---|---|
| **Client-server** | Dedicated servers provide resources; clients request them | Centralized control, security, backup, scalability | Server cost; single point of failure (mitigated with redundancy) |
| **Peer-to-peer (P2P)** | Each host can act as client and server | Cheap, simple for small setups | Decentralized, hard to secure and manage, doesn't scale |

### 13.3 Common server roles and their protocols/ports

| Server role | Protocol | Port(s) |
|---|---|---|
| Web | HTTP / HTTPS | TCP 80 / TCP 443 |
| DNS | DNS | UDP 53 (and TCP 53 for zone transfers/large replies) |
| DHCP | DHCP | UDP 67 (server) / UDP 68 (client) |
| File transfer | FTP | TCP 20 (data) / TCP 21 (control) |
| Trivial file transfer | TFTP | UDP 69 |
| Secure file transfer | SFTP/SCP (over SSH) | TCP 22 |
| Email (send) | SMTP | TCP 25 (587 submission) |
| Email (receive) | POP3 / IMAP | TCP 110 / TCP 143 |
| Remote management | SSH / Telnet | TCP 22 / TCP 23 |
| Network management | SNMP | UDP 161 (polling) / UDP 162 (traps) |
| Logging | Syslog | UDP 514 |
| Time | NTP | UDP 123 |
| AAA | RADIUS / TACACS+ | UDP 1812-1813 (1645-1646 legacy) / TCP 49 |
| Directory | LDAP / LDAPS | TCP 389 / TCP 636 |
| File sharing | SMB | TCP 445 |
| Remote desktop | RDP | TCP 3389 |

### 13.4 Server-related concepts

- **Virtualization:** a **hypervisor** runs multiple VMs on one physical host.
  - **Type 1 (bare-metal):** VMware ESXi, Microsoft Hyper-V, KVM, Xen/XCP-ng.
  - **Type 2 (hosted):** VMware Workstation, VirtualBox.
- **Containers:** lightweight, share the host OS kernel (Docker, Kubernetes).
- **Data center connectivity:** servers often connect with **NIC teaming / bonding** (EtherChannel/LACP) to two switches for redundancy, usually at 10/25/40/100 Gbps.
- **Placement:** public-facing servers go in the **DMZ**; internal servers in a protected **server farm / data center** segment.
- **Cloud:** servers can be on-premises, in a public cloud (IaaS), or consumed as a service (SaaS) — see CCNA topic 1.2/1.12.

---

## 14. Power over Ethernet (PoE)

### 14.1 Role

**PoE** delivers **DC electrical power and data over the same twisted-pair Ethernet cable**, eliminating the need for a separate power outlet/adapter at the device.

### 14.2 Terminology

| Term | Meaning |
|---|---|
| **PSE — Power Sourcing Equipment** | The device that **provides** power: a PoE switch (*endspan*) or a **PoE injector** (*midspan*). |
| **PD — Powered Device** | The device that **receives** power: IP phone, AP, IP camera, IoT sensor, thin client, LED lighting. |
| **Endspan** | PSE built into the switch. |
| **Midspan** | PoE injector placed between a non-PoE switch and the PD. |
| **Power budget** | The **total** power the switch's power supplies can give to all PoE ports combined. |

### 14.3 PoE standards (memorize this table!)

| Standard | Common name | IEEE | Max power at PSE (per port) | Power guaranteed at PD | Pairs used |
|---|---|---|---|---|---|
| Cisco Inline Power (pre-standard) | ILP | Cisco proprietary | ~7 W | ~6.3 W | 2 |
| **802.3af** (2003) | **PoE** (Type 1) | ✅ | **15.4 W** | **12.95 W** | 2 |
| **802.3at** (2009) | **PoE+** (Type 2) | ✅ | **30 W** | **25.5 W** | 2 |
| Cisco UPOE | **Universal PoE** | Cisco proprietary | **60 W** | ~51 W | **4** |
| **802.3bt** (2018) Type 3 | **PoE++ / 4PPoE** | ✅ | **60 W** | **51 W** | 4 |
| **802.3bt** (2018) Type 4 | **PoE++ / Hi-PoE** | ✅ | **90–100 W** | **71–71.3 W** | 4 |
| Cisco UPOE+ | — | Cisco | **90 W** | ~71.3 W | 4 |

> Power is lost as heat along the cable (up to 100 m), so the PD receives less than the PSE sends.

### 14.4 How PoE works (detection → classification → power)

1. **Detection:** the PSE applies a low voltage (≈2.7–10.1 V) and checks for a **25 kΩ signature resistance** at the PD. If not present, **no power is sent** → PoE is safe for non-PoE devices.
2. **Classification:** the PSE determines how much power the PD needs (**power classes**). Further refinement can be negotiated via **CDP** or **LLDP-MED** (Layer 2 power negotiation).
3. **Power-up:** the PSE supplies ~44–57 V DC (nominal **48 V**).
4. **Monitoring / disconnect:** the PSE keeps monitoring and removes power if the PD is disconnected or exceeds its allocation.

### 14.5 IEEE power classes

| Class | Standard | Max power at PSE | Max at PD |
|---|---|---|---|
| 0 | 802.3af (default/unclassified) | 15.4 W | 12.95 W |
| 1 | 802.3af | 4 W | 3.84 W |
| 2 | 802.3af | 7 W | 6.49 W |
| 3 | 802.3af | 15.4 W | 12.95 W |
| 4 | 802.3at | 30 W | 25.5 W |
| 5 | 802.3bt | 45 W | 40 W |
| 6 | 802.3bt | 60 W | 51 W |
| 7 | 802.3bt | 75 W | 62 W |
| 8 | 802.3bt | 90 W | 71.3 W |

### 14.6 Benefits of PoE

- No electrical outlet needed near the device (great for ceiling APs and outdoor cameras).
- **Centralized power** → a **UPS** in the wiring closet keeps phones/APs/cameras running during outages.
- Remote power-cycling of devices (`shutdown` / `no shutdown` or `power inline never/auto`).
- Lower installation cost and flexible placement.

### 14.7 Power budget example (exam-style)

A switch has a **370 W PoE budget**. How many 802.3at (PoE+, 30 W allocated) APs can it power at full allocation?
→ `370 / 30 = 12.33` → **12 APs**.

How many 802.3af phones at 15.4 W?
→ `370 / 15.4 = 24.03` → **24 phones**.

### 14.8 Cisco PoE commands

```
Switch(config)# interface gigabitEthernet1/0/10
Switch(config-if)# power inline auto            ! default: detect and power automatically
Switch(config-if)# power inline never           ! disable PoE on the port
Switch(config-if)# power inline static max 30000 ! pre-allocate power (milliwatts)
Switch(config-if)# power inline police          ! police consumption (Power Policing)

Switch# show power inline
Switch# show power inline gigabitEthernet1/0/10 detail
```

- **Power policing:** if a PD draws more than its allocation, the switch can **err-disable** the port (`power inline police` default action) or just **log** (`power inline police action log`).

---

## 15. Legacy Devices You Should Still Recognize

| Device | Layer | Description |
|---|---|---|
| **Hub** | L1 | Multiport repeater; repeats bits out of all ports; one collision domain; half-duplex. Obsolete. |
| **Repeater** | L1 | Regenerates the signal to extend distance. |
| **Bridge** | L2 | Forwards frames based on MAC; separates collision domains; few ports, software-based. Switches are "multiport hardware bridges". |
| **Modem** | L1/L2 | Modulator/demodulator (DSL, cable). |
| **Media converter** | L1 | Converts copper ↔ fiber. |

---

## 16. Master Comparison Tables

### 16.1 Device summary

| Device | OSI Layer | Forwards based on | Key table | Separates collision domain | Separates broadcast domain |
|---|---|---|---|---|---|
| Hub | 1 | — (repeats bits) | — | ❌ | ❌ |
| L2 switch | 2 | Destination MAC | MAC / CAM table | ✅ per port | ❌ (✅ per VLAN) |
| L3 switch | 2 + 3 | MAC and IP | MAC table + routing table / FIB | ✅ | ✅ |
| Router | 3 | Destination IP | Routing table / FIB | ✅ | ✅ |
| Firewall (stateful) | 3–4 | Rules + state | State/connection table | ✅ | ✅ |
| NGFW | 3–7 | Rules + apps + users + threats | State table + app/threat DBs | ✅ | ✅ |
| IPS (inline) | 2–7 (often transparent L2) | Signatures/anomalies | Signature DB | — | — |
| AP | 2 | MAC (bridges 802.11 ↔ 802.3) | Association table | — | ❌ |
| WLC | Management/control (+ data tunnel) | — | Client/AP database | — | — |

### 16.2 Which device would you choose?

| Requirement | Device |
|---|---|
| Connect PCs in the same office floor | L2 switch |
| Route between VLANs at wire speed in the campus | L3 switch |
| Connect the company LAN to the Internet / WAN | Router |
| Block traffic based on application (e.g., block Facebook Games) | NGFW |
| Block known exploits inline in real time | IPS / NGIPS |
| Passively monitor traffic and alert without blocking | IDS |
| Give wireless access to laptops and smartphones | Access point |
| Manage 300 APs from a single place | WLC |
| Automate, provision, and monitor the entire enterprise network with APIs | Catalyst Center (DNA Center) |
| Power an IP phone/AP/camera without a power outlet | PoE switch (or injector) |
| Provide IP addresses automatically | DHCP server (or router/switch DHCP service) |

---

## 17. Useful CLI Commands

```
! ---- Switch ----
show mac address-table
show mac address-table dynamic
show mac address-table interface gi1/0/1
clear mac address-table dynamic
show vlan brief
show interfaces status
show interfaces trunk
show cdp neighbors [detail]
show lldp neighbors [detail]
show power inline

! ---- L3 switch ----
show ip interface brief
show ip route
show interfaces vlan 10
show ip cef

! ---- Router ----
show ip route
show ip route 10.1.1.0
show ip interface brief
show ip protocols
show arp
show ip nat translations

! ---- WLC (AireOS) ----
show ap summary
show client summary
show wlan summary

! ---- WLC (Catalyst 9800, IOS-XE) ----
show ap summary
show wireless client summary
show wlan summary
```

---

## 18. Exam Tips and Common Traps

1. **Switches use MAC; routers use IP.** The L2 header (MAC) **changes at every router hop**; the L3 header (IP) does not (unless NAT).
2. **Switches flood** unknown unicast, broadcast and multicast **within the VLAN only**, never out the receiving port.
3. **Every switch port = one collision domain. Every VLAN = one broadcast domain. Every router interface = one broadcast domain.**
4. **MAC aging time = 300 seconds** by default.
5. An L2 switch's IP address is **for management only** — it needs `ip default-gateway`.
6. On a multilayer switch, **`ip routing`** must be enabled and SVIs/routed ports configured; `no switchport` turns a port into a routed port.
7. **Stateless ACL ≠ stateful firewall.** A firewall automatically permits return traffic for allowed sessions.
8. **NGFW = stateful FW + AVC + NGIPS + URL filtering + AMP.** Application identification does **not rely only on port numbers**.
9. **IDS = passive/out-of-band (copy of traffic, alerts only). IPS = inline (can drop).**
10. **False negative** is the most dangerous IDS/IPS outcome.
11. **Lightweight APs + WLC = split-MAC + CAPWAP (UDP 5246 control — encrypted; UDP 5247 data).**
12. **Autonomous AP** port = usually **trunk**; **lightweight AP (local mode)** port = usually **access**; **FlexConnect** AP port = often **trunk** (local switching).
13. **WLC manages APs (wireless). Catalyst Center manages the whole network (SDN controller), with REST northbound and SSH/SNMP/NETCONF southbound.** Catalyst Center does **not** forward user data.
14. **PoE values:** 802.3af = **15.4 W**, 802.3at (PoE+) = **30 W**, UPOE = **60 W**, 802.3bt = **60/90-100 W**, UPOE+ = **90 W**. Know PSE vs PD.
15. **PoE detection uses a 25 kΩ signature** — non-PoE devices are not damaged.
16. **Longest prefix match beats AD; AD beats metric.**
17. "Server" is a **role**, not hardware. Know the well-known ports.

---

## 19. Key Terms Glossary

| Term | Definition |
|---|---|
| **ASIC** | Application-Specific Integrated Circuit — hardware chip that forwards frames/packets at wire speed. |
| **CAM table** | Content Addressable Memory — stores the switch's MAC address table. |
| **CEF** | Cisco Express Forwarding — high-performance forwarding using FIB + adjacency table. |
| **FIB** | Forwarding Information Base — optimized copy of the routing table used for forwarding. |
| **SVI** | Switched Virtual Interface — L3 virtual interface for a VLAN. |
| **Routed port** | A physical switch port configured as an L3 interface (`no switchport`). |
| **Default gateway** | The router (or L3 switch SVI) IP that hosts send traffic to for remote networks. |
| **DMZ** | Network segment for public-facing servers, isolated from the inside LAN. |
| **AVC** | Application Visibility and Control — identification/control of applications. |
| **AMP** | Advanced Malware Protection (now Secure Malware Defense / Secure Endpoint). |
| **Talos** | Cisco's threat intelligence group. |
| **Snort** | Open-source IPS engine used by Cisco Secure Firewall/NGIPS. |
| **SSID / BSSID** | Wireless network name / AP radio MAC identifier. |
| **CAPWAP** | Protocol between lightweight APs and WLC (UDP 5246/5247). |
| **Split-MAC** | Division of 802.11 functions between LAP (real-time) and WLC (management). |
| **RRM** | Radio Resource Management — WLC auto channel/power tuning. |
| **FlexConnect** | AP mode allowing local switching and survivability at branches. |
| **SDN** | Software-Defined Networking — centralized, programmable network control. |
| **NBI / SBI** | Northbound / Southbound interfaces of an SDN controller. |
| **IBN** | Intent-Based Networking — define *what* you want; the controller handles *how*. |
| **SD-Access** | Cisco's campus fabric solution automated by Catalyst Center + ISE. |
| **PSE / PD** | PoE Power Sourcing Equipment / Powered Device. |
| **Power budget** | Total PoE power available on a switch. |
| **LLDP-MED** | LLDP extension for media endpoints (VoIP VLAN, PoE negotiation). |

---

## 20. Practice Questions (with Answers)

> Try to answer before opening each solution.

**Q1.** Which device forwards traffic based on destination IP addresses and separates broadcast domains?
- A. Hub
- B. Layer 2 switch
- C. Router
- D. Access point

<details><summary>Answer</summary>

**C. Router.** It operates at Layer 3; every interface is a separate broadcast domain.
</details>

---

**Q2.** A switch receives a frame whose destination MAC is not in its MAC address table. What does it do?
- A. Drops the frame
- B. Floods it out all ports in the same VLAN except the incoming port
- C. Sends it to the default gateway
- D. Sends an ARP request

<details><summary>Answer</summary>

**B.** Unknown unicast frames are flooded within the VLAN (except the ingress port).
</details>

---

**Q3.** Which two capabilities distinguish an NGFW from a traditional stateful firewall? (Choose two.)
- A. NAT
- B. Application Visibility and Control
- C. Stateful packet inspection
- D. Integrated intrusion prevention
- E. Static routing

<details><summary>Answer</summary>

**B and D.** NAT, stateful inspection and routing exist on traditional firewalls too.
</details>

---

**Q4.** What is the key difference between an IDS and an IPS?
- A. IDS uses signatures; IPS uses anomaly detection
- B. IDS is deployed inline; IPS analyzes a copy of traffic
- C. IPS is deployed inline and can block traffic; IDS analyzes a copy and only alerts
- D. There is no difference

<details><summary>Answer</summary>

**C.** IPS is inline (can drop); IDS is promiscuous/out-of-band (alerts).
</details>

---

**Q5.** Which protocol and ports do lightweight APs use to communicate with a WLC?
- A. LWAPP, UDP 12222/12223
- B. CAPWAP, UDP 5246/5247
- C. CAPWAP, TCP 5246/5247
- D. RADIUS, UDP 1812/1813

<details><summary>Answer</summary>

**B.** CAPWAP: UDP 5246 (control, DTLS-encrypted) and UDP 5247 (data). (LWAPP used 12222/12223 — legacy.)
</details>

---

**Q6.** In a split-MAC architecture, which function is performed by the lightweight AP rather than the WLC?
- A. Client authentication
- B. RF management
- C. Beacon and probe response transmission
- D. Association and roaming management

<details><summary>Answer</summary>

**C.** Real-time functions (beacons, probe responses, ACKs, encryption) stay on the AP.
</details>

---

**Q7.** Which interface does an application use to request information from Cisco Catalyst Center (DNA Center)?
- A. Southbound API using NETCONF
- B. Northbound REST API
- C. CAPWAP
- D. SNMP traps

<details><summary>Answer</summary>

**B.** Applications talk to the controller via the northbound REST API.
</details>

---

**Q8.** What is the maximum power a PSE provides per port with IEEE 802.3at (PoE+)?
- A. 7 W
- B. 15.4 W
- C. 30 W
- D. 60 W

<details><summary>Answer</summary>

**C. 30 W** (25.5 W guaranteed at the PD).
</details>

---

**Q9.** A switch has a PoE budget of 740 W. Each AP requires 30 W. What is the maximum number of APs supported at full allocation?
- A. 12
- B. 24
- C. 48
- D. 25

<details><summary>Answer</summary>

**B. 24** (740 / 30 = 24.67 → 24).
</details>

---

**Q10.** How does a PSE determine whether a connected device supports PoE?
- A. It sends a CDP message
- B. It detects a 25 kΩ signature resistance
- C. It always sends 48 V and checks for current
- D. It reads the device MAC OUI

<details><summary>Answer</summary>

**B.** Detection relies on the 25 kΩ signature; CDP/LLDP can refine power allocation afterwards.
</details>

---

**Q11.** Which statement about Layer 3 switches is true?
- A. They cannot perform Layer 2 switching
- B. They route between VLANs using SVIs and hardware-based forwarding
- C. They are typically used for WAN connections with serial interfaces
- D. They do not support routing protocols

<details><summary>Answer</summary>

**B.**
</details>

---

**Q12.** A packet travels from PC-A through two routers to Server-B (no NAT). Which header fields change at every hop?
- A. Source and destination IP addresses
- B. Source and destination MAC addresses
- C. Source and destination port numbers
- D. Nothing changes

<details><summary>Answer</summary>

**B.** MAC addresses are rewritten per hop (and the TTL is decremented); IPs remain the same.
</details>

---

**Q13.** Which AP architecture is managed by a cloud dashboard while client data traffic stays local?
- A. Autonomous
- B. Lightweight in local mode
- C. Cloud-based (e.g., Meraki)
- D. Sniffer mode

<details><summary>Answer</summary>

**C.**
</details>

---

**Q14.** Which network component typically connects to a switch access port configured for a single VLAN and tunnels all client traffic to a controller?
- A. Autonomous AP
- B. Lightweight AP in local mode
- C. FlexConnect AP performing local switching
- D. Router

<details><summary>Answer</summary>

**B.**
</details>

---

**Q15.** A topology has one router with two interfaces. Each interface connects to a 24-port switch with no VLANs configured. How many broadcast domains exist?
- A. 1
- B. 2
- C. 24
- D. 48

<details><summary>Answer</summary>

**B. 2** — one per router interface.
</details>

---

**Q16.** Which IDS/IPS alert outcome is the most dangerous?
- A. True positive
- B. True negative
- C. False positive
- D. False negative

<details><summary>Answer</summary>

**D.** An actual attack goes undetected.
</details>

---

**Q17.** What is the function of a server in a client-server model?
- A. To forward frames between hosts
- B. To provide resources or services requested by clients
- C. To route packets between networks
- D. To provide power to endpoints

<details><summary>Answer</summary>

**B.**
</details>

---

**Q18.** Which Cisco WLC deployment runs the controller function on an access point?
- A. Unified
- B. Cloud-based (9800-CL)
- C. Embedded (on a switch)
- D. Mobility Express / Embedded Wireless Controller on AP

<details><summary>Answer</summary>

**D.**
</details>

---

## Study Checklist

- [ ] I can explain what each device does and at which OSI layer it operates.
- [ ] I can describe switch learning, forwarding, filtering and flooding.
- [ ] I can count collision and broadcast domains in a topology.
- [ ] I can compare L2 switch, L3 switch and router.
- [ ] I can explain stateless vs. stateful vs. NGFW.
- [ ] I can explain IDS vs. IPS and detection methods.
- [ ] I know AP architectures (autonomous, lightweight, cloud) and AP modes.
- [ ] I can explain split-MAC and CAPWAP (ports, encryption).
- [ ] I know WLC deployment models.
- [ ] I can explain Catalyst Center (DNA Center), NBI/SBI and its main functions.
- [ ] I can list endpoint examples and server roles with their ports.
- [ ] I memorized PoE standards, PSE/PD, detection and power budget math.
