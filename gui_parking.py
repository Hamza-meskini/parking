import sys
import random
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, QPushButton, 
                             QTextEdit, QFrame, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QFont, QColor

# Importation de votre logique métier
from parking_system import ParkingSystem

# --- WORKER (PONT ENTRE LOGIQUE ET GUI) ---
class ParkingWorker(QObject):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    update_grid_signal = pyqtSignal(int, bool) # int=index, bool=is_free

    def __init__(self, places_totales=10):
        super().__init__()
        self.system = ParkingSystem(places_totales=places_totales)
        self.occupation_map = [False] * places_totales  # False = Libre, True = Occupé

    def log(self, message):
        self.log_signal.emit(message)
        print(message) # Garder la trace dans la console aussi

    def entree_auto(self, est_abonne):
        """Gère l'entrée et met à jour l'interface"""
        if self.system.places_libres > 0:
            # 1. Trouver visuellement la première place libre
            try:
                idx = self.occupation_map.index(False)
                
                # 2. Appeler la logique métier
                self.log(f"--- Nouvelle voiture ({'Abonné' if est_abonne else 'Visiteur'}) ---")
                self.system.gerer_entree()
                
                # 3. Mettre à jour l'interface
                self.occupation_map[idx] = True
                self.update_grid_signal.emit(idx, False) # False = Devient Rouge
                self.update_status()
            except ValueError:
                self.log("[Erreur] Incohérence interne des places.")
        else:
            self.system.gerer_entree() # Déclenchera le message COMPLET
            self.update_status()

    def sortie_auto(self):
        """Choisit une voiture au hasard pour la faire sortir"""
        # Trouver tous les index occupés
        indices_occupes = [i for i, occupe in enumerate(self.occupation_map) if occupe]
        
        if not indices_occupes:
            self.log("[Erreur] Le parking est vide !")
            return

        # Choisir une voiture au hasard
        idx_a_liberer = random.choice(indices_occupes)
        est_abonne = random.choice([True, False]) # Simulation hasard type client

        self.log(f"--- Départ voiture Place P-{idx_a_liberer+1} ---")
        self.system.gerer_sortie(est_abonne=est_abonne)
        
        # Mise à jour visuelle
        self.occupation_map[idx_a_liberer] = False
        self.update_grid_signal.emit(idx_a_liberer, True) # True = Devient Vert
        self.update_status()

    def update_status(self):
        status = self.system.get_status()
        self.status_signal.emit(status["etat_automate"])


# --- FENÊTRE PRINCIPALE ---
class ParkingDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Projet 8 - Parking Intelligent (Simulation)")
        self.setGeometry(100, 100, 1000, 600)
        self.setStyleSheet("background-color: #2b2b2b; color: white;")
        
        self.worker = ParkingWorker(places_totales=10) # On simule 10 places
        
        # Connexions
        self.worker.log_signal.connect(self.append_log)
        self.worker.status_signal.connect(self.update_header)
        self.worker.update_grid_signal.connect(self.update_place)
        
        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # 1. HEADER
        header = QHBoxLayout()
        title = QLabel("SYSTEME DE GESTION DE PARKING")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet("color: #00aaff;")
        
        self.lbl_status = QLabel("DISPONIBLE")
        self.lbl_status.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.lbl_status.setStyleSheet("background-color: #2ecc71; color: white; padding: 5px 15px; border-radius: 5px;")
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(QLabel("ÉTAT SYSTÈME : "))
        header.addWidget(self.lbl_status)
        layout.addLayout(header)

        # 2. VISUALISATION (GRILLE)
        grid_frame = QFrame()
        grid_frame.setStyleSheet("background-color: #383838; border-radius: 10px;")
        grid_layout = QGridLayout(grid_frame)
        self.places_widgets = []

        # Création des 10 places
        for i in range(10):
            lbl = QLabel(f"P-{i+1}\nLIBRE")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedSize(100, 80)
            lbl.setFont(QFont("Arial", 10, QFont.Bold))
            lbl.setStyleSheet("background-color: #2ecc71; color: white; border: 2px solid #27ae60; border-radius: 8px;")
            
            row = i // 5
            col = i % 5
            grid_layout.addWidget(lbl, row, col)
            self.places_widgets.append(lbl)
            
        layout.addWidget(grid_frame)

        # 3. CONTRÔLES ET LOGS
        bottom_panel = QHBoxLayout()
        
        # Boutons
        ctrl_layout = QVBoxLayout()
        btn_style = """
            QPushButton { background-color: #3498db; color: white; padding: 12px; font-weight: bold; border-radius: 5px; font-size: 14px; }
            QPushButton:hover { background-color: #2980b9; }
        """
        
        btn_visiteur = QPushButton("🚙 Entrée Visiteur")
        btn_visiteur.setStyleSheet(btn_style)
        btn_visiteur.clicked.connect(lambda: self.worker.entree_auto(False))
        
        btn_abonne = QPushButton("💳 Entrée Abonné")
        btn_abonne.setStyleSheet(btn_style.replace("#3498db", "#9b59b6")) # Violet
        btn_abonne.clicked.connect(lambda: self.worker.entree_auto(True))
        
        btn_sortie = QPushButton("🚪 Sortie Aléatoire")
        btn_sortie.setStyleSheet(btn_style.replace("#3498db", "#e67e22")) # Orange
        btn_sortie.clicked.connect(self.worker.sortie_auto)

        ctrl_layout.addWidget(QLabel("SIMULATION ENTREE"))
        ctrl_layout.addWidget(btn_visiteur)
        ctrl_layout.addWidget(btn_abonne)
        ctrl_layout.addSpacing(20)
        ctrl_layout.addWidget(QLabel("SIMULATION SORTIE"))
        ctrl_layout.addWidget(btn_sortie)
        ctrl_layout.addStretch()
        
        # Logs
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: Consolas; border: 1px solid #555;")
        
        bottom_panel.addLayout(ctrl_layout, 1)
        bottom_panel.addWidget(self.txt_logs, 3)
        
        layout.addLayout(bottom_panel)

    def append_log(self, text):
        self.txt_logs.append(text)
        self.txt_logs.verticalScrollBar().setValue(self.txt_logs.verticalScrollBar().maximum())

    def update_header(self, status_text):
        self.lbl_status.setText(status_text)
        if status_text == "COMPLET":
            self.lbl_status.setStyleSheet("background-color: #e74c3c; color: white; padding: 5px 15px; border-radius: 5px;")
        else:
            self.lbl_status.setStyleSheet("background-color: #2ecc71; color: white; padding: 5px 15px; border-radius: 5px;")

    def update_place(self, index, is_free):
        lbl = self.places_widgets[index]
        if is_free:
            lbl.setText(f"P-{index+1}\nLIBRE")
            lbl.setStyleSheet("background-color: #2ecc71; color: white; border: 2px solid #27ae60; border-radius: 8px;")
        else:
            lbl.setText(f"P-{index+1}\nOCCUPÉ")
            lbl.setStyleSheet("background-color: #e74c3c; color: white; border: 2px solid #c0392b; border-radius: 8px;")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ParkingDashboard()
    window.show()
    sys.exit(app.exec_())