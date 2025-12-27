# Bibliothèques standard
import random
import sys
import time
from typing import Dict, List, Optional

# Bibliothèques tierces
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import Qt, QObject, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    from PyQt5.QtMultimedia import QSound
except ImportError:
    class QSound:
        @staticmethod
        def play(path: str) -> None:
            QApplication.beep()

# Imports locaux
from parking_system import ParkingSystem


# ==================== CONSTANTES ====================
# Animation et timing
DELAI_ANIMATION = 0.8  # Secondes entre chaque étape d'animation
DELAI_PAIEMENT = 500   # Millisecondes avant finalisation sortie

# Couleurs UI (Tailwind-inspired)
COULEUR_EMERALD = "#10b981"    # Places libres, succès
COULEUR_ROSE = "#f43f5e"       # Places occupées
COULEUR_AMBER = "#f59e0b"      # Paiement en cours, recettes
COULEUR_BLUE = "#3b82f6"       # Visiteurs, éléments interactifs
COULEUR_PURPLE = "#8b5cf6"     # Abonnés
COULEUR_SLATE_DARK = "#0f172a" # Fond principal
COULEUR_SLATE_MID = "#1e293b"  # Fond secondaire
COULEUR_SLATE_LIGHT = "#334155" # Boutons

# Tailles des widgets
TAILLE_SLOT_WIDTH = 110
TAILLE_SLOT_HEIGHT = 90
TAILLE_KPI_CARD_WIDTH = 180
TAILLE_KPI_CARD_HEIGHT = 85

# ==================== CLASSES ====================

class ClickableLabel(QLabel):
    """Label cliquable pour les slots de parking."""
    
    clicked = pyqtSignal(int)
    
    def __init__(self, index: int, text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self.index = index
    
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.index)
        super().mousePressEvent(event)

