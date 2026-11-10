# Lab network: host-only static IPs — plan for HQ review (2026-11-10)

**Status: STOPPED FOR HQ REVIEW. Nothing below has been executed; no lab change has been made.**

The only commands run so far were reads: VBoxManage `showvminfo`, `list` and `snapshot list`; `ip`, `cat` and `systemctl
is-enabled` over ssh; `revert_node.sh --node-state`.

## 1. Why

- **All lab addresses are DHCP leases on the Wi-Fi LAN** (`wlo1`, 192.168.77.0/24): the laptop (.203), the master
  (.166) and the node (.185). A lease change breaks four things:
  - the ssh aliases;
  - the node's `/etc/hosts` entry for `puppet8master.example.com`, and with it agent→master;
  - the harness-source ACL fixtures (firewall_secure family and node_base, hazards.md item 12);
  - the rsyslog_client fixture, which pins the master's IP into the node's `/etc/hosts`.
- **Another Wi-Fi network** (another location, a new router) changes all of them at once.
- **The VMs are bridged onto that LAN**, so they are visible to it.

The target: lab traffic (laptop↔master, laptop↔node, node→master:8140) runs over the existing host-only network
`vboxnet0` with static addresses. Internet access for apt stays on NIC1 (see §6 for the NAT option).

## 2. Current state (read 2026-11-10, read-only)

| | laptop | master `Ubuntu24-puppet8-Master` | node `ubuntu24-puppet8-Node` |
|---|---|---|---|
| NIC1 | wlo1 192.168.77.203/24 (DHCP, default route) | bridged wlo1, `enp0s3` 192.168.77.166 DHCP | bridged wlo1, `enp0s3` 192.168.77.185 DHCP |
| NIC2 | `vboxnet0` 192.168.56.1/24 (exists since sprint 3.1) | **none** | hostonly vboxnet0, `enp0s8` DOWN, unconfigured (sprint 3.1) |
| netplan | — | `00-installer-config.yaml`: enp0s3 dhcp4 | same (0600 root) |
| name resolution | `~/.ssh/config`: puppet8master(-rsync) → .166, puppet8node(-rsync) → .185 | `/etc/hosts`: puppet8node.example.com → .185 | `/etc/hosts`: puppet8master.example.com → .166; `/etc/resolv.conf` static file |
| snapshot | — | current `P8MASTER_BASELINE_GREEN_v3` | current `P8NODE_BASELINE_GREEN_v2` |

Other facts that matter for the plan:
- **VirtualBox DHCP on vboxnet0:** the server is enabled with pool .101–.254. The chosen static addresses are outside
  it, so the server is left alone.
- **puppetserver:** it listens on `0.0.0.0` (webserver.conf), and its certificate SANs are DNS names only
  (`puppet8master`, `puppet8master.example.com`). Changing the IP needs no certificate change.
- **Node agent:** the agent service is disabled; the harness runs `puppet agent -t`.
- **IP literals in the lab:**
  - Params (untracked) hold four (§4 step 7).
  - The repo has none in its tools. Only documents carry IPs: CLAUDE.md "Facts", hazards.md 12, the
    DESIGN_DECISIONS history and reports. History stays as written.
- **VirtualBox:** 7.2.6. Netplan 1.1.2 on both guests.

**Target addresses:** master `enp0s8` 192.168.56.10/24 and node `enp0s8` 192.168.56.20/24, both without a gateway
(the default route stays on NIC1). The laptop stays 192.168.56.1, so the harness SSH source as the node sees it
becomes 192.168.56.1.

## 3. Rules this plan keeps

- **The master is never restored and never hard powered off.**
  - Its only rollback is undoing each step. That is why every master step below has an undo command, and the netplan
    step has a dead-man timer.
  - A master shutdown that is not a snapshot is human-only.
- **`modifyvm` (and any VM power-cycle it needs) is human-only.** It is in the settings deny list, and the steps
  that need it are marked **[HUMAN]**.
- **Verify before switch.** The bridged path stays the working path until the host-only path has been verified on
  both VMs. The ssh aliases switch only in step 6.
- **Snapshots:**
  - Both snapshots are refreshed only after the canary (§5) passes on the new network.
  - Until then, the node reverts to the unchanged v2 snapshot, plus a scripted overlay (step 4).
  - `P8NODE_BASELINE_GREEN_v2` and `P8MASTER_BASELINE_GREEN_v3` are kept after the refresh. Deleting either is HQ's
    call.
