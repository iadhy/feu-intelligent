# Feu Intelligent - Smart Traffic Light Simulator

Application Python 3 avec Tkinter respectant le cahier des charges :

- architecture MVC ;
- code oriente objet ;
- cycle automatique Rouge -> Vert -> Jaune -> Rouge ;
- compte a rebours ;
- boutons Demarrer, Pause, Reprendre, Arreter, Urgence ;
- demande pieton memorisee ;
- phase pieton Traverser uniquement au Rouge ;
- detection vehicule simulee avec extension du Vert plafonnee a 9 secondes ;
- mode Urgence qui force temporairement le feu au Rouge ;
- journal des evenements horodates.

## Lancer l'application

```powershell
python main.py
```

## Lancer les tests

```powershell
python -m unittest discover -s tests
```

## Architecture MVC

`TrafficLightView` est la vue Tkinter. Elle affiche les lampes, le compteur, les boutons et le journal.

`TrafficLightController` est le controleur. Il recoit les clics utilisateur, appelle le service metier et rafraichit la vue.

`TrafficLightService` est le coeur metier. Il orchestre le cycle, la phase pietonne, le capteur vehicule simule, le timer et le journal.

Les classes `CarStateMachine`, `PedestrianLight`, `VehicleSensor`, `Timer` et `EventLogger` representent les composants metier et techniques demandes dans la conception detaillee.

## Validation de chaque bloc

| Bloc | Element | Validation |
| --- | --- | --- |
| 1 | `CarLightState`, `PedestrianState` | Les etats sont limites aux valeurs autorisees : Rouge, Vert, Jaune, Attendre, Traverser. |
| 2 | Constantes de duree | Les durees sont centralisees : Rouge 5s, Vert 5s, Jaune 2s, Pieton 6s, extension +3s max +9s, Urgence 10s. |
| 3 | `TrafficSnapshot` | La vue recoit un etat complet sans acceder directement a la logique metier. |
| 4 | `CarStateMachine` | La sequence Rouge -> Vert -> Jaune -> Rouge est garantie par `next_state()`. |
| 5 | `PedestrianLight` | Le feu pieton ne peut etre que `Attendre` ou `Traverser`. |
| 6 | `VehicleSensor` | L'extension du Vert est comptabilisee et plafonnee a 9 secondes. |
| 7 | `Timer` | Le compte a rebours sait demarrer, pause, reprendre, s'arreter, s'etendre et expirer. |
| 8 | `EventLogger` | Chaque evenement est horodate et conserve dans l'historique. |
| 9 | `TrafficLightService` | Le service regroupe les composants metier sans melanger l'interface Tkinter. |
| 10 | `start()` | La simulation demarre au Rouge, avec timer initialise et journal mis a jour. |
| 11 | `pause()`, `resume()`, `stop()` | Les controles principaux changent l'etat de simulation et journalisent l'action. |
| 12 | `request_crossing()` | Une seule demande pietonne est memorisee et n'interrompt pas le cycle courant. |
| 13 | `signal_vehicle()` | Le vehicule prolonge uniquement le Vert ; pendant Traverser ou hors Vert, aucun effet metier. |
| 13B | `trigger_emergency()` | Le bouton Urgence force le feu voiture au Rouge pendant 10 secondes, annule la demande pieton en cours et securise l'intersection. |
| 14 | `tick()` | Le cycle avance une fois par seconde seulement si la simulation tourne et n'est pas en pause. |
| 15 | `_advance_phase()` | Les transitions appliquent la securite pieton : Traverser uniquement quand voiture est Rouge. |
| 16 | `get_snapshot()` | Le service expose un etat lisible pour la vue, sans detail interne. |
| 17 | `TrafficLightView` | La fenetre Tkinter contient l'affichage du feu, du pieton, des boutons et du journal. |
| 18 | `_build_layout()` | Tous les widgets attendus dans le cahier des charges sont presents. |
| 19 | `_create_car_lamps()` | Les trois lampes sont dessinees une fois et mises a jour ensuite. |
| 20 | Callbacks de vue | Les boutons deleguent au controleur, pas au service directement. |
| 20B | `_on_emergency()` | Le bouton Urgence delegue son action au controleur, en gardant la vue sans logique metier. |
| 21 | `update_car_light()` | Une seule lampe voiture est allumee a la fois. |
| 22 | Updates UI | Le compteur, le statut et le feu pieton affichent le snapshot courant. |
| 23 | `TrafficLightController` | Le controleur relie proprement Vue et Service selon MVC. |
| 24 | Actions controleur | Chaque bouton appelle une methode metier puis rafraichit l'affichage. |
| 24B | `on_emergency_button()` | Le controleur declenche l'urgence, met a jour le journal et relance la boucle du timer. |
| 25 | Boucle `after()` | Tkinter pilote le cycle sans bloquer l'interface graphique. |
| 26 | `refresh_view()` | L'interface est synchronisee depuis un snapshot unique. |
| 27 | `main()` | Le point d'entree assemble le MVC et lance Tkinter. |

## Criteres d'acceptation couverts

- L'application demarre avec `python main.py`.
- Les trois lampes sont affichees.
- Le cycle automatique respecte Rouge -> Vert -> Jaune -> Rouge.
- Le compte a rebours est visible.
- Les boutons Demarrer, Pause, Reprendre et Arreter sont disponibles.
- Le bouton Urgence force le feu voiture au Rouge pendant 10 secondes.
- Le journal affiche les changements d'etat et les actions importantes.
- Le bouton pieton declenche une phase Traverser au prochain Rouge.
- Le feu pieton ne passe jamais a Traverser pendant le Vert.
- Le bouton Voiture arrive prolonge le Vert jusqu'a 9 secondes maximum.
