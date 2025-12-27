# 🚗 Système de Parking Intelligent (Smart Parking System)

Bienvenue dans la simulation interactive de gestion de parking intelligent. Ce projet démontre l'application concrète de la **théorie des automates à états finis** (FSM) dans un environnement applicatif moderne et temps réel.

## 🌟 Aperçu du Projet

Cette application simule le cycle de vie complet d'un parking : entrée des véhicules, gestion des places, calcul de la tarification et sortie. Elle offre une interface visuelle riche combinant un **Dashboard de contrôle** et une **Visualisation dynamique de l'automate** sous-jacent.

### 🎯 Objectifs
- Illustrer le fonctionnement d'un automate (états/transitions) en temps réel.
- Fournir une simulation réaliste avec contraintes (places limitées, abonnés vs visiteurs).
- Offrir une expérience utilisateur (UX) fluide et interactive.

---

## ✨ Fonctionnalités Principales

### 1. 🖥️ Dashboard de Supervision
- **Monitoring Temps Réel** : Une grille de 10 places affichant l'état de chaque slot.
- **Iconographie Dynamique** : Distingue visuellement les **Visiteurs** (🚗) des **Abonnés** (👑).
- **Timers Individuels** : Chaque place occupée affiche un chronomètre précis (durée de stationnement).
- **Statistiques (KPIs)** : Suivi en direct du nombre de visiteurs, d'abonnés et du chiffre d'affaires (Recettes).

### 2. 🖱️ Interactivité Totale
- **Click-to-Exit** : Cliquez directement sur un véhicule garé pour déclencher sa sortie spécifique.
- **Curseur Contextuel** : Le curseur change (`Main`) au survol des places occupées pour indiquer l'action possible.
- **Contrôles Manuels** :
  - `🎫 Ticket Visiteur` : Simule l'arrivée d'un client standard (Payant).
  - `💳 Badge Abonné` : Simule l'arrivée d'un abonné (Gratuit).
  - `🛑 Simulation Sortie` : Génère une sortie aléatoire (pour tests rapides).

### 3. 🧠 Visualisation de l'Automate
- **Graphe Animé** : Un graphique NetworkX intégré montre l'état interne du système en temps réel.
- **Historique Visuel** : Le chemin parcouru par le véhicule courant est tracé en **pointillés bleus**.
- **Infos-bulles (Tooltips)** : Cliquez sur les nœuds du graphe pour voir la description de chaque état.
- **Nœuds Actifs** : L'état courant s'allume en **Rouge** pour un suivi visuel immédiat.

### 4. 🔊 Retour Audio & Visuel
- **Feedback Sonore** : Sons distincts pour les clics, les succès (barrière) et les avertissements (parking plein).
- **Design Moderne** : Interface sombre ("Dark Mode") avec palette de couleurs soignée (Emerald, Rose, Amber).

---

## 🛠️ Architecture Technique

Le projet est structuré autour du modèle MVC (Modèle-Vue-Contrôleur) simplifié :

- **`parking_system.py` (Modèle)** : Contient la logique métier, la gestion de l'automate et les données (places, tarifs).
- **`gui_parking.py` (Vue & Contrôleur)** : Gère l'interface PyQt5, les signaux, les timers et le widget graphique Matplotlib.
- **`automate_base.py`** : Définition générique de la classe Automate (États et Transitions).
- **`main.py`** : Point d'entrée de l'application.

### Technologies
- **Python 3.x**
- **PyQt5** : Framework GUI.
- **Matplotlib & NetworkX** : Visualisation de graphes.

---

## 🚀 Installation et Utilisation

### Prérequis
Assurez-vous d'avoir Python installé. Installez ensuite les dépendances nécessaires :

```bash
pip install PyQt5 matplotlib networkx
```
*(Ou utilisez `pip install -r requirements.txt` si disponible)*

### Lancement
Exécutez simplement le fichier principal :

```bash
python main.py
```

### Guide Rapide
1.  **Entrée** : Cliquez sur "Ticket Visiteur" ou "Badge Abonné".
2.  **Observation** : Regardez la voiture apparaître sur le dashboard et l'automate bouger sur le graphe.
3.  **Sortie** : Cliquez sur la voiture garée (slot rose) pour la faire sortir et observer le calcul du prix.
4.  **Basculer la Vue** : Utilisez le bouton "Vue Console / Graphe" pour voir les logs détaillés ou le schéma de l'automate.

---

## 🎨 Credits
Développé pour illustrer la puissance des automates finis dans les systèmes embarqués et interactifs.