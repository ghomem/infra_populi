# Behaviour suite

This suite checks what each class of the `puppet_infrastructure` module *does* on a machine, not only that it
compiles. For each class, a set says what the class is for, what can be observed on a node once it has been applied,
and how to probe that. The runner checks a fresh node before the class is applied, applies the class twice, and checks
the node again.

```
spec/behaviour/
  checks/<class>.yml     one set per class
  kinds.yml              the node kinds a set can ask for (OS family, capabilities, tooling)
  fixtures/params/       fake parameter values for the classes (see "Fixtures")
  fixtures/node/         stand-ins for services a test node does not run
  probe_helpers.sh       shell helpers every probe can use
  lib/behaviour/         the runner, the validator and the placeholder renderer
  run                    the command line
  tests/                 the suite's own tests (pytest)
```

## A set

```yaml
class: filesystem_lib64
purpose: 'What the class is for, in a sentence or two (at least 40 characters).'
outcomes:                       # the purpose as things you can observe
- outcome: /usr/lib64/nagios is a link to /usr/lib/nagios
  from: manifests/filesystem_lib64.pp:5-15
  checks: [lib64-nagios-is-a-link-to-lib-nagios]
- outcome: something no check covers yet
  from: manifests/x.pp:3
  uncovered:
    why: why it cannot be checked here
    lifted_by: 'capability: a mail relay'   # or a node kind from kinds.yml, or accepted_gap: <reason>
checks:
- id: lib64-nagios-is-a-link-to-lib-nagios
  what: what the check shows, in words
  control: negative             # must FAIL on the fresh node (proves the class did it); or invariant: must PASS
  probe: |                      # a bash script, run as root on the node
    readlink /usr/lib64/nagios
  expect:
    rc: 0
    stdout: \A/usr/lib/nagios\n\Z   # a Python regular expression over the probe's output
apply:                          # how the run builds the catalog
  resource_type: class          # or define (with title:)
  node: ubuntu                  # a kind from kinds.yml
  catalog:
    Debian:                     # per OS family: the module's base classes (`external:`), then this module's
    - class: filesystem_lib64   # classes, the class under test last
```

Every set needs at least one negative control: a check that fails on a fresh node and passes after the class is
applied. Without one, the set cannot tell the class's work from what the node already had.

Other parts of a set, all optional:

| key | what it does |
|---|---|
| `mutates:` + `effect:` on a check | The probe changes the node (it installs a client, sends a mail, ...). `effect` is a read-only probe that judges the result. On the fresh node only the effect runs, and mutating checks run only after every read-only check has passed. |
| `timeout:` | Seconds (1-600) for a mutating check's action. |
| `mismatch:` on a check | `{varies: what, probe: ...}`: the same probe with one value deliberately wrong. It must fail, or the check does not discriminate. A probe that asks a tool to judge a name, user, key or cipher needs one. |
| `host: peer` on a check | The probe runs on the set's second node. |
| `peer:` | `{kind:, why:, files: [paths]}`: a second fresh node. The listed files are copied from the node under test to `/run/p8test-from-node/` on the peer. |
| `peer_agent:` | `{after: <check id>, certname: p8test-...}`: after that check, the peer runs a Puppet agent against the node under test (for classes that make a Puppet server). |
| `node_agent:` | `{after: <check id or ids>}`: one more Puppet run on the node after that check. |
| `session:` | `{user: p8testuser, desktop: plasma, why:}`: a desktop login before the applied phase, with two Puppet runs while it is up. |
| `variants:` | `[{name, why, node?, params?}]`: more runs on fresh nodes, with another node kind or another params fixture. Checks with `variant: <name>` run only there. |
| `deferred:` | `{needs: second-node\|browser\|rhel\|desktop, why}`: the set cannot run yet. |
| `derived_from:` | Provenance: the lines of the class a check was written from. The validator ignores it. |

### Placeholders

A set never names a real machine. It writes the run's values as placeholders, and the runner fills them in:

| placeholder | value |
|---|---|
| `{{NODE_NAME}}`, `{{NODE_ADDR}}` | the node under test: its short host name and the address the runner reaches it at |
| `{{NODE_PRIMARY_ADDR}}` | the node's primary address as Facter reports it (`networking.ip`) |
| `{{NODE_NETWORK}}` | the network address of the node's /24 |
| `{{PEER_NAME}}`, `{{PEER_ADDR}}` | the second node |
| `{{SERVER_NAME}}`, `{{SERVER_HOST}}`, `{{SERVER_ADDR}}` | the Puppet server: full name, short name, address |
| `{{CONTROLLER_ADDR}}` | the address the node sees the runner's ssh connection come from |
| `{{LOCALDIR}}` | the site's local directory on the node |
| `{{NODE:<kind>}}`, `{{ADDR:<kind>}}` | another machine of that kind (`--other`) |
| `{{SITE:<name>}}` | a site's own record, cited in prose only. A run never needs it. |

Forms: `{{NAME|re}}` is the value escaped for a regular expression, and `{{ADDR+N}}` is an address N above it in the
same /24. Node scripts of a set with a peer also get the peer's address as the shell variable `$PEER_ADDR`.

### Probes

A probe is a bash script run as root on the node (or on the peer), with `probe_helpers.sh` loaded first. Use a helper
wherever one fits:

