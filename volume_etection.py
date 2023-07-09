import tkinter as tk
from tkinter import ttk
import pyaudio
import numpy as np
import threading
import os
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from pynput.keyboard import Controller, Listener, Key
import time

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Sampling rate
CHUNK = 4000  # Chunk size
THRESHOLD = 1000  # Volume threshold
volumes = []  # List to store volume
times = []  # List to store time
start_time = time.time()  # Start time

class Application(tk.Tk):
    def __init__(self):
        super().__init__()

        # Set the font size for widgets
        default_font = tk.font.nametofont("TkDefaultFont")
        default_font.configure(size=18)
        self.option_add("*Font", default_font)

        self.title("音量検知")
        self.controller = KeyTapController()
        self.audio_handler = AudioHandler()
        self.create_widgets()
        self.update_graph()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.controller.terminate()
        self.audio_handler.terminate()
        self.destroy()
        os._exit(0) # 強制的に全てのプロセスを終了させる FIXME: ちゃんと全部のスレッドを見て、適切な終了処理をすべきではあるが、大した事するアプリではないので現状これでいいか

    def create_widgets(self):
        self.threshold_label = ttk.Label(self, text="音量閾値：")
        self.threshold_label.grid(column=0, row=0, sticky="W")
        self.threshold_entry = ttk.Entry(self)
        self.threshold_entry.grid(column=1, row=0, sticky="EW")
        self.threshold_entry.insert(0, str(self.controller.threshold))

        self.key_label = ttk.Label(self, text="入力キー：")
        self.key_label.grid(column=0, row=1, sticky="W")
        self.key_entry = ttk.Entry(self)
        self.key_entry.grid(column=1, row=1, sticky="EW")
        self.key_entry.insert(0, self.controller.key)

        self.update_button = ttk.Button(self, text="更新", command=self.controller.update_settings)
        self.update_button.grid(column=2, row=0, rowspan=2)

        self.lock_status_label = ttk.Label(self, text="")
        self.lock_status_label.grid(column=0, row=3, columnspan=3, sticky="W")

        self.fig, self.ax = plt.subplots()
        self.ax.set_xlim(0, 5)
        self.ax.set_ylim(0, 2 * THRESHOLD)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Volume")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().grid(column=0, row=4, columnspan=3)
        self.canvas.draw()

    def update_graph(self):
        volume = self.audio_handler.read_audio()
        self.controller.process_audio(volume)
        volumes.append(volume)
        times.append(time.time() - start_time)
        self.ax.cla()
        current_time = times[-1]
        self.ax.set_xlim(max(0, current_time - 5), max(5, current_time))
        self.ax.set_ylim(0, 2 * self.controller.threshold)
        self.ax.plot(times, volumes)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Volume")
        self.canvas.draw()
        self.lock_status_label["text"] = "入力状態：" + ("停止中" if self.controller.key_tapped else "受付中")
        if len(times) > 1 and times[0] < current_time - 5:
            times.pop(0)
            volumes.pop(0)
        self.after(100, self.update_graph)

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

        self.start_listener()

    def start_listener(self):
        def on_press(key):
            if key == Key.f1:
                self.settings_mode = not self.settings_mode
            elif not self.settings_mode and hasattr(key, 'char') and key.char == self.key:
                self.key_tapped = False

        self.listener = Listener(on_press=on_press)
        self.listener.start()

    def update_settings(self):
        try:
            threshold = int(app.threshold_entry.get())
            key = app.key_entry.get()
            if len(key) != 1:
                raise ValueError
            self.threshold = threshold
            self.key = key
            with open(self.settings_file, 'w') as file:
                json.dump({'threshold': self.threshold, 'key': self.key}, file)
            self.key_tapped = False
            app.lock_status_label["text"] = "入力状態：受付中"
            self.listener.stop()  # Stop the old listener
            self.start_listener()  # Start a new listener
        except ValueError:
            pass

    def process_audio(self, volume):
        if not self.settings_mode and volume > self.threshold:
            with self.key_tapped_lock:
                if not self.key_tapped:
                    self.keyboard.press(self.key)
                    time.sleep(0.05)
                    self.keyboard.release(self.key)
                    self.key_tapped = True

    def terminate(self):
        self.listener.stop()

if __name__ == "__main__":
    app = Application()
    app.mainloop()
    app.controller.terminate()
    app.audio_handler.terminate()
