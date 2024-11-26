import os
import subprocess
import pathlib
import urllib.request
import select
import pty
import errno
import sys
import shutil
import time
import signal
from contextlib import contextmanager

# made by zeroz - tj

#todo fix win7 config

class WineSetupError(Exception):
    """Custom exception for Wine setup errors"""
    pass

class ProcessTimeoutError(Exception):
    """Custom exception for process timeouts"""
    pass

@contextmanager
def process_timeout(seconds):
    """Context manager for timing out processes"""
    def handle_timeout(signum, frame):
        raise ProcessTimeoutError(f"Process timed out after {seconds} seconds")

    # Set up the timeout
    signal.signal(signal.SIGALRM, handle_timeout)
    signal.alarm(seconds)

    try:
        yield
    finally:
        # Disable the alarm
        signal.alarm(0)

class WineUtils:
    def __init__(self, prefix_path="~/.local/share/ephinea-prefix"):
        """Initialize WineUtils with a prefix path"""
        self.prefix_path = os.path.expanduser(prefix_path)
        # Store complete original environment
        self.original_env = os.environ.copy()
        self.env = os.environ.copy()
        self.env["WINEPREFIX"] = self.prefix_path
        self.env["WINEDEBUG"] = "-all"
        
    # hacky gui suppression methods. Allow us to not show windows when we want, like wine updating or install. WINE GUIS   
    # but its fun at least 
    def suppress_gui(self):
        """Enable GUI suppression for installation/setup"""
        print("Current environment before suppression:")
        for key in sorted(self.env.keys()):
            if key.startswith('WINE'):
                print(f"{key}={self.env[key]}")
        
        self.env["WINEDLLOVERRIDES"] = "mscoree=d;winemenubuilder.exe=d"
        self.env["DISPLAY"] = ""
        
    def enable_gui(self):
        """Enable GUI for game execution"""
        print("Current environment before GUI enable:")
        for key in sorted(self.env.keys()):
            if key.startswith('WINE'):
                print(f"{key}={self.env[key]}")
                
        # Restore original environment except WINEPREFIX and WINEDEBUG
        self.env = self.original_env.copy()
        self.env["WINEPREFIX"] = self.prefix_path
        self.env["WINEDEBUG"] = "-all"
        
        print("Environment after restore:")
        for key in sorted(self.env.keys()):
            if key.startswith('WINE'):
                print(f"{key}={self.env[key]}")
        
    def execute_game(self, command):
        """Execute the game with GUI enabled"""
        self.enable_gui()
        return self.run_command(command, timeout=None)


    def run_command(self, command, timeout=60):
        """Run a command with PTY support and return exit code"""
        print(f"Debug - Running command: {command}")
        
        def kill_process_tree(pid):
            try:
                parent = subprocess.Popen(['ps', '-o', 'pid', '--ppid', str(pid), '--noheaders'],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, _ = parent.communicate()
                
                # Kill children first
                for child_pid in out.split():
                    if child_pid:
                        try:
                            os.kill(int(child_pid), signal.SIGKILL)
                        except ProcessLookupError:
                            pass

                # Kill parent
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            except Exception as e:
                print(f"Error killing process tree: {e}")

        master_fd, slave_fd = pty.openpty()
        process = None
        
        try:
            process = subprocess.Popen(
                command,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                env=self.env,
                preexec_fn=os.setsid  # Create new process group
            )
            os.close(slave_fd)
            
            start_time = time.time()
            while True:
                # Only check timeout if one was specified
                if timeout is not None and time.time() - start_time > timeout:
                    print(f"Command timed out after {timeout} seconds")
                    if process:
                        kill_process_tree(process.pid)
                    return 1

                try:
                    ready, _, _ = select.select([master_fd], [], [], 1.0)
                    if ready:
                        try:
                            data = os.read(master_fd, 1024).decode('utf-8', 'ignore')
                            if not data:
                                break
                            print(data, end='', flush=True)
                        except OSError as e:
                            if e.errno != errno.EIO:
                                raise
                            break
                    elif process.poll() is not None:
                        break
                except (select.error, OSError) as e:
                    if process.poll() is not None:
                        break
                    print(f"Error during command execution: {e}")
                    break

            if process.poll() is None:
                kill_process_tree(process.pid)
                return 1

            return process.returncode if process.returncode is not None else 1

        except Exception as e:
            print(f"Error during command execution: {e}")
            if process:
                kill_process_tree(process.pid)
            return 1
        finally:
            os.close(master_fd)

    def check_wine_installed(self):
        """Check if Wine is installed on the system"""
        try:
            result = subprocess.run(["wine", "--version"], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def check_system_mono(self):
        """Check if Wine Mono is installed system-wide"""
        possible_paths = [
            "/usr/share/wine/mono",
            "/opt/wine/mono",
            "/usr/lib/wine/mono",
        ]
        
        # Check package managers
        package_managers = {
            "dpkg": "wine-mono",
            "pacman": "wine-mono",
            "rpm": "wine-mono",
        }
        
        for pm, package in package_managers.items():
            try:
                if pm == "dpkg":
                    result = subprocess.run(["dpkg", "-s", package], 
                                         capture_output=True, 
                                         timeout=10)
                    if result.returncode == 0:
                        return True
                elif pm == "pacman":
                    result = subprocess.run(["pacman", "-Qi", package], 
                                         capture_output=True, 
                                         timeout=10)
                    if result.returncode == 0:
                        return True
                elif pm == "rpm":
                    result = subprocess.run(["rpm", "-q", package], 
                                         capture_output=True, 
                                         timeout=10)
                    if result.returncode == 0:
                        return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        # Check system paths
        return any(pathlib.Path(path).exists() for path in possible_paths)
    

    def download_file(self, url, destination):
        """Download a file from URL to destination"""
        print(f"Downloading {url}...")
        temp_file = f"{destination}.tmp"
        try:
            urllib.request.urlretrieve(url, temp_file)
            shutil.move(temp_file, destination)
            print("Download completed!")
            return True
        except Exception as e:
            print(f"Download failed: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False

    def install_mono(self):
        """Download and install Wine Mono in the prefix"""
        DEV_MODE = True
        
        cache_dir = os.path.expanduser("~/.cache/pso_wine")
        os.makedirs(cache_dir, exist_ok=True)

        mono_version = "9.3.0"
        mono_filename = f"wine-mono-{mono_version}-x86.msi"
        mono_url = f"https://dl.winehq.org/wine/wine-mono/{mono_version}/{mono_filename}"
        mono_path = os.path.join(cache_dir, mono_filename)

        try:
            have_valid_installer = os.path.exists(mono_path) and os.path.getsize(mono_path) >= 1024

            if DEV_MODE and have_valid_installer:
                print(f"Using existing installer at {mono_path}")
            else:
                if have_valid_installer:
                    os.remove(mono_path)
                if not self.download_file(mono_url, mono_path):
                    return False

            if not os.path.exists(mono_path) or os.path.getsize(mono_path) < 1024:
                print("Wine Mono installer file is missing or corrupt")
                return False

            print("Installing Wine Mono...")
            
            # Try installing with more verbose output and different switches
            install_commands = [
                ["wine", "msiexec", "/i", mono_path, "/l*v", f"{cache_dir}/mono_install.log"],
                ["wine", "msiexec", "/i", mono_path, "/qn"],  # Silent install
                ["wine", "msiexec", "/i", mono_path, "/quiet"],  # Another form of silent install
            ]
            
            success = False
            for cmd in install_commands:
                print(f"Trying installation command: {' '.join(cmd)}")
                exit_code = self.run_command(cmd, timeout=None)
                
                # After each attempt, verify the files exist
                if self._verify_mono_installation():
                    success = True
                    break
                else:
                    print(f"Installation attempt failed or files not found. Exit code: {exit_code}")
                    # Kill any hanging processes
                    subprocess.run(["wineserver", "-k"], env=self.env)
                    time.sleep(2)
            
            if success:
                print("Wine Mono installation completed and verified successfully!")
                return True
            else:
                print("Wine Mono installation failed verification")
                return False

        except Exception as e:
            print(f"Error during Mono installation: {e}")
            if os.path.exists(mono_path):
                os.remove(mono_path)
            return False

    def _verify_mono_installation(self):
        """Verify Mono installation by checking files and registry"""
        # First check if system Mono is installed
        if self.check_system_mono():
            print("System Mono installation detected, skipping Wine Mono version check")
            
            # Just verify registry entries when system Mono is present
            registry_keys = [
                "HKLM\\Software\\Microsoft\\NET Framework Setup\\NDP\\v4\\Full",
                "HKLM\\Software\\Microsoft\\NET Framework Setup\\NDP\\v4\\Client",
                "HKLM\\Software\\Mono",
            ]
            
            for key in registry_keys:
                try:
                    reg_result = subprocess.run(
                        ["wine", "reg", "query", key],
                        env=self.env,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if reg_result.returncode == 0:
                        print(f"Found Mono registry entry: {key}")
                        print(f"Registry output:\n{reg_result.stdout}")
                        return True  # If we find any valid registry entry with system Mono, we're good
                except Exception as e:
                    print(f"Error checking registry key {key}: {e}")
                    continue
                    
            print("No Mono registry entries found even with system Mono")
            return False
        
        # If no system Mono, do the full verification
        print("No system Mono detected, performing full Wine Mono verification...")
        
        # Check critical paths - these are the main Mono directories and files
        critical_paths = [
            os.path.join(self.prefix_path, "drive_c/windows/Microsoft.NET"),
            os.path.join(self.prefix_path, "drive_c/windows/mono"),
            os.path.join(self.prefix_path, "drive_c/Program Files/Mono"),
        ]
        
        files_exist = any(os.path.exists(path) for path in critical_paths)  # Only need one of these to exist
        if not files_exist:
            print("No Mono directories found in expected locations:")
            for path in critical_paths:
                print(f"  {'✓' if os.path.exists(path) else '✗'} {path}")
            return False
        
        # Check registry entries for Mono
        registry_keys = [
            "HKLM\\Software\\Microsoft\\NET Framework Setup\\NDP\\v4\\Full",
            "HKLM\\Software\\Microsoft\\NET Framework Setup\\NDP\\v4\\Client",
            "HKLM\\Software\\Mono",
        ]
        
        registry_found = False
        for key in registry_keys:
            try:
                reg_result = subprocess.run(
                    ["wine", "reg", "query", key],
                    env=self.env,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if reg_result.returncode == 0:
                    print(f"Found Mono registry entry: {key}")
                    print(f"Registry output:\n{reg_result.stdout}")
                    registry_found = True
                    break
            except Exception as e:
                print(f"Error checking registry key {key}: {e}")
                continue
        
        if not registry_found:
            print("No Mono registry entries found")
            return False
            
        # Check if mono is actually working by trying to run a simple test
        try:
            test_result = subprocess.run(
                ["wine", "mono", "--version"],
                env=self.env,
                capture_output=True,
                text=True,
                timeout=10
            )
            if test_result.returncode == 0:
                print(f"Mono test successful:\n{test_result.stdout}")
            else:
                print("Mono version check failed")
                return False
        except Exception as e:
            print(f"Error testing mono command: {e}")
            return False
        
        return True

    def check_prefix_mono(self):
        """Check if Wine Mono is installed in the prefix"""
        return self._verify_mono_installation()
            
    def check_system_gecko(self):
        """Check if Wine Gecko is installed system-wide"""
        possible_paths = [
            "/usr/share/wine/gecko",
            "/opt/wine/gecko",
            "/usr/lib/wine/gecko",
        ]
        
        # Check package managers
        package_managers = {
            "dpkg": "wine-gecko",
            "pacman": "wine-gecko",
            "rpm": "wine-gecko",
        }
        
        for pm, package in package_managers.items():
            try:
                if pm == "dpkg":
                    result = subprocess.run(["dpkg", "-s", package], 
                                        capture_output=True, 
                                        timeout=10)
                    if result.returncode == 0:
                        return True
                elif pm == "pacman":
                    result = subprocess.run(["pacman", "-Qi", package], 
                                        capture_output=True, 
                                        timeout=10)
                    if result.returncode == 0:
                        return True
                elif pm == "rpm":
                    result = subprocess.run(["rpm", "-q", package], 
                                        capture_output=True, 
                                        timeout=10)
                    if result.returncode == 0:
                        return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        # Check system paths
        return any(pathlib.Path(path).exists() for path in possible_paths)

    def check_prefix_gecko(self):
        """Check if Wine Gecko is installed in the prefix"""
        try:
            result = subprocess.run(
                ["wine", "reg", "query", "HKLM\\Software\\Wine\\MSHTML"],
                env=self.env,
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False

    def install_gecko(self):
        """Download and install Wine Gecko in the prefix"""
        DEV_MODE = True
        
        cache_dir = os.path.expanduser("~/.cache/pso_wine")
        os.makedirs(cache_dir, exist_ok=True)

        gecko_version = "2.47.4"
        gecko_files = [
            f"wine-gecko-{gecko_version}-x86.msi",
            f"wine-gecko-{gecko_version}-x86_64.msi"
        ]
        
        try:
            for gecko_filename in gecko_files:
                gecko_url = f"https://dl.winehq.org/wine/wine-gecko/{gecko_version}/{gecko_filename}"
                gecko_path = os.path.join(cache_dir, gecko_filename)
                
                have_valid_installer = os.path.exists(gecko_path) and os.path.getsize(gecko_path) >= 1024

                if DEV_MODE and have_valid_installer:
                    print(f"Using existing installer at {gecko_path}")
                else:
                    if have_valid_installer:
                        os.remove(gecko_path)
                    if not self.download_file(gecko_url, gecko_path):
                        return False

                if not os.path.exists(gecko_path) or os.path.getsize(gecko_path) < 1024:
                    print(f"Wine Gecko installer file {gecko_filename} is missing or corrupt")
                    return False

                print(f"Installing Wine Gecko ({gecko_filename})...")
                
                # Try installing with more verbose output and different switches
                install_commands = [
                    ["wine", "msiexec", "/i", gecko_path, "/l*v", f"{cache_dir}/gecko_install_{gecko_filename}.log"],
                    ["wine", "msiexec", "/i", gecko_path, "/qn"],  # Silent install
                    ["wine", "msiexec", "/i", gecko_path, "/quiet"],  # Another form of silent install
                ]
                
                success = False
                for cmd in install_commands:
                    print(f"Trying installation command: {' '.join(cmd)}")
                    exit_code = self.run_command(cmd, timeout=None)
                    
                    # After each attempt, verify the files exist
                    if self._verify_gecko_installation():
                        success = True
                        break
                    else:
                        print(f"Installation attempt failed or files not found. Exit code: {exit_code}")
                        # Kill any hanging processes
                        subprocess.run(["wineserver", "-k"], env=self.env)
                        time.sleep(2)
                
                if not success:
                    print(f"All installation attempts for {gecko_filename} failed")
                    return False

            # Final verification after both installers
            if self._verify_gecko_installation():
                print("Wine Gecko installation completed and verified successfully!")
                return True
            else:
                print("Wine Gecko installation could not be verified")
                return False

        except Exception as e:
            print(f"Error during Gecko installation: {e}")
            if os.path.exists(gecko_path):
                os.remove(gecko_path)
            return False

    def _verify_gecko_installation(self):
        """Verify Gecko installation by checking files and registry"""
        # First check if system Gecko is installed
        if self.check_system_gecko():
            print("System Gecko installation detected, performing basic verification...")
            
            # Verify basic registry entries when system Gecko is present
            try:
                reg_result = subprocess.run(
                    ["wine", "reg", "query", "HKLM\\Software\\Wine\\MSHTML"],
                    env=self.env,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if reg_result.returncode == 0:
                    print("Found Gecko registry entry in MSHTML")
                    print(f"Registry output:\n{reg_result.stdout}")
                    return True
            except Exception as e:
                print(f"Error checking registry: {e}")
                return False
        
        # If no system Gecko or basic verification failed, do full verification
        print("Performing full Wine Gecko verification...")
        
        # Check critical paths for both 32-bit and 64-bit Gecko
        critical_paths = [
            os.path.join(self.prefix_path, "drive_c/windows/system32/gecko"),
            os.path.join(self.prefix_path, "drive_c/windows/syswow64/gecko"),
            os.path.join(self.prefix_path, "drive_c/windows/system32/mshtml.dll"),
            os.path.join(self.prefix_path, "drive_c/windows/syswow64/mshtml.dll")
        ]
        
        # For Gecko, we want to check which specific files exist
        print("Checking Gecko files:")
        for path in critical_paths:
            exists = os.path.exists(path)
            print(f"  {'✓' if exists else '✗'} {path}")
            
        # Need at least one gecko directory and one mshtml.dll
        has_gecko_dir = any(os.path.exists(p) for p in critical_paths if "gecko" in p)
        has_mshtml = any(os.path.exists(p) for p in critical_paths if "mshtml.dll" in p)
        
        if not (has_gecko_dir and has_mshtml):
            print("Missing required Gecko files")
            return False
            
        # Check various registry entries that should exist with Gecko
        registry_keys = [
            "HKLM\\Software\\Wine\\MSHTML",
            "HKLM\\Software\\Microsoft\\Internet Explorer",
            "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings"
        ]
        
        registry_found = False
        for key in registry_keys:
            try:
                reg_result = subprocess.run(
                    ["wine", "reg", "query", key],
                    env=self.env,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if reg_result.returncode == 0:
                    print(f"Found Gecko-related registry entry: {key}")
                    print(f"Registry output:\n{reg_result.stdout}")
                    registry_found = True
            except Exception as e:
                print(f"Error checking registry key {key}: {e}")
                continue
        
        if not registry_found:
            print("No Gecko registry entries found")
            return False
        
        # Additional check: Try to verify mshtml.dll is properly registered
        try:
            regsvr_result = subprocess.run(
                ["wine", "regsvr32", "/s", "mshtml.dll"],
                env=self.env,
                capture_output=True,
                text=True,
                timeout=10
            )
            if regsvr_result.returncode != 0:
                print("Warning: mshtml.dll registration check failed")
        except Exception as e:
            print(f"Warning: Could not verify mshtml.dll registration: {e}")
        
        return True

    def setup_prefix(self):
        """Set up and configure the Wine prefix with all requirements"""
        #temp do not suppress to ensure mono and gecko stuff works
        #self.suppress_gui()
        if not self.check_wine_installed():
            raise WineSetupError("Wine is not installed or not accessible from the command line.")

        os.makedirs(self.prefix_path, exist_ok=True)

        if not os.path.exists(os.path.join(self.prefix_path, "system.reg")):
            print("Initializing new Wine prefix...")
            
            # Initialize the prefix with wineboot
            print("Running wineboot initialization...")
            if self.run_command(["wineboot", "-u", "-i"], timeout=30) != 0:
                print("Warning: wineboot initialization may have failed")
                time.sleep(2)  # Give it a moment to settle anyway
            
            # Kill any lingering wineserver processes
            subprocess.run(["wineserver", "-k"], env=self.env)
            time.sleep(1)
            
            print("SKIPPING WINDOWS 7 CONFIG STEPS, let pso.bat do it")
            
            # Kill any lingering processes again
            subprocess.run(["wineserver", "-k"], env=self.env)
            time.sleep(2)

        # Handle Mono installation
        if self.check_prefix_mono():
            print("Wine Mono is already installed in the prefix.")
        elif self.check_system_mono():
            print("System-wide Wine Mono installation detected.")
        else:
            print("No Wine Mono installation found. Installing in prefix...")
            if not self.install_mono():
                print("Warning: Failed to install Wine Mono. The launcher might not work properly.")
                print("You may need to install wine-mono using your system's package manager:")
                print("  Debian/Ubuntu: sudo apt install wine-mono")
                print("  Arch Linux: sudo pacman -S wine-mono")
                print("  Fedora: sudo dnf install wine-mono")
                return False

        # Handle Gecko installation
        if self.check_prefix_gecko():
            print("Wine Gecko is already installed in the prefix.")
        elif self.check_system_gecko():
            print("System-wide Wine Gecko installation detected.")
        else:
            print("No Wine Gecko installation found. Installing in prefix...")
            if not self.install_gecko():
                print("Warning: Failed to install Wine Gecko. HTML rendering might not work properly.")
                print("You may need to install wine-gecko using your system's package manager:")
                print("  Debian/Ubuntu: sudo apt install wine-gecko")
                print("  Arch Linux: sudo pacman -S wine-gecko")
                print("  Fedora: sudo dnf install wine-gecko")
                return False

        return True

    def cleanup_prefix(self):
        """Remove the Wine prefix directory"""
        if os.path.exists(self.prefix_path):
            # First kill any wine processes
            subprocess.run(["wineserver", "-k"], env=self.env)
            time.sleep(1)
            
            # Then remove the prefix
            shutil.rmtree(self.prefix_path)