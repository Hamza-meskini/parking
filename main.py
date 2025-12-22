# main.py
from parking_system import ParkingSystem

def main():
    parking = ParkingSystem(places_totales=3)
    
    # Test Console
    parking.gerer_entree() # Visiteur
    parking.gerer_entree(est_abonne=True) # Abonné
    parking.gerer_entree() # Complet
    
    parking.gerer_entree() # Rejet
    
    parking.gerer_sortie(est_abonne=False) # Paiement
    parking.gerer_entree() # Place libérée

if __name__ == "__main__":
    main()