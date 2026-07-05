"""
Smart Traffic Light Simulator

Application Tkinter respectant une architecture MVC :
- Modele / metier : machines d'etats, timer, capteur simule, journal.
- Vue : interface graphique Tkinter.
- Controleur : liaison entre les boutons, le service metier et la vue.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import tkinter as tk
from tkinter import ttk


# Bloc 1 - Enumerations metier.
# Ces Enums evitent les chaines de caracteres libres et securisent les etats.
class CarLightState(Enum):
    RED = "Rouge"
    GREEN = "Vert"
    YELLOW = "Jaune"


class PedestrianState(Enum):
    WAIT = "Attendre"
    CROSS = "Traverser"


# Bloc 2 - Constantes de temporisation.
# Les durees proviennent du cahier des charges du MVP.
RED_DURATION = 5
GREEN_DURATION = 5
YELLOW_DURATION = 2
PEDESTRIAN_DURATION = 6
VEHICLE_EXTENSION_STEP = 3
VEHICLE_EXTENSION_MAX = 9
EMERGENCY_DURATION = 10


# Bloc 3 - Snapshot d'affichage.
# Le service renvoie cet objet pour que la vue affiche l'etat sans logique metier.
@dataclass(frozen=True)
class TrafficSnapshot:
    car_state: CarLightState
    pedestrian_state: PedestrianState
    remaining_seconds: int
    running: bool
    paused: bool
    pedestrian_request: bool
    emergency_mode: bool


# Bloc 4 - Machine a etats du feu voiture.
# Elle connait uniquement la sequence Rouge -> Vert -> Jaune -> Rouge.
class CarStateMachine:
    def __init__(self) -> None:
        self.state = CarLightState.RED

    def reset(self) -> None:
        self.state = CarLightState.RED

    def next_state(self) -> CarLightState:
        if self.state == CarLightState.RED:
            self.state = CarLightState.GREEN
        elif self.state == CarLightState.GREEN:
            self.state = CarLightState.YELLOW
        else:
            self.state = CarLightState.RED
        return self.state

    def current_state(self) -> CarLightState:
        return self.state


# Bloc 5 - Machine a etats du feu pieton.
# Elle garantit que le feu pieton a seulement deux etats possibles.
class PedestrianLight:
    def __init__(self) -> None:
        self.state = PedestrianState.WAIT

    def set_cross(self) -> None:
        self.state = PedestrianState.CROSS

    def set_wait(self) -> None:
        self.state = PedestrianState.WAIT

    def current_state(self) -> PedestrianState:
        return self.state


# Bloc 6 - Capteur vehicule simule.
# Il applique le plafond de +9 secondes pour eviter de bloquer le pieton.
class VehicleSensor:
    def __init__(self, max_extension: int = VEHICLE_EXTENSION_MAX) -> None:
        self.max_extension = max_extension
        self.extension_total = 0

    def signal_detected(self) -> int:
        available = self.max_extension - self.extension_total
        extension = min(VEHICLE_EXTENSION_STEP, max(0, available))
        self.extension_total += extension
        return extension

    def extension_used(self) -> int:
        return self.extension_total

    def reset(self) -> None:
        self.extension_total = 0


# Bloc 7 - Timer metier.
# Il gere le compte a rebours independamment de Tkinter.
class Timer:
    def __init__(self) -> None:
        self.remaining = 0
        self.paused = False

    def start(self, duration: int) -> None:
        self.remaining = duration
        self.paused = False

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def stop(self) -> None:
        self.remaining = 0
        self.paused = False

    def extend(self, seconds: int) -> None:
        self.remaining += seconds

    def tick(self) -> None:
        if not self.paused and self.remaining > 0:
            self.remaining -= 1

    def is_expired(self) -> bool:
        return self.remaining <= 0


# Bloc 8 - Journal applicatif.
# Il centralise l'horodatage de tous les evenements visibles dans l'interface.
class EventLogger:
    def __init__(self) -> None:
        self.history: list[str] = []

    def log(self, message: str) -> str:
        entry = f"{datetime.now().strftime('%H:%M:%S')} - {message}"
        self.history.append(entry)
        return entry

    def get_history(self) -> list[str]:
        return list(self.history)

    def clear(self) -> None:
        self.history.clear()


# Bloc 9 - Service metier principal.
# Il orchestre le cycle, la demande pietonne et l'extension vehicule.
class TrafficLightService:
    def __init__(self) -> None:
        self.car_state_machine = CarStateMachine()
        self.pedestrian_light = PedestrianLight()
        self.vehicle_sensor = VehicleSensor()
        self.timer = Timer()
        self.logger = EventLogger()
        self.running = False
        self.pedestrian_request = False
        self.in_pedestrian_phase = False
        self.emergency_mode = False

    # Bloc 10 - Demarrage du cycle.
    # Le feu commence au Rouge avec 5 secondes, comme dans la maquette.
    def start(self) -> list[str]:
        self.running = True
        self.pedestrian_request = False
        self.in_pedestrian_phase = False
        self.emergency_mode = False
        self.car_state_machine.reset()
        self.pedestrian_light.set_wait()
        self.vehicle_sensor.reset()
        self.timer.start(RED_DURATION)
        return [self.logger.log("Simulation demarree - Feu Rouge")]

    # Bloc 11 - Pause, reprise et arret.
    # Ces operations controlent le Timer sans changer les regles metier.
    def pause(self) -> list[str]:
        if self.running and not self.timer.paused:
            self.timer.pause()
            return [self.logger.log("Simulation en pause")]
        return []

    def resume(self) -> list[str]:
        if self.running and self.timer.paused:
            self.timer.resume()
            return [self.logger.log("Simulation reprise")]
        return []

    def stop(self) -> list[str]:
        if not self.running:
            return []
        self.running = False
        self.pedestrian_request = False
        self.in_pedestrian_phase = False
        self.emergency_mode = False
        self.timer.stop()
        self.pedestrian_light.set_wait()
        self.car_state_machine.reset()
        self.vehicle_sensor.reset()
        return [self.logger.log("Simulation arretee - Retour au Rouge")]

    # Bloc 12 - Demande pietonne.
    # Une seule demande est memorisee ; les demandes multiples ne creent pas de file.
    def request_crossing(self) -> list[str]:
        if not self.running:
            return [self.logger.log("Demande pieton ignoree - simulation arretee")]
        if self.pedestrian_request or self.in_pedestrian_phase:
            return [self.logger.log("Demande pieton deja en attente")]
        self.pedestrian_request = True
        return [self.logger.log("Demande pieton memorisee")]

    # Bloc 13 - Detection vehicule simulee.
    # Elle prolonge seulement le Vert, jamais la phase pietonne.
    def signal_vehicle(self) -> list[str]:
        if not self.running:
            return [self.logger.log("Vehicule detecte - simulation arretee, aucun effet")]
        if self.in_pedestrian_phase:
            return [self.logger.log("Vehicule detecte pendant Traverser - aucun effet")]
        if self.car_state_machine.current_state() != CarLightState.GREEN:
            return [self.logger.log("Vehicule detecte hors Vert - aucun effet")]

        extension = self.vehicle_sensor.signal_detected()
        if extension == 0:
            return [self.logger.log("Vehicule detecte - extension maximale atteinte")]

        self.timer.extend(extension)
        total = self.vehicle_sensor.extension_used()
        return [self.logger.log(f"Vehicule detecte - Vert prolonge de {extension}s (total +{total}s)")]

    # Bloc 13B - Mode urgence.
    # Le bouton Urgence force le feu voiture au Rouge pendant 10 secondes pour securiser l'intersection.
    def trigger_emergency(self) -> list[str]:
        if not self.running:
            return [self.logger.log("Urgence ignoree - simulation arretee")]

        self.emergency_mode = True
        self.in_pedestrian_phase = False
        self.pedestrian_request = False
        self.car_state_machine.state = CarLightState.RED
        self.pedestrian_light.set_wait()
        self.vehicle_sensor.reset()
        self.timer.start(EMERGENCY_DURATION)
        return [self.logger.log("URGENCE - Feu force au Rouge pendant 10s")]

    # Bloc 14 - Tick de simulation.
    # Cette methode est appelee chaque seconde par le controleur.
    def tick(self) -> list[str]:
        if not self.running or self.timer.paused:
            return []

        self.timer.tick()
        if not self.timer.is_expired():
            return []

        return self._advance_phase()

    # Bloc 15 - Transition de phase.
    # Les regles de securite pieton sont appliquees au moment ou une phase expire.
    def _advance_phase(self) -> list[str]:
        events: list[str] = []

        if self.emergency_mode:
            self.emergency_mode = False
            self.car_state_machine.state = CarLightState.GREEN
            self.vehicle_sensor.reset()
            self.timer.start(GREEN_DURATION)
            events.append(self.logger.log("Fin urgence - Rouge -> Vert"))
            return events

        if self.in_pedestrian_phase:
            self.in_pedestrian_phase = False
            self.pedestrian_light.set_wait()
            self.car_state_machine.state = CarLightState.GREEN
            self.vehicle_sensor.reset()
            self.timer.start(GREEN_DURATION)
            events.append(self.logger.log("Pieton Attendre - Rouge -> Vert"))
            return events

        current = self.car_state_machine.current_state()
        previous = current
        next_state = self.car_state_machine.next_state()

        if next_state == CarLightState.RED:
            self.vehicle_sensor.reset()
            if self.pedestrian_request:
                self.pedestrian_request = False
                self.in_pedestrian_phase = True
                self.pedestrian_light.set_cross()
                self.timer.start(PEDESTRIAN_DURATION)
                events.append(self.logger.log(f"{previous.value} -> Rouge - Pieton Traverser"))
                return events
            self.timer.start(RED_DURATION)
        elif next_state == CarLightState.GREEN:
            self.timer.start(GREEN_DURATION)
        else:
            self.timer.start(YELLOW_DURATION)

        events.append(self.logger.log(f"{previous.value} -> {next_state.value}"))
        return events

    # Bloc 16 - Etat courant pour la vue.
    # Le controleur lit ce snapshot et decide uniquement quoi afficher.
    def get_snapshot(self) -> TrafficSnapshot:
        return TrafficSnapshot(
            car_state=self.car_state_machine.current_state(),
            pedestrian_state=self.pedestrian_light.current_state(),
            remaining_seconds=self.timer.remaining,
            running=self.running,
            paused=self.timer.paused,
            pedestrian_request=self.pedestrian_request,
            emergency_mode=self.emergency_mode,
        )


# Bloc 17 - Vue Tkinter.
# La vue construit les widgets et expose des methodes de mise a jour.
class TrafficLightView(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Feu Intelligent - Smart Traffic Light Simulator")
        self.geometry("620x720")
        self.minsize(560, 660)
        self.configure(bg="#f4f6f8")

        self.controller: TrafficLightController | None = None
        self.car_lamps: dict[CarLightState, int] = {}
        self._build_layout()

    # Bloc 18 - Construction generale de l'interface.
    # Les widgets sont regroupes par zone : feu, controles, pieton, journal.
    def _build_layout(self) -> None:
        title = ttk.Label(self, text="FEU INTELLIGENT", font=("Segoe UI", 22, "bold"))
        title.pack(pady=(18, 8))

        self.canvas = tk.Canvas(self, width=190, height=330, bg="#2d3436", highlightthickness=0)
        self.canvas.pack(pady=8)
        self._create_car_lamps()

        self.countdown_label = ttk.Label(self, text="Temps restant : 0 s", font=("Segoe UI", 15, "bold"))
        self.countdown_label.pack(pady=8)

        self.status_label = ttk.Label(self, text="Etat : pret", font=("Segoe UI", 11))
        self.status_label.pack(pady=(0, 10))

        controls = ttk.Frame(self)
        controls.pack(pady=8)
        self.start_button = ttk.Button(controls, text="Demarrer", command=self._on_start)
        self.pause_button = ttk.Button(controls, text="Pause", command=self._on_pause)
        self.resume_button = ttk.Button(controls, text="Reprendre", command=self._on_resume)
        self.stop_button = ttk.Button(controls, text="Arreter", command=self._on_stop)
        self.emergency_button = ttk.Button(controls, text="Urgence", command=self._on_emergency)
        for index, button in enumerate((self.start_button, self.pause_button, self.resume_button, self.stop_button, self.emergency_button)):
            button.grid(row=0, column=index, padx=5, ipadx=8)

        pedestrian_frame = ttk.Frame(self)
        pedestrian_frame.pack(pady=14)
        self.pedestrian_label = ttk.Label(pedestrian_frame, text="Feu pieton : Attendre", font=("Segoe UI", 13, "bold"))
        self.pedestrian_label.grid(row=0, column=0, columnspan=2, pady=(0, 8))
        self.pedestrian_button = ttk.Button(pedestrian_frame, text="Demander a traverser", command=self._on_pedestrian)
        self.vehicle_button = ttk.Button(pedestrian_frame, text="Voiture arrive", command=self._on_vehicle)
        self.pedestrian_button.grid(row=1, column=0, padx=6, ipadx=8)
        self.vehicle_button.grid(row=1, column=1, padx=6, ipadx=8)

        journal_label = ttk.Label(self, text="Journal des evenements", font=("Segoe UI", 13, "bold"))
        journal_label.pack(pady=(16, 4))
        self.log_list = tk.Listbox(self, height=10, font=("Consolas", 10))
        self.log_list.pack(fill="both", expand=True, padx=22, pady=(0, 18))

    # Bloc 19 - Dessin des lampes.
    # Les trois cercles restent fixes ; seule leur couleur change.
    def _create_car_lamps(self) -> None:
        lamp_specs = [
            (CarLightState.RED, 35, "#ff4d4d"),
            (CarLightState.YELLOW, 130, "#ffd43b"),
            (CarLightState.GREEN, 225, "#2ecc71"),
        ]
        for state, y, _color in lamp_specs:
            self.car_lamps[state] = self.canvas.create_oval(45, y, 145, y + 100, fill="#111", outline="#555", width=3)

    # Bloc 20 - Liaison avec le controleur.
    # La vue ne connait pas le service, seulement les callbacks du controleur.
    def set_controller(self, controller: "TrafficLightController") -> None:
        self.controller = controller

    def _on_start(self) -> None:
        if self.controller:
            self.controller.on_start()

    def _on_pause(self) -> None:
        if self.controller:
            self.controller.on_pause()

    def _on_resume(self) -> None:
        if self.controller:
            self.controller.on_resume()

    def _on_stop(self) -> None:
        if self.controller:
            self.controller.on_stop()

    def _on_pedestrian(self) -> None:
        if self.controller:
            self.controller.on_pedestrian_button()

    def _on_vehicle(self) -> None:
        if self.controller:
            self.controller.on_vehicle_button()

    # Bloc 20B - Callback du bouton Urgence.
    # La vue transmet l'action au controleur sans appliquer elle-meme la regle metier.
    def _on_emergency(self) -> None:
        if self.controller:
            self.controller.on_emergency_button()

    # Bloc 21 - Mise a jour du feu voiture.
    # Une seule lampe est allumee a la fois, conformement aux regles metier.
    def update_car_light(self, state: CarLightState) -> None:
        active_colors = {
            CarLightState.RED: "#ff4d4d",
            CarLightState.YELLOW: "#ffd43b",
            CarLightState.GREEN: "#2ecc71",
        }
        for lamp_state, item_id in self.car_lamps.items():
            color = active_colors[lamp_state] if lamp_state == state else "#111"
            self.canvas.itemconfigure(item_id, fill=color)

    # Bloc 22 - Mise a jour du feu pieton, du compteur et du statut.
    # Ces methodes affichent seulement les donnees fournies par le snapshot.
    def update_pedestrian_light(self, state: PedestrianState) -> None:
        label = "Feu pieton : Traverser" if state == PedestrianState.CROSS else "Feu pieton : Attendre"
        self.pedestrian_label.configure(text=label)

    def update_countdown(self, seconds: int) -> None:
        self.countdown_label.configure(text=f"Temps restant : {seconds} s")

    def update_status(self, snapshot: TrafficSnapshot) -> None:
        if not snapshot.running:
            text = "Etat : arrete"
        elif snapshot.paused:
            text = "Etat : pause"
        elif snapshot.emergency_mode:
            text = "Etat : URGENCE - feu force au Rouge"
        elif snapshot.pedestrian_request:
            text = "Etat : demande pieton en attente"
        else:
            text = f"Etat : {snapshot.car_state.value}"
        self.status_label.configure(text=text)

    def append_log(self, entry: str) -> None:
        self.log_list.insert(tk.END, entry)
        self.log_list.yview_moveto(1)


# Bloc 23 - Controleur MVC.
# Il recoit les actions utilisateur et synchronise service + vue.
class TrafficLightController:
    def __init__(self, view: TrafficLightView, service: TrafficLightService) -> None:
        self.view = view
        self.service = service
        self.after_id: str | None = None
        self.view.set_controller(self)
        self.refresh_view()

    # Bloc 24 - Actions des boutons principaux.
    # Chaque action appelle le service, affiche les logs, puis rafraichit la vue.
    def on_start(self) -> None:
        self._append_events(self.service.start())
        self.refresh_view()
        self._schedule_tick()

    def on_pause(self) -> None:
        self._append_events(self.service.pause())
        self.refresh_view()

    def on_resume(self) -> None:
        self._append_events(self.service.resume())
        self.refresh_view()
        self._schedule_tick()

    def on_stop(self) -> None:
        self._cancel_tick()
        self._append_events(self.service.stop())
        self.refresh_view()

    def on_pedestrian_button(self) -> None:
        self._append_events(self.service.request_crossing())
        self.refresh_view()

    def on_vehicle_button(self) -> None:
        self._append_events(self.service.signal_vehicle())
        self.refresh_view()

    # Bloc 24B - Action Urgence.
    # Le controleur appelle le service, rafraichit l'affichage et relance la boucle du timer.
    def on_emergency_button(self) -> None:
        self._append_events(self.service.trigger_emergency())
        self.refresh_view()
        self._schedule_tick()

    # Bloc 25 - Boucle Tkinter.
    # Tkinter appelle _tick toutes les secondes via after().
    def _schedule_tick(self) -> None:
        self._cancel_tick()
        if self.service.running and not self.service.timer.paused:
            self.after_id = self.view.after(1000, self._tick)

    def _cancel_tick(self) -> None:
        if self.after_id is not None:
            self.view.after_cancel(self.after_id)
            self.after_id = None

    def _tick(self) -> None:
        self.after_id = None
        self._append_events(self.service.tick())
        self.refresh_view()
        self._schedule_tick()

    # Bloc 26 - Synchronisation de l'interface.
    # Le controleur applique le snapshot du service a la vue.
    def refresh_view(self) -> None:
        snapshot = self.service.get_snapshot()
        self.view.update_car_light(snapshot.car_state)
        self.view.update_pedestrian_light(snapshot.pedestrian_state)
        self.view.update_countdown(snapshot.remaining_seconds)
        self.view.update_status(snapshot)

    def _append_events(self, events: list[str]) -> None:
        for entry in events:
            self.view.append_log(entry)


# Bloc 27 - Point d'entree.
# Ce bloc assemble MVC et lance la boucle graphique Tkinter.
def main() -> None:
    service = TrafficLightService()
    view = TrafficLightView()
    TrafficLightController(view, service)
    view.mainloop()


if __name__ == "__main__":
    main()
