using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using ArduinoBluetoothAPI;
using UnityEngine;

using Windows.Devices.Bluetooth;
using Windows.Devices.Bluetooth.GenericAttributeProfile;
using Windows.Devices.Enumeration;
using Windows.Storage.Streams;


namespace Test01
{
    class Program
    {
        private static BluetoothHelper bluetoothHelper;

        static async void AsyncMainDefault()
        {
            try
            {
                string[] requestedProperties = { "System.Devices.Aep.DeviceAddress", "System.Devices.Aep.IsConnected", "System.Devices.Aep.Bluetooth.Le.IsConnectable" };
                DeviceWatcher deviceWatcher = DeviceInformation.CreateWatcher(
                    "(System.Devices.Aep.ProtocolId:=\"{bb7bb05e-5972-42b5-94fc-76eaa7084d49}\")", // list Bluetooth LE devices
                    requestedProperties,
                    DeviceInformationKind.AssociationEndpoint
                );
                deviceWatcher.Added += (DeviceWatcher sender, DeviceInformation deviceInfo) =>
                {
                    Debug.Log("DeviceWatcher Added " + deviceInfo.Name);
                    if (deviceInfo.Properties.ContainsKey("System.Devices.Aep.Bluetooth.Le.IsConnectable"))
                        Debug.Log("IsConnectable: " + deviceInfo.Properties.GetValueOrDefault("System.Devices.Aep.Bluetooth.Le.IsConnectable", null));
                };
                deviceWatcher.Updated += (DeviceWatcher sender, DeviceInformationUpdate deviceInfoUpdate) =>
                {
                    Debug.Log("DeviceWatcher Updated " + deviceInfoUpdate.ToString());
                    if (deviceInfoUpdate.Properties.ContainsKey("System.Devices.Aep.Bluetooth.Le.IsConnectable"))
                        Debug.Log("IsConnectable: " + deviceInfoUpdate.Properties.GetValueOrDefault("System.Devices.Aep.Bluetooth.Le.IsConnectable", null));
                };
                deviceWatcher.Start();
                await Task.Delay(2000);
            }
            catch (Exception ex)
            {
                Debug.Log(ex.ToString());
                Debug.Log(ex.Message);
            }
        }

        static async void AsyncMainPlugin()
        { 
            try
            {
                //AsyncMain();
                //Console.ReadLine();

                BluetoothHelper.BLE = true;  //use Bluetooth Low Energy Technology
                bluetoothHelper = BluetoothHelper.GetInstance("CynteractGlove");
                bluetoothHelper.OnConnected += () => 
                {
                    Debug.Log("connected");
                    // bluetoothHelper.StartListening();
                };
                bluetoothHelper.OnConnectionFailed += () =>
                {
                    Debug.Log("connection failed, start scan");
                    bluetoothHelper.ScanNearbyDevices();
                };
                bluetoothHelper.OnScanEnded += (LinkedList<ArduinoBluetoothAPI.BluetoothDevice> devices) =>
                {
                    Debug.Log("Found " + devices.Count);
                    foreach (var item in devices)
                    {
                        Debug.Log(item.DeviceName);
                    }
                    if (devices.Count == 0)
                        return;
                    try
                    {
                        bluetoothHelper.Connect();
                        Debug.Log("Connecting");
                    }
                    catch (Exception ex)
                    {
                        bluetoothHelper.ScanNearbyDevices();
                        Debug.Log(ex.Message);
                    }
                };
                bluetoothHelper.ScanNearbyDevices();
                Debug.Log("scan started");
                while (true)
                {
                    //if (bluetoothHelper.isDevicePaired() && !bluetoothHelper.isConnected())
                    //    bluetoothHelper.Connect();
                    ((MonoBehaviour)GameObject.component).Update();
                    await Task.Delay(100);
                }
            }
            catch (Exception ex){
                Debug.Log(ex.ToString());
                Debug.Log(ex.Message);
            }
        }

        static void Main(string[] args)
        {
            Console.WriteLine("Hello World!");
            //AsyncMainPlugin();
            AsyncMainDefault();
            Console.ReadLine();
        }
    }
}
