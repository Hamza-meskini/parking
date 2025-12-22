import sys
import random
import time
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, QPushButton, 
                             QTextEdit, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QFont

from parking_system import ParkingSystem

# --- CLASS 1 : WORKER (Gestion Logique & Animation) ---
class ParkingWorker(QObject):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(dict) 
    update_grid_signal = pyqtSignal(int, int) # int=index, int=status (-1, 0, 1)

    def __init__(self, places_totales=10):
        super().__init__()
        self.system = ParkingSystem(places_totales=places_totales)
        self.occupation_map = [None] * places_totales 

    def log(self, message):
        self.log_signal.emit(message)
        print(message)

    def _animation_step(self):
        """Callback magique pour animer le graphe étape par étape"""
        self.update_status()          
        QApplication.processEvents()  # Force le rafraîchissement immédiat
        time.sleep(0.8)               # Pause visible

    def entree_auto(self, est_abonne):
        if self.system.places_libres > 0:
            try:
                idx = self.occupation_map.index(None)
                type_client = "ABONNE" if est_abonne else "VISITEUR"
                
                # Animation de l'entrée (le graphe va bouger)
                self.system.gerer_entree(est_abonne=est_abonne, pause_callback=self._animation_step)
                
                self.occupation_map[idx] = type_client
                self.log(f"--- 🚗 Entrée {type_client} (Place P-{idx+1}) ---")
                
                self.update_grid_signal.emit(idx, 0) # Rouge
                self.update_status()
            except ValueError:
                self.log("Erreur interne place.")
        else:
            self.system.gerer_entree(est_abonne) 
            self.update_status()

    def sortie_auto(self):
        indices_occupes = [i for i, x in enumerate(self.occupation_map) if x is not None]
        if not indices_occupes:
            self.log("[Erreur] Le parking est vide !")
            return

        idx = random.choice(indices_occupes)
        type_stocke = self.occupation_map[idx]
        est_abonne = (type_stocke == "ABONNE")

        nom = "Abonné" if est_abonne else "Visiteur"
        prix = "0.00 DH" if est_abonne else "15.00 DH"
        
        self.log(f"--- 🛑 Sortie P-{idx+1} ({nom}). Facture: {prix} ---")
        self.update_grid_signal.emit(idx, -1) # Orange (Paiement)

        # Petit délai pour laisser l'utilisateur voir la case orange
        QTimer.singleShot(500, lambda: self._finaliser_sortie(idx, est_abonne))

    def _finaliser_sortie(self, idx, est_abonne):
        # Lancement de la logique avec animation
        self.system.gerer_sortie(est_abonne=est_abonne, pause_callback=self._animation_step)
        
        self.occupation_map[idx] = None
        self.update_grid_signal.emit(idx, 1) # Vert
        self.update_status()
        self.log("--- ✅ Barrière ouverte ---")

    def update_status(self):
        self.status_signal.emit(self.system.get_status())


