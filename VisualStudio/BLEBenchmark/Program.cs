using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Runtime.InteropServices.WindowsRuntime;
using System.Text;
using System.Threading.Tasks;
using BLEBenchmark;

/*
using ArduinoBluetoothAPI;
using Debug = UnityEngine.Debug;
*/

// this program was derived from microsoft's BluetoothLE sample project: https://docs.microsoft.com/de-de/samples/microsoft/windows-universal-samples/bluetoothle/
// microsoft's introductory to UWP BLE client: https://docs.microsoft.com/de-de/windows/uwp/devices-sensors/gatt-client

// extensive, comprehensible talk about BLE, detailing every aspect, from physcial layer up until application layer: https://www.ineltek.com/wp-content/uploads/2015/09/20160330-Low_Energy_Training.pdf

// empirical values for write with response achieve at min 2.5kB/s for phones https://stackoverflow.com/a/48983252

// Unity BLE plugin to work on all platforms: https://assetstore.unity.com/packages/tools/input-management/arduino-bluetooth-plugin-98960

class Program
{
    /*
    //Asynchronous method to receive messages
    static void OnMessageReceived()
    {
        Debug.Log(bluetoothHelper.ReadBytes().Length.ToString());
        // received_message = 
        // Debug.Log(received_message);
    }

    static void OnConnected()
    {
        try
        {
            bluetoothHelper.StartListening();
        }
        catch (Exception ex)
        {
            Debug.Log(ex.Message);
        }

    }

    static void OnConnectionFailed()
    {
        Debug.Log("Connection Failed");
    }
    */

    static BLE ble = new BLE();
    static Stopwatch stopwatch = new Stopwatch();
    static List<double> timings = new List<double> { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19 };
    static int packageCount = 0;

    static async void AsyncMain()
    {
        var success = false;
        while(!success)
        {
            Console.WriteLine("trying to connect with glove...");
            success = await ble.Connect(1000);
        }
        Console.WriteLine("connection established!");
        success = await ble.ScanServices();
        if (!success)
        {
            Console.WriteLine("scanning services failed!");
            return;
        }
        if (!await ble.StartListen(ValueUpdated))
        {
            Console.WriteLine("start listeneing on updatesfailed!");
            return;
        }
        // do perfomance tests
        var sendData = new byte[] { 0 };
        await Task.Delay(1000);
        await ble.WriteValue(sendData);

        var configurations = new byte[][] {
            new byte[] { 1, 6, 6, 45, 2, 1 },
            new byte[] { 1, 6, 6, 45, 4, 2 },
            new byte[] { 1, 6, 6, 45, 6, 3 },
            new byte[] { 1, 6, 6, 45, 2, 1 },
            new byte[] { 1, 6, 6, 20, 2, 1 },
            new byte[] { 1, 6, 6, 21, 2, 1 },
            new byte[] { 1, 6, 6, 22, 2, 1 },
            new byte[] { 1, 6, 6, 23, 2, 1 },
            new byte[] { 1, 6, 6, 24, 2, 1 },
            new byte[] { 1, 6, 6, 25, 2, 1 },
            new byte[] { 1, 0, 0, 20, 2, 1 },
            new byte[] { 1, 6, 6, 20, 2, 1 },
            new byte[] { 1, 12, 12, 20, 2, 1 },
            new byte[] { 1, 18, 18, 20, 2, 1 },
            new byte[] { 1, 6, 6, 45, 2, 1 },
            new byte[] { 1, 6, 6, 45, 5, 1 },
            new byte[] { 1, 6, 6, 200, 5, 1 },
            new byte[] { 1, 6, 6, 250, 5, 1 }
        };

        foreach (var configuration in configurations)
        {
            Console.Write("next test: ");
            Console.Write(string.Join(", ", configuration).PadRight(30));
            Console.Write(": ");
            await ble.WriteValue(configuration);
            packageCount = 0;
            timings.Clear();
            await Task.Delay(2000);
            var sorted = timings.ToList();
            sorted.Sort();
            var N = sorted.Count;
            Console.WriteLine(String.Format(
                "kbps {7,4:#0.0} N {0,4:#0} Quantiles [{1,4:#0.0} {2,4:#0.0} {3,4:#0.0} {4,4:#0.0} {5,4:#0.0}] avg {6,4:#0.0}",
                N,
                sorted[N * 0 / 4],
                sorted[N * 1 / 4],
                sorted[N * 2 / 4],
                sorted[N * 3 / 4],
                sorted[N * 4 / 4 - 1],
                sorted.Average(),
                N * configuration[3] / 2.0 / 1000
            ));
        }

        Console.WriteLine("reset params");
        sendData = new byte[] { 1, 6, 6, 45, 2, 1 };
        Console.WriteLine(string.Join(", ", sendData));
        await ble.WriteValue(sendData);
    }

    static void ValueUpdated(string name, string value)
    {
        var t = 1.0 * stopwatch.ElapsedTicks / Stopwatch.Frequency * 1000;
        timings.Add(t);
        stopwatch.Restart();

        // realtime measurements:
        //var sorted = timings.ToList();
        //sorted.Sort();
        //timings.RemoveAt(0);
        //// skip prints for more timing accuracy
        //if (packageCount % 20 == 0)
        //    Console.WriteLine(String.Format("min {0,4:#0.0} avg {1,4:#0.0} max {2,4:#0.0} med {3,4:#0.0} out {4}", timings.Min(), timings.Average(), timings.Max(), sorted[10], value.Substring(0, 6)));

        packageCount++;
    }

    static int Main(string[] args)
    {
        AsyncMain();
        Console.WriteLine("Press enter...");
        Console.ReadLine();
        //ble.Disconnect();
        Console.ReadLine();
        return 0;
    }
}

