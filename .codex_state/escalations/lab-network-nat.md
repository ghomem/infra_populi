# Lab network: NIC1 bridged → NAT — plan (2026-11-16)

**Status: APPROVED WITH AMENDMENTS (HQ step review, 2026-11-16); amended here; executing with Salatiel present.**
Execution results go in §8. The original plan (steps 0–6, reviewed by HQ) is in git history; the amendments are listed
in §9.

## 1. Why, and the requirements (HQ 2026-11-16 item 5)
After the host-only project, lab control no longer uses the home LAN. Internet and DNS for the VMs still do, through
NIC1 bridged to `wlo1`:
- **master:** its DNS is the home router, `192.168.77.1`, learned by DHCP on enp0s3 (search domains `lan home`). Its
  internet is via `192.168.77.1`.
- **node:** a static `/etc/resolv.conf` (1.1.1.1, 8.8.8.8), but reached through the home LAN's gateway.
- **both:** the VMs are visible on the home LAN.

Requirements:
1. The VMs' internet AND DNS must not depend on the home LAN.
2. Verify before each switch, with a rollback per step.
3. Human-only steps are marked **[HUMAN]**.
4. Acceptance: the laptop on a phone hotspot, then one revert, one compile and one fixture harness run.

## 2. Design
- **NIC1 → VirtualBox NAT, with `--natdnshostresolver1 on`, on both VMs.** NAT gives each VM its own private network:
  enp0s3 gets 10.0.2.15/24 by DHCP, with gateway 10.0.2.2. Outbound traffic leaves through the laptop's current
  uplink, whatever it is (home Wi-Fi, hotspot).
- **DNS, master.** systemd-resolved with DHCP-provided DNS becomes 10.0.2.3, VirtualBox's NAT DNS. With
  `natdnshostresolver1 on` that proxy resolves each query through the laptop's own resolver, so it follows the
  laptop's network live (home router at home, hotspot DNS on the hotspot). Without the flag, the proxy copies the
  laptop's DNS servers when the VM starts, which goes stale when the laptop changes networks. Hence the flag.
- **DNS, node.** The static 1.1.1.1/8.8.8.8 keeps working through NAT and does not involve the home LAN. **HQ: the
  node keeps its public resolvers**; the acceptance test proves them on the hotspot.
- **Unchanged:** NIC2 host-only (lab control), the harness SSH source 192.168.56.1, `/etc/hosts` on both VMs, the
  certificate (name-only SANs), and puppetserver.
- **The NIC1 attachment is part of the VM configuration, so it lives in snapshots.** Restoring node v3 brings back
  NIC1 bridged. The node therefore needs a new baseline, P8NODE_BASELINE_GREEN_v4; the master gets
  P8MASTER_BASELINE_GREEN_v5 after acceptance. **No step depends on a bridged revert (HQ A):** the node goes to NAT
  straight from a restore of v3, by hand.
- **New lab VMs (HQ G):** every `p8lab-*` VM gets the same NIC1 setting (NAT, `natdnshostresolver1 on`), with NIC2
  host-only on vboxnet0.
- **Retention:** node v2 and master v3 stay through batch 4 (HQ); node v3 and master v4 are kept until HQ rules.
- **Side effect to expect:** the facts change. `networking.ip` / `ipaddress` on both VMs becomes 10.0.2.15 instead of
  192.168.77.x (enp0s3 is the primary interface). A class that renders the node's own IP into a file would render a
  different value, which is fixture context, not a regression. Step 0 lists the done classes that read these facts.
- **Facts that must NOT follow the uplink (HQ B):** `networking.hostname`, `networking.fqdn` and `networking.domain`
  on both VMs are recorded before the change, after it, and on the hotspot, and must be identical all three times.
  If NAT's DHCP changes one of them (VirtualBox NAT passes the host's DNS domain by DHCP), the smallest change that
  pins it goes into v4 (node) or onto the master, and is reported. `networking.ip` becoming 10.0.2.15 is expected.
- **`serverip` (HQ C):** `$server_facts['serverip']` is the master's primary address, which on a two-NIC master is not
  the address the node uses for it (today 192.168.77.166 bridged, 10.0.2.15 after NAT; the node uses 192.168.56.10).
  The ruled firewall_addon_hosting fix used it; step 6 changes that fix.

