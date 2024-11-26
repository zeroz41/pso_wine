import os
import subprocess
import pathlib
import urllib.request
import select
import pty
import errno
import sys

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
        master_fd, slave_fd = pty.openpty()
        process = subprocess.Popen(
            command, 
            stdout=slave_fd, 
            stderr=slave_fd, 
            close_fds=True,
            env=self.env
        )
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
        return process.returncode if process.returncode is not None else 1

    def check_wine_installed(self):
        """Check if Wine is installed on the system"""
        try:
            subprocess.check_output(["wine", "--version"])
            return True
        except FileNotFoundError:
            return False

    def check_system_mono(self):
        # first check packages, then look at some common paths.
        """Check if Wine Mono is installed system-wide"""
        possible_paths = [
            "/usr/share/wine/mono",
            "/opt/wine/mono",
            "/usr/lib/wine/mono",
        ]
        
        # check wine-mono package is installed via package manager. debian,arch,rh
        package_managers = {
            "dpkg": "wine-mono",
            "pacman": "wine-mono",
            "rpm": "wine-mono",
        }
        
        # check pms
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

        # check common system paths
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
        print(f"Downloading {url}...")
        urllib.request.urlretrieve(url, destination)
        print("Download completed!")

    def install_mono(self):
        """Download and install Wine Mono in the prefix"""
        mono_version = "9.3.0"
        mono_filename = f"wine-mono-{mono_version}-x86.msi"
        mono_url = f"https://dl.winehq.org/wine/wine-mono/{mono_version}/{mono_filename}"
        mono_path = os.path.join(os.path.dirname(self.prefix_path), mono_filename)

        if not os.path.exists(mono_path):
            self.download_file(mono_url, mono_path)

        print("Installing Wine Mono...")
        try:
            result = subprocess.run(
                ["wine", "msiexec", "/i", mono_path],
                env=self.env,
                check=True
            )
            print("Wine Mono installation completed successfully!")
            os.remove(mono_path)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to install Wine Mono: {e}")
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
            self.run_command(["winecfg", "/v", "win7"])

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