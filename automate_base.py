from typing import Dict, List, Optional


class Etat:
    """
    Représente un état dans l'automate fini.
    
    Attributes:
        id_etat: Identifiant unique de l'état
        label_etat: Nom lisible de l'état
        type_etat: Type d'état ("initial", "final", "normal", "puits")
        transitions: Dictionnaire des transitions possibles {événement: id_destination}
    """
    
    def __init__(self, id_etat: int, label_etat: str, type_etat: str = "normal") -> None:
        self.id_etat = id_etat
        self.label_etat = label_etat
        self.type_etat = type_etat
        self.transitions: Dict[str, int] = {}

    def __repr__(self) -> str:
        return f"Etat({self.id_etat}: {self.label_etat} [{self.type_etat}])"


class Transition:
    """
    Représente le passage d'un état à un autre via un événement.
    
    Attributes:
        etat_source: État de départ
        etat_dest: État d'arrivée
        etiquette: Événement déclencheur de la transition
    """
    
    def __init__(self, etat_source: Etat, etat_dest: Etat, etiquette: str) -> None:
        self.etat_source = etat_source
        self.etat_dest = etat_dest
        self.etiquette = etiquette


class Automate:
    """
    Moteur générique de l'automate à états finis.
    
    Attributes:
        list_etats: Dictionnaire des états {id: Etat}
        list_transitions: Liste de toutes les transitions
        etat_courant: État actuel du système
    """
    
    def __init__(self) -> None:
        self.list_etats: Dict[int, Etat] = {}
        self.list_transitions: List[Transition] = []
        self.etat_courant: Optional[Etat] = None

    def ajouter_etat(self, etat: Etat) -> None:
        """
        Enregistre un nouvel état dans le système.
        
        Args:
            etat: L'objet Etat à ajouter
        """
        self.list_etats[etat.id_etat] = etat
        if etat.type_etat == "initial":
            self.etat_courant = etat
            print(f"[Automate] État initial défini: {etat.label_etat}")

    def ajouter_transition(self, id_src: int, id_dst: int, evt: str) -> None:
        """
        Crée une transition logique entre deux états existants.
        
        Args:
            id_src: ID de l'état source
            id_dst: ID de l'état destination
            evt: Événement déclencheur
        """
        if id_src in self.list_etats and id_dst in self.list_etats:
            src = self.list_etats[id_src]
            dst = self.list_etats[id_dst]
            
            nouvelle_trans = Transition(src, dst, evt)
            self.list_transitions.append(nouvelle_trans)
            
            src.transitions[evt] = id_dst
        else:
            print(f"[Erreur] État source {id_src} ou destination {id_dst} inexistant.")

    def transition(self, evt: str) -> bool:
        """
        Tente d'exécuter une transition basée sur l'événement donné.
        
        Args:
            evt: Événement déclencheur
            
        Returns:
            True si le changement d'état a eu lieu, False sinon
        """
        if self.etat_courant and evt in self.etat_courant.transitions:
            dst_id = self.etat_courant.transitions[evt]
            ancien_etat = self.etat_courant
            nouveau_etat = self.list_etats[dst_id]
            
            self.etat_courant = nouveau_etat
            print(f"[Transition] '{evt}': {ancien_etat.label_etat} -> {nouveau_etat.label_etat}")
            return True
        else:
            print(f"[Bloqué] Événement '{evt}' impossible depuis l'état '{self.etat_courant.label_etat}'")
            return False
