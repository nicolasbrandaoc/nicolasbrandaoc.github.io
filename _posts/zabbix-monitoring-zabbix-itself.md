---
title: "Zabbix 7.0: monitoring Zabbix itself, PostgreSQL and TimescaleDB (templates + dashboard via API)"
date: 2026-10-25 15:00:00 -0300
categories: [Monitoring, Zabbix]
tags: [zabbix, postgresql, timescaledb, agent2, api, dashboard, templates]
description: "Updating the self-monitoring templates, collecting PostgreSQL metrics with agent 2, building a custom TimescaleDB template, and generating a complete 4-page dashboard through the API."
---

Third article in the series. With Zabbix 7.0 running on PostgreSQL + TimescaleDB, what was missing was visibility into the health of the stack itself: **Zabbix server, PostgreSQL, TimescaleDB and the VM's OS**, all in a single dashboard.

What we'll do:

1. Diagnose the templates on Zabbix's own host.
2. Import the official 7.0 templates (and understand the UUID trap).
3. Collect PostgreSQL metrics with the *PostgreSQL by Zabbix agent 2* template.
4. Build a custom template for **TimescaleDB** (hypertables, compression and jobs).
5. Generate a **4-page dashboard through the API**, with a script.

> All names, IPs, domains and passwords in this article are **examples**.
{: .prompt-info }

---

## 1. Diagnosis: which templates does the Zabbix host use?

In an environment that has gone through several versions, the *Zabbix server* host usually carries old templates. A version upgrade **doesn't update templates**.

```bash
sudo -u zabbix psql -P pager=off zabbix -c "
SELECT t.host FROM hosts_templates ht
JOIN hosts h ON h.hostid=ht.hostid
JOIN hosts t ON t.hostid=ht.templateid
WHERE h.host='Zabbix server';"
```

Result in the example environment:

```
 Template App Zabbix Server
 Template OS Linux by Zabbix agent
```

These date from the 4.x/5.x generation. Their current equivalents are *Zabbix server health* and *Linux by Zabbix agent*, which are far more complete.

> In `psql` queries, use `-P pager=off` so the output doesn't get stuck in the pager (or press `q` to exit).
{: .prompt-tip }

Check agent 2 as well:

```bash
zabbix_agent2 -t agent.version
grep -E '^(Server|ServerActive|Hostname)=' /etc/zabbix/zabbix_agent2.conf
```

---

## 2. Official 7.0 templates

### Download

The official templates live in the Zabbix repository (GitHub mirror, `release/7.0` branch):

```bash
mkdir -p /root/templates && cd /root/templates
B=https://raw.githubusercontent.com/zabbix/zabbix/release/7.0/templates
curl -fsSLo zabbix_server.yaml $B/app/zabbix_server/template_app_zabbix_server.yaml
curl -fsSLo linux.yaml         $B/os/linux/template_os_linux.yaml
curl -fsSLo postgresql_a2.yaml $B/db/postgresql_agent2/template_db_postgresql_agent2.yaml
grep -h "^      template:" *.yaml
```

### API token

