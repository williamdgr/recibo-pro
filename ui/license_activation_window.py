import customtkinter as ctk
import ctypes

from app_info import APP_NAME, APP_VERSION
from licence.licences import ativar_licenca


class LicenseActivationWindow(ctk.CTkToplevel):

    def __init__(self, master, on_success, icon_path=None):
        super().__init__(master)
        self.on_success = on_success

        self.title(f"Ativação de Licença - {APP_NAME}")
        self.geometry("520x260")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        if icon_path:
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.build_layout()
        self.center_on_screen(520, 260)

        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self.grab_set()
        self.key_entry.focus_set()

    def build_layout(self):
        ctk.CTkLabel(self, text="Ativação de Licença", font=("Arial", 24, "bold")).pack(pady=(20, 4))
        ctk.CTkLabel(self, text=f"{APP_NAME} v{APP_VERSION}", font=("Arial", 12)).pack(pady=(0, 14))

        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=20, pady=4)

        ctk.CTkLabel(form, text="Chave da licença:", font=("Arial", 13, "bold")).pack(anchor="w", padx=12, pady=(12, 6))

        self.key_entry = ctk.CTkEntry(form, placeholder_text="Informe sua chave de licença")
        self.key_entry.pack(fill="x", padx=12, pady=(0, 10))

        self.activate_button = ctk.CTkButton(form, text="Ativar", command=self.activate)
        self.activate_button.pack(padx=12, pady=(0, 12), anchor="e")

        self.status_label = ctk.CTkLabel(self, text="", text_color="red")
        self.status_label.pack(pady=(4, 0))

    def activate(self):
        key = self.key_entry.get().strip()
        if not key:
            self.show_error("Informe a chave de licença para ativar.")
            return

        self.activate_button.configure(state="disabled", text="Validando...")
        self.update_idletasks()

        success, message = ativar_licenca(key)
        if not success:
            self.show_error(message)
            self.activate_button.configure(state="normal", text="Ativar")
            return

        self.show_success("Licença ativada com sucesso. Abrindo sistema...")
        self.after(150, self.finish_success)

    def finish_success(self):
        self.grab_release()
        self.destroy()
        self.on_success()

    def show_error(self, message):
        self.status_label.configure(text=message, text_color="red")

    def show_success(self, message):
        self.status_label.configure(text=message, text_color="#22c55e")

    def close_app(self):
        self.grab_release()
        self.master.destroy()

    def center_on_screen(self, width, height):
        self.update_idletasks()
        try:
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
            monitor_info = MONITORINFO()
            monitor_info.cbSize = ctypes.sizeof(MONITORINFO)
            user32.GetMonitorInfoW(monitor, ctypes.byref(monitor_info))

            area = monitor_info.rcWork
            x = area.left + max(0, ((area.right - area.left) - width) // 2)
            y = area.top + max(0, ((area.bottom - area.top) - height) // 2)
            self.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            x = (self.winfo_screenwidth() - width) // 2
            y = (self.winfo_screenheight() - height) // 2
            self.geometry(f"{width}x{height}+{x}+{y}")
