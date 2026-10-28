---
title: "Ubuntu: resetting a user password (and stopping cloud-init from locking the account)"
date: 2026-10-28 06:30:00 -0300
categories: [Linux, Ubuntu]
tags: [ubuntu, passwd, grub, recovery, cloud-init, password]
description: "How to check, unlock and reset a user password on Ubuntu, including from the GRUB recovery shell when you can't log in, and how to keep cloud-init from locking the account on every boot."
---

A quick reference for regaining access to an Ubuntu machine: checking an account's password status, unlocking it, setting a new password, and doing all of that from a recovery shell when no login works.

It also covers a common cause of "the password stopped working after a reboot": **cloud-init** locking the account on boot.

> The examples use the `ubuntu` user. Replace it with the account you need.
{: .prompt-info }

---

## 1. Checking the account status

```bash
sudo passwd -S ubuntu
```

The second field is what matters:

| Field | Meaning | What to do |
|---|---|---|
| `P` | Password set and active | Nothing, the account is fine |
| `L` | Account **locked** | Unlock it with `sudo passwd -u ubuntu` |
| `NP` | No password set | Set one with `sudo passwd ubuntu` |

Example output:

```
ubuntu P 2026-10-28 0 99999 7 -1
```

---

## 2. You can still log in: change or unlock the password

Set a new password:

```bash
sudo passwd ubuntu
```

Unlock a locked account (keeps the existing password):

```bash
sudo passwd -u ubuntu
```

Nothing is shown on screen while you type the password. That's normal.

---

## 3. Why the password stops working after a reboot: cloud-init

On cloud images, **cloud-init** runs on every boot and manages users and passwords. If it can't reach its data source (the metadata or password service of the platform the image was built for), it falls back to `DataSourceNone`. In that mode the default configuration can **lock the default user** (`passwd -l ubuntu`) and inject no valid password.

The symptom: the password works, the machine reboots, and then **no password works anymore**.

Confirm it in the cloud-init log:

```bash
grep -iE "DataSourceNone|passwd|lock" /var/log/cloud-init.log | tail -20
```

### Fix: disable cloud-init

If the machine doesn't depend on cloud-init (users, network and hostname are already configured on disk), disable it. The password currently on disk is then left alone:

```bash
sudo passwd -S ubuntu                     # make sure it shows P, not L
sudo passwd -u ubuntu                     # only if it shows L
sudo touch /etc/cloud/cloud-init.disabled
```

> Do this **while you still have access**: for example, before moving or cloning the machine to an environment where its data source doesn't exist. It's much easier than recovering afterwards.
{: .prompt-tip }

> Don't re-enable cloud-init later. On the next boot it locks the account again and you're back to the same problem.
{: .prompt-warning }

---

## 4. You can't log in: reset through the GRUB recovery shell

Use this when no password works. You need access to the machine's console (physical, IPMI/iDRAC, or the VM console in your virtualization platform), because the network may not be up at this stage.

> If the machine is a VM with a disk operation in progress (migration, copy, snapshot consolidation), let it finish before rebooting.
{: .prompt-danger }

### Step 1: open GRUB and boot into a root shell

1. Reboot the machine from the console.
2. At the very start of the boot, hold `Shift` (BIOS) or press `Esc` repeatedly (UEFI) to show the GRUB menu.
3. With the **Ubuntu** entry selected, press `e` to edit it.
4. Find the line that starts with `linux` (it contains `/vmlinuz-...` and `root=...`).
5. Go to the end of that line (`End` key), make sure it has `rw`, and append:

```
init=/bin/bash
```

The end of the line should look like this:

```
... root=/dev/mapper/ubuntu--vg-ubuntu--lv rw init=/bin/bash
```

6. Press `Ctrl+X` (or `F10`) to boot. You land in a root shell (`root@(none):/#`).

The messages `cannot set terminal process group` and `no job control in this shell` are normal and can be ignored.

### Step 2: fix the account

Make sure the root filesystem is writable:

```bash
mount -o remount,rw /
```

**Option A, set a new password:**

```bash
passwd ubuntu
passwd -u ubuntu
```

**Option B, keep the existing password** (it was only locked):

```bash
passwd -u ubuntu
```

If cloud-init is what locked the account (section 3), disable it here too, or it locks the account again on the next boot:

```bash
touch /etc/cloud/cloud-init.disabled
```

Flush everything to disk:

```bash
sync
```

### Step 3: reboot normally

```bash
exec /sbin/init
```

If it hangs or doesn't respond:

```bash
sync && reboot -f
```

### Step 4: validate

1. Log in as `ubuntu` with the password.
2. **Reboot once more** and log in again, to confirm the fix survives a reboot.

---

## Alternative: the GRUB "recovery mode" entry

Instead of editing the kernel line, you can use the built-in recovery menu:

1. In GRUB, choose **Advanced options for Ubuntu** → the entry ending in **(recovery mode)**.
2. In the menu that appears, choose **root – Drop to root shell prompt** and press `Enter`.
3. Run the same commands from Step 2 (`mount -o remount,rw /`, `passwd ...`).
4. Leave with `exit` and choose **resume**, or run `reboot`.

> If the system has a root password set, recovery mode asks for it. In that case, use the `init=/bin/bash` method instead.
{: .prompt-info }

---

## Notes

- **Network isn't touched by this procedure.** On a server installed from the Ubuntu ISO, the network is usually managed by netplan (`/etc/netplan/*.yaml`) through systemd-networkd, independently of cloud-init.
- **Boot stuck at `Wait for Network to be Configured`** is a separate, common problem after moving a machine: the network interface name may have changed (e.g. `eth0` → `ens3`). Compare the name in the netplan file with the real one from `ip link show`, fix the YAML and run `netplan apply`.
- **Encrypted disks (LUKS)** ask for the disk passphrase before GRUB hands over to the shell. Without it, this procedure can't be used.

## Quick reference

| Situation | Command |
|---|---|
| Check status | `sudo passwd -S ubuntu` |
| Set a new password | `sudo passwd ubuntu` |
| Unlock the account | `sudo passwd -u ubuntu` |
| Stop cloud-init from locking it | `sudo touch /etc/cloud/cloud-init.disabled` |
| Root shell without a password | GRUB → `e` → add `init=/bin/bash` → `Ctrl+X` |
| Make `/` writable in that shell | `mount -o remount,rw /` |
| Leave the shell and boot normally | `exec /sbin/init` or `sync && reboot -f` |
