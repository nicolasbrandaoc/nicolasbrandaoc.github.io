---
title: "Active Directory trust between domains: DNS and authentication"
date: 2026-10-28 06:40:00 -0300
categories: [Windows, Active Directory]
tags: [active-directory, trust, dns, kerberos, conditional-forwarder, netdom, windows-server]
description: "How to set up DNS resolution between two Active Directory domains with conditional forwarders, create a forest or external trust, validate it, and secure it."
---

A guide to configuring DNS resolution between two Active Directory domains and creating the trust relationship that lets users from one domain authenticate in the other.

> All names and IPs in this article are **examples**. Replace them with your own.
{: .prompt-info }

## Example scenario

| Item | Domain A | Domain B |
|---|---|---|
| DNS name | `alfacorp.local` | `betacorp.local` |
| NetBIOS name | `ALFACORP` | `BETACORP` |
| DC / DNS server | `DC-ALFA` — `192.0.2.10` | `DC-BETA` — `198.51.100.10` |

---

## 1. Prerequisites

- Network connectivity between the DCs of both domains (VPN or routing between the networks).
- Firewall ports open **between the DCs, in both directions**:

| Port | Protocol | Service |
|---|---|---|
| 53 | TCP/UDP | DNS |
| 88 | TCP/UDP | Kerberos |
| 135 | TCP | RPC Endpoint Mapper |
| 137–138 | UDP | NetBIOS (external/legacy trusts) |
| 139 | TCP | NetBIOS Session |
| 389 | TCP/UDP | LDAP |
| 445 | TCP | SMB |
| 464 | TCP/UDP | Kerberos password change |
| 636 | TCP | LDAPS (if used) |
| 3268–3269 | TCP | Global Catalog |
| 49152–65535 | TCP | Dynamic RPC |

- Time synchronized between the DCs: Kerberos tolerates at most **5 minutes** of skew.
- **Domain Admins** (or **Enterprise Admins**, for a forest trust) credentials in each domain.

Quick connectivity test, from one DC to the other:

```powershell
Test-NetConnection 198.51.100.10 -Port 445
Test-NetConnection 198.51.100.10 -Port 88
Test-NetConnection 198.51.100.10 -Port 389
Test-NetConnection 198.51.100.10 -Port 135
```

Check the time on both sides:

```powershell
w32tm /query /status
w32tm /stripchart /computer:198.51.100.10 /samples:3 /dataonly
```

---

## 2. DNS: conditional forwarders

The trust only works if each domain can **resolve the other domain's DNS**. The recommended way is a conditional forwarder: "every query for `betacorp.local` goes to the DNS server `198.51.100.10`".

### 2.1. With the GUI

On a DC of **each** domain:

1. Open **DNS Manager** (`dnsmgmt.msc`).
2. Right-click **Conditional Forwarders** → **New Conditional Forwarder**.
3. In *DNS Domain*, type the name of the **other** domain (e.g. `betacorp.local`).
4. In *IP addresses of the master servers*, add the IP of the other domain's DNS/DC (e.g. `198.51.100.10`).
5. Check **"Store this conditional forwarder in Active Directory, and replicate it as follows"** and choose *All DNS servers in this forest* (or *in this domain*), so every DC inherits it.
6. Repeat on the other domain, pointing back.

### 2.2. With PowerShell

On a DC of domain A:

```powershell
Add-DnsServerConditionalForwarderZone -Name "betacorp.local" `
  -MasterServers 198.51.100.10 `
  -ReplicationScope "Forest"
```

On a DC of domain B:

```powershell
Add-DnsServerConditionalForwarderZone -Name "alfacorp.local" `
  -MasterServers 192.0.2.10 `
  -ReplicationScope "Forest"
```

> If the other domain has more than one DC/DNS server, list all of them in `-MasterServers` (comma-separated). A single master is a single point of failure for the trust.
{: .prompt-tip }

### 2.3. Validating DNS (required before the trust)

On each side, resolve the other domain and its SRV records:

```powershell
# From domain A, testing resolution of domain B:
nslookup betacorp.local
nslookup -type=SRV _ldap._tcp.dc._msdcs.betacorp.local
nslookup -type=SRV _kerberos._tcp.betacorp.local
```

All of them must return the other domain's DC.

> **Don't continue if the SRV records don't resolve.** It's the number one cause of trust creation failures.
{: .prompt-danger }

---

## 3. Choosing the trust type

| Type | When to use | Transitive? |
|---|---|---|
| **Forest trust** | Between two full AD forests (created between the **forest root domains**). The recommended option between modern forests | Yes |
| **External trust** | Trust with a single domain of another forest, or with a domain that isn't a forest root | No |
| **Shortcut trust** | Shortcut between two domains of the same forest (Kerberos optimization) | Yes |

A forest trust requires a forest functional level of **Windows Server 2003 or higher** on both sides.

**Direction** — always think "who trusts whom":

- **Two-way**: users from both domains can authenticate in the other. The most common choice.
- **One-way outgoing**: *my* domain trusts the other one → users *from the other* domain can access resources *in mine*.
- **One-way incoming**: the opposite.

Rule of thumb: ***the domain that holds the RESOURCES trusts the domain that holds the ACCOUNTS.***

---

## 4. Creating the trust

### 4.1. With the GUI (recommended the first time)

On a DC of domain A:

1. Open **Active Directory Domains and Trusts** (`domain.msc`).
2. Right-click the domain → **Properties** → **Trusts** tab → **New Trust**.
3. In the wizard:
   - **Trust name**: the FQDN of the other domain (`betacorp.local`).
   - **Trust type**: *Forest trust* (offered when both sides are forest roots with a suitable functional level) or *External trust*.
   - **Direction**: *Two-way* (or one-way, as needed).
   - **Sides of trust**: choose **"Both this domain and the specified domain"**. The wizard creates both sides at once using admin credentials from the other domain. Otherwise you have to run the wizard on each side with an agreed trust password.
   - **Authentication level**:
     - *Domain-wide / Forest-wide authentication*: any authenticated user from the other domain can reach resources (still subject to NTFS/share permissions).
     - *Selective authentication*: only users explicitly granted **"Allowed to Authenticate"** on the computer object can access it. Safer; use it if the other domain isn't fully trusted.
4. At the end, **confirm both the outgoing and incoming trusts** when the wizard asks.

### 4.2. With the command line (netdom)

```powershell
# Two-way trust, created from domain A:
netdom trust alfacorp.local /Domain:betacorp.local /Add /TwoWay `
  /UserD:BETACORP\Administrator /PasswordD:* `
  /UserO:ALFACORP\Administrator /PasswordO:*
```

For a forest trust, add `/ForestTRANsitive:yes` after creating it:

```powershell
netdom trust alfacorp.local /Domain:betacorp.local /ForestTRANsitive:yes `
  /UserD:BETACORP\Administrator /PasswordD:* `
  /UserO:ALFACORP\Administrator /PasswordO:*
```

The `*` makes netdom prompt for the passwords, so they don't end up in the console history.

---

## 5. Validating the trust

```powershell
# Check the trust's secure channel:
netdom trust alfacorp.local /Domain:betacorp.local /Verify `
  /UserD:BETACORP\Administrator /PasswordD:* `
  /UserO:ALFACORP\Administrator /PasswordO:*

# List existing trusts:
netdom query trust
nltest /domain_trusts /all_trusts /v

# Check the secure channel to the other domain:
nltest /sc_verify:betacorp.local

# Test real authentication (from domain A, with a domain B account):
runas /user:BETACORP\testuser cmd
```

In the GUI: trust **Properties** → **Validate**. It should report the trust as validated in both directions.

Final functional test: on a server in domain A, add a group from domain B to a shared folder's ACL and access it with a domain B user.

---

## 6. Trust security (don't skip this)

- **SID filtering (quarantine)** is enabled by default on new trusts. It stops SIDs injected in the other domain (e.g. through SID history) from escalating privileges in yours.
  - External trusts — check with:
    ```powershell
    netdom trust alfacorp.local /Domain:betacorp.local /Quarantine
    ```
  - Forest trusts — SID history is blocked unless explicitly enabled; check with:
    ```powershell
    netdom trust alfacorp.local /Domain:betacorp.local /EnableSIDHistory
    ```
  Only relax it during a migration that relies on SID history, and turn it back on afterwards.
- **Selective authentication**: prefer it when the other domain belongs to a third party or partner. After enabling it, grant "Allowed to Authenticate" on the computers that should be reachable.
- **Don't put groups from the other domain in Domain Admins/Administrators** unless there's a real need.
- **Monitor cross-domain logons** in your SIEM: logons through the trust generate event **4624**, whose `TargetDomainName` field carries the source domain. Events **4768/4769** (Kerberos TGT and service tickets) also show cross-domain traffic. In Wazuh, for example, you can filter `data.win.eventdata.targetDomainName` to build a rule or dashboard of who crosses the trust.

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| "The specified domain either does not exist or could not be contacted" when creating the trust | DNS: the other domain's SRV records don't resolve | Redo/validate section 2.3 |
| Trust is created but doesn't validate | Firewall blocking 445/135/dynamic RPC | Open the ports from section 1 |
| Kerberos error / `KRB_AP_ERR_SKEW` | Clock skew > 5 min | Sync NTP (`w32tm /resync`) |
| Forest trust option not offered | One side isn't a forest root, or functional level too low | Use an external trust or raise the forest functional level |
| User from the other domain gets "access denied" despite permissions | Selective authentication without "Allowed to Authenticate" | Grant the permission on the computer object, or switch to domain-wide |
| Trust breaks after a while | Trust password out of sync | `netdom trust ... /Reset` (with credentials on both sides), then `/Verify` |
| Resolution works on one DC but not another | Forwarder not replicated | Recreate the forwarder with `-ReplicationScope "Forest"` |

Useful logs: Event Viewer → *System* (sources NETLOGON, LsaSrv) and *Security* (4624/4625/4768/4769) on the DCs of both domains.

## Checklist

- [ ] Routing between the DCs and firewall ports open in both directions
- [ ] Time synchronized (skew under 5 minutes)
- [ ] Conditional forwarders on both sides, replicated to all DNS servers
- [ ] SRV records of the other domain resolving on both sides
- [ ] Trust type and direction chosen ("resources trust accounts")
- [ ] Trust created and confirmed on both sides
- [ ] Trust validated (`/Verify`, `nltest`, GUI)
- [ ] Functional test with a real user from the other domain
- [ ] SID filtering on, selective authentication where appropriate
- [ ] Cross-domain logons monitored