class ParkingWorker(QObject):
    """
    Gestion de la logique métier et des animations du parking.
    
    Signals:
        log_signal: Émet les messages de log
        status_signal: Émet les mises à jour de statut
        update_grid_signal: Émet les changements d'état des slots (index, status)
    """
    
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(dict)
    update_grid_signal = pyqtSignal(int, int)

    def __init__(self, places_totales: int = 10) -> None:
        super().__init__()
        self.system = ParkingSystem(places_totales=places_totales)
        self.occupation_map: List[Optional[str]] = [None] * places_totales
        self.entry_times: List[Optional[float]] = [None] * places_totales
        self.history_states: List[str] = ["DISPONIBLE"]

    def log(self, message: str) -> None:
        """Émet un message de log."""
        self.log_signal.emit(message)
        print(message)

    def _animation_step(self) -> None:
        """Callback pour animer le graphe étape par étape."""
        self.update_status()
        QApplication.processEvents()
        time.sleep(DELAI_ANIMATION)               

    def play_sound(self, sound_type: str) -> None:
        """Joue un son selon le type d'événement."""
        sounds = {
            "success": "sounds/success.wav",
            "warning": "sounds/warning.wav",
            "click": "sounds/click.wav"
        }
        path = sounds.get(sound_type)
        if path:
            QSound.play(path)
        else:
            QApplication.beep()

    def entree_auto(self, est_abonne: bool) -> None:
        """Gère l'entrée automatique d'un véhicule."""
        self.play_sound("click")
        if self.system.automate.etat_courant.label_etat == "DISPONIBLE":
            self.history_states = ["DISPONIBLE"]

        if self.system.places_libres > 0:
            try:
                idx = self.occupation_map.index(None)
                type_client = "ABONNE" if est_abonne else "VISITEUR"
                
                self.system.gerer_entree(est_abonne=est_abonne, pause_callback=self._animation_step)
                
                self.occupation_map[idx] = type_client
                self.entry_times[idx] = time.time()
                
                icon = "👑" if est_abonne else "🚗"
                self.log(f"--- {icon} Entrée {type_client} (Place P-{idx+1}) ---")
                
                self.update_grid_signal.emit(idx, 0)
                self.update_status()
            except ValueError:
                self.log("Erreur interne place.")
        else:
            self.play_sound("warning")
            self.system.gerer_entree(est_abonne)
            self.update_status()

    def sortie_specifique(self, idx: int) -> None:
        """Déclenche la sortie pour un slot spécifique."""
        if self.occupation_map[idx] is None:
            return

        self.play_sound("click")
        type_stocke = self.occupation_map[idx]
        est_abonne = (type_stocke == "ABONNE")
        
        start_time = self.entry_times[idx]
        duration = time.time() - start_time if start_time else 0
        prix_calcule = 0.0 if est_abonne else (5.0 + duration * 0.5)

        nom = "Abonné" if est_abonne else "Visiteur"
        self.log(f"--- 🛑 Sortie P-{idx+1} ({nom}). Durée: {int(duration)}s. Facture: {prix_calcule:.2f} DH ---")
        
        self.entry_times[idx] = None
        
        self.update_grid_signal.emit(idx, -1)
        self.update_status()

        QTimer.singleShot(DELAI_PAIEMENT, lambda: self._finaliser_sortie(idx, est_abonne, prix_calcule))

    def sortie_auto(self) -> None:
        """Simule une sortie aléatoire."""
        indices_occupes = [i for i, x in enumerate(self.occupation_map) if x is not None]
        if not indices_occupes:
            self.log("[Erreur] Le parking est vide !")
            return

        idx = random.choice(indices_occupes)
        self.sortie_specifique(idx)

    def _finaliser_sortie(self, idx: int, est_abonne: bool, prix: float) -> None:
        """Finalise la sortie après le paiement."""
        self.system.gerer_sortie(est_abonne=est_abonne, pause_callback=self._animation_step, montant=prix)
        self.play_sound("success")
        
        self.occupation_map[idx] = None
        
        self.update_grid_signal.emit(idx, 1)
        self.update_status()
        self.log("--- ✅ Barrière ouverte ---")

    def update_status(self) -> None:
        """Met à jour le statut et émet le signal."""
        status = self.system.get_status()
        current_state = status["etat_automate"]
        
        if not self.history_states or self.history_states[-1] != current_state:
            self.history_states.append(current_state)

        status["history"] = self.history_states
        self.status_signal.emit(status)


