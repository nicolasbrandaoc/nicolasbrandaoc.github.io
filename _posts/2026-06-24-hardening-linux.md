---
title: "Linux server hardening: a practical guide"
date: 2026-06-24 00:00:00 -0300
categories: [Security, Linux]
tags: [hardening, linux, security, ssh]
---

Hardening is the process of reducing the attack surface of a system. A freshly installed Linux server has several insecure default configurations. This guide covers the essential measures.

## 1. Update the system immediately

```bash
apt update && apt upgrade -y
apt install unattended-upgrades
dpkg-reconfigure --priority=low unattended-upgrades
```

## 2. Secure SSH

```ini
# /etc/ssh/sshd_config

Port 2222                    # change the default port
PermitRootLogin no           # never log in as root
PasswordAuthentication no    # use cryptographic keys only
PubkeyAuthentication yes
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
AllowUsers youruser          # user whitelist
```

```bash
systemctl restart sshd
```

## 3. Firewall with UFW

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow 2222/tcp    # SSH on the new port
ufw enable
```

## 4. Fail2ban

```bash
apt install fail2ban

# /etc/fail2ban/jail.local
[sshd]
enabled = true
port = 2222
maxretry = 3
bantime = 3600
```

## 5. Remove unnecessary services

```bash
systemctl list-units --type=service --state=running
systemctl disable --now <unnecessary-service>
```

## 6. Audit with Lynis

```bash
apt install lynis
lynis audit system
```

Lynis generates a report with a score and specific recommendations for the system. It's an excellent baseline for auditing any Linux server.

Hardening is not a one-time event — review configurations periodically and monitor logs with tools like Fail2ban, Logwatch or OSSEC.
