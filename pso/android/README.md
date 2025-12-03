# Android Installation of PSOBB using Wine

This repository provides an auto-installer for PSOBB (currently only for the Ephinea server) on Android using Wine. If you prefer manual installation or want to try other applications, the code in this repository can still be helpful.

## Instructions
1. Clone this repository. If you download it as a ZIP file, make sure to unzip it.
2. Move the unzipped folder into the Downloads directory on your Android device. The Downloads folder is specified because Android Windows emulators typically mount this folder into the Wine container.
3. Within the Wine prefix, navigate to the `pso_wine/pso/android` folder.
4. Double-click (or right-click with two fingers) and run the `install.bat` file.
   - Note: The installer will automatically download the PSO installer for you. If you already have it downloaded, place the `Ephinea_PSOBB_Installer.exe` file in the `bin` folder of this repository to skip the download.
5. The installer will automatically install the game, configure Wine settings, and create custom desktop and start menu shortcuts not made when running the exe standalone. This is particularly helpful for using the "Shortcuts" quick launch menu in apps like Winlator. By default, the game is installed in the `C:\` directory of the Wine prefix.
6. After installation, the script will exit. You're almost done!
7. The `android` folder contains a helpful configuration script named `setup_params.bat` that allows you to set the game's resolution and DirectX mode. Edit the `USER_PARAMS.txt` file to specify your desired settings, then run the script to apply the changes within seconds.
   - Hint: For the DirectX mode, set the value to 0 for DirectX 8, 1 for DirectX 9, or 5 for Vulkan. (Vulkan may not work depending on your setup; DirectX 9 is a safe choice.)
   - Important: The game's resolution cannot exceed the dimensions of your container's desktop, either horizontally or vertically, or the game will fail to launch. (This step is not strictly necessary if you can consistently open the launcher, but it has been troublesome for some users.)
8. Install Mono from the start menu on the bottom left of the Wine container.
9. Turn WINEESYNC off in your environment variables if it is defined there.
10. Patch the game:
   - First, patch PSOBB. Exit the container, go to the Shortcuts menu, launch PSOBB, select "Patch Download," and then close the game.
   - Next, patch the launcher. Start the launcher from the Shortcuts menu. It will prompt you to install a Gecko package; proceed with the installation. The launcher should download updates and open. You can now quit if desired, or browse the settings menu. If you have trouble opening the launcher, try reinitializing Mono and keep launching. You can also try running the executable directly from within the container. Consistency may vary at this point, but the good news is that the launcher only needs to be opened once for patching.
11. The game is now ready to play. From now on, launch PSOBB from the Shortcuts page in winlator if you use it. Else you may launch from virtual x11 desktop start menu. Controller support is built-in.
12. Remember to log in and use an overlay keyboard for the Enter key. Once you've logged in successfully, you won't need to enter your credentials again.

# For detailed Winlator settings and tips, i recommend using this updated guide from reddit user /r/yummaypatrol [Install guide](https://www.reddit.com/r/PSO/comments/1lo9jd3/how_to_get_ephinea_running_on_retroid_pocket_mini5/).


## User Params
USER_PARAMS.txt:
The exposed parameters here are settings that could also be configured within the launcher. Under the hood they are saved to the windows registry.

The `USER_PARAMS.txt` file allows you to configure the game's settings without modifying the batch scripts directly. The file contains key-value pairs for the following parameters:
- `WINDOWED`: Set to 1 for windowed mode or 0 for fullscreen mode.
- `HOR_RES`: Specify the horizontal resolution of the game.
- `VER_RES`: Specify the vertical resolution of the game.
- `DIRECT3D`: Set the Direct3D version. Use 0 for DirectX 8, 1 for DirectX 9, or 5 for Vulkan.

To apply the settings, run the `setup_params.bat` script. It reads the values from `USER_PARAMS.txt` and sets the corresponding registry parameters using the `utils.bat` script.

Make sure to provide valid values in the `USER_PARAMS.txt` file. If the file is missing or contains invalid entries, the script will display an error message.

Example `USER_PARAMS.txt` file:
```
WINDOWED=0
HOR_RES=1280
VER_RES=720
DIRECT3D=1
```

This configuration sets the game to run in fullscreen mode with a resolution of 1280x720 and uses DirectX 9.





