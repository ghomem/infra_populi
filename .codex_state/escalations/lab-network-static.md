# Lab network: host-only static IPs — plan for HQ review (2026-11-10)

**Status: STEP REVIEW APPROVED by HQ with amendments A–E (2026-11-10, folded in below, listed in §6). Step 0 run (see
its result). Step 1 is Salatiel's — waiting for it. No lab change has been made.**

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
- **`modifyvm` (and any VM power-cycle it needs) is human-only.** Steps 1 and 10 are **[HUMAN]**.
- **Checks prove the path, not only success (HQ A).**
  - Every check over the new network runs through `ho` (below). It uses `-S none`, so no multiplexed socket can
    stand in for the path, and asserts `$SSH_CONNECTION` = `192.168.56.1 … <target> 22` inside the same session.
  - Every name check asserts the address. Printing it is not a check.
- **Host keys are never learned on the fly (HQ B).**
  - Every lab alias carries `HostKeyAlias`, and the alias names are seeded from the entries already trusted for the
    current addresses.
  - Never `StrictHostKeyChecking=no` or `accept-new`.
- **Verify before switch.** The Wi-Fi path stays the working path until the host-only path has been verified on both
  VMs. The main aliases and the tracked overlay setting switch together in step 6.
- **Snapshots:**
  - Both snapshots are refreshed only after the canary (§5) passes on the new network.
  - Until then, the node reverts to the unchanged v2 snapshot, plus the overlay that `.codex_state/lab/lab.env`
    (`NODE_NET=hostonly`) turns on.
  - `P8NODE_BASELINE_GREEN_v2` and `P8MASTER_BASELINE_GREEN_v3` are kept after the refresh. Deleting either is HQ's
    call.
- **No change on the laptop** apart from the user's own `~/.ssh/config` and `~/.ssh/known_hosts`. Each edit is backed
  up under its own step-specific name first. The laptop is a production Puppet 5 node, and vboxnet0 already exists.
- **Every tool change** ships with tests and shellcheck, one commit per step.
- **A failed verification stops the plan.** Each step's rollback is listed, and it is applied only when the step
  itself failed (step 8 excepted: a canary FAIL is escalated, not rolled back).

## 4. Steps

Each step: actor, exact commands, verification (all must pass before the next step), rollback.

The path-asserting helper, sourced before any step. It runs a command over the host-only path, and the remote side
refuses (exit 97) unless the session comes from 192.168.56.1 to the expected address:
```bash
ho() {  # ho <alias> <host-only IP> '<remote command>'
  local alias="$1" ip="$2"; shift 2
  ssh -S none -o BatchMode=yes -o HostName="$ip" "$alias" \
    "set -- \$SSH_CONNECTION; [ \"\$1\" = 192.168.56.1 ] && [ \"\$3\" = $ip ] || { echo \"PATH ASSERT FAILED: \$SSH_CONNECTION\" >&2; exit 97; }; $*"
}
```

### Step 0 — preflight (advisor, read-only)
```bash
test -z "$(git -C ~/work/infra_populi status --porcelain)"                                   # clean worktree
! pgrep -f 'test_class.sh|codex exec|review_class.py|phase3.py'                             # no engine run
VBoxManage snapshot ubuntu24-puppet8-Node list --machinereadable | grep -qx 'SnapshotName[-0-9]*="P8NODE_BASELINE_GREEN_v2"'
VBoxManage snapshot Ubuntu24-puppet8-Master list --machinereadable | grep -qx 'SnapshotName[-0-9]*="P8MASTER_BASELINE_GREEN_v3"'
test "$(ssh puppet8master 'systemctl is-active puppetserver')" = active
ip -br addr show vboxnet0 | grep -q ' 192.168.56.1/24'
# master certificate SANs, fail-closed (HQ A3): at least one DNS: entry, no IP Address, empty output = STOP
san="$(ssh puppet8master 'sudo -n openssl x509 -in /etc/puppetlabs/puppet/ssl/certs/puppet8master.pem -noout -ext subjectAltName')"
grep -q 'DNS:' <<<"$san" && ! grep -q 'IP Address' <<<"$san" || { echo "STOP: SAN check failed: '$san'"; false; }
# trusted host keys exist for the current addresses (step 1a seeds the alias names from them)
for ip in 192.168.77.166 192.168.77.185; do test "$(ssh-keygen -F "$ip" | grep -vc '^#')" -ge 1; done
# the path assert is not vacuous: over the Wi-Fi path it must refuse with 97
ho puppet8master 192.168.77.166 true; test $? -eq 97
```
Any failure = STOP. Rollback: none (no change).

