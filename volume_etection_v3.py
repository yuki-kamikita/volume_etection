import pyaudio
import numpy as np
import threading
import os
import json
from pynput.keyboard import Controller, Listener, Key

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
        KEY = settings['key']
except (FileNotFoundError, ValueError, KeyError):
    THRESHOLD = 300  # ファイルが見つからない場合、または値が無効な場合にはデフォルト値を使用する
    KEY = 'c'

keyboard = Controller()  # キーボードのコントローラを作成
audio = pyaudio.PyAudio()

stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

key_tapped = False  # キーが既にタップされたかどうかを追跡するフラグ
key_tapped_lock = threading.Lock()  # ロックオブジェクトを作成

# ユーザー入力を監視するための別のスレッド
def listen_user_input():
    global THRESHOLD, KEY
    while True:
        user_input = input()
        if user_input.lower() == 'setting':
            try:
                THRESHOLD = int(input('新しいキーを押す音量閾値を入力してください（例：300）：'))
                KEY = input('新しいキーを入力してください（例：c）：')
                # 設定をファイルに保存する
                with open('settings.json', 'w') as file:
                    json.dump({'threshold': THRESHOLD, 'key': KEY}, file)
                reset_display()
            except ValueError:
                print('入力が無効です。閾値は変更されません。')

# キーボードのリスナーを作成
def create_listener():
    def on_key_press(key):
        global key_tapped
        if str(key).replace("'", "") == KEY:
            with key_tapped_lock:  # ロックを取得
                key_tapped = False
                reset_display()  # ディスプレイをリセット
    return Listener(on_press=on_key_press)

def reset_display():
    os.system('cls')  # Clear console
    print("========================================")
    print("=           音声キータッパー           =")
    print("========================================")
    print("\n現在の設定:")
    print(f'  - タップするキー: {KEY}')
    print(f'  - タップする音量閾値: {THRESHOLD}')
    print("\n========================================")
    print("現在の状態:")
    print('  - 入力状態: ', 'ロック中' if key_tapped else '待機中')
    print("\n========================================")
    print("指示:")
    print('  - 音量閾値とタップするキーを変更するには、コンソールに `setting` と入力します。')


listener = create_listener()
listener.start()

reset_display()
input_thread = threading.Thread(target=listen_user_input)
input_thread.start()

try:
    while True:
        data = stream.read(CHUNK)
        numpydata = np.frombuffer(data, dtype=np.int16)
        volume = np.linalg.norm(numpydata) / CHUNK
        with key_tapped_lock:  # ロックを取得
            if volume > THRESHOLD and not key_tapped:
                listener.stop()  # リスナーを一時停止
                keyboard.press(KEY)
                keyboard.release(KEY)  # 直ちにキーを離す
                key_tapped = True  # キーが押されたことを記録する
                listener = create_listener()  # 新しいリスナーを作成
                listener.start()  # リスナーを再開
                reset_display()  # ディスプレイをリセット
except KeyboardInterrupt:
    pass


stream.stop_stream()
stream.close()
audio.terminate()
