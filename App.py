import asyncio
import tkinter as tk
import tkinter.ttk as ttk
import cv2
from bleak import BleakClient, BleakError, BleakScanner
import numpy as np
from PIL import Image,ImageTk
from tkinter.filedialog import askopenfilename
import time

scan_result = {}
is_connected = False

fileDataChar = '70b41ba1-a3cd-4112-9db0-6f73fedcc74d'
fileModeChar = '70b41ba2-a3cd-4112-9db0-6f73fedcc74d'

def build_gui():
    """Build a simple GUI."""
    # For the sake of simplicity, we use some global variables:
    global main_window, device_list, device_data, message_variable, filename, filenameEntry, activeButton

    activeButton = False
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
        height=15,
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
    configure_button = ttk.Button(main_window, text='Configure OTA Packet', command=lambda: configure_window())
    configure_button.grid(column=2, row=0, padx=5, pady=5)

    filenameEntry = tk.Entry(main_window)
    filenameEntry.grid(column=2,row=1,padx=5,pady=5)

    filenameButton = ttk.Button(main_window, text='Load File', command=lambda: getFileName())
    filenameButton.grid(column=3,row=1,padx=5,pady=5)

    sendButton = ttk.Button(main_window, text='Send File', command=lambda: asyncio.create_task(sendBundle()))
    sendButton.grid(column=2,row=2,padx=5,pady=5)
    #cflabel = tk.Label(main_window, text="Configure")
    #cflabel.grid(column=2, row=0)
    #txtbx = tk.Entry(main_window, width=30)
    #txtbx.grid(column=3, row=0, padx=5, pady=5)
    # Don't do: main_window.mainloop()!
    # We are using the asyncio event loop in 'show' to call
    # main_window.update() regularly.

async def sendBundle():
    global filename, nextFile, activeButton
    await BLEclient.start_notify(fileModeChar,mode_notify)
    nextFile = False
    doneFlag = False
    while not doneFlag:
        nextFile = False
        doBleFtp(filename)
        while not nextFile:
            pass
    activeButton = False

async def doBleFtp():
    global fileDataChar, fileModeChar, fileDataList, filename, BLEclient, cIndex, statusVal, activeButton
    if activeButton:
        return
    activeButton = True
    await BLEclient.write_gatt_char(fileModeChar, b'OTA_Start', response=True)
    with open(filename, mode='rb') as file:
        fileContent = file.read()
    n=248
    fileDataList=[fileContent[i:i+n] for i in range(0, len(fileContent), n)]
    maxIndex = len(fileDataList)
    cIndex = 0
    retryIndex = 0
    prevTime = time.time()
    time.sleep(1)
    statusVal = 0
    breakFlag = 0
    totalData = []
    delay_tm = 0.05
    while cIndex < maxIndex:
        totalData.append(getFileDataIncremental(cIndex))
        cIndex+=1
    cIndex = 0
    #print(totalData)
    for i in totalData:
        retryIndex = 0
        statusVal = 0
        #print(i)
        while(time.time() - prevTime < delay_tm):
            pass
        cIndex += 1
        if cIndex % 20 == 0:
            delay_tm = 0.1
        elif cIndex % 100 == 0:
            delay_tm = 0.5
        else:
            delay_tm = 0.01
        try:
            await BLEclient.write_gatt_char(fileDataChar, i, response=True)
        except:
            prevTime = time.time()
            while(time.time() - prevTime < 2):
                pass
            await BLEclient.write_gatt_char(fileDataChar, i, response=True)
        prevTime = time.time()
        #print('Prev Time',prevTime)
        print(cIndex)
        cIndex+=1
        continue
        while(statusVal != 1):
            if(time.time()-prevTime >0.4):
                #print(time.time() - prevTime,time.time())
                print('Retry Val',retryIndex)
                await BLEclient.write_gatt_char(fileDataChar, i, response=True)
                retryIndex+=1
                prevTime = time.time()
                #print(time.time()-prevTime)
            if retryIndex == 15:
                breakFlag = 1
                break
        if breakFlag:
            print('Failed')
            break
    if breakFlag == 0:
        await BLEclient.write_gatt_char(fileDataChar, b'\xff\xff\x00', response=True)


