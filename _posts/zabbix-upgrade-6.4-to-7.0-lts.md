---
title: "Zabbix 6.4 → 7.0 LTS: upgrading on a new VM, migrating only the configuration"
date: 2026-10-22 18:00:00 -0300
categories: [Monitoring, Zabbix]
tags: [zabbix, upgrade, mysql, ubuntu, apache, letsencrypt, netplan]
description: "A complete, production-tested walkthrough for moving from Zabbix 6.4 (Ubuntu 20.04) to 7.0 LTS (Ubuntu 24.04) on a new VM, bringing hosts, templates and users along without carrying the history."
---

This guide documents a real migration from **Zabbix 6.4.21** running on **Ubuntu 20.04 + MySQL 8.0** to **Zabbix 7.0 LTS** on a **new VM with Ubuntu 24.04**. The environment had about **470 hosts**, **130,000 items**, **46,000 triggers** and a **51 GB** database (almost all of it history).

The chosen strategy was to **migrate only the configuration** (hosts, templates, users, actions, maps, dashboards and so on) and leave the history behind. Downtime was a few minutes.

> All names, IPs, domains and passwords in this article are **examples**. Replace them with your own.
{: .prompt-info }

## Example scenario

| Item | Old server | New server |
|---|---|---|
| OS | Ubuntu 20.04 | Ubuntu 24.04 LTS |
| Zabbix | 6.4.21 | 7.0.x LTS |
| Database | MySQL 8.0.42 | MySQL 8.0.4x |
| PHP | 7.4 | 8.3 |
| Primary IP | `192.0.2.10` | `192.0.2.20` (temporary) → `192.0.2.10` |
| Secondary network | `198.51.100.2/24` | `198.51.100.2/24` |
| Domain | `zabbix.example.com` | `zabbix.example.com` |

---

## 1. Why a new VM (and not an in-place upgrade)?

The requirements changed between 6.4 and 7.0:

- **Minimum PHP went from 7.4 to 8.0.** Ubuntu 20.04 ships PHP 7.4, so the frontend won't run without third-party PPAs.
- **Minimum MySQL went from 8.0.0 to 8.0.30.**
- **Ubuntu 20.04 is already out of standard support** (updates only through ESM).

A new VM solves all of this at once and keeps the old server intact as a **rollback**.

### Why Ubuntu 24.04 and not 26.04?

At the time of this migration, the Zabbix **7.0** packages for Ubuntu **26.04** were unstable (missing components, and a repository that disappeared at one point). The **24.04 + Zabbix 7.0** pair is the most stable.

| Combination | When it makes sense |
|---|---|
| Ubuntu 24.04 + Zabbix 7.0 LTS | Maximum stability right now |
| Ubuntu 26.04 + Zabbix 8.0 LTS | Once 8.0 has matured (8.0.1/8.0.2+) |

### Why only the configuration?

With a 51 GB database, `mysqldump` is feasible, but the **import** (single-threaded, rebuilding indexes) takes hours. Without the history:

| Method | Approximate downtime |
|---|---|
| Full dump + restore (51 GB) | 3 to 7 hours |
| Physical copy of the datadir (rsync) | ~10 min + schema upgrade |
| **Configuration only** | **~5 minutes** |

Graphs start from zero, but hosts, templates, triggers, users, permissions, actions, media types, maps and dashboards all come along.

---

## 2. Inventory on the old server

Version and database type:

```bash
zabbix_server -V | head -1
dpkg -l | grep zabbix-server     # zabbix-server-mysql or zabbix-server-pgsql
mysql -V
grep ^DB /etc/zabbix/zabbix_server.conf
```

Database size and the largest tables (reads statistics only, no load on the server):

```bash
mysql -u root -p -t -e "
SELECT table_name AS tbl,
       FORMAT(table_rows,0) AS row_count,
       ROUND((data_length+index_length)/1024/1024/1024,2) AS GB
FROM information_schema.tables
WHERE table_schema='zabbix'
ORDER BY (data_length+index_length) DESC
LIMIT 15;"
```

