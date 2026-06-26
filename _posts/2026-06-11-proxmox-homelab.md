---
title: "Montando um homelab com Proxmox VE"
date: 2026-06-11 00:00:00 -0300
categories: [Virtualização, Homelab]
tags: [proxmox, virtualização, homelab, kvm]
---

Proxmox VE é uma plataforma open-source de virtualização baseada em KVM e LXC. Com interface web completa e suporte a clustering, é ideal para homelabs e ambientes de produção de pequeno porte.

## KVM vs LXC: qual usar?

**KVM (VMs):** isolamento completo, qualquer SO, mais pesado em recursos.  
**LXC (containers):** compartilha o kernel do host, muito mais leve, ideal para serviços Linux.

Regra geral: use LXC para serviços simples (DNS, proxy, monitoramento) e KVM para sistemas completos (Windows, pfSense, appliances).

## Configuração de rede no Proxmox

O Proxmox usa bridges Linux. Estrutura típica para um ambiente com VLANs:

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

## Armazenamento

Opções nativas do Proxmox:

| Tipo | Uso ideal |
|---|---|
| LVM-Thin | VMs e containers locais |
| ZFS | Alta performance + snapshots |
| NFS/CIFS | Armazenamento compartilhado |
| Ceph | Cluster distribuído |

## Snapshots e backups

```bash
# Snapshot via CLI
qm snapshot <vmid> <nome> --description "antes da atualização"

# Backup agendado via vzdump
vzdump <vmid> --storage local --mode snapshot --compress zstd
```

Proxmox virou o coração do meu homelab — rodo pfSense, Pi-hole, Zabbix, e diversas VMs de laboratório em um único servidor.
