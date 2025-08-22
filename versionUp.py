import os
import re
import threading
import time  # Import the time module
import nuke


class AutoSaverCallbacks:
    """
    An auto-saver that uses Nuke's callbacks to work safely.
    It starts a timer only when a script is loaded and pauses saving
    if the user is detected as idle.
    """

    def __init__(self, backup_interval=1200, idle_threshold=300):
        """
        Initializes the auto-saver.
        Args:
            backup_interval (int): Time in seconds between save attempts (e.g., 1200 = 20 minutes).
            idle_threshold (int): Time in seconds of inactivity before considering the user idle (e.g., 300 = 5 minutes).
        """
        self.backup_interval = backup_interval
        self.idle_threshold = idle_threshold
        self.timer = None
        self.last_interaction_time = time.time()

        # Register the callback to track user activity
        nuke.addUpdateUI(self._track_interaction)

        print(
            f"🚀 AutoSaver listo. Intervalo: {backup_interval / 60:.0f} min. Límite de inactividad: {idle_threshold / 60:.0f} min.")

    def _track_interaction(self):
        """Updates the timestamp of the last known user interaction."""
        self.last_interaction_time = time.time()

    def _get_next_version_path(self, script_path):
        """Calculates the path for the next versioned script."""
        script_dir = os.path.dirname(script_path)
        base_name = os.path.basename(script_path)
        match = re.search(r'(.+?)(\.v)(\d+)(\.nk)$', base_name, re.IGNORECASE)

        if match:
            name_part, v_part, version_num, ext_part = match.groups()
            next_version = int(version_num) + 1
            new_name = f"{name_part}{v_part}{next_version:03d}{ext_part}"
        else:
            name_part, ext_part = os.path.splitext(base_name)
            new_name = f"{name_part}.v001{ext_part}"

        return os.path.join(script_dir, new_name)

    def _execute_version_up(self):
        """
        Performs the idle check and then saves a new version of the script.
        This method is called by the timer.
        """
        # --- IDLE CHECK ---
        idle_duration = time.time() - self.last_interaction_time
        if idle_duration > self.idle_threshold:
            print(f"💤 AutoSaver: Usuario inactivo por {idle_duration / 60:.1f} minutos. Omitiendo guardado.")
            self.start_or_reset_timer()  # Reschedule the next check without saving
            return

        # --- SAVE LOGIC ---
        current_path = nuke.root().name()
        if not current_path or current_path == "Root":
            return

        next_version_path = self._get_next_version_path(current_path)

        # If the script name doesn't have a version, this prevents an immediate version up.
        # It will just save normally, and the next auto-save will version up.
        if current_path.lower() == next_version_path.lower():
            nuke.scriptSave()
            print("✅ AutoSaver: Script guardado (sin versionar).")
        else:
            print(f"✅ AutoSaver: Versionando a: {os.path.basename(next_version_path)}")
            nuke.scriptSaveAs(filename=next_version_path, overwrite=1)

        # After saving, restart the timer for the next cycle
        self.start_or_reset_timer()

    def start_or_reset_timer(self):
        """Starts a new timer or resets the existing one."""
        # A manual save or script load is an interaction, so we update the timestamp.
        self._track_interaction()

        if self.timer:
            self.timer.cancel()

        current_path = nuke.root().name()
        if current_path and current_path != "Root":
            print(f"AutoSaver: Próximo guardado programado en {self.backup_interval / 60:.0f} minutos.")
            # Create a timer that calls the save function in the main Nuke thread
            self.timer = threading.Timer(self.backup_interval,
                                         lambda: nuke.executeInMainThread(self._execute_version_up))
            self.timer.start()

    def stop_timer(self):
        """Stops the timer when the script is closed."""
        if self.timer:
            self.timer.cancel()
            self.timer = None
        print("AutoSaver: Temporizador detenido.")
        # It's good practice to remove the callback when it's no longer needed.
        nuke.removeUpdateUI(self._track_interaction)


# 1. Create a single instance of our class.
#    backup_interval is the time between saves (e.g., 20 minutes = 1200 seconds).
#    idle_threshold is the user inactivity limit (e.g., 5 minutes = 300 seconds).
auto_saver_instance = AutoSaverCallbacks(backup_interval=4800, idle_threshold=300)

# 2. Tell Nuke to call our functions when events occur.
#    - On script load (open or new save) -> Starts/resets the timer.
#    - On manual save -> Also resets the timer.
#    - On script close -> Stops the timer.
nuke.addOnScriptLoad(auto_saver_instance.start_or_reset_timer)
nuke.addOnScriptSave(auto_saver_instance.start_or_reset_timer)
nuke.addOnScriptClose(auto_saver_instance.stop_timer)