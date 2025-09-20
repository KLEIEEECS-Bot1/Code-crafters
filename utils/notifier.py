# utils/notifier.py
from plyer import notification

def send_notification(title: str, message: str, timeout: int = 5):
    """
    Show a desktop notification. Keep it minimal so failures don't crash everything.
    """
    try:
        notification.notify(title=title, message=message, app_name="KeepMePrivate", timeout=timeout)
    except Exception as e:
        # best-effort: just print if notification fails
        print("Notifier error:", e)