| helper | prints |
|---|---|
| `p8_count PATTERN [FILE...]` | the number of lines matching an extended regex (stdin when no file is given) |
| `p8_listening PORT [tcp\|udp]` | the local addresses listening on the port, one per line |
| `p8_tcp HOST PORT [TIMEOUT] [SOURCE]` | `open` when a TCP connection is accepted |
| `p8_http URL [CURL_ARGS...]` | the HTTP status code (`000` when nothing answers) |
| `p8_service UNIT` | `<active state> <enabled state>`, e.g. `active enabled` |
| `p8_digest FILE...` | `<path> <owner>:<group> <mode> <sha256>` per file, or `<path> absent` |
| `p8_rc COMMAND [ARGS...]` | the command's first output line, then `rc=<exit code>` |
| `p8_tls HOST PORT SERVERNAME VERSION` | `accepted` when a handshake with that TLS version succeeds |
| `p8_established HOST PORT` | the number of established TCP connections to HOST:PORT |
| `p8_hold HOST PORT SECONDS [SOURCE]` | holds a TCP connection open (a mutating check's action only) |

The exact contract of each helper is in the comment above it in `probe_helpers.sh`.

A probe must not reach a machine other than the node and its peer, copy files between hosts, or run Puppet. A
read-only probe must not change the node. `./run --validate` enforces this.

## Running a set

```
./run --validate                       # every set, no node needed
./run --manifest <class>               # the manifest a run would apply
./run --node ubuntu=admin@203.0.113.20 --server puppet.example.test@203.0.113.10 <class>
./run --provider ./my-provider --apply local --modulepath /etc/puppetlabs/code/modules <class> [<class> ...]
```

A run does the following:

1. Takes a **fresh** node of the set's kind, and a fresh peer when the set has one.
   - With `--provider <cmd>`, the runner asks for a node with `<cmd> fresh <kind>`, which prints `{"dest": "<ssh destination>", "addr": "<address>"}` as JSON, and lets it go with `<cmd> release <dest>`.
   - With `--node <kind>=<dest>@<addr>`, the node you name is used once: the runner marks it and refuses a marked node.
2. **CLEAN phase**: runs every check on the untouched node. Each negative control must fail and each invariant must pass. Otherwise the set is INVALID.
3. **Applies** the class twice. The second run must change nothing, except the `expected_run2_events` the set's `apply:` names. Three modes:
   - `--apply agent` (the default): the node's Puppet agent, against a server that serves the module. `--classify <cmd>` is called as `<cmd> <node name> <manifest file>` so the server gives the node that manifest.
   - `--apply local`: `puppet apply` on the node, with the modules already under `--modulepath`. A set that needs a server declares `apply: {requires: [server], requires_why: <what for>}` (a server fact, a
     file mount such as `puppet:///extra_files`, the agent's catalog cache, another machine using the node as its server)
     and is skipped in this mode.
   - `--apply command --apply-command <cmd>`: your own command, called as `<cmd> <class> <dest> <kind> <manifest>`.
4. **APPLIED phase**: every check must now pass. Read-only checks and their mismatch controls run first, then mutating checks in file order. A failed check is a **finding**: the class does not do what the set says.
5. Runs each **variant** the same way, on another fresh node.

Records go to `behaviour-results/<class>/<UTC>.json`, with a JUnit `.xml` beside it.

Exit codes:

| code | meaning |
|---|---|
| 0 | all pass |
| 1 | findings |
| 2 | invalid set |
| 3 | apply or environment failure |
| 4 | skipped |

## Fixtures

`fixtures/params/<class>.json` holds a class's parameters for a run. Lookup order (the most specific level with a file
wins, in any params directory):

1. `for/<target>/<class>.json`: the class as a base of the target class.
2. `variants/<params>/<class>.json`
3. `kinds/<kind>/<class>.json`
4. `<class>.json`

A file or directory may also carry the module prefix (`puppet_infrastructure::<class>.json`).
Within a level, directories given with `--params` are searched before the suite's own. Use them for values that cannot be committed,
such as a real resolver or a password hash.

Committed fixtures must be **plainly fake**. A commit hook refuses anything else:
- addresses from RFC 5737 (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) or private ranges;
- names under `.example`, `.test`, `.invalid` or `example.com`;
- identities named `p8test...` (users `p8testuser`, interfaces `p8test0`);
- no private keys, and no hashes or tokens unless they carry `p8test`.

A fixture may use placeholders (`{{PEER_ADDR}}`), and the run fills them in. So may a node fixture,
`fixtures/node/<name>.pp`: Puppet code applied before the class, standing in for a service, path or user the class
expects and a test node lacks. A set names it in `apply.node_fixture`.

## Writing a set

- Read the class's manifest and templates first. A set describes what the class does, not what you expect it to do.
  If the node does something else, that is a finding, not a reason to change the expectation.
- For a firewall rule, take its attributes from the compiled catalog, module defaults included (for example
  `proto` defaults to tcp).
- Prefer checks that exercise the purpose (a mail is relayed, a login is refused) over checks that only read a file.
  Cover every outcome, or mark it `uncovered` with the reason and what would lift it.
- Run `./run --validate <class>` and `python3 -m pytest spec/behaviour/tests`.