### Step 1 — [HUMAN] add NIC2 (host-only vboxnet0) to the master
`modifyvm` needs the master powered off.
```bash
VBoxManage controlvm Ubuntu24-puppet8-Master acpipowerbutton
until VBoxManage showvminfo Ubuntu24-puppet8-Master --machinereadable | grep -q '^VMState="poweroff"'; do sleep 2; done
VBoxManage modifyvm Ubuntu24-puppet8-Master --nic2 hostonly --hostonlyadapter2 vboxnet0 --nictype2 82540EM --cableconnected2 on
VBoxManage startvm Ubuntu24-puppet8-Master --type headless
```
- If ACPI does not power the master off within 5 minutes, stop and investigate. Never use `poweroff`.

Verify (advisor), waiting up to 5 minutes for puppetserver (HQ E):
```bash
VBoxManage showvminfo Ubuntu24-puppet8-Master --machinereadable | grep -qx 'nic2="hostonly"'
VBoxManage showvminfo Ubuntu24-puppet8-Master --machinereadable | grep -qx 'hostonlyadapter2="vboxnet0"'
deadline=$((SECONDS + 300))
until [ "$(ssh -o ConnectTimeout=5 puppet8master 'systemctl is-active puppetserver' 2>/dev/null)" = active ]; do
  [ $SECONDS -lt $deadline ] || { echo "STOP: puppetserver not active after 300 s"; false; break; }; sleep 5
done
ssh puppet8master 'ip -br link show enp0s8' | grep -q '^enp0s8 '                              # the new NIC exists
ssh puppet8node "timeout 5 bash -c 'exec 3<>/dev/tcp/puppet8master.example.com/8140'"          # old path intact
```
Rollback [HUMAN]: ACPI shutdown as above, then `VBoxManage modifyvm Ubuntu24-puppet8-Master --nic2 none`, then
`startvm`.

### Step 1a — laptop aliases: host-key aliases and Wi-Fi fallbacks (advisor, before step 2's first check; HQ B)
```bash
cp -p ~/.ssh/config      ~/.ssh/config.pre-p8net-step1a
cp -p ~/.ssh/known_hosts ~/.ssh/known_hosts.pre-p8net-step1a
# seed the alias names from the keys already trusted for the current addresses (no network key fetch)
for pair in puppet8master=192.168.77.166 puppet8node=192.168.77.185; do
  name="${pair%%=*}" ip="${pair#*=}"
  ssh-keygen -F "$name" | grep -q . && continue                       # already seeded
  ssh-keygen -F "$ip" | grep -v '^#' | awk -v n="$name" '{ $1 = n; print }' >> ~/.ssh/known_hosts
done
```
Then edit `~/.ssh/config`:
- add `HostKeyAlias puppet8master` to `puppet8master` and `puppet8master-rsync`, and `HostKeyAlias puppet8node` to
  `puppet8node` and `puppet8node-rsync`;
- add `puppet8master-wifi` (HostName 192.168.77.166, `HostKeyAlias puppet8master`) and `puppet8node-wifi` (HostName
  192.168.77.185, `HostKeyAlias puppet8node`), with the same User / IdentityFile / IdentitiesOnly / LogLevel as the
  main aliases.

Close the engine's multiplexed sockets so the checks below are fresh connections:
`PATH=~/work/infra_populi/.codex_state/tools/sshmux:$PATH ssh -O exit <alias>` for the four main aliases.

Verify:
```bash
for n in puppet8master puppet8node; do                                   # seeded keys = trusted keys, same set
  diff <(ssh-keygen -F "$n" | grep -v '^#' | awk '{print $2, $3}' | sort) \
       <(ssh-keygen -F "$( [ $n = puppet8master ] && echo 192.168.77.166 || echo 192.168.77.185 )" | grep -v '^#' | awk '{print $2, $3}' | sort)
done
for a in puppet8master puppet8master-rsync puppet8master-wifi puppet8node puppet8node-rsync puppet8node-wifi; do
  ssh -G "$a" | awk -v a="$a" '$1=="hostkeyalias"{k=$2} $1=="stricthostkeychecking"{s=$2}
    END { if (k !~ /^puppet8(master|node)$/ || s == "false" || s == "accept-new") { print "STOP " a; exit 1 } }'
  ssh -S none -o BatchMode=yes "$a" true                                 # BatchMode: an unknown key would fail here
done
```
Rollback: `cp -p ~/.ssh/config.pre-p8net-step1a ~/.ssh/config; cp -p ~/.ssh/known_hosts.pre-p8net-step1a ~/.ssh/known_hosts`.

