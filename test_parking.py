from parking_system import ParkingSystem

def test_initialisation():
    p = ParkingSystem(places_totales=5)
    assert p.places_libres == 5
    assert p.automate.etat_courant.label_etat == "DISPONIBLE"

def test_entree_standard():
    p = ParkingSystem(places_totales=5)
    p.gerer_entree(est_abonne=False)
    assert p.places_libres == 4
    # Vérifie que l'automate est bien revenu à un état d'accueil (STATIONNEMENT ou DISPO)
    assert p.automate.etat_courant.id_etat in [0, 4] 

def test_saturation_parking():
    # Petit parking de 1 place
    p = ParkingSystem(places_totales=1)
    p.gerer_entree() # 0 places restantes
    assert p.places_libres == 0
    
    # Tentative d'entrée en force
    p.gerer_entree()
    assert p.places_libres == 0 # Ne doit pas passer à -1

def test_gratuité_abonne():
    p = ParkingSystem(places_totales=5)
    p.gerer_entree() # On gare une voiture
    
    # On la fait sortir en tant qu'abonné
    solde_avant = p.recettes_totales
    p.gerer_sortie(est_abonne=True)
    assert p.recettes_totales == solde_avant # Pas de changement de caisse

def test_paiement_visiteur():
    p = ParkingSystem(places_totales=5)
    p.gerer_entree()
    
    solde_avant = p.recettes_totales
    p.gerer_sortie(est_abonne=False)
    assert p.recettes_totales == solde_avant + 15.0 # +15 DH