- **No change on the laptop** apart from the user's own `~/.ssh/config` (backed up first). It is a production
  Puppet 5 node, and vboxnet0 already exists.
- **Every tool change** ships with tests and shellcheck, one commit per step.

## 4. Steps

Each step: actor, exact commands, verification (all must pass before the next step), rollback.

### Step 0 — preflight (advisor, read-only)
```bash
git -C ~/work/infra_populi status --porcelain            # empty
pgrep -af 'test_class.sh|codex exec|review_class.py'     # nothing running
VBoxManage snapshot ubuntu24-puppet8-Node list --machinereadable | grep -c P8NODE_BASELINE_GREEN_v2      # 1
VBoxManage snapshot Ubuntu24-puppet8-Master list --machinereadable | grep -c P8MASTER_BASELINE_GREEN_v3   # 1
ssh puppet8master 'systemctl is-active puppetserver'     # active
ip -br addr show vboxnet0                                # 192.168.56.1/24 UP
```
Rollback: none (no change).

### Step 1 — [HUMAN] add NIC2 (host-only vboxnet0) to the master
`modifyvm` needs the master powered off.
```bash
VBoxManage controlvm Ubuntu24-puppet8-Master acpipowerbutton
until VBoxManage showvminfo Ubuntu24-puppet8-Master --machinereadable | grep -q '^VMState="poweroff"'; do sleep 2; done
VBoxManage modifyvm Ubuntu24-puppet8-Master --nic2 hostonly --hostonlyadapter2 vboxnet0 --nictype2 82540EM --cableconnected2 on
VBoxManage startvm Ubuntu24-puppet8-Master --type headless
```
- If ACPI does not power the master off within 5 minutes, stop and investigate. Never use `poweroff`.

Verify (advisor):
```bash
VBoxManage showvminfo Ubuntu24-puppet8-Master --machinereadable | grep -E '^(nic2|hostonlyadapter2)='  # hostonly / vboxnet0
ssh puppet8master 'ip -br link show enp0s8; systemctl is-active puppetserver'                      # enp0s8 DOWN; active
ssh puppet8node "timeout 5 bash -c 'exec 3<>/dev/tcp/puppet8master.example.com/8140'" && echo 8140-ok  # old path intact
```
Rollback [HUMAN]: ACPI shutdown as above, then `VBoxManage modifyvm Ubuntu24-puppet8-Master --nic2 none`, then
`startvm`.

### Step 2 — master `enp0s8` static 192.168.56.10/24 (advisor, under a dead-man timer)
```bash
ssh puppet8master 'sudo -n systemd-run --on-active=300 --unit=p8-net-deadman /bin/sh -c "rm -f /etc/netplan/60-p8-hostonly.yaml && netplan apply"'
ssh puppet8master 'printf "network:\n  version: 2\n  ethernets:\n    enp0s8:\n      dhcp4: false\n      addresses: [192.168.56.10/24]\n" | sudo -n tee /etc/netplan/60-p8-hostonly.yaml >/dev/null && sudo -n chmod 600 /etc/netplan/60-p8-hostonly.yaml && sudo -n netplan generate && sudo -n netplan apply'
```
Verify, within the 5-minute window:
```bash
ping -c3 -W2 192.168.56.10
ssh -o HostName=192.168.56.10 puppet8master 'ip -br addr show enp0s8; ip route | head -1'   # .10/24; default still via enp0s3
ssh -o HostName=192.168.56.10 puppet8master 'systemctl is-active puppetserver'               # active
ssh puppet8master true                                                                     # old path intact
```
- **All verifications pass:** disarm the timer with `ssh puppet8master 'sudo -n systemctl stop p8-net-deadman.timer'`.
- **Anything fails:** do nothing. The timer removes the file and re-applies netplan.

Rollback (manual, any time later):
```bash
ssh puppet8master 'sudo -n rm -f /etc/netplan/60-p8-hostonly.yaml && sudo -n netplan apply && sudo -n ip addr flush dev enp0s8'
```