# --- CLASS 2 : FENÊTRE GRAPHIQUE (Layout Schéma Officiel) ---
class GraphWindow(QWidget):
    def __init__(self, automate):
        super().__init__()
        self.setWindowTitle("Moniteur Temps Réel (Automate)")
        self.setGeometry(1150, 50, 1100, 700)
        self.automate = automate
        
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        self.figure = Figure(figsize=(12, 8), facecolor='#2b2b2b')
        self.canvas = FigureCanvas(self.figure)
        main_layout.addWidget(self.canvas)
        
        btn_layout = QPushButton("Réinitialiser Vue (Schéma Rectangulaire)")
        btn_layout.setStyleSheet("background-color: #34495e; color: white; padding: 8px;")
        btn_layout.clicked.connect(lambda: self.update_layout(force_manual=True))
        main_layout.addWidget(btn_layout)
        
        self.G = nx.DiGraph()
        self.pos = None
        
        # Noms d'affichage conformes au schéma demandé
        self.labels_map = {
            "DISPONIBLE": "1. DISPO-\nNIBLE",
            "IDENTIFICATION": "2. IDENTI-\nFICATION",
            "VERIFICATION_ACCES": "3. VERIF\nACCÈS",
            "BARRIERE_ENTREE_OUVERTE": "4. BARRIÈRE\nOUVERTE",
            "STATIONNEMENT": "5. VÉHICULE\nGARÉ",
            "CALCUL_TARIF": "6. CALCUL\nTARIF",
            "ATTENTE_PAIEMENT": "7. ATTENTE\nPAIEMENT",
            "BARRIERE_SORTIE_OUVERTE": "8. BARRIÈRE\nSORTIE",
            "COMPLET": "COMPLET"
        }
        
        self._construire_structure()
        self.update_layout(force_manual=True)

    def _construire_structure(self):
        for id_etat, etat in self.automate.list_etats.items():
            self.G.add_node(etat.label_etat)
            
        for transition in self.automate.list_transitions:
            src = transition.etat_source.label_etat
            dst = transition.etat_dest.label_etat
            
            lbl = transition.etiquette \
                .replace("vehicule_", "").replace("barriere_", "").replace("detecter_", "") \
                .replace("demande_", "").replace("paiement_", "").replace("abonne_", "abonne")
            
            if src == "BARRIERE_SORTIE_OUVERTE" and dst == "DISPONIBLE":
                lbl = "sorti / place_libérée"
                
            self.G.add_edge(src, dst, label=lbl)

    def update_layout(self, force_manual=True):
        if force_manual:
            # COORDONNÉES EXACTES DU RECTANGLE (X, Y)
            self.pos = {
                "COMPLET":                  (0.5, 3.0),
                "DISPONIBLE":               (0.5, 2.0),
                "IDENTIFICATION":           (2.5, 2.0),
                "VERIFICATION_ACCES":       (4.5, 2.0),
                "BARRIERE_ENTREE_OUVERTE":  (6.5, 2.0),
                "STATIONNEMENT":            (6.5, 0.5),
                "CALCUL_TARIF":             (4.5, 0.5),
                "ATTENTE_PAIEMENT":         (2.5, 0.5),
                "BARRIERE_SORTIE_OUVERTE":  (0.5, 0.5)
            }
        else:
            self.pos = nx.spring_layout(self.G)
        self.draw_graph("DISPONIBLE")

    def draw_graph(self, current_label):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#2b2b2b')

        node_colors = []
        edge_colors_list = []
        
        for node in self.G.nodes():
            if node == current_label:
                node_colors.append('#e74c3c') # Rouge vif (Actif)
                edge_colors_list.append('#c0392b')
            elif node == "COMPLET":
                node_colors.append('#ffcccc') # Rose
                edge_colors_list.append('red')
            elif node == "STATIONNEMENT":
                node_colors.append('#ccffcc') # Vert clair
                edge_colors_list.append('green')
            elif "BARRIERE" in node:
                node_colors.append('#ccccff') # Bleu clair
                edge_colors_list.append('blue')
            else:
                node_colors.append('#eeeeee') # Blanc
                edge_colors_list.append('#bdc3c7')

        # Noeuds
        nx.draw_networkx_nodes(self.G, self.pos, ax=ax, node_color=node_colors, 
                               edgecolors=edge_colors_list, linewidths=2, node_size=5000)
        # Labels
        nx.draw_networkx_labels(self.G, self.pos, ax=ax, labels=self.labels_map,
                                font_size=9, font_color="black", font_weight="bold", font_family="Arial")
        # Flèches
        nx.draw_networkx_edges(self.G, self.pos, ax=ax, edge_color='#ecf0f1', 
                               arrows=True, arrowsize=25, width=1.5, 
                               connectionstyle='arc3,rad=0.0', min_source_margin=25, min_target_margin=25)
        # Texte Flèches
        edge_labels = nx.get_edge_attributes(self.G, 'label')
        nx.draw_networkx_edge_labels(self.G, self.pos, edge_labels=edge_labels, 
                                     font_color='#f39c12', font_size=8, ax=ax, rotate=False,
                                     bbox=dict(facecolor='#2b2b2b', edgecolor='none', alpha=0.6))

        ax.set_title(f"ÉTAT ACTIF : {self.labels_map.get(current_label, current_label).replace(chr(10), ' ')}", 
                     color="white", fontsize=16, fontweight='bold', pad=20)
        ax.set_xlim(-1, 8)
        ax.set_ylim(-0.5, 4)
        ax.axis('off')
        self.canvas.draw()


