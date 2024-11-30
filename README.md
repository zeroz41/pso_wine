# pso_wine

-zeroz 

One-command installs for PSO on Linux and Android.
- PSO specific items in the `pso` folder
- Navigate to the `pc` folder for PC instructions
- Navigate to the `android` folder for Android instructions

The goal of this project is to fully and smoothly install Phantasy Star Online Blue Burst (PSOBB) on Linux systems with a single command, without user input, and using the system-installed Wine.

An additional goal of supporting Android was added later. Unlike desktop PCs, Android does not have the same simplicity for installation tools. Therefore, we utilize existing graphical tools that set up a container with configurable settings via GUI or Termux.

PSU not currently supported

## Architecture
To ensure compatibility across platforms, most of the installation and configuration happens within Wine itself, not relying on host system tools. This makes the project portable - the same core setup logic works whether you're on Linux, Android, or potentially other platforms.

The platform-specific code (like the Python script for Linux desktop) just serves as a wrapper to interact with this core Wine functionality. This approach allows:
- Consistent game setup across platforms
- Easy addition of new platform support
- Reliable Wine prefix configuration
- Minimal dependency on host system tools

## Platform Support
- **Linux Desktop**: Full support with automated installation
- **Android**: Supported. Relies on container setup. See pso android section
- **MacOS**: Basic support implemented, needs testing
- **Linux ARM**: Future?

## Current Support
Currently directly supports EphineaPSO

## Future Plans
- Add support for Phantasy Star Universe (PSU) and various addons/texture packs
- Allow easy configurations of separate client installs for other servers
- Linux ARM support
- Mac support/testing
- Offload PC dependency install and verification support into pure internal wine container approach, to allow portability and reusability

