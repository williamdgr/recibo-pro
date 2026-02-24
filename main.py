from ui.main_window import MainWindow
from models.init_db import init_db
from ui.splash_screen import SplashScreen
from ui.license_activation_window import LicenseActivationWindow
from licence.licences import possui_arquivo_licenca
from app_paths import get_asset_path
from services.backup_service import create_startup_backup

if __name__ == "__main__":
    init_db()

    try:
        create_startup_backup(max_files=7)
    except Exception:
        pass

    splash_path = get_asset_path("splash.png")
    icon_path = get_asset_path("icone.ico")

    app = MainWindow(license_active=possui_arquivo_licenca())
    app.withdraw()

    splash = SplashScreen(app, splash_image_path=str(splash_path), icon_path=str(icon_path))

    def show_main_window():
        try:
            if splash.winfo_exists():
                splash.destroy()
        except Exception:
            pass

        app.license_active = True
        app.deiconify()
        app.maximize_window()
        app.after(50, app.maximize_window)
        app.lift()
        app.focus_force()

    def show_activation_window():
        try:
            if splash.winfo_exists():
                splash.destroy()
        except Exception:
            pass

        LicenseActivationWindow(
            app,
            on_success=show_main_window,
            icon_path=str(icon_path),
        )

    def start_flow():
        if possui_arquivo_licenca():
            show_main_window()
        else:
            show_activation_window()

    app.after(1800, start_flow)
    app.mainloop()
