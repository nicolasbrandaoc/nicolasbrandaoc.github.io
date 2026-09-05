---
title: "Infrastructure monitoring with Zabbix"
date: 2026-06-17 00:00:00 -0300
categories: [Monitoring, Infrastructure]
tags: [zabbix, monitoring, snmp, alerts]
---

Zabbix is a mature and scalable open-source monitoring platform. It monitors servers, switches, routers, applications and services using agent, SNMP, ICMP, HTTP and much more.

## Architecture

```
[Devices] → [Zabbix Agent / SNMP] → [Zabbix Server] → [Database] → [Web Frontend]
```

For distributed environments, the Zabbix Proxy collects data locally and sends it to the central server, reducing latency and bandwidth consumption.

## SNMP monitoring

Ideal for network equipment (switches, routers, APs):

```
1. Enable SNMP on the device
2. In Zabbix: add host with SNMP interface
3. Apply template (e.g. "Cisco IOS SNMP")
4. Configure community string
```

## Creating a custom item

```
Name: CPU Usage
Type: Zabbix agent
Key: system.cpu.util[,idle]
Type of information: Numeric (float)
Update interval: 60s
```

## Alert trigger

```
Expression: avg(/server01/system.cpu.util[,idle],5m) < 20
Severity: High
Message: "CPU above 80% for the last 5 minutes"
```

## Actions and notifications

Zabbix supports notifications via email, Telegram, Slack, PagerDuty and custom scripts. I always configure a Telegram script for critical alerts — they arrive on my phone within seconds.

Zabbix has been my standard monitoring tool for years. With community templates, it's up and running in minutes for most devices.