# --- CLASS 3 : DASHBOARD PRINCIPAL ---
class ParkingDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Projet 8 - Dashboard Financier & Technique")
        self.setGeometry(100, 100, 1100, 750)
        self.setStyleSheet("background-color: #2b2b2b; color: white;")
        
        self.worker = ParkingWorker(places_totales=10)
        self.worker.log_signal.connect(self.append_log)
        self.worker.status_signal.connect(self.update_dashboard)
        self.worker.update_grid_signal.connect(self.update_place)
        
        self.init_ui()

    def init_ui(self):
        main = QWidget()
        self.setCentralWidget(main)
        layout = QVBoxLayout(main)

        # HEADER & KPI
        kpi_layout = QHBoxLayout()
        self.card_money = self.create_kpi_card("RECETTES TOTALES", "0.00 DH", "#f1c40f")
        self.card_visit = self.create_kpi_card("VISITEURS", "0", "#3498db")
        self.card_sub = self.create_kpi_card("ABONNÉS", "0", "#9b59b6")
        
        self.lbl_system_status = QLabel("DISPONIBLE")
        self.lbl_system_status.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.lbl_system_status.setStyleSheet("background-color: #2ecc71; padding: 10px; border-radius: 5px;")
        
        kpi_layout.addWidget(self.card_money)
        kpi_layout.addWidget(self.card_visit)
        kpi_layout.addWidget(self.card_sub)
        kpi_layout.addStretch()
        kpi_layout.addWidget(QLabel("ÉTAT :"))
        kpi_layout.addWidget(self.lbl_system_status)
        layout.addLayout(kpi_layout)

        # GRILLE
        grid_frame = QFrame()
        grid_frame.setStyleSheet("background-color: #383838; border-radius: 10px; margin: 10px 0;")
        grid_layout = QGridLayout(grid_frame)
        self.places_widgets = []

        for i in range(10):
            lbl = QLabel(f"P-{i+1}\nLIBRE")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedSize(100, 80)
            lbl.setFont(QFont("Arial", 10, QFont.Bold))
            lbl.setStyleSheet("background-color: #2ecc71; color: white; border-radius: 8px;")
            grid_layout.addWidget(lbl, i//5, i%5)
            self.places_widgets.append(lbl)
            
        layout.addWidget(grid_frame)

        # CONTROLES
        bottom = QHBoxLayout()
        btns = QVBoxLayout()
        
        b_visiteur = QPushButton("Ticket Visiteur")
        b_visiteur.setStyleSheet("background-color: #3498db; padding: 15px; font-weight: bold;")
        b_visiteur.clicked.connect(lambda: self.worker.entree_auto(False))
        
        b_abonne = QPushButton("Badge Abonné")
        b_abonne.setStyleSheet("background-color: #9b59b6; padding: 15px; font-weight: bold;")
        b_abonne.clicked.connect(lambda: self.worker.entree_auto(True))
        
        b_sortie = QPushButton("Sortie Aléatoire")
        b_sortie.setStyleSheet("background-color: #e67e22; padding: 15px; font-weight: bold;")
        b_sortie.clicked.connect(self.worker.sortie_auto)
        
        b_graph = QPushButton("Voir Automate (Graphe)")
        b_graph.setStyleSheet("background-color: #7f8c8d; padding: 15px; font-weight: bold; border: 1px solid white;")
        b_graph.clicked.connect(self.open_graph_window)
        
        btns.addWidget(b_visiteur)
        btns.addWidget(b_abonne)
        btns.addSpacing(10)
        btns.addWidget(b_sortie)
        btns.addSpacing(10)
        btns.addWidget(b_graph)
        btns.addStretch()
        
        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setStyleSheet("background-color: #222; color: #0f0; font-family: Consolas;")
        
        bottom.addLayout(btns, 1)
        bottom.addWidget(self.logs, 2)
        layout.addLayout(bottom)

    def create_kpi_card(self, title, value, color):
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {color}; border-radius: 8px; color: black;")
        frame.setFixedSize(180, 80)
        vbox = QVBoxLayout(frame)
        l_title = QLabel(title)
        l_title.setFont(QFont("Arial", 8, QFont.Bold))
        l_title.setStyleSheet("color: #333;")
        l_val = QLabel(value)
        l_val.setFont(QFont("Arial", 18, QFont.Bold))
        l_val.setAlignment(Qt.AlignCenter)
        vbox.addWidget(l_title)
        vbox.addWidget(l_val)
        return frame

    def open_graph_window(self):
        self.graph_window = GraphWindow(self.worker.system.automate)
        self.graph_window.show()

    def update_dashboard(self, stats):
        # KPIs avec findChildren corrigé
        val_money = stats.get("recettes", 0.0)
        self.card_money.findChildren(QLabel, "", Qt.FindDirectChildrenOnly)[1].setText(f"{val_money:.2f} DH")
        self.card_visit.findChildren(QLabel, "", Qt.FindDirectChildrenOnly)[1].setText(str(stats.get("visiteurs", 0)))
        self.card_sub.findChildren(QLabel, "", Qt.FindDirectChildrenOnly)[1].setText(str(stats.get("abonnes", 0)))
        
        # État Header
        lbl_etat = stats.get("etat_automate", "???")
        self.lbl_system_status.setText(lbl_etat)
        if lbl_etat == "COMPLET":
             self.lbl_system_status.setStyleSheet("background-color: #e74c3c; padding: 10px; border-radius: 5px;")
        else:
             self.lbl_system_status.setStyleSheet("background-color: #2ecc71; padding: 10px; border-radius: 5px;")
        
        # Mise à jour Graphe
        if hasattr(self, 'graph_window') and self.graph_window.isVisible():
            self.graph_window.draw_graph(lbl_etat)

    def append_log(self, text):
        self.logs.append(text)
        self.logs.verticalScrollBar().setValue(self.logs.verticalScrollBar().maximum())

    def update_place(self, idx, status):
        l = self.places_widgets[idx]
        if status == 1:
            l.setStyleSheet("background-color: #2ecc71; color: white; border-radius: 8px;")
            l.setText(f"P-{idx+1}\nLIBRE")
        elif status == 0:
            l.setStyleSheet("background-color: #e74c3c; color: white; border-radius: 8px;")
            l.setText(f"P-{idx+1}\nOCCUPÉ")
        elif status == -1:
            l.setStyleSheet("background-color: #f39c12; color: white; border-radius: 8px;")
            l.setText(f"P-{idx+1}\nPAIEMENT")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ParkingDashboard()
    window.show()
    sys.exit(app.exec_())