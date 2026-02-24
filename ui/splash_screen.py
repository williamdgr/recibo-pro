import customtkinter as ctk
import ctypes
from PIL import Image


class SplashScreen(ctk.CTkToplevel):

    def __init__(self, master, splash_image_path, icon_path=None):
        super().__init__(master)

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.resizable(False, False)

        if icon_path:
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self._image = None
        self._width = 460
        self._height = 240
        try:
            pil_image = Image.open(splash_image_path)
            image_width, image_height = pil_image.size
            self._width, self._height = self.get_fitted_size(image_width, image_height)
            self._image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(self._width, self._height))

            label = ctk.CTkLabel(self, text="", image=self._image)
            label.pack()
        except Exception:
            self._width, self._height = self.get_fitted_size(self._width, self._height)
            self.configure(fg_color="#1f2937")

        self.center_on_screen(self._width, self._height)
        self.after(20, lambda: self.center_on_screen(self._width, self._height))

    def to_logical_size(self, size):
        scaling = self._get_window_scaling() if hasattr(self, "_get_window_scaling") else 1.0
        return max(1, int(round(size / scaling)))

    def get_fitted_size(self, raw_width, raw_height):
        width = self.to_logical_size(raw_width)
        height = self.to_logical_size(raw_height)

        screen_width = self.to_logical_size(self.winfo_screenwidth())
        screen_height = self.to_logical_size(self.winfo_screenheight())

        max_width = int(screen_width * 0.9)
        max_height = int(screen_height * 0.9)

        ratio = min(max_width / width, max_height / height, 1)
        fitted_width = max(1, int(width * ratio))
        fitted_height = max(1, int(height * ratio))
        return fitted_width, fitted_height

    def center_on_screen(self, width, height):
        self.geometry(f"{width}x{height}")
        self.update_idletasks()

        try:
            x, y = self.get_center_position_for_active_monitor(width, height)
            self.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            try:
                self.tk.call("tk::PlaceWindow", self._w, "center")
            except Exception:
                screen_width = self.winfo_screenwidth()
                screen_height = self.winfo_screenheight()
                x = max(0, (screen_width - width) // 2)
                y = max(0, (screen_height - height) // 2)
                self.geometry(f"{width}x{height}+{x}+{y}")

        self.minsize(width, height)
        self.maxsize(width, height)

    def get_center_position_for_active_monitor(self, width, height):
        if not hasattr(ctypes, "windll"):
            raise RuntimeError("Monitor API indisponível neste sistema")

        user32 = ctypes.windll.user32

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", ctypes.c_ulong),
            ]

        point = POINT()
        user32.GetCursorPos(ctypes.byref(point))

        monitor = user32.MonitorFromPoint(point, 2)
        if not monitor:
            raise RuntimeError("Não foi possível obter monitor ativo")

        monitor_info = MONITORINFO()
        monitor_info.cbSize = ctypes.sizeof(MONITORINFO)
        user32.GetMonitorInfoW(monitor, ctypes.byref(monitor_info))

        work_area = monitor_info.rcWork
        monitor_width = work_area.right - work_area.left
        monitor_height = work_area.bottom - work_area.top

        x = work_area.left + max(0, (monitor_width - width) // 2)
        y = work_area.top + max(0, (monitor_height - height) // 2)
        return x, y
