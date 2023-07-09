import pyaudio
import numpy as np
import threading
import os
import json
import win32gui
from pynput.keyboard import Controller, Listener, Key

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024

class AudioHandler:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    
    def read_audio(self):
        data = self.stream.read(CHUNK)
        numpydata = np.frombuffer(data, dtype=np.int16)
        volume = np.linalg.norm(numpydata) / CHUNK
        return volume

    def terminate(self):
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()

class UserInputHandler:
    def __init__(self, controller):
        self.controller = controller

    def terminate(self):
        pass

class KeyTapController:
    def __init__(self, settings_file='settings.json', default_threshold=300, default_key='c'):
        self.settings_file = settings_file
        self.key_tapped_lock = threading.Lock()
        self.key_tapped = False
        self.keyboard = Controller()
        self.settings_mode = False
        
        try:
            with open(self.settings_file, 'r') as file:
                settings = json.load(file)
                self.threshold = settings['threshold']
                self.key = settings['key']
        except (FileNotFoundError, ValueError, KeyError):
            self.threshold = default_threshold
            self.key = default_key
        
        self.reset_display()
        self.listener = self.create_listener()
        self.listener.start()

    def create_listener(self):
        def on_key_press(key):
            # Only handle key presses when the console window is active
            window_title = win32gui.GetWindowText(win32gui.GetForegroundWindow())
            if 'volume_etection' not in window_title.lower():
                return

            if str(key).replace("'", "") == self.key:
                with self.key_tapped_lock:
                    self.key_tapped = False
                    self.reset_display()
            elif key == Key.space:  # Space key will trigger settings mode
                self.settings_mode = True
                self.reset_display()
                self.update_settings()

        return Listener(on_press=on_key_press)

    def update_settings(self):
        if not self.settings_mode:
            return
        
        try:
            new_threshold = int(input('新しいキーを押す音量閾値を入力してください（例：300）：'))
            new_key = input('新しいキーを入力してください（例：c）：')
            with open(self.settings_file, 'w') as file:
                json.dump({'threshold': new_threshold, 'key': new_key}, file)
            self.threshold = new_threshold
            self.key = new_key
        except ValueError:
            print('入力が無効です。閾値は変更されません。')
        
        self.settings_mode = False
        self.key_tapped = False  # Reset key tapped status after updating settings
        self.reset_display()

    def reset_display(self):
        os.system('cls')  # Clear console
        print("========================================")
        print("=           音声キータッパー           =")
        print("========================================")
        print("\n現在の設定:")
        print(f'  - タップするキー: {self.key}')
        print(f'  - タップする音量閾値: {self.threshold}')
        print("\n========================================")
        print("現在の状態:")
        print('  - 入力状態: ', '設定モード' if self.settings_mode else ('ロック中' if self.key_tapped else '待機中'))
        print("\n========================================")
        print("指示:")
        print('  - 音量閾値とタップするキーを変更するには、スペースキーを押します。')

    def process_audio(self, volume):
        if self.settings_mode:
            return
        with self.key_tapped_lock:
            if volume > self.threshold and not self.key_tapped:
                self.listener.stop()
                self.keyboard.press(self.key)
                self.keyboard.release(self.key)
                self.key_tapped = True
                self.listener = self.create_listener()
                self.listener.start()
                self.reset_display()

    def terminate(self):
        self.listener.stop()

controller = KeyTapController()
audio_handler = AudioHandler()
input_handler = UserInputHandler(controller)

try:
    while True:
        volume = audio_handler.read_audio()
        controller.process_audio(volume)
except KeyboardInterrupt:
    pass

controller.terminate()
audio_handler.terminate()
input_handler.terminate()
