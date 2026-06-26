---
title: "pfSense: montando um firewall profissional com hardware acessível"
date: 2026-06-08 00:00:00 -0300
categories: [Segurança, Firewall]
tags: [pfsense, firewall, segurança]
---

pfSense é uma distribuição FreeBSD voltada para firewall e roteamento. Gratuito, open-source e com interface web intuitiva, substitui soluções comerciais caras em ambientes de pequeno e médio porte.

## Por que pfSense?

- Firewall stateful com regras granulares
- Suporte nativo a VPN (IPsec, OpenVPN, WireGuard)
- IDS/IPS com Suricata ou Snort
- Traffic shaping e QoS
- Alta disponibilidade com CARP

## Requisitos mínimos de hardware

| Componente | Mínimo | Recomendado |
|---|---|---|
| CPU | 500 MHz | 1 GHz+ |
| RAM | 512 MB | 2 GB+ |
| Interfaces | 2 NICs | 3+ NICs |
| Armazenamento | 4 GB | 16 GB SSD |

## Estrutura de regras

As regras no pfSense são avaliadas de cima para baixo, por interface. A lógica padrão é:

1. Tráfego LAN → WAN: **permitido por padrão**
2. Tráfego WAN → LAN: **bloqueado por padrão**

Exemplo de regra para bloquear acesso de uma VLAN à outra:

```
Action: Block
Interface: VLAN10
Source: VLAN10 net
Destination: VLAN20 net
```

## Dica de segurança

Desative o acesso à interface web pela WAN. Acesse sempre via LAN ou por VPN. Use certificado TLS válido mesmo em redes internas para evitar ataques MITM.

pfSense é uma das ferramentas mais completas da minha stack — uso em homelab e em clientes pequenos com excelentes resultados.
