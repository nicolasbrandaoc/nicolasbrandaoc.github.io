---
title: "OSPF: fundamentos do protocolo de roteamento de estado de enlace"
date: 2026-06-05 00:00:00 -0300
categories: [Redes, Routing]
tags: [ospf, routing, protocolo]
---

OSPF (Open Shortest Path First) é um protocolo de roteamento dinâmico link-state amplamente usado em redes corporativas. Diferente de protocolos distance-vector como RIP, o OSPF mantém um mapa completo da topologia da rede.

## Como o OSPF funciona

1. Roteadores trocam **Hello packets** para descobrir vizinhos
2. Estabelecem adjacências e elegem DR/BDR em redes multi-acesso
3. Inundam **LSAs** (Link State Advertisements) pela área
4. Cada roteador constrói um **LSDB** (Link State Database)
5. Rodam o algoritmo **Dijkstra (SPF)** para calcular a melhor rota

## Áreas OSPF

O OSPF usa áreas para limitar a propagação de LSAs:

- **Área 0 (backbone):** obrigatória, todas as outras áreas se conectam a ela
- **Stub areas:** não recebem LSAs externos
- **NSSA:** variação da stub que aceita rotas externas redistributídas

## Configuração básica

```bash
Router(config)# router ospf 1
Router(config-router)# network 192.168.1.0 0.0.0.255 area 0
Router(config-router)# network 10.0.0.0 0.0.0.3 area 0
```

## Métricas e custo

O OSPF usa **custo** como métrica, calculado com base na largura de banda da interface:

```
Custo = Referência de banda / Banda da interface
Custo = 100 Mbps / 10 Mbps = 10
```

OSPF é essencial para ambientes de médio e grande porte que exigem convergência rápida e controle fino de rotas.
