# parking_system.py
from automate_base import Automate, Etat
import random # Nécessaire pour la simulation aléatoire dans le GUI

class ParkingSystem:
    def __init__(self, places_totales=50, tarif_horaire=2.5):
        self.places_totales = places_totales
        self.places_libres = places_totales
        self.tarif_horaire = tarif_horaire
        
        # Initialisation du moteur
        self.automate = Automate()
        self._construire_automate()
        
        print(f"[ParkingSystem] Initialisé : {places_totales} places, {tarif_horaire}€/h.")

    def _construire_automate(self):
        """Définit les états et transitions spécifiques au Parking (Projet 8)."""
        # 1. Création des États
        etats = [
            Etat(0, "DISPONIBLE", "initial"),
            Etat(1, "IDENTIFICATION"),
            Etat(2, "VERIFICATION_ACCES"),
            Etat(3, "BARRIERE_ENTREE_OUVERTE"),
            Etat(4, "STATIONNEMENT_EN_COURS"), # État virtuel pour le départ d'une voiture
            Etat(5, "CALCUL_TARIF"),
            Etat(6, "ATTENTE_PAIEMENT"),
            Etat(7, "BARRIERE_SORTIE_OUVERTE"),
            Etat(99, "COMPLET")
        ]
        
        for e in etats:
            self.automate.ajouter_etat(e)

        # 2. Définition des Transitions (CORRIGÉ POUR BOUCLER)
        # Séquence d'Entrée
        self.automate.ajouter_transition(0, 1, "detecter_entree")
        self.automate.ajouter_transition(1, 2, "lire_plaque")
        self.automate.ajouter_transition(2, 3, "acces_valide")
        # MODIFICATION ICI : Une fois entré, on retourne à DISPONIBLE (0) pour la prochaine voiture
        self.automate.ajouter_transition(3, 0, "vehicule_entre") 
        
        # Gestion Saturation
        self.automate.ajouter_transition(0, 99, "parking_plein")
        self.automate.ajouter_transition(99, 0, "place_liberee")
        
        # Séquence de Sortie (Démarre artificiellement de l'état 4)
        self.automate.ajouter_transition(4, 5, "demande_sortie")
        self.automate.ajouter_transition(5, 6, "paiement_requis")
        self.automate.ajouter_transition(5, 7, "abonne_gratuit") # Bypass paiement
        self.automate.ajouter_transition(6, 7, "paiement_valide")
        self.automate.ajouter_transition(7, 0, "vehicule_sorti")

    def get_status(self):
        """Renvoie l'état courant pour l'interface graphique"""
        etat_label = self.automate.etat_courant.label_etat
        # Si l'automate est revenu à 0 mais qu'on est plein, on affiche COMPLET visuellement
        if self.places_libres == 0: 
            etat_label = "COMPLET"
            
        return {
            "etat_automate": etat_label,
            "places_libres": self.places_libres,
            "places_totales": self.places_totales
        }

    def gerer_entree(self):
        """Simule le processus complet d'entrée d'un véhicule."""
        print("\n--- TENTATIVE D'ENTREE ---")
        
        # Si on était bloqué sur l'état virtuel COMPLET, on reset si de la place s'est libérée
        if self.places_libres > 0 and self.automate.etat_courant.id_etat == 99:
             self.automate.transition("place_liberee")

        # Vérification métier
        if self.places_libres > 0:
            succes = self.automate.transition("detecter_entree")
            if succes:
                # Simulation rapide des étapes intermédiaires
                self.automate.transition("lire_plaque")
                self.automate.transition("acces_valide")
                self.automate.transition("vehicule_entre") # Retourne à 0 (DISPONIBLE)
                
                self.places_libres -= 1
                print(f"[Succès] Véhicule garé. Places restantes: {self.places_libres}")
                
                # Si le parking devient plein juste après cette entrée
                if self.places_libres == 0:
                    print("[Alerte] Le parking est maintenant COMPLET.")
                    self.automate.transition("parking_plein")
            else:
                print(f"[Info] Système occupé ou état incorrect ({self.automate.etat_courant.label_etat}).")
        else:
            print("[Refus] Parking COMPLET. Barrière reste fermée.")
            # Si l'automate n'est pas déjà sur COMPLET, on le force
            if self.automate.etat_courant.id_etat != 99:
                self.automate.transition("parking_plein")

    def gerer_sortie(self, est_abonne=False):
        """Simule le processus complet de sortie."""
        print(f"\n--- TENTATIVE DE SORTIE (Abonné: {est_abonne}) ---")
        
        # ASTUCE SIMULATION : On téléporte l'automate à l'état 4 pour commencer la sortie
        # (Car dans la réalité, c'est un automate parallèle ou une autre borne)
        self.automate.etat_courant = self.automate.list_etats[4]
        
        self.automate.transition("demande_sortie")
        
        if est_abonne:
            print("[Système] Abonné détecté : Sortie gratuite.")
            self.automate.transition("abonne_gratuit")
        else:
            print("[Système] Visiteur : Paiement requis.")
            self.automate.transition("paiement_requis")
            self.automate.transition("paiement_valide")
            
        self.automate.transition("vehicule_sorti")
        self.places_libres += 1
        print(f"[Succès] Véhicule parti. Places restantes: {self.places_libres}")
        
        # Si le parking était complet, il redevient disponible
        # Note: L'automate est déjà revenu à 0 via "vehicule_sorti"
        if self.places_libres == 1:
            print("[Info] Parking n'est plus complet.")