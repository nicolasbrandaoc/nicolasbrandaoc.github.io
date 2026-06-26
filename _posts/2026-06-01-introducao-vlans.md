---
title: "Introdução a VLANs: segmentando redes com eficiência"
date: 2026-06-01 00:00:00 -0300
categories: [Redes, Switching]
tags: [vlan, switching, infraestrutura]
---

VLANs (Virtual Local Area Networks) permitem segmentar uma rede física em múltiplas redes lógicas independentes, melhorando segurança, desempenho e organização.

## O que é uma VLAN?

Uma VLAN agrupa dispositivos em domínios de broadcast separados, independentemente de onde estejam fisicamente conectados na rede. Switches gerenciam o tráfego entre VLANs usando tags IEEE 802.1Q.

## Por que usar VLANs?

- **Segurança:** isola setores (ex: financeiro, TI, visitantes)
- **Desempenho:** reduz domínios de broadcast
- **Flexibilidade:** reorganização lógica sem mexer no cabeamento

## Configuração básica em um switch Cisco

```bash
Switch(config)# vlan 10
Switch(config-vlan)# name FINANCEIRO

Switch(config)# interface fastethernet 0/1
Switch(config-if)# switchport mode access
Switch(config-if)# switchport access vlan 10
```

## Trunk entre switches

Para transportar múltiplas VLANs entre switches, usamos portas trunk:

```bash
Switch(config)# interface gigabitethernet 0/1
Switch(config-if)# switchport mode trunk
Switch(config-if)# switchport trunk allowed vlan 10,20,30
```

Entender VLANs é fundamental para qualquer profissional de redes. No próximo post, veremos como configurar roteamento inter-VLAN com Router-on-a-Stick.
