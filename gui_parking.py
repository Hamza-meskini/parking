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
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer, QDateTime, QTime
from PyQt5.QtGui import QFont
try:
    from PyQt5.QtMultimedia import QSound
except ImportError:
    class QSound:
        @staticmethod
        def play(path):
            QApplication.beep() # Fallback

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
        self.entry_times = [None] * places_totales
        self.history_states = ["DISPONIBLE"]

    def log(self, message):
        self.log_signal.emit(message)
        print(message)

    def _animation_step(self):
        """Callback pour animer le graphe étape par étape"""
        self.update_status()          
        QApplication.processEvents()  
        time.sleep(0.8)               

    def play_sound(self, sound_type):
        """Joue un son selon le type d'événement"""
        # Mapping des sons (suppose que les fichiers existent ou fallback beep)
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

    def entree_auto(self, est_abonne):
        self.play_sound("click")
        # Reset history on new entry attempt if we are at start
        if self.system.automate.etat_courant.label_etat == "DISPONIBLE":
             self.history_states = ["DISPONIBLE"]

        if self.system.places_libres > 0:
            try:
                idx = self.occupation_map.index(None)
                type_client = "ABONNE" if est_abonne else "VISITEUR"
                
                # Animation de l'entrée
                self.system.gerer_entree(est_abonne=est_abonne, pause_callback=self._animation_step)
                
                self.occupation_map[idx] = type_client
                self.entry_times[idx] = time.time() # Enregistre l'heure d'entrée
                
                icon = "👑" if est_abonne else "🚗"
                self.log(f"--- {icon} Entrée {type_client} (Place P-{idx+1}) ---")
                
                self.update_grid_signal.emit(idx, 0) # Occupé
                self.update_status()
            except ValueError:
                self.log("Erreur interne place.")
        else:
            self.play_sound("warning")
            self.system.gerer_entree(est_abonne) 
            self.update_status()

    def sortie_auto(self):
        self.play_sound("click")
        indices_occupes = [i for i, x in enumerate(self.occupation_map) if x is not None]
        if not indices_occupes:
            self.log("[Erreur] Le parking est vide !")
            return

        idx = random.choice(indices_occupes)
        type_stocke = self.occupation_map[idx]
        est_abonne = (type_stocke == "ABONNE")
        
        # Calcul Durée/Prix
        start_time = self.entry_times[idx]
        duration = time.time() - start_time if start_time else 0
        # Prix fictif : 5 DH fixe + 0.5 DH par seconde (pour la démo)
        prix_calcule = 0.0 if est_abonne else (5.0 + duration * 0.5)

        nom = "Abonné" if est_abonne else "Visiteur"
        
        self.log(f"--- 🛑 Sortie P-{idx+1} ({nom}). Durée: {int(duration)}s. Facture: {prix_calcule:.2f} DH ---")
        self.update_grid_signal.emit(idx, -1) # Paiement
        self.update_status()

        QTimer.singleShot(500, lambda: self._finaliser_sortie(idx, est_abonne, prix_calcule))

    def _finaliser_sortie(self, idx, est_abonne, prix):
        self.system.gerer_sortie(est_abonne=est_abonne, pause_callback=self._animation_step, montant=prix)
        self.play_sound("success")
        
        self.occupation_map[idx] = None
        self.entry_times[idx] = None
        
        self.update_grid_signal.emit(idx, 1) # Vert
        self.update_status()
        self.log("--- ✅ Barrière ouverte ---")

    def update_status(self):
        status = self.system.get_status()
        current_state = status["etat_automate"]
        
        # Update History
        if not self.history_states or self.history_states[-1] != current_state:
            self.history_states.append(current_state)
            
        # Clean history if simple reset loop
        if current_state == "DISPONIBLE" and len(self.history_states) > 2:
             # Keep it but maybe trim if too long? For now let's just let it be, 
             # entree_auto resets it.
             pass

        status["history"] = self.history_states
        self.status_signal.emit(status)


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
        
        # Interaction
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.selected_node = None
        self.tooltip_annot = None
        
        self.G = nx.DiGraph()
        self.pos = None
        
        self.labels_map = {
            "DISPONIBLE": "1. DISPO-\nNIBLE", "IDENTIFICATION": "2. IDENTI-\nFICATION",
            "VERIFICATION_ACCES": "3. VERIF\nACCÈS", "BARRIERE_ENTREE_OUVERTE": "4. BARRIÈRE\nOUVERTE",
            "STATIONNEMENT": "5. VÉHICULE\nGARÉ", "CALCUL_TARIF": "6. CALCUL\nTARIF",
            "ATTENTE_PAIEMENT": "7. ATTENTE\nPAIEMENT", "BARRIERE_SORTIE_OUVERTE": "8. BARRIÈRE\nSORTIE",
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

        # Legend
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', label='Actif', markerfacecolor='#e74c3c', markersize=10),
            Line2D([0], [0], color='#3498db', lw=2, linestyle='--', label='Historique'),
            Line2D([0], [0], color='#ecf0f1', lw=2, label='Transition Possible'),
            Line2D([0], [0], marker='o', color='w', label='Sélection', markerfacecolor='#f1c40f', markersize=10),
        ]
        ax.legend(handles=legend_elements, loc='lower right', facecolor='#2b2b2b', edgecolor='white', labelcolor='white')

        self.canvas.draw()