## 3. Rules kept
- **Master:** never restored and never hard powered off. Its NIC change needs a power cycle, which is human-only
  (ACPI).
- **[HUMAN]:** every `modifyvm` / `controlvm nic*` (VM configuration), and the network switch of the laptop itself.
- **Every check proves the path:** the host-only helper `ho` (escalations/lab-network-static.md §4). Internet and
  DNS checks assert addresses: no `192.168.77.` address, route or DNS server may remain on a VM.
- **A failed verification stops the plan.** Each step lists its rollback.

## 4. Steps
`ho` is the helper from lab-network-static.md: `-S none`, plus an in-session `$SSH_CONNECTION` assert.
`facts` below is `sudo -n /opt/puppetlabs/bin/facter --json networking.hostname networking.fqdn networking.domain
networking.ip` over `ho` (read-only; not an agent run, so the state token does not move).

**Lab lock for the whole plan:** before step 0 the advisor takes `lab_lock.sh take <holder> "NAT plan"` with a holder
process that lives until step 9, and runs every engine command of the plan with `P8_LAB_LOCKED=1` under it. Nothing
else can revert the node or write the master's node file meanwhile. Released after step 9.

### Step 0 — preflight (advisor, read-only)
```bash
test -z "$(git -C ~/work/infra_populi status --porcelain)"; ! pgrep -f '[t]est_class.sh|[c]odex exec|[r]eview_class.py|[p]hase3.py'
ho puppet8master 192.168.56.10 true && ho puppet8node 192.168.56.20 true
VBoxManage showvminfo Ubuntu24-puppet8-Master --machinereadable | grep -qx 'nic1="bridged"'
VBoxManage showvminfo ubuntu24-puppet8-Node   --machinereadable | grep -qx 'nic1="bridged"'
ho puppet8master 192.168.56.10 'curl -sS -o /dev/null -w "%{http_code}" https://forgeapi.puppet.com/v3/modules/puppetlabs-stdlib' # 200 today
git -C ~/work/infra_populi grep -nE "networking'\]\['ip|\\\$::ipaddress|\\\$ipaddress\b|@ipaddress|server_facts|serverip" -- manifests templates   # list, for §2 (HQ C)
```
- **Facts before (HQ B):** `facts` on both VMs.
- **v3's state token:** the `last_run` of `.codex_state/logs/node_revert.json` (a v3 revert), for step 3.
- **Home SSID (HQ E):** `nmcli -t -f active,ssid dev wifi | grep '^yes'`.

Rollback: none.

### Step 1 — [HUMAN] node to NAT, from v3 (HQ A)
```bash
VBoxManage controlvm ubuntu24-puppet8-Node poweroff
VBoxManage snapshot ubuntu24-puppet8-Node restore P8NODE_BASELINE_GREEN_v3
VBoxManage modifyvm ubuntu24-puppet8-Node --nic1 nat --natdnshostresolver1 on
VBoxManage startvm ubuntu24-puppet8-Node --type headless
```
Rollback: the same poweroff and restore of v3 (NIC1 bridged again); revert_node.sh still points at v3.

### Step 2 — node checks on NAT (advisor)
```bash
until ho puppet8node 192.168.56.20 true 2>/dev/null; do sleep 3; done          # host-only path unchanged (timeout 180 s)
ho puppet8node 192.168.56.20 'ip -br addr show enp0s3 | grep -q " 10.0.2.15/24" && ip route show default | grep -q "via 10.0.2.2 dev enp0s3"'
ho puppet8node 192.168.56.20 '! ip -4 addr | grep -q "192\.168\.77\." && ! grep -q "192\.168\.77\." /etc/resolv.conf'
ho puppet8node 192.168.56.20 'getent ahostsv4 archive.ubuntu.com >/dev/null'   # DNS through NAT (public resolvers)
ho puppet8node 192.168.56.20 'sudo -n timeout 180 apt-get -q update >/dev/null' # internet through NAT; the refreshed lists stay in v4
ho puppet8node 192.168.56.20 "timeout 5 bash -c 'exec 3<>/dev/tcp/puppet8master.example.com/8140'"
ho puppet8node 192.168.56.20 'set -- $(getent hosts puppet8master.example.com); test "$1" = 192.168.56.10'
```
- **Facts after (HQ B):** `facts` on the node; hostname, fqdn and domain identical to step 0, ip 10.0.2.15. A
  difference is pinned here with the smallest change (for example a netplan `dhcp4-overrides` on enp0s3), then
  re-checked, and reported.

