# Glove Circuit Board

This repository contains the Arduino code that runs on the glove (firmware) and some test programs.

## Flash Firmware

- install Arduino
- open project CynteractGlove/CynteractGlove.ino
- in preferences, add <https://dl.espressif.com/dl/package_esp32_index.json> as additional board manager url
- with Arduino's board manager, install board esp32 by Espressif Systems
- in Arduino's library manager, install following libraries:
  - ArduinoJson by Benoit Blanchon
  - Adafruit DRV2605 by Adafruit
- connect the glove via USB
- in tools select "Board: Esp32 Dev Module" and the COM port that appears after plugging the glove in
- click on upload

## Development

If you use Arduino on Windows, set the `%USERPROFILE%\AppData\Local\Arduino15` folder as exception on your antivirus program after Arduino installation to speed up compilation time by ~50% (see <https://arduino.stackexchange.com/a/34695>).

You can use the program in the folder Test01/ to debug your firmware during firmware-development.

Sometimes the serial connection fails and simply resetting the connection doesn't help. To recover, the device must be reset. Serial port reset via windows native com-api (see [SO question](https://stackoverflow.com/questions/1438371/win32-api-function-to-programmatically-enable-disable-device) and [blog post](https://dotnet-experience.blogspot.com/2012/05/resetting-local-ports-and-devices-from.html)) didn't work out for me as I got unauthorized exceptions.
Instead the usb-serial-hardware's sdk is used to reset it. It can be downloaded from <https://www.silabs.com/products/development-tools/software/interface#software>.

To use the UWP Api, you must add System.Runtime.WindowsRuntime and C:\Program Files (x86)\Windows Kits\10\UnionMetadata\10.0.17763.0\Windows.winmd as references to your project. For more details, see https://blogs.windows.com/windowsdeveloper/2017/01/25/calling-windows-10-apis-desktop-application/ . Though, this doesn't work with Unity until NET 5.

To enable Arduino-compaptible formatting in vscode, install the binary astyle and the chiehyu.vscode-astyle extension. Then set following setting in vscode (for linux):

```json
 "astyle.astylerc": "/usr/share/arduino/lib/formatter.conf"
```

## CynteractGlove files, sync with repo cynteract-games

GLove communication is debugged in this repo. The files should be synced over to cynteract-games. You can compare the differences before syncing with following commands:

```
diffall() {
	git diff --color-words --no-index Assets/Glove/Protocol.cs ../glove_platine/VisualStudio/Cynteract.Glove/Protocol.cs
	git diff --color-words --no-index Assets/Glove/GloveCommunication.cs ../glove_platine/VisualStudio/Cynteract.Glove/GloveCommunication.cs
	git diff --color-words --no-index Assets/Glove/Config.cs ../glove_platine/VisualStudio/Cynteract.Glove/Config.cs
	git diff --color-words --no-index Assets/Glove/USB.cs ../glove_platine/VisualStudio/Cynteract.Glove/USB.cs
	git diff --color-words --no-index Assets/Glove/BLE.cs ../glove_platine/VisualStudio/Cynteract.Glove/BLE.cs
}
diffall
```

## Bluetooth Low-Energy / C++ WinRT Development

The glove uses BLE. After some research there are four ways that how to integrate BLE in Unity (maybe there is another one?):

- A. Via a Unity asset. Ther is one that uses UWP API. It doesn't support .NET framework and thus would only be realistically be usable on Mac for development. Furthermore it provided a rather slow device scan which had to run to the end before returning any result. A big advantage would be the supported Android, Mac and Iphone target.
- B. Using UWP native. It doesn't run in the Unity Editor, it must be exported to use it. You would need one api for the editor and another one for the export. This way it is not debuggable. This may drastically improve with the merge of UWP and .NET framework in .NET version 5, somewhere midst 2021.
- C. Buy bluetoothframework C# edition, that would also work in the editor. But it's another dependency to maintain.
- D. Use a C++ WinRT dll. It is rather hard to develop it but it works in the Unity Editor.
- E. Use an external binary for Windows.

This repo uses option D, using UWP API with the help of a C++ WinRT dll. UWP provides BLE. But Unity's environment is .NET Framework only. The dll's source is in VisualStudio/BleWinrtDll. It holds that UWP = .NET Core ≠ .NET Framework, but that will be equalised with .NET 5. But for now, to use UWP code inside Unity's editor, it must be wrapped into a C++ winrt dll and imported into Unity as dll. Theoretically UWP code can be run from .NET Framework via a WindowsUnion reference. It works in VisualStudio but it won't work in Unity because Unity is doing some inhouse code transformations.

To create a new winrt dll, create a new c++ dll project in VisualStudio Add following line somewhere in the program:

```
  #pragma comment(lib, "windowsapp")
```

Under preferences, set C++ language level to C++17 and add the command line argument `await`. To reference a dll into Unity, select Release configuration in VisualStudio's menu bar, right-click the project and select "Build". After that, copy the created dll from Release/x64/\*.dll to Unity's Asset folder. While debugging you can use the Debug configuration.