class GraphWidget(QWidget):
    """Widget d'affichage du graphe de l'automate."""
    
    def __init__(self, automate) -> None:
        super().__init__()
        self.automate = automate
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)

        self.figure = Figure(facecolor='#2b2b2b')
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.selected_node: Optional[str] = None
        self.tooltip_annot = None
        
        self.G = nx.DiGraph()
        self.pos: Optional[Dict] = None
        
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
        
        self.state_info = {
            "DISPONIBLE": "Le système est prêt à accueillir un véhicule. (Attente détection)",
            "IDENTIFICATION": "Lecture de la plaque ou du badge d'abonné.",
            "VERIFICATION_ACCES": "Vérification des droits d'accès dans la base de données.",
            "BARRIERE_ENTREE_OUVERTE": "Accès autorisé, la barrière s'ouvre.",
            "STATIONNEMENT": "Véhicule garé. Le système surveille la place.",
            "CALCUL_TARIF": "Calcul du montant à payer selon la durée.",
            "ATTENTE_PAIEMENT": "Le conducteur doit régler le montant affiché.",
            "BARRIERE_SORTIE_OUVERTE": "Paiement validé (ou gratuit), sortie autorisée.",
            "COMPLET": "Aucune place disponible. Entrée bloquée."
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
                "COMPLET": (0.0, 8.0), 
                "DISPONIBLE": (0.0, 4.0),
                "IDENTIFICATION": (4.0, 4.0), 
                "VERIFICATION_ACCES": (8.0, 4.0),
                "BARRIERE_ENTREE_OUVERTE": (12.0, 4.0), 
                "STATIONNEMENT": (12.0, 0.0),
                "CALCUL_TARIF": (8.0, 0.0), 
                "ATTENTE_PAIEMENT": (4.0, 0.0),
                "BARRIERE_SORTIE_OUVERTE": (0.0, 0.0)
            }
        else:
            self.pos = nx.spring_layout(self.G)
        self.draw_graph("DISPONIBLE")
        
    def on_click(self, event):
        if event.inaxes is None: return
        # Trouver le noeud le plus proche
        min_dist = float('inf')
        closest = None
        for node, (x, y) in self.pos.items():
            dist = (x - event.xdata)**2 + (y - event.ydata)**2
            if dist < min_dist:
                min_dist = dist
                closest = node
        
        if closest and min_dist < 1.0: # Seuil de clic
            self.selected_node = closest if self.selected_node != closest else None
            # On redessine avec l'état courant stocké (hack: on ne l'a pas ici, on suppose DISPONIBLE ou on attend refresh)
            # Mieux : on stocke last_label et last_history
            if hasattr(self, 'last_label'):
                self.draw_graph(self.last_label, getattr(self, 'last_history', []))

    def draw_graph(self, current_label, history=[]):
        self.last_label = current_label
        self.last_history = history
        
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#2b2b2b')

        node_colors = []
        edge_colors = []
        node_sizes = []
        
        for node in self.G.nodes():
            size = 5000
            
            if node == current_label:
                node_colors.append('#e74c3c') # Rouge Actif
                edge_colors.append('#c0392b')
            elif node == self.selected_node:
                node_colors.append('#f1c40f') # Selection (Jaune)
                edge_colors.append('#f39c12')
                size = 5500 # Slightly bigger
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
            
            node_sizes.append(size)

        # 1. Draw Nodes
        nx.draw_networkx_nodes(self.G, self.pos, ax=ax, node_color=node_colors, 
                               edgecolors=edge_colors, linewidths=3, node_size=node_sizes)

        # 2. Labels inside nodes
        nx.draw_networkx_labels(self.G, self.pos, ax=ax, labels=self.labels_map, 
                                font_size=9, font_weight="bold", font_family="Arial")

        # 3. Draw Edges (Historical vs Normal)
        # Identify historical edges
        hist_edges = []
        for i in range(len(history) - 1):
            u, v = history[i], history[i+1]
            if self.G.has_edge(u, v):
                hist_edges.append((u, v))
                
        # Draw all edges first (default style)
        nx.draw_networkx_edges(self.G, self.pos, ax=ax, edge_color='#ecf0f1', 
                               arrows=True, arrowsize=25, width=2.0, 
                               connectionstyle='arc3,rad=0.0',
                               min_source_margin=20, min_target_margin=20)
        
        # Overdraw historical edges (Dashed, Blue)
        if hist_edges:
            nx.draw_networkx_edges(self.G, self.pos, ax=ax, edgelist=hist_edges,
                                   edge_color='#3498db', style='dashed', alpha=0.8,
                                   arrows=True, arrowsize=25, width=2.5,
                                   connectionstyle='arc3,rad=0.0',
                                   min_source_margin=20, min_target_margin=20)

        # Edge Labels
        edge_labels = nx.get_edge_attributes(self.G, 'label')
        nx.draw_networkx_edge_labels(self.G, self.pos, edge_labels=edge_labels, 
                                     font_color='#f39c12', font_size=8, ax=ax, 
                                     bbox=dict(facecolor='#2b2b2b', edgecolor='none', alpha=0.6))

        # Title & Limits
        ax.set_title(f"ÉTAT : {self.labels_map.get(current_label, current_label).replace(chr(10), ' ')}", 
                     color="white", fontsize=14, fontweight='bold')
        ax.set_xlim(-2, 14) 
        ax.set_ylim(-2, 10) 
        ax.axis('off')
        
        # Tooltip for selected node
        if self.selected_node:
            info = self.state_info.get(self.selected_node, "Pas d'info.")
            ax.text(6, 9, f"INFO ({self.selected_node}):\n{info}", 
                    bbox=dict(facecolor='#f1c40f', alpha=0.9, boxstyle='round,pad=0.5'),
                    fontsize=10, color='black', ha='center')



        self.canvas.draw()


