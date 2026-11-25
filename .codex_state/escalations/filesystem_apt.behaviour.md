# filesystem_apt — behaviour finding: a custom apt_surface_list is not joined (OPEN: one clear fix, queued as a policy-B local change after the sweep)

Found by the sweep's variant run `custom` (results/filesystem_apt/.json): with apt_surface_list ["vim", "less"] the
surface script renders `SURFACE="["vim", "less"]"`. At the baseline, manifests/filesystem_apt.pp:59-61 assigns the
array itself (`$_apt_surface_list = $apt_surface_list`), unlike the server and desktop lists, which are joined with
spaces (lines 52-58); the template writes `SURFACE="<%= @_apt_surface_list %>"` (apt-update-surface.sh.erb:5), which is
the array's text. The shell then reads SURFACE as `[vim,` and `less]`, so the script updates neither package.

Production use: no production node statement sets apt_surface_list on filesystem_apt or node_base
(diagnosis/fleet_variant_usage.md); node_base forwards its default [] (node_base.pp:117-122). So the defect does not
reach production today, but a custom list cannot work.

One clear fix: `$_apt_surface_list = join($apt_surface_list, " ")`, as for the other two lists. Under the run rule
this is a policy-B local change (before evidence: the run above; after: the same check). Queued after the sweep.

## 2026-11-25: second item, ENVIRONMENT (escalated): the dist-upgrade check cannot finish within 600 s on this uplink
Found by the before run of the surface-list local change (results/filesystem_apt/20261125T214543Z-author): the base
run's `the-full-update-script-leaves-nothing-to-upgrade` failed with action rc 124. phase3.py ended the action at its
600 s limit (a mutating check's `timeout` may not exceed 600 s, phase3.py:611) while apt-update-dist.sh was still
running `apt-get dist-upgrade`; the effect then read "199 upgraded, 20 newly installed" still pending. Measured on the
node afterwards (a later variant's fresh revert): 250 upgraded and 27 newly installed pending, 986 MB in 277 files
(`apt-get --print-uris`). The same check passed on 2026-11-23 in four author and reviewer runs (0 left to upgrade):
the node baseline (v5 = v4 + the paravirt provider, packages as v4 had them) falls further behind the Ubuntu archive
every day, and the downloads go through this uplink. The class's script does what the baseline says; the backlog is
the lab's.

Options (more than one reasonable design, so escalated under the run rule; the run continues):
- **A:** a node baseline with the archive's updates applied (P8NODE_BASELINE_GREEN_v6), taken by Salatiel. It moves
  every class's clean state forward, and every set would then run against it.
- **B:** let a mutating check's action run longer than 600 s (a phase3.py change with tests), and give this check the
  time the uplink needs.
- **C:** record the check as environment-limited on this uplink for the approval report, keeping its 2026-11-23
  passes as the evidence that the script works.
Recommendation: C now (the 2026-11-23 passes show the behaviour; nothing in the class changed since), and A at the
next baseline Salatiel takes for other reasons.
