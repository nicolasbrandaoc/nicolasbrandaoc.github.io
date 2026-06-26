---
title: "Proteção de servidores Linux com UFW e Fail2Ban"
date: 2026-06-26 00:00:00 -0300
categories: [Segurança, Linux]
tags: [ufw, fail2ban, firewall, hardening, linux]
---

UFW (Uncomplicated Firewall) combinado com Fail2Ban é uma das configurações mais eficientes para proteger servidores Linux. O UFW gerencia as regras de firewall e o Fail2Ban monitora logs e bane automaticamente IPs com comportamento suspeito.

## Instalação

```bash
apt update && apt install fail2ban ufw -y
```

## Configurando o UFW

Defina a política padrão — bloquear tudo que entra, permitir tudo que sai:

```bash
ufw default deny incoming
ufw default allow outgoing
```

Libere apenas as portas necessárias:

```bash
ufw allow 22/tcp      # SSH
ufw allow 80/tcp      # HTTP
ufw allow 443/tcp     # HTTPS
```

Ative o firewall:

```bash
ufw --force enable
ufw status numbered
```

## Configurando o Fail2Ban

Crie o arquivo `/etc/fail2ban/jail.local` — nunca edite o `jail.conf` diretamente, pois ele é sobrescrito em atualizações:

```bash
cat <<EOF > /etc/fail2ban/jail.local
[DEFAULT]
bantime  = -1
findtime = 10m
maxretry = 5
backend  = systemd
banaction = ufw
banaction_allports = ufw
ignoreip = 127.0.0.1/8

[sshd]
enabled  = true
port     = ssh
logpath  = /var/log/auth.log
maxretry = 4
bantime  = -1

[recidive]
enabled  = true
logpath  = /var/log/fail2ban.log
interval = 1d
maxretry = 3
bantime  = 1w
findtime = 1d

[pam-generic]
enabled  = true
filter   = pam-generic
logpath  = /var/log/auth.log
maxretry = 3
bantime  = 1h

[nginx-http-auth]
enabled = true

[nginx-badbots]
enabled = true

[nginx-noscript]
enabled = true

[nginx-dos]
enabled  = true
port     = http,https
logpath  = /var/log/nginx/access.log
maxretry = 300
findtime = 1m
bantime  = 1h

[apache-auth]
enabled  = true
port     = http,https
logpath  = /var/log/apache2/error.log
maxretry = 5

[apache-badbots]
enabled  = true
port     = http,https
logpath  = /var/log/apache2/access.log
bantime  = 48h
maxretry = 1

[apache-noscript]
enabled  = true
port     = http,https
logpath  = /var/log/apache2/error.log
maxretry = 3

[apache-overflow]
enabled  = true
port     = http,https
logpath  = /var/log/apache2/error.log
maxretry = 2

[vsftpd]
enabled  = true
port     = ftp,ftp-data,ftps,ftps-data
logpath  = /var/log/vsftpd.log
maxretry = 5
bantime  = -1
EOF
```

### Parâmetros importantes

| Parâmetro | Valor | Descrição |
|---|---|---|
| `bantime = -1` | Permanente | IP banido indefinidamente |
| `findtime = 10m` | 10 minutos | Janela de tempo para contar tentativas |
| `maxretry = 5` | 5 tentativas | Falhas antes do banimento |
| `backend = systemd` | systemd | Fonte de logs |
| `banaction = ufw` | UFW | Integração direta com o firewall |

## Filtros personalizados

Crie filtros para detectar padrões específicos de ataque:

```bash
# Proteção contra DoS no Nginx
cat <<EOF > /etc/fail2ban/filter.d/nginx-dos.conf
[Definition]
failregex = ^<HOST> -.*"(GET|POST|HEAD).*HTTP.*"$
EOF

# Bots maliciosos no Nginx
cat <<EOF > /etc/fail2ban/filter.d/nginx-badbots.conf
[Definition]
failregex = ^<HOST> -.*"GET .* HTTP/.*" 403 .* "(?:Atomic_Email_Hunter|Jorgee|PycURL|libwww-perl|Whacker)"$
EOF

# Tentativas de acesso a scripts inexistentes
cat <<EOF > /etc/fail2ban/filter.d/nginx-noscript.conf
[Definition]
failregex = ^<HOST> -.*"GET .*\.(?:php|asp|exe|pl|cgi) HTTP/.*" 404
EOF

# Tentativas de acesso a home directories
cat <<EOF > /etc/fail2ban/filter.d/nginx-nohome.conf
[Definition]
failregex = ^<HOST> -.*"GET /~.* HTTP/.*" 404
EOF

# Overflow no Apache
cat <<EOF > /etc/fail2ban/filter.d/apache-overflow.conf
[Definition]
failregex = ^\[\] \[error\] \[client <HOST>\] (?:request failed: URI too long|invalid request-line)
EOF
```

## Ativando e verificando

```bash
systemctl restart fail2ban
systemctl enable fail2ban
```

Verifique os jails ativos:

```bash
fail2ban-client status
```

Verifique um jail específico:

```bash
fail2ban-client status sshd
```

Verificar regras do UFW aplicadas:

```bash
ufw status numbered
```

## Comandos úteis do dia a dia

```bash
# Desbanir um IP manualmente
fail2ban-client set sshd unbanip <IP>

# Ver IPs banidos atualmente
fail2ban-client get sshd banned

# Testar um filtro antes de ativar
fail2ban-regex /var/log/auth.log /etc/fail2ban/filter.d/sshd.conf

# Recarregar configuração sem reiniciar
fail2ban-client reload
```

## Sobre o `bantime = -1`

Banimento permanente (`-1`) é agressivo mas eficaz para SSH. Combine com a jail `recidive` para banir IPs que insistem mesmo após múltiplos banimentos temporários. Mantenha sempre um IP de gerência na lista `ignoreip` para não se bloquear do próprio servidor.
