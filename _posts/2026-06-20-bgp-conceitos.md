---
title: "BGP: o protocolo que mantém a internet de pé"
date: 2026-06-20 00:00:00 -0300
categories: [Redes, Routing]
tags: [bgp, routing, autonomous-system, internet]
---

BGP (Border Gateway Protocol) é o protocolo de roteamento que interconecta sistemas autônomos (ASes) na internet. É um protocolo path-vector, diferente do OSPF (link-state) e do RIP (distance-vector).

## Conceitos fundamentais

- **AS (Autonomous System):** conjunto de redes sob controle administrativo único, identificado por um ASN
- **eBGP:** sessão BGP entre ASes diferentes
- **iBGP:** sessão BGP dentro do mesmo AS
- **Prefixo:** bloco de endereços IP anunciado (ex: 200.100.0.0/24)

## Atributos de path

O BGP usa atributos para selecionar a melhor rota:

| Atributo | Tipo | Descrição |
|---|---|---|
| WEIGHT | Cisco local | Maior valor preferido (local ao roteador) |
| LOCAL_PREF | Well-known | Preferência dentro do AS |
| AS_PATH | Well-known | Lista de ASes — menor = melhor |
| MED | Optional | Dica ao AS vizinho sobre entrada preferida |
| NEXT_HOP | Well-known | Endereço do próximo salto |

## Configuração básica (Cisco)

```bash
Router(config)# router bgp 65001
Router(config-router)# neighbor 203.0.113.1 remote-as 65002
Router(config-router)# network 200.100.0.0 mask 255.255.255.0
```

## Route filtering com prefix-list

```bash
ip prefix-list PERMITIR seq 10 permit 200.100.0.0/24
ip prefix-list PERMITIR seq 20 deny 0.0.0.0/0 le 32

router bgp 65001
 neighbor 203.0.113.1 prefix-list PERMITIR out
```

BGP exige cuidado — um anúncio errado pode afetar o roteamento global. Sempre use filtros de saída e valide prefixos com RPKI quando possível.
