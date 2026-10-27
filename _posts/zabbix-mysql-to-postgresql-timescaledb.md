---
title: "Zabbix 7.0: migrating from MySQL to PostgreSQL + TimescaleDB"
date: 2026-10-25 14:00:00 -0300
categories: [Monitoring, Zabbix]
tags: [zabbix, postgresql, timescaledb, mysql, pgloader, python, tuning]
description: "How to move the Zabbix 7.0 database from MySQL 8 to PostgreSQL 16 with TimescaleDB, working around pgloader's bugs with MySQL 8, plus tuning and compression."
---

This follows the 6.4 → 7.0 upgrade article. With Zabbix 7.0 running on MySQL 8, the next step was switching the database to **PostgreSQL 16 + TimescaleDB**. The reason: in an environment with **~130,000 items**, the database grew about **5 GB per day**, and the MySQL housekeeper deletes history row by row.

The result: a migration with a few minutes of downtime, MySQL preserved as a rollback, and history partitioned and compressed by TimescaleDB.

> All names, IPs, domains and passwords in this article are **examples**.
{: .prompt-info }

## Why PostgreSQL + TimescaleDB?

The real gain isn't PostgreSQL itself, it's **TimescaleDB**:

- **Automatic partitioning** of `history*` and `trends*` into time-based chunks.
- **Chunk-level housekeeping**: instead of row-by-row `DELETE`, Zabbix drops whole chunks. Much lighter.
- **Native compression** of older data, typically reducing size by more than 90%.

### What about MariaDB?

Zabbix 7.0 supports it, but it doesn't make sense here:

| Option | Assessment |
|---|---|
| Stay on MySQL 8 | Fine while the housekeeper keeps up |
| MariaDB | A sideways move with no real gain; migrating from MySQL 8 has friction (collations, syntax) |
| PostgreSQL + TimescaleDB | The path for large environments |

### The best time

Right after the upgrade, while the history is still small. Here we'll again bring **only the configuration** (no `history*`, `trends*` or `auditlog`).

---

## Overview

1. Back up the configuration in MySQL.
2. Install PostgreSQL and load the official Zabbix 7.0 schema.
3. Copy the data MySQL → PostgreSQL.
4. Swap the server package and point the server and frontend at PostgreSQL.
5. Stop MySQL (kept for rollback).
6. Tune PostgreSQL.
7. Install TimescaleDB, convert the tables and enable compression.

Zabbix keeps running on MySQL until step 3.

---

## 1. Backup and checks

```bash
mysql -e "SELECT ROUND(SUM(data_length+index_length)/1024/1024/1024,2) AS GB
          FROM information_schema.tables WHERE table_schema='zabbix';"
df -h /
```

Configuration-only backup (fast):

```bash
IGN=$(mysql -N -e "SELECT CONCAT('--ignore-table=zabbix.',table_name)
  FROM information_schema.tables WHERE table_schema='zabbix'
  AND (table_name LIKE 'history%' OR table_name LIKE 'trends%' OR table_name='auditlog');")
mysqldump --single-transaction --no-data zabbix | gzip > /root/bkp_pre_pg_schema.sql.gz
mysqldump --single-transaction --no-create-info --skip-triggers $IGN zabbix | gzip > /root/bkp_pre_pg_data.sql.gz
ls -lh /root/bkp_pre_pg_*
```

> MySQL 8 ships with the **binlog enabled** and writes everything again to `/var/lib/mysql/binlog.*`. On a write-heavy database, that takes up many GB. Worth knowing before you plan disk space.
{: .prompt-tip }

---

## 2. PostgreSQL and the official schema

```bash
apt install -y postgresql php8.3-pgsql
psql --version          # PostgreSQL 16.x on Ubuntu 24.04

sudo -u postgres createuser --pwprompt zabbix
sudo -u postgres createdb -O zabbix zabbix
sudo -u postgres psql -P pager=off -c "\l zabbix"
```

> Avoid `@`, `:` and `/` in the password: they break connection URLs in many tools.
{: .prompt-warning }

Load the official 7.0 schema (structure + initial data, which will be overwritten):

```bash
zcat /usr/share/zabbix-sql-scripts/postgresql/server.sql.gz | sudo -u zabbix psql -q zabbix 2>&1 | tail -5
sudo -u zabbix psql zabbix -c "SELECT mandatory FROM dbversion;"      # 7000000
sudo -u zabbix psql zabbix -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';"
```

