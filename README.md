# Alcor GNU/Linux

**An Arch Linux-based Linux distribution focused on cybersecurity, system integration, and isolated tool management.**

Alcor GNU/Linux combines a lightweight XFCE desktop with a dedicated cybersecurity environment powered by Podman and Distrobox.

Built around **Algol**, an isolated environment for security tools, and **Alcor Router**, a custom package-routing system, Alcor aims to separate cybersecurity workflows from the host system while maintaining seamless desktop integration.

The project is currently in **Beta**. Its core architecture and integrations are under active development, with reliability, error handling, and installation stability remaining key priorities.

## Features

- **Arch Linux Base:** Rolling-release package ecosystem with AUR support.
- **Algol:** A dedicated container environment for cybersecurity tools.
- **Alcor Router:** A custom package-management wrapper that routes supported package operations to the host or Algol.
- **Container Infrastructure:** Podman and Distrobox integration for managing isolated Linux environments.
- **Desktop Integration:** Exports supported container applications and `.desktop` launchers to the host desktop.
- **GUI Application Support:** Runs supported graphical applications inside Algol with host desktop integration.
- **Manifest-Based Categorization:** Organizes cybersecurity tools into predefined application menu categories.
- **First-Boot Setup:** Uses a systemd service to prepare the cybersecurity environment in the background.
- **Kernel Options:** Standard Linux and Linux Zen, depending on the release configuration.
- **XFCE Desktop:** A lightweight and configurable graphical environment.
- **Zsh and Fastfetch:** A preconfigured shell and customized system information display.
- **Custom Plymouth Theme:** An Alcor-branded boot splash experience.

## System Architecture

```text
Alcor GNU/Linux
│
├── Host System
│   ├── Arch Linux
│   ├── Pacman
│   ├── XFCE Desktop
│   ├── Alcor Router
│   ├── Systemd Services
│   └── Exported Application Launchers
│
└── Algol Container
    ├── Podman
    ├── Distrobox
    ├── BlackArch Tool Repositories
    ├── Cybersecurity Tools
    └── Containerized GUI Applications
```

### Algol

Algol is Alcor's dedicated environment for cybersecurity tools.

Tools routed through Alcor Router are installed inside the Algol container instead of directly on the host system.

Its objectives include:

- Reducing conflicts between security tools and host packages.
- Separating cybersecurity tooling from everyday desktop applications.
- Providing a dedicated environment for security-related workflows.
- Supporting containerized command-line and graphical applications.

Containerization provides useful separation but is not an absolute security boundary. Isolation depends on privileges, device access, mounted directories, capabilities, and configuration.

### Alcor Router

Alcor Router is a custom package-management wrapper designed to direct supported package operations to the appropriate environment.

**Supported target modes:**

- **Automatic:** Selects the target according to the routing rules.
- **Host:** Directs supported operations to the host system.
- **Algol:** Directs supported operations to the Algol container.

Explicit target selection is available through `--host` and `--algol`.

The router complements the underlying package manager rather than replacing Pacman.

### Desktop Integration

Alcor integrates supported applications installed inside Algol with the host desktop.

- Exports supported executable entry points and `.desktop` launchers.
- Adds the `(Algol)` suffix to exported application entries.
- Supports graphical applications when display access and permissions are correctly configured.

Application compatibility depends on the software, container configuration, and required host resources.

### Tool Categorization

Manifest rules organize supported cybersecurity applications into predefined categories:

- Information Gathering
- Database Assessment
- Web Security
- Wireless Security
- Password Security
- Sniffing
- Exploitation
- Forensics
- Reverse Engineering
- Post-Exploitation
- Reporting
- Social Engineering

Available menu entries depend on the tools, manifests, and category rules included in each release.

## Technology Stack

| Component | Technology |
| --- | --- |
| Base System | Arch Linux |
| Package Manager | Pacman |
| Container Runtime | Podman |
| Container Integration | Distrobox |
| Security Environment | Algol |
| Package Routing | Alcor Router |
| Security Repositories | BlackArch |
| Desktop Environment | XFCE |
| Shell | Zsh |
| System Information | Fastfetch |
| Boot Splash | Plymouth |
| Init System | systemd |
| Kernel Options | Linux / Linux Zen |

