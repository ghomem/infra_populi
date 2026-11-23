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