Compare with MySQL: the table count must match (203 in Zabbix 7.0).

```bash
mysql -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='zabbix';"
```

---

## 3. Copying the data: why pgloader didn't work

The classic route is `pgloader`. With **MySQL 8**, the Ubuntu 24.04 package (3.6.7) ran into two problems:

### Problem 1: `QMYND:MYSQL-UNSUPPORTED-AUTHENTICATION`

pgloader doesn't understand MySQL 8's default authentication (`caching_sha2_password`), **even with the user created as `mysql_native_password`**, because the server offers its default plugin in the initial handshake. The fix is to change the server default:

```bash
echo "default_authentication_plugin = mysql_native_password" >> /etc/mysql/mysql.conf.d/mysqld.cnf
systemctl restart mysql
```

### Problem 2: `76 fell through ECASE expression` (no fix)

pgloader's MySQL library doesn't recognize **collation 76** (`utf8mb3_tolower_ci`), which MySQL 8 uses in `information_schema`. No configuration change solves it with the distribution package.

### Solution: a Python script with native drivers

Since it's only ~2 million configuration rows, a simple script does the job predictably:

```bash
apt install -y python3-pymysql python3-psycopg2
mysql -e "CREATE USER 'migr'@'127.0.0.1' IDENTIFIED WITH mysql_native_password BY 'TemporaryPass123';
          GRANT SELECT ON zabbix.* TO 'migr'@'127.0.0.1';"
```

The script has two modes:

- **`check`**: compares tables and columns across both databases and counts rows, without writing anything;
- **`run`**: does the copy, with FKs and triggers disabled during the load (`session_replication_role = replica`).

```python
#!/usr/bin/env python3
# /opt/my2pg.py — copies the Zabbix configuration from MySQL to PostgreSQL
import sys, pymysql, psycopg2, psycopg2.extras

MODE = sys.argv[1] if len(sys.argv) > 1 else "check"
SKIP_PREFIX = ("history", "trends")
SKIP = {"auditlog"}

my = pymysql.connect(host="127.0.0.1", user="migr", password="TemporaryPass123",
                     database="zabbix", charset="utf8mb4")
pg = psycopg2.connect(dbname="zabbix")   # runs as the postgres user (peer)
pc, mc = pg.cursor(), my.cursor()

pc.execute("SELECT table_name FROM information_schema.tables "
           "WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY 1")
pg_tables = [r[0] for r in pc.fetchall()]
mc.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='zabbix'")
my_tables = {r[0] for r in mc.fetchall()}

tables = [t for t in pg_tables if not t.startswith(SKIP_PREFIX) and t not in SKIP]
plan, problems = [], 0
for t in tables:
    if t not in my_tables:
        print(f"[WARN] {t}: not in MySQL"); problems += 1; continue
    pc.execute("SELECT column_name FROM information_schema.columns "
               "WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position", (t,))
    pcols = [r[0] for r in pc.fetchall()]
    mc.execute("SELECT column_name FROM information_schema.columns "
               "WHERE table_schema='zabbix' AND table_name=%s", (t,))
    mcols = {r[0] for r in mc.fetchall()}
    only_pg, only_my = set(pcols) - mcols, mcols - set(pcols)
    if only_pg or only_my:
        print(f"[WARN] {t}: only in PG={sorted(only_pg)} only in MySQL={sorted(only_my)}"); problems += 1
    plan.append((t, [c for c in pcols if c in mcols]))

for t in sorted(my_tables - set(pg_tables)):
    print(f"[WARN] {t}: exists in MySQL but not in PG"); problems += 1

if MODE == "check":
    total = 0
    for t, _ in plan:
        mc.execute(f"SELECT COUNT(*) FROM `{t}`"); total += mc.fetchone()[0]
    print(f"\nTables to copy: {len(plan)} | rows: {total} | warnings: {problems}")
    sys.exit(0)

pc.execute("SET session_replication_role = replica")
pc.execute("TRUNCATE " + ", ".join(f'"{t}"' for t, _ in plan))   # clears the initial data
grand = 0
for t, cols in plan:
    sc = my.cursor(pymysql.cursors.SSCursor)
    sc.execute("SELECT " + ",".join(f"`{c}`" for c in cols) + f" FROM `{t}`")
    ins = f'INSERT INTO "{t}" (' + ",".join(f'"{c}"' for c in cols) + ") VALUES %s"
    n = 0
    while True:
        rows = sc.fetchmany(5000)
        if not rows: break
        psycopg2.extras.execute_values(pc, ins, rows, page_size=1000)
        n += len(rows)
    sc.close(); grand += n
    print(f"{t:40s} {n}")
pg.commit()
print(f"\nOK: {len(plan)} tables, {grand} rows copied")
```

