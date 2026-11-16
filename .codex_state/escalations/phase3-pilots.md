# Phase 3 pilots — authoring report (2026-11-10)

**Status (2026-11-16): all three pilots RUN on the host-only network as step 8 of the lab-network canary. Each ends
ALL_PASS, and the reviewer (`--phase3`) reproduced each one: PASS, derivation ok, no findings.** Two pilots needed a
second author run because of authoring errors in my probes (below), not behaviour findings. Original pre-run status:
check sets authored and validated, not run. The only node contact was:
- the read-only look at the clean node's sshd and tools, listed under shared research below;
- one read-only transport smoke test of the runner (`id -u` and `sshd -T | grep port` via `sudo -n bash -s` on stdin;
  node state token unchanged).

Runner: `.codex_state/tools/phase3.py` (tests: `tests/test_phase3.py`, 39). Usage: CLAUDE.md "Phase 3 checks".

## Authoring minutes (wall clock, measured)
| class | checks | negative controls | invariants | baseline references | authoring (class-specific) |
|---|---:|---:|---:|---:|---:|
| backup_rsnapshot | 6 (1 mutating) | 6 | 0 | 15 | 1.0 min (15:58:20Z → 15:59:02Z; +0.3 min 16:17Z, mutating check) |
| ssh_secure | 14 | 13 | 1 | 28 | 1.4 min (15:59:21Z → 16:00:44Z, includes a runner fix) |
| nginx_static_domain | 9 | 9 | 0 | 23 | 2.0 min (16:00:52Z → 16:02:11Z; +~0.7 min 16:21:30Z → 16:22:16Z, name check) |
| shared research for all three | | | | | ~5 min (15:52Z → 15:57Z): baselines, fixtures, read-only clean-node sshd/tools, fixture certificate type |

Building the runner and its tests (15:56Z → 15:58Z, then fixes) is engine time and is not counted above. Each check
set's `authoring` block carries its own numbers and method.

## Findings so far (authoring; run findings will be added after the canary)
1. **ssh_secure: `Protocol 2` and `UsePrivilegeSeparation yes` (baseline lines 57, 77) are deprecated and ignored
   by OpenSSH ≥ 7.5.** The node runs 9.6p1, so these options have no behaviour to test. Upstream carries dead
   configuration. Phase 5 candidate, not a Phase 1 issue.
2. **ssh_secure: the clean node's sshd already matches 12 of the class's options** (Ubuntu 24.04 defaults). They
   form one `invariant` check with its reason. The remaining 13 checks discriminate: on the clean node, KEX, ciphers,
   MACs, password auth (`yes`), root login (`without-password`), ClientAlive (0/3), AllowGroups (absent), host-key
   order, moduli (different file) and the ssh_in group (absent) all differ.
3. **ssh_secure: a run-time risk the checks will expose.** Ubuntu 24.04 ships `/etc/ssh/sshd_config.d/*.conf`
   (cloud-init can set `PasswordAuthentication yes` there). If saz-ssh's rendered sshd_config keeps the `Include`
   line above the class's options, sshd's first-value-wins rule lets the drop-in override the class.
   `password-auth-off` tests the EFFECTIVE value (`sshd -T`) and the server's offered methods, so either outcome is
   reported as a fact, not assumed.
4. **nginx_static_domain: the fixture certificate did not name the fixture domain** (throwaway p8test PKI, SAN
   p8test.invalid / *.p8test.invalid / star.example.com). Resolved per HQ: master_fixtures.sh pki v2 adds
   `p8test.example.com` and `*.p8test.example.com` and was applied to the master on 2026-11-10 16:21Z (new CA and server
   cert, `openssl verify` OK, a second run reports OK). The new check `https-name-verifies` verifies the name; the
   fingerprint check stays.
5. **nginx_static_domain: the baseline cipher string has an empty element.** `${prefix}:${additional}:${suffix}` with
   no additional ciphers renders as `…:ECDHE-RSA-AES256-SHA::!DSS:!EXPORT`. It was accepted at GREEN; `nginx -t` and
   the handshake checks will confirm OpenSSL ignores it.
6. **The validator caught one authoring error before any run.** nginx_base.pp:38 was the local line (the migration
   header shifts lines by 2); the baseline line is 36. derived_from binds to the pin, not to the local tree.
7. **backup_rsnapshot: a real backup now runs.** HQ allowed mutating probes on 2026-11-10: opt-in per check, the
   change declared, run after all read-only probes pass, never on the master, the evidence is the effect.
   `daily-backup-executes` runs the cron's own command once and passes only if `daily.0` holds a byte-identical
   `/etc/hostname`. It adds 0.3 min to the class's authoring time (now 1.0 min).

