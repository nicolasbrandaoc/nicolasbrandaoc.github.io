---
title: "Zabbix 7.0 → 8.0 LTS: in-place upgrade on Ubuntu 24.04 with PostgreSQL + TimescaleDB"
date: 2026-11-09 19:00:00 -0300
categories: [Monitoring, Zabbix]
tags: [zabbix, upgrade, postgresql, timescaledb, ubuntu, agent2, saml]
description: "A production-tested in-place upgrade from Zabbix 7.0 LTS to 8.0 LTS on Ubuntu 24.04 with PostgreSQL 16 and TimescaleDB, including the gotchas: agent 2 plugin path, custom queries disabled by default, the new history_json hypertable, the frontend move to ui/ and SAML certificates."
---

This is the fourth article in the series. With Zabbix 7.0 LTS running on **Ubuntu 24.04 + PostgreSQL 16 + TimescaleDB 2.22**, the next step was **Zabbix 8.0 LTS**. Unlike the 6.4 → 7.0 migration, this one can be done **in place**: the OS and the database already meet the 8.0 requirements.

The upgrade itself takes a few minutes. Most of the work is in the details that change between versions, and they're all documented below.

> All names, IPs, domains and passwords in this article are **examples**. Replace them with your own.
{: .prompt-info }

## Example scenario

| Item | Value |
|---|---|
| Server | `zabbix-01` — Ubuntu 24.04 LTS |
| Zabbix | 7.0.x LTS → 8.0.0 LTS |
| Database | PostgreSQL 16 + TimescaleDB 2.22.1 (held with `apt-mark hold`) |
| Frontend | Apache, `https://zabbix.example.com/zabbix`, SAML login |
| Agent 2 | PostgreSQL plugin with custom queries (TimescaleDB metrics) |

---

## 1. Requirements check

| 8.0 requirement | Minimum | This server | OK? |
|---|---|---|---|
| PHP | 8.2 | 8.3 (Ubuntu 24.04) | ✅ |
| PostgreSQL | 15 | 16 | ✅ |
| TimescaleDB | 2.20 | 2.22.1 | ✅ |
| MySQL / MariaDB (if used) | 8.4 / 10.11 | — | — |

Upgrading directly from 7.0 LTS to 8.0 LTS is supported, without going through 7.2 or 7.4.

### What changes in 8.0 and may affect you

- **Frontend path:** since 7.2 the frontend lives in `/usr/share/zabbix/ui`. Anything you placed in the old `/usr/share/zabbix/conf/` (such as **SAML certificates**) must be moved.
- **New hypertable:** 8.0 adds `history_json`. The server doesn't convert it to a TimescaleDB hypertable on its own.
- **Settings table:** the global settings moved from `config` to `settings` (name/value).
- **Agent 2 PostgreSQL plugin:** new binary path and **custom queries disabled by default**.
- **Legacy macros removed:** `{ACK.*}`, `{HOSTNAME<1-9>}`, `{IPADDRESS<1-9>}`, `{PROFILE.*}`, `{TRIGGER.COMMENT}`, `{TRIGGER.KEY}`, `{STATUS}`, `{USER.ALIAS}`.
- **API:** disabled by default for new installations and roles; empty allow lists now deny everything.
- **HTTP templates and webhooks** verify TLS by default.
- **Templates** are not updated automatically.
- **Proxies** on 7.0 keep collecting in a limited mode until upgraded.

> The database schema upgrade **can't be undone**. Take a **full VM snapshot/backup** before you start. It's the only real rollback.
{: .prompt-danger }

---

## 2. Backup and inventory

Even with a VM snapshot, keep local copies of the configuration and the SAML certificates. Restoring a single file is much faster than restoring a whole machine.

```bash
mkdir -p /root/pre-8.0
cp -a /etc/zabbix /root/pre-8.0/etc-zabbix
cp -a /usr/share/zabbix/conf/certs /root/pre-8.0/saml-certs
cp -a /etc/apache2/sites-available /root/pre-8.0/apache-sites

dpkg -l | grep -E "zabbix|timescaledb" | awk '{print $1, $2, $3}'
ls /etc/apt/sources.list.d/
apt-mark showhold
sudo -u zabbix psql -At zabbix -c "SELECT mandatory FROM dbversion;"     # 7000000
df -h /
```

---

