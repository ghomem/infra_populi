# Lab network: NIC1 bridged → NAT — plan for HQ review (2026-11-16)

**Status: PLAN ONLY. STOPPED FOR HQ REVIEW. Nothing below has been executed.** The only commands run so far were
reads: VBoxManage `showvminfo`, `resolvectl` on the laptop and the master.

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
- **DNS, node.** The static 1.1.1.1/8.8.8.8 keeps working through NAT and does not involve the home LAN. Option for
  HQ (§6.2): switch it to 10.0.2.3 for the same behaviour as the master. That changes the node baseline's
  resolv.conf (snapshot content), so I recommend keeping the public resolvers and letting the acceptance test prove
  them on the hotspot.
- **Unchanged:** NIC2 host-only (lab control), the harness SSH source 192.168.56.1, `/etc/hosts` on both VMs, the
  certificate (name-only SANs), and puppetserver.
- **The NIC1 attachment is part of the VM configuration, so it lives in snapshots.** Restoring node v3 brings back
  NIC1 bridged, which is also the node's rollback. The node therefore needs a new baseline, P8NODE_BASELINE_GREEN_v4;
  the master gets P8MASTER_BASELINE_GREEN_v5 after acceptance.
- **Retention:** node v2 and master v3 stay through batch 4 (HQ); node v3 and master v4 are kept until HQ rules.
- **Side effect to expect:** the facts change. `networking.ip` / `ipaddress` on both VMs becomes 10.0.2.15 instead of
  192.168.77.x (enp0s3 is the primary interface). A class that renders the node's own IP into a file would render a
  different value, which is fixture context, not a regression. Step 0 lists the done classes that read these facts.

## 3. Rules kept
- **Master:** never restored and never hard powered off. Its NIC change needs a power cycle, which is human-only
  (ACPI).
- **[HUMAN]:** every `modifyvm` / `controlvm nic*` (VM configuration), and the network switch of the laptop itself.
- **Every check proves the path:** the host-only helper `ho` (escalations/lab-network-static.md §4). Internet and
  DNS checks assert addresses: no `192.168.77.` address, route or DNS server may remain on a VM.
- **A failed verification stops the plan.** Each step lists its rollback.

## 4. Steps
`ho` is the helper from lab-network-static.md: `-S none`, plus an in-session `$SSH_CONNECTION` assert.

### Step 0 — preflight (advisor, read-only)
```bash
test -z "$(git -C ~/work/infra_populi status --porcelain)"; ! pgrep -f '[t]est_class.sh|[c]odex exec|[r]eview_class.py|[p]hase3.py'
ho puppet8master 192.168.56.10 true && ho puppet8node 192.168.56.20 true
VBoxManage showvminfo Ubuntu24-puppet8-Master --machinereadable | grep -qx 'nic1="bridged"'
VBoxManage showvminfo ubuntu24-puppet8-Node   --machinereadable | grep -qx 'nic1="bridged"'
ho puppet8master 192.168.56.10 'curl -sS -o /dev/null -w "%{http_code}" https://forgeapi.puppet.com/v3/modules/puppetlabs-stdlib' # 200 today
git -C ~/work/infra_populi grep -nE "networking'\]\['ip|\\\$::ipaddress|\\\$ipaddress\b|@ipaddress" -- manifests templates   # list, for §2
```
Rollback: none.

### Step 1 — node trial on NAT (the node is disposable; nothing persists)
1. Advisor: `.codex_state/tools/revert_node.sh` (v3, bridged).
2. **[HUMAN]**:
   ```bash
   VBoxManage controlvm ubuntu24-puppet8-Node poweroff
   VBoxManage modifyvm ubuntu24-puppet8-Node --nic1 nat --natdnshostresolver1 on
   VBoxManage startvm ubuntu24-puppet8-Node --type headless
   ```
3. Verify (advisor):
   ```bash
   until ho puppet8node 192.168.56.20 true 2>/dev/null; do sleep 3; done          # host-only path unchanged (timeout 180 s)
   ho puppet8node 192.168.56.20 'ip -br addr show enp0s3 | grep -q " 10.0.2.15/24" && ip route show default | grep -q "via 10.0.2.2 dev enp0s3"'
   ho puppet8node 192.168.56.20 '! ip -4 addr | grep -q "192\.168\.77\." && ! grep -q "192\.168\.77\." /etc/resolv.conf'
   ho puppet8node 192.168.56.20 'getent ahostsv4 archive.ubuntu.com >/dev/null'   # DNS through NAT
   ho puppet8node 192.168.56.20 'sudo -n timeout 180 apt-get -q update >/dev/null' # internet through NAT
   ho puppet8node 192.168.56.20 "timeout 5 bash -c 'exec 3<>/dev/tcp/puppet8master.example.com/8140'"
   ```

Rollback: `.codex_state/tools/revert_node.sh`. Restoring v3 restores NIC1 bridged; run it at the end of the step either
way.

