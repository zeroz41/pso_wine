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
import platform
import re

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
    
    def run_command(self, command, timeout=60, env=None, capture_output=False):
        if env is None:
            env = self.env
        return super().run_command(command, timeout=timeout, env=env, capture_output=capture_output)

        
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
            result = self.run_command(["wine", "--version"], timeout=10)
            return result == 0
        except Exception:
            return False

    def check_system_mono(self):
        """Check if Wine Mono is installed system-wide"""
        possible_paths = [
            "/usr/share/wine/mono",
            "/opt/wine/mono",
            "/usr/lib/wine/mono",
        ]
        
        # Check package managers
        package_name = "wine-mono"  # Same name across distros
        if self.check_package_installed(package_name):
            print("Found wine-mono system package installed")
            return True

        # Check system paths as fallback
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
        
    def get_cache_dir(self):
        if platform.system() == "Linux":
            return os.path.expanduser("~/.cache/pso_wine")
        elif platform.system() == "Darwin":
            return os.path.expanduser("~/Library/Caches/pso_wine")
        
        return None 

    def install_mono(self):
        """Download and install Wine Mono in the prefix"""
        cache_dir = self.get_cache_dir()
        os.makedirs(cache_dir, exist_ok=True)

        mono_version = "9.3.0"
        mono_filename = f"wine-mono-{mono_version}-x86.msi"
        mono_url = f"https://dl.winehq.org/wine/wine-mono/{mono_version}/{mono_filename}"
        mono_path = os.path.join(cache_dir, mono_filename)

        try:
            # Download if needed
            if not os.path.exists(mono_path) or os.path.getsize(mono_path) < 1024:
                if not self.download_file(mono_url, mono_path):
                    return False

            print("Installing Wine Mono...")
            
            # Kill any existing wine processes and wait
            self.run_command(["wineserver", "-k"], timeout=10)
            
            # Do a clean prefix initialization
            self.run_command(["wineboot", "-i"], timeout=30)
            
            # Run the MSI installer with a longer timeout
            print("Running MSI installation...")
            result = self.run_command(
                ["wine", "msiexec", "/i", mono_path],
                timeout=500 # long timnout
            )
            
            if result != 0:
                print("MSI installation failed")
                return False
                
            # Final verification
            if self._verify_mono_installation():
                print("Wine Mono installation completed successfully!")
                return True
            else:
                print("Wine Mono installation could not be verified")
                return False

        except Exception as e:
            print(f"Error during Mono installation: {e}")
            return False

    def _verify_mono_installation(self):
        """Verify Mono installation is properly configured, whether system or prefix"""
        # If system mono is available, verify using wine uninstaller
        if self.check_system_mono():
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
                result = self.run_command(
                    ["wine", "reg", "query", key],
                    timeout=10
                )
                if result == 0:
                    print(f"Found registry key: {key}")
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
    
    def _get_gecko_version(self):
        """Determine appropriate Gecko version based on Wine version"""
        try:
            # Get Wine version using our new command runner with capture_output
            returncode, output = self.run_command(
                ["wine", "--version"], 
                timeout=10, 
                capture_output=True
            )
            
            if returncode != 0:
                print("Could not determine Wine version, defaulting to Gecko 2.47.4")
                return "2.47.4"

            # Version mapping
            gecko_versions = {
                4.0: "2.47.0",
                5.0: "2.47.1",
                6.0: "2.47.2",
                7.0: "2.47.3",
                8.0: "2.47.4"  # 8.0 and up
            }

            # Find appropriate version
            version_match = re.search(r'wine-(\d+\.\d+)', output)
            if not version_match:
                print("Could not parse Wine version output, defaulting to Gecko 2.47.4")
                return "2.47.4"
            
            wine_ver = float(version_match.group(1))
            
            # Find appropriate version
            selected_version = "2.47.4"  # Default to latest for 8.0+ or unknown versions
            for ver in sorted(gecko_versions.keys()):
                if wine_ver >= ver:
                    selected_version = gecko_versions[ver]
            
            print(f"Selected Gecko version {selected_version} for Wine {wine_ver}")
            return selected_version

        except Exception as e:
            print(f"Error determining Gecko version: {e}, defaulting to 2.47.4")
            return "2.47.4"

    def check_prefix_gecko(self):
        """Check if Wine Gecko is installed in the prefix"""
        try:
            result = self.run_command(
                ["wine", "reg", "query", "HKLM\\Software\\Wine\\MSHTML"],
                timeout=10
            )
            return result == 0
        except Exception:
            return False
        
    def check_system_gecko(self):
        """Check if Wine Gecko is installed system-wide"""
        possible_paths = [
            "/usr/share/wine/gecko",
            "/opt/wine/gecko",
            "/usr/lib/wine/gecko",
        ]
        
        # Check package managers first
        package_name = "wine-gecko"  # Same name across distros
        if self.check_package_installed(package_name):
            print("System Gecko package verification:")
            print("  ✓ Found wine-gecko system package installed")
            return True

        # Check system paths as fallback
        for path in possible_paths:
            if pathlib.Path(path).exists():
                print(f"  ✓ Found Gecko in system path: {path}")
                return True
                
        print("  ✗ No system Gecko installation found")
        return False

    def install_gecko(self, has_system_gecko=None):
        """Download and install Wine Gecko in the prefix"""
        if has_system_gecko is None:
            has_system_gecko = self.check_system_gecko()
            
        cache_dir = self.get_cache_dir()
        os.makedirs(cache_dir, exist_ok=True)

        # Get appropriate Gecko version based on Wine version
        gecko_version = self._get_gecko_version()
        
        gecko_files = [
            f"wine-gecko-{gecko_version}-x86.msi",
            f"wine-gecko-{gecko_version}-x86_64.msi"
        ]
        
        try:
            # Clean slate before install
            self.run_command(["wineserver", "-k"], timeout=10)
            
            for gecko_filename in gecko_files:
                gecko_url = f"https://dl.winehq.org/wine/wine-gecko/{gecko_version}/{gecko_filename}"
                gecko_path = os.path.join(cache_dir, gecko_filename)
                
                # Use existing installer if valid
                have_valid_installer = os.path.exists(gecko_path) and os.path.getsize(gecko_path) >= 1024
                if have_valid_installer:
                    print(f"Using existing installer at {gecko_path}")
                else:
                    if not self.download_file(gecko_url, gecko_path):
                        return False

                print(f"Installing Wine Gecko ({gecko_filename})...")
                result = self.run_command(
                    ["wine", "msiexec", "/i", gecko_path],
                    timeout=None
                )
                
                if result != 0:
                    print(f"MSI installation failed for {gecko_filename}")
                    return False

                # Clean up after each installer
                self.run_command(["wineserver", "-k"], timeout=10)

            # Final verification
            if self._verify_gecko_installation(has_system_gecko):
                print("Wine Gecko installation completed successfully!")
                return True

            print("Wine Gecko installation could not be verified")
            return False

        except Exception as e:
            print(f"Error during Gecko installation: {e}")
            return False
        
    def _verify_gecko_installation(self, has_system_gecko=None):
        """Verify Gecko installation is properly configured"""
        # Cache system check result if not provided
        if has_system_gecko is None:
            has_system_gecko = self.check_system_gecko()
            
        print("\nPerforming Gecko verification...")
        verification_passed = True

        # Always check registry
        print("\nChecking MSHTML registry:")
        try:
            result = self.run_command(
                ["wine", "reg", "query", "HKLM\\Software\\Wine\\MSHTML"],
                timeout=10
            )
            print(f"  {'✓' if result == 0 else '✗'} MSHTML registry key {'found' if result == 0 else 'not found'}")
            if result != 0:
                verification_passed = False
        except Exception as e:
            print(f"  ✗ Error checking registry: {e}")
            verification_passed = False

        # Always check critical paths
        print("\nChecking critical Gecko paths:")
        critical_paths = [
            os.path.join(self.prefix_path, "drive_c/windows/system32/gecko"),
            os.path.join(self.prefix_path, "drive_c/windows/syswow64/gecko"),
            os.path.join(self.prefix_path, "drive_c/windows/system32/mshtml.dll"),
            os.path.join(self.prefix_path, "drive_c/windows/syswow64/mshtml.dll")
        ]
        
        for path in critical_paths:
            exists = os.path.exists(path)
            print(f"  {'✓' if exists else '✗'} {path}")
            if not exists:
                verification_passed = False

        print(f"\nGecko verification {'passed' if verification_passed else 'failed'} all checks")
        return verification_passed

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
                        
            self.run_command(["wineserver", "-k"], timeout=10)
            print("SKIPPING WINDOWS 7 CONFIG STEPS, let pso.bat do it")

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

        # Check Gecko - streamlined like DXVK
        has_system_gecko = self.check_system_gecko()
        if has_system_gecko:
            print("System-wide Wine Gecko detected.")
            if not self._verify_gecko_installation(has_system_gecko):
                print("Configuring system Gecko in prefix...")
                if not self.install_gecko(has_system_gecko):
                    print("Warning: Failed to configure system Gecko.")
                    return False
        else:
            print("No system Wine Gecko detected, checking prefix installation...")
            if not self._verify_gecko_installation(has_system_gecko):
                print("Installing Gecko in prefix...")
                if not self.install_gecko(has_system_gecko):
                    print("Warning: Failed to install Wine Gecko. You may need to install using your package manager:")
                    print("  Debian/Ubuntu: sudo apt install wine-gecko")
                    print("  Arch Linux: sudo pacman -S wine-gecko")
                    print("  Fedora: sudo dnf install wine-gecko")
                    return False

        if install_dxvk:
            # Check DXVK status once and store the result
            has_system_dxvk = self.check_system_dxvk()
            
            if self._verify_dxvk_installation(has_system_dxvk):
                print("DXVK is already installed in the prefix.")
            elif has_system_dxvk:
                print("System-wide DXVK installation detected, configuring prefix...")
                if not self.install_dxvk(has_system_dxvk):
                    print("Warning: Failed to configure system DXVK.")
                    return False
            else:
                print("No DXVK installation found. Installing in prefix...")
                if not self.install_dxvk(has_system_dxvk):
                    print("Warning: Failed to install DXVK. You may need to install using your package manager:")
                    print("  Debian/Ubuntu: sudo apt install dxvk")
                    print("  Arch Linux: yay -S dxvk-bin")
                    print("  Fedora: sudo dnf install dxvk")
                    return False

        print("All components installed successfully!")
        return True

    
    def get_system_package_manager(self):
        """Detect the system's package manager"""
        if platform.system() != "Linux":
            return None
            
        # Check for common package managers
        package_managers = {
            "pacman": "pacman",
            "apt": "dpkg",
            "dnf": "rpm",
            "yum": "rpm"
        }
        
        for cmd, pm_type in package_managers.items():
            try:
                if self.run_command(["which", cmd], timeout=10) == 0:
                    return pm_type
            except Exception:
                continue
                
        return None
    
    def check_package_installed(self, package_name):
        """Check if a package is installed using the appropriate package manager"""
        pm = self.get_system_package_manager()
        if not pm:
            return False
            
        try:
            if pm == "pacman":
                result = self.run_command(["pacman", "-Qi", package_name], timeout=10)
            elif pm == "dpkg":
                result = self.run_command(["dpkg", "-s", package_name], timeout=10)
            elif pm == "rpm":
                result = self.run_command(["rpm", "-q", package_name], timeout=10)
            return result == 0
        except Exception:
            return False
    
    def check_system_dxvk(self):
        """Check if DXVK is installed system-wide"""
        possible_paths = [
            "/usr/share/dxvk",
            "/usr/lib/dxvk",
            "/usr/local/share/dxvk",
        ]
        
        # Check package managers
        package_name = "dxvk-bin" if self.get_system_package_manager() == "pacman" else "dxvk"
        if self.check_package_installed(package_name):
            print("Found dxvk system package installed")
            return True

        # Check system paths as fallback
        return any(pathlib.Path(path).exists() for path in possible_paths)

    def install_dxvk(self, has_system_dxvk=None):
        """Install DXVK in the prefix. Use system DXVK if available, otherwise download."""
        DEV_MODE = True
        cache_dir = self.get_cache_dir()
        os.makedirs(cache_dir, exist_ok=True)

        # No need to check again - use the passed value
        override_setting = "native" if has_system_dxvk else "native,builtin"
        
        if has_system_dxvk:
            print("Using system DXVK installation...")
            setup_paths = [
                "/usr/share/dxvk/setup_dxvk.sh",
                "/usr/bin/setup_dxvk",
                "/usr/local/bin/setup_dxvk"
            ]
            
            setup_script = next((path for path in setup_paths if os.path.exists(path)), None)
            
            if setup_script:
                print(f"Found DXVK setup script at {setup_script}")
                try:
                    result = self.run_command([setup_script, "install"], timeout=30)
                    if result == 0 and self._verify_dxvk_installation(has_system_dxvk):
                        print("System DXVK setup completed successfully!")
                        return True
                    print(f"DXVK setup script failed or verification failed")
                except Exception as e:
                    print(f"Error running DXVK setup script: {e}")
            else:
                print("No system DXVK setup script found!")

            print("System DXVK setup failed, falling back to manual installation...")

        # Manual installation from GitHub
        try:
            dxvk_version = "2.3"
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

            # Set DLL overrides once with correct override_setting
            override_dlls = ["d3d9", "d3d10core", "d3d11", "dxgi", "d3d8"]
            for dll in override_dlls:
                self.run_command([
                    "wine", "reg", "add", "HKEY_CURRENT_USER\\Software\\Wine\\DllOverrides",
                    "/v", dll, "/d", override_setting, "/f"
                ], timeout=10)

            if self._verify_dxvk_installation(has_system_dxvk):
                print("DXVK installation completed and verified successfully!")
                return True
                
            raise Exception("DXVK installation verification failed")

        except Exception as e:
            print(f"Manual DXVK installation failed: {e}")
            return False
        
    def check_prefix_dxvk(self):
        """Check if DXVK is installed in the prefix"""
        #useless function. remove later
        return self._verify_dxvk_installation()

    def _verify_dxvk_installation(self, has_system_dxvk):
        """Verify DXVK installation actually installed"""
        # Use the system DXVK check result to determine expected override setting
        
        #convoluted but eh
        if has_system_dxvk is None:
            has_system_dxvk = self.check_system_dxvk()
            
        expected_override = "native" if has_system_dxvk else "native,builtin"
        print(f"Checking {'system' if has_system_dxvk else 'local'} DXVK installation (expecting '{expected_override}' overrides)...")
    
        # Check DXVK DLLs in both 32-bit and 64-bit system directories
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
                    
        if not all_dlls_present and not has_system_dxvk:
            print("Missing required DXVK DLLs")
            return False
                    
        # Check DLL overrides in registry
        try:
            result = self.run_command(
                ["wine", "reg", "query", "HKEY_CURRENT_USER\\Software\\Wine\\DllOverrides"],
                timeout=10
            )
            
            if result == 0:
                required_dlls = {"d3d9", "d3d10core", "d3d11", "dxgi"}
                found_dlls = set()
                
                for dll in required_dlls:
                    dll_result = self.run_command([
                        "wine", "reg", "query", 
                        "HKEY_CURRENT_USER\\Software\\Wine\\DllOverrides",
                        "/v", dll
                    ], timeout=10)
                    
                    if dll_result == 0:
                        found_dlls.add(dll)
                
                missing_dlls = required_dlls - found_dlls
                if missing_dlls:
                    print(f"Missing DLL overrides for: {', '.join(missing_dlls)}")
                    print(f"Note: Looking for '{expected_override}' override setting")
                    return False
            else:
                print("Failed to query DLL overrides")
                return False
        except Exception as e:
            print(f"Error checking DLL overrides: {e}")
            return False

        print("DXVK verification successful - all files and registry entries present")
        return True

    def cleanup_prefix(self):
        """Remove the Wine prefix directory"""
        if os.path.exists(self.prefix_path):
            # First kill any wine processes
            self.run_command(["wineserver", "-k"], timeout=10)
            # Then remove the prefix
            shutil.rmtree(self.prefix_path)