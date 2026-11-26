# nginx_default_removal: authoring notes (the comments of .codex_state/checks/nginx_default_removal.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::nginx_default_removal (class; node ubuntu; no parameters, no required
# base). The class removes the default site that Ubuntu's nginx package enables. It does not install nginx, so the
# checks install the package (as nginx_base does in production), which enables the default site, and let the next
# agent run remove it.
  # 2026-11-18 authoring correction (run 1, 20261118T214739Z): the welcome page says "Welcome to nginx" in its title and
  # its heading, so the count was 2; the heading alone is counted now.
```