class ParkingDashboard(QMainWindow):
    """Interface principale du tableau de bord de parking."""
    
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Projet 8 - Smart City Parking Dashboard")
        self.setGeometry(100, 100, 1200, 800)
        
        self.simulation_start = time.time()
        
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {COULEUR_SLATE_DARK}; }}
            QLabel {{ color: white; font-family: 'Segoe UI', sans-serif; }}
            QPushButton {{
                background-color: {COULEUR_SLATE_LIGHT};
                color: white;
                border: none;
                padding: 12px;
                border-radius: 8px;
                font-family: 'Segoe UI', sans-serif;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: #475569; }}
            QPushButton:pressed {{ background-color: {COULEUR_SLATE_MID}; }}
        """)
        
        self.worker = ParkingWorker(places_totales=10)
        self.worker.log_signal.connect(self.append_log)
        self.worker.status_signal.connect(self.update_dashboard)
        self.worker.update_grid_signal.connect(self.update_place)
        
        self.init_ui()
        
        self.timer_clock = QTimer(self)
        self.timer_clock.timeout.connect(self.update_clocks)
        self.timer_clock.start(1000)

    def init_ui(self):
        main = QWidget()
        self.setCentralWidget(main)
        layout = QVBoxLayout(main)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        header_top = QHBoxLayout()
        
        self.lbl_sim_time = QLabel("⏱ SESSION: 00:00")
        self.lbl_sim_time.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.lbl_sim_time.setStyleSheet(f"color: {COULEUR_BLUE}; background-color: {COULEUR_SLATE_MID}; padding: 5px 10px; border-radius: 5px;")

        header_top.addStretch()
        header_top.addWidget(self.lbl_sim_time)
        
        layout.addLayout(header_top)
        
        # 1. KPI SECTION
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(15)
        self.card_money = self.create_kpi_card("RECETTES TOTALES", "0.00 DH", COULEUR_AMBER)
        self.card_visit = self.create_kpi_card("VISITEURS ACTIFS", "0", COULEUR_BLUE)
        self.card_sub = self.create_kpi_card("ABONNÉS PRÉSENTS", "0", COULEUR_PURPLE)
        
        self.lbl_system_status = QLabel("DISPONIBLE")
        self.lbl_system_status.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.lbl_system_status.setStyleSheet(f"background-color: {COULEUR_EMERALD}; padding: 8px 16px; border-radius: 6px;")
        
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
        grid_frame.setStyleSheet(f"background-color: {COULEUR_SLATE_MID}; border-radius: 12px;")
        grid_layout = QGridLayout(grid_frame)
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(15, 15, 15, 15)
        self.places_widgets = []

        for i in range(10):
            # Layout interne pour chaque place (Icon + Text + Timer)
            # Utilisation de ClickableLabel pour interactivité
            lbl = ClickableLabel(i, f"P-{i+1}\nLIBRE")
            lbl.clicked.connect(self.worker.sortie_specifique)
            
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedSize(TAILLE_SLOT_WIDTH, TAILLE_SLOT_HEIGHT)
            lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
            lbl.setStyleSheet(f"""
                background-color: {COULEUR_EMERALD}; 
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
        
        b_visiteur = QPushButton("🎫  Ticket Visiteur")
        b_visiteur.setStyleSheet(f"QPushButton {{ background-color: {COULEUR_SLATE_LIGHT}; border-left: 4px solid {COULEUR_BLUE}; }} QPushButton:hover {{ background-color: #475569; }}")
        b_visiteur.clicked.connect(lambda: self.worker.entree_auto(False))
        
        b_abonne = QPushButton("💳  Badge Abonné")
        b_abonne.setStyleSheet(f"QPushButton {{ background-color: {COULEUR_SLATE_LIGHT}; border-left: 4px solid {COULEUR_PURPLE}; }} QPushButton:hover {{ background-color: #475569; }}")
        b_abonne.clicked.connect(lambda: self.worker.entree_auto(True))
        
        b_sortie = QPushButton("🛑  Simulation Sortie")
        b_sortie.setStyleSheet(f"QPushButton {{ background-color: {COULEUR_SLATE_LIGHT}; border-left: 4px solid {COULEUR_ROSE}; }} QPushButton:hover {{ background-color: #475569; }}")
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

    def create_kpi_card(self, title: str, value: str, base_color: str) -> QFrame:
        """Crée une carte KPI avec gradient."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            .QFrame {{
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {base_color}, stop:1 {COULEUR_SLATE_MID});
                border-radius: 10px;
                border: 1px solid {base_color};
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        frame.setFixedSize(TAILLE_KPI_CARD_WIDTH, TAILLE_KPI_CARD_HEIGHT)
        
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
        
        if lbl_etat == "COMPLET":
            self.lbl_system_status.setStyleSheet(f"background-color: {COULEUR_ROSE}; padding: 8px 16px; border-radius: 6px;")
        else:
            self.lbl_system_status.setStyleSheet(f"background-color: {COULEUR_EMERALD}; padding: 8px 16px; border-radius: 6px;")
        
        history = stats.get("history", [])
        self.graph_widget.draw_graph(lbl_etat, history)

    def append_log(self, text):
        self.logs.append(text)
        self.logs.verticalScrollBar().setValue(self.logs.verticalScrollBar().maximum())

    def update_place(self, idx: int, status: int) -> None:
        """Met à jour l'affichage d'un slot de parking."""
        l = self.places_widgets[idx]
        
        if status == 1:
            l.setStyleSheet(f"""
                background-color: {COULEUR_EMERALD}; 
                color: white; 
                border-radius: 8px;
                border: 2px solid transparent;
            """)
            l.setText(f"P-{idx+1}\nLIBRE")
            l.setCursor(Qt.ArrowCursor)
            
        elif status == 0:
            l.setCursor(Qt.PointingHandCursor)
            
        elif status == -1:
            l.setStyleSheet(f"""
                background-color: {COULEUR_AMBER}; 
                color: white; 
                border-radius: 8px;
                border: 2px solid #d97706;
            """)
            l.setText(f"P-{idx+1}\n⏳ PAIEMENT")
            l.setCursor(Qt.ArrowCursor)

    def update_clocks(self) -> None:
        """Met à jour les horloges et les timers des slots."""
        elapsed = time.time() - self.simulation_start
        m, s = divmod(int(elapsed), 60)
        self.lbl_sim_time.setText(f"⏱ SESSION: {m:02d}:{s:02d}")
        
        current_time = time.time()
        for idx in range(10):
            entry = self.worker.entry_times[idx]
            occ_type = self.worker.occupation_map[idx]
            widget = self.places_widgets[idx]
            
            if entry is not None and occ_type is not None:
                duration_sec = int(current_time - entry)
                mm, ss = divmod(duration_sec, 60)
                hh, mm = divmod(mm, 60)
                
                icon = "👑" if occ_type == "ABONNE" else "🚗"
                
                txt = (f"<div style='text-align: center;'>"
                       f"<span style='font-size:10pt; font-weight:bold;'>P-{idx+1}</span> "
                       f"<span style='font-size:16pt;'>{icon}</span><br>"
                       f"<span style='font-size:11pt; font-family:Consolas; font-weight:bold;'>{hh:02d}:{mm:02d}:{ss:02d}</span>"
                       f"</div>")
                widget.setText(txt)
                
                widget.setStyleSheet(f"""
                    background-color: {COULEUR_ROSE}; 
                    color: white; 
                    border-radius: 8px;
                    border: 2px solid #e11d48;
                """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ParkingDashboard()
    window.show()
    sys.exit(app.exec_())