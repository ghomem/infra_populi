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

---

# Second puppet-nginx 8 incompatibility: the stream block's access_log has no format (2026-11-17, after ruling 1)

**Status: needs an HQ ruling (a further module-compatibility change to nginx_base, beyond ruling 1).
nginx_frontend_mail is blocked on it again (category 1). Ruling 1 is done: nginx_base was re-migrated (f02baf8,
review PASS, Phase 3 ALL_PASS), and its 7 dependents were re-verified PASS.**

## Evidence
- **The run:** nginx_frontend_mail, revert-first harness, 2026-11-17 21:46Z (fresh node, nginx_base applied with
  `my_configs => {mail => true, stream => true, package_name => 'nginx-core'}`).
  - `Service[nginx]` restart failed: `[emerg] log format is not specified in /etc/nginx/nginx.conf:55`.
  - The modules-enabled include is now single (line 8), so ruling 1 holds.
- **The rendered stream block:**
  `stream { include /etc/nginx/conf.stream.d/*.conf; include /etc/nginx/streams-enabled/*; access_log /var/log/nginx/stream-access.log; }`
- **Where the line comes from:** puppet-nginx 8.4.0 templates/conf.d/nginx.conf.erb:419-421 always renders
  `access_log <stream_access_log>[ <stream_custom_format_log>]`. Its defaults are `stream_access_log =
  "${log_dir}/stream-access.log"` and `stream_custom_format_log = undef` (init.pp:260-261), so no format is rendered.
