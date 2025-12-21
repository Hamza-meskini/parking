# main.py
from parking_system import ParkingSystem

def main():
    # 1. Instanciation (Petit parking pour tester la saturation vite)
    parking = ParkingSystem(places_totales=3)
    
    # 2. Scénario de Test
    
    # --- Cas 1 : Entrée Visiteur ---
    parking.gerer_entree()
    
    # --- Cas 2 : Entrée Abonné ---
    parking.gerer_entree()
    
    # --- Cas 3 : Entrée (Le parking devient COMPLET) ---
    parking.gerer_entree()
    
    # --- Cas 4 : Tentative d'entrée alors que c'est plein ---
    parking.gerer_entree() # Doit afficher "Refus" et être bloqué
    
    # --- Cas 5 : Sortie d'un visiteur (Libère une place) ---
    parking.gerer_sortie(est_abonne=False)
    
    # --- Cas 6 : Nouvelle entrée possible ---
    parking.gerer_entree()

if __name__ == "__main__":
    main()