**A failed check stops the plan** (HQ A); the revert script still points at v3. Rollback as step 1.

### Step 3 — node baseline P8NODE_BASELINE_GREEN_v4
1. Advisor: the state token is unchanged: `revert_node.sh --node-state` prints this boot's ID and a `last_run` equal
   to v3's (step 0): one clean boot, no agent run.
2. Advisor: clean poweroff, `ssh puppet8node 'sudo -n systemctl poweroff'`, then wait for `VMState="poweroff"`.
3. **[HUMAN] (HQ H)**: the advisor's settings deny a raw snapshot take on ubuntu24-puppet8-Node (lab_vm.sh acts on
   p8lab-* only) and stay that way, so Salatiel runs:
   ```bash
   VBoxManage snapshot ubuntu24-puppet8-Node take P8NODE_BASELINE_GREEN_v4 --description "v3 + NIC1 NAT (natdnshostresolver1 on) + package lists refreshed through NAT; one clean boot, no agent run; state token unchanged (last_run <v3's>); repo <sha>"
   ```
   The VM stays powered off; the next revert (step 5) starts it.

Rollback: none needed; v3 is untouched, and v4 stays unused until step 5's commit.

### Step 4 — [HUMAN] master NIC1 → NAT
```bash
VBoxManage controlvm Ubuntu24-puppet8-Master acpipowerbutton
until VBoxManage showvminfo Ubuntu24-puppet8-Master --machinereadable | grep -q '^VMState="poweroff"'; do sleep 2; done
VBoxManage modifyvm Ubuntu24-puppet8-Master --nic1 nat --natdnshostresolver1 on
VBoxManage startvm Ubuntu24-puppet8-Master --type headless
```
- If ACPI doesn't stop the master within 5 minutes, stop and investigate. Never use `poweroff`.

Verify (advisor):
```bash
deadline=$((SECONDS+300)); until ho puppet8master 192.168.56.10 'test "$(systemctl is-active puppetserver)" = active' 2>/dev/null; do [ $SECONDS -lt $deadline ] || break; sleep 5; done
ho puppet8master 192.168.56.10 'test "$(curl -sk https://localhost:8140/status/v1/simple)" = running'
ho puppet8master 192.168.56.10 'ip -br addr show enp0s3 | grep -q " 10.0.2.15/24" && ip route show default | grep -q "via 10.0.2.2 dev enp0s3"'
ho puppet8master 192.168.56.10 'resolvectl dns enp0s3 | grep -q "10\.0\.2\.3" && ! resolvectl status | grep -q "192\.168\.77\."'
ho puppet8master 192.168.56.10 'test "$(curl -sS -o /dev/null -w "%{http_code}" https://forgeapi.puppet.com/v3/modules/puppetlabs-stdlib)" = 200'   # r10k's Forge
ho puppet8master 192.168.56.10 'set -- $(getent hosts puppet8node.example.com); test "$1" = 192.168.56.20'
ho puppet8master 192.168.56.10 'ip -br addr show enp0s8 | grep -q " 192.168.56.10/24"'
.codex_state/tools/test_class.sh --compile-only puppet_infrastructure::dns_client
```
- **One non-A query (HQ D):** `ho puppet8master 192.168.56.10 'resolvectl query --type=MX gmail.com'`, result
  recorded. A failure is a noted limit of the NAT DNS proxy, not a stop.
- **Facts after (HQ B):** `facts` on the master; hostname, fqdn and domain identical to step 0. A difference is
  pinned on the master with the smallest change and reported.
- **serverip (HQ C):** recorded (expected 10.0.2.15).

Rollback [HUMAN]: ACPI shutdown, then `VBoxManage modifyvm Ubuntu24-puppet8-Master --nic1 bridged --bridgeadapter1
wlo1 --natdnshostresolver1 off`, then `startvm`.

