import os
import subprocess
import pathlib
import urllib.request
import select
import pty
import errno
import sys
import shutil

# made by zeroz - tj

class WineSetupError(Exception):
    """Custom exception for Wine setup errors"""
    pass

class WineUtils:
    def __init__(self, prefix_path="~/.local/share/ephinea-prefix"):
        """Initialize WineUtils with a prefix path"""
        self.prefix_path = os.path.expanduser(prefix_path)
        self.env = os.environ.copy()
        self.env["WINEPREFIX"] = self.prefix_path

    def run_command(self, command):
        """Run a command with PTY support and return exit code"""
        print(f"Debug - Running command: {command}")
        
        master_fd, slave_fd = pty.openpty()
        process = subprocess.Popen(
            command, 
            stdout=slave_fd, 
            stderr=slave_fd, 
            close_fds=True,
            env=self.env
        )
        os.close(slave_fd)
        
        # Rest of the method remains the same
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
        return process.returncode if process.returncode is not None else 1

    def check_wine_installed(self):
        """Check if Wine is installed on the system"""
        try:
            subprocess.check_output(["wine", "--version"])
            return True
        except FileNotFoundError:
            return False

    def check_system_mono(self):
        """Check if Wine Mono is installed system-wide"""
        # Common paths where Wine Mono might be installed
        possible_paths = [
            "/usr/share/wine/mono",
            "/opt/wine/mono",
            "/usr/lib/wine/mono",
        ]
        
        # Check if wine-mono package is installed via package manager
        package_managers = {
            "dpkg": "wine-mono",
            "pacman": "wine-mono",
            "rpm": "wine-mono",
        }
        
        # Try package manager checks first
        for pm, package in package_managers.items():
            try:
                if pm == "dpkg":
                    result = subprocess.run(["dpkg", "-s", package], capture_output=True, text=True)
                    if result.returncode == 0:
                        print("Wine Mono is installed via dpkg (Debian/Ubuntu package manager)")
                        return True
                elif pm == "pacman":
                    result = subprocess.run(["pacman", "-Qi", package], capture_output=True, text=True)
                    if result.returncode == 0:
                        print("Wine Mono is installed via pacman (Arch package manager)")
                        return True
                elif pm == "rpm":
                    result = subprocess.run(["rpm", "-q", package], capture_output=True, text=True)
                    if result.returncode == 0:
                        print("Wine Mono is installed via rpm (Fedora/RHEL package manager)")
                        return True
            except FileNotFoundError:
                continue

        # Check common system paths
        for path in possible_paths:
            if pathlib.Path(path).exists():
                print(f"Found Wine Mono installation in system path: {path}")
                return True

        return False

    def check_prefix_mono(self):
        """Check if Wine Mono is installed in the prefix"""
        try:
            result = subprocess.run(
                ["wine", "reg", "query", "HKLM\\Software\\Microsoft\\NET Framework Setup\\NDP\\v4\\Client"],
                env=self.env,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except subprocess.CalledProcessError:
            return False

    def download_file(self, url, destination):
        """Download a file from URL to destination"""
        temp_file = f"{destination}.tmp"
        try:
            print(f"Downloading {url}...")
            urllib.request.urlretrieve(url, temp_file)
            # If download completes successfully, rename to final name
            shutil.move(temp_file, destination)
            print("Download completed!")
            return True
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            print(f"Failed to download file: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False
        except Exception as e:
            print(f"Unexpected error while downloading: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False

    def install_mono(self):
        """Download and install Wine Mono in the prefix"""
        # TEMP DEV MODE - Try to use existing file first
        DEV_MODE = True  # TEMPORARY FOR TESTING
        
        # Create a temporary directory in the user's cache directory
        cache_dir = os.path.expanduser("~/.cache/pso_wine")
        os.makedirs(cache_dir, exist_ok=True)

        mono_version = "9.3.0"
        mono_filename = f"wine-mono-{mono_version}-x86.msi"
        mono_url = f"https://dl.winehq.org/wine/wine-mono/{mono_version}/{mono_filename}"
        mono_path = os.path.join(cache_dir, mono_filename)

        try:
            # Check if we have a valid existing installer
            have_valid_installer = os.path.exists(mono_path) and os.path.getsize(mono_path) >= 1024

            if DEV_MODE:
                print("DEV MODE: Checking for existing mono installer...")
                if have_valid_installer:
                    print(f"Using existing installer at {mono_path}")
                else:
                    print("No valid existing installer found, downloading...")
                    if not self.download_file(mono_url, mono_path):
                        print("Failed to download Wine Mono installer")
                        return False
            else:
                # In non-dev mode, always ensure a fresh download
                if have_valid_installer:
                    print(f"Removing existing installer at {mono_path}")
                    os.remove(mono_path)
                
                print("Downloading fresh copy of Wine Mono installer...")
                if not self.download_file(mono_url, mono_path):
                    print("Failed to download Wine Mono installer")
                    return False

            # Verify we have a valid installer before proceeding
            if not os.path.exists(mono_path) or os.path.getsize(mono_path) < 1024:
                print("Wine Mono installer file is missing or corrupt")
                return False

            print("Installing Wine Mono...")
            print(f"Debug - Mono installer path: {mono_path}")
            exit_code = self.run_command(["wine", "msiexec", "/i", mono_path])
            
            if exit_code == 0:
                print("Wine Mono installation completed successfully!")
                return True
            else:
                print(f"Wine Mono installation failed with exit code: {exit_code}")
                return False

        except Exception as e:
            print(f"Error during Mono installation: {e}")
            if os.path.exists(mono_path):
                print(f"Cleaning up potentially corrupt installer at {mono_path}")
                os.remove(mono_path)
            return False

    def setup_prefix(self):
        """Set up and configure the Wine prefix with all requirements"""
        # Check for Wine installation
        if not self.check_wine_installed():
            raise WineSetupError("Wine is not installed or not accessible from the command line.")

        # Create prefix directory
        os.makedirs(self.prefix_path, exist_ok=True)

        # Initialize prefix if needed
        if not os.path.exists(os.path.join(self.prefix_path, "system.reg")):
            print("Initializing new Wine prefix...")
            self.run_command(["wine", "reg", "add", "HKEY_CURRENT_USER\\Software\\Wine\\Version", "/v", "Windows", "/d", "win7", "/f"])
            
            # Ensure Windows version is set properly
            self.run_command(["wine", "reg", "add", "HKLM\\System\\CurrentControlSet\\Control\\Windows", "/v", "CSDVersion", "/t", "REG_DWORD", "/d", "256", "/f"])

        # Handle Mono installation
        if self.check_prefix_mono():
            print("Wine Mono is already installed in the prefix.")
            return True

        if self.check_system_mono():
            print("System-wide Wine Mono installation detected.")
            return True

        print("No Wine Mono installation found. Installing in prefix...")
        if not self.install_mono():
            print("Warning: Failed to install Wine Mono. The launcher might not work properly.")
            print("You may need to install wine-mono using your system's package manager:")
            print("  Debian/Ubuntu: sudo apt install wine-mono")
            print("  Arch Linux: sudo pacman -S wine-mono")
            print("  Fedora: sudo dnf install wine-mono")
            return False

        return True

    def cleanup_prefix(self):
        """Remove the Wine prefix directory"""
        if os.path.exists(self.prefix_path):
            shutil.rmtree(self.prefix_path)
            print(f"Removed Wine prefix at {self.prefix_path}")