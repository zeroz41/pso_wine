import os
import subprocess
import platform
import sys
import argparse
import shutil
import pty
import errno
import select

from os_helper import install_shortcuts, uninstall_shortcuts

#zeroz41

def run_command(command):
    master_fd, slave_fd = pty.openpty()
    process = subprocess.Popen(command, stdout=slave_fd, stderr=slave_fd, close_fds=True)
    os.close(slave_fd)

    while True:
        try:
            ready, _, _ = select.select([master_fd], [], [], 1)
            if ready:
                data = os.read(master_fd, 1024).decode('utf-8', 'ignore')
                if not data:
                    break
                print(data, end='', flush=True)
            elif process.poll() is not None:
                break
        except OSError as e:
            if e.errno != errno.EIO:
                print(f"Error: {e}", file=sys.stderr)
                break

    process.wait()
    os.close(master_fd)
    exit_code = process.returncode
    if exit_code is None:
        exit_code = 1  # Set a default exit code if it's None
    return exit_code

def get_installed_path():
    # Implement the logic to determine the PSO installation directory
    # This can be based on the registry entry or other methods
    install_dir = "~/.local/share/ephinea-prefix\drive_c\EphineaPSO"
    return install_dir

def set_wine_prefix():
    prefix_dir = os.path.expanduser("~/.local/share/ephinea-prefix")
    # Create the custom prefix directory if it doesn't exist
    os.makedirs(prefix_dir, exist_ok=True)

    # Set the WINEPREFIX environment variable
    os.environ["WINEPREFIX"] = prefix_dir

    # Check if the prefix is already initialized
    if not os.path.exists(os.path.join(prefix_dir, "system.reg")):
        # Initialize the new Wine prefix
        subprocess.run(["winecfg", "/v", "win7"])

def install_ephinea(shortcuts=False, dxvk=False):
    pso_bat_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "pso.bat")
    if not os.path.exists(pso_bat_path):
        print(f"Error: pso.bat script not found at {pso_bat_path}")
        sys.exit(1)

    try:
        subprocess.check_output(["wine", "--version"])
    except FileNotFoundError:
        print("Error: Wine is not installed or not accessible from the command line.")
        sys.exit(1)

    set_wine_prefix()

    print("Installing Ephinea...")
    command = ["wine", pso_bat_path, "-i"]
    if shortcuts:
        command.append("-s")
    print(f"Command: {' '.join(command)}")
    exit_code = run_command(command)
    print(f"Installer finished with exit code: {exit_code}")
    if exit_code != 0:
        print(f"Installation failed with exit code {exit_code}")
        sys.exit(1)

    # Install DXVK if requested
    if dxvk:
        print("Starting DXVK installation in the background...")
        winetricks_command = ["winetricks", "-q", "dxvk"]
        print(f"Command: {' '.join(winetricks_command)}")
        
        try:
            # Run the DXVK installation command as a background process
            subprocess.Popen(winetricks_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("DXVK installation process started.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to start DXVK installation process: {str(e)}")

    print("Installation completed successfully!")

def uninstall_ephinea():
    pso_bat_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "pso.bat")
    if not os.path.exists(pso_bat_path):
        print(f"Error: pso.bat script not found at {pso_bat_path}")
        sys.exit(1)

    try:
        subprocess.check_output(["wine", "--version"])
    except FileNotFoundError:
        print("Error: Wine is not installed or not accessible from the command line.")
        sys.exit(1)

    set_wine_prefix()

    print("Uninstalling Ephinea...")
    command = ["wine", pso_bat_path, "-u"]
    print(f"Command: {' '.join(command)}")
    exit_code = run_command(command)
    print(f"Uninstaller finished with exit code: {exit_code}")
    if exit_code != 0:
        print(f"Uninstallation failed with exit code {exit_code}")
        sys.exit(1)

    prefix_dir = os.path.expanduser("~/.local/share/ephinea-prefix")
    # Remove the custom prefix directory
    if os.path.exists(prefix_dir):
        shutil.rmtree(prefix_dir)
    uninstall_shortcuts()
    print("Uninstallation completed successfully!")

def execute_ephinea(launcher=False):
    pso_install_dir = os.path.expanduser("~/.local/share/ephinea-prefix/drive_c/EphineaPSO")
    
    set_wine_prefix()

    print("Executing Ephinea...")
    if launcher:
        wine_executable = os.path.join(pso_install_dir, "online.exe")
    else:
        wine_executable = os.path.join(pso_install_dir, "PsoBB.exe")
    
    print(f"Launching: {wine_executable}")
    try:
        subprocess.call(f"wine '{wine_executable}'", shell=True)
    except KeyboardInterrupt:
        print("\nExecution interrupted by the user.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ephinea installer script")
    parser.add_argument("-i", "--install", action="store_true", help="Install Ephinea")
    parser.add_argument("-u", "--uninstall", action="store_true", help="Uninstall Ephinea")
    parser.add_argument("-e", "--execute", action="store_true", help="Execute Ephinea")
    parser.add_argument("-l", "--launcher", action="store_true", help="Launch Ephinea with the launcher")
    parser.add_argument("-s", "--shortcuts", action="store_true", help="Install with desktop shortcuts")
    parser.add_argument("-x", "--dxvk", action="store_true", help="Install DXVK during Ephinea installation")

    args = parser.parse_args()

    if args.uninstall:
        uninstall_ephinea()
    elif args.install:
        install_ephinea(shortcuts=args.shortcuts, dxvk=args.dxvk)
    elif args.execute:
        execute_ephinea(launcher=args.launcher)
    else:
        print("No action specified. Please use -i or --install to install, -u or --uninstall to uninstall, or -e or --execute to execute. Add -l flag with e to open launcher")