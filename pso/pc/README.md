## Linux Desktop Wrapper for PSOBB Installation
*Note: MacOS support is WIP. It has been partially implemented but not tested. If you're a Mac user, feel free to try, but no guarentees*

 Installation manager for Phantasy Star Online Blue Burst *Ephinea*, providing fully automated, headless installation with zero user interaction required. You won't see any Wine windows or popups during the entire process.
 Made by zeroz

### Requirements
- Python >=3.6
- System-installed Wine
- Linux system (MacOS?)

### Quick Start
1. `python pso.py -i` - Install the game
2. `python pso.py -l` - Run launcher first for updates
3. `python pso.py -e` - Run the game

### Installation Details
The installer will automatically download the Ephinea client installer if needed. If you already have the `Ephinea_PSOBB_Installer.exe`, simply place it in the `bin` folder before running the install command.

The entire installation process is automated and headless:
- No popup windows or Wine dialogs
- No user interaction required
- Silent dependency installation
- Automatic prefix configuration
- Background component verification

### Detailed Usage

```bash
# Basic Installation
python pso.py -i                    # Install PSOBB with optimal settings

# Running the Game
python pso.py -e                    # Launch PSOBB directly
python pso.py -l                    # Launch Ephinea Launcher

# Special Cases
python pso.py -i --skip-dxvk-install       # Install without DXVK
python pso.py -e --directx-runtime         # Run using Wine's DirectX runtime instead of DXVK

# Maintenance
python pso.py -u                    # Uninstall completely
```

### Features

#### Automated Installation & Management
- Fully automated, headless installation with zero popups
- Automatic client installer download (or use your own)
- Silent dependency handling
- Clean uninstallation with full prefix cleanup

#### Desktop Integration
- Desktop launch applications and icons
- Application menu entries for launcher and game
- Proper window management via XDG desktop entries and Wine X11 integration

#### Wine Management & Dependencies
- Uses system Wine packages when available (wine-mono, wine-gecko, dxvk)
- Full verification of system packages with automatic fallback to prefix installation
- Comprehensive component testing and validation
- Custom prefix isolation to avoid conflicts
- Silent dependency handling and environment configuration

#### Graphics & Performance
- DXVK support for optimal graphics
- DirectX runtime option for compatibility

#### Error Handling & Diagnostics
- Detailed component verification and state tracking
- Process management and clean shutdowns
- Automatic recovery attempts
- Clear error messages and suggestions

#### System Integration
- PTY-based process management
- Uses cached wine dependencies packages if available
- System package detection
- Signal handling for clean shutdowns

### Notes
- Installer creates a Wine prefix at `~/.local/share/ephinea-prefix`
- Downloads required files if not present
- If on Ubuntu/gnome and your icon images don't update without relog, use sudo update-icon-caches /usr/share/icons/*
