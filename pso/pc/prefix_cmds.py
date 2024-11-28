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
import tarfile
from cmd_runner import CommandRunner

# made by zeroz - tj

class WineSetupError(Exception):
    """Custom exception for Wine setup errors"""
    pass

class WineUtils(CommandRunner):
    def __init__(self, prefix_path="~/.local/share/ephinea-prefix"):
        self.prefix_path = os.path.expanduser(prefix_path)
        self.original_env = os.environ.copy()
        self.env = os.environ.copy()
        self.env["WINEPREFIX"] = self.prefix_path
        self.env["WINEDEBUG"] = "-all"
    
    def run_command(self, command, timeout=60):
        return super().run_command(command, timeout, self.env)
        
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
        """Download and install Wine Mono in the prefix. Use system Mono if available."""
        # If system Mono is available, ensure it's properly initialized
        if self.check_system_mono():
            print("System Mono detected, configuring the prefix for you to use it...")
            try:
                # Run wineboot once to initialize system mono
                self.run_command(["wineboot", "-u"], timeout=30)
                print("System mono configured. Rechecking prefix....")
                
                # Verify it worked
                if self._verify_mono_installation():
                    print("System Mono configuration completed successfully!")
                    return True
                    
                print("System wine mono configuration FAILED")
                print("System Mono configuration incomplete, falling back to local installation...")
            except Exception as e:
                print(f"Error configuring system Mono: {e}")
                print("Falling back to local installation...")
        
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
      
        """Verify Mono installation is properly configured, whether system or prefix"""
    # If system mono is available, verify using wine uninstaller
        if self.check_system_mono():
            #print("Checking for Wine Mono Runtime...")
            #result = self.run_command(["wine", "uninstaller", "--list"])
            #if result == 0:
            #    # We'll see the output in run_command since it uses PTY
            #    return True
            #    
            #print("Wine Mono Runtime check failed")
            #return False

            #just return true; no extra veri needed or worth it.
            # can make sure mono works by running dot net mcs compiled application.
            # note: system wine-mono does not do the same as local wine installed. won't have mono on cmd for example
            return True
        
        # For non-system (MSI) installations, do full verification
        print("Checking local Mono installation...")
        REQUIRED_REGISTRY_KEYS = [
            "HKLM\\Software\\Microsoft\\NET Framework Setup\\NDP\\v4\\Full",
            "HKLM\\Software\\Microsoft\\NET Framework Setup\\NDP\\v4\\Client",
        ]
        
        # Check essential registry keys
        registry_found = False
        for key in REQUIRED_REGISTRY_KEYS:
            try:
                reg_result = subprocess.run(
                    ["wine", "reg", "query", key],
                    env=self.env,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if reg_result.returncode == 0:
                    print(f"Found registry key: {key}")
                    print(f"Registry output:\n{reg_result.stdout}")
                    registry_found = True
                    break
            except Exception as e:
                print(f"Error checking registry key {key}: {e}")
                continue
                
        if not registry_found:
            print("Required Mono registry entries not found")
            return False
            
        # Verify core DLL presence and size
        framework_path = os.path.join(self.prefix_path, "drive_c/windows/Microsoft.NET/Framework")
        found_valid_dll = False
        min_dll_size = 100000  # Minimum size in bytes for a valid mscorlib.dll
        
        if os.path.exists(framework_path):
            for folder in os.listdir(framework_path):
                if folder.startswith('v4.'):
                    dll_path = os.path.join(framework_path, folder, "mscorlib.dll")
                    if os.path.exists(dll_path):
                        dll_size = os.path.getsize(dll_path)
                        if dll_size >= min_dll_size:
                            found_valid_dll = True
                            print(f"Found valid mscorlib.dll in {folder} (size: {dll_size:,} bytes)")
                            break
                        else:
                            print(f"Found mscorlib.dll in {folder} but size is too small: {dll_size:,} bytes")
        
        if not found_valid_dll:
            print("Could not find valid mscorlib.dll")
            return False
            
        print("Mono verification completed successfully")
        return True
            
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
                
                # gecko attempts. first should work
                install_commands = [
                    ["wine", "msiexec", "/i", gecko_path, "/l*v", f"{cache_dir}/gecko_install_{gecko_filename}.log"],
                    ["wine", "msiexec", "/i", gecko_path, "/qn"],  # Silent install
                    ["wine", "msiexec", "/i", gecko_path, "/quiet"],  # Another form of silent install
                ]
                
                success = False
                for cmd in install_commands:
                    print(f"Trying installation command: {' '.join(cmd)}")
                    exit_code = self.run_command(cmd, timeout=None)
                    
                    # verify the files exist
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
        
        # If no system Gecko...verify
        print("Performing full Wine Gecko verification...")
        
        # check both 32-bit and 64-bit Gecko
        critical_paths = [
            os.path.join(self.prefix_path, "drive_c/windows/system32/gecko"),
            os.path.join(self.prefix_path, "drive_c/windows/syswow64/gecko"),
            os.path.join(self.prefix_path, "drive_c/windows/system32/mshtml.dll"),
            os.path.join(self.prefix_path, "drive_c/windows/syswow64/mshtml.dll")
        ]
        
        # gecko files exist?
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
            
        # Check registry entries for gecko
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
        
        # Try to verify mshtml.dll is properly registered
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

    def setup_prefix(self, install_dxvk=True):
        """Set up and configure the Wine prefix with all requirements"""
        self.suppress_gui()
        if not self.check_wine_installed():
            raise WineSetupError("Wine is not installed or not accessible from the command line.")

        os.makedirs(self.prefix_path, exist_ok=True)

        #add windowing associate
        self.run_command([
        "wine", "reg", "add", "HKCU\\Software\\Wine\\X11 Driver",
        "/v", "Managed", "/t", "REG_SZ", "/d", "Y", "/f"
        ])

        # Initialize new prefix if needed
        if not os.path.exists(os.path.join(self.prefix_path, "system.reg")):
            print("Initializing new Wine prefix...")
            print("Running wineboot initialization...")
            if self.run_command(["wineboot", "-u", "-i"], timeout=60) != 0:
                print("Warning: wineboot initialization may have failed")
                time.sleep(2)
                
            subprocess.run(["wineserver", "-k"], env=self.env)
            time.sleep(1)
            
            print("SKIPPING WINDOWS 7 CONFIG STEPS, let pso.bat do it")
            
            subprocess.run(["wineserver", "-k"], env=self.env)
            time.sleep(2)

        # Handle Mono installation
        if self._verify_mono_installation():
            print("Mono is already configured in the prefix.")
        else:
            print("No Mono configuration found prexisting WITHIN PREFIX. Configuring...")
            if not self.install_mono():
                print("Warning: Failed to install Mono. The launcher might not work properly.")
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

        if install_dxvk:
            if self.check_prefix_dxvk():
                print("DXVK is already installed in the prefix.")
            elif self.check_system_dxvk():
                print("System-wide DXVK installation detected, configuring prefix...")
                if not self.install_dxvk():
                    print("Warning: Failed to configure system DXVK.")
                    print("You may need to install DXVK using your system's package manager:")
                    print("  Debian/Ubuntu: sudo apt install dxvk")
                    print("  Arch Linux: yay -S dxvk-bin")
                    print("  Fedora: sudo dnf install dxvk")
                    return False
            else:
                print("No DXVK installation found. Installing in prefix...")
                if not self.install_dxvk():
                    print("Warning: Failed to install DXVK. Graphics performance might not be optimal.")
                    print("You may need to install DXVK using your system's package manager:")
                    print("  Debian/Ubuntu: sudo apt install dxvk")
                    print("  Arch Linux: yay -S dxvk-bin")
                    print("  Fedora: sudo dnf install dxvk")
                    return False
        else:
            print("Skipping DXVK installation as per user request")

        print("All components installed successfully!")
        return True
    
    def check_system_dxvk(self):
        """Check if DXVK is installed system-wide"""
        possible_paths = [
            "/usr/share/dxvk",
            "/usr/lib/dxvk",
            "/usr/local/share/dxvk",
        ]
        
        # Check package managers
        package_managers = {
            "dpkg": "dxvk",
            "pacman": "dxvk-bin",
            "rpm": "dxvk",
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

    def install_dxvk(self):
        """Install DXVK in the prefix. Use system DXVK if available, otherwise download."""
        DEV_MODE = True
        cache_dir = os.path.expanduser("~/.cache/pso_wine")
        os.makedirs(cache_dir, exist_ok=True)

        # If system DXVK is available, use system setup script
        if self.check_system_dxvk():
            print("System DXVK detected, attempting to configure prefix...")
            
            # Common paths for dxvk setup script
            setup_paths = [
                "/usr/share/dxvk/setup_dxvk.sh",
                "/usr/bin/setup_dxvk",
                "/usr/local/bin/setup_dxvk"
            ]
            
            setup_script = None
            for path in setup_paths:
                if os.path.exists(path):
                    setup_script = path
                    break
            
            if setup_script:
                print(f"Found DXVK setup script at {setup_script}")
                try:
                    # Run the setup script with our prefix
                    result = subprocess.run(
                        [setup_script, "install"],
                        env=self.env,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        print("System DXVK setup completed successfully!")
                        return True
                    print(f"DXVK setup script failed with error code {result.returncode}")
                except Exception as e:
                    print(f"Error running DXVK setup script: {e}")
            else:
                print("No system DXVK setup script found!")

            print("System DXVK setup failed, falling back to manual installation...")
                    

        # Manual installation from GitHub if system DXVK isn't available or setup failed
        try:
            dxvk_version = "2.3"  # Latest stable as of writing
            dxvk_filename = f"dxvk-{dxvk_version}.tar.gz"
            dxvk_url = f"https://github.com/doitsujin/dxvk/releases/download/v{dxvk_version}/{dxvk_filename}"
            dxvk_path = os.path.join(cache_dir, dxvk_filename)

            print(f"Installing DXVK {dxvk_version} from GitHub...")
            
            # Download and verify archive
            have_valid_archive = os.path.exists(dxvk_path) and os.path.getsize(dxvk_path) >= 1024
            if DEV_MODE and have_valid_archive:
                print(f"Using existing DXVK archive at {dxvk_path}")
            else:
                if have_valid_archive:
                    os.remove(dxvk_path)
                if not self.download_file(dxvk_url, dxvk_path):
                    raise Exception("Failed to download DXVK archive")

            # Extract and install DXVK
            print("Extracting DXVK...")
            extract_dir = os.path.join(cache_dir, f"dxvk-{dxvk_version}")
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
                
            with tarfile.open(dxvk_path, "r:gz") as tar:
                tar.extractall(cache_dir)

            # Install the DLLs
            dll_paths = {
                "x32": os.path.join(extract_dir, "x32"),
                "x64": os.path.join(extract_dir, "x64")
            }

            for arch, dll_dir in dll_paths.items():
                if os.path.exists(dll_dir):
                    for dll in ["d3d9.dll", "d3d10core.dll", "d3d11.dll", "dxgi.dll", "d3d8"]:
                        dll_path = os.path.join(dll_dir, dll)
                        if os.path.exists(dll_path):
                            target_dir = os.path.join(self.prefix_path, 
                                                    "drive_c/windows/system32" if arch == "x64" else "drive_c/windows/syswow64")
                            os.makedirs(target_dir, exist_ok=True)
                            shutil.copy2(dll_path, target_dir)
                            print(f"Installed {dll} to {target_dir}")

            # Set DLL overrides
            override_dlls = ["d3d9", "d3d10core", "d3d11", "dxgi", "d3d8"]
            for dll in override_dlls:
                #d3d9 will get dummy slapped back to native,builtin later. but its intended
                self.run_command([
                    "wine", "reg", "add", "HKEY_CURRENT_USER\\Software\\Wine\\DllOverrides",
                    "/v", dll, "/d", "native", "/f"
                ], timeout=10)

            if self._verify_dxvk_installation():
                print("DXVK installation completed and verified successfully!")
                return True
                
            raise Exception("DXVK installation verification failed")

        except Exception as e:
            print(f"Manual DXVK installation failed: {e}")
            print("Attempting fallback installation via winetricks...")
            
            # Fallback to winetricks if manual installation fails
            if self._install_dxvk_winetricks():
                if self._verify_dxvk_installation():
                    print("DXVK installation completed successfully via winetricks!")
                    return True
                
            print("All DXVK installation methods failed")
            return False

    def _install_dxvk_winetricks(self):
        """Fallback method to install DXVK using winetricks"""
        try:
            # Check if winetricks is available
            if shutil.which("winetricks") is None:
                print("Winetricks not found, cannot attempt fallback installation")
                return False

            print("Attempting DXVK installation via winetricks...")
            result = subprocess.run(
                ["winetricks", "-q", "dxvk"],
                env=self.env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                print("Winetricks DXVK installation completed")
                return True
            else:
                print(f"Winetricks DXVK installation failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"Error during winetricks DXVK installation: {e}")
            return False
    
    def check_prefix_dxvk(self):
        """Check if DXVK is installed in the prefix"""
        #add more custom stuff independent here if needed
        return self._verify_dxvk_installation()

    def _verify_dxvk_installation(self):
        """Verify DXVK installation actually installed"""
        # Check if system DXVK is available
        if self.check_system_dxvk():
            print("System DXVK installation detected, checking basic configuration...")
            
            # verify DLL overrides when system DXVK is present
            try:
                reg_result = subprocess.run(
                    ["wine", "reg", "query", "HKEY_CURRENT_USER\\Software\\Wine\\DllOverrides"],
                    env=self.env,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if reg_result.returncode == 0 and any(dll in reg_result.stdout for dll in ["d3d9", "d3d11", "dxgi"]):
                    print("Found DXVK DLL overrides in registry")
                    print(f"Registry output:\n{reg_result.stdout}")
                    return True
            except Exception as e:
                print(f"Error checking registry: {e}")
                return False
                
        # full verification for non-system DXVK
        print("Performing full DXVK verification...")
        
        # check DXVK DLLs in both 32-bit and 64-bit system directories
        dll_list = ["d3d9.dll", "d3d10core.dll", "d3d11.dll", "dxgi.dll"]
        dll_paths = {
            "system32": os.path.join(self.prefix_path, "drive_c/windows/system32"),
            "syswow64": os.path.join(self.prefix_path, "drive_c/windows/syswow64")
        }
        
        print("Checking DXVK DLLs:")
        all_dlls_present = True
        for dir_name, dir_path in dll_paths.items():
            for dll in dll_list:
                dll_path = os.path.join(dir_path, dll)
                exists = os.path.exists(dll_path)
                print(f"  {'✓' if exists else '✗'} {dir_name}/{dll}")
                if not exists:
                    all_dlls_present = False
                    
        if not all_dlls_present:
            print("Missing required DXVK DLLs")
            return False
                
        # Check DLL overrides in registry
        try:
            reg_result = subprocess.run(
                ["wine", "reg", "query", "HKEY_CURRENT_USER\\Software\\Wine\\DllOverrides"],
                env=self.env,
                capture_output=True,
                text=True,
                timeout=10
            )
            if reg_result.returncode == 0:
                print("Found registry entries:")
                print(reg_result.stdout)
                
                # More flexible verification of registry entries
                required_dlls = {"d3d9", "d3d10core", "d3d11", "dxgi"}
                found_dlls = set()
                
                for line in reg_result.stdout.splitlines():
                    for dll in required_dlls:
                        if dll in line.lower() and "native,builtin" in line.lower():
                            found_dlls.add(dll)
                
                missing_dlls = required_dlls - found_dlls
                if missing_dlls:
                    print(f"Missing DLL overrides for: {', '.join(missing_dlls)}")
                    return False
            else:
                print("Failed to query DLL overrides")
                return False
        except Exception as e:
            print(f"Error checking DLL overrides: {e}")
            return False

        print("DXVK verification successful - all DLLs and registry entries present")
        return True

    def cleanup_prefix(self):
        """Remove the Wine prefix directory"""
        if os.path.exists(self.prefix_path):
            # First kill any wine processes
            subprocess.run(["wineserver", "-k"], env=self.env)
            time.sleep(1)
            
            # Then remove the prefix
            shutil.rmtree(self.prefix_path)