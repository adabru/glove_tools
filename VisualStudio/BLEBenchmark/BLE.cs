using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices.WindowsRuntime;
using System.Threading;
using System.Threading.Tasks;
using Windows.Devices.Bluetooth;
using Windows.Devices.Bluetooth.GenericAttributeProfile;
using Windows.Devices.Enumeration;
using Windows.Storage.Streams;

namespace BLEBenchmark
{
    // copied from Bluetooth_Low_Energy_sample.zip
    class BLE
    {
        Guid SERVICE_UUID = Guid.Parse("4fafc201-1fb5-459e-8fcc-c5c9c331914b");
        Guid UUID_NOTIFY_1 = Guid.Parse("beb5483e-36e1-4688-b7f5-ea07361b26a8");
        Guid UUID_NOTIFY_2 = Guid.Parse("beb5483e-36e1-4688-b7f5-ea07361b26a9");
        Guid UUID_NOTIFY_3 = Guid.Parse("beb5483e-36e1-4688-b7f5-ea07361b26ab");
        Guid UUID_WRITE = Guid.Parse("beb5483e-36e1-4688-b7f5-ea07361b26aa");

        private readonly SemaphoreSlim discoveryLock = new SemaphoreSlim(0, 1);
        private DeviceWatcher deviceWatcher;
        private Dictionary<string, DeviceInformation> devices = new Dictionary<string, DeviceInformation>();
        private Dictionary<Guid, Dictionary<Guid, GattCharacteristic>> serviceChars = new Dictionary<Guid, Dictionary<Guid, GattCharacteristic>>();
        private Dictionary<ushort, string> charNames = new Dictionary<ushort, string>();

        private Dictionary<ushort, Action<string, string>> changeListener = new Dictionary<ushort, Action<string, string>>();
        
        public async Task<bool> Connect(int timeout = -1)
        {
            //Connected bluetooth devices
            //DeviceInformationCollection ConnectedBluetoothDevices =
            //       await DeviceInformation.FindAllAsync(BluetoothDevice.GetDeviceSelectorFromConnectionStatus(BluetoothConnectionStatus.Connected));

            if (deviceWatcher == null)
            {
                string[] requestedProperties = { "System.Devices.Aep.DeviceAddress", "System.Devices.Aep.IsConnected", "System.Devices.Aep.Bluetooth.Le.IsConnectable" };
                deviceWatcher = DeviceInformation.CreateWatcher(
                    "(System.Devices.Aep.ProtocolId:=\"{bb7bb05e-5972-42b5-94fc-76eaa7084d49}\")", // list Bluetooth LE devices
                    requestedProperties,
                    DeviceInformationKind.AssociationEndpoint
                );
                deviceWatcher.Added += DeviceWatcher_Added;
                deviceWatcher.Updated += DeviceWatcher_Updated;
                deviceWatcher.EnumerationCompleted += DeviceWatcher_EnumerationCompleted;

                // ~30 seconds scan ; for permanent scanning use BluetoothLEAdvertisementWatcher, see the BluetoothAdvertisement.zip sample
                deviceWatcher.Start();
                await discoveryLock.WaitAsync(timeout);
            }
            else
            {
                await discoveryLock.WaitAsync(timeout);
            }
            //deviceWatcher.Status == DeviceWatcherStatus.
            return devices.Count > 0;
        }
        private async void DeviceUpdated(DeviceInformation device)
        {
            if (device.Name == "Glove5")
            {
                Console.WriteLine("Glove5 found!");
                bool isConnected = (bool?)device.Properties["System.Devices.Aep.IsConnected"] == true;
                if (isConnected)
                    Console.WriteLine("Is already connected");
                bool isConnectable = (bool?)device.Properties["System.Devices.Aep.Bluetooth.Le.IsConnectable"] == true;
                if (!isConnectable)
                {
                    Console.WriteLine("Is not connectable");
                    return;
                }
                discoveryLock.Release();
            }

        }
        private async void DeviceWatcher_Added(DeviceWatcher sender, DeviceInformation deviceInfo)
        {
            devices[deviceInfo.Id] = deviceInfo;
            DeviceUpdated(deviceInfo);
        }
        private async void DeviceWatcher_Updated(DeviceWatcher sender, DeviceInformationUpdate deviceInfoUpdate)
        {
            DeviceInformation device;
            if (devices.TryGetValue(deviceInfoUpdate.Id, out device))
            {
                device.Update(deviceInfoUpdate);
                DeviceUpdated(device);
            }
        }
        private async void DeviceWatcher_EnumerationCompleted(DeviceWatcher sender, object e)
        {
            StopBleDeviceWatcher();
            discoveryLock.Release();
        }
        private void StopBleDeviceWatcher()
        {
            if (deviceWatcher != null)
            {
                deviceWatcher.Added -= DeviceWatcher_Added;
                deviceWatcher.Updated -= DeviceWatcher_Updated;
                deviceWatcher.EnumerationCompleted -= DeviceWatcher_EnumerationCompleted;
                deviceWatcher.Stop();
                deviceWatcher = null;
            }
        }