### Step 2 — master `enp0s8` static 192.168.56.10/24 (advisor, under a dead-man timer)
```bash
ssh puppet8master 'sudo -n systemd-run --on-active=300 --unit=p8-net-deadman /bin/sh -c "rm -f /etc/netplan/60-p8-hostonly.yaml && netplan apply && ip addr flush dev enp0s8"'
ssh puppet8master 'printf "network:\n  version: 2\n  ethernets:\n    enp0s8:\n      dhcp4: false\n      addresses: [192.168.56.10/24]\n" | sudo -n tee /etc/netplan/60-p8-hostonly.yaml >/dev/null && sudo -n chmod 600 /etc/netplan/60-p8-hostonly.yaml && sudo -n netplan generate && sudo -n netplan apply'
```
Verify, within the 5-minute window:
```bash
ping -c3 -W2 192.168.56.10
ho puppet8master 192.168.56.10 'ip -br addr show enp0s8 | grep -q " 192.168.56.10/24" && ip route show default | grep -q "dev enp0s3"'
ho puppet8master 192.168.56.10 'test "$(systemctl is-active puppetserver)" = active'
ssh -S none puppet8master-wifi true                                                         # fallback intact
```
- **All verifications pass:** disarm the timer with `ssh puppet8master 'sudo -n systemctl stop p8-net-deadman.timer'`.
- **Anything fails:** do nothing. The timer removes the file, re-applies netplan and flushes enp0s8.

Rollback (manual, any time later):
```bash
ssh puppet8master-wifi 'sudo -n rm -f /etc/netplan/60-p8-hostonly.yaml && sudo -n netplan apply && sudo -n ip addr flush dev enp0s8'
```

### Step 3 — one-off node trial (advisor, on a freshly reverted node; the node is disposable)
```bash
.codex_state/tools/revert_node.sh                                        # lab.env absent → today's bridged mode
ssh puppet8node-wifi 'printf "network:\n  version: 2\n  ethernets:\n    enp0s8:\n      dhcp4: false\n      addresses: [192.168.56.20/24]\n" | sudo -n tee /etc/netplan/60-p8-hostonly.yaml >/dev/null && sudo -n chmod 600 /etc/netplan/60-p8-hostonly.yaml && sudo -n netplan generate && sudo -n netplan apply'
```
Verify, in this order (each must pass; the noop agent run counts only after the name assert):
```bash
ping -c3 -W2 192.168.56.20
ho puppet8node 192.168.56.20 'ip route show default | grep -q "dev enp0s3"'                  # internet stays on NIC1
ho puppet8node 192.168.56.20 "timeout 5 bash -c 'exec 3<>/dev/tcp/192.168.56.10/8140'"
ho puppet8node 192.168.56.20 'sudo -n sed -i "s/^192\.168\.77\.166 /192.168.56.10 /" /etc/hosts'
ho puppet8node 192.168.56.20 'set -- $(getent hosts puppet8master.example.com); test "$1" = 192.168.56.10'   # assert (HQ A2)
ho puppet8node 192.168.56.20 'sudo -n /opt/puppetlabs/bin/puppet agent -t --noop; rc=$?; test $rc -eq 0 -o $rc -eq 2'
ho puppet8node 192.168.56.20 'sudo -n timeout 180 apt-get -q update >/dev/null'
```
Rollback: `.codex_state/tools/revert_node.sh` (v2 is untouched). Always run it at the end of this step: the agent run
used up the node.

### Step 4 — tracked overlay setting + overlay mode in revert_node.sh (advisor; tool change + tests + shellcheck, own commit; HQ C)
- **Setting.** New tracked file `.codex_state/lab/lab.env` with `NODE_NET=bridged` (this commit). revert_node.sh reads
  it; `P8_NODE_NET` stays only as a test override. An unknown value is an error.
