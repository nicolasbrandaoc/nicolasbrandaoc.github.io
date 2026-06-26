---
title: "Monitoramento de infraestrutura com Zabbix"
date: 2026-06-17 00:00:00 -0300
categories: [Monitoramento, Infraestrutura]
tags: [zabbix, monitoramento, snmp, alertas]
---

Zabbix é uma plataforma de monitoramento open-source madura e escalável. Monitora servidores, switches, roteadores, aplicações e serviços com coleta via agente, SNMP, ICMP, HTTP e muito mais.

## Arquitetura

```
[Dispositivos] → [Zabbix Agent / SNMP] → [Zabbix Server] → [Banco de dados] → [Frontend Web]
```

Para ambientes distribuídos, o Zabbix Proxy coleta dados localmente e envia ao servidor central, reduzindo latência e consumo de banda.

## Monitoramento via SNMP

Ideal para equipamentos de rede (switches, roteadores, APs):

```
1. Ativar SNMP no dispositivo
2. No Zabbix: adicionar host com interface SNMP
3. Aplicar template (ex: "Cisco IOS SNMP")
4. Configurar community string
```

## Criando um item personalizado

```
Name: Uso de CPU
Type: Zabbix agent
Key: system.cpu.util[,idle]
Type of information: Numeric (float)
Update interval: 60s
```

## Trigger de alerta

```
Expression: avg(/servidor01/system.cpu.util[,idle],5m) < 20
Severity: High
Message: "CPU acima de 80% nos últimos 5 minutos"
```

## Ações e notificações

O Zabbix suporta notificações por e-mail, Telegram, Slack, PagerDuty e scripts customizados. Configuro sempre um script de Telegram para alertas críticos — chegam no celular em segundos.

Zabbix é minha ferramenta padrão de monitoramento há anos. Com templates da comunidade, fica funcional em poucos minutos para a maioria dos dispositivos.