# --- CLASS 3 : DASHBOARD (Avec Switch) ---
class ParkingDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Projet 8 - Smart City Parking Dashboard")
        self.setGeometry(100, 100, 1200, 800)
        
        # Clocks variables
        self.simulation_start = time.time()
        
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
        
        # Timers
        self.timer_clock = QTimer(self)
        self.timer_clock.timeout.connect(self.update_clocks)
        self.timer_clock.start(1000) # Every 1s update clocks & slots

    def init_ui(self):
        main = QWidget()
        self.setCentralWidget(main)
        layout = QVBoxLayout(main)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # --- HEADER SUPERIEUR (CLOCKS) ---
        header_top = QHBoxLayout()
        
        self.lbl_sim_time = QLabel("⏱ SESSION: 00:00")
        self.lbl_sim_time.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.lbl_sim_time.setStyleSheet("color: #3b82f6; background-color: #1e293b; padding: 5px 10px; border-radius: 5px;")

        header_top.addStretch()
        header_top.addWidget(self.lbl_sim_time)
        
        layout.addLayout(header_top)
        
        # 1. KPI SECTION
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
            # Layout interne pour chaque place (Icon + Text + Timer)
            lbl = QLabel(f"P-{i+1}\nLIBRE")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedSize(110, 90)
            lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
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
        
        history = stats.get("history", [])
        self.graph_widget.draw_graph(lbl_etat, history)

    def append_log(self, text):
        self.logs.append(text)
        self.logs.verticalScrollBar().setValue(self.logs.verticalScrollBar().maximum())

    def update_place(self, idx, status):
        # Cette fonction change le style de base, les timers sont mis à jour par update_clocks
        l = self.places_widgets[idx]
        
        if status == 1: # Libre (Emerald)
            l.setStyleSheet("""
                background-color: #10b981; 
                color: white; 
                border-radius: 8px;
                border: 2px solid #059669;
            """)
            l.setText(f"P-{idx+1}\nLIBRE")
            
        elif status == 0: # Occupé (Rose)
            # Le texte exact avec icône sera géré par la boucle clock si Occupé
            pass 
            
        elif status == -1: # Paiement (Amber)
            l.setStyleSheet("""
                background-color: #f59e0b; 
                color: white; 
                border-radius: 8px;
                border: 2px solid #d97706;
            """)
            l.setText(f"P-{idx+1}\n⏳ PAIEMENT")

    def update_clocks(self):
        # 2. Session Timer
        elapsed = time.time() - self.simulation_start
        m, s = divmod(int(elapsed), 60)
        self.lbl_sim_time.setText(f"⏱ SESSION: {m:02d}:{s:02d}")
        
        # 3. Update Slot Timers
        current_time = time.time()
        for idx in range(10):
            entry = self.worker.entry_times[idx]
            occ_type = self.worker.occupation_map[idx]
            widget = self.places_widgets[idx]
            
            if entry is not None and occ_type is not None:
                # Calcul durée
                duration_sec = int(current_time - entry)
                mm, ss = divmod(duration_sec, 60)
                hh, mm = divmod(mm, 60)
                
                # Icon
                icon = "👑" if occ_type == "ABONNE" else "🚗"
                
                # Mise à jour texte
                txt = f"P-{idx+1} | {icon}\n{hh:02d}:{mm:02d}:{ss:02d}"
                widget.setText(txt)
                
                # Assurer le style Occupé (au cas où update_place n'a pas tout set)
                widget.setStyleSheet("""
                    background-color: #f43f5e; 
                    color: white; 
                    border-radius: 8px;
                    border: 2px solid #e11d48;
                    font-size: 11px;
                """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ParkingDashboard()
    window.show()
    sys.exit(app.exec_())