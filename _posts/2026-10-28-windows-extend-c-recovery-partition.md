---
title: "Windows Server: extending C: when the recovery partition is in the way"
date: 2026-10-28 11:15:00 -0300
categories: [Windows, Storage]
tags: [windows-server, diskpart, winre, reagentc, recovery-partition, mbr, gpt]
description: "How to extend the C: volume after growing a VM's disk, when the unallocated space sits after the Windows Recovery partition: disable WinRE, delete and recreate the partition, extend C: and re-enable WinRE."
---

After growing a VM's virtual disk, the new unallocated space ends up **at the end of the disk**. On many Windows installations the **Recovery partition (WinRE)** sits right after `C:`, so Disk Management greys out *Extend Volume*: Windows can only extend a volume into space that is directly adjacent to it.

The fix is to move WinRE out of the way: disable it, delete the recovery partition, extend `C:`, then recreate the recovery partition at the end of the disk and re-enable WinRE.

> The disk numbers, partition numbers and sizes in this article are **examples**. Always confirm yours with `list partition` before deleting anything.
{: .prompt-info }

## Typical layout

Before:

| Partition | Content | Size |
|---|---|---|
| 1 | System Reserved / EFI | ~100–500 MB |
| 2 | `C:` (Windows) | 40 GB |
| 3 | Recovery (WinRE) | ~600 MB |
| — | **Unallocated** (new space) | 10 GB |

After:

| Partition | Content | Size |
|---|---|---|
| 1 | System Reserved / EFI | unchanged |
| 2 | `C:` (Windows) | ~50 GB |
| 3 | Recovery (WinRE), recreated at the end | ~750 MB |

---

## 0. Before you start

- **Take a snapshot or backup of the VM.** `delete partition override` doesn't ask twice.
- Run everything from an **elevated** prompt (*Run as administrator*).
- Find out whether the disk is **MBR or GPT**, because one step differs:

```
diskpart
list disk
exit
```

A `*` in the **Gpt** column means GPT. No `*` means MBR (Legacy BIOS).

---

## 1. Disable WinRE

Disabling WinRE moves `Winre.wim` from the recovery partition into `C:\Windows\System32\Recovery`, so nothing is lost when the partition is deleted.

```
reagentc /info
reagentc /disable
```

Confirm the image is now on `C:`:

```
dir /a C:\Windows\System32\Recovery
```

You should see `Winre.wim`.

> If `Winre.wim` is **not** there after `reagentc /disable`, stop. Deleting the partition would leave the server without a recovery environment, and you'd need installation media to rebuild it.
{: .prompt-danger }

---

## 2. Delete the recovery partition

```
diskpart
select disk 0
list partition
```

Identify the recovery partition: usually the small one (500–1000 MB) **right after** the Windows partition. Inspect it before deleting:

```
select partition 3
detail partition
```

`detail partition` should show a *Type* of `27` (MBR) or `de94bba4-06d1-4d40-a16a-bfd50179d6ac` (GPT), and no drive letter. Then:

```
delete partition override
```

`override` is required because Windows protects recovery partitions from normal deletion.

---

## 3. Extend C:

Still in diskpart, select the Windows partition:

```
select partition 2
```

You have two options:

- **Use all the space** (if you don't want WinRE back):
  ```
  extend
  ```
- **Leave room for a new recovery partition** at the end. Extend by the free space minus ~750 MB. `size` is in **MB**: for example, with 10.6 GB (≈ 10,850 MB) unallocated, leave 750 MB:
  ```
  extend size=10100
  ```

Check the result:

```
list partition
```

---

## 4. Recreate the recovery partition at the end of the disk

Still in diskpart:

```
create partition primary
format quick fs=ntfs label="Recovery"
```

Then mark it as a recovery partition. This is the step that differs by partition style.

**MBR:**

```
set id=27
```

**GPT:**

```
set id=de94bba4-06d1-4d40-a16a-bfd50179d6ac
gpt attributes=0x8000000000000001
```

The GPT attributes make the partition required by the platform and hide it from getting a drive letter.

Leave diskpart:

```
list partition
exit
```

> Microsoft recommends at least **250 MB free** inside the recovery partition for future WinRE updates. That's why ~750 MB is a safer size than the original ~500–600 MB.
{: .prompt-tip }

---

## 5. Re-enable and validate WinRE

```
reagentc /enable
reagentc /info
```

`reagentc /enable` moves `Winre.wim` back into the new recovery partition.

Expected result:

```
Windows RE status:         Enabled
Windows RE location:       \\?\GLOBALROOT\device\harddisk0\partition3\Recovery\WindowsRE
```

Also confirm in **Disk Management** (`diskmgmt.msc`) that:

- `C:` shows the new size;
- the recovery partition sits at the end of the disk, with no drive letter.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| *Extend Volume* greyed out in Disk Management | Unallocated space isn't adjacent to `C:` | This procedure |
| `Virtual Disk Service error: Cannot delete a protected partition without the force protected parameter set` | Missing `override` | `delete partition override` |
| `reagentc /enable` fails with `0x2` or "Windows RE image was not found" | `Winre.wim` isn't in `C:\Windows\System32\Recovery` | Restore it from a copy or from installation media (`sources\install.wim`), then enable again |
| `reagentc /info` shows `Enabled` but the location is on `partition2` | No valid recovery partition found, so WinRE stayed on `C:` | Check the partition's ID (`27` / GPT GUID) and that it's formatted NTFS, then `reagentc /disable` and `/enable` |
| `extend` says there isn't enough space | Wrong partition selected, or `size` larger than the free space | `list partition` / `list volume`, recompute in MB |
| New space doesn't show up at all | The guest hasn't rescanned the disk | Disk Management → *Action* → *Rescan Disks*, or `rescan` in diskpart |

## Quick reference

| Step | Command |
|---|---|
| Check WinRE | `reagentc /info` |
| Disable WinRE | `reagentc /disable` |
| Check the image | `dir /a C:\Windows\System32\Recovery` |
| Delete recovery partition | `select partition N` → `delete partition override` |
| Extend C: | `select partition N` → `extend` or `extend size=MB` |
| Recreate (MBR) | `create partition primary` → `format quick fs=ntfs label="Recovery"` → `set id=27` |
| Recreate (GPT) | ... → `set id=de94bba4-06d1-4d40-a16a-bfd50179d6ac` → `gpt attributes=0x8000000000000001` |
| Re-enable WinRE | `reagentc /enable` |
