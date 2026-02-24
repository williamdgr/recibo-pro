import customtkinter as ctk
from app_paths import get_asset_path
from app_info import APP_NAME, APP_VERSION
from ui.receipt_view import ReceiptView

class MainWindow(ctk.CTk):

    def __init__(self, license_active=False):
        super().__init__()
        self.license_active = license_active

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.maximize_window()
        self.set_app_icon()

        self.main_area = ctk.CTkFrame(self)
        self.main_area.pack(fill="both", expand=True)

        self.show_receipt()

    def clear(self):
        for widget in self.main_area.winfo_children():
            widget.destroy()

    def show_receipt(self):
        self.clear()
        ReceiptView(self.main_area)

    def set_app_icon(self):
        icon_path = get_asset_path("icone.ico")
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

    def apply_screen_ratio_layout(self, width_ratio=0.7, height_ratio=0.88):
        self.update_idletasks()

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        width = max(960, int(screen_width * width_ratio))
        height = max(680, int(screen_height * height_ratio))

        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)

        self.geometry(f"{width}x{height}+{x}+{y}")

    def maximize_window(self):
        try:
            self.state("zoomed")
        except Exception:
            self.apply_screen_ratio_layout(width_ratio=1.0, height_ratio=1.0)