## 3. Switch the repository to 8.0

Remove the 7.0 repository files and install the 8.0 release package:

```bash
rm -f /etc/apt/sources.list.d/zabbix.sources /etc/apt/sources.list.d/zabbix-tools.sources
cd /root
wget https://repo.zabbix.com/zabbix/8.0/release/ubuntu/pool/main/z/zabbix-release/zabbix-release_latest_8.0+ubuntu24.04_all.deb
dpkg -i zabbix-release_latest_8.0+ubuntu24.04_all.deb
```

`dpkg` asks about the file you just deleted:

```
Configuration file '/etc/apt/sources.list.d/zabbix.sources'
 ==> Deleted (by you or by a script) since installation.
 ==> Package distributor has shipped an updated version.
*** zabbix.sources (Y/I/N/O/D/Z) [default=N] ?
```

> Answer **`Y`**. The default `N` keeps the deleted file deleted, and apt ends up with no Zabbix repository at all.
{: .prompt-warning }

Check that the candidate comes from the **stable** 8.0 repository, and that the `unstable` one is disabled:

```bash
grep -i enabled /etc/apt/sources.list.d/zabbix-unstable.sources     # Enabled: no
apt update
apt policy zabbix-server-pgsql zabbix-frontend-php
```

Expected:

```
zabbix-server-pgsql:
  Installed: 1:7.0.x-1+ubuntu24.04
  Candidate: 2:8.0.0-1+ubuntu24.04
        500 https://repo.zabbix.com/zabbix/8.0/stable/ubuntu noble/main amd64 Packages
```

---

## 4. Upgrade the packages

Stop the server and upgrade. `--force-confold` keeps the configuration files you edited (such as `zabbix_server.conf`) without prompting. Files you never touched, like `/etc/zabbix/apache.conf`, get the new version, which already points to the new frontend path.

```bash
systemctl stop zabbix-server
DEBIAN_FRONTEND=noninteractive apt-get install -y --only-upgrade \
  -o Dpkg::Options::="--force-confold" \
  zabbix-server-pgsql zabbix-frontend-php zabbix-apache-conf zabbix-sql-scripts \
  zabbix-agent2 zabbix-agent2-plugin-postgresql
dpkg -l | grep zabbix | awk '{print $1, $2, $3}'
```

Warnings like these are harmless. The old directory still contains files you placed there, so `dpkg` can't remove it:

```
dpkg: warning: unable to delete old directory '/usr/share/zabbix/conf/certs': Directory not empty
```

If you use agent 2 with the PostgreSQL plugin, the upgrade probably **fails at this point**. See the next section.

---

## 5. Agent 2: fixing the PostgreSQL plugin

### 5.1. `failed to start plugin process ... no such file or directory`

```
iF zabbix-agent2 2:8.0.0-1+ubuntu24.04
iU zabbix-agent2-plugin-postgresql 1:8.0.0-1+ubuntu24.04
```

```bash
zabbix_agent2 -T -c /etc/zabbix/zabbix_agent2.conf 2>&1 | tail -3
```

```
ERROR: Cannot register plugins: failed to register metrics of plugin "PostgreSQL":
failed to start plugin process "/usr/sbin/zabbix-agent2-plugin/zabbix-agent2-plugin-postgresql":
no such file or directory.
```

**Cause:** in 8.0 the plugin binary moved to `/usr/libexec/zabbix/`. Since `plugins.d/postgresql.conf` had been edited (to add the custom queries path), `dpkg` kept the old file and saved the new one as `postgresql.conf.dpkg-new`.

Confirm the new path:

```bash
grep -vE '^\s*#|^\s*$' /etc/zabbix/zabbix_agent2.d/plugins.d/postgresql.conf.dpkg-new
dpkg -L zabbix-agent2-plugin-postgresql | grep -i 'libexec'
```

```
Plugins.PostgreSQL.System.Path=/usr/libexec/zabbix/zabbix-agent2-plugin-postgresql
/usr/libexec/zabbix/zabbix-agent2-plugin-postgresql
```

### 5.2. Custom queries are disabled by default

In 8.0 the plugin has a new parameter, **`Plugins.PostgreSQL.CustomQueriesEnabled`**, which defaults to **`false`**. Without it, every `pgsql.custom.query` item returns:

```
[m|ZBX_NOTSUPPORTED] [Key "pgsql.custom.query" is disabled.]
```

### 5.3. File permissions

`postgresql.conf.dpkg-new` is created as **`root:root 640`**. After moving it into place, the agent (which runs as the `zabbix` user) can't read it. The test passes as root but the service fails:

```
ERROR: Cannot read configuration: cannot include ".../plugins.d/postgresql.conf": ... permission denied.
```

> Always validate the agent configuration **as the service user** (`sudo -u zabbix zabbix_agent2 -T ...`). Running the test as root hides permission problems.
{: .prompt-tip }

### 5.4. The fix

```bash
cd /etc/zabbix/zabbix_agent2.d/plugins.d
mv postgresql.conf.dpkg-new postgresql.conf
cat >> postgresql.conf <<'EOF'
Plugins.PostgreSQL.CustomQueriesPath=/etc/zabbix/zabbix_agent2.d/pgsql_queries
Plugins.PostgreSQL.CustomQueriesEnabled=true
EOF
chown root:zabbix postgresql.conf

grep -vE '^\s*#|^\s*$' postgresql.conf
sudo -u zabbix /usr/sbin/zabbix_agent2 -T -c /etc/zabbix/zabbix_agent2.conf 2>&1 | tail -1   # Validation successful

dpkg --configure -a
dpkg -l | grep zabbix | awk '{print $1, $2, $3}'     # all "ii"
systemctl restart zabbix-agent2 && systemctl is-active zabbix-agent2
```

Test a custom query (here, one that returns the TimescaleDB version):

```bash
zabbix_agent2 -t 'pgsql.custom.query["tcp://localhost:5432","zbx_monitor","MONITOR_PASSWORD","zabbix","tsdb_version"]'
```

```
[s|[{"extversion":"2.22.1"}]]
```

---

## 6. Frontend: the move to `ui/` and SAML certificates

Check the new layout:

```bash
ls -la /usr/share/zabbix/ui/conf/
grep -n "Alias" /etc/zabbix/apache.conf
```

Expected:

```
zabbix.conf.php -> /etc/zabbix/web/zabbix.conf.php
    Alias /zabbix /usr/share/zabbix/ui
```

`zabbix.conf.php` is a symlink to `/etc/zabbix/web/`, so the database connection settings carry over automatically. The **SAML certificates don't**: they were in `/usr/share/zabbix/conf/certs/` and must move to the new `ui/conf/certs/`:

```bash
mkdir -p /usr/share/zabbix/ui/conf/certs
cp -a /root/pre-8.0/saml-certs/{idp.crt,sp.crt,sp.key} /usr/share/zabbix/ui/conf/certs/
ls -l /usr/share/zabbix/ui/conf/certs/
```

The files keep their original owner and permissions (`root:www-data`, `sp.key` with `640`).

> If you skip this step, SAML login fails with `Invalid array settings: sp_certs_not_found_and_required, idp_cert_or_fingerprint_not_found_and_required`.
{: .prompt-warning }

If you customized the Apache vhost to point at `/usr/share/zabbix` directly (instead of using the `zabbix-apache-conf` alias), update it to `/usr/share/zabbix/ui`. Otherwise you'll get the "Manual intervention is required" page.

---

## 7. Database schema upgrade

```bash
systemctl restart apache2
systemctl start zabbix-server
tail -f /var/log/zabbix/zabbix_server.log | grep --line-buffered -iE "upgrade|error|cannot|version"
```

Wait for `database upgrade fully completed`, then press `Ctrl+C` (that only stops `tail`).

> **Don't stop or restart the server while the schema upgrade is running.**
{: .prompt-danger }

Confirm the version:

```bash
sudo -u zabbix psql -At zabbix -c "SELECT mandatory, optional FROM dbversion;"     # 8000000|8000000
```

---

## 8. TimescaleDB: the new `history_json` hypertable

List the history tables and which ones are hypertables:

```bash
sudo -u zabbix psql -P pager=off zabbix -c "
SELECT t.table_name, (h.hypertable_name IS NOT NULL) AS hypertable
FROM information_schema.tables t
LEFT JOIN timescaledb_information.hypertables h ON h.hypertable_name=t.table_name
WHERE t.table_schema='public'
  AND (t.table_name LIKE 'history%' OR t.table_name LIKE 'trends%' OR t.table_name='auditlog')
ORDER BY 1;"
```

