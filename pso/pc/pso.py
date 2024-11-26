import os
import sys
import argparse
from prefix_cmds import WineUtils, WineSetupError

# made by zeroz - tj

def install_ephinea(shortcuts=False):
    pso_bat_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "pso.bat")
    if not os.path.exists(pso_bat_path):
        print(f"Error: pso.bat script not found at {pso_bat_path}")
        sys.exit(1)

    wine = WineUtils()
    try:
        wine.setup_prefix()
    except WineSetupError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print("Installing Ephinea...")
    # Modified to use cmd /c to execute the batch file
    command = ["wine", "cmd", "/c", pso_bat_path, "-i"]
    if shortcuts:
        command.append("-s")
    
    print(f"Command: {' '.join(command)}")
    exit_code = wine.run_command(command)
    print(f"Installer finished with exit code: {exit_code}")
    
    if exit_code != 0:
        print(f"Installation failed with exit code {exit_code}")
        sys.exit(1)
    
    print("Installation completed successfully!")

def uninstall_ephinea():
    wine = WineUtils()

    # Only try to run the uninstaller if the prefix actually exists
    if os.path.exists(wine.prefix_path):
        if wine.check_wine_installed():
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            pso_bat_path = os.path.normpath(os.path.join(script_dir, "scripts", "pso.bat"))
            
            if os.path.exists(pso_bat_path):
                print("Uninstalling Ephinea...")
                command = ["wine", "cmd", "/c", pso_bat_path, "-u"]
                print(f"Command: {' '.join(command)}")
                exit_code = wine.run_command(command)
                print(f"Uninstaller finished with exit code: {exit_code}")
                if exit_code != 0:
                    print(f"Warning: Uninstaller exited with code {exit_code}, continuing with prefix cleanup...")
            else:
                print(f"Warning: pso.bat script not found at {pso_bat_path}, skipping wine uninstall...")
        else:
            print("Warning: Wine is not installed, skipping wine uninstall...")

        # Clean up the prefix directory if it exists
        wine.cleanup_prefix()
        print("Uninstallation completed successfully!")
    else:
        print("Nothing to uninstall - prefix directory doesn't exist.")

def execute_ephinea(launcher=False):
    pso_bat_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "pso.bat")
    if not os.path.exists(pso_bat_path):
        print(f"Error: pso.bat script not found at {pso_bat_path}")
        sys.exit(1)

    wine = WineUtils()
    try:
        wine.setup_prefix()
    except WineSetupError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print("Executing Ephinea...")
    command = ["wine", "cmd", "/c", pso_bat_path, "-e"]
    if launcher:
        command.append("-l")
    print(f"Command: {' '.join(command)}")
    exit_code = wine.run_command(command)
    print(f"Execution finished with exit code: {exit_code}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ephinea installer script")
    parser.add_argument("-i", "--install", action="store_true", help="Install Ephinea")
    parser.add_argument("-u", "--uninstall", action="store_true", help="Uninstall Ephinea")
    parser.add_argument("-e", "--execute", action="store_true", help="Execute Ephinea")
    parser.add_argument("-l", "--launcher", action="store_true", help="Launch Ephinea with the launcher. Use -el not just -l")
    parser.add_argument("-s", "--shortcuts", action="store_true", help="Install with desktop shortcuts")

    args = parser.parse_args()

    if args.uninstall:
        uninstall_ephinea()
    elif args.install:
        install_ephinea(shortcuts=args.shortcuts)
    elif args.execute:
        execute_ephinea(launcher=args.launcher)
    else:
        print("No action specified. Please use -i or --install to install, -u or --uninstall to uninstall, or -e or --execute to execute or -el to run launcher.")