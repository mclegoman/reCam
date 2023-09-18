# Name: reCam
# Author: MCLegoMan
# GitHub: https://github.com/MCLegoMan/reCam
# License: CC0-1.0

import cv2
import numpy as np
import pyaudio
import threading
import tkinter as tk
from tkinter import ttk
import os
import datetime

class ReCam:
    def __init__(self):
        self.appTitle = "reCam"
        self.isRunning = False
        self.isFullscreen = False
        self.selectedCameraIndex = 0
        self.selectedMicrophoneIndex = 0
        self.audioBuffer = []

        self.frameWidth = 1280
        self.frameHeight = 720

        self.cameraCapture = cv2.VideoCapture(self.selectedCameraIndex)
        self.cameraCapture.set(cv2.CAP_PROP_FRAME_WIDTH, self.frameWidth)
        self.cameraCapture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frameHeight)

        self.audioFormat = pyaudio.paInt16
        self.audioChannels = 1
        self.audioRate = 44100
        self.audioChunkSize = 1024

        self.p = pyaudio.PyAudio()

        self.audioInputStream = None
        self.audioOutputStream = None

        self.videoThread = None
        self.audioCaptureThread = None
        self.audioPlaybackThread = None

        self.initGui()

    def initGui(self):
        self.root = tk.Tk()
        self.root.title(f"{self.appTitle} - Configuration")

        self.cameraLabel = ttk.Label(self.root, text="Select Camera:")
        self.microphoneLabel = ttk.Label(self.root, text="Select Microphone:")
        self.cameraCombobox = ttk.Combobox(self.root, values=[], state="readonly", width=40)
        self.microphoneCombobox = ttk.Combobox(self.root, values=[], state="readonly", width=40)

        self.cameraCombobox.bind("<<ComboboxSelected>>", self.setSelectedCamera)
        self.microphoneCombobox.bind("<<ComboboxSelected>>", self.setSelectedMicrophone)

        self.populateComboboxes()

        self.cameraCombobox.current(self.selectedCameraIndex)
        self.microphoneCombobox.current(self.selectedMicrophoneIndex)

        self.cameraLabel.grid(row=0, column=0)
        self.microphoneLabel.grid(row=1, column=0)
        self.cameraCombobox.grid(row=0, column=1)
        self.microphoneCombobox.grid(row=1, column=1)

        self.launchButton = ttk.Button(self.root, text="Launch", command=self.launchVideoWindow)
        self.launchButton.grid(row=2, columnspan=2)

    def populateComboboxes(self):
        availableCameras = []
        availableMicrophones = []

        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                availableCameras.append(f"{int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
                cap.release()

        for i in range(self.p.get_device_count()):
            deviceInfo = self.p.get_device_info_by_index(i)
            if deviceInfo['maxInputChannels'] > 0:
                availableMicrophones.append(deviceInfo['name'])

        self.cameraCombobox['values'] = availableCameras
        self.microphoneCombobox['values'] = availableMicrophones

    def setSelectedCamera(self, event):
        self.selectedCameraIndex = self.cameraCombobox.current()
        self.cameraCapture.release()
        self.cameraCapture = cv2.VideoCapture(self.selectedCameraIndex)
        self.cameraCapture.set(cv2.CAP_PROP_FRAME_WIDTH, self.frameWidth)
        self.cameraCapture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frameHeight)

    def setSelectedMicrophone(self, event):
        self.selectedMicrophoneIndex = self.microphoneCombobox.current()

    def setWindowSize(self):
        cv2.namedWindow(f"{self.appTitle} - Video Output", cv2.WINDOW_NORMAL)
        cv2.resizeWindow(f"{self.appTitle} - Video Output", self.frameWidth, self.frameHeight)
        if self.isFullscreen:
            cv2.setWindowProperty(f"{self.appTitle} - Video Output", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        else:
            cv2.setWindowProperty(f"{self.appTitle} - Video Output", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)

    def openVideoWindow(self):
        cv2.namedWindow(f"{self.appTitle} - Video Output", cv2.WINDOW_NORMAL)
        self.setWindowSize()

        while self.isRunning:
            available, frame = self.cameraCapture.read()
            if available:
                cv2.imshow(f"{self.appTitle} - Video Output", frame)

                key = cv2.waitKey(1) & 0xFF
                if key == 27:
                    self.isRunning = False
                    break
                elif key == ord('f'):
                    self.isFullscreen = not self.isFullscreen
                    if self.isFullscreen:
                        cv2.setWindowProperty(f"{self.appTitle} - Video Output", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                    else:
                        cv2.setWindowProperty(f"{self.appTitle} - Video Output", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
                elif key == ord('s'):
                    self.captureScreenshot(frame, self.isFullscreen)

    def captureScreenshot(self, frame, isFullscreen):
        scriptDirectory = os.path.dirname(__file__)
        screenshotFolder = os.path.join(scriptDirectory, "reCamScreenshots")

        try:
            if not os.path.exists(screenshotFolder):
                os.makedirs(screenshotFolder)
        except PermissionError as e:
            print(f"Permission error: {e}. Unable to create the screenshot folder.")
            return
        except Exception as e:
            print(f"Error: {e}. Unable to create the screenshot folder.")
            return

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        suffix = 1

        while True:
            uniqueSuffix = f"{timestamp}_{suffix}"
            screenshotName = os.path.join(screenshotFolder, f"screenshot_{uniqueSuffix}.png")

            if not os.path.exists(screenshotName):
                cv2.imwrite(screenshotName, frame)

                break

            suffix += 1

    def captureAudio(self):
        self.audioInputStream = self.p.open(
            format=self.audioFormat,
            channels=self.audioChannels,
            rate=self.audioRate,
            input=True,
            input_device_index=self.selectedMicrophoneIndex,
            frames_per_buffer=self.audioChunkSize
        )

        while self.isRunning:
            audioData = self.audioInputStream.read(self.audioChunkSize)
            self.audioBuffer.append(np.frombuffer(audioData, dtype=np.int16))
            if len(self.audioBuffer) > 10:
                self.audioBuffer.pop(0)

    def playAudio(self):
        self.audioOutputStream = self.p.open(
            format=self.audioFormat,
            channels=self.audioChannels,
            rate=self.audioRate,
            output=True
        )

        while self.isRunning:
            if self.audioBuffer:
                audioData = self.audioBuffer.pop(0).tobytes()
                self.audioOutputStream.write(audioData)

    def videoThreadFunction(self):
        self.openVideoWindow()

    def audioCaptureThreadFunction(self):
        self.captureAudio()

    def audioPlaybackThreadFunction(self):
        self.playAudio()

    def startThreads(self):
        self.videoThread = threading.Thread(target=self.videoThreadFunction)
        self.audioCaptureThread = threading.Thread(target=self.audioCaptureThreadFunction)
        self.audioPlaybackThread = threading.Thread(target=self.audioPlaybackThreadFunction)

        self.videoThread.start()
        self.audioCaptureThread.start()
        self.audioPlaybackThread.start()

    def launchVideoWindow(self):
        self.isRunning = True
        self.root.destroy()
        self.startThreads()
        self.openVideoWindow()

if __name__ == "__main__":
    app = ReCam()
    app.root.mainloop()