- **`bridged`:** byte-for-byte today's behaviour (tests prove it).
- **`hostonly`, in order:**
  1. After restoring v2 and booting, wait for SSH on `puppet8node-wifi`.
  2. Apply the overlay: step 3's netplan file, and the `/etc/hosts` master line → 192.168.56.10.
  3. Then, with `-S none`: assert `$SSH_CONNECTION` (192.168.56.1 → 192.168.56.20) and assert
     `getent hosts puppet8master.example.com` = 192.168.56.10 (a mismatch fails the revert).
  4. Then the existing checks over `puppet8node`: hostname, `apt-get update`, node→`puppet8master.example.com:8140`.
  5. Finally the state token (`revert-mark`). The overlay applies no agent run, so the token stays the snapshot's.

Verify:
- stub-lab tests: overlay order, each assert failing closed, the env override, an unknown value, the master never
  touched;
- one real revert in `bridged` mode (unchanged behaviour). The first real `hostonly` revert is step 6.

Rollback: `git revert` the commit.

### Step 5 — master `/etc/hosts` node entry (advisor; asserted, HQ A2)
```bash
ho puppet8master 192.168.56.10 'sudo -n cp -p /etc/hosts /etc/hosts.pre-p8net && sudo -n sed -i "s/^192\.168\.77\.185 puppet8node\.example\.com/192.168.56.20 puppet8node.example.com/" /etc/hosts'
ho puppet8master 192.168.56.10 'set -- $(getent hosts puppet8node.example.com); test "$1" = 192.168.56.20'      # assert
```
- Puppet itself never connects from master to node. The entry only keeps the master's view consistent.

Rollback: `ssh puppet8master-wifi 'sudo -n cp -p /etc/hosts.pre-p8net /etc/hosts'`.