```
  table_name  | hypertable
--------------+------------
 auditlog     | t
 history      | t
 history_bin  | t
 history_json | f        <-- new in 8.0
 history_log  | t
 ...
```

Run the 8.0 TimescaleDB script with the server stopped. Note that the script now lives under `/usr/share/zabbix/sql-scripts/` (it used to be `/usr/share/zabbix-sql-scripts/`):

```bash
systemctl stop zabbix-server
cat /usr/share/zabbix/sql-scripts/postgresql/timescaledb/schema.sql \
  | sudo -u zabbix psql zabbix 2>&1 | grep -vE "WARNING|HINT" | tail -8
systemctl start zabbix-server
```

The script is idempotent. It skips the existing hypertables and only converts the new one:

```
NOTICE:  table "trends" is already a hypertable, skipping
NOTICE:  TimescaleDB extension is already installed; not changing configuration
NOTICE:  TimescaleDB is configured successfully
DO
```

`compression_enabled = f` on `history_json` right afterwards is normal: the housekeeper enables compression on its next run (within about an hour).

### Check that the housekeeping settings survived

In 8.0, the `config` table no longer exists (`ERROR: relation "config" does not exist`). Settings now live in **`settings`**, as name/value rows:

```bash
sudo -u zabbix psql -P pager=off zabbix -c "
SELECT name, value_int, value_str FROM settings
WHERE name IN ('db_extension','hk_history_global','hk_history','hk_trends_global','hk_trends',
               'compression_status','compress_older')
ORDER BY name;"
```

```
        name        | value_int |  value_str
--------------------+-----------+-------------
 compression_status |         1 |
 compress_older     |         0 | 7d
 db_extension       |         0 | timescaledb
 hk_history         |         0 | 30d
 hk_history_global  |         1 |
 hk_trends          |         0 | 120d
 hk_trends_global   |         1 |
```

---

## 9. Validation

### Server and caches

```bash
systemctl is-active zabbix-server zabbix-agent2 postgresql apache2
grep -ciE "out of memory|cannot connect to the database" /var/log/zabbix/zabbix_server.log   # 0
zabbix_server -R diaginfo=historycache
```

### Browser