        public async Task<bool> ScanServices()
        {
            if (devices.Count < 1)
            {
                Console.WriteLine("before scanning services a device must first be found via advertising");
                return false;
            }

            StopBleDeviceWatcher();
           
            try
            {
                BluetoothLEDevice bluetoothLeDevice = null;
                bluetoothLeDevice = await BluetoothLEDevice.FromIdAsync(devices.First().Value.Id);
                if (bluetoothLeDevice == null)
                {
                    Console.WriteLine("Failed to connect to device.");
                    return false;
                }

                Console.WriteLine("retrieve services");
                GattDeviceServicesResult serviceScan = await bluetoothLeDevice.GetGattServicesAsync(BluetoothCacheMode.Uncached);
                if (serviceScan.Status != GattCommunicationStatus.Success)// || serviceScan.Services.Count == 0)
                {
                    Console.WriteLine("no services found");
                    return false;
                }
                Console.WriteLine(String.Format("succesfully retrieved {0} services", serviceScan.Services.Count));
                foreach (var service in serviceScan.Services)
                {
                    serviceChars[service.Uuid] = new Dictionary<Guid, GattCharacteristic>();
                    /*
                    var accessStatus = await service.RequestAccessAsync();
                    if (accessStatus != DeviceAccessStatus.Allowed)
                    {
                        Console.WriteLine("Error accessing service {0}", service.Uuid);
                        continue;
                    }
                    */
                    GattCharacteristicsResult charScan = await service.GetCharacteristicsAsync(BluetoothCacheMode.Uncached/*Cached*/);
                    if (charScan.Status != GattCommunicationStatus.Success)
                    {
                        Console.WriteLine("Error scanning characteristics from service {0}", service.Uuid);
                        continue;
                    }
                    foreach (GattCharacteristic c in charScan.Characteristics)
                    {
                        Console.WriteLine("Custom Characteristic: " + c.Uuid);
                        serviceChars[service.Uuid][c.Uuid] = c;
                        // retrieve user description
                        //var descriptorScan = await c.GetDescriptorsAsync(BluetoothCacheMode.Uncached);
                        var descriptorScan = await c.GetDescriptorsForUuidAsync(Guid.Parse(string.Format("0000{0}-0000-1000-8000-00805F9B34FB", "2901")), BluetoothCacheMode.Uncached);
                        if (descriptorScan.Descriptors.Count > 0) {
                            GattDescriptor descriptor = descriptorScan.Descriptors.First();
                            var nameResult = await descriptor.ReadValueAsync();
                            if (nameResult.Status != GattCommunicationStatus.Success)
                            {
                                Console.WriteLine("couldn't read user description for charasteristic {0}", c.Uuid);
                                continue;
                            }
                            var dataReader = DataReader.FromBuffer(nameResult.Value);
                            var output = dataReader.ReadString(dataReader.UnconsumedBufferLength);
                            charNames[c.AttributeHandle] = output;
                            Console.WriteLine(output);
                        }
                    }
                }
            }
            catch (Exception e)
            {
                Console.WriteLine(e);
                return false;
            }

            if (!serviceChars.ContainsKey(SERVICE_UUID))
            {
                Console.WriteLine("custom service was not scanned!");
                return false;
            }
            if (serviceChars[SERVICE_UUID].Count < 2)
            {
                Console.WriteLine("custom service returned less than 3 characteristics!");
                return false;
            }

            return true;
        }

