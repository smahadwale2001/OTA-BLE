import asyncio
import tkinter as tk
import tkinter.ttk as ttk

from bleak import BleakClient, BleakError, BleakScanner


scan_result = {}
is_connected = False


def build_gui():
    """Build a simple GUI."""
    # For the sake of simplicity, we use some global variables:
    global main_window, device_list, device_data, message_variable

    main_window = tk.Tk()
    main_window.title('Tkinter/bleak asyncio Demo')

    # Pressing the x-Icon on the Window calls stop_loop()
    main_window.protocol("WM_DELETE_WINDOW", stop_loop)

    message_variable = tk.StringVar()
    row_span_multiplier = 12
    # Left part of the GUI, Scan button and list of detected devices
    device_frame = ttk.Labelframe(main_window, text='Devices')
    device_frame.grid(padx=5, pady=5, rowspan=row_span_multiplier, sticky='ew')
    device_iframe = tk.Frame(device_frame)
    device_iframe.pack()
    scrollbar = ttk.Scrollbar(device_iframe)
    device_list = ttk.Treeview(
        device_iframe,
        height=20,
        yscrollcommand=scrollbar.set,
        show='tree',
    )
    device_list.pack(side='left', padx=5, pady=5)
    device_list.bind('<<TreeviewSelect>>', device_selection)
    scrollbar.configure(command=device_list.yview)
    scrollbar.pack(side='right', fill='y')
    scan_button = ttk.Button(
        main_window,
        text='Scan for BLE devices',
        command=lambda: asyncio.create_task(scan()),  # scan is asynchronous!
    )
    scan_button.grid(column=0, row=row_span_multiplier, rowspan=2*row_span_multiplier, padx=5, pady=5)

    # Right part of the GUI, Connect Button, data window and status messages
    data_frame = ttk.Labelframe(main_window, text='Device Data')
    data_frame.grid(padx=5, pady=5, row=0, rowspan=row_span_multiplier ,column=1, sticky='ns')
    device_data = tk.Text(data_frame, height=10, width=30)
    device_data.grid(padx=5, rowspan=row_span_multiplier, pady=5)

    message_frame = ttk.Labelframe(data_frame, text='Status')
    message_frame.grid(column=0, row=row_span_multiplier, rowspan=2*row_span_multiplier ,padx=5, pady=5, sticky='ew')
    message_label = ttk.Label(
        message_frame, textvariable=message_variable, width=38
    )
    message_label.grid(row=row_span_multiplier, rowspan=2*row_span_multiplier,padx=5, pady=5)
    connect_button = ttk.Button(
        main_window,
        text='Connect/Disconnect to/from device',
        command=lambda: asyncio.create_task(connect()),
    )
    connect_button.grid(column=1, row=row_span_multiplier, rowspan=2*row_span_multiplier, padx=5, pady=5)
    #cflabel = tk.Label(main_window, text="Configure")
    #cflabel.grid(column=2, row=0)
    #txtbx = tk.Entry(main_window, width=30)
    #txtbx.grid(column=3, row=0, padx=5, pady=5)
    # Don't do: main_window.mainloop()!
    # We are using the asyncio event loop in 'show' to call
    # main_window.update() regularly.


async def scan():
    """Scan for unconnected Bluetooth LE devices."""
    device_list.delete(*device_list.get_children())
    device_data.delete('0.0', tk.END)
    scan_result.clear()

    try:
        async with BleakScanner() as scanner:
            message_variable.set('Scanning (5 secs)...')
            await asyncio.sleep(5)
            message_variable.set('Scanning finished.')
            result = scanner.discovered_devices_and_advertisement_data
            if result:
                scan_result.update(result)
            for key in result:
                device, adv_data = result[key]
                if device.name:
                    name = device.name
                else:
                    name = 'No name'
                device_list.insert('', 'end', text=f'{name}, {device.address}')
    except (OSError, BleakError):
        message_variable.set('Bluetooth not available (off or absent)')


def device_selection(event):
    """Show advertised data of selected device."""
    for item in device_list.selection():
        name, key = device_list.item(item, 'text').split(',')
        device_data.delete('0.0', tk.END)
        device_data.insert('0.0', str(scan_result[key.strip()][1]))
        message_variable.set(f'Device address: {str(key)}')


async def connect():
    """Connect to or disconnect from selected/connected device."""
    global is_connected

    if is_connected:
        message_variable.set('Trying to disconnect...')
        disconnect.set()
        return
    # Pick the BLE device from the scan result:
    for item in device_list.selection():
        _, key = device_list.item(item, 'text').split(',')
        device = scan_result[key.strip()][0]
        name = device.name if device.name is not None else device.address

    try:
        message_variable.set(f'Trying to connect to {name}')
        async with BleakClient(device, disconnect_callback):
            message_variable.set(f'Device {name} is connected!')
            is_connected = True
            while not disconnect.is_set():
                await asyncio.sleep(0.1)
            is_connected = False
            return
    except (BleakError, asyncio.TimeoutError):
        message_variable.set(f'Connecting to {name}\nnot successful')
        is_connected = False


def disconnect_callback(client):
    """Handle disconnection.

    This callback is called when the device is disconnected.
    """
    message_variable.set(f'Device {client.address} has/was\ndisconnected')


async def show():
    """Handle the GUI's update method asynchronously.

    Most of the time the program is waiting here and
    updates the GUI regularly.
    This function principally replaces the Tkinter mainloop.
    """
    while not stop.is_set():
        main_window.update()
        await asyncio.sleep(0.1)


def stop_loop():
    """Set stop event."""
    stop.set()


async def main():
    """Start the GUI."""
    global stop, disconnect
    stop = asyncio.Event()
    disconnect = asyncio.Event()
    build_gui()
    await show()
    main_window.destroy()


asyncio.run(main())
