---
title: "Building a homelab with Proxmox VE"
date: 2026-06-11 00:00:00 -0300
categories: [Virtualization, Homelab]
tags: [proxmox, virtualization, homelab, kvm]
---

Proxmox VE is an open-source virtualization platform based on KVM and LXC. With a complete web interface and clustering support, it's ideal for homelabs and small production environments.

## KVM vs LXC: which one to use?

**KVM (VMs):** full isolation, any OS, heavier on resources.  
**LXC (containers):** shares the host kernel, much lighter, ideal for Linux services.

General rule: use LXC for simple services (DNS, proxy, monitoring) and KVM for full systems (Windows, pfSense, appliances).

## Network configuration in Proxmox

Proxmox uses Linux bridges. Typical setup for an environment with VLANs:

```
/etc/network/interfaces

auto vmbr0
iface vmbr0 inet static
    address 192.168.1.10/24
    gateway 192.168.1.1
    bridge-ports eno1
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes
    bridge-vids 2-4094
```

## Storage

Native Proxmox storage options:

| Type | Best use |
|---|---|
| LVM-Thin | Local VMs and containers |
| ZFS | High performance + snapshots |
| NFS/CIFS | Shared storage |
| Ceph | Distributed cluster |

## Snapshots and backups

```bash
# Snapshot via CLI
qm snapshot <vmid> <name> --description "before update"

# Scheduled backup via vzdump
vzdump <vmid> --storage local --mode snapshot --compress zstd
```

Proxmox has become the heart of my homelab — I run pfSense, Pi-hole, Zabbix and various lab VMs on a single server.
