import time
import threading
import ctypes
import random
from ctypes import wintypes

# --- Win32 API Definitions ---
user32 = ctypes.windll.user32
winmm = ctypes.windll.winmm

INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))]

class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD),
                ("mi", MOUSEINPUT)]

def _send_click(btn_down, btn_up):
    extra = ctypes.c_ulong(0)
    ii_down = INPUT()
    ii_down.type = INPUT_MOUSE
    ii_down.mi.dwFlags = btn_down
    ii_down.mi.dwExtraInfo = ctypes.pointer(extra)

    ii_up = INPUT()
    ii_up.type = INPUT_MOUSE
    ii_up.mi.dwFlags = btn_up
    ii_up.mi.dwExtraInfo = ctypes.pointer(extra)

    # Send input array to reduce system calls
    inputs = (INPUT * 2)(ii_down, ii_up)
    user32.SendInput(2, ctypes.pointer(inputs), ctypes.sizeof(INPUT))

class HighResClicker:
    def __init__(self):
        self.running = False
        self.thread = None
        self._stop_event = threading.Event()
        
        # Settings
        self.cps = 10.0
        self.button = 'left' # left, right, middle
        self.random_range = 0.0 # ms jitter
        self.limit_mode = 'none' # none, count, time
        self.limit_value = 0
        
        # Stats
        self.total_clicks = 0
        self.start_time = 0
        self.on_stats_update = None # Callback function
        
        # Win32 Timer Resolution
        self.timer_resolution_set = False

    def _set_timer_resolution(self):
        if not self.timer_resolution_set:
            winmm.timeBeginPeriod(1)
            self.timer_resolution_set = True

    def _reset_timer_resolution(self):
        if self.timer_resolution_set:
            winmm.timeEndPeriod(1)
            self.timer_resolution_set = False

    def _get_click_flags(self):
        if self.button == 'right':
            return MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
        elif self.button == 'middle':
            return MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP
        else:
            return MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP

    def start(self):
        if self.running:
            return
        
        self.running = True
        self._stop_event.clear()
        self.total_clicks = 0
        self.start_time = time.time()
        
        self._set_timer_resolution()
        
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        self._stop_event.set()
        self.thread.join()
        self._reset_timer_resolution()

    def _loop(self):
        down_flag, up_flag = self._get_click_flags()
        next_click_time = time.perf_counter()
        
        clicks_done = 0
        
        while self.running:
            if self._stop_event.is_set():
                break

            # Check limits
            if self.limit_mode == 'count' and clicks_done >= self.limit_value:
                break
            if self.limit_mode == 'time' and (time.time() - self.start_time) >= self.limit_value:
                break

            # Perform Click
            _send_click(down_flag, up_flag)
            clicks_done += 1
            self.total_clicks = clicks_done
            
            # Update stats (throttled to avoid GUI lag)
            if self.on_stats_update and clicks_done % 10 == 0:
                 self.on_stats_update(clicks_done, time.time() - self.start_time)

            # Calculate delay
            base_interval = 1.0 / self.cps
            jitter = 0
            if self.random_range > 0:
                # Randomize within +/- range (converted to seconds)
                jitter = random.uniform(-self.random_range/1000.0, self.random_range/1000.0)
            
            target_delay = base_interval + jitter
            if target_delay < 0.001: target_delay = 0.001 # Hard floor for stability

            # Precise sleep logic
            current_time = time.perf_counter()
            next_click_time += target_delay
            
            # If we fell behind, catch up but don't burst too hard
            if next_click_time < current_time:
                next_click_time = current_time

            sleep_duration = next_click_time - current_time
            if sleep_duration > 0:
                time.sleep(sleep_duration)

        self.running = False
        self._reset_timer_resolution()
        # Final update
        if self.on_stats_update:
            self.on_stats_update(self.total_clicks, time.time() - self.start_time)

