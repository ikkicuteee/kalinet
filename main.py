"""KaliNet native Linux desktop entry point."""
import sys


def main():
    if sys.platform != "linux":
        print("KaliNet requires Linux. Run it inside your Kali Linux VM.", file=sys.stderr)
        return 1
    try:
        import tkinter as tk
        from app.gui.main_window import MainWindow
        from app.utils.logger import configure_logging
        configure_logging()
        window = MainWindow()
        window.mainloop()
    except ImportError as exc:
        print(f"Missing dependency: {exc}. See README.md for installation.", file=sys.stderr)
        return 1
    except tk.TclError as exc:
        print(f"Cannot open the desktop window: {exc}. Run inside the Kali desktop.", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Cannot initialize KaliNet: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
