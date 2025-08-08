import sys
import os
import json
import subprocess
import ctypes
import random
import urllib.parse
from typing import List, Dict, Optional, Tuple
from pathlib import Path

import psutil
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QLineEdit, QTextEdit, QGroupBox,
    QScrollArea, QFrame, QMessageBox, QProgressBar, QTabWidget,
    QListWidget, QListWidgetItem, QDialog, QFormLayout, QDialogButtonBox,
    QSplitter, QStatusBar, QMenuBar, QMenu, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor, QAction, QPixmap

try:
    from auth import RobloxAuth
except ImportError:
    print("Warning: auth.py not found. Authentication features will be disabled.")
    RobloxAuth = None


class ModernButton(QPushButton):
    """Modern styled button with hover effects."""
    
    def __init__(self, text: str, primary: bool = False):
        super().__init__(text)
        self.primary = primary
        self.setup_style()
    
    def setup_style(self):
        """Setup button styling."""
        if self.primary:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 6px;
                    font-weight: 600;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                    color: #666666;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #f3f2f1;
                    color: #323130;
                    border: 1px solid #d2d0ce;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #edebe9;
                    border-color: #c7c6c4;
                }
                QPushButton:pressed {
                    background-color: #e1dfdd;
                }
                QPushButton:disabled {
                    background-color: #f3f2f1;
                    color: #a19f9d;
                    border-color: #edebe9;
                }
            """)


class ModernGroupBox(QGroupBox):
    """Modern styled group box."""
    
    def __init__(self, title: str):
        super().__init__(title)
        self.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                font-size: 14px;
                color: #323130;
                border: 2px solid #d2d0ce;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                background-color: white;
            }
        """)