        public async Task<bool> StartListen(Action<string, string> handler)
        {
            foreach (var guid in new Guid[] { UUID_NOTIFY_1, UUID_NOTIFY_2, UUID_NOTIFY_3 })
            {
                var c = serviceChars[SERVICE_UUID][guid];
                var status = await c.WriteClientCharacteristicConfigurationDescriptorAsync(GattClientCharacteristicConfigurationDescriptorValue.Notify);
                if (status != GattCommunicationStatus.Success)
                {
                    Console.WriteLine("Error on subscribing");
                    return false;
                }
                changeListener[c.AttributeHandle] = handler;
                c.ValueChanged += Characteristic_ValueChanged;
            }
            return true;
        }
        public async Task StopListen()
        {
            await serviceChars[SERVICE_UUID][UUID_NOTIFY_1].WriteClientCharacteristicConfigurationDescriptorAsync(GattClientCharacteristicConfigurationDescriptorValue.None);
        }
        public async Task<bool> WriteValue(byte[] value)
        {
            return await WriteBufferToSelectedCharacteristicAsync(
                WindowsRuntimeBufferExtensions.AsBuffer(value),
                serviceChars[SERVICE_UUID][UUID_WRITE]
            );
        }

        private async void Characteristic_ValueChanged(GattCharacteristic c, GattValueChangedEventArgs args)
        {
            if (!changeListener.ContainsKey(c.AttributeHandle))
            {
                Console.WriteLine("value changed notification received but no handler is registered!");
                return;
            }
            var buf = args.CharacteristicValue;
            var dataReader = DataReader.FromBuffer(buf);
            var output = dataReader.ReadString(20);
            changeListener[c.AttributeHandle](charNames[c.AttributeHandle], output);
        }
        private async Task<bool> WriteBufferToSelectedCharacteristicAsync(IBuffer buffer, GattCharacteristic c)
        {
            try
            {
                // BT_Code: Writes the value from the buffer to the characteristic.
                var result = await c.WriteValueWithResultAsync(buffer);

                if (result.Status != GattCommunicationStatus.Success)
                {
                    Console.WriteLine("characteristic write failed!");
                    return false;
                }
            }
            catch (Exception ex) when (ex.HResult == E_BLUETOOTH_ATT_INVALID_PDU)
            {
                Console.WriteLine("characteristic write failed!: E_BLUETOOTH_ATT_INVALID_PDU ", ex);
                return false;
            }
            catch (Exception ex) when (ex.HResult == E_BLUETOOTH_ATT_WRITE_NOT_PERMITTED || ex.HResult == E_ACCESSDENIED)
            {
                // This usually happens when a device reports that it support writing, but it actually doesn't.
                Console.WriteLine("characteristic write failed!: ", ex);
                return false;
            }
            return true;
        }
        public async void Disconnect()
        {
            await StopListen();
            serviceChars[SERVICE_UUID][UUID_NOTIFY_1].Service.Dispose();
        }

        readonly int E_BLUETOOTH_ATT_WRITE_NOT_PERMITTED = unchecked((int)0x80650003);
        readonly int E_BLUETOOTH_ATT_INVALID_PDU = unchecked((int)0x80650004);
        readonly int E_ACCESSDENIED = unchecked((int)0x80070005);
        readonly int E_DEVICE_NOT_AVAILABLE = unchecked((int)0x800710df); // HRESULT_FROM_WIN32(ERROR_DEVICE_NOT_AVAILABLE)        
    }
}
