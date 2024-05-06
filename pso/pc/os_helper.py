# os_helper.py
import os
import platform
import subprocess
import shutil

def get_pso_install_dir():
    # Use the install directory defined in the pso.py script
    from pso import get_installed_path
    return get_installed_path()

def install_shortcuts():
    if platform.system() == "Linux":
        install_linux_shortcuts()
    elif platform.system() == "Darwin":
        install_macos_shortcuts()

def install_linux_shortcuts():
    desktop_entry_template = """[Desktop Entry]
Type=Application
Name={name}
Exec={exec_path}
Icon={icon_path}
Path={work_path}
Categories=Game;
"""

    applications_dir = os.path.expanduser("~/.local/share/applications")
    os.makedirs(applications_dir, exist_ok=True)

    pso_install_dir = os.path.expanduser("~/.local/share/ephinea-prefix/drive_c/EphineaPSO")
    pso_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pso.py')
    pso_script_dir = os.path.dirname(pso_script_path)

    shortcuts = [
        {"name": "Ephinea Launcher", "exec": f"python {pso_script_path} -e -l", "icon": "online.ico"},
        {"name": "Ephinea PSOBB", "exec": f"python {pso_script_path} -e", "icon": "PsoBB.ico"}
    ]

    for shortcut in shortcuts:
        icon_path = os.path.join(pso_install_dir, shortcut["icon"])

        desktop_entry = desktop_entry_template.format(
            name=shortcut["name"],
            exec_path=shortcut["exec"],
            icon_path=icon_path,
            work_path=pso_script_dir
        )
        with open(os.path.join(applications_dir, shortcut["name"] + ".desktop"), "w") as file:
            file.write(desktop_entry)

    subprocess.run(["update-desktop-database", applications_dir], check=True)

def install_macos_shortcuts():
    applications_dir = "/Applications"
    pso_install_dir = os.path.expanduser("~/.local/share/ephinea-prefix/drive_c/EphineaPSO")
    pso_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pso.py")

    shortcuts = [
        {"name": "Ephinea Launcher", "exec": f"python {pso_script_path} -e -l", "icon": "online.ico"},
        {"name": "Ephinea PSOBB", "exec": f"python {pso_script_path} -e", "icon": "PsoBB.ico"}
    ]

    for shortcut in shortcuts:
        app_bundle_path = os.path.join(applications_dir, shortcut["name"] + ".app")
        os.makedirs(app_bundle_path, exist_ok=True)
        os.makedirs(os.path.join(app_bundle_path, "Contents", "MacOS"), exist_ok=True)
        os.makedirs(os.path.join(app_bundle_path, "Contents", "Resources"), exist_ok=True)

        icon_src_path = os.path.join(pso_install_dir, shortcut["icon"])
        icon_dest_path = os.path.join(app_bundle_path, "Contents", "Resources", shortcut["icon"].replace(".ico", ".icns"))
        subprocess.run(["sips", "-s", "format", "icns", icon_src_path, "--out", icon_dest_path], check=True)

        with open(os.path.join(app_bundle_path, "Contents", "Info.plist"), "w") as file:
            file.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>{shortcut["name"]}</string>
    <key>CFBundleIconFile</key>
    <string>{shortcut["icon"].replace(".ico", ".icns")}</string>
    <key>CFBundleIdentifier</key>
    <string>com.ephinea.{shortcut["name"].lower().replace(" ", "")}</string>
</dict>
</plist>
""")

        with open(os.path.join(app_bundle_path, "Contents", "MacOS", shortcut["name"]), "w") as file:
            file.write(f'#!/bin/bash\n{shortcut["exec"]}')
        os.chmod(os.path.join(app_bundle_path, "Contents", "MacOS", shortcut["name"]), 0o755)

def uninstall_shortcuts():
    if platform.system() == "Linux":
        uninstall_linux_shortcuts()
    elif platform.system() == "Darwin":
        uninstall_macos_shortcuts()

def uninstall_linux_shortcuts():
    applications_dir = os.path.expanduser("~/.local/share/applications")

    for shortcut in ["Ephinea Launcher", "Ephinea PSOBB"]:
        desktop_entry_path = os.path.join(applications_dir, shortcut + ".desktop")
        if os.path.exists(desktop_entry_path):
            os.remove(desktop_entry_path)

    subprocess.run(["update-desktop-database", applications_dir], check=True)

def uninstall_macos_shortcuts():
    applications_dir = "/Applications"

    for shortcut in ["Ephinea Launcher", "Ephinea PSOBB"]:
        app_bundle_path = os.path.join(applications_dir, shortcut + ".app")
        if os.path.exists(app_bundle_path):
            shutil.rmtree(app_bundle_path)