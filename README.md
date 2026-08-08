# Alcor GNU/Linux

Alcor GNU/Linux is an independent, offensive security and pentesting-focused, and lightweight Linux distribution built on top of a robust Arch Linux base. Designed for enthusiasts, developers, and penetration testers, Alcor aims to provide a fast, clean, and highly customizable operating system experience.

*(Note on "Independent": While built on Arch Linux for a reliable foundation, Alcor maintains its own custom identity, configuration ecosystem, custom installer roadmap, and sandboxed toolsets rather than just being a pre-configured theme.)*

## Features
- **Arch Linux Base:** Rolling-release model with access to the Arch User Repository (AUR) and cutting-edge software.
- **Custom Boot Experience:** Features a custom-tailored, fluid Plymouth startup animation.
- **Optimized Environment:** Lightweight XFCE desktop setup paired with a pre-configured Zsh terminal and fastfetch.
- **Offensive Security Ready:** Architecture designed to run penetration testing and security tools safely inside isolated containers without risking host stability.

---

## Roadmap

### Phase 1: Foundation & Alpha (Current)
- [x] Establish core Arch Linux live ISO structure (`archiso`).
- [x] Implement custom Plymouth boot animation and theme.
- [x] Configure initial Zsh terminal and fastfetch settings.
- [x] Integrate Calamares installer for temporary deployment and testing.
- [x] Release Alpha 1 build for public testing.

### Phase 2: Ecosystem & Tooling (Next)
- [ ] **Distrobox & Podman Integration:** Build a robust containerization layer so users can run security, pentesting, and development tools safely without risking host system stability.
- [ ] **Bloatware Cleanup:** Streamline pre-installed packages and optimize system performance/resource usage.

### Phase 3: Beta & Polishing
- [ ] **Installer Evaluation:** Test and configure Calamares first. *(Note: If Calamares doesn't meet our exact custom requirements, we will pivot to developing our own dedicated native installer).*
- [ ] Expand pre-configured Distrobox container templates for cybersecurity workflows.
- [ ] Improve documentation, hardware compatibility, and community contribution guidelines.

### Phase 4: Stable v1.0 Release
- [ ] Official stable release of Alcor GNU/Linux.
- [ ] Long-term support (LTS) kernel options and dedicated package repositories.
