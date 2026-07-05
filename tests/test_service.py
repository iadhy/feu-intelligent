import unittest

from main import (
    CarLightState,
    EMERGENCY_DURATION,
    GREEN_DURATION,
    PEDESTRIAN_DURATION,
    TrafficLightService,
    YELLOW_DURATION,
)


# Bloc test 1 - Outil de simulation.
# Cette fonction avance le service sans lancer Tkinter.
def advance(service: TrafficLightService, seconds: int) -> None:
    for _ in range(seconds):
        service.tick()


# Bloc test 2 - Validation du cycle automatique.
# Le feu doit suivre Rouge -> Vert -> Jaune -> Rouge.
class TrafficLightServiceTest(unittest.TestCase):
    def test_cycle_rouge_vert_jaune_rouge(self) -> None:
        service = TrafficLightService()
        service.start()

        advance(service, 5)
        self.assertEqual(service.car_state_machine.current_state(), CarLightState.GREEN)

        advance(service, GREEN_DURATION)
        self.assertEqual(service.car_state_machine.current_state(), CarLightState.YELLOW)

        advance(service, YELLOW_DURATION)
        self.assertEqual(service.car_state_machine.current_state(), CarLightState.RED)

    # Bloc test 3 - Validation de la demande pietonne.
    # La phase Traverser doit apparaitre seulement quand le feu voiture est Rouge.
    def test_demande_pieton_declenche_traverser_au_rouge(self) -> None:
        service = TrafficLightService()
        service.start()

        advance(service, 5)
        service.request_crossing()
        advance(service, GREEN_DURATION + YELLOW_DURATION)

        snapshot = service.get_snapshot()
        self.assertEqual(snapshot.car_state, CarLightState.RED)
        self.assertEqual(snapshot.pedestrian_state.value, "Traverser")

        advance(service, PEDESTRIAN_DURATION)
        snapshot = service.get_snapshot()
        self.assertEqual(snapshot.car_state, CarLightState.GREEN)
        self.assertEqual(snapshot.pedestrian_state.value, "Attendre")

    # Bloc test 4 - Validation du plafond vehicule.
    # Les appuis successifs ne doivent jamais depasser +9 secondes.
    def test_extension_vehicule_est_plafonnee_a_neuf_secondes(self) -> None:
        service = TrafficLightService()
        service.start()
        advance(service, 5)

        base_remaining = service.timer.remaining
        service.signal_vehicle()
        service.signal_vehicle()
        service.signal_vehicle()
        service.signal_vehicle()

        self.assertEqual(service.vehicle_sensor.extension_used(), 9)
        self.assertEqual(service.timer.remaining, base_remaining + 9)

    # Bloc test 5 - Validation pause/reprise.
    # Le timer ne doit pas diminuer pendant la pause.
    def test_pause_bloque_le_compte_a_rebours(self) -> None:
        service = TrafficLightService()
        service.start()
        service.pause()

        before = service.timer.remaining
        advance(service, 3)
        self.assertEqual(service.timer.remaining, before)

        service.resume()
        advance(service, 1)
        self.assertEqual(service.timer.remaining, before - 1)

    # Bloc test 6 - Validation du mode urgence.
    # Le bouton Urgence force le feu au Rouge, puis le cycle reprend au Vert apres 10 secondes.
    def test_urgence_force_rouge_puis_reprend_au_vert(self) -> None:
        service = TrafficLightService()
        service.start()
        advance(service, 5)

        service.trigger_emergency()
        snapshot = service.get_snapshot()
        self.assertEqual(snapshot.car_state, CarLightState.RED)
        self.assertTrue(snapshot.emergency_mode)
        self.assertEqual(snapshot.remaining_seconds, EMERGENCY_DURATION)

        advance(service, EMERGENCY_DURATION)
        snapshot = service.get_snapshot()
        self.assertEqual(snapshot.car_state, CarLightState.GREEN)
        self.assertFalse(snapshot.emergency_mode)


if __name__ == "__main__":
    unittest.main()
