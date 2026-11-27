#!/usr/bin/env python3
"""The reviewer's rename mode: mechanical evidence that a class came through the module rename unchanged (HQ review of
the behaviour suite, ruling 9). For every class: its diff is the rename only, and its re-verification on the public
runner after the rename is green and gives the same verdict, check for check, as the run its last review judged before
it. For the selected classes the reviewer also runs the class itself (`phase3.py run <class> --role reviewer`) and
its run must agree with the re-verification.

  rename_review.py selection             the classes the reviewer re-runs: every class whose node-visible names
                                         change, and a random 15% of the rest (seeded by the rename commit: chosen
                                         by neither the author nor the reviewer)
  rename_review.py check <class>         the evidence, one line per check, and whether this class is re-run
  rename_review.py verdict <class> --evidence TEXT [--evidence ...]
                                         persists .codex_state/reviews/rename/<class>/<UTC>.json; PASS = every check ok

The rename is the commit after the `pre-rename` tag whose subject starts `P2: rename module`. A class's node-visible
names change when its manifest names the module outside a class or define reference (a file path, a unit or instance
name, a resource title), when a template or file it renders names it outside a `scope[...]` lookup (the rendered text
reaches the node), or when it reads the local directory (`filesystem::localdir`, which the rename moves in the lab).
"""

from __future__ import annotations

import datetime as dt
import json
import random
import re
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))
import behaviour_sample  # noqa: E402
import rename_check  # noqa: E402  (the proof's own rules, applied to one class's files)

TAG = "pre-rename"
OLD_FORMS = rename_check.OLD_FORMS
RESULTS = REPO / ".codex_state" / "checks" / "results"
OUT = REPO / ".codex_state" / "reviews" / "rename"
REF = re.compile(r"""(?:template|epp|file)\(\s*['"](?:puppet_infrastructure|infra_populi)/([^'"]+)['"]"""
                 r"""|puppet:///modules/(?:puppet_infrastructure|infra_populi)/([^'"\s,)\]]+)""")


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True).stdout


def show(ref: str, path: str) -> str | bytes | None:
    """A file at a commit: text, or bytes for a binary file, or None where it does not exist."""
    p = subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:{path}"], capture_output=True)
    if p.returncode != 0:
        return None
    try:
        return p.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return p.stdout


def rename_commit() -> tuple[str, dt.datetime] | None:
    for line in git("log", "--reverse", "--format=%H %ct %s", f"{TAG}..HEAD").splitlines():
        sha, ts, subject = line.split(" ", 2)
        if subject.startswith("P2: rename module"):
            return sha, dt.datetime.fromtimestamp(int(ts), dt.timezone.utc)
    return None


def classes() -> list[str]:
    return sorted(p.stem for p in (REPO / "spec" / "behaviour" / "checks").glob("*.yml"))


def class_files(cls: str, ref: str = TAG) -> list[str]:
    """The class's manifest and the templates and files it renders, as they were before the rename."""
    manifest = f"manifests/{cls}.pp"
    text = git("show", f"{ref}:{manifest}")
    out = [manifest]
    for m in REF.finditer(text):
        if m.group(1):
            out.append(f"templates/{m.group(1)}")
        elif m.group(2):
            prefix = f"files/{m.group(2)}"
            out += [p for p in git("ls-tree", "-r", "--name-only", ref, prefix).splitlines()]
    return sorted(set(out))


def node_visible(cls: str) -> list[str]:
    """Why the class's node-visible names change (empty when they do not)."""
    why = []
    for path in class_files(cls):
        text = show(TAG, path)
        if not isinstance(text, str):  # absent, or binary (an image names nothing)
            continue
        for n, line in enumerate(text.split("\n"), 1):
            code = line.split("#", 1)[0] if path.endswith(".pp") else line
            if path.endswith(".pp"):
                code = re.sub(r"[Pp]uppet_infrastructure::\w", "", code)  # class and define references
                code = re.sub(r"""(?:template|epp|file)\(\s*['"]puppet_infrastructure/|puppet:///modules/puppet_"""
                              r"""infrastructure/""", "", code)
            else:
                code = re.sub(r"""scope\[['"]puppet_infrastructure::""", "", code)  # a lookup, not rendered
            if any(f in code for f in OLD_FORMS):
                why.append(f"{path}:{n} names the module in what reaches the node")
        if path.endswith(".pp") and re.search(r"filesystem::localdir|\$localdir\b", text):
            why.append(f"{path} reads the local directory, which the rename moves")
    return why


def selection() -> tuple[list[str], list[str]]:
    rc = rename_commit()
    if rc is None:
        raise SystemExit("no `P2: rename module` commit after the pre-rename tag")
    visible = [c for c in classes() if node_visible(c)]
    rest = [c for c in classes() if c not in visible]
    sample = sorted(random.Random(rc[0]).sample(rest, round(0.15 * len(rest))))
    return visible, sample


