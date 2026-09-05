---
title: "WireGuard: modern, fast and simple VPN"
date: 2026-06-14 00:00:00 -0300
categories: [Security, VPN]
tags: [wireguard, vpn, security, tunneling]
---

WireGuard is a modern VPN protocol that stands out for its simplicity, performance and lean codebase (~4,000 lines vs ~400k for OpenVPN). It has been integrated into the Linux kernel since version 5.6.

## Why WireGuard?

- **Performance:** uses ChaCha20 for encryption, much faster than AES on hardware without acceleration
- **Latency:** 1-RTT handshake
- **Simplicity:** configuration in a few plain text files
- **Security:** minimal attack surface, no algorithm negotiation

## Installation on Ubuntu/Debian

```bash
apt install wireguard
wg genkey | tee privatekey | wg pubkey > publickey
```

## Server configuration

```ini
# /etc/wireguard/wg0.conf

[Interface]
Address = 10.10.0.1/24
ListenPort = 51820
PrivateKey = <server-private-key>

PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

[Peer]
PublicKey = <client-public-key>
AllowedIPs = 10.10.0.2/32
```

## Client configuration

```ini
[Interface]
Address = 10.10.0.2/24
PrivateKey = <client-private-key>
DNS = 1.1.1.1

[Peer]
PublicKey = <server-public-key>
Endpoint = my-server.com:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

## Enable and manage

```bash
systemctl enable --now wg-quick@wg0
wg show   # interface status
```

WireGuard completely replaced OpenVPN in my environment — lower latency and a much cleaner configuration.
