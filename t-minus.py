import pygame
import sys
import os
import json
import tkinter as tk
from tkinter import colorchooser, filedialog
from datetime import datetime, timedelta
import ctypes
from ctypes import wintypes 

# --- CONFIG & PATHS ---
CONFIG_FILE = os.path.join(os.environ.get('APPDATA', '.'), "clock_settings.json")

defaults = {
    "speed": 3,
    "font_size": 120,
    "color": "#00FF00",
    "opacity": 255,
    "timer_minutes": 10,
    "audio_path": "alarm.mp3",
    "font_name": "Consolas",
    "ignore_mouse": False
}

def load_settings():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return {**defaults, **json.load(f)}
        except: return defaults
    return defaults

def save_settings(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

def show_settings_gui():
    config = load_settings()
    root = tk.Tk()
    root.title("T-Minus Configuration")
    root.geometry("400x600")
    root.attributes("-topmost", True)

    tk.Label(root, text="Timer Minutes:").pack(pady=2)
    min_ent = tk.Entry(root); min_ent.insert(0, str(config["timer_minutes"])); min_ent.pack()

    tk.Label(root, text="Bounce Speed:").pack(pady=2)
    speed_sc = tk.Scale(root, from_=1, to=30, orient="horizontal"); speed_sc.set(config["speed"]); speed_sc.pack()

    tk.Label(root, text="Font Size:").pack(pady=2)
    size_sc = tk.Scale(root, from_=20, to=400, orient="horizontal"); size_sc.set(config["font_size"]); size_sc.pack()

    tk.Label(root, text="Opacity:").pack(pady=2)
    op_sc = tk.Scale(root, from_=30, to=255, orient="horizontal"); op_sc.set(config["opacity"]); op_sc.pack()

    ignore_var = tk.BooleanVar(value=config["ignore_mouse"])
    tk.Checkbutton(root, text="Ignore Mouse Movement", variable=ignore_var).pack(pady=10)

    current_color = config["color"]
    def pick_color():
        nonlocal current_color
        color = colorchooser.askcolor(title="Pick Color")[1]
        if color: current_color = color
    tk.Button(root, text="Pick Color", command=pick_color).pack()

    current_audio = config["audio_path"]
    def browse_audio():
        nonlocal current_audio
        file = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav")])
        if file: current_audio = file
    tk.Button(root, text="Browse Audio", command=browse_audio).pack(pady=5)

    def apply():
        config.update({"timer_minutes": int(min_ent.get()), "speed": speed_sc.get(), 
                       "font_size": size_sc.get(), "opacity": op_sc.get(), 
                       "color": current_color, "audio_path": current_audio,
                       "ignore_mouse": ignore_var.get()})
        save_settings(config); root.destroy()

    tk.Button(root, text="SAVE & START", bg="green", fg="white", command=apply).pack(pady=20)
    root.mainloop()

# --- THE SCREENSAVER ENGINE ---
def run_clock(preview_hwnd=None):
    config = load_settings()
    
    try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except: ctypes.windll.user32.SetProcessDPIAware()

    pygame.init()
    pygame.mixer.init()
    
    real_h = ctypes.windll.user32.GetSystemMetrics(1) 
    
    if preview_hwnd:
        rect = wintypes.RECT()
        ctypes.windll.user32.GetClientRect(preview_hwnd, ctypes.byref(rect))
        v_width, v_height = rect.right - rect.left, rect.bottom - rect.top
        if v_width <= 0: v_width, v_height = 160, 120
        
        scale_ratio = v_height / real_h
        os.environ['SDL_WINDOWID'] = str(preview_hwnd)
        screen = pygame.display.set_mode((v_width, v_height))
        
        f_size = max(int(config["font_size"] * scale_ratio), 8)
        
        # --- THE SPEED FIX ---
        # We multiply by 0.5 or lower to ensure it doesn't zip around like a fly
        move = [config["speed"] * scale_ratio * 0.5, 
                config["speed"] * scale_ratio * 0.5]
    else:
        v_width = ctypes.windll.user32.GetSystemMetrics(78)
        v_height = ctypes.windll.user32.GetSystemMetrics(79)
        v_left = ctypes.windll.user32.GetSystemMetrics(76)
        v_top = ctypes.windll.user32.GetSystemMetrics(77)

        os.environ['SDL_VIDEO_WINDOW_POS'] = f"{v_left},{v_top}"
        screen = pygame.display.set_mode((v_width, v_height), pygame.NOFRAME)
        pygame.mouse.set_visible(False)
        
        f_size = config["font_size"]
        move = [float(config["speed"]), float(config["speed"])]

    font = pygame.font.SysFont(config["font_name"], f_size)
    sub_font = pygame.font.SysFont(config["font_name"], f_size // 2)
    
    # Track position as floats for smooth sub-pixel movement
    pos = [float(v_width // 4), float(v_height // 4)]
    
    end_time = datetime.now() + timedelta(minutes=config["timer_minutes"])
    alarm_triggered = False
    clock_timer = pygame.time.Clock()

    while True:
        screen.fill((0, 0, 0))
        now = datetime.now()
        
        time_surf = font.render(now.strftime("%H:%M:%S"), True, config["color"])
        time_surf.set_alpha(config["opacity"])
        
        rem_seconds = int((end_time - now).total_seconds())
        if rem_seconds > 0:
            m, s = divmod(rem_seconds, 60)
            cd_surf = sub_font.render(f"T-MINUS {m:02d}:{s:02d}", True, config["color"])
        else:
            cd_surf = sub_font.render("TIME UP", True, "#FF0000")
            if not alarm_triggered and not preview_hwnd:
                try:
                    if os.path.exists(config["audio_path"]):
                        pygame.mixer.music.load(config["audio_path"])
                        # CHANGED: -1 means loop infinitely
                        pygame.mixer.music.play(loops=-1) 
                        pygame.mixer.music.set_volume(1.0)
                    alarm_triggered = True
                except: pass
        cd_surf.set_alpha(config["opacity"])

        max_w = max(time_surf.get_width(), cd_surf.get_width())
        total_h = time_surf.get_height() + cd_surf.get_height()

        # Update position with floats
        pos[0] += move[0]
        pos[1] += move[1]

        # Bounce Logic
        if pos[0] <= 0 or pos[0] + max_w >= v_width: move[0] *= -1
        if pos[1] <= 0 or pos[1] + total_h >= v_height: move[1] *= -1

        # Blit using integer versions of the float position
        screen.blit(time_surf, (int(pos[0]) + (max_w - time_surf.get_width())//2, int(pos[1])))
        screen.blit(cd_surf, (int(pos[0]) + (max_w - cd_surf.get_width())//2, int(pos[1]) + time_surf.get_height()))

        pygame.display.flip()

        for event in pygame.event.get():
            if not preview_hwnd:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_s:
                        pygame.quit(); show_settings_gui(); run_clock(); return
                    else: pygame.quit(); sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN: pygame.quit(); sys.exit()
                if event.type == pygame.MOUSEMOTION and not config["ignore_mouse"]:
                    if abs(event.rel[0]) > 15 or abs(event.rel[1]) > 15: pygame.quit(); sys.exit()
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
        
        clock_timer.tick(60)

if __name__ == "__main__":
    mode = "/s"
    hwnd = None

    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if "/c" in arg:
            mode = "/c"
        elif "/p" in arg:
            mode = "/p"
            if ":" in arg:
                hwnd = int(arg.split(":")[1])
            elif len(sys.argv) > 2:
                hwnd = int(sys.argv[2])

    if mode == "/c":
        show_settings_gui()
    elif mode == "/p" and hwnd is not None:
        run_clock(preview_hwnd=hwnd)
    else:
        run_clock()