import os
import platform
import shutil
from pathlib import Path
from cmd_runner import CommandRunner

class ShortcutManager(CommandRunner):
    def __init__(self, prefix_path="~/.local/share/ephinea-prefix"):
        self.prefix_path = os.path.expanduser(prefix_path)
        self.pso_install_dir = os.path.join(self.prefix_path, "drive_c/EphineaPSO")
        self.pso_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pso.py")
        self.pso_script_dir = os.path.dirname(self.pso_script_path)

        #if we were running wine cmds, we could just instantiate the WineUtils
        #should i make this more generic for getting pso paths from WineUtils? 
        #not worth it to make fully generic atm.

    def create_shortcuts(self):
        if platform.system() == "Linux":
            self._create_linux_shortcuts()
        elif platform.system() == "Darwin":
            self._create_macos_shortcuts()
            
    def _create_linux_shortcuts(self):
        desktop_entry_template = """[Desktop Entry]
Name={name}
Type=Application
Exec=env WINEPREFIX="{wine_prefix}" python {script_path} {args}
Icon={icon_path}
Path={work_path}
Categories=Game;
StartupWMClass={wmclass}
Terminal=false
Comment=Ephinea PSO Blue Burst
"""
        applications_dir = os.path.expanduser("~/.local/share/applications")
        os.makedirs(applications_dir, exist_ok=True)

        shortcuts = [
            {
                "name": "Ephinea Launcher",
                "args": "-l",
                "icon": "online.exe",
                "wmclass": "online.exe",
                "desktop_file": "ephinea-launcher.desktop"
            },
            {
                "name": "Ephinea PSOBB",
                "args": "-e",
                "icon": "PsoBB.exe",
                "wmclass": "psobb.exe",
                "desktop_file": "ephinea-psobb.desktop"
            }
        ]

        for shortcut in shortcuts:
            icon_path = os.path.join(self.pso_install_dir, shortcut["icon"])
            if not os.path.exists(icon_path):
                print(f"Warning: Icon file not found at {icon_path}")
                continue

            desktop_entry = desktop_entry_template.format(
                name=shortcut["name"],
                wine_prefix=self.prefix_path,
                script_path=self.pso_script_path,
                args=shortcut["args"],
                icon_path=icon_path,
                work_path=self.pso_script_dir,
                wmclass=shortcut["wmclass"]
            )
            
            entry_path = os.path.join(applications_dir, shortcut["desktop_file"])
            with open(entry_path, "w") as f:
                f.write(desktop_entry)
            os.chmod(entry_path, 0o755)

        self.run_command(["update-desktop-database", applications_dir], timeout=10)

    def _create_macos_shortcuts(self):
        applications_dir = "/Applications"

        shortcuts = [
            {"name": "Ephinea Launcher", "exec": f"python {self.pso_script_path} -l", "icon": "online.exe"},
            {"name": "Ephinea PSOBB", "exec": f"python {self.pso_script_path} -e", "icon": "PsoBB.exe"}
        ]

        for shortcut in shortcuts:
            app_bundle_path = os.path.join(applications_dir, f"{shortcut['name']}.app")
            os.makedirs(os.path.join(app_bundle_path, "Contents/MacOS"), exist_ok=True)
            os.makedirs(os.path.join(app_bundle_path, "Contents/Resources"), exist_ok=True)

            icon_src = os.path.join(self.pso_install_dir, shortcut["icon"])
            icon_dest = os.path.join(app_bundle_path, "Contents/Resources", 
                                   shortcut["icon"].replace(".ico", ".icns"))
            
            if os.path.exists(icon_src):
                self.run_command(["sips", "-s", "format", "icns", icon_src, "--out", icon_dest], timeout=30)

            info_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>{shortcut['name']}</string>
    <key>CFBundleIconFile</key>
    <string>{shortcut['icon'].replace('.ico', '.icns')}</string>
    <key>CFBundleIdentifier</key>
    <string>com.ephinea.{shortcut['name'].lower().replace(' ', '')}</string>
    <key>CFBundleName</key>
    <string>{shortcut['name']}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.10</string>
</dict>
</plist>"""
            
            with open(os.path.join(app_bundle_path, "Contents/Info.plist"), "w") as f:
                f.write(info_plist)

            exec_script = f"""#!/bin/bash
cd "{self.pso_script_dir}"
{shortcut['exec']}"""
            
            exec_path = os.path.join(app_bundle_path, "Contents/MacOS", shortcut['name'])
            with open(exec_path, "w") as f:
                f.write(exec_script)
            os.chmod(exec_path, 0o755)

    def cleanup_shortcuts(self):
        if platform.system() == "Linux":
            self._cleanup_linux_shortcuts()
        elif platform.system() == "Darwin":
            self._cleanup_macos_shortcuts()

    def _cleanup_linux_shortcuts(self):
        applications_dir = os.path.expanduser("~/.local/share/applications")
        wrapper_dir = os.path.expanduser("~/.local/bin")
        
        # Remove .desktop files
        for name in ["ephinea-psobb"]:
            desktop_path = os.path.join(applications_dir, f"{name}.desktop")
            wrapper_path = os.path.join(wrapper_dir, name)
            
            if os.path.exists(desktop_path):
                os.remove(desktop_path)
            if os.path.exists(wrapper_path):
                os.remove(wrapper_path)

        self.run_command(["update-desktop-database", applications_dir], timeout=10)

    def _cleanup_macos_shortcuts(self):
        applications_dir = "/Applications"
        
        for name in ["Ephinea Launcher", "Ephinea PSOBB"]:
            path = os.path.join(applications_dir, f"{name}.app")
            if os.path.exists(path):
                shutil.rmtree(path)