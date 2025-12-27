from typing import Optional, Callable
from automate_base import Automate, Etat


# Constantes de configuration
PLACES_TOTALES_DEFAULT = 10
TARIF_HORAIRE_DEFAULT = 2.5


class ParkingSystem:
    """
    Système de gestion de parking intelligent avec automate à états finis.
    
    Gère les entrées/sorties de véhicules, le calcul des tarifs, et les transitions
    d'états du système de parking.
    
    Attributes:
        places_totales: Nombre total de places disponibles
        places_libres: Nombre de places actuellement libres
        tarif_horaire: Tarif horaire pour les visiteurs
        recettes_totales: Montant total des recettes
        total_visiteurs: Nombre total de visiteurs accueillis
        total_abonnes: Nombre total d'abonnés accueillis
        automate: Instance de l'automate à états finis
    """
    
    def __init__(self, places_totales: int = PLACES_TOTALES_DEFAULT, 
                 tarif_horaire: float = TARIF_HORAIRE_DEFAULT) -> None:
        self.places_totales = places_totales
        self.places_libres = places_totales
        self.tarif_horaire = tarif_horaire
        
        self.recettes_totales = 0.0
        self.total_visiteurs = 0
        self.total_abonnes = 0
        
        self.automate = Automate()
        self._construire_automate()
        print(f"[ParkingSystem] Initialisé : {places_totales} places.")

    def _construire_automate(self) -> None:
        """Construit la structure de l'automate à états finis."""
        etats = [
            Etat(0, "DISPONIBLE", "initial"),
            Etat(1, "IDENTIFICATION"),
            Etat(2, "VERIFICATION_ACCES"),
            Etat(3, "BARRIERE_ENTREE_OUVERTE"),
            Etat(4, "STATIONNEMENT"),
            Etat(5, "CALCUL_TARIF"),
            Etat(6, "ATTENTE_PAIEMENT"),
            Etat(7, "BARRIERE_SORTIE_OUVERTE"),
            Etat(99, "COMPLET")
        ]
        for e in etats:
            self.automate.ajouter_etat(e)

        # Transitions d'entrée
        self.automate.ajouter_transition(0, 1, "detecter_entree")
        self.automate.ajouter_transition(1, 2, "lire_plaque")
        self.automate.ajouter_transition(2, 3, "acces_valide")
        self.automate.ajouter_transition(3, 4, "vehicule_entre")
        
        # Transitions de sortie
        self.automate.ajouter_transition(4, 5, "demande_sortie")
        self.automate.ajouter_transition(5, 6, "paiement_requis")
        self.automate.ajouter_transition(5, 7, "abonne_gratuit")
        self.automate.ajouter_transition(6, 7, "paiement_valide")
        self.automate.ajouter_transition(7, 0, "vehicule_sorti")
        
        # Gestion saturation
        self.automate.ajouter_transition(0, 99, "parking_plein")
        self.automate.ajouter_transition(99, 0, "place_liberee")

    def get_status(self) -> dict:
        """
        Retourne l'état actuel du système.
        
        Returns:
            Dictionnaire contenant les statistiques du parking
        """
        etat_label = self.automate.etat_courant.label_etat
        if self.places_libres == 0:
            etat_label = "COMPLET"
            
        return {
            "etat_automate": etat_label,
            "places_libres": self.places_libres,
            "places_totales": self.places_totales,
            "recettes": self.recettes_totales,
            "visiteurs": self.total_visiteurs,
            "abonnes": self.total_abonnes
        }

    def gerer_entree(self, est_abonne: bool = False, 
                     pause_callback: Optional[Callable] = None) -> None:
        """
        Gère l'entrée d'un véhicule dans le parking.
        
        Args:
            est_abonne: True si le véhicule est un abonné, False pour visiteur
            pause_callback: Fonction de callback pour animer les transitions
        """
        if est_abonne:
            self.total_abonnes += 1
        else:
            self.total_visiteurs += 1

        print("\n--- TENTATIVE D'ENTREE ---")
        if self.places_libres > 0:
            current_id = self.automate.etat_courant.id_etat
            if current_id == 99 or current_id == 4:
                self.automate.etat_courant = self.automate.list_etats[0]

            if self.automate.transition("detecter_entree"):
                if pause_callback:
                    pause_callback()
                
                self.automate.transition("lire_plaque")
                if pause_callback:
                    pause_callback()
                
                self.automate.transition("acces_valide")
                if pause_callback:
                    pause_callback()
                
                self.automate.transition("vehicule_entre")
                
                self.places_libres -= 1
                print(f"[Succès] Véhicule garé. Places restantes: {self.places_libres}")
                
                if self.places_libres == 0:
                    self.automate.etat_courant = self.automate.list_etats[0]
                    self.automate.transition("parking_plein")
        else:
            print("[Refus] Parking COMPLET.")
            if self.automate.etat_courant.id_etat != 99:
                self.automate.transition("parking_plein")

    def gerer_sortie(self, est_abonne: bool = False, 
                     pause_callback: Optional[Callable] = None, 
                     montant: float = 15.0) -> None:
        """
        Gère la sortie d'un véhicule du parking.
        
        Args:
            est_abonne: True si le véhicule est un abonné, False pour visiteur
            pause_callback: Fonction de callback pour animer les transitions
            montant: Montant à payer (ignoré pour les abonnés)
        """
        print(f"\n--- SORTIE (Abonné: {est_abonne}) ---")
        
        self.automate.etat_courant = self.automate.list_etats[4]
        
        self.automate.transition("demande_sortie")
        if pause_callback:
            pause_callback()
        
        if est_abonne:
            self.automate.transition("abonne_gratuit")
            print(">> Gratuit (Abonné)")
            if pause_callback:
                pause_callback()
        else:
            self.automate.transition("paiement_requis")
            print(f">> Paiement requis ({montant:.2f} DH)...")
            if pause_callback:
                pause_callback()
            
            self.recettes_totales += montant
            
            self.automate.transition("paiement_valide")
            print(">> Paiement accepté")
            if pause_callback:
                pause_callback()
            
        self.automate.transition("vehicule_sorti")
        self.places_libres += 1