Details that matter:

- **Every table is truncated before** the load. Truncating table by table with `CASCADE` would wipe data already loaded into dependent tables.
- The script runs as `postgres` because `session_replication_role` requires a superuser.
- It copies **only the common columns** and reports any schema mismatch.

Validation, without writing anything:

```bash
chmod 755 /opt/my2pg.py
sudo -u postgres python3 /opt/my2pg.py check
```

Expected (Zabbix 7.0): `Tables to copy: 194 | rows: ... | warnings: 0`. That's 203 tables minus the 9 excluded ones.

### Cutover window

```bash
systemctl stop zabbix-server
sudo -u postgres python3 /opt/my2pg.py run 2>&1 | tee /root/my2pg.log | tail -25
```

About 2 million rows take 1 to 3 minutes. Validate:

```bash
sudo -u zabbix psql zabbix -c "SELECT COUNT(*) AS hosts FROM hosts;"
sudo -u zabbix psql zabbix -c "SELECT COUNT(*) AS items FROM items;"
sudo -u zabbix psql zabbix -c "SELECT mandatory, optional FROM dbversion;"
mysql -N -e "SELECT COUNT(*) FROM zabbix.hosts;"       # must match
sudo -u postgres psql zabbix -c "VACUUM ANALYZE;"
```

---

## 4. Pointing the server and frontend at PostgreSQL

Back up the configuration files (needed for rollback):

```bash
cp -a /etc/zabbix/zabbix_server.conf /root/zabbix_server.conf.mysql
cp -a /etc/zabbix/web/zabbix.conf.php /root/zabbix.conf.php.mysql
```

Swap the server package. `zabbix-server-mysql` is removed and the `.conf` is kept:

```bash
apt install -y zabbix-server-pgsql
dpkg -l | grep zabbix-server       # ii pgsql / rc mysql
```

### `zabbix_server.conf`

```bash
read -s -p "PostgreSQL zabbix user password: " PGPW; echo
```

> Run `read -s` **on its own**, not pasted together with other commands. When you paste a whole block, `read` may capture the next line as the "password".
{: .prompt-warning }

```bash
C=/etc/zabbix/zabbix_server.conf
sed -i -E 's/^#? *DBHost=.*/DBHost=localhost/' $C
sed -i -E 's/^#? *DBUser=.*/DBUser=zabbix/' $C
sed -i -E "s|^#? *DBPassword=.*|DBPassword=${PGPW}|" $C
sed -i -E 's/^#? *DBPort=.*/DBPort=5432/' $C

# sed may change both the active AND the commented line: remove duplicates
sed -i '0,/^DBUser=/! {/^DBUser=/d}' $C
grep -E '^DB' $C | sed 's/DBPassword=.*/DBPassword=***/'

# Test the password that ended up in the file
PGPASSWORD="$(grep '^DBPassword=' $C | cut -d= -f2-)" psql -h localhost -U zabbix zabbix -c "SELECT 'password ok';"
```

### Frontend (`zabbix.conf.php`)

```bash
PGPW="$(grep '^DBPassword=' /etc/zabbix/zabbix_server.conf | cut -d= -f2-)"
F=/etc/zabbix/web/zabbix.conf.php
sed -i -E "s/(\\\$DB\['TYPE'\]\s*=\s*)'[^']*'/\1'POSTGRESQL'/" $F
sed -i -E "s/(\\\$DB\['SERVER'\]\s*=\s*)'[^']*'/\1'localhost'/" $F
sed -i -E "s/(\\\$DB\['PORT'\]\s*=\s*)'[^']*'/\1'5432'/" $F
sed -i -E "s/(\\\$DB\['PASSWORD'\]\s*=\s*)'[^']*'/\1'${PGPW}'/" $F
grep -E "\\\$DB\['(TYPE|SERVER|PORT|DATABASE|USER|SCHEMA)'\]" $F
```

