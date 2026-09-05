---
title: "BGP: the protocol that keeps the internet running"
date: 2026-06-20 00:00:00 -0300
categories: [Networking, Routing]
tags: [bgp, routing, autonomous-system, internet]
---

BGP (Border Gateway Protocol) is the routing protocol that interconnects autonomous systems (ASes) on the internet. It is a path-vector protocol, unlike OSPF (link-state) and RIP (distance-vector).

## Core concepts

- **AS (Autonomous System):** a set of networks under single administrative control, identified by an ASN
- **eBGP:** BGP session between different ASes
- **iBGP:** BGP session within the same AS
- **Prefix:** an IP address block being announced (e.g. 200.100.0.0/24)

## Path attributes

BGP uses attributes to select the best route:

| Attribute | Type | Description |
|---|---|---|
| WEIGHT | Cisco local | Higher value preferred (local to the router) |
| LOCAL_PREF | Well-known | Preference within the AS |
| AS_PATH | Well-known | List of ASes — shorter = better |
| MED | Optional | Hint to neighboring AS about preferred entry point |
| NEXT_HOP | Well-known | Next-hop address |

## Basic configuration (Cisco)

```bash
Router(config)# router bgp 65001
Router(config-router)# neighbor 203.0.113.1 remote-as 65002
Router(config-router)# network 200.100.0.0 mask 255.255.255.0
```

## Route filtering with prefix-list

```bash
ip prefix-list ALLOW seq 10 permit 200.100.0.0/24
ip prefix-list ALLOW seq 20 deny 0.0.0.0/0 le 32

router bgp 65001
 neighbor 203.0.113.1 prefix-list ALLOW out
```

BGP requires careful handling — a wrong announcement can affect global routing. Always use outbound filters and validate prefixes with RPKI whenever possible.
