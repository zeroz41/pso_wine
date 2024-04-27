# Winlator Settings

- Release Version: 6.1

The following screenshots show the recommended settings for Winlator. Not absolutely all of them are required to be set this way.

![Screenshot_20240426-223018](https://github.com/zeroz41/pso_wine/assets/166859298/ce606a47-e6da-425f-92a7-ecc5e6f0a76a)

![Screenshot_20240426-223030](https://github.com/zeroz41/pso_wine/assets/166859298/2f0988e9-29c6-4966-813d-258b6194bcd9)

![Screenshot_20240426-223037](https://github.com/zeroz41/pso_wine/assets/166859298/3cd36cff-68ea-427b-8e83-daaded9f488a)

![Screenshot_20240426-223044](https://github.com/zeroz41/pso_wine/assets/166859298/1553a069-7745-4905-8519-7b6f13c222cd)


![Screenshot_20240426-223053](https://github.com/zeroz41/pso_wine/assets/166859298/14b9030c-c886-4c67-a103-6e8dc2e64279)


![Screenshot_20240426-223105](https://github.com/zeroz41/pso_wine/assets/166859298/08a535e5-2adb-4ddd-ba3e-20a4a6118f5b)
![Screenshot_20240426-223112](https://github.com/zeroz41/pso_wine/assets/166859298/e1ccd711-6662-430e-af8f-dceda8e33635)

![Screenshot_20240426-223130](https://github.com/zeroz41/pso_wine/assets/166859298/a272647a-d002-429e-ad89-3d4327bed39c)
![Screenshot_20240426-223146](https://github.com/zeroz41/pso_wine/assets/166859298/e39ac63a-d372-4bbc-acf2-dcabf7e63c38)

The default Wine version installed with Winlator is used. Other Wine versions may work but might not have the same built-in ease of use with game controllers.

Note: After creating your container, go back to the Winlator settings page and reset the box86 and box64 versions to the ones shown in the screenshots. There seems to be a bug where the versions get reset upon initializing a new prefix.

## Tips
- Swipe from the left to open the menu with keyboard and touch controls.
- Switch to RTS on-screen mode temporarily to access the Enter key, which is useful for entering passwords.

## Miscellaneous Notes
- Experiment with Turnip driver and/or DXVK if you have an Adreno device.
- Experiment with processor affinity settings if you know what you're doing. The optimal settings depend on your device's core setup.
- You can allocate more than 4096 MB of video memory if desired.
