def log(gui_mode: bool, message: str):
    """Print message only if not in GUI mode"""
    if not gui_mode:
        print(message)
