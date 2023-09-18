import cv2
import numpy as np
import pyaudio
import threading
import tkinter as tk
from tkinter import ttk
import os
import datetime

cameraCapture = cv2.VideoCapture(0)
frame_width = int(cameraCapture.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cameraCapture.get(cv2.CAP_PROP_FRAME_HEIGHT))

audio_format = pyaudio.paInt16
audio_channels = 1
audio_rate = 44100
audio_chunk_size = 1024

p = pyaudio.PyAudio()

selected_camera_index = 0
selected_microphone_index = 0

audio_input_stream = None
audio_output_stream = None
audio_buffer = []

video_thread = None
audio_capture_thread = None
audio_playback_thread = None
is_running = True
is_fullscreen = False

app_title = "reCam"

def set_window_size():
    cv2.namedWindow(app_title, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(app_title, frame_width, frame_height)
    if is_fullscreen:
        cv2.setWindowProperty(app_title, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    else:
        cv2.setWindowProperty(app_title, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)

def open_video_window():
    global is_running, is_fullscreen
    cv2.namedWindow(app_title, cv2.WINDOW_NORMAL)
    set_window_size()

    while is_running:
        available, frame = cameraCapture.read()
        if available:
            cv2.imshow(app_title, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                is_running = False
                break
            elif key == ord('f'):
                is_fullscreen = not is_fullscreen
                if is_fullscreen:
                    cv2.setWindowProperty(app_title, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                else:
                    cv2.setWindowProperty(app_title, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
            elif key == ord('s'):
                capture_screenshot(frame, is_fullscreen)

def capture_screenshot(frame, is_fullscreen):
    script_directory = os.path.dirname(__file__)
    screenshot_folder = os.path.join(script_directory, "reCamScreenshots")
    
    try:
        if not os.path.exists(screenshot_folder):
            os.makedirs(screenshot_folder)
    except PermissionError as e:
        print(f"Permission error: {e}. Unable to create the screenshot folder.")
        return
    except Exception as e:
        print(f"Error: {e}. Unable to create the screenshot folder.")
        return
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    suffix = 1

    while True:
        unique_suffix = f"{timestamp}_{suffix}"
        screenshot_name = os.path.join(screenshot_folder, f"screenshot_{unique_suffix}.png")

        if not os.path.exists(screenshot_name):
            cv2.imwrite(screenshot_name, frame)
            
            break

        suffix += 1

def capture_audio():
    global audio_input_stream
    audio_input_stream = p.open(
        format=audio_format,
        channels=audio_channels,
        rate=audio_rate,
        input=True,
        input_device_index=selected_microphone_index,
        frames_per_buffer=audio_chunk_size
    )

    while is_running:
        audio_data = audio_input_stream.read(audio_chunk_size)
        audio_buffer.append(np.frombuffer(audio_data, dtype=np.int16))
        if len(audio_buffer) > 10:
            audio_buffer.pop(0)

def play_audio():
    global audio_output_stream
    audio_output_stream = p.open(
        format=audio_format,
        channels=audio_channels,
        rate=audio_rate,
        output=True
    )

    while is_running:
        if audio_buffer:
            audio_data = audio_buffer.pop(0).tobytes()
            audio_output_stream.write(audio_data)

def video_thread_function():
    open_video_window()

def audio_capture_thread_function():
    capture_audio()

def audio_playback_thread_function():
    play_audio()

def start_threads():
    global video_thread, audio_capture_thread, audio_playback_thread
    video_thread = threading.Thread(target=video_thread_function)
    audio_capture_thread = threading.Thread(target=audio_capture_thread_function)
    audio_playback_thread = threading.Thread(target=audio_playback_thread_function)

    video_thread.start()
    audio_capture_thread.start()
    audio_playback_thread.start()

root = tk.Tk()
root.title(f"{app_title} - Configuration")

camera_label = ttk.Label(root, text="Select Camera:")
microphone_label = ttk.Label(root, text="Select Microphone:")
camera_combobox = ttk.Combobox(root, values=[], state="readonly", width=40)
microphone_combobox = ttk.Combobox(root, values=[], state="readonly", width=40)

def set_selected_camera(event):
    global selected_camera_index, cameraCapture
    selected_camera_index = camera_combobox.current()
    cameraCapture.release()
    cameraCapture = cv2.VideoCapture(selected_camera_index)

def set_selected_microphone(event):
    global selected_microphone_index
    selected_microphone_index = microphone_combobox.current()

camera_combobox.bind("<<ComboboxSelected>>", set_selected_camera)
microphone_combobox.bind("<<ComboboxSelected>>", set_selected_microphone)

def populate_comboboxes():
    available_cameras = []
    available_microphones = []

    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available_cameras.append(f"{int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
            cap.release()

    for i in range(p.get_device_count()):
        device_info = p.get_device_info_by_index(i)
        if device_info['maxInputChannels'] > 0:
            available_microphones.append(device_info['name'])

    return available_cameras, available_microphones

camera_combobox_values, microphone_combobox_values = populate_comboboxes()
camera_combobox['values'] = camera_combobox_values
microphone_combobox['values'] = microphone_combobox_values

selected_camera_index = 0
selected_microphone_index = 0
camera_combobox.current(selected_camera_index)
microphone_combobox.current(selected_microphone_index)

camera_label.grid(row=0, column=0)
microphone_label.grid(row=1, column=0)
camera_combobox.grid(row=0, column=1)
microphone_combobox.grid(row=1, column=1)

def launch_video_window():
    global is_running
    is_running = True
    root.destroy()
    start_threads()
    open_video_window()

launch_button = ttk.Button(root, text="Launch", command=launch_video_window)
launch_button.grid(row=2, columnspan=2)

root.mainloop()