### Step 5 — revert to v4 (advisor; tool change + tests + shellcheck, own commit)
- `.codex_state/lab/nodes.yml`: ubuntu's `baseline_snapshot: P8NODE_BASELINE_GREEN_v4`.
- revert_node.sh, post-restore asserts, for every node:
  - the default route is via 10.0.2.2, on the interface holding 10.0.2.15/24 (NIC1 NAT);
  - no `192.168.77.` address on the node.

  The existing `apt-get update` (Debian) / `dnf makecache` (RedHat) keeps proving internet and DNS.
- Verify: two consecutive real reverts, then `test_class.sh --revert-first --fixture guarded_exec` GREEN.

Rollback: `git revert` the step-5 commit (back to v3, bridged).

### Step 6 — firewall_addon_hosting: the ruled master rule follows the node (HQ C)
- **Change to the ruled fix** (upstream_defects.md, own commit): `destination => $server_facts['servername']` instead
  of `$server_facts['serverip']`. puppetlabs-firewall 8.3.0 resolves a hostname destination on the AGENT
  (`PuppetX::Firewall::Utility.host_to_ip`, `Resolv.each_address`: /etc/hosts, then DNS) and compares the resolved
  /32 with the installed rule (`insync?` → `host_to_mask`), so the rule carries the address the node resolves for
  its master's name.
- **Proof** (the class itself is not re-migrated here; a plain `Done` class waits for its re-migration):
  - the amended rule applied to the class in the worktree, uncommitted, then
    `test_class.sh --revert-first puppet_infrastructure::firewall_addon_hosting`: GREEN, meaning run 2 reached the
    master through the class's own `OUTPUT` drop policy and changed nothing (idempotent);
  - `iptables -S OUTPUT` on the node shows `-d 192.168.56.10/32 -p tcp --dport 8140 -j ACCEPT`;
  - the compiled catalog's `serverip` is 10.0.2.15, the address the old wording would have allowed.
  - Then the manifest is restored (`git restore`), the node reverted, and the evidence written into the entry.
- If the class cannot reach GREEN on the harness for another reason (a fixture or base gap), that reason is recorded
  and the proof falls back to the rule alone in a fixture manifest; the plan does not stop.

