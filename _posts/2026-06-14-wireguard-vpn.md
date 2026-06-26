---
title: "WireGuard: VPN moderna, rápida e simples de configurar"
date: 2026-06-14 00:00:00 -0300
categories: [Segurança, VPN]
tags: [wireguard, vpn, segurança, tunneling]
---

WireGuard é um protocolo VPN moderno que se destaca pela simplicidade, performance e código enxuto (~4000 linhas vs ~400k do OpenVPN). Está integrado ao kernel Linux desde a versão 5.6.

## Por que WireGuard?

- **Performance:** usa ChaCha20 para criptografia, muito mais rápido que AES em hardware sem aceleração
- **Latência:** handshake em 1-RTT
- **Simplicidade:** configuração em poucos arquivos texto
- **Segurança:** surface de ataque mínima, sem negociação de algoritmos

## Instalação no Ubuntu/Debian

```bash
apt install wireguard
wg genkey | tee privatekey | wg pubkey > publickey
```

## Configuração do servidor

```ini
# /etc/wireguard/wg0.conf

[Interface]
Address = 10.10.0.1/24
ListenPort = 51820
PrivateKey = <chave-privada-do-servidor>

PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

[Peer]
PublicKey = <chave-pública-do-cliente>
AllowedIPs = 10.10.0.2/32
```

## Configuração do cliente

```ini
[Interface]
Address = 10.10.0.2/24
PrivateKey = <chave-privada-do-cliente>
DNS = 1.1.1.1

[Peer]
PublicKey = <chave-pública-do-servidor>
Endpoint = meu-servidor.com:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

## Ativar e gerenciar

```bash
systemctl enable --now wg-quick@wg0
wg show   # status da interface
```

WireGuard substituiu completamente o OpenVPN no meu ambiente — latência menor e configuração muito mais limpa.