In a **private window** (to avoid the old frontend's cached assets):

1. Log in via **SAML** and with a local user.
2. *Reports → System information*: server running, version **8.0.0**, no warnings.
3. *Monitoring → Latest data*: values arriving with current timestamps.
4. Open your dashboards and check that the widgets load.

### Expected log noise

Right after the upgrade you may see errors from existing items (preprocessing on HTTP checks, Docker JSON paths, and so on). Compare with the logs from before the upgrade: if they were already there, they're not related to it.

---

## 10. Post-upgrade checks

### Legacy macros

Search the database for macros removed in 8.0, in actions, media types, scripts and triggers:

```bash
sudo -u zabbix psql -P pager=off zabbix <<'EOF'
\set re '\\{(ACK\\.[A-Z.]+|HOSTNAME[1-9]?|IPADDRESS[1-9]?|PROFILE\\.[A-Z._]+|TRIGGER\\.COMMENT|TRIGGER\\.KEY|STATUS|USER\\.ALIAS)\\}'

SELECT 'action' AS location, a.name AS object
FROM opmessage om JOIN operations o ON o.operationid=om.operationid JOIN actions a ON a.actionid=o.actionid
WHERE coalesce(om.subject,'')||coalesce(om.message,'') ~ :'re'
UNION ALL
SELECT 'media type message', mt.name
FROM media_type_message mm JOIN media_type mt ON mt.mediatypeid=mm.mediatypeid
WHERE coalesce(mm.subject,'')||coalesce(mm.message,'') ~ :'re'
UNION ALL
SELECT 'media type param', mt.name||' / '||mp.name
FROM media_type_param mp JOIN media_type mt ON mt.mediatypeid=mp.mediatypeid
WHERE mp.value ~ :'re'
UNION ALL
SELECT 'script', s.name FROM scripts s WHERE s.command ~ :'re'
UNION ALL
SELECT 'trigger', t.description FROM triggers t
WHERE coalesce(t.description,'')||coalesce(t.comments,'')||coalesce(t.event_name,'')||coalesce(t.opdata,'') ~ :'re'
ORDER BY 1,2;
EOF
```

`(0 rows)` means there's nothing to fix.

### Outdated templates

Since 6.0, official templates carry `vendor_name` and `vendor_version`. That's enough to classify every template in use:

```bash
sudo -u zabbix psql -P pager=off zabbix -c "
SELECT t.host AS template,
       coalesce(nullif(t.vendor_name,''),'-')    AS vendor,
       coalesce(nullif(t.vendor_version,''),'-') AS version,
       count(DISTINCT h.hostid) AS hosts,
       CASE
         WHEN t.vendor_name='Zabbix' AND t.vendor_version LIKE '8.0%' THEN 'official, current'
         WHEN t.vendor_name='Zabbix'                                  THEN 'official, older'
         WHEN t.host LIKE 'Template %'                                THEN 'LEGACY'
         ELSE 'custom'
       END AS status
FROM hosts t
JOIN hosts_templates ht ON ht.templateid=t.hostid
JOIN hosts h ON h.hostid=ht.hostid AND h.status IN (0,1)
WHERE t.status=3
GROUP BY t.host, t.vendor_name, t.vendor_version
ORDER BY status, hosts DESC;"
```

| Status | Meaning | What to do |
|---|---|---|
| official, current | Imported from 8.0 | Nothing |
| official, older | Official, from 7.x or earlier | Re-import the 8.0 version |
| LEGACY | 4.x/5.x era (`Template OS Linux...`, `Template App ...`) | Replace with the current equivalent (`Linux by Zabbix agent`, `Nginx by Zabbix agent`...) |
| custom | Yours or community-made | Review case by case |

> Official templates keep the **same UUID** across versions, so importing the new one updates the old template in place. That keeps the history, but the import is refused when an item changes type on a template linked to many hosts. Test each template on a single host first, and treat large ones (like the Linux template across a whole fleet) as a separate change with its own window.
{: .prompt-warning }

### Other items

- **API tokens and automation:** check the user role in *Users → User roles → API access*.
- **Proxies:** upgrade them to 8.0.
- **Old frontend directory:** once everything works, remove what's left in `/usr/share/zabbix/conf/` (the old SAML certificates).

---

## Quick troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| apt has no Zabbix repository after installing `zabbix-release` | Answered `N` to the `zabbix.sources` prompt | Reinstall with `dpkg -i` and answer `Y` |
| `zabbix-agent2` stuck in `iF`, plugin in `iU` | Old plugin binary path in `postgresql.conf` | Use `postgresql.conf.dpkg-new` (`/usr/libexec/zabbix/...`) |
| Agent test passes as root, service fails with `permission denied` | `postgresql.conf` owned by `root:root 640` | `chown root:zabbix` |
| `Key "pgsql.custom.query" is disabled` | Custom queries off by default in 8.0 | `Plugins.PostgreSQL.CustomQueriesEnabled=true` |
| SAML: `sp_certs_not_found_and_required` | Certificates still in the old `conf/certs` | Copy them to `/usr/share/zabbix/ui/conf/certs/` |
| "Manual intervention is required" page | Vhost pointing at the old frontend path | Point it at `/usr/share/zabbix/ui` |
| `history_json` isn't a hypertable | The upgrade doesn't run the TimescaleDB script | Run `postgresql/timescaledb/schema.sql` |
| `relation "config" does not exist` | Settings moved in 8.0 | Query the `settings` table |

## Checklist

- [ ] VM snapshot/backup + local copy of `/etc/zabbix` and SAML certificates
- [ ] Requirements: PHP ≥ 8.2, PostgreSQL ≥ 15, TimescaleDB ≥ 2.20
- [ ] 8.0 repository installed (answered `Y`), candidate from `stable`
- [ ] Packages upgraded with `--force-confold`
- [ ] Agent 2 PostgreSQL plugin: new path, custom queries enabled, `root:zabbix`
- [ ] SAML certificates copied to `ui/conf/certs/`
- [ ] Schema upgraded (`8000000`)
- [ ] `history_json` converted with `timescaledb/schema.sql`
- [ ] Housekeeping settings checked in `settings`
- [ ] Browser validation: SAML, version, latest data, dashboards
- [ ] Legacy macros and outdated templates reviewed
- [ ] Proxies, API roles, old frontend directory