### Start and validate

```bash
systemctl start zabbix-server
systemctl restart apache2
sleep 20
systemctl status zabbix-server --no-pager | head -5
grep -iE "database|too many|connection" /var/log/zabbix/zabbix_server.log | grep -vi "not enough data" | tail -10
sudo -u postgres psql -c "SELECT count(*) AS zabbix_connections FROM pg_stat_activity WHERE usename='zabbix';"
sudo -u zabbix psql zabbix -c "SELECT COUNT(*) AS values FROM history_uint;"     # growing
```

Validate in the browser too: login, *Latest data* with current timestamps, and *Reports → System information* showing PostgreSQL.

---

## 5. Stopping MySQL (preserved)

```bash
mysql -e "DROP USER 'migr'@'127.0.0.1';"
systemctl stop mysql
systemctl disable mysql
du -sh /var/lib/mysql        # the data stays there for rollback
```

---

## 6. Tuning PostgreSQL

Ubuntu's default configuration is conservative (`shared_buffers` of 128 MB, `random_page_cost` of 4, meant for spinning disks). Ubuntu automatically includes files from `conf.d`, so there's no need to touch `postgresql.conf`:

```ini
# /etc/postgresql/16/main/conf.d/zabbix-tuning.conf  (16 GB VM, SSD/flash storage)

# Memory
shared_buffers = 4GB
effective_cache_size = 11GB
work_mem = 16MB
maintenance_work_mem = 1GB
wal_buffers = 16MB

# Connections (Zabbix used ~31 in this environment, plus the frontend)
max_connections = 200

# WAL / checkpoints
min_wal_size = 1GB
max_wal_size = 4GB
checkpoint_completion_target = 0.9
synchronous_commit = off

# SSD/flash storage
random_page_cost = 1.1
effective_io_concurrency = 200

# Parallelism
max_worker_processes = 8
max_parallel_workers = 4
max_parallel_workers_per_gather = 2
```

```bash
systemctl restart postgresql
sudo -u postgres psql -c "SELECT name, setting, unit FROM pg_settings
  WHERE name IN ('shared_buffers','effective_cache_size','work_mem','max_connections','random_page_cost','synchronous_commit');"
```

`synchronous_commit = off` is the equivalent of MySQL's `flush_log_at_trx_commit = 2`: at most ~1 s of data lost if the VM crashes.

---

## 7. TimescaleDB

### Version: the detail that matters most

The official TimescaleDB repository ships versions much newer than Zabbix 7.0 supports. In the 7.0 series, the maximum supported version became **TimescaleDB 2.22.X**. With a newer version, the server only starts with `AllowUnsupportedDBVersions=1`, which isn't recommended in production.

> Check the maximum supported version in the release notes for your exact Zabbix version before installing.
{: .prompt-warning }

```bash
echo "deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -cs) main" \
  > /etc/apt/sources.list.d/timescaledb.list
wget -qO- https://packagecloud.io/timescale/timescaledb/gpgkey | gpg --dearmor -o /etc/apt/trusted.gpg.d/timescaledb.gpg
apt update

apt-cache madison timescaledb-2-postgresql-16 | grep ' 2\.22\.'
apt-cache madison timescaledb-2-loader-postgresql-16 | grep ' 2\.22\.'
```

Install 2.22.x on **both packages** (main and loader must match) and **hold** them so `apt upgrade` doesn't bump the version:

```bash
apt install -y timescaledb-2-postgresql-16=2.22.1~ubuntu24.04 timescaledb-2-loader-postgresql-16=2.22.1~ubuntu24.04
apt-mark hold timescaledb-2-postgresql-16 timescaledb-2-loader-postgresql-16

echo "shared_preload_libraries = 'timescaledb'" >> /etc/postgresql/16/main/conf.d/zabbix-tuning.conf
echo "timescaledb.telemetry_level = off"        >> /etc/postgresql/16/main/conf.d/zabbix-tuning.conf
systemctl restart postgresql
sudo -u postgres psql -c "SHOW shared_preload_libraries;"
```