### Step 3 — one-off node trial (advisor, on a freshly reverted node; the node is disposable)
```bash
.codex_state/tools/revert_node.sh
ssh puppet8node 'printf "network:\n  version: 2\n  ethernets:\n    enp0s8:\n      dhcp4: false\n      addresses: [192.168.56.20/24]\n" | sudo -n tee /etc/netplan/60-p8-hostonly.yaml >/dev/null && sudo -n chmod 600 /etc/netplan/60-p8-hostonly.yaml && sudo -n netplan generate && sudo -n netplan apply'
```
Verify:
```bash
ping -c3 -W2 192.168.56.20
ssh -o HostName=192.168.56.20 puppet8node 'echo $SSH_CLIENT'                                    # 192.168.56.1 ...
ssh -o HostName=192.168.56.20 puppet8node "timeout 5 bash -c 'exec 3<>/dev/tcp/192.168.56.10/8140'" && echo 8140-ok
ssh -o HostName=192.168.56.20 puppet8node 'sudo -n sed -i "s/^192\.168\.77\.166 /192.168.56.10 /" /etc/hosts && getent hosts puppet8master.example.com'   # 192.168.56.10
ssh -o HostName=192.168.56.20 puppet8node 'sudo -n /opt/puppetlabs/bin/puppet agent -t --noop' ; echo rc=$?          # 0 or 2: catalog fetched over host-only
ssh -o HostName=192.168.56.20 puppet8node 'sudo -n timeout 180 apt-get -q update' >/dev/null && echo apt-ok        # internet still via NIC1
```
- The node's `ip route` must still show its default route via `enp0s3`.

Rollback: `.codex_state/tools/revert_node.sh` (v2 is untouched). Always run it at the end of this step: the agent run
used up the node.

### Step 4 — canary-period node overlay in revert_node.sh (advisor; tool change + tests + shellcheck, own commit)
- **Mode.** An opt-in mode `P8_NODE_NET=hostonly`, documented in the script header.
- **Boot path.** After restoring v2 and booting, reach the node over the bridged path through a new alias,
  `puppet8node-bridged` (HostName 192.168.77.185, the same DHCP fragility as today, for the canary period only).
- **Overlay.**
  - Write step 3's netplan file and apply it.
  - Re-point the `/etc/hosts` master line to 192.168.56.10.
- **Then the existing checks, now over `puppet8node`** (host-only after step 6):
  - hostname;
  - `apt-get update`;
  - node→`puppet8master.example.com:8140`, which must now resolve to 192.168.56.10;
  - the state token (`revert-mark`).

The overlay applies no agent run, so the token stays that of the snapshot.
- **Default off.** With the variable unset the script is byte-for-byte today's behaviour (tests prove both).

Verify: stub-lab tests (overlay order, the fail-closed paths, the master never touched), then one real
`P8_NODE_NET=hostonly revert_node.sh` with step 3's checks.

Rollback: unset `P8_NODE_NET` (or `git revert` the commit).

### Step 5 — master `/etc/hosts` node entry (advisor)
```bash
ssh puppet8master 'sudo -n cp -p /etc/hosts /etc/hosts.pre-p8net && sudo -n sed -i "s/^192\.168\.77\.185 puppet8node\.example\.com/192.168.56.20 puppet8node.example.com/" /etc/hosts && getent hosts puppet8node.example.com'   # 192.168.56.20
```
- Puppet itself never connects from master to node. The entry only keeps the master's view consistent.

Rollback: `ssh puppet8master 'sudo -n cp -p /etc/hosts.pre-p8net /etc/hosts'`.

### Step 6 — switch the laptop aliases (advisor; the user's own `~/.ssh/config`, backed up)
1. Back up the file: `cp -p ~/.ssh/config ~/.ssh/config.pre-p8net`.
2. Add `puppet8node-bridged` (HostName 192.168.77.185, the same options as `puppet8node`) for step 4.
3. Verify the new addresses before switching:
   ```bash
   ssh -o HostName=192.168.56.10 puppet8master true && ssh -o HostName=192.168.56.20 puppet8node true
   ```
   This needs a node with the overlay applied (`P8_NODE_NET=hostonly revert_node.sh`).
4. Switch the `HostName` of `puppet8master`, `puppet8master-rsync`, `puppet8node` and `puppet8node-rsync` to
   192.168.56.10 / .20.
5. Close the old control sockets: `ssh -O exit puppet8master; ssh -O exit puppet8node`.

Verify:
```bash
ssh puppet8node 'echo $SSH_CLIENT'                                            # 192.168.56.1
P8_NODE_NET=hostonly .codex_state/tools/revert_node.sh                        # SUCCESS + REVERT_NODE_STATE
.codex_state/tools/test_class.sh --compile-only puppet_infrastructure::dns_client   # master over host-only
```
Rollback: `cp -p ~/.ssh/config.pre-p8net ~/.ssh/config`, then `ssh -O exit` for both.