### Step 7 — documents (advisor, one commit)
- CLAUDE.md "Facts": NIC1 is NAT (internet and DNS through the laptop's current uplink), no longer bridged.
- The revert_node.sh header: the wlo1 lines.
- A DESIGN_DECISIONS entry (NAT, the step-0 fact list, facts B results, the serverip ruling change, new lab VMs on
  NAT per HQ G).
- The step 0 fact list (classes reading the VM's own IP or server facts), with any fixture consequence.

### Step 8 — acceptance on a phone hotspot ([HUMAN] + advisor)
1. **[HUMAN]** Salatiel connects the laptop to a phone hotspot (Wi-Fi to the hotspot's SSID; home Wi-Fi forgotten
   for the duration, or out of range). The VMs stay running across the switch (HQ E). Mobile data use: one
   `apt-get update` (tens of MB at most) plus the Forge check.
2. Advisor, in order; each must pass:
   ```bash
   nmcli -t -f active,ssid dev wifi | grep '^yes'                            # hotspot SSID, recorded; must differ from home (HQ E)
   ! ip route show default | grep -q "192\.168\.77\."                       # the laptop is really off the home LAN
   .codex_state/tools/revert_node.sh                                       # one revert (v4): NAT internet + DNS for apt, asserts
   .codex_state/tools/test_class.sh --compile-only puppet_infrastructure::dns_client   # one compile
   .codex_state/tools/test_class.sh --fixture guarded_exec                 # one fixture harness run on that fresh revert (NODE_FRESH yes, GREEN)
   ho puppet8master 192.168.56.10 'getent ahostsv4 forgeapi.puppet.com >/dev/null'    # master DNS follows the hotspot
   ```
   - **Facts on the hotspot (HQ B):** `facts` on both VMs, after the fixture run; hostname, fqdn and domain identical
     to step 0.
3. **[HUMAN]** Salatiel returns the laptop to the home Wi-Fi.
4. Advisor, back home (HQ E): the home SSID again; the master DNS check (`getent ahostsv4 forgeapi.puppet.com`) and
   one compile (`--compile-only puppet_infrastructure::dns_client`).

A failure stops the plan and is escalated with evidence; there is no automatic rollback (as in lab-network step 8).

### Step 9 — master snapshot (advisor; only after step 8 passes)
`.codex_state/tools/snapshot_master.sh P8MASTER_BASELINE_GREEN_v5 --note "since v4: NIC1 NAT (natdnshostresolver1
on); enp0s3 10.0.2.15 via DHCP; DNS 10.0.2.3"`.

Then, over `ho`: enp0s8 = .10, both names → .10 / .20, puppetserver active and 8140 running, and the enp0s3 / DNS
asserts of step 4. Then the lab lock is released.

Rollback: none needed (an added snapshot). Master v4 is kept until HQ rules.

### After acceptance (HQ F, G, J — in order)
1. **Bytes on NIC1 (HQ F), before the next batch** (tool change + tests, own commit): revert_node.sh records the bytes
   received on the node's NIC1 per revert (the interface counter after the restore's boot and package refresh), and
   test_class.sh records them per harness run (counter delta); `metrics.py close` folds them per class. They appear in
   the batch report, so HQ can decide on a package cache before the 23rd.
2. **New lab VMs on NAT (HQ G)** (tool change + tests, own commit): `lab_vm.sh start` refuses a p8lab-* VM whose NIC1
   is not NAT with the host resolver on.
3. Re-run user_base's Phase 3 checks (stale since its `uncovered` note) and have them reviewed.
4. Bring up p8lab-rhel9 while Salatiel is present (HQ 2026-11-16 items 4–5).
5. `/migrate-next 10` from openvpn_server.

## 5. What stays the same
- Lab control: host-only, the aliases, HostKeyAlias, the harness SSH source and the ACL fixtures.
- No change on the laptop: VirtualBox NAT needs nothing on the host.

## 6. HQ decisions (step review, 2026-11-16)
1. Steps approved as amended (§9); run now, with Salatiel present.
2. Node DNS: the node keeps its public resolvers.
3. Batch 4 ran first on the bridged network (done).

## 7. Risks
- **A network that blocks outbound DNS to public resolvers** (some captive or corporate Wi-Fi) breaks the node's DNS
  but not the master's. HQ kept the public resolvers; the hotspot proves them.
- **VirtualBox's NAT proxy and the host's systemd-resolved stub (127.0.0.53).** With `natdnshostresolver1 on`, the
  proxy resolves through the host's system resolver API, not by forwarding to 127.0.0.53, which is why the flag is
  required. Step 4 proves it at home; step 8 proves it on the hotspot. Non-A records (MX/TXT) through the proxy are
  recorded in step 4 (HQ D).
- **Fact changes (§2):** step 0 lists the classes affected before anything changes.

## 8. Execution record
| Step | Result | Evidence |
|---|---|---|

## 9. HQ step-review amendments (2026-11-16)
- **A.** No step depends on a bridged revert: the node goes to NAT from a manual restore of v3 (step 1, [HUMAN]);
  the checks of step 2 refresh the package lists that stay in v4; v4 is taken after a clean poweroff with the state
  token unchanged (step 3); revert_node.sh moves to v4 only after the master step (step 5). A failed step-2 check
  stops the plan with the revert script still on v3.
- **B.** hostname, fqdn and domain recorded on both VMs before, after and on the hotspot; identical all three times,
  pinned with the smallest change otherwise; ip 10.0.2.15 expected.
- **C.** `server_facts` and `serverip` in the step-0 grep; the ruled firewall_addon_hosting fix matches the address
  the node resolves for its master, with an idempotency proof and the upstream_defects.md entry updated (step 6).
- **D.** One non-A DNS query on the master, recorded; a failure is a noted limit.
- **E.** SSIDs recorded at home and on the hotspot (must differ); the VMs stay running across the switch; back home,
  the master DNS check and one compile again.
- **F.** Bytes received on the node's NIC1 per revert and per class in the metrics from the next batch.
- **G.** New `p8lab-*` VMs get the same NIC1 NAT setting.
- **H.** The snapshot take on ubuntu24-puppet8-Node is handed to Salatiel; the settings are not loosened.
- **I.** A commit touching `.codex_state/tools/` or the settings runs the full suite in the pre-commit hook (done,
  396274e).
- **J.** After acceptance: user_base's checks, p8lab-rhel9 bring-up with Salatiel present, then `/migrate-next 10`
  from openvpn_server.
- The whole plan runs under one lab lock.