### Step 6 — switch the main aliases and the overlay setting together (advisor; one commit for lab.env)
1. Back up under a new name (step 1a's backup is not overwritten):
   `cp -p ~/.ssh/config ~/.ssh/config.pre-p8net-step6`.
2. Prepare a node on the new path:
   - `.codex_state/tools/revert_node.sh` (still `bridged`);
   - apply step 3's netplan and hosts commands over `puppet8node-wifi`;
   - verify before switching: `ho puppet8master 192.168.56.10 true && ho puppet8node 192.168.56.20 true`.
3. Close the control sockets BEFORE editing (HQ A4). `%C` hashes the HostName, so after the edit the old sockets
   could no longer be addressed:
   `PATH=~/work/infra_populi/.codex_state/tools/sshmux:$PATH; for a in puppet8master puppet8master-rsync puppet8node puppet8node-rsync; do ssh -O exit "$a" 2>/dev/null || true; done`
4. Switch the `HostName` of `puppet8master` and `puppet8master-rsync` to 192.168.56.10, and of `puppet8node` and
   `puppet8node-rsync` to 192.168.56.20. The `-wifi` aliases stay unchanged.
5. Assert what ssh will use:
   ```bash
   for a in puppet8master puppet8master-rsync; do test "$(ssh -G $a | awk '$1=="hostname"{print $2}')" = 192.168.56.10; done
   for a in puppet8node puppet8node-rsync;     do test "$(ssh -G $a | awk '$1=="hostname"{print $2}')" = 192.168.56.20; done
   ```
6. Commit `.codex_state/lab/lab.env` with `NODE_NET=hostonly` (the overlay setting flips in the same step as the
   aliases).

Verify:
```bash
ssh -S none puppet8node   'echo $SSH_CONNECTION' | awk '$1=="192.168.56.1" && $3=="192.168.56.20" {ok=1} END {exit !ok}'
ssh -S none puppet8master 'echo $SSH_CONNECTION' | awk '$1=="192.168.56.1" && $3=="192.168.56.10" {ok=1} END {exit !ok}'
.codex_state/tools/revert_node.sh                                                 # first real hostonly revert: SUCCESS
.codex_state/tools/test_class.sh --compile-only puppet_infrastructure::dns_client  # master over host-only
```
Rollback:
1. `cp -p ~/.ssh/config.pre-p8net-step6 ~/.ssh/config`, then close the sockets again;
2. `git revert` the lab.env commit.

### Step 7 — fixtures, documents, and a sweep of the master for old addresses (advisor)
- **Params (untracked):**
  - `acl` / `ssh_acl` 192.168.77.203 → 192.168.56.1: firewall_secure, firewall_secure_extra, node_base.
  - rsyslog_client `target_ip` 192.168.77.166 → 192.168.56.10. Without this, its `host` resource re-points the
    node's master entry to the Wi-Fi IP.
  - network_static's `gateway` 192.168.77.1 is fixture data for `p8test0`, not lab addressing, and stays.
- **Sweep (HQ E).** A read-only scan of the master (the environment lives under /etc), file names only, with the
  passwd directory excluded:
  ```bash
  ssh puppet8master "sudo -n sh -c 'find /etc -path /etc/puppetlabs/code/environments/production/manifests/nodes/passwd -prune -o -type f -print0 | xargs -0 grep -IlF 192.168.77. 2>/dev/null'"
  ```
  - Every listed file is triaged in this file (expected: `/etc/hosts.pre-p8net`, the step 5 backup).
  - A lab-addressing hit is a finding to fix (fixture state) or escalate. File contents are never copied into the
    repo.
- **Tracked, one commit:**
  - CLAUDE.md "Facts" (addresses);
  - hazards.md item 12: the harness source is now static 192.168.56.1, and the per-dispatch re-check stays;
  - the revert_node.sh header (the wlo1-bridge wait text);
  - a DESIGN_DECISIONS entry.

Verify:
- `ho puppet8node 192.168.56.20 'echo $SSH_CLIENT'` starts with the params' 192.168.56.1;
- `classify_path.py firewall_secure` still routes.

Rollback: restore the four params values; `git revert` the commit.

### Step 8 — canary (advisor; §5, HQ-chosen; lab.env `NODE_NET=hostonly`)
In this order; each item must pass before the next:
1. firewall_secure — reviewer `firewall_secure --fresh` (revert-first harness; default-drop with the harness-source ACL
   192.168.56.1, agent→master 8140 over host-only). Verdict committed as usual.
2. rsyslog_client — reviewer `rsyslog_client --fresh` (its `host` resource pins puppet8master.example.com to the step-7
   fixture address 192.168.56.10; the agent must still reach the master after the pin).
3. The three Phase 3 pilots — `phase3.py run <class>` then reviewer `<class> --phase3`, for backup_rsnapshot, ssh_secure,
   nginx_static_domain (escalations/phase3-pilots.md).

**A canary FAIL stops the plan and is escalated (HQ E).** It goes into `escalations/lab-network-canary.md` with the
evidence (verdict JSON, harness log tail, the path asserts), with no automatic rollback; HQ decides. A Phase 3 FINDING
is a pilot result, not a canary failure.

### Step 9 — refresh both snapshots (only after the canary passes; old snapshots kept)
- **Node (HQ D: no agent run between the overlay and the poweroff):**
  1. `.codex_state/tools/revert_node.sh` (hostonly overlay; it records the state token).
  2. Non-mutating checks only:
     ```bash
     ping -c3 -W2 192.168.56.20
     ho puppet8node 192.168.56.20 true                                                     # SSH_CONNECTION assert
     ho puppet8node 192.168.56.20 "timeout 5 bash -c 'exec 3<>/dev/tcp/puppet8master.example.com/8140'"
     ho puppet8node 192.168.56.20 'set -- $(getent hosts puppet8master.example.com); test "$1" = 192.168.56.10'
     ho puppet8node 192.168.56.20 'ip route show default | grep -q "dev enp0s3"'
     ```
  3. The state token is unchanged since the overlay:
     `diff <(.codex_state/tools/revert_node.sh --node-state) <(python3 -c 'import json; r = json.load(open(".codex_state/logs/node_revert.json")); print(r["boot_id"]); print(r["last_run"])')`.
  4. A clean shutdown, `ssh puppet8node 'sudo -n systemctl poweroff'`, and wait for `VMState="poweroff"`.
  5. `VBoxManage snapshot ubuntu24-puppet8-Node take P8NODE_BASELINE_GREEN_v3 --description "<v2 + enp0s8
     192.168.56.20/24 + hosts master 192.168.56.10; repo <sha>; token <boot>/<last_run>>"`.
     - The snapshot also carries the apt lists of that revert's `apt-get update`, which is refreshed after every
       revert anyway.
  6. revert_node.sh: `NODE_SNAPSHOT=P8NODE_BASELINE_GREEN_v3`.
     - Remove the overlay mode AND `.codex_state/lab/lab.env` (HQ C).
     - The post-restore check asserts enp0s8 = .20 and `$SSH_CONNECTION`.
     - Tests + shellcheck, own commit.
  7. Verify: two consecutive real reverts, then `test_class.sh --revert-first --fixture guarded_exec` GREEN.
- **Master:** `.codex_state/tools/snapshot_master.sh P8MASTER_BASELINE_GREEN_v4` (take-only, ACPI, restarts and
  verifies puppetserver + 8140, records the name and UUID). It also captures the pki v2 fixture state.
- **Rollback:**
  - Node: `git revert` the step-9 commit (back to v2 + the lab.env overlay).
  - Master: v4 is only an added snapshot; nothing to undo.
  - v2 and v3 remain until HQ rules on deletion.

### Step 10 — [HUMAN] Wi-Fi off proof, then retire the fallback aliases (after both snapshots are verified; HQ E)
1. Salatiel turns the laptop's Wi-Fi off.
2. Advisor, with no revert (its apt refresh needs internet):
   ```bash
   ssh -S none puppet8master 'echo $SSH_CONNECTION' | awk '$1=="192.168.56.1" && $3=="192.168.56.10" {ok=1} END {exit !ok}'
   ssh -S none puppet8node   'echo $SSH_CONNECTION' | awk '$1=="192.168.56.1" && $3=="192.168.56.20" {ok=1} END {exit !ok}'
   ssh -S none puppet8node "timeout 5 bash -c 'exec 3<>/dev/tcp/puppet8master.example.com/8140'"
   .codex_state/tools/test_class.sh --compile-only puppet_infrastructure::dns_client
   ```
3. Salatiel turns Wi-Fi back on.
4. Only if step 2 passed: back up to `~/.ssh/config.pre-p8net-step10`, then remove `puppet8master-wifi` and
   `puppet8node-wifi`. The seeded `puppet8master` / `puppet8node` known_hosts entries stay: the main aliases use them.

Rollback: restore `~/.ssh/config.pre-p8net-step10`.

## 5. Canary (HQ decision)
firewall_secure + rsyslog_client (reviewer re-verification) + the three Phase 3 pilots — step 8.

## 6. HQ decisions
Design (2026-11-10):
1. Approved. NIC1 stays bridged for internet; NAT is a follow-up plan, written once host-only control is proven.
2. Canary §5. Addresses 192.168.56.10 (master) / .20 (node).
3. Step 0 verifies that the master certificate's SANs are name-only.
4. The `-wifi` fallback aliases are kept until the snapshots are refreshed (since the step review: until step 10
   passes).

Step review (2026-11-10), approved with these amendments, all folded in above:
- **A. Checks prove the path.**
  1. `ho` gives `-S none` plus an in-session `$SSH_CONNECTION` assert.
  2. getent results are asserted (steps 3, 4, 5, 9); the noop agent run comes after the assert.
  3. The step 0 SAN check fails closed.
  4. Step 6 closes the sockets before the edit and asserts `ssh -G`.
- **B. Host keys.** `HostKeyAlias` on the main, `-rsync` and `-wifi` aliases, seeded from the trusted entries
  (step 1a, before step 2). Never `StrictHostKeyChecking=no` or `accept-new`.
- **C. The overlay mode is the tracked `.codex_state/lab/lab.env`** (`NODE_NET`). The env var is only a test override.
  It flips in step 6 and is removed with the overlay in step 9.
- **D. Step 9 runs non-mutating checks only**, with the state token unchanged since the overlay, then poweroff and
  snapshot.
- **E. Smaller amendments:**
  - distinct backup names;
  - the dead-man unit also flushes enp0s8;
  - step 1 waits for puppetserver;
  - step 7 sweeps the master;
  - a step 8 FAIL is escalated, not rolled back;
  - new step 10 (Wi-Fi off proof) before the `-wifi` aliases are removed.

## 7. Risks
- **netplan apply on a guest briefly re-renders networkd for every interface.** The DHCP lease on enp0s3 is normally
  kept.
  - Master: protected by the step 2 dead-man timer, plus the `-wifi` path for recovery.
  - Node: always revertible.
- **During the canary period the overlay reaches the node over the Wi-Fi DHCP address** (`puppet8node-wifi`, step 4).
  That is today's fragility, removed in step 9.
- **The laptop's own Puppet 5 agent could manage `~/.ssh/config`, `~/.ssh/known_hosts` or vboxnet0.** None carries a
  Puppet header today; a reverted edit shows at the next ssh, which step 1a's BatchMode checks run.