Everything from here on uses the API. Create a token under *Users → API tokens → Create API token*, tied to a **Super admin** user, and copy the value (it's shown only once).

```bash
read -s -p "API token: " ZT; echo
export ZT
curl -s -H 'Content-Type: application/json-rpc' -H "Authorization: Bearer $ZT" \
  -d '{"jsonrpc":"2.0","method":"host.get","params":{"filter":{"host":["Zabbix server"]},"output":["hostid","host"]},"id":1}' \
  http://127.0.0.1/zabbix/api_jsonrpc.php; echo
```

Note the `hostid` (on a default Zabbix, the *Zabbix server* host is usually `10084`).

### Import

```python
# /root/templates/import.py
import json, os, sys, urllib.request
URL = "http://127.0.0.1/zabbix/api_jsonrpc.php"
TOKEN = os.environ["ZT"]
rules = {k: {"createMissing": True, "updateExisting": True} for k in
         ["template_groups","templates","items","triggers","graphs",
          "discoveryRules","valueMaps","templateDashboards","httptests"]}
rules["templateLinkage"] = {"createMissing": True}
for f in sys.argv[1:]:
    body = json.dumps({"jsonrpc":"2.0","method":"configuration.import",
        "params":{"format":"yaml","rules":rules,"source":open(f).read()},"id":1}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type":"application/json-rpc",
                                             "Authorization":"Bearer "+TOKEN})
    print(f, "->", urllib.request.urlopen(req).read().decode()[:300])
```

```bash
python3 import.py linux.yaml postgresql_a2.yaml zabbix_server.yaml
```

### The UUID trap

The result was:

```
linux.yaml         -> error: cannot update readonly parameter "value_type" of inherited object.
postgresql_a2.yaml -> result: true
zabbix_server.yaml -> result: true
```

The reason: **the new templates have the same UUIDs as the old ones**. Zabbix simply renamed the templates between versions. So the import **updates and renames** the old template instead of creating a new one:

- *Template App Zabbix Server* → became **Zabbix server health**, already linked to the host, with the 7.0 items;
- *Template DB PostgreSQL Agent 2* → became **PostgreSQL by Zabbix agent 2**;
- *Template OS Linux by Zabbix agent* → **failed**, because it was linked to hundreds of hosts and the update would change the item types on all of them.

Check the effect:

```bash
sudo -u zabbix psql -P pager=off zabbix -c "
SELECT t.host AS template, COUNT(ht.hostid) AS linked_hosts
FROM hosts t LEFT JOIN hosts_templates ht ON ht.templateid=t.hostid
WHERE t.status=3 AND (t.host ILIKE '%zabbix server%' OR t.host ILIKE '%linux by zabbix agent%' OR t.host ILIKE '%postgresql%')
GROUP BY t.host ORDER BY 1;"
```

> Updating the Linux template for an entire fleet is a **separate project**: it affects every host and needs a maintenance window and testing. For this dashboard, the old Linux template covers the Zabbix VM's OS.
{: .prompt-warning }

---

## 3. PostgreSQL through agent 2

### Read-only monitoring user

The `pg_monitor` role grants access to statistics without write permission:

```bash
PGMON=$(openssl rand -hex 16); export PGMON
sudo -u postgres psql -c "CREATE ROLE zbx_monitor WITH LOGIN PASSWORD '$PGMON' INHERIT; GRANT pg_monitor TO zbx_monitor;"
```

> If you run the block again, `openssl` generates **another password** in the variable, but the user already exists with the previous one: the test fails with `ping = 0`. Fix it with `ALTER ROLE zbx_monitor WITH PASSWORD '$PGMON';`.
{: .prompt-warning }

### Agent 2 PostgreSQL plugin

In 7.0, the plugin is a **separate package**:

```bash
apt install -y zabbix-agent2-plugin-postgresql
systemctl restart zabbix-agent2
zabbix_agent2 -t "pgsql.ping[\"tcp://localhost:5432\",\"zbx_monitor\",\"$PGMON\",\"postgres\"]" | sed "s/$PGMON/***/"
```

Expected: `[s|1.000000]`.

### Linking the template and creating the macros

Template macros: `{$PG.CONNSTRING.AGENT2}` (default `tcp://localhost:5432`), `{$PG.USER}`, `{$PG.PASSWORD}` and `{$PG.DATABASE}`. The password goes in as a **secret macro** (type 1), invisible in the frontend:

```python
# /root/templates/link_pg.py
import json, os, urllib.request
URL="http://127.0.0.1/zabbix/api_jsonrpc.php"; T=os.environ["ZT"]; PW=os.environ["PGMON"]
HID="10084"   # hostid of "Zabbix server"
def api(m,p):
    r=urllib.request.Request(URL,json.dumps({"jsonrpc":"2.0","method":m,"params":p,"id":1}).encode(),
       {"Content-Type":"application/json-rpc","Authorization":"Bearer "+T})
    return json.loads(urllib.request.urlopen(r).read())
tid=api("template.get",{"filter":{"host":["PostgreSQL by Zabbix agent 2"]},"output":["templateid"]})["result"][0]["templateid"]
print("link:",api("host.massadd",{"hosts":[{"hostid":HID}],"templates":[{"templateid":tid}]}))
for m,v,t in [("{$PG.USER}","zbx_monitor",0),("{$PG.PASSWORD}",PW,1),("{$PG.DATABASE}","postgres",0)]:
    print(m,"->",api("usermacro.create",{"hostid":HID,"macro":m,"value":v,"type":t}).get("result"))
```

```bash
python3 /root/templates/link_pg.py
```

Within 1 to 2 minutes the template discovers the databases (`DB [postgres]`, `DB [zabbix]`) and starts collecting connections, transactions, cache hit, locks, checkpoints, bgwriter, autovacuum, query times and database sizes.

---

## 4. Custom TimescaleDB template

There's no official template with TimescaleDB metrics. The way to get them is the **custom queries** feature of the agent 2 PostgreSQL plugin.

### Permissions

`pg_monitor` is enough to read `timescaledb_information` and the size functions. Test it:

```bash
PGPASSWORD="$PGMON" psql -h localhost -U zbx_monitor zabbix -P pager=off -c "
SELECT h.hypertable_name,
       pg_size_pretty(hypertable_size(format('%I.%I',h.hypertable_schema,h.hypertable_name)::regclass)) AS size,
       (SELECT count(*) FROM timescaledb_information.chunks c WHERE c.hypertable_name=h.hypertable_name) AS chunks
FROM timescaledb_information.hypertables h ORDER BY 1;"
```

### The queries

The plugin parameter is `Plugins.PostgreSQL.CustomQueriesPath`. Each `.sql` file becomes a query you can call by name:

```bash
Q=/etc/zabbix/zabbix_agent2.d/pgsql_queries; mkdir -p $Q

cat > $Q/tsdb_hypertables.sql <<'EOF'
SELECT h.hypertable_name AS name,
       hypertable_size(format('%I.%I',h.hypertable_schema,h.hypertable_name)::regclass) AS total_bytes,
       (SELECT count(*) FROM timescaledb_information.chunks c
         WHERE c.hypertable_schema=h.hypertable_schema AND c.hypertable_name=h.hypertable_name) AS chunks,
       (SELECT count(*) FROM timescaledb_information.chunks c
         WHERE c.hypertable_schema=h.hypertable_schema AND c.hypertable_name=h.hypertable_name AND c.is_compressed) AS compressed_chunks,
       COALESCE(s.before_compression_total_bytes,0) AS before_bytes,
       COALESCE(s.after_compression_total_bytes,0) AS after_bytes
FROM timescaledb_information.hypertables h
LEFT JOIN LATERAL hypertable_compression_stats(format('%I.%I',h.hypertable_schema,h.hypertable_name)::regclass) s ON true
ORDER BY 1;
EOF

cat > $Q/tsdb_jobs.sql <<'EOF'
SELECT count(*) AS total_jobs,
       count(*) FILTER (WHERE last_run_status='Failed') AS failed_jobs,
       COALESCE(sum(total_failures),0) AS total_failures
FROM timescaledb_information.job_stats;
EOF

cat > $Q/tsdb_version.sql <<'EOF'
SELECT extversion FROM pg_extension WHERE extname='timescaledb';
EOF

chown -R root:zabbix $Q; chmod 750 $Q; chmod 640 $Q/*.sql
echo "Plugins.PostgreSQL.CustomQueriesPath=$Q" >> /etc/zabbix/zabbix_agent2.d/plugins.d/postgresql.conf
systemctl restart zabbix-agent2
```

Test:

```bash
for q in tsdb_version tsdb_jobs tsdb_hypertables; do
  zabbix_agent2 -t "pgsql.custom.query[\"tcp://localhost:5432\",\"zbx_monitor\",\"$PGMON\",\"zabbix\",\"$q\"]" \
    | sed "s/$PGMON/***/" | cut -c1-300
done
```

Each query returns JSON (a list of objects, one per row), for example:

```
[{"extversion":"2.22.1"}]
[{"failed_jobs":0,"total_failures":"4","total_jobs":10}]
[{"after_bytes":0,"before_bytes":0,"chunks":1,"compressed_chunks":0,"name":"history","total_bytes":32456704}, ...]
```

### The template, built through the API

The **"TimescaleDB by Zabbix agent 2"** template is generated as JSON and imported with `configuration.import`. Structure:

- **3 "raw" items** (passive agent) that run the queries and store the JSON;
- **dependent items** with JSONPath: version, total jobs, failed jobs (with a trigger) and accumulated failures;
- a **dependent discovery rule** that creates, for each hypertable, items for total size, chunks, compressed chunks, and bytes before and after compression.

Dependent items let **a single database query** feed dozens of metrics.

{% raw %}
```python
# /root/templates/tsdb_template.py
import json, os, uuid, urllib.request
URL="http://127.0.0.1/zabbix/api_jsonrpc.php"; T=os.environ["ZT"]; HID="10084"
def api(m,p):
    r=urllib.request.Request(URL,json.dumps({"jsonrpc":"2.0","method":m,"params":p,"id":1}).encode(),
       {"Content-Type":"application/json-rpc","Authorization":"Bearer "+T})
    return json.loads(urllib.request.urlopen(r).read())
U=lambda: uuid.uuid4().hex
TPL="TimescaleDB by Zabbix agent 2"
CS='"{$PG.CONNSTRING.AGENT2}","{$PG.USER}","{$PG.PASSWORD}","zabbix"'
tag=[{"tag":"component","value":"timescaledb"}]
MH=f'pgsql.custom.query[{CS},"tsdb_hypertables"]'
MJ=f'pgsql.custom.query[{CS},"tsdb_jobs"]'
MV=f'pgsql.custom.query[{CS},"tsdb_version"]'

def raw(name,key,delay):
    return {"uuid":U(),"name":name,"type":"ZABBIX_PASSIVE","key":key,"delay":delay,
            "history":"1h","trends":"0","value_type":"TEXT","tags":tag}
def dep(name,key,master,path,vt="UNSIGNED",trig=None):
    d={"uuid":U(),"name":name,"type":"DEPENDENT","key":key,"delay":"0","value_type":vt,
       "history":"30d","preprocessing":[{"type":"JSONPATH","parameters":[path]}],
       "master_item":{"key":master},"tags":tag}
    if vt=="CHAR": d["trends"]="0"
    if trig: d["triggers"]=trig
    return d
items=[
 raw("TimescaleDB: hypertables (raw)",MH,"5m"),
 raw("TimescaleDB: jobs (raw)",MJ,"5m"),
 raw("TimescaleDB: version (raw)",MV,"1h"),
 dep("TimescaleDB: version","tsdb.version",MV,"$[0].extversion","CHAR"),
 dep("TimescaleDB: background jobs total","tsdb.jobs.total",MJ,"$[0].total_jobs"),
 dep("TimescaleDB: background jobs failed (last run)","tsdb.jobs.failed",MJ,"$[0].failed_jobs",
     trig=[{"uuid":U(),"expression":f"last(/{TPL}/tsdb.jobs.failed)>0",
            "name":"TimescaleDB: background job failed on last run","priority":"WARNING"}]),
 dep("TimescaleDB: background jobs failures (total)","tsdb.jobs.failures",MJ,"$[0].total_failures"),
]
def proto(name,key,field,units=""):
    return {"uuid":U(),"name":f"Hypertable [{{#NAME}}]: {name}","type":"DEPENDENT",
            "key":f"{key}[{{#NAME}}]","delay":"0","value_type":"UNSIGNED","units":units,"history":"30d",
            "preprocessing":[{"type":"JSONPATH","parameters":[f"$[?(@.name=='{{#NAME}}')].{field}.first()"]}],
            "master_item":{"key":MH},"tags":tag+[{"tag":"hypertable","value":"{#NAME}"}]}
lld={"uuid":U(),"name":"Hypertables discovery","type":"DEPENDENT","key":"tsdb.hypertables.discovery",
     "delay":"0","master_item":{"key":MH},"lld_macro_paths":[{"lld_macro":"{#NAME}","path":"$.name"}],
     "item_prototypes":[proto("total size","tsdb.ht.size","total_bytes","B"),
                        proto("chunks","tsdb.ht.chunks","chunks"),
                        proto("compressed chunks","tsdb.ht.chunks.compressed","compressed_chunks"),
                        proto("size before compression","tsdb.ht.before","before_bytes","B"),
                        proto("size after compression","tsdb.ht.after","after_bytes","B")]}
exp={"zabbix_export":{"version":"7.0",
  "template_groups":[{"uuid":"748ad4d098d447d492bb935c907f652f","name":"Templates/Databases"}],
  "templates":[{"uuid":U(),"template":TPL,"name":TPL,
     "description":"Custom: TimescaleDB hypertables, compression and jobs (agent 2 custom queries)",
     "groups":[{"name":"Templates/Databases"}],"items":items,"discovery_rules":[lld]}]}}
rules={k:{"createMissing":True,"updateExisting":True} for k in
       ["template_groups","templates","items","triggers","discoveryRules"]}
print("import:",api("configuration.import",{"format":"json","rules":rules,"source":json.dumps(exp)}))
tid=api("template.get",{"filter":{"host":[TPL]},"output":["templateid"]})["result"][0]["templateid"]
print("link:",api("host.massadd",{"hosts":[{"hostid":HID}],"templates":[{"templateid":tid}]}))
```
{% endraw %}

```bash
python3 /root/templates/tsdb_template.py
```

Notes:

- The `{$PG.*}` macros come from the PostgreSQL template and the host, so the TimescaleDB template inherits them with no extra configuration.
- In Zabbix 7.0, a list of JSON objects is already a valid LLD format: just map `{#NAME}` → `$.name` in `lld_macro_paths`.
- Generating the export as JSON inside Python avoids depending on PyYAML and keeps the UUIDs unique automatically.

---

## 5. Checking the collection

Wait 3 to 5 minutes and look at the state of the host's items per template:

```bash
sudo -u zabbix psql -P pager=off zabbix -c "
SELECT COALESCE(t.host,'(discovered/LLD)') AS source, COUNT(*) AS items,
       SUM(CASE WHEN ir.state=0 THEN 1 ELSE 0 END) AS ok,
       SUM(CASE WHEN ir.state=1 THEN 1 ELSE 0 END) AS unsupported
FROM items i
LEFT JOIN item_rtdata ir ON ir.itemid=i.itemid
LEFT JOIN items ti ON ti.itemid=i.templateid
LEFT JOIN hosts t ON t.hostid=ti.hostid
WHERE i.hostid=10084 AND i.flags IN (0,4)
GROUP BY 1 ORDER BY 1;"
```

Result in the example environment:

```
              source               | items | ok  | unsupported
-----------------------------------+-------+-----+-------------
 (discovered/LLD)                  |   142 | 126 |          16
 PostgreSQL by Zabbix agent 2      |    65 |  64 |           1
 Template OS Linux by Zabbix agent |    42 |  42 |           0
 TimescaleDB by Zabbix agent 2     |     7 |   7 |           0
 Zabbix server health              |    79 |  67 |          12
```

All the unsupported items were expected:

| Item | Reason |
|---|---|
| Interfaces with old names (`eth0`, `eth1`) | Discovered on the old server; the new VM uses `enX0`/`enX1`. They go away after the "lost resources period" |
| Utilization of VMware, Java, IPMI, report writer, connectors, SNMP trapper | Processes that aren't enabled on this server |

To see the errors:

```bash
sudo -u zabbix psql -P pager=off zabbix -c "
SELECT i.name, LEFT(ir.error,90) AS error
FROM items i JOIN item_rtdata ir ON ir.itemid=i.itemid
WHERE i.hostid=10084 AND ir.state=1 ORDER BY 1;"
```

Generate the full list of item names so you can design the dashboard without guessing:

```bash
sudo -u zabbix psql -At zabbix -c "
SELECT COALESCE(t.host,'LLD') || ' | ' || i.name || ' | ' || i.key_
FROM items i
LEFT JOIN items ti ON ti.itemid=i.templateid
LEFT JOIN hosts t ON t.hostid=ti.hostid
WHERE i.hostid=10084 AND i.flags IN (0,4) AND i.status=0
ORDER BY 1;" > /root/templates/host_items.txt
```

---

## 6. A 4-page dashboard through the API

Building dozens of widgets by hand is slow and hard to reproduce. Through the API, the dashboard becomes versionable code.

### Layout

| Page | Content |
|---|---|
| **Zabbix Server** | Version, NVPS, queues; gauges for the 6 caches; NVPS by type, queues, data collector and internal process utilization, caches, value cache hits × misses, values synced/s, host problems |
| **PostgreSQL** | Database size, connections (total and %), cache hit, oldest xid age, autovacuum; connections by state, commits × rollbacks, tuples, locks, checkpoints, bgwriter, blocks cache × disk, max query time, database sizes, slow queries and deadlocks |
| **TimescaleDB** | Version, jobs, failures; size per hypertable, chunks × compressed, before × after compression, jobs, database size |
| **System (VM)** | Uptime, CPUs, RAM, load, processes; gauges for CPU, RAM, disk, swap and disk utilization; CPU by type, load, memory, disk I/O and latency, network, filesystem, context switches |

### Notes on widgets in Zabbix 7.0

- The dashboard grid has **72 columns** (it was 24 in older versions).
- **Graph (`svggraph`)**: works with **name patterns** (`ds.N.hosts.0`, `ds.N.items.0`, `ds.N.dataset_type = 1`) and accepts wildcards such as `Utilization of * data collector processes, in %`. No `itemid` needed.
- **Item value (`item`)** and **gauge (`gauge`)**: need the `itemid` in the `itemid.0` field (type 4). The script resolves the IDs by name.
- **Problems (`problems`)**: host filter in the `hostids.0` field (type 3).

### Script

```python
# /root/templates/dashboard.py
import json, os, urllib.request
URL="http://127.0.0.1/zabbix/api_jsonrpc.php"; T=os.environ["ZT"]; HOST="Zabbix server"; HID="10084"
def api(m,p):
    r=urllib.request.Request(URL,json.dumps({"jsonrpc":"2.0","method":m,"params":p,"id":1}).encode(),
       {"Content-Type":"application/json-rpc","Authorization":"Bearer "+T})
    return json.loads(urllib.request.urlopen(r).read())
items={i["name"]:i["itemid"] for i in api("item.get",{"hostids":HID,"output":["itemid","name"]})["result"]}
C=["1A7C11","F63100","2774A4","A54F10","FC6EA3","6C59DC","AC8C14","611F27","F230E0","5CCD18","BB2A02","00A3E0"]
F=lambda t,n,v:{"type":t,"name":n,"value":v}

def item(name,x,y,w=12,h=3,title=None):
    if name not in items: print("  [skipped]",name); return None
    return {"type":"item","name":title or name,"x":x,"y":y,"width":w,"height":h,
            "fields":[F(4,"itemid.0",items[name])]}
def gauge(name,x,y,w=12,h=5,title=None,mx="100"):
    if name not in items: print("  [skipped]",name); return None
    return {"type":"gauge","name":title or name,"x":x,"y":y,"width":w,"height":h,
            "fields":[F(4,"itemid.0",items[name]),F(1,"min","0"),F(1,"max",mx)]}
def svg(title,x,y,w,h,patterns):
    f=[F(0,"legend_lines",4)]
    for i,p in enumerate(patterns):
        f+=[F(0,f"ds.{i}.dataset_type",1),F(1,f"ds.{i}.hosts.0",HOST),F(1,f"ds.{i}.items.0",p),
            F(1,f"ds.{i}.color",C[i%len(C)]),F(0,f"ds.{i}.width",2),F(0,f"ds.{i}.fill",1)]
    return {"type":"svggraph","name":title,"x":x,"y":y,"width":w,"height":h,"fields":f}
def problems(x,y,w,h):
    return {"type":"problems","name":"Zabbix server host problems","x":x,"y":y,"width":w,"height":h,
            "fields":[F(3,"hostids.0",HID)]}
def page(name,ws): return {"name":name,"widgets":[w for w in ws if w]}

p1=page("Zabbix Server",[
 item("Version",0,0),item("Number of processed values per second",12,0,title="NVPS"),
 item("Queue",24,0,title="Queue (delayed items)"),item("Queue over 10 minutes",36,0,title="Queue > 10 min"),
 item("Preprocessing queue",48,0),item("LLD queue",60,0),
 gauge("Configuration cache, % used",0,3),gauge("History write cache, % used",12,3),
 gauge("History index cache, % used",24,3),gauge("Trend write cache, % used",36,3),
 gauge("Value cache, % used",48,3),gauge("Trend function cache, % of misses",60,3),
 svg("NVPS by value type",0,8,36,6,["Number of processed values per second",
     "Number of processed numeric (unsigned) values per second","Number of processed numeric (float) values per second",
     "Number of processed character values per second","Number of processed text values per second",
     "Number of processed log values per second","Number of processed not supported values per second"]),
 svg("Queues",36,8,36,6,["Queue","Queue over 10 minutes","Preprocessing queue","LLD queue","Discovery queue"]),
 svg("Data collector utilization (%)",0,14,36,7,["Utilization of * data collector processes, in %"]),
 svg("Internal process utilization (%)",36,14,36,7,["Utilization of * internal processes, in %"]),
 svg("Caches (% used)",0,21,36,6,["*cache, % used"]),
 svg("Value cache: hits x misses",36,21,36,6,["Value cache hits","Value cache misses"]),
 svg("Values synced to the database/s",0,27,36,5,["Number of values synchronized with the database per second"]),
 problems(36,27,36,5),
])
p2=page("PostgreSQL",[
 item("DB [zabbix]: Database size",0,0,title="zabbix DB size"),item("Connections sum: Total",12,0,title="Connections"),
 item("Connections sum: Total, %",24,0,title="Connections (% of max)"),item("Cache hit ratio, %",36,0,title="Cache hit %"),
 item("Age of oldest xid",48,0),item("Count of autovacuum workers",60,0,title="Autovacuum workers"),
 svg("Connections by state",0,3,36,6,["Connections sum: Active","Connections sum: Idle",
     "Connections sum: Idle in transaction","Connections sum: Waiting","Connections sum: Idle in transaction (aborted)"]),
 svg("Transactions: commits x rollbacks (zabbix)",36,3,36,6,["DB [zabbix]: Commits per second","DB [zabbix]: Rollbacks per second"]),
 svg("Tuples/s (zabbix)",0,9,36,6,["DB [zabbix]: Tuples inserted per second","DB [zabbix]: Tuples updated per second",
     "DB [zabbix]: Tuples deleted per second","DB [zabbix]: Tuples fetched per second","DB [zabbix]: Tuples returned per second"]),
 svg("Locks (zabbix)",36,9,36,6,["DB [zabbix]: Num of * locks","DB [zabbix]: Num of locks total"]),
 svg("Checkpoints",0,15,36,6,["Checkpoint: *"]),
 svg("Background writer",36,15,36,6,["Bgwriter: *"]),
 svg("Blocks: cache x disk (zabbix)",0,21,36,6,["DB [zabbix]: Blocks hit per second","DB [zabbix]: Disk blocks read per second"]),
 svg("Max query time (zabbix)",36,21,36,6,["DB [zabbix]: Queries max query time",
     "DB [zabbix]: Queries max transaction time","DB [zabbix]: Queries max maintenance time"]),
 svg("Database sizes",0,27,36,6,["DB [*]: Database size"]),
 svg("Slow queries and deadlocks (zabbix)",36,27,36,6,["DB [zabbix]: Queries slow * count",
     "DB [zabbix]: Detected deadlocks per second","DB [zabbix]: Temp_files created per second"]),
])
p3=page("TimescaleDB",[
 item("TimescaleDB: version",0,0),item("TimescaleDB: background jobs total",12,0,title="Jobs"),
 item("TimescaleDB: background jobs failed (last run)",24,0,title="Failed jobs"),
 item("TimescaleDB: background jobs failures (total)",36,0,title="Accumulated failures"),
 item("Hypertable [history_uint]: total size",48,0,title="history_uint"),
 item("Hypertable [history]: total size",60,0,title="history"),
 svg("Size per hypertable",0,3,36,7,["Hypertable [*]: total size"]),
 svg("Chunks x compressed chunks",36,3,36,7,["Hypertable [*]: chunks","Hypertable [*]: compressed chunks"]),
 svg("Compression: before x after",0,10,72,7,["Hypertable [*]: size before compression","Hypertable [*]: size after compression"]),
 svg("TimescaleDB jobs",0,17,36,5,["TimescaleDB: background jobs*"]),
 svg("zabbix database size",36,17,36,5,["DB [zabbix]: Database size"]),
])
p4=page("System (VM)",[
 item("System uptime",0,0,title="Uptime"),item("Number of CPUs",12,0,title="CPUs"),
 item("Total memory",24,0,title="Total RAM"),item("Load average (1m avg)",36,0,title="Load 1m"),
 item("Number of processes",48,0,title="Processes"),item("Zabbix agent ping",60,0,title="Agent ping"),
 gauge("CPU utilization",0,3,title="CPU %"),gauge("Memory utilization",12,3,title="RAM %"),
 gauge("/: Space utilization",24,3,title="Disk / %"),gauge("Free swap space in %",36,3,title="Free swap %"),
 gauge("Available memory in %",48,3,title="Available RAM %"),gauge("xvda: Disk utilization",60,3,title="xvda util %"),
 svg("CPU by time type",0,8,36,6,["CPU * time"]),
 svg("Load average",36,8,36,6,["Load average*"]),
 svg("Memory",0,14,36,6,["Available memory","Total memory"]),
 svg("Disk xvda: read x write (ops/s)",36,14,36,6,["xvda: Disk read rate","xvda: Disk write rate"]),
 svg("Disk xvda: latency (ms)",0,20,36,6,["xvda: Disk read request avg waiting time (r_await)",
     "xvda: Disk write request avg waiting time (w_await)"]),
 svg("Network enX0 / enX1",36,20,36,6,["Interface enX*: Bits *"]),
 svg("Filesystem /",0,26,36,6,["/: Used space","/: Total space"]),
 svg("Context switches and interrupts",36,26,36,6,["Context switches per second","Interrupts per second"]),
])
print(api("dashboard.create",{"name":"Zabbix + PostgreSQL/TimescaleDB - Health",
      "display_period":60,"auto_start":0,"pages":[p1,p2,p3,p4]}))
```

```bash
python3 /root/templates/dashboard.py
```

Expected: `{'jsonrpc': '2.0', 'result': {'dashboardids': ['...']}}`.

Adapt it to your environment:

- **Disk and interface names** (`xvda`, `enX*`): change them to your VM's (`vda`, `sda`, `ens*`...).
- **`HID`**: the `hostid` of your *Zabbix server* host.
- Items that aren't found are **skipped** and listed in the terminal: the rest of the dashboard is created normally.

The dashboard starts out **private** to the token's owner. Share it under *Dashboards → (dashboard) → Edit → Sharing*.

---

## Next steps

- **Triggers** for TimescaleDB metrics beyond jobs (for example, a hypertable growing faster than expected).
- **History retention**: with TimescaleDB, keeping 14 or 30 days of history is cheap, because the days past the 7th are compressed.
- **Update the fleet's Linux template** to *Linux by Zabbix agent*, as a separate project with a window and testing.
- Revoke the **API token**, or give it an expiry date, once it's no longer needed.

## File summary

| Path | Contents |
|---|---|
| `/etc/zabbix/zabbix_agent2.d/pgsql_queries/*.sql` | Custom TimescaleDB queries |
| `/etc/zabbix/zabbix_agent2.d/plugins.d/postgresql.conf` | `Plugins.PostgreSQL.CustomQueriesPath` |
| `/root/templates/import.py` | YAML template import via the API |
| `/root/templates/link_pg.py` | PostgreSQL template link + macros |
| `/root/templates/tsdb_template.py` | Custom TimescaleDB template |
| `/root/templates/dashboard.py` | 4-page dashboard |
