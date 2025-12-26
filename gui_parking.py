import sys
import random
import time
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, QPushButton, 
                             QTextEdit, QFrame, QStackedWidget)
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
        """Callback pour animer le graphe étape par étape"""
        self.update_status()          
        QApplication.processEvents()  
        time.sleep(0.8)               

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

        QTimer.singleShot(500, lambda: self._finaliser_sortie(idx, est_abonne))

    def _finaliser_sortie(self, idx, est_abonne):
        self.system.gerer_sortie(est_abonne=est_abonne, pause_callback=self._animation_step)
        self.occupation_map[idx] = None
        self.update_grid_signal.emit(idx, 1) # Vert
        self.update_status()
        self.log("--- ✅ Barrière ouverte ---")

    def update_status(self):
        self.status_signal.emit(self.system.get_status())


# --- CLASS 2 : WIDGET GRAPHE (Intégré) ---
class GraphWidget(QWidget):
    def __init__(self, automate):
        super().__init__()
        self.automate = automate
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0) # Pas de marges pour bien coller

        self.figure = Figure(facecolor='#2b2b2b')
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        self.G = nx.DiGraph()
        self.pos = None
        
        self.labels_map = {
            "DISPONIBLE": "1. DISPO-\nNIBLE", "IDENTIFICATION": "2. IDENTI-\nFICATION",
            "VERIFICATION_ACCES": "3. VERIF\nACCÈS", "BARRIERE_ENTREE_OUVERTE": "4. BARRIÈRE\nOUVERTE",
            "STATIONNEMENT": "5. VÉHICULE\nGARÉ", "CALCUL_TARIF": "6. CALCUL\nTARIF",
            "ATTENTE_PAIEMENT": "7. ATTENTE\nPAIEMENT", "BARRIERE_SORTIE_OUVERTE": "8. BARRIÈRE\nSORTIE",
            "COMPLET": "COMPLET"
        }
        
        self._construire_structure()
        self.update_layout(force_manual=True)

    def _construire_structure(self):
        for id_etat, etat in self.automate.list_etats.items():
            self.G.add_node(etat.label_etat)
        for t in self.automate.list_transitions:
            src, dst = t.etat_source.label_etat, t.etat_dest.label_etat
            lbl = t.etiquette.replace("vehicule_", "").replace("barriere_", "").replace("detecter_", "").replace("paiement_", "").replace("abonne_", "abonne")
            if src == "BARRIERE_SORTIE_OUVERTE" and dst == "DISPONIBLE": lbl = "sorti/libéré"
            self.G.add_edge(src, dst, label=lbl)

    def update_layout(self, force_manual=True):
        if force_manual:
            # Layout espacé pour grandes bulles
            self.pos = {
                "COMPLET": (0.5, 6.0), 
                "DISPONIBLE": (0.5, 3.0),
                "IDENTIFICATION": (3.5, 3.0), 
                "VERIFICATION_ACCES": (6.5, 3.0),
                "BARRIERE_ENTREE_OUVERTE": (9.5, 3.0), 
                "STATIONNEMENT": (9.5, 0.5),
                "CALCUL_TARIF": (6.5, 0.5), 
                "ATTENTE_PAIEMENT": (3.5, 0.5),
                "BARRIERE_SORTIE_OUVERTE": (0.5, 0.5)
            }
        else:
            self.pos = nx.spring_layout(self.G)
        self.draw_graph("DISPONIBLE")

    def draw_graph(self, current_label):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#2b2b2b')

        node_colors = []
        edge_colors = []
        for node in self.G.nodes():
            if node == current_label:
                node_colors.append('#e74c3c') # Rouge Actif
                edge_colors.append('#c0392b')
            elif node == "COMPLET":
                node_colors.append('#ffcccc')
                edge_colors.append('red')
            elif node == "STATIONNEMENT":
                node_colors.append('#ccffcc')
                edge_colors.append('green')
            elif "BARRIERE" in node:
                node_colors.append('#ccccff')
                edge_colors.append('blue')
            else:
                node_colors.append('#eeeeee')
                edge_colors.append('#bdc3c7')

        # 1. Enlarge Nodes & Borders
        nx.draw_networkx_nodes(self.G, self.pos, ax=ax, node_color=node_colors, 
                               edgecolors=edge_colors, linewidths=3, node_size=8000)

        # 2. Enhance Typography (Labels inside nodes)
        nx.draw_networkx_labels(self.G, self.pos, ax=ax, labels=self.labels_map, 
                                font_size=10, font_weight="bold", font_family="Arial")

        # 4. Refine Arrows (Larger width, arrowsize, and margins for borders)
        # min_source_margin et min_target_margin pour ne pas commencer sous le texte ou le bord
        nx.draw_networkx_edges(self.G, self.pos, ax=ax, edge_color='#ecf0f1', 
                               arrows=True, arrowsize=30, width=2.5, 
                               connectionstyle='arc3,rad=0.0',
                               min_source_margin=25, min_target_margin=25)
        
        # Titres des transitions plus grands
        edge_labels = nx.get_edge_attributes(self.G, 'label')
        nx.draw_networkx_edge_labels(self.G, self.pos, edge_labels=edge_labels, 
                                     font_color='#f39c12', font_size=9, ax=ax, 
                                     bbox=dict(facecolor='#2b2b2b', edgecolor='none', alpha=0.6))

        # 3. Optimize Layout Spacing (Title & Limits)
        ax.set_title(f"ÉTAT : {self.labels_map.get(current_label, current_label).replace(chr(10), ' ')}", 
                     color="white", fontsize=14, fontweight='bold')
        
        # Cadrage parfait pour le nouveau layout
        ax.set_xlim(-1, 11) 
        ax.set_ylim(-1, 8) 
        ax.axis('off')
        self.canvas.draw()


