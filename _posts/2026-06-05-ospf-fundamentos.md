---
title: "OSPF: fundamentals of the link-state routing protocol"
date: 2026-06-05 00:00:00 -0300
categories: [Networking, Routing]
tags: [ospf, routing, protocol]
---

OSPF (Open Shortest Path First) is a link-state dynamic routing protocol widely used in corporate networks. Unlike distance-vector protocols like RIP, OSPF maintains a complete map of the network topology.

## How OSPF works

1. Routers exchange **Hello packets** to discover neighbors
2. They establish adjacencies and elect DR/BDR on multi-access networks
3. They flood **LSAs** (Link State Advertisements) across the area
4. Each router builds an **LSDB** (Link State Database)
5. They run the **Dijkstra (SPF)** algorithm to calculate the best route

## OSPF areas

OSPF uses areas to limit LSA propagation:

- **Area 0 (backbone):** mandatory — all other areas connect to it
- **Stub areas:** do not receive external LSAs
- **NSSA:** a stub variant that accepts redistributed external routes

## Basic configuration

```bash
Router(config)# router ospf 1
Router(config-router)# network 192.168.1.0 0.0.0.255 area 0
Router(config-router)# network 10.0.0.0 0.0.0.3 area 0
```

## Metrics and cost

OSPF uses **cost** as its metric, calculated based on interface bandwidth:

```
Cost = Reference bandwidth / Interface bandwidth
Cost = 100 Mbps / 10 Mbps = 10
```

OSPF is essential for medium and large environments that require fast convergence and fine-grained route control.
