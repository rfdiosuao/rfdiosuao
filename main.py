import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import threading
import time
import json
import os
import sys
import re

# Resource helper for PyInstaller
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Debug helper
def log(msg):
    # print(f"[DEBUG] {msg}") # Uncomment for debug
    pass

try:
    import keyboard
    import mouse
    from clicker_core import HighResClicker
except Exception as e:
    messagebox.showerror("Error", f"Dependency missing: {e}")
    sys.exit(1)

# --- Configuration & Assets ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SyntaxHighlighter:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.tags = {
            "keyword": "#FF7B72", # Red/Pink
            "string": "#A5D6FF",  # Light Blue
            "comment": "#8B949E", # Gray
            "number": "#79C0FF",  # Blue
            "function": "#D2A8FF" # Purple
        }
        self._setup_tags()
        self.text_widget.bind("<KeyRelease>", self.highlight)

    def _setup_tags(self):
        for name, color in self.tags.items():
            self.text_widget.tag_config(name, foreground=color)

    def highlight(self, event=None):
        content = self.text_widget.get("1.0", "end-1c")
        
        # Clear existing tags
        for tag in self.tags.keys():
            self.text_widget.tag_remove(tag, "1.0", "end")

        # Regex patterns
        patterns = [
            ("keyword", r"\b(import|def|if|else|elif|while|for|return|from|as|try|except|finally)\b"),
            ("function", r"\b(mouse|time|print|click|move|press|release|sleep)\b"),
            ("string", r"(['\"])(?:(?=(\\?))\2.)*?\1"),
            ("comment", r"#.*"),
            ("number", r"\b\d+(\.\d+)?\b")
        ]

        for tag, pattern in patterns:
            for match in re.finditer(pattern, content):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.text_widget.tag_add(tag, start, end)

class AutomationApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("自动化脚本工具 Pro")
        self.geometry("900x700")
        self.resizable(True, True)
        
        # Set Window Icon
        try:
            # Use PNG for window icon, but resize it first to prevent display issues
            icon_path = resource_path("icon.png")
            img = Image.open(icon_path)
            # Resize to standard icon size (32x32 is standard for window title bar)
            img = img.resize((32, 32), Image.Resampling.LANCZOS)
            
            self.icon_image = ImageTk.PhotoImage(img)
            self.iconphoto(False, self.icon_image)
            
            # Try to set taskbar icon separately if ICO exists
            icon_ico_path = resource_path("icon.ico")
            if os.path.exists(icon_ico_path):
                 try:
                    self.iconbitmap(icon_ico_path)
                 except: pass
        except Exception as e:
            print(f"Warning: Could not load icon: {e}")

        # Core Components
        self.clicker = HighResClicker()
        self.clicker.on_stats_update = self.update_clicker_stats
        
        self.hotkey_clicker = "F8"
        self.hotkey_record = "F9"
        self.hotkey_play = "F10"
        
        self.is_recording = False
        self.recorded_events = []
        self.playback_thread = None
        self.is_playing = False

        # Grid Layout (1x2)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # --- Sidebar ---
        self._setup_sidebar()

        # --- Main Content Frames ---
        self.frames = {}
        self.frames["clicker"] = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frames["recorder"] = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frames["settings"] = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        
        self._setup_clicker_frame()
        self._setup_recorder_frame()
        self._setup_settings_frame()

        # Show Home by default
        self.select_frame("clicker")
        
        # Initial Hotkeys - Delayed to avoid startup freeze
        self.after(1000, self._refresh_hotkeys)

    def _setup_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="AutoScript Pro", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.nav_btns = {}
        
        self.nav_btns["clicker"] = ctk.CTkButton(self.sidebar_frame, text="鼠标连点器", command=lambda: self.select_frame("clicker"))
        self.nav_btns["clicker"].grid(row=1, column=0, padx=20, pady=10)
        
        self.nav_btns["recorder"] = ctk.CTkButton(self.sidebar_frame, text="脚本录制/编辑", command=lambda: self.select_frame("recorder"))
        self.nav_btns["recorder"].grid(row=2, column=0, padx=20, pady=10)
        
        self.nav_btns["settings"] = ctk.CTkButton(self.sidebar_frame, text="全局设置", command=lambda: self.select_frame("settings"))
        self.nav_btns["settings"].grid(row=3, column=0, padx=20, pady=10)

        # Appearance Mode
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="主题模式:", anchor="w")
        self.appearance_mode_label.grid(row=6, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Dark", "Light", "System"],
                                                               command=lambda m: ctk.set_appearance_mode(m))
        self.appearance_mode_optionemenu.grid(row=7, column=0, padx=20, pady=(10, 20))

    def select_frame(self, name):
        # Reset buttons
        for btn_name, btn in self.nav_btns.items():
            btn.configure(fg_color=("gray75", "gray25") if btn_name == name else "transparent")
            
        # Switch frame
        for frame_name, frame in self.frames.items():
            if frame_name == name:
                frame.grid(row=0, column=1, sticky="nsew")
            else:
                frame.grid_forget()

    # --- Clicker Frame ---
    def _setup_clicker_frame(self):
        frame = self.frames["clicker"]
        frame.grid_columnconfigure(0, weight=1)
        
        # Stats Panel
        stats_panel = ctk.CTkFrame(frame, corner_radius=15)
        stats_panel.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        stats_panel.grid_columnconfigure((0,1,2), weight=1)
        
        self.clicker_start_btn = ctk.CTkButton(stats_panel, text=f"开始连点 ({self.hotkey_clicker})", 
                                             font=ctk.CTkFont(size=18, weight="bold"),
                                             height=60, corner_radius=10, 
                                             command=self.toggle_clicker,
                                             fg_color="#2CC985", hover_color="#229C68")
        self.clicker_start_btn.grid(row=0, column=0, rowspan=2, padx=20, pady=20, sticky="ew")
        
        self.click_count_lbl = ctk.CTkLabel(stats_panel, text="0", font=ctk.CTkFont(size=24, weight="bold"))
        self.click_count_lbl.grid(row=1, column=1)
        ctk.CTkLabel(stats_panel, text="点击次数").grid(row=0, column=1)
        
        self.click_time_lbl = ctk.CTkLabel(stats_panel, text="0.0s", font=ctk.CTkFont(size=24, weight="bold"))
        self.click_time_lbl.grid(row=1, column=2)
        ctk.CTkLabel(stats_panel, text="运行时间").grid(row=0, column=2)

        # Config Panel
        config_panel = ctk.CTkScrollableFrame(frame, label_text="连点配置")
        config_panel.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)
        
        # CPS
        ctk.CTkLabel(config_panel, text="点击频率 (CPS):").pack(anchor="w", padx=10)
        self.cps_slider = ctk.CTkSlider(config_panel, from_=1, to=500, number_of_steps=499, command=lambda v: self.cps_val_lbl.configure(text=str(int(v))))
        self.cps_slider.set(10)
        self.cps_slider.pack(fill="x", padx=10)
        self.cps_val_lbl = ctk.CTkLabel(config_panel, text="10")
        self.cps_val_lbl.pack(anchor="e", padx=10)
        
        # Button
        ctk.CTkLabel(config_panel, text="鼠标按键:").pack(anchor="w", padx=10, pady=(10,0))
        self.btn_seg = ctk.CTkSegmentedButton(config_panel, values=["左键", "右键", "中键"])
        self.btn_seg.set("左键")
        self.btn_seg.pack(fill="x", padx=10, pady=5)

    # --- Recorder Frame ---
    def _setup_recorder_frame(self):
        frame = self.frames["recorder"]
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # Toolbar
        toolbar = ctk.CTkFrame(frame)
        toolbar.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        
        self.rec_btn = ctk.CTkButton(toolbar, text=f"开始录制 ({self.hotkey_record})", command=self.toggle_recording, fg_color="#E04F5F", hover_color="#C23848")
        self.rec_btn.pack(side="left", padx=5, pady=5)
        
        self.play_btn = ctk.CTkButton(toolbar, text=f"播放脚本 ({self.hotkey_play})", command=self.toggle_playback, fg_color="#3B8ED0", hover_color="#36719F")
        self.play_btn.pack(side="left", padx=5, pady=5)
        
        ctk.CTkButton(toolbar, text="清空", command=self.clear_script, fg_color="gray", width=60).pack(side="right", padx=5)
        
        # Editor
        self.editor_container = ctk.CTkFrame(frame)
        self.editor_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.editor_container.grid_rowconfigure(0, weight=1)
        self.editor_container.grid_columnconfigure(0, weight=1)
        
        # Using CTkTextbox but accessing underlying tk widget for tagging
        self.editor = ctk.CTkTextbox(self.editor_container, font=("Consolas", 14), undo=True, wrap="none")
        self.editor.grid(row=0, column=0, sticky="nsew")
        self.editor.insert("1.0", "# 脚本编辑器\n# 点击 '开始录制' 生成代码\nimport mouse\nimport time\n")
        
        # Initialize Highlighter
        # Access internal textbox: ._textbox is the CTkTextbox's internal tk.Text
        self.highlighter = SyntaxHighlighter(self.editor._textbox)
        self.highlighter.highlight()

    # --- Settings Frame ---
    def _setup_settings_frame(self):
        frame = self.frames["settings"]
        
        ctk.CTkLabel(frame, text="热键设置", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=20, pady=20)
        
        self.hk_entries = {}
        for key, label in [("clicker", "连点器开关"), ("record", "录制开关"), ("play", "播放开关")]:
            row = ctk.CTkFrame(frame)
            row.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(row, text=label).pack(side="left", padx=10)
            
            entry = ctk.CTkEntry(row, placeholder_text="点击绑定")
            entry.pack(side="right", padx=10)
            
            # Default values
            default_val = getattr(self, f"hotkey_{key}")
            entry.insert(0, default_val)
            
            # Bind events
            entry.bind("<FocusIn>", lambda e, k=key, ent=entry: self._on_hotkey_focus(k, ent))
            entry.bind("<FocusOut>", lambda e, ent=entry: self._on_hotkey_blur(ent))
            
            self.hk_entries[key] = entry
            
        ctk.CTkLabel(frame, text="注意: 修改热键后自动生效，请避免热键冲突。", text_color="gray").pack(pady=20)

    # --- Hotkey Logic ---
    def _on_hotkey_focus(self, key_name, entry_widget):
        entry_widget.delete(0, "end")
        entry_widget.insert(0, "按下按键...")
        self.current_binding_key = key_name
        self.current_binding_entry = entry_widget
        # Hook keyboard to catch next key
        self.hook_id = keyboard.hook(self._on_key_press)

    def _on_hotkey_blur(self, entry_widget):
        if hasattr(self, "hook_id"):
            try:
                keyboard.unhook(self.hook_id)
            except:
                pass
        # If left empty/waiting, revert (simplified)
        if entry_widget.get() == "按下按键...":
             old_val = getattr(self, f"hotkey_{self.current_binding_key}")
             entry_widget.delete(0, "end")
             entry_widget.insert(0, old_val)

    def _on_key_press(self, event):
        if event.event_type == "down":
            key = event.name.upper()
            if key in ["CTRL", "SHIFT", "ALT"]:
                return
            
            self.current_binding_entry.delete(0, "end")
            self.current_binding_entry.insert(0, key)
            
            setattr(self, f"hotkey_{self.current_binding_key}", key)
            self._refresh_hotkeys()
            
            keyboard.unhook(self.hook_id)
            del self.hook_id
            self.focus()

    def _refresh_hotkeys(self):
        try:
            keyboard.unhook_all()
            keyboard.add_hotkey(self.hotkey_clicker, self.toggle_clicker)
            keyboard.add_hotkey(self.hotkey_record, self.toggle_recording)
            keyboard.add_hotkey(self.hotkey_play, self.toggle_playback)
            
            self.clicker_start_btn.configure(text=f"开始连点 ({self.hotkey_clicker})")
            self.rec_btn.configure(text=f"开始录制 ({self.hotkey_record})")
            self.play_btn.configure(text=f"播放脚本 ({self.hotkey_play})")
        except Exception as e:
            print(f"Hotkey Error: {e}")

    # --- Clicker Logic ---
    def toggle_clicker(self):
        if self.clicker.running:
            self.clicker.stop()
            self.clicker_start_btn.configure(fg_color="#2CC985", text=f"开始连点 ({self.hotkey_clicker})")
        else:
            self.clicker.cps = self.cps_slider.get()
            btn_map = {"左键": "left", "右键": "right", "中键": "middle"}
            self.clicker.button = btn_map.get(self.btn_seg.get(), "left")
            self.clicker.start()
            self.clicker_start_btn.configure(fg_color="#E53935", text=f"停止连点 ({self.hotkey_clicker})")

    def update_clicker_stats(self, count, elapsed):
        self.after(0, lambda: self.click_count_lbl.configure(text=str(count)))
        self.after(0, lambda: self.click_time_lbl.configure(text=f"{elapsed:.1f}s"))

    # --- Recorder Logic ---
    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        self.is_recording = True
        self.recorded_events = []
        self.rec_btn.configure(text=f"停止录制 ({self.hotkey_record})", fg_color="#E53935")
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", "# 正在录制...\n")
        
        # Capture initial position manually because hook might miss it before first move
        try:
            init_pos = mouse.get_position()
            self.recorded_events.append(mouse.MoveEvent(init_pos[0], init_pos[1], time.time()))
        except:
            pass
            
        mouse.hook(self.recorded_events.append)
        self.start_time = time.time()

    def stop_recording(self):
        self.is_recording = False
        mouse.unhook(self.recorded_events.append)
        self.rec_btn.configure(text="正在处理...", fg_color="gray", state="disabled")
        
        # Run processing in a background thread to prevent UI freeze
        threading.Thread(target=self._process_recording_async, daemon=True).start()

    def _process_recording_async(self):
        try:
            # 1. Optimize Event Stream (Sparse Sampling)
            # Filter out 90% of redundant move events to speed up processing
            optimized_events = self._optimize_event_stream(self.recorded_events)
            
            # 2. Generate Code
            code = self._events_to_code(optimized_events)
            
            # 3. Update UI on Main Thread
            self.after(0, lambda: self._finish_processing(code))
        except Exception as e:
            print(f"Processing Error: {e}")
            self.after(0, lambda: self._finish_processing(f"# Error processing recording: {e}"))

    def _finish_processing(self, code):
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", code)
        self.highlighter.highlight()
        self.rec_btn.configure(text=f"开始录制 ({self.hotkey_record})", fg_color="#E04F5F", state="normal")

    def _optimize_event_stream(self, events):
        if not events: return []
        filtered = []
        last_pos = (-100, -100)
        
        n = len(events)
        for i, e in enumerate(events):
            if isinstance(e, mouse.ButtonEvent):
                filtered.append(e)
            elif isinstance(e, mouse.MoveEvent):
                # Always keep the first move
                if not filtered:
                    filtered.append(e)
                    last_pos = (e.x, e.y)
                    continue
                
                # Always keep move if the NEXT event is a ButtonEvent (Precision)
                if i + 1 < n and isinstance(events[i+1], mouse.ButtonEvent):
                    filtered.append(e)
                    last_pos = (e.x, e.y)
                    continue

                # Otherwise, only keep if distance > 5 pixels (Sparse Sampling)
                if abs(e.x - last_pos[0]) > 5 or abs(e.y - last_pos[1]) > 5:
                    filtered.append(e)
                    last_pos = (e.x, e.y)
        return filtered

    def _events_to_code(self, events):
        if not events:
            return ""
            
        lines = ["import mouse", "import time", "import ctypes", "", 
                 "# Enable high precision timer",
                 "ctypes.windll.winmm.timeBeginPeriod(1)", 
                 "# Enable High DPI Awareness",
                 "try:",
                 "    ctypes.windll.shcore.SetProcessDpiAwareness(1)",
                 "except:",
                 "    pass",
                 "",
                 "def run_script():"]
        
        # --- PASS 1: Normalize Events & Detect Clicks ---
        # Convert raw events into a stream of:
        # {'type': 'move', 'x': x, 'y': y, 'time': t}
        # {'type': 'click', 'button': b, 'x': x, 'y': y, 'time': t, 'duration': d}
        # {'type': 'press', ...}
        # {'type': 'release', ...}
        
        normalized = []
        i = 0
        n = len(events)
        
        # Track current state
        cur_x, cur_y = 0, 0
        
        while i < n:
            e = events[i]
            if isinstance(e, mouse.MoveEvent):
                cur_x, cur_y = e.x, e.y
                normalized.append({'type': 'move', 'x': e.x, 'y': e.y, 'time': e.time})
                i += 1
            elif isinstance(e, mouse.ButtonEvent):
                if e.event_type == 'down':
                    # Look ahead for Up
                    found_up = False
                    j = i + 1
                    while j < n:
                        next_e = events[j]
                        if isinstance(next_e, mouse.MoveEvent):
                            # Ignore small moves
                            if abs(next_e.x - cur_x) > 5 or abs(next_e.y - cur_y) > 5:
                                break
                            j += 1
                            continue
                        if isinstance(next_e, mouse.ButtonEvent) and next_e.event_type == 'up' and next_e.button == e.button:
                            # It's a click
                            normalized.append({
                                'type': 'click', 
                                'button': e.button, 
                                'x': cur_x, 
                                'y': cur_y, 
                                'time': next_e.time, # Use end time
                                'start_time': e.time
                            })
                            i = j + 1
                            found_up = True
                            break
                        break
                    
                    if not found_up:
                        normalized.append({'type': 'press', 'button': e.button, 'x': cur_x, 'y': cur_y, 'time': e.time})
                        i += 1
                else:
                    normalized.append({'type': 'release', 'button': e.button, 'x': cur_x, 'y': cur_y, 'time': e.time})
                    i += 1
        
        # --- PASS 2: Detect Double Clicks ---
        final_ops = []
        i = 0
        n = len(normalized)
        
        while i < n:
            op = normalized[i]
            
            if op['type'] == 'click':
                # Check next op for double click
                is_double = False
                j = i + 1
                while j < n:
                    next_op = normalized[j]
                    if next_op['type'] == 'move':
                        # Allow tiny moves between clicks
                        if abs(next_op['x'] - op['x']) > 5 or abs(next_op['y'] - op['y']) > 5:
                            break
                        j += 1
                        continue
                    
                    if next_op['type'] == 'click' and next_op['button'] == op['button']:
                        # Check time gap
                        gap = next_op['start_time'] - op['time']
                        if gap < 0.8: # Generous 0.8s gap
                            final_ops.append({
                                'type': 'double_click',
                                'button': op['button'],
                                'x': op['x'],
                                'y': op['y'],
                                'time': next_op['time']
                            })
                            i = j + 1 # Skip both clicks
                            is_double = True
                        break
                    break
                
                if not is_double:
                    final_ops.append(op)
                    i += 1
            else:
                final_ops.append(op)
                i += 1
                
        # --- PASS 3: Generate Code ---
        last_time = events[0].time if events else time.time()
        
        # We need to track the "current" cursor position in the script to avoid redundant moves
        script_x, script_y = -1, -1
        
        for op in final_ops:
            # Time delay
            # For double clicks, we use the time of the *second* click, but we want to wait relative to previous op
            # If it's a double click, 'time' is the end of 2nd click.
            # We should probably use the start of the sequence.
            # Simplified: just use op['time'] or op['start_time'] if available.
            
            # Use 'start_time' for clicks if available to get pre-click delay, else 'time'
            target_time = op.get('start_time', op['time']) if op['type'] in ['click', 'double_click'] else op['time']
            
            dt = target_time - last_time
            if dt > 0.002:
                lines.append(f"    time.sleep({dt:.4f})")
            
            # Move
            if 'x' in op:
                if (op['x'], op['y']) != (script_x, script_y):
                     lines.append(f"    mouse.move({op['x']}, {op['y']})")
                     script_x, script_y = op['x'], op['y']
            
            # Action
            if op['type'] == 'move':
                pass # Already handled by move logic above
            elif op['type'] == 'click':
                lines.append(f"    mouse.click(button='{op['button']}')")
            elif op['type'] == 'double_click':
                lines.append(f"    mouse.double_click(button='{op['button']}')")
            elif op['type'] == 'press':
                lines.append(f"    mouse.press(button='{op['button']}')")
            elif op['type'] == 'release':
                lines.append(f"    mouse.release(button='{op['button']}')")
                
            last_time = op['time'] # Update to end time of operation

        lines.append("")
        lines.append("    ctypes.windll.winmm.timeEndPeriod(1)")
        lines.append("")
        lines.append("if __name__ == '__main__':")
        lines.append("    run_script()")
        return "\n".join(lines)

    # --- Playback Logic ---
    def toggle_playback(self):
        if self.is_playing:
            self.is_playing = False 
        else:
            code = self.editor.get("1.0", "end")
            threading.Thread(target=self._run_script, args=(code,), daemon=True).start()

    def _run_script(self, code):
        self.is_playing = True
        self.play_btn.configure(text=f"停止播放 ({self.hotkey_play})", fg_color="#E53935")
        
        try:
            # Pass __name__='__main__' so the script executes its main block
            exec(code, {'mouse': mouse, 'time': time, '__name__': '__main__'})
        except Exception as e:
            print(f"Script Error: {e}")
            messagebox.showerror("运行错误", f"脚本执行出错:\n{e}")
        finally:
            self.is_playing = False
            self.after(0, lambda: self.play_btn.configure(text=f"播放脚本 ({self.hotkey_play})", fg_color="#3B8ED0"))
            
    def clear_script(self):
        self.editor.delete("1.0", "end")

if __name__ == "__main__":
    try:
        app = AutomationApp()
        
        def on_closing():
            if app.clicker.running:
                app.clicker.stop()
            app.destroy()
            keyboard.unhook_all()
            mouse.unhook_all()
            
        app.protocol("WM_DELETE_WINDOW", on_closing)
        app.mainloop()
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("Error... Press Enter")