### Step 7 — fixtures and documents (advisor)
- **Params (untracked):**
  - `acl` / `ssh_acl` 192.168.77.203 → 192.168.56.1: firewall_secure, firewall_secure_extra, node_base.
  - rsyslog_client `target_ip` 192.168.77.166 → 192.168.56.10. Without this, its `host` resource re-points the
    node's master entry to the bridged IP.
  - network_static's `gateway` 192.168.77.1 is fixture data for `p8test0`, not lab addressing, and stays.
- **Tracked, one commit:**
  - CLAUDE.md "Facts" (addresses);
  - hazards.md item 12: the harness source is now static 192.168.56.1, and the per-dispatch re-check stays;
  - the revert_node.sh header (the wlo1-bridge wait text);
  - a DESIGN_DECISIONS entry.

Verify: `ssh puppet8node 'echo $SSH_CLIENT'` matches the params, and `classify_path.py firewall_secure` still
routes.

Rollback: restore the four params values; `git revert` the commit.

### Step 8 — canary (advisor; §5)
Recommended: run the canary under `P8_NODE_NET=hostonly`. If it fails, roll back steps 7 → 1 in reverse order.

### Step 9 — refresh both snapshots (only after the canary passes; old snapshots kept)
- **Node:**
  1. `P8_NODE_NET=hostonly revert_node.sh`, then the step 3 checks.
  2. A clean shutdown, `ssh puppet8node 'sudo -n systemctl poweroff'`, and wait for `poweroff`.
  3. `VBoxManage snapshot ubuntu24-puppet8-Node take P8NODE_BASELINE_GREEN_v3 --description "<v2 + enp0s8
     192.168.56.20/24 + hosts master 192.168.56.10; repo <sha>>"`.
  4. revert_node.sh: `NODE_SNAPSHOT=P8NODE_BASELINE_GREEN_v3`, remove the overlay mode and `puppet8node-bridged`,
     and make the post-restore check verify enp0s8 = .20 (tests + shellcheck, own commit).
  5. Verify: two consecutive real reverts, then `test_class.sh --revert-first --fixture guarded_exec` GREEN.
- **Master:** `.codex_state/tools/snapshot_master.sh P8MASTER_BASELINE_GREEN_v4` (take-only, ACPI, restarts and
  verifies puppetserver + 8140, records the name and UUID).
- **Rollback:**
  - Node: point revert_node.sh back at v2 with the overlay (the previous commit).
  - Master: v4 is only an added snapshot; nothing to undo.
  - v2 and v3 remain until HQ rules on deletion.

## 5. Canary — decision for HQ
**Recommended:** both of these, in order:
1. **firewall_secure re-verification** (reviewer `--fresh`: revert-first harness on the new network). It is the most
   network-sensitive done class: default-drop with the harness-source ACL and agent→master 8140.
2. **The three Phase 3 pilots** (backup_rsnapshot, ssh_secure, nginx_static_domain), as HQ already scheduled them.

**Alternative:** the next pending class (gnome_lock_screen) through the full loop, which would open batch 4.

## 6. Decisions for HQ
1. **Approve steps 1–9 as written.** Step 1 is human-only; I execute the rest in order and stop at any failed
   verification.
2. **NIC1 stays bridged (recommended) or becomes NAT.** NAT removes the VMs from the Wi-Fi LAN entirely and makes
   apt independent of it.
   - With NAT: `[HUMAN] VBoxManage controlvm <vm> nic1 nat` (live), or `modifyvm --nic1 nat` while powered off, for
     both VMs, inserted before step 8. The canary then also proves apt over NAT.
   - Recommended: keep bridged for this project and decide NAT separately. Host-only already removes every DHCP
     dependency from lab addressing.
3. **Canary choice (§5).**
4. **Addresses:** 192.168.56.10 / .20 (outside the vboxnet0 DHCP pool .101–.254).

## 7. Risks
- **netplan apply on a guest briefly re-renders networkd for every interface.** The DHCP lease on enp0s3 is normally
  kept.
  - Master: protected by the step 2 dead-man timer, plus the bridged path for recovery.
  - Node: always revertible.
- **During the canary period the overlay reaches the node over the bridged DHCP address** (step 4). That is today's
  fragility, removed in step 9.
- **The laptop's own Puppet 5 agent could manage `~/.ssh/config` or vboxnet0.** Neither carries a Puppet header
  today; if either is reverted, step 6 shows it at the next ssh.