async def ftp_notify(sender, data):
    global statusVal
    statusVal = int(data[0])
    #print('Got Notification',statusVal)

async def mode_notify(sender, data):
    global filename, nextFile, doneFlag, filesFolderPath
    filename = filesFolderPath+str(data)
    nextFile = True
    print('Starting OTA for ',filename)

def getFileDataIncremental(packetIndex):
    global fileDataList
    Plength = len(fileDataList[packetIndex])
    Plength = Plength.to_bytes(1,'big')
    Pindex = packetIndex.to_bytes(2,'big')
    return Pindex+Plength+fileDataList[packetIndex]


def getFileName():
    global filename, filenameEntry, filesFolderPath
    filename = askopenfilename()
    filesFolderPath = filename[:len(filename)-filename[::-1].index('/')]
    print(filesFolderPath)
    filenameEntry.insert(0,filename)

def configure_window():
    global packetValues, configureWindow, configureCombox, byteSize
    packetValues = ['Packet Length','Packet Number','File Size','CRC','Data']
    configureWindow = tk.Toplevel(main_window)
    configureWindow.title("Packet Configuration")
    #configureWindow.geometry("200x200")
    configureCombox = ttk.Combobox(configureWindow,values=packetValues)
    configureCombox.grid(column=0,row=0,pady=5,padx=5)
    byteSize = tk.Entry(configureWindow, width=10)
    byteSize.grid(column=1,row=0,pady=5,padx=5)
    configAddButton = ttk.Button(configureWindow, text='Add Option',command=lambda: reArrangePacket())
    configAddButton.grid(column=2,row=0,pady=5,padx=5)
    saveButton = ttk.Button(configureWindow, text='Save Configuration',command=lambda: saveConfiguration())
    saveButton.grid(column=3,row=0,pady=5,padx=5)

def reArrangePacket():
    global PacketByteSize, packetDefination, selIndex, totalSize, configureCombox, img, prevOrg
    RED = (0, 0, 255)
    GREEN = (0, 255, 0)
    BLUE = (255, 0, 0)
    YELLOW = (0, 255, 255)
    CYAN = (255, 255, 0)
    MAGENTA = (255, 0, 255)
    color = [RED,GREEN,BLUE,YELLOW,MAGENTA]
    if len(packetValues)==5:
        PacketByteSize = 0
        packetDefination = {}
        selIndex = 0
        totalSize = 0
        prevOrg = 50
        img = np.ones(dtype=np.uint8,shape=(150,350,3)) * 255
    selType = configureCombox.get()
    selByteSize = int(byteSize.get())
    totalSize+=selByteSize
    packetDefination[selType] = [selByteSize,selIndex]
    packetValues.remove(selType)
    configureCombox = ttk.Combobox(configureWindow,values=packetValues)
    configureCombox.grid(column=0,row=0,pady=5,padx=5)
    img = cv2.rectangle(img, (prevOrg,10), (prevOrg+int(selByteSize),40), color[selIndex], -1)
    prevOrg+=int(selByteSize)+1
    img = cv2.putText(img, selType+' : '+str(selByteSize), (50,60+selIndex*16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color[selIndex], 1, cv2.LINE_AA)
    selIndex+=1
    imageGP = ImageTk.PhotoImage(image=Image.fromarray(img))
    consumeGraph = tk.Label(configureWindow)
    consumeGraph.photo_image = imageGP
    consumeGraph.configure(image=imageGP)
    consumeGraph.grid(column=0,row=1,columnspan=4,padx=5,pady=5)
    #print(packetDefination)

def saveConfiguration():
    pass

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
    global is_connected, BLEclient

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
        BLEclient = BleakClient(device, disconnect_callback)
        async with BLEclient:
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
