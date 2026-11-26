"""A run's record (JSON) and its JUnit report."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

OUTCOME_RC = {"ALL_PASS": 0, "FINDINGS": 1, "INVALID_SET": 2, "APPLY_FAILED": 3, "ENVIRONMENT_FAILED": 3, "SKIPPED": 4}
OUTCOME_ORDER = ["INVALID_SET", "ENVIRONMENT_FAILED", "APPLY_FAILED", "FINDINGS", "SKIPPED", "ALL_PASS"]


def combined(outcomes: list[str | None]) -> str:
    """The worst of the base run's and the variant runs' outcomes."""
    return min((o or "ENVIRONMENT_FAILED" for o in outcomes), key=OUTCOME_ORDER.index)


def junit(cls: str, record: dict) -> bytes:
    suites = ET.Element("testsuites", name=f"behaviour.{cls}")
    _suites(suites, cls, record)
    for name, v in (record.get("variants") or {}).items():
        _suites(suites, f"{cls}.{name}", v)
    return ET.tostring(suites, encoding="utf-8", xml_declaration=True)


def _suites(suites, cls: str, record: dict) -> None:
    for phase, rows, rule in (("clean", record["clean"], "control"), ("applied", record["applied"], "pass")):
        suite = ET.SubElement(suites, "testsuite", name=f"behaviour.{cls}.{phase}", tests=str(len(rows)))
        bad = 0
        for r in rows:
            case = ET.SubElement(suite, "testcase", classname=f"behaviour.{cls}.{phase}", name=r["id"])
            if r.get("not_run"):
                ET.SubElement(case, "skipped", message=r["not_run"])
                continue
            if rule == "control":
                ok, msg = r["ok"], ("negative control passed on the clean node" if r["control"] == "negative"
                                    else "invariant failed on the clean node")
            else:
                ok, msg = r["passed"], "check failed after the class was applied (finding)"
            if not ok:
                bad += 1
                ET.SubElement(case, "failure", message=msg).text = f"rc {r['rc']}\n{r['stdout']}\n{r['stderr']}"
            mm = r.get("mismatch") if phase == "applied" else None
            if mm:
                mcase = ET.SubElement(suite, "testcase", classname=f"behaviour.{cls}.applied", name=f"{r['id']}.mismatch")
                suite.set("tests", str(int(suite.get("tests")) + 1))
                if mm.get("not_run"):
                    ET.SubElement(mcase, "skipped", message=mm["not_run"])
                elif mm["passed"]:
                    bad += 1
                    ET.SubElement(mcase, "failure", message=f"mismatch control passed ({mm['varies']}): the check "
                                  "does not discriminate").text = f"rc {mm['rc']}\n{mm['stdout']}"
        suite.set("failures", str(bad))
        if phase == "applied" and not rows:
            ET.SubElement(suite, "testcase", classname=f"behaviour.{cls}.applied", name="not-run").append(
                ET.Element("skipped", message=str(record["outcome"])))


def write(out_dir: Path, cls: str, record: dict, stem_name: str) -> Path:
    out = out_dir / cls
    out.mkdir(parents=True, exist_ok=True)
    stem = out / stem_name
    stem.with_suffix(".json").write_text(json.dumps(record, indent=1) + "\n")
    stem.with_suffix(".xml").write_bytes(junit(cls, record))
    return stem
