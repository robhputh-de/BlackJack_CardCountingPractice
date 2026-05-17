# expiry.py
# ============================================================
# Trial / Expiry system for Rob's Blackjack App
# Works in BOTH modes:
#   A) Pure Python (just import this module)
#   B) Compiled EXE (reads install date from Windows registry,
#      written there by the NSIS installer)
#
# HOW TO USE IN YOUR APP:
#   Add this one line at the very top of blackjack.py:
#
#       from expiry import check_expiry
#       check_expiry()    # will exit the app if expired
#
# TRIAL PERIOD:
#   - Set TRIAL_DAYS below to however many days you want (30, 60, etc.)
#   - If running as compiled EXE: reads InstallDate from registry
#   - If running as Python script: uses a local hidden file as fallback
# ============================================================

import sys
import os
from datetime import datetime, timedelta

# ── CONFIG ──────────────────────────────────────────────────
TRIAL_DAYS   = 60          # change to 30 for one month, 60 for two months
APP_NAME     = "BlackjackApp"
REG_KEY      = r"Software\BlackjackApp"
REG_VALUE    = "InstallDate"
FALLBACK_FILE = os.path.join(os.path.expanduser("~"), ".blackjack_install")
# ────────────────────────────────────────────────────────────


def _get_install_date_from_registry() -> datetime | None:
    """Read the install date written by the NSIS installer."""
    try:
        import winreg
        key  = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY)
        val, _ = winreg.QueryValueEx(key, REG_VALUE)
        winreg.CloseKey(key)
        # Format is YYYYMMDD e.g. "20260512"
        return datetime.strptime(str(val), "%Y%m%d")
    except Exception:
        return None


def _get_or_create_install_date_from_file() -> datetime:
    """
    Fallback for running as plain Python (no installer).
    Creates a hidden file with today's date on first run.
    """
    if os.path.exists(FALLBACK_FILE):
        try:
            with open(FALLBACK_FILE, "r") as f:
                date_str = f.read().strip()
            return datetime.strptime(date_str, "%Y%m%d")
        except Exception:
            pass  # corrupted — reset below

    # First run: record today
    today_str = datetime.now().strftime("%Y%m%d")
    try:
        with open(FALLBACK_FILE, "w") as f:
            f.write(today_str)
        # Hide the file on Windows
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(FALLBACK_FILE, 2)  # 2 = HIDDEN
    except Exception:
        pass

    return datetime.now()


def _get_install_date() -> datetime:
    """Try registry first (compiled EXE), fall back to file (Python script)."""
    reg_date = _get_install_date_from_registry()
    if reg_date:
        return reg_date
    return _get_or_create_install_date_from_file()


def check_expiry(silent: bool = False) -> bool:
    """
    Check if the trial period has expired.

    Returns:
        True  — still within trial, app can continue
        False — expired (and exits the app unless silent=True)

    Usage:
        check_expiry()           # exits automatically if expired
        check_expiry(silent=True)  # returns False without exiting
    """
    install_date  = _get_install_date()
    expiry_date   = install_date + timedelta(days=TRIAL_DAYS)
    today         = datetime.now()
    days_remaining = (expiry_date - today).days

    print(f"[Trial] Install date : {install_date.strftime('%B %d, %Y')}")
    print(f"[Trial] Expiry date  : {expiry_date.strftime('%B %d, %Y')}")
    print(f"[Trial] Days remaining: {max(0, days_remaining)}")

    if today > expiry_date:
        _show_expired_message(expiry_date)
        if not silent:
            sys.exit(0)
        return False

    # Show a warning when close to expiry
    if days_remaining <= 7:
        _show_warning_message(days_remaining)

    return True


def days_remaining() -> int:
    """Utility: how many trial days are left (0 if expired)."""
    install_date = _get_install_date()
    expiry_date  = install_date + timedelta(days=TRIAL_DAYS)
    remaining    = (expiry_date - datetime.now()).days
    return max(0, remaining)


def _show_expired_message(expiry_date: datetime):
    """Show a GUI or console expiry message."""
    msg = (
        f"This trial version of {APP_NAME} expired on "
        f"{expiry_date.strftime('%B %d, %Y')}.\n\n"
        f"Please contact Rob Puth to obtain a full license."
    )
    try:
        # Try PyQt5 dialog first (since the app uses PyQt5)
        from PyQt5.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication(sys.argv)
        box = QMessageBox()
        box.setWindowTitle("Trial Expired")
        box.setText(msg)
        box.setIcon(QMessageBox.Critical)
        box.exec_()
    except ImportError:
        # Fallback: plain console message
        print("\n" + "="*50)
        print("  TRIAL EXPIRED")
        print("="*50)
        print(msg)
        print("="*50 + "\n")


def _show_warning_message(days_left: int):
    """Warn user when expiry is approaching."""
    msg = (
        f"Your trial of {APP_NAME} expires in {days_left} day(s).\n"
        f"Please contact Rob Puth for a full license."
    )
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.warning(None, "Trial Expiring Soon", msg)
    except ImportError:
        print(f"\n[WARNING] {msg}\n")


# ── Quick test when run directly ────────────────────────────
if __name__ == "__main__":
    print(f"Trial days configured : {TRIAL_DAYS}")
    print(f"Days remaining        : {days_remaining()}")
    result = check_expiry(silent=True)
    print(f"App allowed to run    : {result}")