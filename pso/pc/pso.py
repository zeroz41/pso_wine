import os
import sys
import argparse
from prefix_cmds import WineUtils, WineSetupError
from shortcut_manager import ShortcutManager

# made by zeroz - tj

def install_ephinea(install_dxvk=True):
    pso_bat_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "pso.bat")
    if not os.path.exists(pso_bat_path):
        print(f"Error: pso.bat script not found at {pso_bat_path}")
        sys.exit(1)

    wine = WineUtils()
    try:
        wine.setup_prefix(install_dxvk=install_dxvk)
    except WineSetupError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print("Installing Ephinea...")
    command = ["wine", "cmd", "/c", pso_bat_path, "-i"]
    
    print(f"Command: {' '.join(command)}")
    exit_code = wine.run_command(command, timeout=None)
    print(f"Installer finished with exit code: {exit_code}")
    
    if exit_code != 0:
        print(f"Installation failed with exit code {exit_code}")
        sys.exit(1)

    print("Creating desktop shortcuts...")
    shortcut_manager = ShortcutManager()
    shortcut_manager.create_shortcuts()
    shortcut_manager.remove_wine_generated_shortcuts()
    
    print("Installation completed successfully!")

def uninstall_ephinea():
    wine = WineUtils()

    print("Removing all desktop shortcuts and icons")
    shortcut_manager = ShortcutManager()
    shortcut_manager.cleanup_shortcuts()
    # in case they are back somehow  
    shortcut_manager.remove_wine_generated_shortcuts()

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
        print("Cleaning up and removing PSO wine prefix")
        wine.cleanup_prefix()

        print("Uninstallation completed successfully!")
    else:
        print("Nothing to uninstall - prefix directory doesn't exist.")

def execute_ephinea(launcher=False):

    #must set wine env variables before wineutils initialize
    if args.vm_no_graphics:
        print("LAUNCHING IN VM COMPATIBILITY MODE (NO HARDWARE GRAPHICS)")
        os.environ['WINEESYNC'] = "1"
        os.environ['WINEDLLOVERRIDES'] = "dxvk_config=b;d3d9,d3d11,dxgi=b"

    wine = WineUtils()
    
    # Check if prefix exists first
    if not os.path.exists(wine.prefix_path):
        print("Error: Ephinea is not installed. Please install it first with -i")
        sys.exit(1)

    pso_bat_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "pso.bat")
    if not os.path.exists(pso_bat_path):
        print(f"Error: pso.bat script not found at {pso_bat_path}")
        sys.exit(1)

    print("Executing Ephinea...")
    command = ["wine", "cmd", "/c", pso_bat_path, "-e"]
    if launcher:
        command.append("-l")
    print(f"Command: {' '.join(command)}")
    # Use execute_game instead of run_command
    exit_code = wine.execute_game(command)
    print(f"Execution finished with exit code: {exit_code}")

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Ephinea installer script")
    parser.add_argument("-i", "--install", action="store_true", help="Install Ephinea")
    parser.add_argument("-u", "--uninstall", action="store_true", help="Uninstall Ephinea")
    parser.add_argument("-e", "--execute", action="store_true", help="Start PSO Blue Burst")
    parser.add_argument("-l", "--launcher", action="store_true", help="Start Ephinea Launcher")
    parser.add_argument("--directx-runtime", action="store_true",
            help="Use Wine's DirectX runtime instead of DXVK. Useful for compatibility issues. Run with -e or -l")
    parser.add_argument("--skip-dxvk-install", action="store_true", 
            help="Install using Wine's DirectX runtime instead of DXVK. Run with -i")

    args = parser.parse_args()

    if args.uninstall:
        uninstall_ephinea()
    elif args.install:
        install_ephinea(install_dxvk=not args.skip_dxvk_install)
    elif args.execute or args.launcher:
        execute_ephinea(launcher=args.launcher)
    else:
        script_name = os.path.basename(sys.argv[0])
        print(f"No action specified. Run with `python {script_name} -h` for help")