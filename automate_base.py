# automate_base.py

class Etat:
    """Représente un état dans l'automate fini."""
    def __init__(self, id_etat, label_etat, type_etat="normal"):
        self.id_etat = id_etat          # Identifiant unique (int)
        self.label_etat = label_etat    # Nom lisible (str)
        self.type_etat = type_etat      # "initial", "final", "normal", "puits"
        self.transitions = {}           # Dictionnaire {evenement: id_dest}

    def __repr__(self):
        return f"Etat({self.id_etat}: {self.label_etat} [{self.type_etat}])"

class Transition:
    """Représente le passage d'un état à un autre via un événement."""
    def __init__(self, etat_source, etat_dest, etiquette):
        self.etat_source = etat_source
        self.etat_dest = etat_dest
        self.etiquette = etiquette      # L'événement déclencheur

class Automate:
    """Moteur générique de l'automate à états finis."""
    def __init__(self):
        self.list_etats = {}       # Dictionnaire id -> Objet Etat
        self.list_transitions = [] # Liste des objets Transition
        self.etat_courant = None   # L'état actuel du système

    def ajouter_etat(self, etat):
        """Enregistre un nouvel état dans le système."""
        self.list_etats[etat.id_etat] = etat
        if etat.type_etat == "initial":
            self.etat_courant = etat
            print(f"[Automate] État initial défini: {etat.label_etat}")

    def ajouter_transition(self, id_src, id_dst, evt):
        """Crée une transition logique entre deux états existants."""
        if id_src in self.list_etats and id_dst in self.list_etats:
            src = self.list_etats[id_src]
            dst = self.list_etats[id_dst]
            
            # Création de l'objet Transition (pour archivage/graphe)
            nouvelle_trans = Transition(src, dst, evt)
            self.list_transitions.append(nouvelle_trans)
            
            # Mise à jour de la logique de l'état source
            src.transitions[evt] = id_dst
            # print(f"[Automate] Transition ajoutée: '{evt}': {src.label_etat} -> {dst.label_etat}")
        else:
            print(f"[Erreur] État source {id_src} ou destination {id_dst} inexistant.")

    def transition(self, evt):
        """
        Tente d'exécuter une transition basée sur l'événement donné.
        Retourne True si le changement d'état a eu lieu.
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