## Known Beta Issues

Alcor is under active development. The following issues are known and require further testing or fixes.

### 1. Live Environment: Infinite Loop / Null Byte Output

**Description:** During installation preparation, a failed `pacman -Syy` synchronization caused by connectivity problems or repository timeouts can leave the backend error-handling loop stuck. The terminal may repeatedly display `^@` (null-byte output), preventing the Python interface from launching.

**Current workaround:** Restart the operation after the error occurs.

**Status:** Unresolved. A permanent fix for the error-handling loop is needed.

### 2. Wireshark-Qt: Container Interface Permissions

**Description:** Wireshark-Qt can launch through the exported Algol desktop entry, but its `dumpcap` backend may encounter permission errors when accessing network interfaces such as `enp0s3`. This can prevent packet capture.

Running `sudo wireshark` on the host does not resolve the issue if Wireshark is not installed on the host.

**Current workaround:**

```bash
distrobox enter algol -- sudo wireshark
```

**Status:** GUI launch workaround available. Successful packet capture still depends on interface access, permissions, and container configuration. The command does not guarantee that packet capture will work.

## Roadmap

### Phase 1: Foundation & Alpha — Completed

- [x] Establish the Arch Linux live ISO structure using `archiso`.
- [x] Configure the initial XFCE desktop environment.
- [x] Implement the custom Plymouth boot experience.
- [x] Configure Zsh and Fastfetch.
- [x] Integrate Calamares for initial installation and testing.
- [x] Release the initial Alpha build.

### Phase 2: Core Ecosystem — Completed

- [x] Integrate Podman and Distrobox.
- [x] Establish the Algol container environment.
- [x] Develop the initial Alcor Router package-routing workflow.
- [x] Implement host and Algol target selection.
- [x] Integrate supported container applications with the host desktop.
- [x] Introduce manifest-based tool categorization.
- [x] Implement first-boot environment preparation.

### Phase 3: Beta Hardening — Current

- [ ] Fix the live environment's null-byte output and error-handling loop.
- [ ] Improve network failure handling and repository synchronization.
- [ ] Validate automatic, host, and Algol package routing.
- [ ] Improve Algol provisioning and first-boot reliability.
- [ ] Resolve graphical application and network-interface permission issues.
- [ ] Validate manifest rules and exported application launchers.
- [ ] Test clean installations and supported kernel configurations.
- [ ] Improve diagnostics, recovery procedures, and documentation.

### Phase 4: Release Candidate

- [ ] Complete critical Beta bug fixes.
- [ ] Validate clean installation and first-boot workflows.
- [ ] Test package operations and container integration across supported configurations.
- [ ] Verify upgrades, failure recovery, and repeatable ISO builds.
- [ ] Document known limitations and supported hardware.
- [ ] Publish a Release Candidate for broader testing.

### Phase 5: Stable 1.0

- [ ] Publish the first stable Alcor GNU/Linux release.
- [ ] Finalize the core system and Algol integration.
- [ ] Establish a reliable update and release process.
- [ ] Document installation, maintenance, and recovery procedures.
- [ ] Evaluate dedicated package repositories and long-term kernel support.
- [ ] Publish contribution guidelines and security policies.

## Contributing

Contributions, testing, bug reports, and documentation improvements are welcome.

When reporting a bug, include:

1. The affected Alcor release.
2. Relevant system and container details.
3. Steps to reproduce the issue.
4. Relevant logs or error output.

Changes affecting package routing, container configuration, installation, or first-boot services should be tested carefully before being included in a release.

## Links

- **Website:** https://alcorlinux.netlify.app/
- **Releases:** https://alcorlinux.netlify.app/alcorlinux#releases
- **Laplace Portfolio:** https://laplace-portfolio.netlify.app/

## License

The project's license has not yet been specified. Add the chosen license before distributing the project and document applicable third-party licenses.

