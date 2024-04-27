# pso_wine

One-command installs for PSO on Linux and Android.

- PSO specific items in the `pso` folder.
- Navigate to the `pc` folder for PC instructions.
- Navigate to the `android` folder for Android instructions.

The goal of this project is to fully and smoothly install Phantasy Star Online Blue Burst (PSOBB) on Linux systems with a single command, without user input, and using the system-installed Wine.

An additional goal of supporting Android was added later. Unlike desktop PCs, Android does not have the same simplicity for installation tools. Therefore, we utilize existing graphical tools that set up a container with configurable settings via GUI or Termux.

To ensure compatibility with common Wine installs on both Linux (and possibly macOS) host machines and Android, the core functionality is built using a language that Wine can understand without relying on prebuilt binaries or the host system's library calls. However, in some cases, it may be more efficient (and save headaches) to statically precompile the code to run within Wine.

By having the core functionality run within Wine prefixes, the project becomes portable and allows simple wrappers (such as the Python script in the `pc` folder) to control the functions at a higher level and enable platform-specific setup.

During development, various configurations of dgVoodoo and DxWrapper were tested but ultimately deemed mostly unnecessary for the majority of use cases. However, for debugging purposes, DxWrapper allows extra logging output, as does manually piping the standard error and standard output from the running applications.

The project uses the native, built-in override for Wine's Direct3D 9 implementation. This approach allows the game to utilize the system's Direct3D 9 libraries while still leveraging the Ephinea client's custom extra directx libraries. For specific use cases or troubleshooting, using pure native Direct3D or a combination of dgVoodoo or DxWrapper with a custom d3d9 dll in the game's install folder can be considered.

Winegdb is also an okay tool for debugging but was avoided for the most part in this project.

---

Currently directly supports EphineaPSO

Future plans:
- Add support for Phantasy Star Universe (PSU) and various addons/texture packs.
- Allow easy configurations of separate client installs for other servers
- Mac support/testing
