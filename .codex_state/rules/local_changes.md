# Local changes list — single source for purpose fixes (HQ 2026-11-18 policy B)
Every change this repository makes to a class's templates, files or scripts so that the class achieves its purpose on
the target OS releases (Ubuntu 24.04 for Phase 1). Each row needs:
- the behaviour check that failed before and passes after (check id, both result files);
- the minimal change;
- the reviewer verdict.

Earlier ruled changes keep their own single sources, which are not repeated here: `class_rulings.txt` holds
module-compatibility changes and ruled per-class edits, and `../upstream_defects.md` holds locally fixed upstream
defects. Escalate instead of listing when a fix changes a class interface, removes functionality, or has more than
one reasonable design. Advisor-only file.

| # | class | change (file:line) | check failing before → passing after | reviewer | date |
|---|---|---|---|---|---|
