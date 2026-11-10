# Phase 3 pilots — authoring report (2026-11-10)

**Status: check sets authored and validated. NOT RUN.** HQ scheduled the pilot runs after the lab-network change,
as its canary (`escalations/lab-network-static.md`, stopped for HQ review). The only node contact was:
- the read-only look at the clean node's sshd and tools, listed under shared research below;
- one read-only transport smoke test of the runner (`id -u` and `sshd -T | grep port` via `sudo -n bash -s` on stdin;
  node state token unchanged).

Runner: `.codex_state/tools/phase3.py` (tests: `tests/test_phase3.py`, 39). Usage: CLAUDE.md "Phase 3 checks".

## Authoring minutes (wall clock, measured)
| class | checks | negative controls | invariants | baseline references | authoring (class-specific) |
|---|---:|---:|---:|---:|---:|
| backup_rsnapshot | 5 | 5 | 0 | 12 | 0.7 min (15:58:20Z → 15:59:02Z) |
| ssh_secure | 14 | 13 | 1 | 28 | 1.4 min (15:59:21Z → 16:00:44Z, includes a runner fix) |
| nginx_static_domain | 8 | 8 | 0 | 19 | 1.3 min (16:00:52Z → 16:02:11Z) |
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
4. **nginx_static_domain: the fixture certificate does not name the fixture domain.** It is the throwaway p8test PKI
   (RSA 2048, SAN p8test.invalid / *.p8test.invalid / star.example.com). The checks compare the served certificate's
   fingerprint with the deployed bundle, not names.
5. **nginx_static_domain: the baseline cipher string has an empty element.** `${prefix}:${additional}:${suffix}` with
   no additional ciphers renders as `…:ECDHE-RSA-AES256-SHA::!DSS:!EXPORT`. It was accepted at GREEN; `nginx -t` and
   the handshake checks will confirm OpenSSL ignores it.
6. **The validator caught one authoring error before any run.** nginx_base.pp:38 was the local line (the migration
   header shifts lines by 2); the baseline line is 36. derived_from binds to the pin, not to the local tree.
7. **backup_rsnapshot: probes are read-only, so a real backup is not executed.** `rsnapshot -t daily` (test mode)
   shows the planned rsync instead. Executing a snapshot would be the first exercise-type (mutating) probe; that is a
   rule decision for HQ (the node is reverted before every run, so it is safe to allow).

## Next (after the network change)
For each pilot:
1. `phase3.py run <class>`;
2. the reviewer with `<class> --phase3`;
3. commit the results, the review, and this report updated with the run findings.
