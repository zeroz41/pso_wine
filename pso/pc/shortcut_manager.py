import os
import platform
import shutil
from pathlib import Path
from cmd_runner import CommandRunner

# made by zeroz, tj

class ShortcutManager(CommandRunner):
    def __init__(self, prefix_path="~/.local/share/ephinea-prefix"):
        self.prefix_path = os.path.expanduser(prefix_path)
        self.pso_install_dir = os.path.join(self.prefix_path, "drive_c/EphineaPSO")
        self.pso_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pso.py")
        self.pso_script_dir = os.path.dirname(self.pso_script_path)

        self.resources_dir = os.path.join(os.path.dirname(self.pso_script_dir), "resources")

        self.local_icons_dir = os.path.expanduser("~/.local/share/icons/hicolor")

        #if we were running wine cmds, we could just instantiate the WineUtils
        #should i make this more generic for getting pso paths from WineUtils? 
        #not worth it to make fully generic atm.
            
    def _install_linux_icon(self, icon_source, icon_name):
        """Install icon to local icons directory in various sizes"""
        if not icon_source.endswith('.png'):
            return icon_source 
            
        # make dirs if not there
        sizes = ['16x16', '32x32', '48x48', '64x64', '128x128']
        for size in sizes:
            icon_dir = os.path.join(self.local_icons_dir, size, 'apps')
            os.makedirs(icon_dir, exist_ok=True)
            
            # copy icons
            dest_path = os.path.join(icon_dir, f"{icon_name}.png")
            shutil.copy2(icon_source, dest_path)
            
        # copy to scalable dir
        scalable_dir = os.path.join(self.local_icons_dir, 'scalable/apps')
        os.makedirs(scalable_dir, exist_ok=True)
        scalable_path = os.path.join(scalable_dir, f"{icon_name}.png")
        shutil.copy2(icon_source, scalable_path)
        
        return icon_name

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
                "icon": os.path.join(self.resources_dir, "launcher.png"),
                "icon_name": "ephinea-launcher",
                "wmclass": "online.exe",
                "desktop_file": "ephinea-launcher.desktop"
            },
            {
                "name": "Ephinea PSOBB",
                "args": "-e",
                "icon": os.path.join(self.resources_dir, "bb.png"),
                "icon_name": "ephinea-psobb",
                "wmclass": "psobb.exe",
                "desktop_file": "ephinea-psobb.desktop"
            }
        ]

        for shortcut in shortcuts:
            if not os.path.exists(shortcut["icon"]):
                print(f"Warning: Icon file not found at {shortcut['icon']}")
                continue

            # install icon and get the icon name to use
            icon_path = self._install_linux_icon(shortcut["icon"], shortcut["icon_name"])

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

        # update icon cache
        # needs sudo sometimes. nbd
        self.run_command(["update-desktop-database", applications_dir], timeout=10)
        self.run_command(["gtk-update-icon-cache", self.local_icons_dir, "-f"], timeout=10)


    def _create_macos_shortcuts(self):
        applications_dir = os.path.expanduser("~/Applications")
        os.makedirs(applications_dir, exist_ok=True)

        shortcuts = [
            {
                "name": "Ephinea Launcher",
                "args": "-l",
                "icon": os.path.join(self.resources_dir, "launcher.png"),
                "icon_name": "ephinea-launcher"
            },
            {
                "name": "Ephinea PSOBB",
                "args": "-e",
                "icon": os.path.join(self.resources_dir, "bb.png"),
                "icon_name": "ephinea-psobb"
            }
        ]

        for shortcut in shortcuts:
            app_bundle_path = os.path.join(applications_dir, f"{shortcut['name']}.app")
            contents_path = os.path.join(app_bundle_path, "Contents")
            resources_path = os.path.join(contents_path, "Resources")
            
            # bundle directory structure
            os.makedirs(resources_path, exist_ok=True)

            if os.path.exists(shortcut["icon"]):
                icon_name = f"{shortcut['icon_name']}.icns"
                icon_dest = os.path.join(resources_path, icon_name)
                
                try:
                    # make iconset
                    iconset_path = os.path.join(resources_path, f"{shortcut['icon_name']}.iconset")
                    os.makedirs(iconset_path, exist_ok=True)
                    
                    # various sizes
                    sizes = [16, 32, 128, 256, 512]
                    for size in sizes:
                        self.run_command([
                            "sips",
                            "-z", str(size), str(size),
                            shortcut["icon"],
                            "--out",
                            os.path.join(iconset_path, f"icon_{size}x{size}.png")
                        ], timeout=30)
                        # 2x versions for Retina
                        if size <= 256:
                            self.run_command([
                                "sips",
                                "-z", str(size*2), str(size*2),
                                shortcut["icon"],
                                "--out",
                                os.path.join(iconset_path, f"icon_{size}x{size}@2x.png")
                            ], timeout=30)
                    
                    # convert iconset to icns
                    self.run_command(["iconutil", "-c", "icns", iconset_path, "-o", icon_dest], timeout=30)
                    
                    # cleanup
                    shutil.rmtree(iconset_path)
                except Exception as e:
                    print(f"Warning: Failed to convert icon for {shortcut['name']}: {e}")
                    icon_name = ""
            else:
                print(f"Warning: Icon file not found at {shortcut['icon']}")
                icon_name = ""

            # create Info.plist
            info_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
            <plist version="1.0">
            <dict>
                <key>CFBundleExecutable</key>
                <string>python</string>
                <key>CFBundleIconFile</key>
                <string>{icon_name}</string>
                <key>CFBundleIdentifier</key>
                <string>com.ephinea.{shortcut['icon_name']}</string>
                <key>CFBundleName</key>
                <string>{shortcut['name']}</string>
                <key>CFBundlePackageType</key>
                <string>APPL</string>
                <key>CFBundleShortVersionString</key>
                <string>1.0</string>
                <key>LSMinimumSystemVersion</key>
                <string>10.10</string>
                <key>NSHighResolutionCapable</key>
                <true/>
                <key>CFBundleExecutableParameters</key>
                <array>
                    <string>{self.pso_script_path}</string>
                    <string>{shortcut['args']}</string>
                </array>
                <key>WorkingDirectory</key>
                <string>{self.pso_script_dir}</string>
            </dict>
            </plist>"""
            
            with open(os.path.join(contents_path, "Info.plist"), "w") as f:
                f.write(info_plist)

    def cleanup_shortcuts(self):
        if platform.system() == "Linux":
            self._cleanup_linux_shortcuts()
        elif platform.system() == "Darwin":
            self._cleanup_macos_shortcuts()

    def _cleanup_linux_shortcuts(self):
        applications_dir = os.path.expanduser("~/.local/share/applications")
        
        # Remove .desktop files
        for name in ["ephinea-launcher", "ephinea-psobb"]:
            desktop_path = os.path.join(applications_dir, f"{name}.desktop")
            if os.path.exists(desktop_path):
                os.remove(desktop_path)
                
            # Clean up icons
            for size in ['16x16', '32x32', '48x48', '64x64', '128x128', 'scalable']:
                icon_path = os.path.join(self.local_icons_dir, f"{size}/apps/{name}.png")
                if os.path.exists(icon_path):
                    os.remove(icon_path)

        self.run_command(["update-desktop-database", applications_dir], timeout=10)
        self.run_command(["gtk-update-icon-cache", self.local_icons_dir, "-f"], timeout=10)

    def _cleanup_macos_shortcuts(self):
        applications_dir = os.path.expanduser("~/Applications")
        
        for name in ["Ephinea Launcher", "Ephinea PSOBB"]:
            path = os.path.join(applications_dir, f"{name}.app")
            if os.path.exists(path):
                try:
                    shutil.rmtree(path)
                except Exception as e:
                    print(f"Warning: Failed to remove {path}: {e}")