Almost all the volume sits in `history_uint`, `history`, `trends_uint` and `trends`.

Save the server's active parameters (you'll need the tunings later):

```bash
grep -vE '^\s*#|^\s*$' /etc/zabbix/zabbix_server.conf > /root/server_conf_active.txt
```

Also list everything else that will need migrating:

```bash
ls -la /usr/lib/zabbix/alertscripts /usr/lib/zabbix/externalscripts
cat /etc/netplan/*.yaml
ip route
ls -l /etc/apache2/sites-enabled/
ls /etc/letsencrypt/live/ 2>/dev/null
```

> If your `zabbix_server.conf` uses **`DBUser=root`**, fix it during the migration. On the new server we'll use a dedicated `zabbix` user.
{: .prompt-warning }

---

## 3. Preparing the new VM (Ubuntu 24.04)

Update and set the time zone:

```bash
apt update && apt -y upgrade
timedatectl set-timezone America/Sao_Paulo
reboot
```

Add the official Zabbix 7.0 repository:

```bash
wget https://repo.zabbix.com/zabbix/7.0/ubuntu/pool/main/z/zabbix-release/zabbix-release_latest_7.0+ubuntu24.04_all.deb
dpkg -i zabbix-release_latest_7.0+ubuntu24.04_all.deb
apt update
```

> Skipping this step gives you `E: Unable to locate package zabbix-server-mysql`.
{: .prompt-tip }

Install MySQL, the server, the frontend and agent 2:

```bash
apt install -y mysql-server zabbix-server-mysql zabbix-frontend-php \
  zabbix-apache-conf zabbix-sql-scripts zabbix-agent2
```

Keep the server from starting too early:

```bash
systemctl stop zabbix-server && systemctl disable zabbix-server
apt policy zabbix-server-mysql      # should point to repo.zabbix.com
```

The package pulls in `snmpd` as a dependency. If the VM doesn't need to be monitored over SNMP:

```bash
systemctl disable --now snmpd
```

### Database and dedicated user

```bash
mysql
```

```sql
CREATE DATABASE zabbix CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
CREATE USER 'zabbix'@'localhost' IDENTIFIED BY 'STRONG_PASSWORD_HERE';
GRANT ALL PRIVILEGES ON zabbix.* TO 'zabbix'@'localhost';
SET GLOBAL log_bin_trust_function_creators = 1;
QUIT;
```

> Do **not** import the clean-install `server.sql.gz`. The schema will come from your dump.
{: .prompt-danger }

If two VMs with the same hostname are up at the same time, rename the new one temporarily so you don't run a command on the wrong server:

```bash
hostnamectl set-hostname zabbix-new
```

---

## 4. Configuration-only dump (old server)

The idea: one dump with the **structure of every table** and another with the **data of everything except history**.

```bash
read -s -p "MySQL root password: " MYSQL_PWD; export MYSQL_PWD; echo

# Tables whose DATA will be skipped
IGN=$(mysql -u root -N -e "SELECT CONCAT('--ignore-table=zabbix.',table_name)
  FROM information_schema.tables WHERE table_schema='zabbix'
  AND (table_name LIKE 'history%' OR table_name LIKE 'trends%' OR table_name='auditlog');")
echo "$IGN"
```

Expected output:

```
--ignore-table=zabbix.auditlog
--ignore-table=zabbix.history
--ignore-table=zabbix.history_log
--ignore-table=zabbix.history_str
--ignore-table=zabbix.history_text
--ignore-table=zabbix.history_uint
--ignore-table=zabbix.trends
--ignore-table=zabbix.trends_uint
```

The two dumps:

