# Ubuntu 26.04: OpenVox support (read-only check, HQ 2026-11-18 ruling D)

**Status: information for HQ. Nothing was installed or changed. The 26.04 pass waits for HQ's word (ruling D).**

## Finding
Ubuntu 26.04 is supported by the **OpenVox 8 series**, not only by OpenVox 9.
- **The repository:** the official repository apt.voxpupuli.org has a suite `ubuntu26.04` with components `openvox8 openvox9`
  (Release dated 2026-11-13). Its amd64 package indexes, read 2026-11-18, contain:

  | component | package | first 26.04 build | latest |
  |---|---|---|---|
  | openvox8 | openvox-agent | 8.25.0 | 8.33.0 |
  | openvox8 | openvox-server | 8.13.0 | 8.18.0 |
  | openvox8 | openvoxdb | 8.13.0 | 8.18.0 |
  | openvox9 | openvox-agent | 9.0.0~beta1 | 9.4.0 |
  | openvox9 | openvox-server / openvoxdb | 9.0.0~beta1 | 9.2.0 |

  The release package `openvox8-release-ubuntu26.04.deb` exists (HTTP 200).
- **Vox Pupuli's posts:** Ubuntu 26.04 agent packages exist "since the 12th of March" (agent 8.25.0), for amd64, aarch64
  and armhf. Server and DB 8.13.0 shipped 26.04 packages. The supported-platforms page lists Ubuntu 26.04 for the agent,
  the server and OpenVoxDB.
- **Not read:** no 26.04-specific known issues were found. The pages state no Ruby/JRuby or Java requirement for the
  8.x server on 26.04 (OpenVox 9's server needs Java 21 or 25).

## What it means for the lab
- **The lab is older than the first 26.04 builds.** puppet8master runs openvox-agent 8.24.2 and openvox-server 8.11.0,
  so the lab has no 26.04 build of either version.
- **A 26.04 node runs agent ≥ 8.25.0.** The lab master would then be older than the agent. The usual compatibility
  rule is a server at least as new as its agents.
- **So the 26.04 pass needs a decision first:**
  - (a) Raise the lab to current openvox8: agent 8.33.0 and server 8.18.0. That is a new lab baseline, and every check
    set has to be re-run on it.
  - (b) Keep the lab master and accept agent-newer-than-server within 8.x, for the 26.04 nodes only.

  It also bears on production's cutover target versions, which the plan does not yet name.
- **Recommendation:** decide the cutover's OpenVox versions with the 26.04 pass, and make the lab match them before
  that pass rather than during it.

## Sources
- apt.voxpupuli.org `dists/ubuntu26.04/Release` and `dists/ubuntu26.04/{openvox8,openvox9}/binary-amd64/Packages`,
  read 2026-11-18.
- https://voxpupuli.org/blog/2026/04/27/ubuntu-26.04-acceptance-tests/
- https://voxpupuli.org/blog/2026/05/08/new-openvox-server-and-db-releases/
- https://docs.openvoxproject.org/openvox/latest/supported_platforms.html
