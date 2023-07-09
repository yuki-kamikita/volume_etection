import tkinter as tk
from pynput.keyboard import Controller
import time

# キーボードのコントローラを作成
keyboard = Controller()

def press_c():
    keyboard.press('c')
    time.sleep(0.05)
    keyboard.release('c')

# GUIウィンドウを作成
window = tk.Tk()
window.title("cボタン")

# ボタンを作成
button = tk.Button(window, text="cを押す", command=press_c)
button.pack()

# GUIを実行
window.mainloop()