```bash
# 1) Structure of ALL tables (history/trends come out empty)
mysqldump -u root --single-transaction --no-data \
  --default-character-set=utf8mb4 zabbix | gzip > /root/zbx_schema.sql.gz

# 2) Data, except history/trends/auditlog
mysqldump -u root --single-transaction --no-create-info --skip-triggers \
  --default-character-set=utf8mb4 $IGN zabbix | gzip > /root/zbx_data.sql.gz

unset MYSQL_PWD
ls -lh /root/zbx_*.sql.gz
zcat /root/zbx_schema.sql.gz | tail -1     # -- Dump completed on ...
zcat /root/zbx_data.sql.gz   | tail -1     # -- Dump completed on ...
```

In the example scenario, a 51 GB database turned into **24 MB** of data + **19 KB** of schema, in under a minute.

Key points:

- `--single-transaction` gives a consistent snapshot **without stopping Zabbix**.
- `--skip-triggers` on the data dump avoids creating the triggers twice (they already come with the structure dump).
- Run everything **in the same shell session**: the `$IGN` and `$MYSQL_PWD` variables are lost in another terminal.
- From here until the cutover, **don't change hosts/templates** on the old server.

---

## 5. Transferring the dumps

```bash
scp /root/zbx_*.sql.gz user@192.0.2.20:/home/user/
```

> If the old server's SSH doesn't accept connections (different port, root blocked), reverse the direction: **push** from the old server to the new one, as above.
{: .prompt-tip }

On the new VM:

```bash
mv /home/user/zbx_*.sql.gz /root/
```

---

## 6. Importing on the new VM (and the two gotchas)

Check that the database is empty:

```bash
mysql -e "SELECT COUNT(*) AS tables FROM information_schema.tables WHERE table_schema='zabbix';"
```

### Gotcha 1: `ERROR 1227 ... SUPER or SET_USER_ID privilege`

If the old database used `root`, the dump's triggers come with `DEFINER=root@localhost`, and the `zabbix` user can't create them on behalf of another user.

**Fix:** import as **root** (on Ubuntu 24.04, MySQL's root logs in through the socket, without a password, when you're logged in as root on the system).

### Gotcha 2: `ERROR 1118 Row size too large (> 8126)`

This happens on the **`host_inventory`** table, which has dozens of `varchar` columns. With `innodb_strict_mode` on, MySQL 8 refuses to create the table based on the *theoretical* sum of the columns, even though it works fine in practice (long columns are stored off-page).

Confirm it isn't an inherited `ROW_FORMAT=COMPACT`:

```bash
zcat /root/zbx_schema.sql.gz | grep -c "ROW_FORMAT"      # 0 = that's not it
```

**Fix:** turn strict mode off only during the import **and the schema upgrade**.

### Import

```bash
mysql -e "DROP DATABASE zabbix; CREATE DATABASE zabbix CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;"
mysql -e "SET GLOBAL innodb_strict_mode = OFF; SET GLOBAL log_bin_trust_function_creators = 1;"

zcat /root/zbx_schema.sql.gz | mysql --default-character-set=utf8mb4 zabbix
zcat /root/zbx_data.sql.gz   | mysql --default-character-set=utf8mb4 zabbix

mysql -e "SELECT COUNT(*) AS hosts FROM zabbix.hosts; SELECT mandatory FROM zabbix.dbversion;"
```

Expected: your environment's host count and `mandatory = 6040000` (6.4 schema).

> Keep `innodb_strict_mode = OFF` until the schema upgrade finishes. The upgrade may alter `host_inventory` and would hit the same error.
{: .prompt-warning }

Set a known password for the `zabbix` user:

```bash
mysql -e "ALTER USER 'zabbix'@'localhost' IDENTIFIED BY 'STRONG_PASSWORD_HERE';"
mysql -u zabbix -p -e "SELECT 1;" zabbix
```

---

## 7. Configuring and starting Zabbix server 7.0

Edit `/etc/zabbix/zabbix_server.conf`:

```ini
DBName=zabbix
DBUser=zabbix
DBPassword=STRONG_PASSWORD_HERE
```

> **Don't copy the old `zabbix_server.conf` wholesale.** Some parameters changed in 7.0. Replicate your tunings one parameter at a time from `server_conf_active.txt`.
{: .prompt-warning }

Start it and follow the schema upgrade:

```bash
systemctl enable --now zabbix-server
tail -f /var/log/zabbix/zabbix_server.log
```

With a configuration-only database, it takes a few minutes:

```
completed 99% of database upgrade
completed 100% of database upgrade
database upgrade fully completed
```

Reset the MySQL parameters and confirm the schema version:

```bash
mysql -e "SET GLOBAL innodb_strict_mode = ON; SET GLOBAL log_bin_trust_function_creators = 0;"
mysql -e "SELECT mandatory FROM zabbix.dbversion;"     # 7000000
systemctl enable --now zabbix-agent2
systemctl restart apache2
```

> Both servers running at the same time produce **duplicate and false alerts** (the new one can't reach every network yet). Until the cutover, keep the new server stopped: `systemctl stop zabbix-server`. The frontend stays reachable for validation.
{: .prompt-danger }

---

## 8. Frontend: the wizard is required

Opening `http://192.0.2.20/zabbix` shows the setup wizard. It **doesn't touch the database**: it only generates `/etc/zabbix/web/zabbix.conf.php`.

1. **Welcome**: language
2. **Pre-requisites**: all OK
3. **DB connection**: MySQL, host `localhost`, port `0`, database `zabbix`, user `zabbix` and the password
4. **Settings**: server name and the `America/Sao_Paulo` time zone
5. **Install → Finish**

The login is the **same as on the old server**, because users come from the database.

---

## 9. Web server and Let's Encrypt certificate

Inspect the old server's vhosts (`-R` follows the `sites-enabled` symlinks):

```bash
grep -RE "ServerName|ServerAlias|DocumentRoot|SSLCertificate|Redirect|Rewrite" /etc/apache2/sites-enabled/
```

A common pattern:

- **port 80**: redirects everything to HTTPS;
- **port 443**: Let's Encrypt certificate, `DocumentRoot /var/www/html`;
- Zabbix is served by the global `/zabbix` alias from the `zabbix-apache-conf` package.

### Copying vhosts and certificate (old server)

```bash
tar czf /root/web-le.tgz /etc/letsencrypt \
  /etc/apache2/sites-available/zabbix.example.com.conf \
  /etc/apache2/sites-available/zabbix.example.com-le-ssl.conf
scp /root/web-le.tgz user@192.0.2.20:/home/user/
```

> **Don't migrate an old phpMyAdmin** published under `/var/www/html`. An outdated version exposed to the internet, with direct database access, is a serious risk, and it probably won't even run on PHP 8.3. Use `mysql` over SSH or an SSH tunnel with DBeaver.
{: .prompt-danger }

### Applying (new server)

```bash
apt install -y certbot python3-certbot-apache
tar xzf /home/user/web-le.tgz -C /
ls -l /etc/letsencrypt/live/zabbix.example.com/     # symlinks to ../../archive/...

a2enmod ssl rewrite headers
a2ensite zabbix.example.com.conf zabbix.example.com-le-ssl.conf
apache2ctl configtest && systemctl restart apache2     # restart: the ssl module is new

# Optional: "/" redirects to "/zabbix"
echo '<meta http-equiv="refresh" content="0; url=/zabbix/">' > /var/www/html/index.html

# Optional: silence the AH00558 warning
echo "ServerName zabbix.example.com" > /etc/apache2/conf-available/servername.conf
a2enconf servername && systemctl reload apache2
```

Check the certificate's validity:

```bash
openssl x509 -enddate -noout -in /etc/letsencrypt/live/zabbix.example.com/cert.pem
```

`certbot.timer` is active on the new VM. After the cutover, validate renewal:

```bash
certbot renew --dry-run
```

---

## 10. Network: netplan with a secondary network and static routes

Zabbix servers often have a second interface on a management network, with routes to several monitored networks. **If the new VM lacks that NIC, the hosts on those networks become unreachable.**

Example netplan from the old server:

```yaml
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: true
    eth1:
      dhcp4: no
      addresses: [198.51.100.2/24]
      routes:
        - { to: 10.10.0.0/24,   via: 198.51.100.1, on-link: true }
        - { to: 10.20.0.0/16,   via: 198.51.100.1, on-link: true }
        - { to: 172.16.0.0/16,  via: 198.51.100.1, on-link: true }
        - { to: 192.168.0.0/20, via: 198.51.100.1, on-link: true }
```

On the new VM, **interface names may change** (Xen VMs show up as `enX0`, `enX1`). Adapt it:

```yaml
network:
  version: 2
  ethernets:
    enX0:
      dhcp4: true
    enX1:
      dhcp4: no
      addresses: [198.51.100.2/24]
      routes:
        - { to: 10.10.0.0/24,   via: 198.51.100.1, on-link: true }
        - { to: 10.20.0.0/16,   via: 198.51.100.1, on-link: true }
        - { to: 172.16.0.0/16,  via: 198.51.100.1, on-link: true }
        - { to: 192.168.0.0/20, via: 198.51.100.1, on-link: true }
```

Stop cloud-init from overwriting the file:

```bash
echo "network: {config: disabled}" > /etc/cloud/cloud.cfg.d/99-disable-network-config.cfg
chmod 600 /etc/netplan/50-cloud-init.yaml
```

Check whether the old server has routes outside netplan (`/etc/rc.local`, `/etc/network/`) by comparing `ip route` with the YAML.

### Primary IP via the orchestrator's DHCP

If the primary interface gets its IP from a cloud orchestrator's DHCP (CloudStack, OpenStack, etc.), **don't hard-code the IP**: anti-spoofing may block it and the inventory becomes inconsistent. Move the IP through the orchestrator itself:

1. Stop the old VM.
2. Release the IP from the old NIC (change it to another or remove the NIC).
3. With the new VM stopped, assign the old IP to its NIC.
4. Move the **Static NAT / Port Forwarding** rules for the public IP to the new VM (DNS doesn't change).

### Cutover order

1. Stop the old VM (**don't destroy it**).
2. Move the primary IP and NAT to the new VM.
3. Start the new VM and, **from the console** (SSH on the temporary IP will drop):

```bash
netplan try           # rolls back by itself after 120 s if you lose access
ip a; ip route
ping -c2 198.51.100.1
systemctl enable --now zabbix-server
```

4. Open `https://zabbix.example.com` and check *Latest data*.
5. `certbot renew --dry-run`.

---

## 11. First production start: `please increase CacheSize`

On the first start with every host, the server went into a restart loop. The log showed:

```
__zbx_shmem_realloc(): out of memory (requested 14736 bytes)
__zbx_shmem_realloc(): please increase CacheSize configuration parameter
One child process died ... Exiting ...
```

The default `CacheSize` (32 MB) can't hold the configuration of 130,000 items. Since only the configuration was migrated, **the old server's tunings didn't come along**.

### Sizing

`CacheSize` holds **only the configuration** (hosts, items, triggers, macros). Rule of thumb: 1 to 2 KB per item.

```bash
mysql -e "SELECT COUNT(*) AS items FROM zabbix.items; SELECT COUNT(*) AS triggers FROM zabbix.triggers;"
free -h
```

| Items | Suggested CacheSize |
|---|---|
| up to ~150k | 512M |
| 150–400k | 1G |
| over 400k | 2G or more |

For ~130,000 items on a 16 GB VM:

```bash
sed -i 's/^#\? *CacheSize=.*/CacheSize=512M/' /etc/zabbix/zabbix_server.conf

cat >> /etc/zabbix/zabbix_server.conf <<'EOF'

# Post-migration tuning
HistoryCacheSize=256M
HistoryIndexCacheSize=64M
TrendCacheSize=128M
ValueCacheSize=512M
EOF

grep -E '^(CacheSize|HistoryCacheSize|HistoryIndexCacheSize|TrendCacheSize|ValueCacheSize)=' \
  /etc/zabbix/zabbix_server.conf      # exactly 5 lines
systemctl restart zabbix-server
```

> Each parameter must appear **exactly once** without `#`. Edits in nano that don't remove the `#` are a common cause of "I set it and nothing changed".
{: .prompt-tip }

The **"More than 75% used in the trends cache"** alert right after startup is `TrendCacheSize` still at its 4 MB default. It clears on its own after the change.

### MySQL

The default buffer pool is 128 MB. In `/etc/mysql/mysql.conf.d/mysqld.cnf` (`[mysqld]` section):

```ini
innodb_buffer_pool_size = 6G
innodb_redo_log_capacity = 1G
innodb_flush_log_at_trx_commit = 2
```

```bash
systemctl restart mysql && systemctl restart zabbix-server
mysql -e "SELECT @@innodb_buffer_pool_size/1024/1024/1024 AS buffer_GB,
                 @@innodb_redo_log_capacity/1024/1024 AS redo_MB,
                 @@innodb_flush_log_at_trx_commit AS flush;"
```

`flush_log_at_trx_commit = 2` loses at most ~1 s of data if the VM crashes, which is acceptable for Zabbix.

Rough math: ~1.5 GB of Zabbix caches + 6 GB for MySQL + OS, Apache/PHP and page cache.

---

## 12. Post-migration

### Expected log messages

- **"not enough data"** on calculated items: they depend on previous values and the history was reset. They resolve on their own within minutes.
- Interface items with old names (`eth0`) showing as unsupported: the new VM uses different names. They disappear when discovery's "lost resources period" expires.

### Scripts and certificates

A configuration-only migration **doesn't bring files**. If you use script notifications (Telegram, webhook) or *External checks*, copy them from the old server:

```
/usr/lib/zabbix/alertscripts/
/usr/lib/zabbix/externalscripts/
```

Also copy PSK/TLS files if used with proxies. Validate each media type in *Alerts → Media types → Test*.

### Proxies and agents

- **Proxies**: upgrade them to 7.0 soon. 6.4 proxies keep collecting, but don't receive configuration changes.
- **Agents**: can wait.

### What to watch in the first hours

- *Zabbix server health* dashboard: processes above 75% need more instances (`StartPollers`, `StartPingers`, etc.).
- *Administration → Queue*: items delayed by more than 5 minutes point to a lack of processes.

### Rollback

Keep the old VM **stopped, not destroyed**, for a few days. To roll back: shut down the new one, give back the IP/NAT and start the old one. Its 6.4 database is still intact.

---

## Quick troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Unable to locate package zabbix-server-mysql` | Repository not added | Install the 7.0 `zabbix-release` |
| `ERROR 1227 ... SET_USER_ID` | Triggers with `DEFINER=root` | Import as root |
| `ERROR 1118 Row size too large` | `host_inventory` + strict mode | `innodb_strict_mode=OFF` during import and upgrade |
| `ERROR 1007 database exists` | Database already created | Check that it's empty |
| `scp: Connection refused` | Old server's SSH closed/different port | Push from old to new |
| Server looping, `please increase CacheSize` | 32 MB default cache | `CacheSize=512M` or more |
| Trends cache alert > 75% | Default `TrendCacheSize` (4 MB) | `TrendCacheSize=128M` |
| Hosts on one network unreachable | Missing secondary NIC/routes | Second NIC + routes in netplan |

## Checklist

- [ ] Inventory: version, database, size, active conf, scripts, network, vhosts
- [ ] New VM with the 7.0 repository, packages, and the server **stopped**
- [ ] Database and dedicated `zabbix` user
- [ ] Structure dump + data dump without history/trends
- [ ] Import as root with `innodb_strict_mode=OFF`
- [ ] Schema upgrade complete (`7000000`), strict mode back ON
- [ ] Frontend wizard
- [ ] Vhosts and Let's Encrypt
- [ ] Netplan with secondary network and routes
- [ ] Cutover: IP, NAT, server start
- [ ] Zabbix caches and MySQL buffer pool tuned
- [ ] Scripts, PSK, proxies
- [ ] Old VM preserved for rollback