- **Why nginx refuses it:** nginx's stream `access_log` needs a format name, and the stream module has no default
  format (unlike http's `combined`). So `stream => true` with the module's defaults never starts.
- **Upstream:** 8.4.0 is the latest release and the template on master is unchanged.
- **What production renders:** production's puppet-nginx 0.15 (and 0.16) renders the stream block with the two
  includes only, and no access_log (templates/conf.d/nginx.conf.erb:229-236 at v0.15.0). Stream access logging was
  therefore off in production (nginx's stream default).

## Options (HQ)
1. **Recommended:** a module-compatibility change in nginx_base: add `stream_access_log => 'off'` to its default
   configs.
   - Stream nodes render `access_log off;`, which is what production does today: no stream access log.
   - Nodes without `stream` render no stream block, so nothing changes for them.
   - A node can still pass a path plus `stream_custom_format_log`/`stream_log_format` through my_configs.
   - It would be a second re-migration of nginx_base, re-verified with its dependents as for ruling 1, plus a Phase 3
     check that a stream node starts.
2. Leave nginx_base alone, and at cutover put `stream_access_log => 'off'` (or a format) into every stream frontend's
   my_configs.
   - The lab fixture would carry the same value.
   - The risk is a production frontend whose nginx refuses to start because the cutover note was missed.
3. Report it upstream (voxpupuli/puppet-nginx) in any case. A fix there would let option 1 be dropped later
   (Phase 5).

## Ruling A1 evidence (HQ 2026-11-18): `stream_access_log => 'off'` — the rendered nginx.conf before and after
- **Method:** `test_class.sh --compile-only --facts <debian|redhat> [--defaults] --file-digest /etc/nginx/nginx.conf <class>`
  on puppet8master, 2026-11-18, before (HEAD 5a1501a's nginx_base) and after (the ruled line added). The filter prints
  the sha256 and size of File['/etc/nginx/nginx.conf']'s rendered content, never the content (38c8d75).
- **Result:** byte-identical for nginx_base, hashman_web, nginx_frontend, nginx_frontend_domain, nginx_static,
  nginx_static_domain, ssl_nginx and ssl_nginx_domain, on Debian and RedHat facts (their fixtures; nginx_base and
  hashman_web also with defaults). Only nginx_frontend_mail (`stream => true`) changes, by 29 bytes: the stream
  block's `access_log /var/log/nginx/stream-access.log;` becomes `access_log off;`. Classes with required
  parameters have no defaults variant (the compile fails identically before and after: no value for a parameter).
- **Re-review scope (ruling A1):** nginx_base, and nginx_frontend_mail as a new migration. No other class's
  rendering changed.

```
before nginx_base debian fixtures sha256:d86ca9397952b7b6b19a8c46f6235e901b5ffe6dbfd7b5afba862ebb25a9ad7f bytes:1491
after nginx_base debian fixtures sha256:d86ca9397952b7b6b19a8c46f6235e901b5ffe6dbfd7b5afba862ebb25a9ad7f bytes:1491
before nginx_base debian defaults sha256:d86ca9397952b7b6b19a8c46f6235e901b5ffe6dbfd7b5afba862ebb25a9ad7f bytes:1491
after nginx_base debian defaults sha256:d86ca9397952b7b6b19a8c46f6235e901b5ffe6dbfd7b5afba862ebb25a9ad7f bytes:1491
before nginx_base redhat fixtures sha256:6a65401c654637e8806a68f2a0d6052fbfc0a291f0436a4660c51b8293986586 bytes:1488
after nginx_base redhat fixtures sha256:6a65401c654637e8806a68f2a0d6052fbfc0a291f0436a4660c51b8293986586 bytes:1488
before nginx_base redhat defaults sha256:6a65401c654637e8806a68f2a0d6052fbfc0a291f0436a4660c51b8293986586 bytes:1488
after nginx_base redhat defaults sha256:6a65401c654637e8806a68f2a0d6052fbfc0a291f0436a4660c51b8293986586 bytes:1488
before hashman_web debian fixtures sha256:d86ca9397952b7b6b19a8c46f6235e901b5ffe6dbfd7b5afba862ebb25a9ad7f bytes:1491
after hashman_web debian fixtures sha256:d86ca9397952b7b6b19a8c46f6235e901b5ffe6dbfd7b5afba862ebb25a9ad7f bytes:1491
before hashman_web debian defaults sha256:d86ca9397952b7b6b19a8c46f6235e901b5ffe6dbfd7b5afba862ebb25a9ad7f bytes:1491
after hashman_web debian defaults sha256:d86ca9397952b7b6b19a8c46f6235e901b5ffe6dbfd7b5afba862ebb25a9ad7f bytes:1491
before hashman_web redhat fixtures sha256:6a65401c654637e8806a68f2a0d6052fbfc0a291f0436a4660c51b8293986586 bytes:1488
after hashman_web redhat fixtures sha256:6a65401c654637e8806a68f2a0d6052fbfc0a291f0436a4660c51b8293986586 bytes:1488
before hashman_web redhat defaults sha256:6a65401c654637e8806a68f2a0d6052fbfc0a291f0436a4660c51b8293986586 bytes:1488
after hashman_web redhat defaults sha256:6a65401c654637e8806a68f2a0d6052fbfc0a291f0436a4660c51b8293986586 bytes:1488
before nginx_frontend debian fixtures sha256:d86ca9397952b7b6b19a8c46f6235e901b5ffe6dbfd7b5afba862ebb25a9ad7f bytes:1491
after nginx_frontend debian fixtures sha256:d86ca9397952b7b6b19a8c46f6235e901b5ffe6dbfd7b5afba862ebb25a9ad7f bytes:1491
before nginx_frontend redhat fixtures sha256:6a65401c654637e8806a68f2a0d6052fbfc0a291f0436a4660c51b8293986586 bytes:1488
after nginx_frontend redhat fixtures sha256:6a65401c654637e8806a68f2a0d6052fbfc0a291f0436a4660c51b8293986586 bytes:1488
before nginx_frontend_domain debian fixtures sha256:d86ca9397952b7b6b19a8c46f6235e901b5ffe6dbfd7b5afba862ebb25a9ad7f bytes:1491
after nginx_frontend_domain debian fixtures sha256:d86ca9397952b7b6b19a8c46f6235e901b5ffe6dbfd7b5afba862ebb25a9ad7f bytes:1491
before nginx_frontend_domain redhat fixtures sha256:6a65401c654637e8806a68f2a0d6052fbfc0a291f0436a4660c51b8293986586 bytes:1488
after nginx_frontend_domain redhat fixtures sha256:6a65401c654637e8806a68f2a0d6052fbfc0a291f0436a4660c51b8293986586 bytes:1488
before nginx_frontend_mail debian fixtures sha256:bdb97684bcc92f757d6712ac5f92d98427f36307fe94ff6d46db75376ca2e1e4 bytes:1683
after nginx_frontend_mail debian fixtures sha256:728f63bdbf957f72fd78c2c951113441ee2405236f41dfdb27b73e6c4afb20da bytes:1654
before nginx_frontend_mail redhat fixtures sha256:1f0035e1ee58e5aa87869612be3a68586a704276e99e8e12f9dfc18efd168d32 bytes:1680
after nginx_frontend_mail redhat fixtures sha256:f8bf9f1ac1bce245272dc9e2f2ada6d33d299040bf0178ec90145bd9c0e987da bytes:1651
before nginx_static debian fixtures sha256:d86ca9397952b7b6b19a8c46f6235e901b5ffe6dbfd7b5afba862ebb25a9ad7f bytes:1491
after nginx_static debian fixtures sha256:d86ca9397952b7b6b19a8c46f6235e901b5ffe6dbfd7b5afba862ebb25a9ad7f bytes:1491
before nginx_static redhat fixtures sha256:6a65401c654637e8806a68f2a0d6052fbfc0a291f0436a4660c51b8293986586 bytes:1488
after nginx_static redhat fixtures sha256:6a65401c654637e8806a68f2a0d6052fbfc0a291f0436a4660c51b8293986586 bytes:1488
before nginx_static_domain debian fixtures sha256:d86ca9397952b7b6b19a8c46f6235e901b5ffe6dbfd7b5afba862ebb25a9ad7f bytes:1491
after nginx_static_domain debian fixtures sha256:d86ca9397952b7b6b19a8c46f6235e901b5ffe6dbfd7b5afba862ebb25a9ad7f bytes:1491
before nginx_static_domain redhat fixtures sha256:6a65401c654637e8806a68f2a0d6052fbfc0a291f0436a4660c51b8293986586 bytes:1488
after nginx_static_domain redhat fixtures sha256:6a65401c654637e8806a68f2a0d6052fbfc0a291f0436a4660c51b8293986586 bytes:1488
before ssl_nginx debian fixtures sha256:d86ca9397952b7b6b19a8c46f6235e901b5ffe6dbfd7b5afba862ebb25a9ad7f bytes:1491
after ssl_nginx debian fixtures sha256:d86ca9397952b7b6b19a8c46f6235e901b5ffe6dbfd7b5afba862ebb25a9ad7f bytes:1491
before ssl_nginx redhat fixtures sha256:6a65401c654637e8806a68f2a0d6052fbfc0a291f0436a4660c51b8293986586 bytes:1488
after ssl_nginx redhat fixtures sha256:6a65401c654637e8806a68f2a0d6052fbfc0a291f0436a4660c51b8293986586 bytes:1488
before ssl_nginx_domain debian fixtures sha256:d86ca9397952b7b6b19a8c46f6235e901b5ffe6dbfd7b5afba862ebb25a9ad7f bytes:1491
after ssl_nginx_domain debian fixtures sha256:d86ca9397952b7b6b19a8c46f6235e901b5ffe6dbfd7b5afba862ebb25a9ad7f bytes:1491
before ssl_nginx_domain redhat fixtures sha256:6a65401c654637e8806a68f2a0d6052fbfc0a291f0436a4660c51b8293986586 bytes:1488
after ssl_nginx_domain redhat fixtures sha256:6a65401c654637e8806a68f2a0d6052fbfc0a291f0436a4660c51b8293986586 bytes:1488
```