# --- CLASS 3 : DASHBOARD (Avec Switch) ---
class ParkingDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Projet 8 - Smart City Parking Dashboard")
        self.setGeometry(100, 100, 1200, 800)
        # 1. Refined Dark Theme
        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; }
            QLabel { color: white; font-family: 'Segoe UI', sans-serif; }
            QPushButton {
                background-color: #334155;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 8px;
                font-family: 'Segoe UI', sans-serif;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #475569; }
            QPushButton:pressed { background-color: #1e293b; }
        """)
        
        self.worker = ParkingWorker(places_totales=10)
        self.worker.log_signal.connect(self.append_log)
        self.worker.status_signal.connect(self.update_dashboard)
        self.worker.update_grid_signal.connect(self.update_place)
        
        self.init_ui()

    def init_ui(self):
        main = QWidget()
        self.setCentralWidget(main)
        layout = QVBoxLayout(main)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. HEADER & KPI
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(15)
        # Colors: Emerald #10b981, Blue #3b82f6, Purple #8b5cf6
        self.card_money = self.create_kpi_card("RECETTES TOTALES", "0.00 DH", "#f59e0b") # Amber for money
        self.card_visit = self.create_kpi_card("VISITEURS ACTIFS", "0", "#3b82f6")
        self.card_sub = self.create_kpi_card("ABONNÉS PRÉSENTS", "0", "#8b5cf6")
        
        self.lbl_system_status = QLabel("DISPONIBLE")
        self.lbl_system_status.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.lbl_system_status.setStyleSheet("background-color: #10b981; padding: 8px 16px; border-radius: 6px;")
        
        kpi_layout.addWidget(self.card_money)
        kpi_layout.addWidget(self.card_visit)
        kpi_layout.addWidget(self.card_sub)
        kpi_layout.addStretch()
        
        status_box = QHBoxLayout()
        l_stat = QLabel("ÉTAT DU SYSTÈME :")
        l_stat.setStyleSheet("color: #94a3b8; font-weight: bold;")
        status_box.addWidget(l_stat)
        status_box.addWidget(self.lbl_system_status)
        kpi_layout.addLayout(status_box)
        
        layout.addLayout(kpi_layout)

        # 2. INTERACTIVE PARKING GRID
        grid_frame = QFrame()
        grid_frame.setStyleSheet("background-color: #1e293b; border-radius: 12px;")
        grid_layout = QGridLayout(grid_frame)
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(15, 15, 15, 15)
        self.places_widgets = []

        for i in range(10):
            lbl = QLabel(f"P-{i+1}\nLIBRE")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedSize(110, 90)
            lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
            # Initial Style: Free (Emerald)
            lbl.setStyleSheet("""
                background-color: #10b981; 
                color: white; 
                border-radius: 8px;
                border: 2px solid transparent;
            """)
            grid_layout.addWidget(lbl, i//5, i%5)
            self.places_widgets.append(lbl)
            
        layout.addWidget(grid_frame)

        # 3. CONTROLS & MONITORING
        bottom = QHBoxLayout()
        btns = QVBoxLayout()
        btns.setSpacing(10)
        
        # Actions Styling
        btn_style_action = "background-color: #334155; border-left: 4px solid #3b82f6;"
        
        b_visiteur = QPushButton("🎫  Ticket Visiteur")
        b_visiteur.setStyleSheet(f"QPushButton {{ {btn_style_action} }} QPushButton:hover {{ background-color: #475569; }}")
        b_visiteur.clicked.connect(lambda: self.worker.entree_auto(False))
        
        b_abonne = QPushButton("💳  Badge Abonné")
        b_abonne.setStyleSheet(f"QPushButton {{ background-color: #334155; border-left: 4px solid #8b5cf6; }} QPushButton:hover {{ background-color: #475569; }}")
        b_abonne.clicked.connect(lambda: self.worker.entree_auto(True))
        
        b_sortie = QPushButton("🛑  Sortie Aléatoire")
        b_sortie.setStyleSheet(f"QPushButton {{ background-color: #334155; border-left: 4px solid #f43f5e; }} QPushButton:hover {{ background-color: #475569; }}")
        b_sortie.clicked.connect(self.worker.sortie_auto)
        
        b_switch = QPushButton("🔄  Vue Console / Graphe")
        b_switch.setStyleSheet("border: 1px solid #475569;")
        b_switch.clicked.connect(self.toggle_view)
        
        btns.addWidget(b_visiteur)
        btns.addWidget(b_abonne)
        btns.addSpacing(5)
        btns.addWidget(b_sortie)
        btns.addSpacing(15)
        btns.addWidget(b_switch)
        btns.addStretch()
        
        # Stacked Widget (Console / Graph)
        self.stack = QStackedWidget()
        
        # Page 0: Integrated Monitoring Console
        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setStyleSheet("""
            QTextEdit {
                background-color: rgba(30, 41, 59, 0.7);
                color: #10b981;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                border: 1px solid #475569;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        # Page 1: Graph
        self.graph_widget = GraphWidget(self.worker.system.automate)
        
        self.stack.addWidget(self.logs)       
        self.stack.addWidget(self.graph_widget) 
        
        bottom.addLayout(btns, 1)
        bottom.addWidget(self.stack, 3) 
        layout.addLayout(bottom, 1)

    def create_kpi_card(self, title, value, base_color):
        frame = QFrame()
        # 2. Advanced KPI Cards (Gradient & Opacity)
        # Using qlineargradient in a simplified way via background
        # Note: Qt stylesheets support linear gradients.
        # We use .QFrame to target only the container frame, not the child QLabels (which inherit QFrame)
        frame.setStyleSheet(f"""
            .QFrame {{
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {base_color}, stop:1 #1e293b);
                border-radius: 10px;
                border: 1px solid {base_color};
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        frame.setFixedSize(180, 85)
        
        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(15, 10, 15, 10)
        
        l_title = QLabel(title)
        l_title.setFont(QFont("Segoe UI", 9, QFont.Bold))
        l_title.setStyleSheet("color: rgba(255, 255, 255, 180);")
        
        l_val = QLabel(value)
        l_val.setFont(QFont("Segoe UI", 18, QFont.Bold))
        l_val.setStyleSheet("color: white;")
        l_val.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        vbox.addWidget(l_title)
        vbox.addWidget(l_val)
        return frame

    def toggle_view(self):
        current = self.stack.currentIndex()
        if current == 0:
            self.stack.setCurrentIndex(1)
        else:
            self.stack.setCurrentIndex(0)

    def update_dashboard(self, stats):
        val_money = stats.get("recettes", 0.0)
        self.card_money.findChildren(QLabel)[1].setText(f"{val_money:.2f} DH")
        self.card_visit.findChildren(QLabel)[1].setText(str(stats.get("visiteurs", 0)))
        self.card_sub.findChildren(QLabel)[1].setText(str(stats.get("abonnes", 0)))
        
        lbl_etat = stats.get("etat_automate", "???")
        self.lbl_system_status.setText(lbl_etat)
        
        # Color mapping for system status
        if lbl_etat == "COMPLET":
             self.lbl_system_status.setStyleSheet("background-color: #f43f5e; padding: 8px 16px; border-radius: 6px;") # Rose
        else:
             self.lbl_system_status.setStyleSheet("background-color: #10b981; padding: 8px 16px; border-radius: 6px;") # Emerald
        
        self.graph_widget.draw_graph(lbl_etat)

    def append_log(self, text):
        self.logs.append(text)
        self.logs.verticalScrollBar().setValue(self.logs.verticalScrollBar().maximum())

    def update_place(self, idx, status):
        l = self.places_widgets[idx]
        # 3. Interactive Parking Grid logic
        if status == 1: # Libre (Emerald)
            l.setStyleSheet("""
                background-color: #10b981; 
                color: white; 
                border-radius: 8px;
                border: 2px solid #059669;
            """)
            l.setText(f"P-{idx+1}\nLIBRE")
            
        elif status == 0: # Occupé (Rose + Emoji)
            l.setStyleSheet("""
                background-color: #f43f5e; 
                color: white; 
                border-radius: 8px;
                border: 2px solid #e11d48;
            """)
            l.setText(f"P-{idx+1}\n🚗 OCCUPÉ")
            
        elif status == -1: # Paiement (Amber)
            l.setStyleSheet("""
                background-color: #f59e0b; 
                color: white; 
                border-radius: 8px;
                border: 2px solid #d97706;
            """)
            l.setText(f"P-{idx+1}\n⏳ PAIEMENT")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ParkingDashboard()
    window.show()
    sys.exit(app.exec_())