def results(cls: str, role: str) -> list[dict]:
    out = []
    for p in sorted((RESULTS / cls).glob(f"*-{role}.json")):
        r = json.loads(p.read_text())
        r["_at"] = dt.datetime.strptime(r["at"], "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
        out.append(r)
    return out


def green(r: dict) -> bool:
    runs = [r] + list((r.get("variants") or {}).values())
    return all((x.get("apply") or {}).get("green") for x in runs) and r.get("valid")


def differences(a: dict, b: dict) -> list[str]:
    out = []
    pairs = [("base", a, b)] + [(f"variant {n}", v, (b.get("variants") or {}).get(n) or {})
                                for n, v in (a.get("variants") or {}).items()]
    for run, x, y in pairs:
        vx, vy = behaviour_sample.verdicts(x), behaviour_sample.verdicts(y)
        out += [f"{run} {k[0]} {k[1]}: before {vx.get(k)!r}, after {vy.get(k)!r}"
                for k in sorted(set(vx) | set(vy), key=str) if vx.get(k) != vy.get(k)]
    return out


def evidence(cls: str) -> dict:
    rc = rename_commit()
    if rc is None:
        raise SystemExit("no `P2: rename module` commit after the pre-rename tag")
    sha, when = rc
    checks, notes = {}, []
    # 1. the class's own files and its check set: the rename only
    sc = rename_check.read_scope(git("show", f"{TAG}:.codex_state/rules/rename_scope.txt"))
    news = rename_check.new_forms(json.loads(git("show", f"{sha}:metadata.json"))["name"])
    problems = []
    for path in class_files(cls) + [f"spec/behaviour/checks/{cls}.yml"]:
        old, new = show(TAG, path), show(sha, path)
        if not isinstance(old, str) or not isinstance(new, str):
            if old != new:
                problems.append(f"{path}: changed (binary or missing)")
            continue
        if path.endswith(".yml"):
            problems += rename_check.check_set(path, old, new, sc, news)
        elif [rename_check.mapped(l, sc, news) for l in old.split("\n")] != new.split("\n"):
            problems.append(f"{path}: not the rename of its old content")
    checks["rename_only"] = "fail" if problems else "ok"
    notes += problems or [f"{len(class_files(cls)) + 1} files, each its old content renamed"]
    # 2. the re-verification after the rename: green, the same verdicts as the run the last review judged before it
    data = __import__("yaml").safe_load((REPO / "spec" / "behaviour" / "checks" / f"{cls}.yml").read_text())
    after = [r for r in results(cls, "author") if r["_at"] > when]
    before = [r for r in results(cls, "reviewer") if r["_at"] < when]
    if "deferred" in data:
        checks["reverified"] = "ok"
        notes.append("deferred set: no behaviour run; the harness re-verification is the reviewer's own (`review_class.py "
                     "check`)")
    elif not after:
        checks["reverified"] = "fail"
        notes.append("no author run after the rename")
    else:
        a = after[-1]
        diff = differences(before[-1], a) if before else ["no reviewed run before the rename"]
        checks["reverified"] = "ok" if green(a) and not diff else "fail"
        notes.append(f"after the rename: {a['at']}-author {a['outcome']}, apply {'green' if green(a) else 'NOT green'}")
        notes += diff or [f"identical to {before[-1]['at']}-reviewer check for check"]
    # 3. the selected classes: the reviewer's own run after the rename agrees with the author's
    visible, sample = selection()
    if cls in visible or cls in sample:
        mine = [r for r in results(cls, "reviewer") if r["_at"] > when]
        if "deferred" in data:
            checks["rerun"] = "ok"
        elif not mine or not after:
            checks["rerun"] = "fail"
            notes.append(f"selected ({'node-visible names change' if cls in visible else 'random 15%'}): run "
                         f"`phase3.py run {cls} --role reviewer`, then check again")
        else:
            diff = differences(after[-1], mine[-1])
            checks["rerun"] = "ok" if green(mine[-1]) and not diff else "fail"
            notes.append(f"re-run {mine[-1]['at']}-reviewer: " + ("agrees with the author's run" if not diff
                                                                  else "; ".join(diff)))
    return {"class": cls, "rename_commit": sha, "checks": checks, "notes": notes,
            "selected": "node-visible" if cls in visible else "random" if cls in sample else None,
            "node_visible": node_visible(cls)}


def main(argv: list[str]) -> int:
    if argv[:1] == ["selection"]:
        visible, sample = selection()
        print(f"node-visible ({len(visible)}): {' '.join(visible)}")
        print(f"random 15% of the rest ({len(sample)}): {' '.join(sample)}")
        return 0
    if len(argv) >= 2 and argv[0] in ("check", "verdict"):
        e = evidence(argv[1])
        for k, v in e["checks"].items():
            print(f"{k}: {v}")
        for n in e["notes"] + e["node_visible"]:
            print(f"  {n}")
        print(f"selected for re-run: {e['selected'] or 'no'}")
        if argv[0] == "check":
            return 0
        given = [argv[i + 1] for i, a in enumerate(argv[:-1]) if a == "--evidence"]
        if not given:
            raise SystemExit("ERROR: verdict needs at least one --evidence")
        verdict = "PASS" if all(v == "ok" for v in e["checks"].values()) else "FAIL"
        at = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        (OUT / argv[1]).mkdir(parents=True, exist_ok=True)
        path = OUT / argv[1] / f"{at}.json"
        path.write_text(json.dumps({**e, "at": at, "verdict": verdict, "evidence": given}, indent=1) + "\n")
        print(f"VERDICT {verdict}\npersisted {path.relative_to(REPO)}")
        return 0 if verdict == "PASS" else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
