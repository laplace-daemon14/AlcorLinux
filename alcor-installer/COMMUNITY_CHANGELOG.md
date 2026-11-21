# Alcor Community — Source and Change Log

Review baseline: **2026-11-20**

This file records the date each project was added to Alcor (where known), the latest upstream revision observed during review, and the files changed by that revision. Git commit timestamps show repository history; they are not a security audit, proof of identity, or a guarantee that a mutable branch still contains the same files.

## CZA

- Repository: https://gitlab.com/ranonimolan/cza
- Alcor Community entry added: **2026-11-20**
- Upstream branch inspected: `main`
- Latest upstream commit observed: **2026-11-14 21:46 (+03:00)** — `ec90216f` (`binary daha hafif hale getirildi`)
- Version in `Cargo.toml`: `0.1.2`
- License declared by the project: `BSD-3-Clause`

### Tracked upstream file revisions observed on 2026-11-20

| Upstream file | Last change observed | Commit |
|---|---:|---|
| `install.sh` | 2026-10-17 14:25 (+03:00) | `1d56e731` |
| `README.md` | 2026-10-17 14:31 (+03:00) | `7c8bf3b1` |
| `src/ops.rs` | 2026-11-14 19:31 (+03:00) | `a8776acb` |
| `packages-en.json` | 2026-11-14 16:08 (UTC) | `036d4670` |
| `dist/cza-linux-x86_64` | 2026-11-14 21:46 (+03:00) | `ec90216f` |

### Security and integration decision

CZA is selectable in the Community tab and uses the same explicit **Host / Algol** target prompt as the Python libraries. The frontend displays a second confirmation before accepting CZA selection. The target is serialized into `COMMUNITY_HOST` or `COMMUNITY_ALGOL`.

The installer runs with `--global` only inside the selected target. The Host path is handled by `alcor_backend.sh` through `arch-chroot`; the Algol path is handled by `algol-init` after the rootful Distrobox container exists. The CZA CLI is kept separate from the Python package arrays, so it is never passed to `pip`.

Security caveat: the documented installer URL points to the mutable `main` branch. The reviewed installer did not show checksum or signature verification for its downloaded binary. The reviewed CZA source fetches package catalogues from upstream and passes catalogue-provided install commands to `/bin/bash -c` after prompting the user. Those catalogue commands can change independently of an Alcor ISO release. The frontend warns users to inspect the current installer, binary provenance, catalogues and commands before opting in. Algol is rootful and host-integrated; it is not a strong security boundary.

## LightPacket

- Repository: https://github.com/Light-Projects/LightPacket
- Tracking baseline recorded in Alcor: **2026-11-20** (the exact original Alcor-addition date was not available in the supplied source files)
- Latest GitHub commit observed: **2026-11-14 23:50 (+03:00)** — `55cedad8`
- Commit message: `New Scapy like protocol registry style with support for TCP/UDP/SLLv1/SLLv2 as well`
- GitHub commit verification: **unsigned**
- Files changed in that commit:
  - `BaseLayer.py`
  - `Dot3.py`
  - `EthernetII.py`
  - `LLC.py`
  - `Layers/register.py`
  - `Wireless/wlan.py`
  - `ipv4.py`
  - `ipv6.py`
  - `platforms/linux/sll.py`
  - `ppp.py`
  - `tcp.py`
  - `tests/test_register.py`
  - `udp.py`
- Latest PyPI release observed: **1.0.3**, released **2026-11-06**. The existing Alcor summary says `1.0.4`; verify the version source before treating those numbers as equivalent.
- License declared on PyPI: `MPL-2.0`.

## LightBPF

- Repository: https://github.com/Light-Projects/LightBPF
- Tracking baseline recorded in Alcor: **2026-11-20** (the exact original Alcor-addition date was not available in the supplied source files)
- Latest GitHub commit observed: **2026-11-13 00:12 (+03:00)** — `326fb0bc`
- Commit message: `SECURITY.md Update`
- GitHub commit verification: **unsigned**
- Files changed in that commit: `SECURITY.md`
- Latest PyPI release observed: **1.0.0**, released **2026-09-24**. The existing Alcor summary refers to `1.2.1` release notes; verify the version source before treating those numbers as equivalent.
- License declared on PyPI: `MPL-2.0`.

## Alcor-side changes on 2026-11-20

- `alcor_frontend.py`: added the Community third-party warning; CZA now requires a second confirmation and an explicit Host / Algol target selection; the project details explain the system-wide upstream installer behavior.
- `alcor_backend.sh`: added a CZA CLI-tool allow-list and Host-target install path. The downloaded installer is saved, checked with `bash -n`, then executed in the installed Host chroot with `--global`.
- `algol-init`: added a separate CZA CLI-tool path for the Algol selection. It downloads and syntax-checks the installer inside the rootful Algol container, then executes it with `--global`. Python libraries remain in their existing `pip` path.

## Future update log

Append a new dated entry here whenever a Community project is re-reviewed or its upstream files change. Do not overwrite earlier entries. For every review, record the new commit SHA, date, changed file paths and whether the Alcor integration decision changed. The latest upstream commit may update only one file; list the files reported by that commit rather than assuming the entire repository changed.

### Entry template

```text
YYYY-MM-DD — PROJECT NAME
Repository:
Branch:
Reviewed commit:
Commit verification/signature status:
Changed files and upstream dates:
Version/release metadata checked:
Review notes:
Alcor integration change:
```
