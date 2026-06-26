---
title: "Hardening de servidores Linux: guia prático"
date: 2026-06-24 00:00:00 -0300
categories: [Segurança, Linux]
tags: [hardening, linux, segurança, ssh]
---

Hardening é o processo de reduzir a superfície de ataque de um sistema. Um servidor Linux recém-instalado tem diversas configurações padrão inseguras. Este guia cobre as medidas essenciais.

## 1. Atualize o sistema imediatamente

```bash
apt update && apt upgrade -y
apt install unattended-upgrades
dpkg-reconfigure --priority=low unattended-upgrades
```

## 2. SSH seguro

```ini
# /etc/ssh/sshd_config

Port 2222                    # troque a porta padrão
PermitRootLogin no           # nunca faça login como root
PasswordAuthentication no    # apenas chaves criptográficas
PubkeyAuthentication yes
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
AllowUsers seunome           # whitelist de usuários
```

```bash
systemctl restart sshd
```

## 3. Firewall com UFW

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow 2222/tcp    # SSH na nova porta
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

## 5. Remova serviços desnecessários

```bash
systemctl list-units --type=service --state=running
systemctl disable --now <serviço-desnecessário>
```

## 6. Auditoria com Lynis

```bash
apt install lynis
lynis audit system
```

O Lynis gera um relatório com score e recomendações específicas para o sistema. É uma excelente baseline para auditar qualquer servidor Linux.

Hardening não é um evento único — revise as configurações periodicamente e monitore logs com ferramentas como Fail2ban, Logwatch ou OSSEC.
