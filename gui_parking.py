import sys
import random
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, QPushButton, 
                             QTextEdit, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QFont

# Importation de votre logique métier
from parking_system import ParkingSystem

# --- WORKER (INTIELLIGENCE ET MÉMOIRE) ---
class ParkingWorker(QObject):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    # int=index, int=status_code (1=Vert, 0=Rouge, -1=Orange)
    update_grid_signal = pyqtSignal(int, int) 

    def __init__(self, places_totales=10):
        super().__init__()
        self.system = ParkingSystem(places_totales=places_totales)
        # MODIFICATION : On stocke le TYPE de client (ou None si libre)
        # Exemple : [None, "VISITEUR", "ABONNE", None, ...]
        self.occupation_map = [None] * places_totales 

    def log(self, message):
        self.log_signal.emit(message)
        print(message)

    def entree_auto(self, est_abonne):
        """Gère l'entrée et mémorise le type de client"""
        if self.system.places_libres > 0:
            try:
                # 1. Trouver la première place vide (celle qui est None)
                idx = self.occupation_map.index(None)
                
                # 2. Mémoriser qui se gare
                type_client = "ABONNE" if est_abonne else "VISITEUR"
                self.occupation_map[idx] = type_client # <--- C'est ici qu'on sauvegarde l'info
                
                # 3. Appeler la logique métier (Backend)
                self.log(f"--- 🚗 Nouvelle voiture ({type_client}) ---")
                self.system.gerer_entree()
                
                # 4. Mettre à jour l'interface (ROUGE)
                self.update_grid_signal.emit(idx, 0)
                self.update_status()
            except ValueError:
                self.log("[Erreur] Incohérence interne des places.")
        else:
            self.system.gerer_entree() # Déclenchera le message COMPLET
            self.update_status()

    def sortie_auto(self):
        """Fait sortir une voiture en utilisant ses VRAIES informations"""
        # 1. Trouver les places qui ne sont PAS None
        indices_occupes = [i for i, x in enumerate(self.occupation_map) if x is not None]
        
        if not indices_occupes:
            self.log("[Erreur] Le parking est vide !")
            return

        # 2. Choisir une voiture au hasard parmi celles présentes
        idx_a_liberer = random.choice(indices_occupes)
        
        # 3. RÉCUPÉRER L'IDENTITÉ RÉELLE (Plus de random ici !)
        type_stocke = self.occupation_map[idx_a_liberer]
        est_abonne = (type_stocke == "ABONNE")

        # 4. PHASE 1 : DÉBUT PROCÉDURE (VISUEL ORANGE)
        montant = "0.00 DH" if est_abonne else "15.00 DH"
        nom_affiche = "Abonné" if est_abonne else "Visiteur"
        
        self.log(f"--- 🛑 Départ demandé Place P-{idx_a_liberer+1} ({nom_affiche}) ---")
        
        if est_abonne:
            self.log(f"--- 🎫 Badge abonné détecté. Sortie gratuite. ---")
        else:
            self.log(f"--- 💳 Ticket visiteur. Paiement de {montant} en cours... ---")
        
        # Mettre la case en Orange (-1)
        self.update_grid_signal.emit(idx_a_liberer, -1) 

        # 5. PHASE 2 : FINALISATION APRÈS 2 SECONDES
        QTimer.singleShot(2000, lambda: self._finaliser_sortie(idx_a_liberer, est_abonne))

    def _finaliser_sortie(self, idx, est_abonne):
        """Libère la place et efface la mémoire"""
        # Appel Backend
        self.system.gerer_sortie(est_abonne=est_abonne)
        
        # IMPORTANT : On remet la mémoire à None pour cette place
        self.occupation_map[idx] = None
        
        # Mise à jour visuelle (VERT)
        self.update_grid_signal.emit(idx, 1)
        self.update_status()
        self.log(f"--- ✅ Barrière ouverte. Place P-{idx+1} libérée. ---")

    def update_status(self):
        status = self.system.get_status()
        self.status_signal.emit(status["etat_automate"])