### Step 2 — [HUMAN] master NIC1 → NAT
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
.codex_state/tools/test_class.sh --compile-only puppet_infrastructure::dns_client
```
Rollback [HUMAN]: ACPI shutdown, then `VBoxManage modifyvm Ubuntu24-puppet8-Master --nic1 bridged --bridgeadapter1
wlo1 --natdnshostresolver1 off`, then `startvm`.

### Step 3 — node baseline P8NODE_BASELINE_GREEN_v4 (NAT in the machine configuration)
1. Advisor: `revert_node.sh` (v3). Record the state token; run only non-mutating checks; then a clean poweroff
   (`ssh puppet8node 'sudo -n systemctl poweroff'`, wait for `poweroff`), as in lab-network-static.md step 9 (no
   agent run).
2. **[HUMAN]** (node powered off): `VBoxManage modifyvm ubuntu24-puppet8-Node --nic1 nat --natdnshostresolver1 on`.
3. Advisor: `VBoxManage snapshot ubuntu24-puppet8-Node take P8NODE_BASELINE_GREEN_v4 --description "v3 + NIC1 NAT
   (natdnshostresolver1 on); disk = v3 + one clean boot, no agent run; repo <sha>"`.
4. Advisor, tool change (tests + shellcheck, own commit). revert_node.sh: `NODE_SNAPSHOT=P8NODE_BASELINE_GREEN_v4`.
   The post-restore asserts gain:
   - enp0s3 holds 10.0.2.15/24 with the default route via 10.0.2.2;
   - no `192.168.77.` address on the node.

   The existing `apt-get update` keeps proving internet and DNS.
5. Verify: two consecutive real reverts, then `test_class.sh --revert-first --fixture guarded_exec` GREEN.

Rollback: `git revert` the step-3 commit (back to v3, bridged). v4 stays as an unused snapshot until HQ rules.

### Step 4 — documents (advisor, one commit)
- CLAUDE.md "Facts": NIC1 is NAT (internet and DNS through the laptop's current uplink), no longer bridged.
- The revert_node.sh header: the wlo1 lines.
- A DESIGN_DECISIONS entry.
- The step 0 fact list (classes reading the VM's own IP), with any fixture consequence.

### Step 5 — acceptance on a phone hotspot ([HUMAN] + advisor)
1. **[HUMAN]** Salatiel connects the laptop to a phone hotspot (Wi-Fi to the hotspot's SSID; home Wi-Fi forgotten
   for the duration, or out of range). Mobile data use: one `apt-get update` (tens of MB at most) plus the Forge
   check.
2. Advisor, in order; each must pass:
   ```bash
   ! ip route show default | grep -q "192\.168\.77\."                       # the laptop is really off the home LAN
   .codex_state/tools/revert_node.sh                                       # one revert: NAT internet + DNS for apt, host-only asserts
   .codex_state/tools/test_class.sh --compile-only puppet_infrastructure::dns_client   # one compile
   .codex_state/tools/test_class.sh --fixture guarded_exec                 # one fixture harness run on that fresh revert (NODE_FRESH yes, GREEN)
   ho puppet8master 192.168.56.10 'getent ahostsv4 forgeapi.puppet.com >/dev/null'    # master DNS follows the hotspot
   ```
3. **[HUMAN]** Salatiel returns the laptop to the home Wi-Fi.

A failure stops the plan and is escalated with evidence; there is no automatic rollback (as in lab-network step 8).

### Step 6 — master snapshot (advisor; only after step 5 passes)
`.codex_state/tools/snapshot_master.sh P8MASTER_BASELINE_GREEN_v5 --note "since v4: NIC1 NAT (natdnshostresolver1
on); enp0s3 10.0.2.15 via DHCP; DNS 10.0.2.3"`.

Then, over `ho`: enp0s8 = .10, both names → .10 / .20, puppetserver active and 8140 running, and the enp0s3 / DNS
asserts of step 2.

Rollback: none needed (an added snapshot). Master v4 is kept until HQ rules.

## 5. What stays the same
- Lab control: host-only, the aliases, HostKeyAlias, the harness SSH source and the ACL fixtures.
- No change on the laptop: VirtualBox NAT needs nothing on the host.

## 6. Decisions for HQ
1. **Approve steps 0–6.** Steps 1–3 and 5 contain [HUMAN] parts for Salatiel.
2. **Node DNS:** keep the static public resolvers (recommended; the hotspot proves them), or switch the node to the
   NAT DNS 10.0.2.3 inside the v4 baseline.
3. **When:** batch 4 runs first on the current network. NAT changes the VMs' own IP facts, and running it after the
   batch keeps batch 4 comparable.

## 7. Risks
- **A network that blocks outbound DNS to public resolvers** (some captive or corporate Wi-Fi) breaks the node's DNS
  but not the master's. §6.2 covers it.
- **VirtualBox's NAT proxy and the host's systemd-resolved stub (127.0.0.53).** With `natdnshostresolver1 on`, the
  proxy resolves through the host's system resolver API, not by forwarding to 127.0.0.53, which is why the flag is
  required. Step 2 proves it at home; step 5 proves it on the hotspot.
- **Fact changes (§2):** step 0 lists the classes affected before anything changes.