class ModernTextEdit(QTextEdit):
    """Modern styled text edit with dark theme."""
    
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #464647;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                selection-background-color: #264f78;
            }
        """)


class AccountDialog(QDialog):
    """Dialog for adding/editing account information."""
    
    def __init__(self, parent=None, account_data=None):
        super().__init__(parent)
        self.account_data = account_data
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle("Add Account" if not self.account_data else "Edit Account")
        self.setModal(True)
        self.resize(400, 200)
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.description_edit = QLineEdit()
        self.cookie_edit = QLineEdit()
        self.cookie_edit.setEchoMode(QLineEdit.EchoMode.Password)
        
        if self.account_data:
            self.name_edit.setText(self.account_data.get('name', ''))
            self.description_edit.setText(self.account_data.get('description', ''))
            self.cookie_edit.setText(self.account_data.get('cookie', ''))
        
        form_layout.addRow("Name:", self.name_edit)
        form_layout.addRow("Description:", self.description_edit)
        form_layout.addRow("Cookie:", self.cookie_edit)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_account_data(self) -> Dict:
        """Get the account data from the form."""
        return {
            'name': self.name_edit.text(),
            'description': self.description_edit.text(),
            'cookie': self.cookie_edit.text()
        }


class RobloxProcessWorker(QThread):
    """Worker thread for managing Roblox processes."""
    
    process_started = pyqtSignal(int, str)  # PID, description
    process_failed = pyqtSignal(str)  # Error message
    log_message = pyqtSignal(str)  # Log message
    
    def __init__(self, exe_path: str, auth_ticket: str, place_id: str = None,
                 job_id: str = None, private_server_link: str = None):
        super().__init__()
        self.exe_path = exe_path
        self.auth_ticket = auth_ticket
        self.place_id = place_id
        self.job_id = job_id
        self.private_server_link = private_server_link
    
    def run(self):
        """Launch Roblox process."""
        try:
            self.log_message.emit("Starting Roblox process...")
            
            if self.place_id:
                browser_tracker_id = random.randint(100000000, 9999999999999)
                
                # Construct the base PlaceLauncher URL based on join type
                if self.private_server_link:
                    launcher_url = (
                        f'https://assetgame.roblox.com/game/PlaceLauncher.ashx'
                        f'?placeId={self.place_id}'
                        f'&accessCode={self.private_server_link}'
                        f'&request=RequestPrivateGame'
                    )
                    self.log_message.emit(f"Joining private server with code: {self.private_server_link}")
                elif self.job_id:
                    launcher_url = (
                        f'https://assetgame.roblox.com/game/PlaceLauncher.ashx'
                        f'?placeId={self.place_id}'
                        f'&gameId={self.job_id}'
                        f'&request=RequestGame'
                    )
                    self.log_message.emit("Joining specific server instance")
                else:
                    launcher_url = (
                        f'https://assetgame.roblox.com/game/PlaceLauncher.ashx'
                        f'?placeId={self.place_id}'
                        f'&request=RequestGame'
                    )
                    self.log_message.emit("Joining public server")
                
                # Build the launch URL with the constructed PlaceLauncher URL
                launch_url = (
                    f"roblox-player:1+"
                    f"launchmode:play+"
                    f"gameinfo:{self.auth_ticket}+"
                    f"placelauncherurl:{urllib.parse.quote(launcher_url)}"
                )
                
                # Use --browser flag which is what Roblox website uses
                cmd = [self.exe_path, "--browser", launch_url]
            else:
                cmd = [self.exe_path, '--authenticationTicket', self.auth_ticket]
            
            self.log_message.emit(f"Command: {' '.join(cmd)}")
            process = subprocess.Popen(cmd)
            
            description = f"Place ID: {self.place_id}" if self.place_id else "Roblox Player"
            self.process_started.emit(process.pid, description)
            
        except Exception as e:
            self.process_failed.emit(f"Error launching Roblox: {str(e)}")


class RobloxLauncherGUI(QMainWindow):
    """Main GUI application for Roblox account-manager launcher."""
    
    def __init__(self):
        super().__init__()
        self.accounts = []
        self.servers = []
        self.current_auth = None
        self.exe_path = None
        self.mutex = None
        self.processes = []
        
        self.setup_ui()
        self.load_data()
        self.find_roblox_executable()
        self.create_mutex()
        self.setup_process_monitor()
    
    def setup_ui(self):
        """Setup the main UI."""
        self.setWindowTitle("Roblox Account Manager Launcher")
        self.setMinimumSize(900, 700)
        
        # Apply modern styling
        self.apply_modern_style()
        
        # Create menu bar
        self.create_menu_bar()
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Controls
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Logs and Process list
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 500])
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def apply_modern_style(self):
        """Apply modern Windows 11-style theme."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
                color: #323130;
            }
            QWidget {
                background-color: #ffffff;
                color: #323130;
            }
            QComboBox {
                padding: 6px 12px;
                border: 1px solid #d2d0ce;
                border-radius: 4px;
                background-color: white;
                min-height: 20px;
            }
            QComboBox:hover {
                border-color: #0078d4;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #d2d0ce;
                border-radius: 4px;
                background-color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
                outline: none;
            }
            QListWidget {
                border: 1px solid #d2d0ce;
                border-radius: 4px;
                background-color: white;
                alternate-background-color: #f9f9f9;
            }
            QTabWidget::pane {
                border: 1px solid #d2d0ce;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #f3f2f1;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #0078d4;
            }
            QMenuBar {
                background-color: #f3f2f1;
                border-bottom: 1px solid #d2d0ce;
            }
            QMenuBar::item {
                padding: 8px 12px;
                background-color: transparent;
            }
            QMenuBar::item:selected {
                background-color: #e1dfdd;
            }
            /* Modern scrollbar styling */
            QScrollBar:vertical {
                background-color: #f3f2f1;
                width: 12px;
                border-radius: 6px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #c7c6c4;
                border-radius: 6px;
                min-height: 20px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a19f9d;
            }
            QScrollBar::handle:vertical:pressed {
                background-color: #979593;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: transparent;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QScrollBar:horizontal {
                background-color: #f3f2f1;
                height: 12px;
                border-radius: 6px;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background-color: #c7c6c4;
                border-radius: 6px;
                min-width: 20px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #a19f9d;
            }
            QScrollBar::handle:horizontal:pressed {
                background-color: #979593;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                background: transparent;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: transparent;
            }
        """)
    
    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        add_account_action = QAction('Add Account', self)
        add_account_action.triggered.connect(self.add_account)
        file_menu.addAction(add_account_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu('Tools')
        
        refresh_executable_action = QAction('Refresh Roblox Path', self)
        refresh_executable_action.triggered.connect(self.find_roblox_executable)
        tools_menu.addAction(refresh_executable_action)
        
        kill_processes_action = QAction('Kill All Roblox Processes', self)
        kill_processes_action.triggered.connect(self.kill_all_processes)
        tools_menu.addAction(kill_processes_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_left_panel(self) -> QWidget:
        """Create the left control panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Account selection
        account_group = ModernGroupBox("Account Selection")
        account_layout = QVBoxLayout(account_group)
        
        self.account_combo = QComboBox()
        self.account_combo.addItem("No Authentication")
        self.account_combo.currentTextChanged.connect(self.on_account_changed)
        
        account_buttons_layout = QHBoxLayout()
        self.refresh_auth_btn = ModernButton("Refresh Auth")
        self.refresh_auth_btn.clicked.connect(self.refresh_auth)
        self.refresh_auth_btn.setEnabled(False)
        
        add_account_btn = ModernButton("Add Account")
        add_account_btn.clicked.connect(self.add_account)
        
        account_buttons_layout.addWidget(self.refresh_auth_btn)
        account_buttons_layout.addWidget(add_account_btn)
        
        account_layout.addWidget(self.account_combo)
        account_layout.addLayout(account_buttons_layout)
        
        # Game launch section
        launch_group = ModernGroupBox("Launch Game")
        launch_layout = QVBoxLayout(launch_group)
        
        # Place ID input
        place_layout = QHBoxLayout()
        place_layout.addWidget(QLabel("Place ID:"))
        self.place_id_edit = QLineEdit()
        self.place_id_edit.setPlaceholderText("Enter Roblox game Place ID")
        place_layout.addWidget(self.place_id_edit)
        
        # Private server input
        private_layout = QHBoxLayout()
        private_layout.addWidget(QLabel("Private Server:"))
        self.private_server_edit = QLineEdit()
        self.private_server_edit.setPlaceholderText("Optional: Private server link or code")
        private_layout.addWidget(self.private_server_edit)
        
        # Launch button
        self.launch_btn = ModernButton("Launch Roblox", primary=True)
        self.launch_btn.clicked.connect(self.launch_roblox)
        
        launch_layout.addLayout(place_layout)
        launch_layout.addLayout(private_layout)
        launch_layout.addWidget(self.launch_btn)
        
        # Saved servers section
        servers_group = ModernGroupBox("Saved Games")
        servers_layout = QVBoxLayout(servers_group)
        
        self.servers_list = QListWidget()
        self.servers_list.itemClicked.connect(self.select_saved_server)
        
        servers_buttons_layout = QHBoxLayout()
        refresh_servers_btn = ModernButton("Refresh")
        refresh_servers_btn.clicked.connect(self.load_servers)
        
        servers_buttons_layout.addWidget(refresh_servers_btn)
        servers_buttons_layout.addStretch()
        
        servers_layout.addWidget(self.servers_list)
        servers_layout.addLayout(servers_buttons_layout)
        
        # Add all groups to main layout
        layout.addWidget(account_group)
        layout.addWidget(launch_group)
        layout.addWidget(servers_group)
        layout.addStretch()
        
        return panel
    
    def create_right_panel(self) -> QWidget:
        """Create the right panel with logs and process list."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # Logs tab
        logs_widget = QWidget()
        logs_layout = QVBoxLayout(logs_widget)
        
        self.log_display = ModernTextEdit()
        # Remove the fixed height to allow equal space sharing
        
        clear_logs_btn = ModernButton("Clear Logs")
        clear_logs_btn.clicked.connect(self.log_display.clear)
        
        logs_layout.addWidget(QLabel("Application Logs:"))
        logs_layout.addWidget(self.log_display)
        logs_layout.addWidget(clear_logs_btn, 0, Qt.AlignmentFlag.AlignRight)
        
        tab_widget.addTab(logs_widget, "Logs")
        
        # Processes tab
        processes_widget = QWidget()
        processes_layout = QVBoxLayout(processes_widget)
        
        self.process_list = QListWidget()
        
        process_buttons_layout = QHBoxLayout()
        refresh_processes_btn = ModernButton("Refresh")
        refresh_processes_btn.clicked.connect(self.refresh_process_list)
        
        kill_selected_btn = ModernButton("Kill Selected")
        kill_selected_btn.clicked.connect(self.kill_selected_process)
        
        process_buttons_layout.addWidget(refresh_processes_btn)
        process_buttons_layout.addWidget(kill_selected_btn)
        process_buttons_layout.addStretch()
        
        processes_layout.addWidget(QLabel("Running Roblox Processes:"))
        processes_layout.addWidget(self.process_list)
        processes_layout.addLayout(process_buttons_layout)
        
        tab_widget.addTab(processes_widget, "Processes")
        
        layout.addWidget(tab_widget)
        
        return panel
    
    def load_data(self):
        """Load accounts and servers data."""
        self.load_accounts()
        self.load_servers()
    
    def load_accounts(self):
        """Load accounts from JSON file."""
        try:
            if os.path.exists('cookies.json'):
                with open('cookies.json', 'r') as f:
                    data = json.load(f)
                    self.accounts = data.get('accounts', [])
            else:
                self.accounts = []
            
            # Update combo box
            self.account_combo.clear()
            self.account_combo.addItem("No Authentication")
            
            for account in self.accounts:
                display_name = f"{account['name']} - {account['description']}"
                self.account_combo.addItem(display_name)
            
            self.log_message(f"Loaded {len(self.accounts)} accounts")
            
        except Exception as e:
            self.log_message(f"Error loading accounts: {str(e)}")
    
    def load_servers(self):
        """Load servers from JSON file."""
        try:
            if os.path.exists('servers.json'):
                with open('servers.json', 'r') as f:
                    data = json.load(f)
                    self.servers = data.get('servers', [])
            else:
                self.servers = []
                # Create empty servers.json
                with open('servers.json', 'w') as f:
                    json.dump({'servers': []}, f, indent=4)
            
            # Update servers list
            self.servers_list.clear()
            for server in self.servers:
                item_text = f"{server['name']} (ID: {server['place_id']})"
                if server.get('private_servers'):
                    item_text += f" - {len(server['private_servers'])} private servers"
                
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, server)
                self.servers_list.addItem(item)
            
            self.log_message(f"Loaded {len(self.servers)} saved games")
            
        except Exception as e:
            self.log_message(f"Error loading servers: {str(e)}")
    
    def find_roblox_executable(self):
        """Find the latest Roblox Player executable."""
        try:
            # Default Roblox installation path
            base_path = os.path.expandvars(r"%LOCALAPPDATA%\Roblox\Versions")
            
            if not os.path.exists(base_path):
                self.log_message(f"Roblox installation directory not found at: {base_path}")
                self.exe_path = None
                return
            
            # Get all version directories
            version_dirs = []
            for d in os.listdir(base_path):
                full_path = os.path.join(base_path, d)
                if os.path.isdir(full_path):
                    # Check if directory contains the exe
                    exe_path = os.path.join(full_path, "RobloxPlayerBeta.exe")
                    if os.path.exists(exe_path):
                        # Get the version directory's last modification time
                        version_dirs.append((full_path, os.path.getmtime(full_path)))
            
            if not version_dirs:
                self.log_message("Could not find RobloxPlayerBeta.exe in any version directory")
                self.exe_path = None
                return
            
            # Sort by modification time (newest first)
            version_dirs.sort(key=lambda x: x[1], reverse=True)
            
            # Get the newest version's exe path
            latest_version_dir = version_dirs[0][0]
            self.exe_path = os.path.join(latest_version_dir, "RobloxPlayerBeta.exe")
            
            version_name = os.path.basename(latest_version_dir)
            self.log_message(f"Found Roblox Player: {version_name}")
            self.status_bar.showMessage(f"Roblox Player: {version_name}")
            
        except Exception as e:
            self.log_message(f"Error finding Roblox executable: {str(e)}")
            self.exe_path = None
    
    def create_mutex(self):
        """Create and maintain the Roblox singleton mutex."""
        try:
            self.mutex = ctypes.windll.kernel32.CreateMutexW(
                None, True, "ROBLOX_singletonMutex"
            )
            if self.mutex:
                self.log_message("Successfully created ROBLOX_singletonMutex")
            else:
                error = ctypes.get_last_error()
                self.log_message(f"Failed to create mutex: {error}")
        except Exception as e:
            self.log_message(f"Error creating mutex: {str(e)}")
            self.mutex = None
    
    def setup_process_monitor(self):
        """Setup process monitoring timer."""
        self.process_timer = QTimer()
        self.process_timer.timeout.connect(self.refresh_process_list)
        self.process_timer.start(5000)  # Refresh every 5 seconds
    
    def log_message(self, message: str):
        """Add a message to the log display."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_display.append(f"[{timestamp}] {message}")
        # Auto-scroll to bottom
        cursor = self.log_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_display.setTextCursor(cursor)
    
    def on_account_changed(self, account_text: str):
        """Handle account selection change."""
        if account_text == "No Authentication":
            self.current_auth = None
            self.refresh_auth_btn.setEnabled(False)
            self.log_message("Switched to no authentication mode")
        else:
            # Find the selected account
            for account in self.accounts:
                display_name = f"{account['name']} - {account['description']}"
                if display_name == account_text:
                    if RobloxAuth is None:
                        QMessageBox.warning(
                            self, "Authentication Unavailable",
                            "Authentication module not found. Please ensure auth.py is available."
                        )
                        self.account_combo.setCurrentIndex(0)
                        return
                    
                    self.current_auth = RobloxAuth(account['cookie'])
                    
                    if not self.current_auth.validate_cookie():
                        QMessageBox.warning(
                            self, "Cookie Validation Failed",
                            "The selected account's cookie is invalid or expired.\n\n"
                            "Tips to fix this:\n"
                            "1. Make sure you copied the entire .ROBLOSECURITY cookie value\n"
                            "2. Try logging out and back in to Roblox to get a fresh cookie\n"
                            "3. Check if your IP is not being rate limited by Roblox"
                        )
                        self.account_combo.setCurrentIndex(0)
                        self.current_auth = None
                        return
                    
                    user_id = self.current_auth.get_user_id()
                    if user_id:
                        self.log_message(f"Authenticated as user ID: {user_id}")
                        self.refresh_auth_btn.setEnabled(True)
                    else:
                        QMessageBox.warning(
                            self, "Authentication Failed",
                            "Failed to authenticate with the selected account."
                        )
                        self.account_combo.setCurrentIndex(0)
                        self.current_auth = None
                    break
    
    def refresh_auth(self):
        """Refresh the authentication ticket."""
        if not self.current_auth:
            return
        
        auth_ticket = self.current_auth.get_auth_ticket()
        if auth_ticket:
            self.log_message("Successfully refreshed auth ticket")
            QMessageBox.information(self, "Success", "Auth ticket refreshed successfully!")
        else:
            self.log_message("Failed to refresh auth ticket")
            QMessageBox.warning(self, "Error", "Failed to refresh auth ticket.")
    
    def add_account(self):
        """Open dialog to add new account."""
        dialog = AccountDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            account_data = dialog.get_account_data()
            
            if not all([account_data['name'], account_data['cookie']]):
                QMessageBox.warning(self, "Error", "Name and Cookie are required fields.")
                return
            
            # Add to accounts list
            self.accounts.append(account_data)
            
            # Save to file
            try:
                data = {'accounts': self.accounts}
                with open('cookies.json', 'w') as f:
                    json.dump(data, f, indent=4)
                
                self.load_accounts()  # Refresh the combo box
                self.log_message(f"Added account: {account_data['name']}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save account: {str(e)}")
    
    def launch_roblox(self):
        """Launch Roblox with current settings."""
        if not self.exe_path:
            QMessageBox.warning(
                self, "Error", 
                "Roblox executable not found. Please install Roblox first."
            )
            return
        
        place_id = self.place_id_edit.text().strip()
        private_server = self.private_server_edit.text().strip()
        
        if not place_id and not self.current_auth:
            QMessageBox.information(
                self, "Info",
                "Please enter a Place ID or select an account to launch Roblox."
            )
            return
        
        # Get auth ticket if authenticated
        auth_ticket = ""
        if self.current_auth:
            self.log_message("Getting fresh auth ticket...")
            auth_ticket = self.current_auth.get_auth_ticket()
            if not auth_ticket:
                QMessageBox.warning(
                    self, "Error",
                    "Failed to get auth ticket. Try refreshing authentication."
                )
                return
        
        # Create worker thread for launching
        self.worker = RobloxProcessWorker(
            exe_path=self.exe_path,
            auth_ticket=auth_ticket,
            place_id=place_id if place_id else None,
            private_server_link=private_server if private_server else None
        )
        
        # Connect signals
        self.worker.process_started.connect(self.on_process_started)
        self.worker.process_failed.connect(self.on_process_failed)
        self.worker.log_message.connect(self.log_message)
        
        # Start the worker
        self.worker.start()
        
        # Disable launch button temporarily
        self.launch_btn.setEnabled(False)
        self.launch_btn.setText("Launching...")
    
    def select_saved_server(self, item: QListWidgetItem):
        """Select a saved server and populate the form fields."""
        server_data = item.data(Qt.ItemDataRole.UserRole)
        
        # Set the place ID
        self.place_id_edit.setText(server_data['place_id'])
        
        # Handle private servers if available
        if server_data.get('private_servers'):
            private_servers = server_data['private_servers']
            
            if len(private_servers) == 1:
                # Auto-populate if only one private server
                self.private_server_edit.setText(private_servers[0]['code'])
                self.log_message(f"Selected {server_data['name']} with private server: {private_servers[0]['name']}")
            else:
                # Show dialog to select private server
                from PyQt6.QtWidgets import QInputDialog
                
                server_names = [f"{ps['name']}" for ps in private_servers]
                server_names.append("Join public server")
                
                choice, ok = QInputDialog.getItem(
                    self, "Select Server Type",
                    f"Select server type for {server_data['name']}:",
                    server_names, 0, False
                )
                
                if ok:
                    if choice == "Join public server":
                        self.private_server_edit.clear()
                        self.log_message(f"Selected {server_data['name']} - public server")
                    else:
                        # Find the selected private server
                        for ps in private_servers:
                            if ps['name'] == choice:
                                self.private_server_edit.setText(ps['code'])
                                self.log_message(f"Selected {server_data['name']} with private server: {choice}")
                                break
                else:
                    # User cancelled, clear the selection
                    self.place_id_edit.clear()
                    self.private_server_edit.clear()
        else:
            self.private_server_edit.clear()
            self.private_server_edit.setPlaceholderText("Optional: Private server link or code")
            self.log_message(f"Selected {server_data['name']} - public servers only")
    
    def launch_saved_server(self, item: QListWidgetItem):
        """Launch a saved server from the list (legacy method - now unused)."""
        # This method is kept for compatibility but no longer used
        # The functionality has been moved to select_saved_server
        pass
    
    def on_process_started(self, pid: int, description: str):
        """Handle successful process start."""
        self.log_message(f"Successfully launched Roblox (PID: {pid}) - {description}")
        self.processes.append(pid)
        
        # Re-enable launch button
        self.launch_btn.setEnabled(True)
        self.launch_btn.setText("Launch Roblox")
        
        # Refresh process list
        self.refresh_process_list()
    
    def on_process_failed(self, error: str):
        """Handle process launch failure."""
        self.log_message(f"Failed to launch Roblox: {error}")
        QMessageBox.critical(self, "Launch Error", f"Failed to launch Roblox:\n{error}")
        
        # Re-enable launch button
        self.launch_btn.setEnabled(True)
        self.launch_btn.setText("Launch Roblox")
    
    def refresh_process_list(self):
        """Refresh the list of running Roblox processes."""
        self.process_list.clear()
        
        roblox_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'create_time']):
            try:
                if proc.info['name'].lower() in ['robloxplayerbeta.exe', 'roblox.exe']:
                    roblox_processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        for proc in roblox_processes:
            item_text = f"{proc['name']} (PID: {proc['pid']})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, proc['pid'])
            self.process_list.addItem(item)
        
        # Update status bar
        if roblox_processes:
            self.status_bar.showMessage(f"{len(roblox_processes)} Roblox processes running")
        else:
            self.status_bar.showMessage("No Roblox processes running")
    
    def kill_selected_process(self):
        """Kill the selected Roblox process."""
        current_item = self.process_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "No Selection", "Please select a process to kill.")
            return
        
        pid = current_item.data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(
            self, "Confirm Kill Process",
            f"Are you sure you want to kill process {pid}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                process = psutil.Process(pid)
                process.terminate()
                self.log_message(f"Terminated process {pid}")
                self.refresh_process_list()
            except psutil.NoSuchProcess:
                self.log_message(f"Process {pid} not found")
                self.refresh_process_list()
            except Exception as e:
                self.log_message(f"Error killing process {pid}: {str(e)}")
                QMessageBox.warning(self, "Error", f"Failed to kill process: {str(e)}")
    
    def kill_all_processes(self):
        """Kill all Roblox processes."""
        roblox_processes = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() in ['robloxplayerbeta.exe', 'roblox.exe']:
                    roblox_processes.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        if not roblox_processes:
            QMessageBox.information(self, "No Processes", "No Roblox processes found.")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Kill All",
            f"Are you sure you want to kill all {len(roblox_processes)} Roblox processes?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            killed_count = 0
            for pid in roblox_processes:
                try:
                    process = psutil.Process(pid)
                    process.terminate()
                    killed_count += 1
                except psutil.NoSuchProcess:
                    pass
                except Exception as e:
                    self.log_message(f"Error killing process {pid}: {str(e)}")
            
            self.log_message(f"Terminated {killed_count} Roblox processes")
            self.refresh_process_list()
    
    def show_about(self):
        """Show about dialog."""
        about_text = """
        <h3>Roblox Account Manager Launcher</h3>
        <p>A modern PyQt6 application for launching multiple Roblox instances with account management.</p>
        <p><b>Features:</b></p>
        <ul>
        <li>Multiple account support with cookie authentication</li>
        <li>Private server joining</li>
        <li>Saved games management</li>
        <li>Process monitoring and management</li>
        <li>Modern Windows 11-style interface</li>
        </ul>
        <p><b>Requirements:</b></p>
        <ul>
        <li>PyQt6</li>
        <li>psutil</li>
        <li>Roblox installed on Windows</li>
        </ul>
        """
        
        QMessageBox.about(self, "About", about_text)
    
    def closeEvent(self, event):
        """Handle application closing."""
        # Clean up mutex
        if self.mutex:
            try:
                ctypes.windll.kernel32.CloseHandle(self.mutex)
                self.log_message("Released ROBLOX_singletonMutex")
            except:
                pass
        
        # Stop any running worker threads
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        
        event.accept()


class SplashScreen(QWidget):
    """Splash screen shown during application startup."""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup splash screen UI."""
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(400, 200)
        
        # Center the splash screen
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title_label = QLabel("Roblox Account Manager Launcher")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        # Subtitle
        subtitle_label = QLabel("Loading application...")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_font = QFont()
        subtitle_font.setPointSize(10)
        subtitle_label.setFont(subtitle_font)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        layout.addStretch()
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addStretch()
        layout.addWidget(self.progress_bar)
        
        # Apply styling
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 2px solid #0078d4;
                border-radius: 10px;
            }
            QLabel {
                color: #323130;
                border: none;
            }
            QProgressBar {
                border: 1px solid #d2d0ce;
                border-radius: 4px;
                text-align: center;
                background-color: #f3f2f1;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
        """)


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("Roblox Account Manager Launcher")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("RobloxLauncher")
    
    # Show splash screen
    splash = SplashScreen()
    splash.show()
    
    # Process events to show splash screen
    app.processEvents()
    
    # Create main window
    window = RobloxLauncherGUI()
    
    # Close splash screen and show main window
    splash.close()
    window.show()
    
    # Start the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()