The memory parameters were already tuned by hand, so `timescaledb-tune` isn't needed.

### Converting the tables

With Zabbix stopped:

```bash
systemctl stop zabbix-server
sudo -u postgres psql zabbix -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"
cat /usr/share/zabbix-sql-scripts/postgresql/timescaledb/schema.sql | sudo -u zabbix psql zabbix 2>&1 | tail -15
```

Expected ending:

```
NOTICE:  migrating data to chunks
NOTICE:  TimescaleDB is configured successfully
DO
```

The `WARNING: column type "character varying" ... does not follow best practices` lines are style recommendations for `auditlog` columns. They don't affect anything.

> In Zabbix 7.0, the script moved and was renamed: from `postgresql/timescaledb.sql` to `postgresql/timescaledb/schema.sql`.
{: .prompt-info }

```bash
sudo -u zabbix psql zabbix -c "SELECT hypertable_name, compression_enabled
  FROM timescaledb_information.hypertables ORDER BY 1;"
systemctl start zabbix-server
```

Expected hypertables: `auditlog`, `history`, `history_bin`, `history_log`, `history_str`, `history_text`, `history_uint`, `trends` and `trends_uint`.

### Compression

Right after the conversion you'll see `compression_enabled = f`. **That's normal**: the Zabbix housekeeper enables compression on its first run (within ~1 hour). Check the configuration (in 7.0 it lives in the `config` table):

```bash
sudo -u zabbix psql zabbix -c "SELECT db_extension, compression_status, compress_older,
  hk_history_global, hk_history, hk_trends_global, hk_trends FROM config;"
```

```
 db_extension | compression_status | compress_older | hk_history_global | hk_history | hk_trends_global | hk_trends
--------------+--------------------+----------------+-------------------+------------+------------------+-----------
 timescaledb  |                  1 | 7d             |                 1 | 7d         |                1 | 120d
```

With the **global override** for history/trends enabled, the housekeeper drops **whole chunks**: that's the main performance gain.

After ~1 hour, every hypertable should show `compression_enabled = t`.

> If history is kept for **7 days** and compression also starts at **7 days** (the minimum allowed), history practically never gets compressed. Compression benefits trends. To keep more raw history cheaply, raise retention (14 or 30 days) in *Administration → Housekeeping*: the days past the 7th get compressed.
{: .prompt-tip }

---

## 8. Cleanup

| Item | Action |
|---|---|
| Files with plain-text passwords (load scripts) | Delete now |
| Migration logs | Delete |
| Copy script | Delete (the temporary user is already gone) |
| `bkp_pre_pg_*` backups and `.conf.mysql` files | Keep until MySQL is removed |
| Passwords that appeared on screen or in a shared terminal | Rotate |

Rotating the PostgreSQL password:

```bash
sudo -u postgres psql -c "ALTER ROLE zabbix WITH PASSWORD 'NEW_PASSWORD';"
# Update DBPassword in zabbix_server.conf and $DB['PASSWORD'] in zabbix.conf.php
systemctl restart zabbix-server
```

After a few stable days, remove MySQL and free up `/var/lib/mysql`.

## Rollback

1. `systemctl stop zabbix-server`
2. `apt install zabbix-server-mysql`
3. Restore `/root/zabbix_server.conf.mysql` and `/root/zabbix.conf.php.mysql`
4. `systemctl enable --now mysql && systemctl start zabbix-server`

The MySQL database stays intact throughout the whole process.

---

## Quick troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| pgloader: `MYSQL-UNSUPPORTED-AUTHENTICATION` | `caching_sha2_password` in the handshake | `default_authentication_plugin = mysql_native_password` |
| pgloader: `76 fell through ECASE` | Unknown MySQL 8 collation | Use the Python script |
| Correct password, but ping/connection fails | `read -s` captured another line | Run `read` on its own; test with `psql` |
| Duplicate `DBUser` in the conf | `sed` changed active and commented lines | `sed -i '0,/^DBUser=/! {/^DBUser=/d}'` |
| `relation "settings" does not exist` | In 7.0 it's the `config` table | Query `config` |
| `compression_enabled = f` after conversion | Housekeeper hasn't run yet | Wait ~1 hour |
| Server refuses to start after installing TimescaleDB | Version above the supported one | Install the supported version and `apt-mark hold` |
