# coding: utf-8
import os
import re
import threading
import time  # Se importa el modulo time
import nuke


class AutoSaverCallbacks:

    # Se anaden los nuevos parametros con valores por defecto
    def __init__(self, backup_interval=1200, idle_threshold=300):
        self.backup_interval = backup_interval
        self.idle_threshold = idle_threshold  # Nuevo: Umbral de inactividad
        self.timer = None
        self.last_interaction_time = time.time()  # Nuevo: Guarda el tiempo de la ultima interaccion

        # Nuevo: Se registra el callback para detectar la actividad del usuario
        nuke.addUpdateUI(self._track_interaction)

        # Mensaje modificado para ser mas informativo, usando el formato antiguo
        print("AutoSaver listo. Intervalo: {0:.0f} min. Limite de inactividad: {1:.0f} min.".format(
            self.backup_interval / 60.0, self.idle_threshold / 60.0))

    # --- NUEVO METODO ---
    # Este metodo se ejecuta constantemente para actualizar el tiempo de la ultima interaccion
    def _track_interaction(self):
        self.last_interaction_time = time.time()

    def _get_next_version_path(self, script_path):
        script_dir = os.path.dirname(script_path)
        base_name = os.path.basename(script_path)
        match = re.search(r'(.+?)(\.v)(\d+)(\.nk)$', base_name, re.IGNORECASE)
        if match:
            name_part, v_part, version_num, ext_part = match.groups()
            next_version = int(version_num) + 1
            new_name = "{0}{1}{2:03d}{3}".format(name_part, v_part, next_version, ext_part)
        else:
            name_part, ext_part = os.path.splitext(base_name)
            new_name = "{0}.v001{1}".format(name_part, ext_part)
        return os.path.join(script_dir, new_name)

    def _execute_version_up(self):

        # --- LOGICA DE INACTIVIDAD ANADIDA ---
        idle_duration = time.time() - self.last_interaction_time
        if idle_duration > self.idle_threshold:
            # Mensaje sin emojis y con formato antiguo
            print("AutoSaver: Usuario inactivo por {0:.1f} minutos. Omitiendo guardado.".format(idle_duration / 60.0))
            self.start_or_reset_timer()  # Se reprograma la proxima revision
            return
        # --- FIN DE LA LOGICA DE INACTIVIDAD ---

        current_path = nuke.root().name()
        if not current_path or current_path == "Root":
            return

        next_version_path = self._get_next_version_path(current_path)
        if current_path.lower() == next_version_path.lower():
            nuke.scriptSave()
            return

        print("[OK] AutoSaver: Versionando a: {0}".format(os.path.basename(next_version_path)))
        nuke.scriptSaveAs(filename=next_version_path, overwrite=1)

        self.start_or_reset_timer()

    def start_or_reset_timer(self):
        # Nuevo: Cualquier guardado o carga de script cuenta como una interaccion
        self._track_interaction()

        if self.timer:
            self.timer.cancel()

        current_path = nuke.root().name()
        if current_path and current_path != "Root":
            print("AutoSaver: Proximo guardado programado en {0:.0f} minutos.".format(self.backup_interval / 60.0))
            self.timer = threading.Timer(self.backup_interval,
                                         lambda: nuke.executeInMainThread(self._execute_version_up))
            self.timer.start()

    def stop_timer(self):
        if self.timer:
            self.timer.cancel()
            self.timer = None

        # Nuevo: Es una buena practica eliminar el callback cuando ya no se necesita
        nuke.removeUpdateUI(self._track_interaction)
        print("AutoSaver: Temporizador detenido.")


# Se crea la instancia con los nuevos parametros
# backup_interval es el tiempo entre guardados (1200 seg = 20 minutos)
# idle_threshold es el limite de inactividad (300 seg = 5 minutos)
auto_saver_instance = AutoSaverCallbacks(backup_interval=4800, idle_threshold=300)

# El registro de los callbacks principales no cambia
nuke.addOnScriptLoad(auto_saver_instance.start_or_reset_timer)
nuke.addOnScriptSave(auto_saver_instance.start_or_reset_timer)
nuke.addOnScriptClose(auto_saver_instance.stop_timer)