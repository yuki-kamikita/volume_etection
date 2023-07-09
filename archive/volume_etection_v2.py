import pyaudio
import numpy as np
import threading
import os
import json
import time
from pynput.keyboard import Controller

# 音声の形式とレートを設定
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024

# 初期設定ファイルを読み込む
try:
    with open('settings.json', 'r') as file:
        settings = json.load(file)
        THRESHOLD = settings['threshold']
        THRESHOLD_RELEASE = settings['threshold_release']
        KEY = settings['key']
except (FileNotFoundError, ValueError, KeyError):
    THRESHOLD = 300  # ファイルが見つからない場合、または値が無効な場合にはデフォルト値を使用する
    THRESHOLD_RELEASE = 50
    KEY = 'c'

def display_settings():
    os.system('cls')  # Clear console
    print(f'キーを押す音量閾値：{THRESHOLD}')
    print(f'キーを離す音量閾値：{THRESHOLD_RELEASE}')
    print(f'現在の押し続けるキー：{KEY}')
    print('コンソールに`setting`と入力して閾値と押し続けるキーを変更できます')

keyboard = Controller()  # キーボードのコントローラを作成
audio = pyaudio.PyAudio()

stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

key_pressed = False  # キーが現在押されているかどうかを追跡するフラグ

# ユーザー入力を監視するための別のスレッド
def listen_user_input():
    global THRESHOLD, THRESHOLD_RELEASE, KEY
    while True:
        user_input = input()
        if user_input.lower() == 'setting':
            try:
                THRESHOLD = int(input('新しいキーを押す音量閾値を入力してください（例：300）：'))
                THRESHOLD_RELEASE = int(input('新しいキーを離す音量閾値を入力してください（例：50）：'))
                KEY = input('新しいキーを入力してください（例：c）：')
                # 設定をファイルに保存する
                with open('settings.json', 'w') as file:
                    json.dump({'threshold': THRESHOLD, 'threshold_release': THRESHOLD_RELEASE, 'key': KEY}, file)
                display_settings()
            except ValueError:
                print('入力が無効です。閾値は変更されません。')

display_settings()
input_thread = threading.Thread(target=listen_user_input)
input_thread.start()

try:
    while True:
        data = stream.read(CHUNK)
        numpydata = np.frombuffer(data, dtype=np.int16)
        volume = np.linalg.norm(numpydata) / CHUNK
        if volume > THRESHOLD and not key_pressed:
            keyboard.press(KEY)  # キーを押す
            time.sleep(0.05)
            keyboard.release(KEY)  # キーを離す
            key_pressed = True
        elif volume <= THRESHOLD_RELEASE and key_pressed:
            key_pressed = False
except KeyboardInterrupt:
    pass

# スクリプトを終了する前に、必ずキーを離す
if key_pressed:
    keyboard.release(KEY)

stream.stop_stream()
stream.close()
audio.terminate()
