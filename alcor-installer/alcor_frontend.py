import sys
import os
import re
import shlex
import subprocess
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QRadioButton, QCheckBox, QLabel, QScrollArea, 
                             QPushButton, QStackedWidget, QGridLayout,
                             QMessageBox, QComboBox,
                             QLineEdit, QProgressDialog, QSizePolicy, QFrame,
                             QToolButton, QTabWidget)
from PyQt6.QtCore import (
    Qt, QSize, QTimer, QSignalBlocker, QUrl
)
from PyQt6.QtGui import QPixmap, QIcon, QDesktopServices

class AlcorFrontend(QWidget):
    def __init__(self):
        super().__init__()
        
        self.pentest_boxes = {}
        self.daily_boxes = {}
        self.expert_boxes = {}
        self.expert_package_groups = {}
        self.expert_package_widgets = []
        self.expert_package_widget_boxes = {}
        self.built_expert_package_profiles = set()
        self.tool_entries = []
        self.tool_groups = set()
        self.category_expanded = {}
        self.category_toggle_buttons = {}
        self.category_grids = {}
        
        self.logo_dir = os.path.dirname(os.path.abspath(__file__))
        default_selection_file = f"/tmp/alcor_selection_{os.getuid()}.txt"
        self.selection_file = os.environ.get("ALCOR_SELECTION_FILE", default_selection_file)
        self.package_count_timer = QTimer(self)
        self.package_count_timer.setSingleShot(True)
        self.package_count_timer.setInterval(45)
        self.package_count_timer.timeout.connect(self.refresh_package_count)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(90)
        self.search_timer.timeout.connect(
            lambda: self.filter_tools(self.tool_search.text())
        )
        
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Alcor GNU/Linux Installer')
        self.resize(1040, 760)
        self.setMinimumSize(820, 600)

        self.setStyleSheet("""
            QWidget {
                background-color: #f3f5f8;
                color: #1d2735;
                font-family: 'Noto Sans', 'Segoe UI', sans-serif;
            }
            QCheckBox {
                padding: 5px 4px;
                color: #354154;
                spacing: 8px;
            }
            QCheckBox:hover {
                color: #17212f;
                background-color: #edf1f5;
                border-radius: 4px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #aeb8c6;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QCheckBox::indicator:checked {
                background-color: #d97716;
                border-color: #bd5f0d;
            }
            QGroupBox {
                border: 1px solid #d5dce5;
                border-radius: 8px;
                margin-top: 16px;
                padding: 14px 10px 10px 10px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 7px;
                color: #a9520b;
                font-weight: 700;
                background-color: #f3f5f8;
            }
            QComboBox, QLineEdit {
                min-height: 20px;
                padding: 7px 10px;
                border: 1px solid #cbd3de;
                border-radius: 6px;
                background-color: #ffffff;
                selection-background-color: #d97716;
                selection-color: #ffffff;
            }
            QComboBox:focus, QLineEdit:focus {
                border-color: #c66b13;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #cbd3de;
                background-color: #ffffff;
                selection-background-color: #f8eadc;
                selection-color: #1d2735;
            }
            QPushButton {
                padding: 9px 16px;
                border: 1px solid #cbd3de;
                border-radius: 6px;
                background-color: #ffffff;
                color: #253144;
                font-weight: 700;
            }
            QPushButton:hover {
                border-color: #c66b13;
                background-color: #fff8f1;
            }
            QPushButton:disabled {
                color: #8a94a3;
                border-color: #d8dee6;
                background-color: #edf0f4;
            }
            QScrollArea {
                border: 1px solid #d5dce5;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QScrollBar:vertical {
                width: 10px;
                background: #f3f5f8;
                margin: 3px;
            }
            QScrollBar::handle:vertical {
                background: #c2cad5;
                border-radius: 4px;
                min-height: 36px;
            }
            QScrollBar::handle:vertical:hover {
                background: #8d99a9;
            }
            QTabWidget::pane {
                border: 1px solid #d5dce5;
                border-radius: 8px;
                background: #ffffff;
                top: -1px;
            }
            QTabBar::tab {
                color: #536074;
                background: #e8ecf1;
                border: 1px solid #d5dce5;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 9px 20px;
                margin-right: 4px;
                min-width: 90px;
            }
            QTabBar::tab:selected {
                color: #8f4509;
                background: #ffffff;
                border-color: #d5dce5;
                font-weight: 700;
            }
            QTabBar::tab:hover:!selected {
                color: #253144;
                background: #f7f8fa;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(18, 10, 18, 10)
        main_layout.setSpacing(7)
        
        title = QLabel("ALCOR LINUX INSTALLER")
        title.setObjectName("installerTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 23px; font-weight: 800; color: #192536; letter-spacing: 1px; margin-top: 4px;")
        main_layout.addWidget(title)

        subtitle = QLabel(
            "Choose a working profile, review the target, then launch Calamares."
        )
        subtitle.setObjectName("installerSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #687588; font-size: 12px; margin-bottom: 2px;")
        main_layout.addWidget(subtitle)

        theme_row = QHBoxLayout()
        theme_row.addStretch()
        theme_label = QLabel("Appearance")
        theme_label.setObjectName("themeLabel")
        self.theme_selector = QComboBox()
        self.theme_selector.addItem("Light", "light")
        self.theme_selector.addItem("Dark", "dark")
        self.theme_selector.setCurrentIndex(1)
        self.theme_selector.setToolTip("Switch between light and dark appearance")
        self.theme_selector.currentIndexChanged.connect(self.apply_theme)
        theme_row.addWidget(theme_label)
        theme_row.addWidget(self.theme_selector)
        main_layout.addLayout(theme_row)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        setup_page = QWidget()
        setup_layout = QVBoxLayout(setup_page)
        setup_layout.setContentsMargins(10, 8, 10, 8)
        setup_layout.setSpacing(6)
        main_layout.addWidget(self.tabs, 1)

        self.tool_search = QLineEdit()
        self.tool_search.setPlaceholderText("Search tools across the selected profile...")
        self.tool_search.setClearButtonEnabled(True)
        self.tool_search.setStyleSheet("""
            QLineEdit {
                color: #253144;
                background-color: #ffffff;
                border: 1px solid #cbd3de;
                border-radius: 6px;
                padding: 9px 12px;
                selection-background-color: #f8eadc;
            }
            QLineEdit:focus {
                border-color: #c66b13;
            }
        """)
        self.tool_search.textChanged.connect(self.schedule_tool_filter)
        setup_layout.addWidget(self.tool_search)

        mode_layout = QGridLayout()
        mode_layout.setSpacing(8)
        mode_layout.setColumnStretch(0, 1)
        mode_layout.setColumnStretch(1, 1)
        
        self.radio_pentest = QRadioButton("  AlcorPentest")
        self.radio_pentest.setObjectName("profilePentest")
        self.radio_pentest.setIcon(QIcon(QPixmap(os.path.join(self.logo_dir, "red_alcor.png"))))
        self.radio_pentest.setIconSize(QSize(34, 34))
        self.radio_pentest.setMinimumSize(230, 54)
        self.radio_pentest.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.radio_pentest.setStyleSheet("""
            QRadioButton {
                font-size: 14px;
                font-weight: bold;
                color: #4a5669;
                padding: 12px 16px;
                border: 1px solid #d5dce5;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QRadioButton:checked {
                color: #ff1e27;
                border-color: #ff1e27;
                background-color: #fff3f2;
            }
        """)
        mode_layout.addWidget(self.radio_pentest, 0, 0)

        self.radio_daily = QRadioButton("  AlcorDaily")
        self.radio_daily.setObjectName("profileDaily")
        self.radio_daily.setIcon(QIcon(QPixmap(os.path.join(self.logo_dir, "blue_alcor.png"))))
        self.radio_daily.setIconSize(QSize(34, 34))
        self.radio_daily.setMinimumSize(230, 54)
        self.radio_daily.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.radio_daily.setStyleSheet("""
            QRadioButton {
                font-size: 14px;
                font-weight: bold;
                color: #4a5669;
                padding: 12px 16px;
                border: 1px solid #d5dce5;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QRadioButton:checked {
                color: #1e77ff;
                border-color: #1e77ff;
                background-color: #f1f6ff;
            }
        """)
        mode_layout.addWidget(self.radio_daily, 0, 1)

        self.radio_carma = QRadioButton("  AlcorCarma")
        self.radio_carma.setObjectName("profileCarma")
        self.radio_carma.setIcon(QIcon(QPixmap(os.path.join(self.logo_dir, "purple_alcor.png"))))
        self.radio_carma.setIconSize(QSize(34, 34))
        self.radio_carma.setMinimumSize(230, 54)
        self.radio_carma.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.radio_carma.setStyleSheet("""
            QRadioButton {
                font-size: 14px;
                font-weight: bold;
                color: #4a5669;
                padding: 12px 16px;
                border: 1px solid #d5dce5;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QRadioButton:checked {
                color: #a61eff;
                border-color: #a61eff;
                background-color: #f8f2ff;
            }
        """)
        mode_layout.addWidget(self.radio_carma, 1, 0)

        self.radio_expert = QRadioButton("  AlcorExpert")
        self.radio_expert.setObjectName("profileExpert")
        self.radio_expert.setIcon(QIcon(QPixmap(os.path.join(self.logo_dir, "expert_alcor.png"))))
        self.radio_expert.setIconSize(QSize(34, 34))
        self.radio_expert.setMinimumSize(230, 54)
        self.radio_expert.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.radio_expert.setStyleSheet("""
            QRadioButton {
                font-size: 14px;
                font-weight: bold;
                color: #4a5669;
                padding: 12px 16px;
                border: 1px solid #d5dce5;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QRadioButton:checked {
                color: #ff9f1c;
                border-color: #ff9f1c;
                background-color: #fff7eb;
            }
        """)
        mode_layout.addWidget(self.radio_expert, 1, 1)

        setup_layout.addLayout(mode_layout)

        self.selection_status = QLabel("Choose a profile to configure your deployment")
        self.selection_status.setObjectName("selectionStatus")
        self.selection_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.selection_status.setStyleSheet("color: #687588; font-size: 12px; padding: 5px;")
        setup_layout.addWidget(self.selection_status)

        self.package_count_label = QLabel("0 packages selected")
        self.package_count_label.setObjectName("packageCount")
        self.package_count_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.package_count_label.setStyleSheet("color: #536074; font-size: 12px; font-weight: 700; padding-bottom: 2px;")

        package_actions = QHBoxLayout()
        package_actions.addWidget(self.package_count_label)
        package_actions.addStretch()
        self.select_all_button = QPushButton("Select all")
        self.clear_all_button = QPushButton("Clear all")
        self.select_all_button.setEnabled(False)
        self.clear_all_button.setEnabled(False)
        self.select_all_button.clicked.connect(
            lambda: self.set_active_packages_selected(True)
        )
        self.clear_all_button.clicked.connect(
            lambda: self.set_active_packages_selected(False)
        )
        package_actions.addWidget(self.select_all_button)
        package_actions.addWidget(self.clear_all_button)
        setup_layout.addLayout(package_actions)

        self.radio_pentest.toggled.connect(self.switch_panel)
        self.radio_daily.toggled.connect(self.switch_panel)
        self.radio_carma.toggled.connect(self.switch_panel)
        self.radio_expert.toggled.connect(self.switch_panel)

        self.stack = QStackedWidget()
        
        self.page_empty = QLabel("Select a deployment profile to get started.")
        self.page_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_empty.setStyleSheet("color: #687588; font-style: italic; font-size: 14px;")
        
        self.page_pentest = self.init_pentest_ui()
        self.page_daily = self.init_daily_ui()
        self.page_carma = self.init_carma_ui()
        self.page_expert = self.init_expert_ui()

        self.stack.addWidget(self.page_empty)
        self.stack.addWidget(self.page_pentest)
        self.stack.addWidget(self.page_daily)
        self.stack.addWidget(self.page_carma)
        self.stack.addWidget(self.page_expert)
        setup_layout.addWidget(self.stack, 1)

        btn_layout = QHBoxLayout()
        self.btn_save_profile = QPushButton("SAVE PROFILE")
        self.btn_save_profile.setObjectName("secondaryAction")
        self.btn_save_profile.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #cbd3de;
                border-radius: 6px;
                padding: 10px 18px;
                color: #354154;
                font-weight: bold;
            }
            QPushButton:hover {
                border-color: #c66b13;
                color: #1d2735;
            }
        """)
        self.btn_save_profile.clicked.connect(self.save_profile)
        btn_layout.addWidget(self.btn_save_profile)
        btn_layout.addStretch()
        self.btn_launch = QPushButton("INITIALIZE CALAMARES ENGINE")
        self.btn_launch.setObjectName("primaryAction")
        self.btn_launch.setStyleSheet("""
            QPushButton {
                background-color: #a96410;
                border: 1px solid #d58b27;
                border-radius: 8px;
                padding: 11px 24px;
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c27b1a;
                border-color: #ffb84d;
            }
        """)
        self.btn_launch.clicked.connect(self.save_and_launch)
        btn_layout.addWidget(self.btn_launch)
        setup_layout.addLayout(btn_layout)

        # Keep the navigation order intentional: Installer → Community → LaplaceTools → Help.
        self.tabs.addTab(setup_page, "Installer")
        self.tabs.addTab(self.init_community_ui(), "Community")
        self.tabs.addTab(self.init_laplace_tools_ui(), "LaplaceTools")
        self.tabs.addTab(self.init_help_ui(), "Help")
        self.setLayout(main_layout)
        self.stack.setCurrentIndex(0)
        self.apply_theme()

    def init_laplace_tools_ui(self):
        """Show tools authored or maintained for the Alcor ecosystem by Laplace."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        heading = QLabel("LAPLACE TOOLS")
        heading.setObjectName("laplaceToolsTitle")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)

        intro = QLabel(
            "A dedicated space for tools and utilities developed or maintained "
            "by Laplace for the Alcor ecosystem."
        )
        intro.setObjectName("laplaceToolsIntro")
        intro.setAlignment(Qt.AlignmentFlag.AlignCenter)
        intro.setWordWrap(True)
        layout.addWidget(intro)

        owner_card = QFrame()
        owner_card.setObjectName("laplaceToolsHero")
        owner_layout = QVBoxLayout(owner_card)
        owner_layout.setContentsMargins(18, 18, 18, 18)
        owner_layout.setSpacing(8)

        owner_label = QLabel("PROJECT OWNER  ·  LAPLACE")
        owner_label.setObjectName("laplaceToolsOwner")
        owner_layout.addWidget(owner_label)

        owner_description = QLabel(
            "Laplace Tools collects standalone utilities created for development, "
            "system administration and the Alcor workflow. Each published entry "
            "will include a clear purpose, usage notes and a source location when available."
        )
        owner_description.setObjectName("laplaceToolsBody")
        owner_description.setWordWrap(True)
        owner_layout.addWidget(owner_description)
        layout.addWidget(owner_card)

        empty_state = QFrame()
        empty_state.setObjectName("laplaceToolsEmpty")
        empty_layout = QVBoxLayout(empty_state)
        empty_layout.setContentsMargins(18, 20, 18, 20)
        empty_layout.setSpacing(8)

        empty_title = QLabel("MORE TOOLS ARE ON THE WAY")
        empty_title.setObjectName("laplaceToolsEmptyTitle")
        empty_layout.addWidget(empty_title)

        empty_description = QLabel(
            "There are no additional Laplace Tools entries published in this section yet. "
            "New tools will appear here as they are completed and ready to share."
        )
        empty_description.setObjectName("laplaceToolsBody")
        empty_description.setWordWrap(True)
        empty_layout.addWidget(empty_description)
        layout.addWidget(empty_state)

        layout.addStretch(1)
        scroll.setWidget(page)
        return scroll

    def init_help_ui(self):
        """Build the installer guide using the options exposed by this frontend."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        heading = QLabel("ALCOR INSTALLER GUIDE")
        heading.setObjectName("helpPageTitle")
        layout.addWidget(heading)

        intro = QLabel(
            "This guide explains the deployment profiles, package selection, Host and "
            "Algol environments, kernel and firewall options, and the Calamares installation "
            "steps. Review the selected configuration before applying any disk changes."
        )
        intro.setObjectName("helpPageIntro")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        topics = [
            (
                "1. Installation workflow",
                "Start in the Installer tab and choose one deployment profile. Expand package "
                "categories to review individual tools, use the search field to find packages, "
                "and use Select all or Clear all for the active profile. The package counter "
                "shows how many selections are currently enabled. SAVE PROFILE stores the "
                "current selection under ~/alcor-profiles/. INITIALIZE CALAMARES ENGINE "
                "validates the selection, displays a deployment summary and then launches "
                "Calamares. Saving a profile does not install the system.",
            ),
            (
                "2. Choose the deployment profile",
                "AlcorPentest selects security assessment, reconnaissance, web, wireless, "
                "network, forensics and reverse-engineering tool groups and uses the standard "
                "Linux kernel. AlcorDaily selects desktop, gaming, media, development and "
                "productivity tools and uses Linux Zen. AlcorCarma combines the Pentest and "
                "Daily package groups and requests both Linux Zen and standard Linux kernels. "
                "AlcorExpert lets you choose a kernel, an optional package set and an optional "
                "UFW firewall configuration.",
            ),
            (
                "3. Expert settings: kernel, packages and firewall",
                "The Expert kernel selector offers Linux Standard, Linux Zen, Linux Hardened "
                "and Linux LTS. The Expert package profile can be None, Pentest, Daily or "
                "Carma; None means no additional profile package group is selected. The "
                "firewall selector offers No firewall or UFW (deny incoming). When UFW is "
                "selected, Alcor configures incoming traffic to be denied and outgoing traffic "
                "to be allowed. The firewall option is part of the Expert configuration.",
            ),
            (
                "4. Host and Algol environments",
                "The installed desktop environment is XFCE with LightDM. Alcor uses a Host "
                "system alongside the Algol container environment. Package routing is handled "
                "by Alcor's package wrapper and package mapping; a tool is not necessarily "
                "installed on the Host just because it appears in a package list. Community "
                "Python projects ask you to choose Host or Algol separately. Prefer the "
                "isolated Algol environment for tools you do not need integrated into the "
                "base desktop, and review third-party code before installing it anywhere.",
            ),
            (
                "5. Package availability and repository notes",
                "Before launch, the installer checks whether selected packages are visible in "
                "the currently enabled repositories. If some packages are not found, it shows "
                "a warning and asks whether you want to continue. Some BlackArch packages may "
                "be resolved inside Algol after its repository is configured. AUR packages are "
                "not built automatically by this installer. Review the missing package names "
                "and continue only when you understand the warning.",
            ),
            (
                "6. Community projects",
                "The Community tab lists independently maintained third-party projects. Read "
                "each project's details, source repository, license and update information "
                "before selecting it. Where installation is supported, choose the requested "
                "target (Host or Algol) in the target dialog. CZA is shown as a reference-only "
                "entry for manual review; Alcor does not automatically install it. Community "
                "software can change after an Alcor release and is not guaranteed or audited "
                "by the Alcor installer team.",
            ),
            (
                "7. Calamares: disks, partitions and filesystems",
                "Disk partitioning is performed in Calamares, not in the profile selector. "
                "Carefully confirm the target drive, partition layout, mount points and "
                "formatting choices. Formatting, deleting or replacing partitions can erase "
                "existing data. Back up important files before proceeding. Choose the "
                "filesystem and bootloader options offered by Calamares; the Expert screen "
                "does not override the filesystem choice.",
            ),
            (
                "8. Kernel setup and first boot",
                "The selected kernel or kernels are installed into the target system. Alcor's "
                "backend prepares the corresponding mkinitcpio presets and builds initramfs "
                "images for the selected kernels. The installed system is configured for the "
                "XFCE graphical session with LightDM. The first-boot process then handles "
                "the remaining Alcor setup, including Algol initialization and selected "
                "package-routing tasks. Do not interrupt installation while packages or "
                "initramfs images are being configured.",
            ),
            (
                "9. Before you start",
                "Keep the computer connected to reliable power. Make sure you have a backup "
                "of important data, verify the destination disk, review the deployment "
                "summary, and check the selected kernel and package set. An internet "
                "connection may be required for package downloads and first-boot setup. If "
                "Calamares reports an error, note the exact message and retain the relevant "
                "installer logs before retrying.",
            ),
        ]

        for title, body in topics:
            card = QFrame()
            card.setObjectName("helpTopicCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(6)

            topic_title = QLabel(title)
            topic_title.setObjectName("helpTopicTitle")
            card_layout.addWidget(topic_title)

            topic_body = QLabel(body)
            topic_body.setObjectName("helpTopicBody")
            topic_body.setWordWrap(True)
            card_layout.addWidget(topic_body)
            layout.addWidget(card)

        layout.addStretch(1)
        scroll.setWidget(page)
        return scroll

    def apply_theme(self, _index=None):
        palettes = {
            "light": {
                "window": "#f3f5f8",
                "surface": "#ffffff",
                "soft": "#e8ecf1",
                "input": "#ffffff",
                "text": "#1d2735",
                "muted": "#687588",
                "border": "#d5dce5",
                "hover": "#fff8f1",
                "accent": "#c66b13",
                "selection": "#fff3e5",
                "on_accent": "#ffffff",
            },
            "dark": {
                "window": "#0b0e14",
                "surface": "#121923",
                "soft": "#1a2431",
                "input": "#0f151e",
                "text": "#e6eaf2",
                "muted": "#9aa5b5",
                "border": "#303b4d",
                "hover": "#202a38",
                "accent": "#ff9f1c",
                "selection": "#302312",
                "on_accent": "#17120a",
            },
        }
        theme = self.theme_selector.currentData()
        colors = palettes.get(theme, palettes["light"])
        accent = getattr(self, "profile_accent", colors["accent"])

        for widget in self.findChildren(QWidget):
            widget.setStyleSheet("")

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {colors['window']};
                color: {colors['text']};
                font-family: 'Noto Sans', 'Segoe UI', sans-serif;
                font-size: 12px;
            }}
            QLabel#installerTitle {{ font-size: 23px; font-weight: 800; }}
            QLabel {{ background: transparent; }}
            QLabel#installerSubtitle, QLabel#selectionStatus,
            QLabel#themeLabel {{ color: {colors['muted']}; }}
            QLabel#packageCount {{ color: {colors['text']}; font-weight: 700; }}
            QLabel#categoryTitle {{ color: {accent}; font-weight: 700; }}
            QLineEdit, QComboBox {{
                color: {colors['text']};
                background: {colors['input']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                padding: 8px 10px;
                min-height: 20px;
                selection-background-color: {accent};
                selection-color: {colors['on_accent']};
            }}
            QLineEdit:focus, QComboBox:focus {{ border-color: {accent}; }}
            QComboBox QAbstractItemView {{
                color: {colors['text']};
                background: {colors['surface']};
                selection-background-color: {colors['selection']};
                selection-color: {colors['text']};
            }}
            QRadioButton {{
                color: {colors['muted']};
                background: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 14px;
                font-weight: 700;
            }}
            QRadioButton:checked {{
                color: {accent};
                border-color: {accent};
                background: {colors['selection']};
            }}
            QCheckBox {{ color: {colors['text']}; spacing: 8px; padding: 4px; }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {colors['border']};
                border-radius: 4px;
                background: {colors['surface']};
            }}
            QCheckBox::indicator:checked {{
                background: {accent};
                border-color: {accent};
            }}
            QPushButton {{
                color: {colors['text']};
                background: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                padding: 8px 13px;
                font-weight: 700;
            }}
            QPushButton:hover {{ border-color: {accent}; background: {colors['hover']}; }}
            QPushButton:disabled {{ color: {colors['muted']}; background: {colors['soft']}; }}
            QPushButton#primaryAction {{
                color: {colors['on_accent']};
                background: {accent};
                border-color: {accent};
                padding: 11px 24px;
                font-size: 14px;
            }}
            QToolButton {{
                color: {colors['muted']};
                background: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: 5px;
                padding: 5px 9px;
            }}
            QToolButton:hover {{ color: {colors['text']}; border-color: {accent}; }}

            QLabel#helpPageTitle {{
                color: {colors['text']};
                font-size: 20px;
                font-weight: 900;
                letter-spacing: 1px;
            }}
            QLabel#helpPageIntro {{
                color: {colors['muted']};
                font-size: 12px;
                padding-bottom: 4px;
            }}
            QLabel#helpTopicTitle {{
                color: {accent};
                font-size: 13px;
                font-weight: 800;
            }}
            QLabel#helpTopicBody {{
                color: {colors['text']};
                font-size: 12px;
            }}
            QLabel#laplaceToolsTitle {{
                color: {colors['text']};
                font-size: 25px;
                font-weight: 900;
                letter-spacing: 1px;
            }}
            QLabel#laplaceToolsIntro {{
                color: {colors['muted']};
                font-size: 13px;
            }}
            QFrame#laplaceToolsHero {{
                background: {colors['surface']};
                border: 1px solid {colors['border']};
                border-left: 5px solid #a78bfa;
                border-radius: 9px;
            }}
            QLabel#laplaceToolsOwner {{
                color: #a78bfa;
                font-size: 12px;
                font-weight: 900;
                letter-spacing: 1px;
            }}
            QLabel#laplaceToolsBody {{
                color: {colors['text']};
                font-size: 12px;
            }}
            QFrame#laplaceToolsEmpty {{
                background: {colors['soft']};
                border: 1px dashed {colors['border']};
                border-radius: 9px;
            }}
            QLabel#laplaceToolsEmptyTitle {{
                color: {colors['text']};
                font-size: 14px;
                font-weight: 900;
            }}
            QFrame#communitySecurityNotice {{
                background: {colors['selection']};
                border: 1px solid {colors['accent']};
                border-left: 5px solid {colors['accent']};
                border-radius: 8px;
            }}
            QLabel#communitySecurityTitle {{
                color: {colors['accent']};
                font-size: 13px;
                font-weight: 900;
            }}
            QLabel#communitySecurityBody {{
                color: {colors['text']};
                font-size: 12px;
            }}
            QLabel#communityExternalProjectTitle {{
                color: {colors['text']};
                font-size: 18px;
                font-weight: 900;
            }}
            QLabel#communityManualReviewBadge {{
                color: #9a3412;
                background: #ffedd5;
                border: 1px solid #fdba74;
                border-radius: 5px;
                padding: 5px 8px;
                font-size: 10px;
                font-weight: 900;
            }}
            QFrame#communityContributionCard {{
                background: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: 9px;
            }}
            QLabel#communityContributionText {{
                color: {colors['text']};
                font-weight: 700;
            }}
            QLabel#communityContributionHint {{
                color: {colors['muted']};
            }}
            QPushButton#communityDiscordButton {{
                color: #ffffff;
                background: #5865F2;
                border: 1px solid #5865F2;
                border-radius: 7px;
                padding: 10px 20px;
                font-weight: 800;
            }}
            QPushButton#communityDiscordButton:hover {{
                background: #4752C4;
                border-color: #4752C4;
            }}
            QFrame#packageCategory, QFrame#helpTopicCard,
            QFrame#expertProfileCard, QFrame#expertSummaryCard,
            QFrame#expertFlowCard {{
                background: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
            }}
            QFrame#packageCategory {{ border-left: 3px solid {accent}; }}
            QFrame#expertProfileCard {{ border-left: 5px solid {accent}; }}
            QScrollArea {{
                background: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
            }}
            QScrollBar:vertical {{ width: 10px; background: {colors['window']}; margin: 3px; }}
            QScrollBar::handle:vertical {{ background: {colors['border']}; border-radius: 4px; min-height: 32px; }}
            QTabWidget::pane {{ border: 1px solid {colors['border']}; border-radius: 8px; background: {colors['surface']}; top: -1px; }}
            QTabBar::tab {{ color: {colors['muted']}; background: {colors['soft']}; border: 1px solid {colors['border']}; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; padding: 9px 20px; margin-right: 4px; min-width: 90px; }}
            QTabBar::tab:selected {{ color: {accent}; background: {colors['surface']}; font-weight: 700; }}
        """)

    def update_dynamic_styles(self, color_code):
        self.profile_accent = color_code
        self.apply_theme()

    def switch_panel(self):
        if self.radio_pentest.isChecked():
            self.stack.setCurrentIndex(1)
            self.update_dynamic_styles("#ff1e27") # Neon Kırmızı
            self.selection_status.setText("AlcorPentest selected - security toolkit and assessment utilities")
        elif self.radio_daily.isChecked():
            self.stack.setCurrentIndex(2)
            self.update_dynamic_styles("#1e77ff") # Neon Mavi
            self.selection_status.setText("AlcorDaily selected - desktop, gaming, work and media tools")
        elif self.radio_carma.isChecked():
            self.stack.setCurrentIndex(3)
            self.update_dynamic_styles("#a61eff") # Neon Mor
            self.selection_status.setText("AlcorCarma selected - combined security and daily environment")
        elif self.radio_expert.isChecked():
            self.stack.setCurrentIndex(4)
            self.update_expert_kernel_style()
            self.selection_status.setText("AlcorExpert selected - choose your kernel and advanced toolset")

        self.update_package_selection_actions()
        self.update_package_count()

    def update_expert_kernel_style(self, _index=None):
        kernel_colors = {
            "linux": "#ff9f1c",
            "linux-zen": "#38d996",
            "linux-hardened": "#ff5c5c",
            "linux-lts": "#5ba7ff"
        }
        color = kernel_colors.get(self.expert_kernel.currentData(), "#ff9f1c")
        if self.radio_expert.isChecked():
            self.update_dynamic_styles(color)
            self.update_expert_summary()

    def create_master_group(self, title, tools, storage_dict):
        category_icons = {
            "Recon": "[R]",
            "Web": "[W]",
            "Wireless": "[N]",
            "Network": "[N]",
            "Password": "[P]",
            "Exploit": "[X]",
            "Cloud": "[C]",
            "Container": "[C]",
            "Forensics": "[F]",
            "Reverse": "[F]",
            "Gaming": "[G]",
            "Media": "[M]",
            "Development": "[D]",
            "Terminal": "[T]",
            "Monitoring": "[S]",
            "Hardware": "[S]",
            "Privacy": "[V]",
            "Social": "[V]",
            "Virtualization": "[V]"
        }
        icon = next((value for key, value in category_icons.items() if key in title), "[+]")
        box = QFrame()
        box.setObjectName("packageCategory")
        box_lay = QVBoxLayout()
        box_lay.setContentsMargins(12, 8, 12, 8)
        box_lay.setSpacing(6)
        
        category_header = QHBoxLayout()
        category_title = QLabel(f"{icon}  {title}")
        category_title.setObjectName("categoryTitle")
        category_header.addWidget(category_title)
        category_header.addStretch()
        expand_button = QToolButton()
        expand_button.setText("Show packages")
        expand_button.setCheckable(True)
        expand_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        expand_button.setArrowType(Qt.ArrowType.RightArrow)
        expand_button.setStyleSheet(
            "QToolButton { color: #536074; padding: 4px 7px; "
            "border: 1px solid #cbd3de; border-radius: 5px; }"
            "QToolButton:hover { color: #1d2735; border-color: #8793a3; }"
        )
        category_header.addWidget(expand_button)
        box_lay.addLayout(category_header)
        
        grid_widget = QWidget()
        grid_lay = QGridLayout(grid_widget)
        grid_lay.setContentsMargins(0, 0, 0, 0)
        
        child_boxes = []
        for index, tool in enumerate(tools):
            chk = QCheckBox(tool)
            chk.setChecked(True)
            chk.stateChanged.connect(self.update_package_count)
            child_boxes.append(chk)
            self.tool_entries.append((chk, box, grid_widget))
            self.tool_groups.add(box)
            
            row = index // 2
            col = index % 2
            grid_lay.addWidget(chk, row, col)
            
        storage_dict[title] = child_boxes
        self.category_expanded[id(box)] = False
        self.category_toggle_buttons[id(box)] = expand_button
        self.category_grids[id(box)] = grid_widget

        expand_button.toggled.connect(
            lambda expanded, package_grid=grid_widget, group=box:
                self.toggle_category(expanded, package_grid, group)
        )
        
        grid_widget.setVisible(False)
        box_lay.addWidget(grid_widget)
        box.setLayout(box_lay)
        return box

    def set_active_packages_selected(self, checked):
        _profile, _kernel, groups = self.active_profile()
        blockers = []
        try:
            for group in groups.values():
                for checkbox in group:
                    blockers.append(QSignalBlocker(checkbox))
                    checkbox.setChecked(checked)
        finally:
            del blockers
        self.update_package_count()

    def update_package_selection_actions(self, _index=None):
        has_packages = bool(self.active_profile()[2])
        self.select_all_button.setEnabled(has_packages)
        self.clear_all_button.setEnabled(has_packages)

    def toggle_category(self, expanded, package_grid, group):
        self.category_expanded[id(group)] = expanded
        toggle_button = self.category_toggle_buttons[id(group)]
        toggle_button.setText("Hide packages" if expanded else "Show packages")
        toggle_button.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )
        package_grid.setVisible(expanded or bool(self.tool_search.text().strip()))
        self.filter_tools(self.tool_search.text())
        self.update_package_count()

    def schedule_tool_filter(self, _query):
        self.search_timer.start()

    def filter_tools(self, query):
        query = query.strip().lower()
        groups_with_matches = set()
        for checkbox, group, _package_grid in self.tool_entries:
            matches = not query or query in checkbox.text().lower()
            checkbox.setVisible(matches)
            if matches:
                groups_with_matches.add(id(group))

        for group in self.tool_groups:
            group_id = id(group)
            has_matches = group_id in groups_with_matches
            group.setVisible(not query or has_matches)
            toggle_button = self.category_toggle_buttons[group_id]
            toggle_button.setEnabled(not query)
            toggle_button.setText(
                "Search matches"
                if query and has_matches
                else (
                    "Hide packages"
                    if self.category_expanded.get(group_id, False)
                    else "Show packages"
                )
            )
            self.category_grids[group_id].setVisible(
                (bool(query) and has_matches)
                or self.category_expanded.get(group_id, False)
            )

    def update_package_count(self, _state=None):
        self.package_count_timer.start()

    def refresh_package_count(self):
        selected = self.get_selected_packages()
        count = len(selected)
        label = f"{count} package{'s' if count != 1 else ''} selected"
        if self.package_count_label.text() != label:
            self.package_count_label.setText(label)
        if (
            self.radio_expert.isChecked()
            and hasattr(self, "expert_profile_packages")
        ):
            self.expert_profile_packages.setText(
                f"{count} package{'s' if count != 1 else ''} available below"
            )
            self.update_expert_summary()

    def init_pentest_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        widget = QWidget()
        layout = QVBoxLayout(widget)

        sections = {
            "Recon & Information Gathering": ["nmap", "recon-ng", "subfinder", "amass", "theharvester", "masscan", "dnsrecon", "rustscan"],
            "Web Testing & Vulnerability": ["nikto", "burpsuite", "sqlmap", "gobuster", "ffuf", "nuclei", "zaproxy", "whatweb", "wpscan"],
            "Wireless & Network Analysis": ["aircrack-ng", "wifite", "wireshark-qt", "bettercap", "hcxdumptool", "hcxtools", "proxychains-ng", "openvpn"],
            "Password, Exploit & Utility": ["john", "hashcat", "hydra", "metasploit", "responder", "seclists", "wordlists", "enum4linux", "netexec"],
            "Network, Traffic & OSINT": ["tcpdump", "socat", "netcat", "whois", "bind", "smbclient", "bind-tools", "tor"],
            "Cloud & Container Security": ["aws-cli-v2", "kubectl", "trivy", "skopeo", "docker", "podman", "k9s", "yq"],
            "Forensics & Reverse Engineering": ["autopsy", "binwalk", "foremost", "sleuthkit", "volatility3", "yara", "radare2", "ghidra", "strace", "ltrace"],
            "Social Engineering & Privacy": ["set", "evilginx", "mitmproxy", "proxychains-ng", "tor", "torsocks", "macchanger", "hashcat"]
        }

        for sec_title, tools in sections.items():
            layout.addWidget(self.create_master_group(sec_title, tools, self.pentest_boxes))

        scroll.setWidget(widget)
        return scroll

    def init_daily_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        widget = QWidget()
        layout = QVBoxLayout(widget)

        sections = {
            "Gaming (Zen Kernel Tuned)": ["steam", "lutris", "wine-staging", "gamemode", "mangohud", "prismlauncher"],
            "Digital Workspace & Media": ["vlc", "obs-studio", "discord", "firefox", "chromium", "gimp", "kdenlive", "audacity", "krita"],
            "Productivity & Development": ["git", "neovim", "docker", "docker-compose", "python", "nodejs", "libreoffice-fresh", "gcc", "cmake", "rust", "go", "htop"],
            "Communication & File Tools": ["thunderbird", "filezilla", "qbittorrent", "signal-desktop", "rsync", "rclone", "curl", "wget"],
            "Terminal & System Utilities": ["alacritty", "tmux", "ripgrep", "fd", "bat", "fzf", "tree", "ncdu"],
            "Virtualization & Containers": ["virt-manager", "qemu-desktop", "libvirt", "virt-viewer", "podman-compose", "vagrant", "virtualbox"],
            "System Monitoring & Hardware": ["btop", "iotop", "nmon", "lm_sensors", "smartmontools", "nvtop", "sysstat", "pciutils"]
        }

        for sec_title, tools in sections.items():
            layout.addWidget(self.create_master_group(sec_title, tools, self.daily_boxes))

        scroll.setWidget(widget)
        return scroll

    def init_carma_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.carma_pentest_boxes = {}
        self.carma_daily_boxes = {}
        
        info_lbl = QLabel("Hybrid Environment Active: combined security and daily package groups.")
        info_lbl.setStyleSheet("color: #a61eff; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(info_lbl)

        kernel_info = QLabel(
            "Dual kernel host: Daily/Game (Zen) + CyberSEC (Linux)"
        )
        kernel_info.setStyleSheet(
            "color: #354154; font-weight: bold; padding: 6px;"
        )
        layout.addWidget(kernel_info)
        
        sections_p = {
            "Hybrid Suite - Recon": ["nmap", "recon-ng", "subfinder", "amass", "theharvester", "masscan", "dnsrecon", "rustscan"],
            "Hybrid Suite - Web Testing": ["nikto", "burpsuite", "sqlmap", "gobuster", "ffuf", "nuclei", "zaproxy", "whatweb", "wpscan"],
            "Hybrid Suite - Wireless": ["aircrack-ng", "wifite", "wireshark-qt", "bettercap", "hcxdumptool", "hcxtools", "proxychains-ng", "openvpn"],
            "Hybrid Suite - Passwords & Exploits": ["john", "hashcat", "hydra", "metasploit", "responder", "seclists", "wordlists", "enum4linux", "netexec"],
            "Hybrid Suite - Network & OSINT": ["tcpdump", "socat", "netcat", "whois", "bind", "smbclient", "bind-tools", "tor"],
            "Hybrid Suite - Cloud & Containers": ["aws-cli-v2", "kubectl", "trivy", "skopeo", "docker", "podman", "k9s", "yq"],
            "Hybrid Suite - Forensics & RE": ["autopsy", "binwalk", "foremost", "sleuthkit", "volatility3", "yara", "radare2", "ghidra", "strace", "ltrace"],
            "Hybrid Suite - Privacy & Social Testing": ["set", "evilginx", "mitmproxy", "proxychains-ng", "tor", "torsocks", "macchanger", "hashcat"]
        }
        for sec_title, tools in sections_p.items():
            layout.addWidget(self.create_master_group(sec_title, tools, self.carma_pentest_boxes))
            
        sections_d = {
            "Hybrid Suite - Gaming": ["steam", "lutris", "wine-staging", "gamemode", "mangohud", "prismlauncher"],
            "Hybrid Suite - Workspace & Media": ["vlc", "obs-studio", "discord", "firefox", "chromium", "gimp", "kdenlive", "audacity", "krita"],
            "Hybrid Suite - Development": ["git", "neovim", "docker", "docker-compose", "python", "nodejs", "libreoffice-fresh", "gcc", "cmake", "rust", "go", "htop"],
            "Hybrid Suite - Communication & Files": ["thunderbird", "filezilla", "qbittorrent", "signal-desktop", "rsync", "rclone", "curl", "wget"],
            "Hybrid Suite - Terminal Utilities": ["alacritty", "tmux", "ripgrep", "fd", "bat", "fzf", "tree", "ncdu"],
            "Hybrid Suite - Virtualization": ["virt-manager", "qemu-desktop", "libvirt", "virt-viewer", "podman-compose", "vagrant", "virtualbox"],
            "Hybrid Suite - Monitoring & Hardware": ["btop", "iotop", "nmon", "lm_sensors", "smartmontools", "nvtop", "sysstat", "pciutils"]
        }
        for sec_title, tools in sections_d.items():
            layout.addWidget(self.create_master_group(sec_title, tools, self.carma_daily_boxes))
            
        scroll.setWidget(widget)
        return scroll

    def init_expert_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        widget = QWidget()
        layout = QVBoxLayout(widget)

        target_layout = QGridLayout()
        target_layout.setColumnStretch(0, 1)
        target_layout.setColumnStretch(1, 1)

        kernel_label = QLabel("Target kernel")
        kernel_label.setStyleSheet("color: #a9520b; font-weight: bold; padding: 6px;")
        self.expert_kernel = QComboBox()
        self.expert_kernel.addItem("Linux Standard", "linux")
        self.expert_kernel.addItem("Linux Zen - Performance", "linux-zen")
        self.expert_kernel.addItem("Linux Hardened - Security", "linux-hardened")
        self.expert_kernel.addItem("Linux LTS - Stability", "linux-lts")
        self.expert_kernel.setCurrentIndex(2)
        self.expert_kernel.currentIndexChanged.connect(self.update_expert_kernel_style)
        self.expert_kernel.currentIndexChanged.connect(self.update_expert_summary)
        self.expert_kernel.setMinimumHeight(36)

        firewall_label = QLabel("Firewall (optional)")
        firewall_label.setStyleSheet("color: #a9520b; font-weight: bold; padding: 6px;")
        self.expert_firewall = QComboBox()
        self.expert_firewall.addItem("No firewall", "none")
        self.expert_firewall.addItem("UFW (deny incoming)", "ufw")
        self.expert_firewall.setMinimumHeight(36)
        self.expert_firewall.currentIndexChanged.connect(self.update_expert_flow_cards)
        self.expert_firewall.currentIndexChanged.connect(self.update_expert_summary)

        target_layout.addWidget(kernel_label, 0, 0)
        target_layout.addWidget(firewall_label, 0, 1)
        target_layout.addWidget(self.expert_kernel, 1, 0)
        target_layout.addWidget(self.expert_firewall, 1, 1)
        layout.addLayout(target_layout)

        package_row = QHBoxLayout()
        package_label = QLabel("Expert package profile")
        package_label.setStyleSheet("color: #ffb84d; font-weight: bold; padding: 6px;")
        self.expert_package_profile = QComboBox()
        self.expert_package_profile.addItem("None - no packages", "none")
        self.expert_package_profile.addItem("Pentest package set", "pentest")
        self.expert_package_profile.addItem("Daily package set", "daily")
        self.expert_package_profile.addItem("Carma package set", "carma")
        self.expert_package_profile.currentIndexChanged.connect(
            lambda _index: self.update_expert_package_groups(
                self.expert_package_profile.currentData()
            )
        )
        self.expert_package_profile.currentIndexChanged.connect(
            self.update_package_count
        )
        self.expert_package_profile.currentIndexChanged.connect(
            self.update_package_selection_actions
        )
        self.expert_package_profile.setMinimumHeight(36)
        self.expert_package_profile.setStyleSheet("""
            QComboBox {
                color: #253144;
                background-color: #ffffff;
                border: 1px solid #cbd3de;
                border-radius: 6px;
                padding: 6px 10px;
                min-width: 260px;
            }
            QComboBox QAbstractItemView {
                color: #253144;
                background-color: #ffffff;
                selection-background-color: #f8eadc;
                selection-color: #1d2735;
            }
        """)
        package_row.addWidget(package_label)
        package_row.addWidget(self.expert_package_profile)
        package_row.addStretch()
        layout.addLayout(package_row)

        self.expert_profile_card = QFrame()
        self.expert_profile_card.setObjectName("expertProfileCard")
        profile_card_layout = QVBoxLayout(self.expert_profile_card)
        profile_card_layout.setContentsMargins(14, 10, 14, 10)
        profile_card_layout.setSpacing(3)
        self.expert_profile_title = QLabel()
        self.expert_profile_title.setStyleSheet(
            "font-size: 16px; font-weight: bold;"
        )
        self.expert_profile_description = QLabel()
        self.expert_profile_description.setWordWrap(True)
        self.expert_profile_description.setStyleSheet(
            "color: #536074; font-size: 12px;"
        )
        self.expert_profile_packages = QLabel()
        self.expert_profile_packages.setStyleSheet(
            "color: #354154; font-size: 12px; font-weight: bold;"
        )
        profile_card_layout.addWidget(self.expert_profile_title)
        profile_card_layout.addWidget(self.expert_profile_description)
        profile_card_layout.addWidget(self.expert_profile_packages)
        layout.addWidget(self.expert_profile_card)

        self.expert_summary_card = QFrame()
        self.expert_summary_card.setObjectName("expertSummaryCard")
        summary_layout = QGridLayout(self.expert_summary_card)
        summary_layout.setContentsMargins(14, 10, 14, 10)
        summary_layout.setHorizontalSpacing(18)
        summary_layout.setVerticalSpacing(3)
        summary_title = QLabel("DEPLOYMENT SUMMARY")
        summary_title.setStyleSheet(
            "color: #a9520b; font-size: 11px; font-weight: bold;"
        )
        self.expert_summary_profile = QLabel()
        self.expert_summary_kernel = QLabel()
        self.expert_summary_packages = QLabel()
        self.expert_summary_target = QLabel("Packages → Host / ALGOL")
        for label in (
            self.expert_summary_profile,
            self.expert_summary_kernel,
            self.expert_summary_packages,
            self.expert_summary_target,
        ):
            label.setStyleSheet("color: #354154; font-size: 12px;")
        summary_layout.addWidget(summary_title, 0, 0, 1, 2)
        summary_layout.addWidget(self.expert_summary_profile, 1, 0)
        summary_layout.addWidget(self.expert_summary_kernel, 1, 1)
        summary_layout.addWidget(self.expert_summary_packages, 2, 0)
        summary_layout.addWidget(self.expert_summary_target, 2, 1)
        layout.addWidget(self.expert_summary_card)

        flow_layout = QHBoxLayout()
        self.expert_host_card = self.create_expert_flow_card(
            "HOST SYSTEM",
            "Kernel, desktop and disk setup",
            "#ff9f1c",
        )
        self.expert_algol_card = self.create_expert_flow_card(
            "ALGOL CONTAINER",
            "Verified security tools and BlackArch packages",
            "#a61eff",
        )
        flow_layout.addWidget(self.expert_host_card)
        flow_layout.addWidget(self.expert_algol_card)
        layout.addLayout(flow_layout)

        self.expert_ready_label = QLabel()
        self.expert_ready_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.expert_ready_label.setStyleSheet(
            "padding: 8px; font-weight: bold; color: #687588;"
        )
        layout.addWidget(self.expert_ready_label)

        package_info = QLabel(
            "Select or clear individual packages from the chosen profile below."
        )
        package_info.setWordWrap(True)
        package_info.setStyleSheet("color: #687588; padding: 8px 4px;")
        layout.addWidget(package_info)

        self.expert_package_sources = {
            "pentest": self.pentest_boxes,
            "daily": self.daily_boxes,
            "carma": self.carma_pentest_boxes | self.carma_daily_boxes,
        }
        self.expert_package_container = QWidget()
        self.expert_package_container_layout = QVBoxLayout(
            self.expert_package_container
        )
        self.expert_package_container_layout.setContentsMargins(0, 0, 0, 0)
        self.expert_package_container_layout.setSpacing(8)
        layout.addWidget(self.expert_package_container)

        scroll.setWidget(widget)
        self.update_expert_package_groups("none")
        self.update_expert_profile_card("none")
        self.update_expert_summary()
        self.update_expert_flow_cards()
        return scroll

    def create_expert_flow_card(self, title, subtitle, color):
        card = QFrame()
        card.setObjectName("expertFlowCard")
        card.setStyleSheet(
            f"""
            QFrame#expertFlowCard {{
                background-color: #ffffff;
                border: 1px solid {color};
                border-radius: 8px;
            }}
            """
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 9, 12, 9)
        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {color}; font-weight: bold; font-size: 12px;"
        )
        subtitle_label = QLabel(subtitle)
        subtitle_label.setWordWrap(True)
        subtitle_label.setStyleSheet("color: #687588; font-size: 11px;")
        detail_label = QLabel()
        detail_label.setWordWrap(True)
        detail_label.setStyleSheet("color: #354154; font-size: 12px;")
        card_layout.addWidget(title_label)
        card_layout.addWidget(subtitle_label)
        card_layout.addWidget(detail_label)
        card.detail_label = detail_label
        return card

    def active_profile(self):
        if self.radio_pentest.isChecked():
            return "pentest", "linux", self.pentest_boxes
        if self.radio_daily.isChecked():
            return "daily", "linux-zen", self.daily_boxes
        if self.radio_carma.isChecked():
            groups = {**self.carma_pentest_boxes, **self.carma_daily_boxes}
            return "carma", "linux-zen,linux", groups
        if self.radio_expert.isChecked():
            package_profile = self.expert_package_profile.currentData()
            groups = {
                str(id(group)): self.expert_package_widget_boxes[group]
                for group in self.expert_package_groups.get(package_profile, [])
            }
            return "expert", self.expert_kernel.currentData(), groups
        return None, None, {}

    def update_expert_package_groups(self, profile_name):
        if profile_name != "none" and \
           profile_name not in self.built_expert_package_profiles:
            source_groups = self.expert_package_sources.get(profile_name, {})
            for title, source_checkboxes in source_groups.items():
                tools = [checkbox.text() for checkbox in source_checkboxes]
                group_title = f"Expert {profile_name.title()} - {title}"
                group = self.create_master_group(
                    group_title, tools, self.expert_boxes
                )
                self.expert_package_groups.setdefault(profile_name, []).append(group)
                self.expert_package_widgets.append(group)
                self.expert_package_widget_boxes[group] = \
                    self.expert_boxes[group_title]
                self.expert_package_container_layout.addWidget(group)
            self.built_expert_package_profiles.add(profile_name)

        visible_groups = {
            id(group)
            for group in self.expert_package_groups.get(profile_name, [])
        }
        for group in self.expert_package_widgets:
            group.setVisible(id(group) in visible_groups)
        self.update_expert_profile_card(profile_name)

    def update_expert_profile_card(self, profile_name):
        profiles = {
            "none": (
                "NONE",
                "Expert settings only; no Algol packages will be installed.",
                "#6b7280",
            ),
            "pentest": (
                "PENTEST PACKAGE SET",
                "Recon, web testing, wireless and offensive security tools.",
                "#ff1e27",
            ),
            "daily": (
                "DAILY PACKAGE SET",
                "Desktop, gaming, media, development and productivity tools.",
                "#1e77ff",
            ),
            "carma": (
                "CARMA PACKAGE SET",
                "The complete Pentest and Daily package collection.",
                "#a61eff",
            ),
        }
        title, description, color = profiles.get(
            profile_name, profiles["none"]
        )
        package_count = len(self.get_selected_packages()) if hasattr(
            self, "expert_package_widgets"
        ) else 0
        self.expert_profile_title.setText(title)
        self.expert_profile_title.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {color};"
        )
        self.expert_profile_description.setText(description)
        self.expert_profile_packages.setText(
            f"{package_count} package{'s' if package_count != 1 else ''} "
            "available below"
        )
        self.update_expert_summary()

    def update_expert_summary(self):
        if not hasattr(self, "expert_summary_profile"):
            return
        profile_name = self.expert_package_profile.currentData()
        profile_labels = {
            "none": "None",
            "pentest": "Pentest",
            "daily": "Daily",
            "carma": "Carma",
        }
        package_count = len(self.get_selected_packages())
        self.expert_summary_profile.setText(
            f"Profile: Expert + {profile_labels.get(profile_name, 'None')}"
        )
        self.expert_summary_kernel.setText(
            f"Kernel: {self.expert_kernel.currentData()}"
        )
        firewall = self.expert_firewall.currentData()
        firewall_label = "UFW" if firewall == "ufw" else "Off"
        self.expert_summary_target.setText(
            f"LightDM + XFCE  •  Firewall: {firewall_label}"
        )
        self.expert_summary_packages.setText(
            f"Packages: {package_count} selected"
        )
        self.update_expert_flow_cards()

    def update_expert_flow_cards(self):
        if not hasattr(self, "expert_host_card"):
            return
        kernel = self.expert_kernel.currentData()
        firewall = self.expert_firewall.currentData()
        firewall_label = "UFW (deny incoming)" if firewall == "ufw" else "Off"
        package_profile = self.expert_package_profile.currentData()
        package_count = len(self.get_selected_packages())
        self.expert_host_card.detail_label.setText(
            f"Kernel: {kernel}\n"
            "Desktop: XFCE + LightDM\n"
            f"Firewall: {firewall_label}\n"
            "Filesystem and bootloader: choose in Calamares"
        )
        self.expert_algol_card.detail_label.setText(
            f"Profile: {package_profile.title()}\n"
            f"Packages: {package_count}\n"
            "Repository: BlackArch"
        )
        ready = package_profile != "none" and package_count > 0
        if ready:
            self.expert_ready_label.setText(
                "✓ READY TO DEPLOY  •  Host system + Algol container configured"
            )
        else:
            self.expert_ready_label.setText(
                "✓ READY TO DEPLOY  •  Expert kernel and host configuration only"
            )

    def get_selected_packages(self):
        _profile, _kernel, groups = self.active_profile()
        selected = []
        selected_names = set()
        for group in groups.values():
            for checkbox in group:
                package = checkbox.text()
                if checkbox.isChecked() and package not in selected_names:
                    selected.append(package)
                    selected_names.add(package)
        return selected

    def write_selection_file(self, path):
        profile, kernel, _groups = self.active_profile()
        packages = self.get_selected_packages()
        if not profile:
            return False
        firewall = (
            self.expert_firewall.currentData()
            if profile == "expert"
            else "none"
        )

        with open(path, "w", encoding="utf-8") as selection:
            selection.write(f"PROFILE:{profile}\n")
            selection.write(
                f"KERNELS:{kernel}\n" if "," in kernel else f"KERNEL:{kernel}\n"
            )
            selection.write(
                "DISPLAY_MANAGER:lightdm\n"
            )
            selection.write(f"FIREWALL:{firewall}\n")
            selection.write(f"PACKAGES:{','.join(packages)}\n")
            community_targets = getattr(
                self, "community_install_targets", {}
            )

            community_host = sorted(
                package
                for package, target in community_targets.items()
                if target == "host"
            )

            community_algol = sorted(
                package
                for package, target in community_targets.items()
                if target == "algol"
            )

            selection.write(
                f"COMMUNITY_HOST:{','.join(community_host)}\n"
            )
            selection.write(
                f"COMMUNITY_ALGOL:{','.join(community_algol)}\n"
            )
        return True

    def validate_packages(self, packages):
        pacman_path = "/usr/bin/pacman"
        if not packages or not os.path.exists(pacman_path):
            return True

        try:
            result = subprocess.run(
                [pacman_path, "-Si", *packages],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
                env={**os.environ, "LC_ALL": "C"},
            )
        except (OSError, subprocess.TimeoutExpired):
            return True

        found = set(re.findall(r"^Name\s*:\s*(\S+)", result.stdout, re.MULTILINE))
        missing = [package for package in packages if package not in found]
        if not missing:
            return True

        message = "These packages were not found in the currently enabled repositories:\n\n"
        message += ", ".join(missing[:16])
        if len(missing) > 16:
            message += f"\n... and {len(missing) - 16} more"
        message += (
            "\n\nContinue anyway? BlackArch packages may resolve inside Algol after "
            "its repository is configured. AUR packages are not built automatically."
        )
        answer = QMessageBox.question(
            self,
            "Package availability warning",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        return answer == QMessageBox.StandardButton.Yes

    def show_install_summary(self, packages, kernel):
        profile, _kernel, _groups = self.active_profile()
        preview = ", ".join(packages[:24])
        if len(packages) > 24:
            preview += f", ... ({len(packages) - 24} more)"
        summary = (
            f"Profile: {profile}\n"
            f"Kernel: {kernel}\n"
            f"Packages: {len(packages)}\n\n"
            f"{preview or 'No packages selected'}"
        )
        if profile == "expert":
            summary += "\n\nDesktop: XFCE + LightDM\nFilesystem: choose in Calamares"
        answer = QMessageBox.question(
            self,
            "Review deployment",
            summary,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        return answer == QMessageBox.StandardButton.Yes

    def save_profile(self):
        profile, _kernel, _groups = self.active_profile()
        if not profile:
            QMessageBox.warning(self, "Deployment mode required", "Select a profile before saving it.")
            return

        profile_dir = os.path.expanduser("~/alcor-profiles")
        os.makedirs(profile_dir, exist_ok=True)
        profile_path = os.path.join(profile_dir, f"{profile}.conf")
        self.write_selection_file(profile_path)
        QMessageBox.information(self, "Profile saved", f"Profile saved to:\n{profile_path}")

    def save_and_launch(self):
        profile, kernel, _groups = self.active_profile()
        if not profile:
            QMessageBox.warning(self, "Deployment mode required", "Select a deployment mode before continuing.")
            return

        packages = self.get_selected_packages()
        if not packages and not (
            profile == "expert"
            and self.expert_package_profile.currentData() == "none"
        ):
            QMessageBox.warning(self, "No packages selected", "Select at least one package before continuing.")
            return
        if not self.validate_packages(packages) or not self.show_install_summary(packages, kernel):
            return

        self.write_selection_file(self.selection_file)

        self.btn_launch.setEnabled(False)
        self.launch_progress = QProgressDialog("Starting Calamares...", None, 0, 0, self)
        self.launch_progress.setWindowTitle("Alcor Deployment")
        self.launch_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.launch_progress.setCancelButton(None)
        self.launch_progress.show()
        QApplication.processEvents()
        try:
            calamares_command = " ".join([
                "sudo",
                "env",
                shlex.quote(f"ALCOR_SELECTION_FILE={self.selection_file}"),
                "calamares",
            ])
            subprocess.Popen([
                "xfce4-terminal",
                "--hold",
                "--command",
                calamares_command,
            ])
            QTimer.singleShot(900, self.launch_progress.close)
            QTimer.singleShot(1000, self.close)
        except OSError as error:
            self.launch_progress.close()
            self.btn_launch.setEnabled(True)
            QMessageBox.critical(self, "Calamares could not start", str(error))
            ##
    def init_community_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header
        title = QLabel("ALCOR COMMUNITY")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "font-size: 25px; font-weight: 800; color: #192536;"
            "letter-spacing: 1px;"
        )
        layout.addWidget(title)

        subtitle = QLabel("Community Projects & Tools")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(
            "font-size: 17px; font-weight: 800; color: #d97716;"
        )
        layout.addWidget(subtitle)

        description = QLabel(
            "Discover libraries, tools and projects developed by the community."
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        layout.addWidget(description)

        # Prominent notice for independently maintained community projects.
        security_notice = QFrame()
        security_notice.setObjectName("communitySecurityNotice")
        notice_layout = QVBoxLayout(security_notice)
        notice_layout.setContentsMargins(14, 12, 14, 12)
        notice_layout.setSpacing(6)

        security_title = QLabel("IMPORTANT SECURITY NOTICE — THIRD-PARTY SOFTWARE")
        security_title.setObjectName("communitySecurityTitle")
        notice_layout.addWidget(security_title)

        security_body = QLabel(
            "Community projects are maintained independently and may change "
            "after an Alcor release. Review the source code, installation scripts, "
            "package commands and upstream change history before downloading or "
            "running anything. Selecting CZA downloads and runs its upstream "
            "installer with system-wide permissions in the Host or Algol target "
            "you choose. If you are unsure, do not install it on the Host — skip it. "
            "Algol is rootful and host-integrated, not a security boundary. Alcor "
            "does not audit, maintain or guarantee third-party projects; use them "
            "at your own risk."
        )
        security_body.setObjectName("communitySecurityBody")
        security_body.setWordWrap(True)
        notice_layout.addWidget(security_body)
        layout.addWidget(security_notice)

        # Logo directory
        community_dir = os.path.join(self.logo_dir, "comminty")

        if not os.path.isdir(community_dir):
            community_dir = os.path.join(self.logo_dir, "community")

        # Community projects and README summaries
        community_tools = [
            {
                "name": "LightPacket",
                "package": "lightpacket",
                "logo": "LightPacket-Logo.png",
                "github": "https://github.com/Light-Projects/LightPacket",

                "description": "Python Packet Manipulation Library",

                "readme": """
                <h3>Overview</h3>

                <p>
                LightPacket is a Python library designed for building,
                dissecting, capturing and replaying network packets.
                It combines a Scapy-style layered packet model with
                protocol dissection, filtering and capture utilities.
                </p>

                <h3>Packet Construction and Dissection</h3>

                <p>
                Packets can be constructed by stacking protocol layers
                with the <b>/</b> operator and serialized into
                wire-format bytes using the build interface.
                Incoming raw frames can be inspected through
                DetectLayer, with access to packet layers and fields.
                </p>

                <h3>Protocol Coverage</h3>

                <ul>
                    <li>Ethernet II, VLAN and QinQ</li>
                    <li>ARP, LLC, STP and Linux cooked capture</li>
                    <li>IPv4, IPv6, TCP and UDP</li>
                    <li>PPP, PPPoE and EAPOL</li>
                    <li>IEEE 802.11 wireless frame layers</li>
                </ul>

                <h3>Filtering and LightBPF Integration</h3>

                <p>
                LightPacket integrates the LightBPF classic Berkeley
                Packet Filter engine. Filters can be compiled and
                evaluated in Python, or attached to supported Linux
                sockets through SO_ATTACH_FILTER.
                </p>

                <h3>Live Capture and Socket Backends</h3>

                <ul>
                    <li>
                    <b>Sniffer:</b> Streaming capture with callbacks,
                    packet limits, timeouts and filtering.
                    </li>
                    <li>
                    <b>L2Socket:</b> libpcap/Npcap-backed Layer 2 socket.
                    </li>
                    <li>
                    <b>L2Packet:</b> Linux AF_PACKET implementation.
                    </li>
                </ul>

                <p>
                Backend selection depends on the operating system and
                available system facilities.
                </p>

                <h3>PCAP, PCAPNG and Replay</h3>

                <p>
                Pure-Python modules support reading and writing PCAP
                and PCAPNG capture files without requiring a native
                capture library for file operations. The replay
                utilities support configurable timing, loops and jitter.
                </p>

                <h3>Installation Requirements</h3>

                <p>
                Python 3.8 or later. Live capture has additional
                platform-specific requirements. Linux raw packet
                operations may require elevated privileges or
                appropriate capabilities. Windows requires Npcap
                for the libpcap-compatible backend.
                </p>

                <p>
                <b>Version noted in the existing Alcor summary:</b> 1.0.4<br>
                <b>Latest PyPI release observed:</b> 1.0.3 (2026-11-06; verify the version-source difference)<br>
                <b>Latest GitHub commit:</b> 2026-11-14 23:50 (+03:00), <b>55cedad8</b><br>
                <b>Files changed in that commit:</b> BaseLayer.py, Dot3.py, EthernetII.py,
                LLC.py, Layers/register.py, Wireless/wlan.py, ipv4.py, ipv6.py,
                platforms/linux/sll.py, ppp.py, tcp.py, tests/test_register.py, udp.py<br>
                <b>GitHub commit signature:</b> unsigned<br>
                <b>Alcor tracking baseline:</b> 2026-11-20<br>
                <b>License:</b> Mozilla Public License 2.0
                </p>
                """,

                "install": "pip install lightpacket"
            },

            {
                "name": "LightBPF",
                "package": "lightbpf",
                "logo": "LightBPF.svg",
                "github": "https://github.com/Light-Projects/LightBPF",

                "description": "Pure-Python Berkeley Packet Filter Engine",

                "readme": """
                <h3>Overview</h3>

                <p>
                LightBPF is a standalone, pure-Python Berkeley Packet
                Filter engine for packet inspection, filtering and
                network security applications. It implements the
                classic BPF pipeline without requiring native C
                dependencies.
                </p>

                <h3>Compiler Architecture</h3>

                <p>
                The engine processes filter expressions through a
                complete compilation pipeline:
                </p>

                <ul>
                    <li><b>Lexer:</b> Tokenizes filter expressions.</li>
                    <li><b>Parser:</b> Builds an Abstract Syntax Tree.</li>
                    <li><b>Compiler:</b> Generates classic BPF instructions.</li>
                    <li><b>Disassembler:</b> Converts bytecode into readable instructions.</li>
                    <li><b>Emulator:</b> Executes compiled filters in Python.</li>
                </ul>

                <h3>Protocol and Filter Support</h3>

                <ul>
                    <li>IPv4 and IPv6 dual-stack filtering</li>
                    <li>TCP, UDP, ICMP, ARP and Ethernet</li>
                    <li>VLAN and MPLS expressions</li>
                    <li>Host, network, source and destination filters</li>
                    <li>Port and port-range filtering</li>
                    <li>Raw packet byte access and arithmetic expressions</li>
                    <li>TCP flags and ICMP type fields</li>
                </ul>

                <h3>Offline Packet Filtering</h3>

                <p>
                BpfEmulator can execute compiled filters directly
                against raw packet bytes in Python. This makes it
                possible to test filtering logic without opening
                raw sockets or requiring root privileges.
                </p>

                <h3>Linux Kernel Integration</h3>

                <p>
                Compiled filters can be packaged into Linux
                sock_fprog structures and attached to supported
                raw sockets using SO_ATTACH_FILTER.
                Actual raw socket operations still require
                appropriate system permissions.
                </p>

                <h3>Compiler Optimizations</h3>

                <ul>
                    <li>Short-circuit boolean control flow</li>
                    <li>Relative jump resolution and jump threading</li>
                    <li>Register spilling through scratch memory</li>
                    <li>Dynamic IPv4 header-length tracking</li>
                    <li>VLAN offset handling</li>
                    <li>BPF_JSET bitmask optimization</li>
                    <li>AST algebraic optimization</li>
                    <li>Compiler state isolation</li>
                </ul>

                <h3>Additional Platform Support</h3>

                <p>
                The supplied 1.2.1 release notes describe BSD
                kernel structure support, PPP and PPPoE protocol
                handling, and additional compiler optimizations.
                </p>

                <h3>Dependencies and License</h3>

                <p>
                The core filtering engine is implemented in pure
                Python and does not require libpcap, GCC or an
                external native BPF compiler for offline operations.
                </p>

                <p>
                <b>Version stated in the supplied release-note summary:</b> 1.2.1<br>
                <b>Latest PyPI release observed:</b> 1.0.0 (2026-09-24; verify the version-source difference)<br>
                <b>Latest GitHub commit:</b> 2026-11-13 00:12 (+03:00), <b>326fb0bc</b><br>
                <b>Files changed in that commit:</b> SECURITY.md<br>
                <b>GitHub commit signature:</b> unsigned<br>
                <b>Alcor tracking baseline:</b> 2026-11-20<br>
                <b>License:</b> Mozilla Public License 2.0
                </p>
                """,

                "install": "pip install lightbpf"
            },
            {
                "name": "CZA",
                "package": "cza",
                "install_kind": "shell_script",
                "logo": "",
                "logo_text": "CZA",
                "github": "https://gitlab.com/ranonimolan/cza",
                "description": "Modern terminal application catalogue and installer",
                "readme": """
                <h3>Overview</h3>
                <p>
                CZA is an independently maintained command-line application
                catalogue and installer. It provides package search, package
                information, install/removal commands, catalogue updates and
                English/Turkish language selection.
                </p>

                <h3>Alcor Integration</h3>
                <p>
                Selecting CZA adds the CZA command-line client to the chosen
                installation target. Choose <b>Host</b> or <b>Algol</b> when
                prompted. Alcor invokes the upstream installer with
                <b>--global</b> inside that selected target; it does not
                automatically install any applications from CZA's catalogue.
                </p>

                <h3>Security Review Notes</h3>
                <ul>
                    <li>
                    The upstream installer is fetched from the mutable
                    <b>main</b> branch. The reviewed installer did not show
                    checksum or signature verification for the downloaded binary.
                    </li>
                    <li>
                    CZA retrieves its package catalogues from the upstream
                    repository. Catalogue entries can change independently of
                    the Alcor ISO.
                    </li>
                    <li>
                    The reviewed CZA source passes a catalogue-provided install
                    command to <b>/bin/bash -c</b> after asking for confirmation.
                    Treat catalogue commands as executable code, not harmless metadata.
                    </li>
                    <li>
                    The <b>--global</b> mode installs system-wide in the selected
                    target. Host means the installed Host system. Algol is a
                    rootful, host-integrated container and is not a security boundary.
                    </li>
                </ul>

                <h3>Tracked Upstream Revision</h3>
                <p>
                <b>Alcor Community entry added:</b> 2026-11-20<br>
                <b>Latest upstream commit observed:</b> 2026-11-14 21:46 (+03:00),
                <b>ec90216f</b> — binary size update.<br>
                <b>install.sh last changed:</b> 2026-10-17 14:25 (+03:00),
                <b>1d56e731</b>.<br>
                <b>src/ops.rs last changed:</b> 2026-11-14 19:31 (+03:00),
                <b>a8776acb</b>.<br>
                <b>packages-en.json last changed:</b> 2026-11-14.<br>
                <b>dist/cza-linux-x86_64 last changed:</b> 2026-11-14 21:46 (+03:00),
                <b>ec90216f</b>.<br>
                <b>Version in Cargo.toml:</b> 0.1.2<br>
                <b>License:</b> BSD-3-Clause
                </p>
                <p>
                These are upstream timestamps observed on 2026-11-20, not a
                security audit or a guarantee that remote files remain unchanged.
                See COMMUNITY_CHANGELOG.md for Alcor's recorded review baseline.
                </p>
                """,
            }
        ]

        self.community_install_targets = {}

        # Projects container
        tools_card = QFrame()
        tools_card.setObjectName("packageCategory")

        tools_layout = QVBoxLayout(tools_card)
        tools_layout.setContentsMargins(16, 16, 16, 16)
        tools_layout.setSpacing(15)

        category_title = QLabel("COMMUNITY PROJECTS")
        category_title.setStyleSheet(
            "font-size: 15px; font-weight: 800; color: #d97716;"
        )
        tools_layout.addWidget(category_title)

        for tool in community_tools:
            card = QFrame()
            card.setObjectName("communityToolCard")
            card.setStyleSheet("""
                QFrame#communityToolCard {
                    background-color: #ffffff;
                    border: 1px solid #d5dce5;
                    border-radius: 9px;
                }
            """)

            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 14, 14, 14)
            card_layout.setSpacing(10)

            # Logo + checkbox header
            header = QHBoxLayout()
            header.setSpacing(18)

            logo_label = QLabel()
            logo_label.setFixedSize(100, 100)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            logo_path = os.path.join(
                community_dir,
                tool["logo"]
            )

            logo_icon = QIcon(logo_path)

            if not logo_icon.isNull():
                logo_label.setPixmap(
                    logo_icon.pixmap(QSize(88, 88))
                )
            else:
                logo_label.setText(tool.get("logo_text", "LOGO"))
                logo_label.setStyleSheet(
                    "color: #9aa5b5; border: 1px dashed #cbd3de;"
                )

            header.addWidget(logo_label)

            external_only = bool(tool.get("external_only"))
            checkbox = None
            if external_only:
                project_name = QLabel(tool["name"])
                project_name.setObjectName("communityExternalProjectTitle")
                project_name.setMinimumHeight(55)
                project_name.setAlignment(
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                )
                project_name.setStyleSheet(
                    "font-size: 18px; font-weight: 900; color: #253144; padding: 8px;"
                )
                manual_badge = QLabel("MANUAL REVIEW ONLY")
                manual_badge.setObjectName("communityManualReviewBadge")
                manual_badge.setStyleSheet(
                    "color: #9a3412; background: #ffedd5; border: 1px solid #fdba74;"
                    "border-radius: 5px; padding: 5px 8px; font-size: 10px; font-weight: 900;"
                )
                header.addWidget(project_name, 1)
                header.addWidget(manual_badge)
            else:
                checkbox = QCheckBox(tool["name"])
                checkbox.setMinimumHeight(55)
                checkbox.setStyleSheet("""
                    QCheckBox {
                        font-size: 17px;
                        font-weight: 800;
                        color: #253144;
                        spacing: 10px;
                        padding: 8px;
                    }
                """)
                header.addWidget(checkbox, 1)

            card_layout.addLayout(header)

            short_description = QLabel(tool["description"])
            short_description.setWordWrap(True)
            short_description.setStyleSheet(
                "color: #d97716; font-size: 13px; "
                "font-weight: 700; padding-left: 5px;"
            )
            card_layout.addWidget(short_description)

            # Detailed README information
            
            # Show / Hide details button
            details_button = QPushButton("Show details")
            details_button.setCheckable(True)
            details_button.setChecked(False)
            card_layout.addWidget(details_button)

            # Detailed README information
            details = QLabel(tool["readme"])
            details.setTextFormat(Qt.TextFormat.RichText)
            details.setWordWrap(True)
            details.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            details.setStyleSheet("""
                QLabel {
                    color: #354154;
                    background-color: #f7f8fa;
                    border: 1px solid #e1e5eb;
                    border-radius: 7px;
                    padding: 12px;
                }
            """)
            details.hide()
            card_layout.addWidget(details)

            # Explicit clickable GitHub button
            repo_button = QPushButton(
                "↗  Open Project Repository"
            )
            repo_button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )
            repo_button.setStyleSheet("""
                QPushButton {
                    color: #ffffff;
                    background-color: #a96410;
                    border: 1px solid #a96410;
                    border-radius: 6px;
                    padding: 9px 14px;
                    font-weight: 700;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #c27b1a;
                    border-color: #c27b1a;
                }
            """)
            repo_button.clicked.connect(
                lambda _checked=False, url=tool["github"]:
                QDesktopServices.openUrl(QUrl(url))
            )
            repo_button.hide()
            card_layout.addWidget(repo_button)

            # Show / Hide behavior
            def toggle_details(
                expanded,
                info=details,
                repository=repo_button,
                button=details_button
            ):
                info.setVisible(expanded)
                repository.setVisible(expanded)
                button.setText(
                    "Hide details" if expanded else "Show details"
                )

            details_button.toggled.connect(toggle_details)

            target_label = QLabel()
            target_label.setStyleSheet(
                "color: #d97716; font-weight: 800; padding: 4px;"
            )
            target_label.hide()
            card_layout.addWidget(target_label)

            if not external_only:
                # Selection and installation target dialog
                def handle_selection(
                    checked,
                    item=tool,
                    checkbox_widget=checkbox,
                    target_status=target_label,
                    details_toggle=details_button
                ):
                    if not checked:
                        self.community_install_targets.pop(
                            item["package"], None
                        )
                        details_toggle.setChecked(False)
                        target_status.hide()
                        return

                    details_toggle.setChecked(True)

                    if item.get("install_kind") == "shell_script":
                        approval = QMessageBox.warning(
                            self,
                            "Third-party installer execution",
                            "CZA is installed by downloading and executing its "
                            "upstream install.sh script with --global. The script "
                            "comes from the mutable GitLab main branch and installs "
                            "system-wide in the target you choose. Review the current "
                            "script first. Algol is rootful and host-integrated, not "
                            "a security boundary. Continue to choose a target?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                            QMessageBox.StandardButton.No,
                        )
                        if approval != QMessageBox.StandardButton.Yes:
                            checkbox_widget.blockSignals(True)
                            checkbox_widget.setChecked(False)
                            checkbox_widget.blockSignals(False)
                            details_toggle.setChecked(False)
                            target_status.hide()
                            return

                    dialog = QMessageBox(self)
                    dialog.setWindowTitle("Installation Target")
                    dialog.setText(
                        f'Where should {item["name"]} be installed?'
                    )
                    if item.get("install_kind") == "shell_script":
                        dialog.setInformativeText(
                            "CZA will run its upstream installer with --global "
                            "inside the selected target. Host = installed Host; "
                            "Algol = rootful Distrobox environment."
                        )
                    else:
                        dialog.setInformativeText(
                            "Choose the Python installation environment."
                        )

                    algol_button = dialog.addButton(
                        "Algol",
                        QMessageBox.ButtonRole.AcceptRole
                    )
                    host_button = dialog.addButton(
                        "Host",
                        QMessageBox.ButtonRole.AcceptRole
                    )
                    dialog.addButton(
                        "Cancel",
                        QMessageBox.ButtonRole.RejectRole
                    )

                    dialog.exec()
                    selected = dialog.clickedButton()

                    if selected == algol_button:
                        target = "algol"
                    elif selected == host_button:
                        target = "host"
                    else:
                        checkbox_widget.blockSignals(True)
                        checkbox_widget.setChecked(False)
                        checkbox_widget.blockSignals(False)

                        details_toggle.setChecked(False)
                        target_status.hide()
                        return

                    self.community_install_targets[
                        item["package"]
                    ] = target

                    target_status.setText(
                        f'INSTALL TARGET: {target.upper()}'
                    )
                    target_status.show()

                checkbox.toggled.connect(handle_selection)

            tools_layout.addWidget(card)

        layout.addWidget(tools_card)

        # Community contribution footer
        footer = QFrame()
        footer.setObjectName("communityContributionCard")

        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 14, 16, 14)
        footer_layout.setSpacing(14)

        footer_text_layout = QVBoxLayout()
        footer_text_layout.setSpacing(5)

        footer_title = QLabel(
            "Want to add your tool to Alcor Community?"
        )
        footer_title.setObjectName("communityContributionText")
        footer_title.setStyleSheet("font-size: 14px;")

        footer_description = QLabel(
            "Join our community and share your project with us."
        )
        footer_description.setObjectName("communityContributionHint")
        footer_description.setWordWrap(True)

        footer_text_layout.addWidget(footer_title)
        footer_text_layout.addWidget(footer_description)

        discord_button = QPushButton("Discord Community")
        discord_button.setObjectName("communityDiscordButton")
        discord_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        # Replace this with your actual website URL.
        community_website_url = "https://alcorlinux.netlify.app/"

        def open_community_website():
            if not community_website_url:
                QMessageBox.information(
                    self,
                    "Website URL",
                    "Set your website URL in init_community_ui()."
                )
                return

            QDesktopServices.openUrl(QUrl(community_website_url))

        discord_button.clicked.connect(open_community_website)

        footer_layout.addLayout(footer_text_layout, 1)
        footer_layout.addWidget(discord_button)

        layout.addWidget(footer)
        layout.addStretch(1)

        scroll.setWidget(page)
        return scroll


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = AlcorFrontend()
    win.show()
    sys.exit(app.exec())