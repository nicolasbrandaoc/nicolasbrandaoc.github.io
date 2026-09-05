---
title: "Introduction to VLANs: segmenting networks efficiently"
date: 2026-06-01 00:00:00 -0300
categories: [Networking, Switching]
tags: [vlan, switching, infrastructure]
---

VLANs (Virtual Local Area Networks) allow you to segment a physical network into multiple independent logical networks, improving security, performance and organization.

## What is a VLAN?

A VLAN groups devices into separate broadcast domains, regardless of where they are physically connected on the network. Switches manage traffic between VLANs using IEEE 802.1Q tags.

## Why use VLANs?

- **Security:** isolates departments (e.g. finance, IT, guests)
- **Performance:** reduces broadcast domains
- **Flexibility:** logical reorganization without touching the cabling

## Basic configuration on a Cisco switch

```bash
Switch(config)# vlan 10
Switch(config-vlan)# name FINANCE

Switch(config)# interface fastethernet 0/1
Switch(config-if)# switchport mode access
Switch(config-if)# switchport access vlan 10
```

## Trunk between switches

To carry multiple VLANs between switches, use trunk ports:

```bash
Switch(config)# interface gigabitethernet 0/1
Switch(config-if)# switchport mode trunk
Switch(config-if)# switchport trunk allowed vlan 10,20,30
```

Understanding VLANs is fundamental for any network professional. In the next post, we'll look at how to configure inter-VLAN routing with Router-on-a-Stick.
