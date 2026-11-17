# nginx_base (done, 33 production node statements): modules-enabled included twice with puppet-nginx 8.4.0 (2026-11-17, batch 8)

**Status: needs an HQ ruling (a module-compatibility change to a done class). Found while migrating nginx_frontend_mail,
which is blocked on it (category 1). nginx_base's own GREEN and Phase 3 never saw it.**

## Evidence
- nginx_frontend_mail harness run 2 of the day (fresh node; nginx_base applied for the target with `my_configs =>
  {mail => true, stream => true, package_name => 'nginx-core'}`, see below): `Service[nginx]` restart failed;
  `nginx -t`: `module "ngx_http_geoip2_module" is already loaded in /etc/nginx/modules-enabled/50-mod-http-geoip2.conf:1`.
- The rendered /etc/nginx/nginx.conf has two includes of the same directory:
  `include /etc/nginx/modules-enabled/*.conf;` (the module's) and `include /etc/nginx/modules-enabled/*;` (nginx_base's).
- puppet-nginx 8.4.0 (the lab pin): params.pp's Debian override sets `include_modules_enabled => true`, and
  templates/conf.d/nginx.conf.erb:29 renders that include `if @include_modules_enabled or @mail`.
- nginx_base (release-0.9.10) passes `nginx_cfg_prepend => {'include' => '/etc/nginx/modules-enabled/*'}` in its
  default configs (nginx_base.pp:88 area). In production's puppet-nginx 0.15 the module had no such include, so
  nginx_base's prepend was the only one.
- **Why the lab missed it:** on Ubuntu 24.04 the `nginx` package carries no dynamic modules, so modules-enabled is empty
  and a double include loads nothing twice. nginx_base's comment (nginx_base.pp:81) assumes `nginx` is "a metapackage
  for nginx-core". That was true on older releases. On 24.04 `nginx-core` is the package that depends on
  libnginx-mod-{mail,stream,http-geoip2,…}; `nginx` alone does not.
- **Production risk (likely; not proven in the lab):** on a production node whose nginx has dynamic modules enabled
  (nginx-core and its libnginx-mod-* packages), the migrated nginx_base with puppet-nginx 8 would render both includes,
  and nginx would refuse to start. I have not checked which packages the production nginx frontends carry; one read
  (`ls /etc/nginx/modules-enabled` on a frontend) settles it.

## Options (HQ)
1. **Recommended:** a module-compatibility change in nginx_base: set `include_modules_enabled => true` in its default
   configs and drop its own `nginx_cfg_prepend` include. Exactly one include of modules-enabled results, from the
   module, on every OS and with `mail` on or off. Behaviour stays the baseline's intent: load the enabled modules.
   A re-migration of nginx_base, recorded in class_rulings.txt.
2. Keep nginx_base's prepend and set `include_modules_enabled => false`. This does not cover `mail => true`
   (the template includes on `@mail` regardless), so mail frontends would still double-include. Not recommended.
3. Leave it. nginx breaks on module-carrying nodes. Not recommended.

## For nginx_frontend_mail (blocked until the ruling)
- prod 0 node statements. Its lab fixture: a per-target base fixture (params/for/<target>/nginx_base.json, local)
  `my_configs => {mail => true, stream => true, package_name => 'nginx-core'}`.
  - `mail`/`stream`: puppet-nginx refuses a mailhost without the mail flag and renders no stream block without it.
  - `nginx-core`: on 24.04 it is the package that brings the mail and stream modules.
- **Documentation list, production cutover:** on Ubuntu 24.04, mail frontends need nginx_base's
  package_name nginx-core (or the libnginx-mod packages).
