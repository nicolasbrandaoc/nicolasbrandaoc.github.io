---
title: "Linux server protection with UFW and Fail2Ban"
date: 2026-06-26 00:00:00 -0300
categories: [Security, Linux]
tags: [ufw, fail2ban, firewall, hardening, linux]
---

UFW (Uncomplicated Firewall) combined with Fail2Ban is one of the most efficient configurations for protecting Linux servers. UFW manages firewall rules while Fail2Ban monitors logs and automatically bans IPs with suspicious behavior.

## Installation

```bash
apt update && apt install fail2ban ufw -y
```

## Configuring UFW

Set the default policy — block all incoming, allow all outgoing:

```bash
ufw default deny incoming
ufw default allow outgoing
```

Allow only the necessary ports:

```bash
ufw allow 22/tcp      # SSH
ufw allow 80/tcp      # HTTP
ufw allow 443/tcp     # HTTPS
```

Enable the firewall:

```bash
ufw --force enable
ufw status numbered
```

## Configuring Fail2Ban

Create the `/etc/fail2ban/jail.local` file — never edit `jail.conf` directly, as it gets overwritten on updates:

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

### Key parameters

| Parameter | Value | Description |
|---|---|---|
| `bantime = -1` | Permanent | IP banned indefinitely |
| `findtime = 10m` | 10 minutes | Time window to count attempts |
| `maxretry = 5` | 5 attempts | Failures before banning |
| `backend = systemd` | systemd | Log source |
| `banaction = ufw` | UFW | Direct integration with the firewall |

## Custom filters

Create filters to detect specific attack patterns:

```bash
# DoS protection for Nginx
cat <<EOF > /etc/fail2ban/filter.d/nginx-dos.conf
[Definition]
failregex = ^<HOST> -.*"(GET|POST|HEAD).*HTTP.*"$
EOF

# Malicious bots on Nginx
cat <<EOF > /etc/fail2ban/filter.d/nginx-badbots.conf
[Definition]
failregex = ^<HOST> -.*"GET .* HTTP/.*" 403 .* "(?:Atomic_Email_Hunter|Jorgee|PycURL|libwww-perl|Whacker)"$
EOF

# Attempts to access non-existent scripts
cat <<EOF > /etc/fail2ban/filter.d/nginx-noscript.conf
[Definition]
failregex = ^<HOST> -.*"GET .*\.(?:php|asp|exe|pl|cgi) HTTP/.*" 404
EOF

# Home directory access attempts
cat <<EOF > /etc/fail2ban/filter.d/nginx-nohome.conf
[Definition]
failregex = ^<HOST> -.*"GET /~.* HTTP/.*" 404
EOF

# Apache overflow
cat <<EOF > /etc/fail2ban/filter.d/apache-overflow.conf
[Definition]
failregex = ^\[\] \[error\] \[client <HOST>\] (?:request failed: URI too long|invalid request-line)
EOF
```

## Enabling and verifying

```bash
systemctl restart fail2ban
systemctl enable fail2ban
```

Check active jails:

```bash
fail2ban-client status
```

Check a specific jail:

```bash
fail2ban-client status sshd
```

Check UFW rules applied:

```bash
ufw status numbered
```

## Useful day-to-day commands

```bash
# Manually unban an IP
fail2ban-client set sshd unbanip <IP>

# View currently banned IPs
fail2ban-client get sshd banned

# Test a filter before enabling
fail2ban-regex /var/log/auth.log /etc/fail2ban/filter.d/sshd.conf

# Reload configuration without restarting
fail2ban-client reload
```

## About `bantime = -1`

Permanent banning (`-1`) is aggressive but effective for SSH. Combine it with the `recidive` jail to ban IPs that persist even after multiple temporary bans. Always keep a management IP in the `ignoreip` list to avoid locking yourself out of your own server.
