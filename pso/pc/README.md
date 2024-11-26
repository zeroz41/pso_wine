## Linux Python Wrapper for Simple Wine Install of PSOBB

This wrapper utilizes the core `pso.bat` script to ensure functional compatibility when running within Wine itself, rather than relying on the native OS.

The wrapper allows for reuse between Android and Linux, and doesn't rely on platform specific tools like lutris or bottles.

The installer creates PSO Launcher and PSOBB executable files within the Wine prefix's start menu, which are also accessible from the host Linux system's start menu. The shortcuts are custom-renamed for ease of launching. (Icon replacement may be added in the future.) Desktop shortcuts are not added by default unless the -s flag is passed with the install flag.

This setup could easily enable simple, user input-free installation and uninstallation using desktop packaging tools such as apt or pacman (yay, paru).

### Requirements
- python >=3.6

### Installation
1. Download the repository.
2. Place the `Ephinea_PSOBB_Installer.exe` file in the `bin` folder of the repository. If you don't have the installer file, the script will automatically download it for you.
3. Run the Python installer using the command: `python pso.py -i`

The installer relies on the user's native system-installed Wine, ensuring compatibility with any modern Wine version without requiring custom versions.

No additional tools like dgVoodoo, winetricks are needed. The Wine prefix is set to `~/.local/share/ephinea-prefix` by default.

### Usage
- To install: `python pso.py -i`
- To uninstall: `python pso.py -u`

- Running the launcher at least once is required to update the game usually. Settings menus also exist here.
- To run the launcher via cmdline `python pso.py -el`
- To only run the blue burst exe (the actual game) `python pso.py -e`

Note: If you don't have the `Ephinea_PSOBB_Installer.exe` file in the `bin` folder, the script will automatically download it during the installation process. The downloaded installer will be saved in the `bin` folder for future use.
