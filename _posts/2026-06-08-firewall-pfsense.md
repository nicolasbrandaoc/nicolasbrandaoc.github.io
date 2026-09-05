---
title: "pfSense: building a professional firewall with affordable hardware"
date: 2026-06-08 00:00:00 -0300
categories: [Security, Firewall]
tags: [pfsense, firewall, security]
---

pfSense is a FreeBSD-based distribution designed for firewalling and routing. Free, open-source and with an intuitive web interface, it replaces expensive commercial solutions in small and medium-sized environments.

## Why pfSense?

- Stateful firewall with granular rules
- Native VPN support (IPsec, OpenVPN, WireGuard)
- IDS/IPS with Suricata or Snort
- Traffic shaping and QoS
- High availability with CARP

## Minimum hardware requirements

| Component | Minimum | Recommended |
|---|---|---|
| CPU | 500 MHz | 1 GHz+ |
| RAM | 512 MB | 2 GB+ |
| Interfaces | 2 NICs | 3+ NICs |
| Storage | 4 GB | 16 GB SSD |

## Rule structure

Rules in pfSense are evaluated top-down, per interface. The default logic is:

1. LAN → WAN traffic: **allowed by default**
2. WAN → LAN traffic: **blocked by default**

Example rule to block access from one VLAN to another:

```
Action: Block
Interface: VLAN10
Source: VLAN10 net
Destination: VLAN20 net
```

## Security tip

Disable web interface access from the WAN. Always access via LAN or VPN. Use a valid TLS certificate even on internal networks to prevent MITM attacks.

pfSense is one of the most complete tools in my stack — I use it in my homelab and for small clients with excellent results.