## HQ instructions for the runs (2026-11-10)
- **If ssh_secure's `password-auth-off` shows password authentication enforced ON** (effective `sshd -T` value `yes`,
  or the server offering `password`): write it up as an upstream defect, with the sshd_config.d drop-in evidence
  (which file, which line, and the rendered sshd_config's `Include` position), and flag it to Salatiel directly, not
  only in this report.
- **Fixture PKI:** the server certificate gains the fixture domain SAN (`p8test.example.com`) through
  master_fixtures.sh (pki v2), so name-based TLS verification becomes possible.


## Run results (2026-11-16, host-only network, NODE_FRESH yes on every apply)
| class | author runs | final | reviewer | results / review |
|---|---|---|---|---|
| backup_rsnapshot | 2: run 1 FINDINGS (authoring error in daily-plan) → corrected → run 2 ALL_PASS 6/6 | ALL_PASS, incl. 1 real `rsnapshot daily` | PASS (reproduced) | results/backup_rsnapshot/20261116T113012Z, T113256Z, T113446Z-reviewer; reviews/…/T113635Z |
| ssh_secure | 1: ALL_PASS 14/14 | ALL_PASS | PASS (reproduced) | results/ssh_secure/20261116T113657Z, T113845Z-reviewer; reviews/…/T114031Z |
| nginx_static_domain | 2: run 1 FINDINGS (authoring error in https-name-verifies) → corrected → run 2 ALL_PASS 9/9 | ALL_PASS | PASS (reproduced) | results/nginx_static_domain/20261116T114053Z, T114355Z, T114642Z-reviewer; reviews/…/T114846Z |

Every clean phase held: all 28 negative controls failed on the reverted node, and the one invariant passed. Every
first run's results are kept (append-only), with the correction and its minutes recorded in the check file.
Final authoring minutes: backup_rsnapshot 1.5, ssh_secure 1.4, nginx_static_domain 3.0.

## Findings from the runs
8. **Authoring error, backup_rsnapshot `daily-plan`.** rsnapshot test mode prints the backup point as `/etc/`, the
   destination as `daily.0//etc` and a trailing space; my expectation was too literal. The behaviour was as derived.
   The corrected regex also asserts that the destination ends in `etc`.
9. **Authoring error, nginx_static_domain `https-name-verifies`, and a lesson for check design.**
   - The probe anchored OpenSSL 3's indented `Verify return code` line at column 0, so it matched nothing.
   - The obvious fix would NOT have discriminated: OpenSSL 3.0.13 prints `Verify return code: 0 (ok)` even for a
     handshake aborted on `hostname mismatch`.
   - That surfaced only because I ran the fixed probe against a wrong hostname. The clean-node negative control cannot
     catch a probe that also passes on a WRONG configuration (on the clean node nothing listens, so any probe fails).
   - The probe now reads the top-level `Verification: OK | Verification error: …` line. Three cases were tested: the
     right name passes, a wrong name fails, and no listener fails.
   - Proposal for HQ: an optional per-check `mismatch` control (the same probe with one value deliberately wrong,
     which must fail on the applied node), mandatory for TLS/name checks.
10. **Observation, ssh_secure: password authentication is enforced off, so HQ's upstream-defect contingency is not
    triggered.**
    - Clean node: effective `yes`, offers `publickey,password`. Applied: `no`, offers `publickey` only.
    - The cloud-init drop-in `/etc/ssh/sshd_config.d/50-cloud-init.conf` (`PasswordAuthentication yes`) is still
      present, but the sshd_config rendered by saz-ssh has no `Include` line, so sshd ignores every drop-in.
    - That is why the class wins here. It also means the class silently disables all of `sshd_config.d` (upstream
      behaviour, recorded for Phase 5 consideration, not a defect).
11. **Observation, backup_rsnapshot: the snapshot of `/etc` lands at `daily.0/etc/etc/…`** (`backup /etc ./etc` plus
    rsnapshot's `--relative`). Restores must use that nested path. Upstream behaviour.
12. **Confirmed, nginx_static_domain:**
    - The baseline cipher string's empty element (`::`, finding 5) is harmless: `nginx -t` OK, handshakes OK.
    - The server's order wins: DHE-RSA-AES128-GCM-SHA256 with `Server Temp Key: DH, 2048 bits` over a client-preferred
      ECDHE suite, and the ECDHE curve is prime256v1.
    - `/` answers 403 with no listing (autoindex off, no index file).