# --- FENÊTRE PRINCIPALE (Interface inchangée, juste le style) ---
class ParkingDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Projet 8 - Parking Intelligent (Simulation)")
        self.setGeometry(100, 100, 1100, 650)
        self.setStyleSheet("background-color: #2b2b2b; color: white;")
        
        self.worker = ParkingWorker(places_totales=10)
        
        self.worker.log_signal.connect(self.append_log)
        self.worker.status_signal.connect(self.update_header)
        self.worker.update_grid_signal.connect(self.update_place)
        
        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # HEADER
        header = QHBoxLayout()
        title = QLabel("SYSTEME DE GESTION DE PARKING")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet("color: #3498db;")
        
        self.lbl_status = QLabel("DISPONIBLE")
        self.lbl_status.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.lbl_status.setStyleSheet("background-color: #2ecc71; color: white; padding: 8px 20px; border-radius: 5px;")
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(QLabel("ÉTAT SYSTÈME : "))
        header.addWidget(self.lbl_status)
        layout.addLayout(header)

        # GRILLE
        grid_frame = QFrame()
        grid_frame.setStyleSheet("background-color: #383838; border-radius: 10px; margin-top: 10px;")
        grid_layout = QGridLayout(grid_frame)
        self.places_widgets = []

        for i in range(10):
            lbl = QLabel(f"P-{i+1}\nLIBRE")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedSize(120, 90)
            lbl.setFont(QFont("Arial", 11, QFont.Bold))
            lbl.setStyleSheet("background-color: #2ecc71; color: white; border: 2px solid #27ae60; border-radius: 8px;")
            
            row = i // 5
            col = i % 5
            grid_layout.addWidget(lbl, row, col)
            self.places_widgets.append(lbl)
            
        layout.addWidget(grid_frame)

        # PANNEAU BAS
        bottom_panel = QHBoxLayout()
        
        # Contrôles
        ctrl_layout = QVBoxLayout()
        btn_style = """
            QPushButton { background-color: #34495e; color: white; padding: 15px; font-weight: bold; border-radius: 5px; font-size: 14px; border: 1px solid #555; }
            QPushButton:hover { background-color: #435c75; }
            QPushButton:pressed { background-color: #2c3e50; }
        """
        
        btn_visiteur = QPushButton("🚙 Entrée Visiteur")
        btn_visiteur.setStyleSheet(btn_style.replace("#34495e", "#3498db"))
        btn_visiteur.clicked.connect(lambda: self.worker.entree_auto(False))
        
        btn_abonne = QPushButton("💳 Entrée Abonné")
        btn_abonne.setStyleSheet(btn_style.replace("#34495e", "#9b59b6"))
        btn_abonne.clicked.connect(lambda: self.worker.entree_auto(True))
        
        btn_sortie = QPushButton("🚪 Sortie Aléatoire")
        btn_sortie.setStyleSheet(btn_style.replace("#34495e", "#e67e22"))
        btn_sortie.clicked.connect(self.worker.sortie_auto)

        ctrl_layout.addWidget(QLabel("SIMULATION ENTREE"))
        ctrl_layout.addWidget(btn_visiteur)
        ctrl_layout.addWidget(btn_abonne)
        ctrl_layout.addSpacing(15)
        ctrl_layout.addWidget(QLabel("SIMULATION SORTIE"))
        ctrl_layout.addWidget(btn_sortie)
        ctrl_layout.addStretch()
        
        # Logs
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setStyleSheet("QTextEdit { background-color: #1e1e1e; color: #2ecc71; font-family: Consolas; font-size: 12px; border: 1px solid #555; border-radius: 5px; }")
        
        bottom_panel.addLayout(ctrl_layout, 1)
        bottom_panel.addWidget(self.txt_logs, 2)
        layout.addLayout(bottom_panel)

    def append_log(self, text):
        self.txt_logs.append(text)
        self.txt_logs.verticalScrollBar().setValue(self.txt_logs.verticalScrollBar().maximum())

    def update_header(self, status_text):
        self.lbl_status.setText(status_text)
        if status_text == "COMPLET":
            self.lbl_status.setStyleSheet("background-color: #e74c3c; color: white; padding: 8px 20px; border-radius: 5px;")
        else:
            self.lbl_status.setStyleSheet("background-color: #2ecc71; color: white; padding: 8px 20px; border-radius: 5px;")

    def update_place(self, index, status_code):
        lbl = self.places_widgets[index]
        if status_code == 1: # VERT
            lbl.setText(f"P-{index+1}\nLIBRE")
            lbl.setStyleSheet("background-color: #2ecc71; color: white; border: 2px solid #27ae60; border-radius: 8px;")
        elif status_code == 0: # ROUGE
            lbl.setText(f"P-{index+1}\nOCCUPÉ")
            lbl.setStyleSheet("background-color: #e74c3c; color: white; border: 2px solid #c0392b; border-radius: 8px;")
        elif status_code == -1: # ORANGE
            lbl.setText(f"P-{index+1}\nPAIEMENT...")
            lbl.setStyleSheet("background-color: #f39c12; color: white; border: 2px solid #d35400; border-radius: 8px;")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ParkingDashboard()
    window.show()
    sys.exit(app.exec_())