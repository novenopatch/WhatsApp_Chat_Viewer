# WhatsApp Chat Viewer

<div align="center">

[![CI](https://github.com/BlueTechTG/whatsapp-chat-viewer/actions/workflows/ci.yml/badge.svg)](https://github.com/BlueTechTG/whatsapp-chat-viewer/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-1.4.0-brightgreen.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](requirements.txt)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Framework: Standard Library](https://img.shields.io/badge/framework-standard_library-orange.svg)](#)

**Convertissez vos exports WhatsApp (archives `.zip` ou fichier `.txt` + dossier de médias) en un visualiseur HTML interactif, moderne, fluide et ultra-performant.**

[English](README.md) | [Français](README.fr.md)

</div>

---

## ⚡ Points forts

* **Zéro framework lourd** : Fonctionne entièrement avec la bibliothèque standard Python 3 et du JavaScript vanilla pur. Aucun serveur Node.js, Flask, Django ou bundler complexe requis.
* **Conçu pour les gros volumes** : Testé et validé sur des archives volumineuses (**1.74+ Go, plus de 4 400 médias**) avec téléversement en streaming direct sur disque — aucune saturation de RAM ni freeze machine.
* **Double mode d'utilisation** :
  * **Interface Web locale (`--serve`)** : Interface moderne en Drag & Drop avec suivi en temps réel de la décompression et des ressources.
  * **Ligne de commande (CLI)** : Automatisation facile de conversions et scripts d'archivage.
* **Mode Fichier Unique Autonome (Standalone)** : Embarque toutes les photos, audios et stickers directement en Base64 dans un unique fichier HTML indépendant et transportable par email ou clé USB.
* **Expérience WhatsApp Web authentique** : Thèmes Clair et Sombre, citations de réponse avec animation de saut, badges de réactions avec capsule interactive, notes vocales avec sélecteur de vitesse (1x/1.5x/2x), lightbox plein écran, tiroir galerie complet, statistiques avancées et recherche instantanée non-bloquante.
* **Impression & Export PDF publication-ready** : Feuille de style dédiée `@media print` avec pagination propre sans coupure de bulles, en-tête de document et numérotation des pages.
* **Support multilingue** : Interface et messages système en français et en anglais (`--lang fr|en|auto`).
* **Sécurité renforcée** : Protection native contre les attaques Zip Slip (traversée de répertoires), les bombes ZIP et les archives corrompues.

---

## 🎯 Cas d'usage

**WhatsApp Chat Viewer** est conçu pour toute personne qui a besoin d'archiver, d'analyser ou de partager des conversations WhatsApp en dehors de l'écosystème de l'application :

### Archivage personnel
- **Préserver des conversations importantes** : Historique de relations, souvenirs familiaux, étapes de vie
- **Sauvegarde avant changement de compte** : Changement de numéro, fermeture de compte ou migration d'appareil
- **Stockage à long terme** : Garder les conversations en sécurité même si le compte WhatsApp est banni ou perdu
- **Accès hors-ligne** : Lire l'historique des discussions sans connexion internet ni WhatsApp Web

### Professionnel et juridique
- **Documentation juridique** : Avocats et juristes préservant des preuves pour des affaires civiles ou pénales
- **Sources journalistiques** : Documentation d'entretiens et enregistrements de communications avec des sources
- **Archives professionnelles** : Discussions avec clients, décisions de projet, accords de partenariat
- **Documentation RH** : Conversations de recrutement (avec consentement) et communications internes

### Création de contenu
- **Production média** : YouTubers, streamers et blogueurs illustrant des conversations
- **Narration** : Mémorialistes documentant l'histoire personnelle et familiale
- **Partage social** : Extraits de conversations soignés pour les réseaux sociaux ou présentations

### Modération de groupes
- **Archives communautaires** : Admins préservant les décisions de groupe, règles et discussions importantes
- **Documentation de projet** : Équipes maintenant des historiques de conversations pour référence
- **Coordination d'événements** : Organisateurs gardant des traces de la logistique et communications participants

### Recherche et analyse
- **Recherche académique** : Chercheurs étudiant les patterns de communication numérique
- **Ethnographie** : Sociologues documentant les communautés en ligne
- **Analyse de données** : Extraction d'insights à partir des patterns de messages, timing et partage de médias

---

## 📊 Comparaison

| Fonctionnalité | WhatsApp Web | Export natif | Screenshots | WhatsApp Chat Viewer |
|----------------|--------------|--------------|-------------|---------------------|
| **Accès hors-ligne** | ❌ Nécessite internet | ✅ Oui | ✅ Oui | ✅ Oui |
| **Recherche** | ⚠️ Limitée | ❌ Non | ❌ Non | ✅ Recherche plein texte |
| **Design visuel** | ⚠️ UI mobile sur desktop | ❌ Texte brut | ✅ Visuel | ✅ UI moderne responsive |
| **Intégration médias** | ✅ En ligne uniquement | ❌ Dossier séparé | ❌ Non | ✅ Intégrés ou liés |
| **Analytics/Stats** | ❌ Aucune | ❌ Aucune | ❌ Aucune | ✅ Dashboard détaillé |
| **Fichier autonome** | ❌ Non | ⚠️ Texte seulement | ❌ Images seulement | ✅ Fichier HTML unique |
| **Export impression/PDF** | ❌ Médiocre | ❌ Non | ⚠️ Manuel | ✅ Publication-ready |
| **Mode sombre** | ✅ Oui | ❌ Non | ❌ Non | ✅ Système + manuel |
| **Validation sécurité** | ✅ Officiel | ❌ Aucune | ❌ Aucune | ✅ Protection Zip Slip/Bomb |
| **Vérification hash** | ❌ Non | ❌ Non | ❌ Non | ✅ Intégrité SHA-256 |
| **Coût** | Gratuit | Gratuit | Gratuit | **Gratuit & Open Source** |
| **Multi-plateforme** | ✅ Oui | ✅ Oui | ✅ Oui | ✅ Python 3.10+ |

---

## 🚀 Fonctionnalités principales

### 🎨 Interface WhatsApp Web fidèle
- **Différenciation "Moi" vs "Autres"** : Vos messages s'alignent à droite en vert WhatsApp (`#d9fdd3` / `#005c4b`) ; les messages reçus s'alignent à gauche sur fond blanc/sombre avec le nom coloré de l'expéditeur.
- **Sélecteur dynamique d'interlocuteur** : Changez de participant à la volée depuis le menu déroulant de l'en-tête sans recharger la page.
- **Mode Sombre officiel** : Détection automatique des préférences système (`prefers-color-scheme: dark`) avec switch interactif ☀️/🌙 et mémorisation dans le `localStorage`.
- **Notes vocales & lecteur audio** : Sélecteur de vitesse intégré (**1x**, **1.5x**, **2x**) et barre de progression pour les fichiers `.opus`, `.ogg`, `.mp3`, `.m4a`.
- **Citations de réponse (Quotes)** : Encadré de citation authentique avec barre d'accent colorée. Un clic sur une citation fait défiler la discussion directement jusqu'au message cité avec impulsion visuelle.
- **Réactions Emojis WhatsApp** : Détection et regroupement automatique des réactions (`👍 ❤️ 😂 😮 😢 🙏`). Survol d'un message pour ouvrir la capsule interactive et réagir en direct.
- **Lightbox & Galerie de médias** :
  - Visualiseur plein écran pour photos et vidéos avec zoom et raccourcis clavier (`←` / `→` / `Échap`).
  - Tiroir galerie à onglets (Photos, Audios, Documents, Liens).

### ⚡ Performances de premier ordre
- **Upload en streaming & requêtes Range** : Les uploads sont streamés par blocs de 1 Mo directement sur disque, maintenant l'empreinte RAM sous 45 Mo. Les médias supportent `Accept-Ranges: bytes` (HTTP 206) pour une avance/retour rapide fluide dans les vidéos et audios.
- **Miniatures optimisées (`--thumbs`)** : Génération parallèle en ThreadPool pour garantir un défilement à 60/120 fps.
- **CSS `content-visibility: auto`** : Le moteur de rendu du navigateur ne calcule que les messages visibles à l'écran.
- **Recherche instantanée sans DOM** : Index de recherche fluide avec temporisation (debounce 200ms) et navigation clavier (`Entrée` / `Shift+Entrée`).
- **Tableau de bord statistique** : Répartition des messages par participant, histogramme d'activité sur 24h, décompte des médias et jour le plus actif.

---

## 🏗️ Architecture du projet

```text
whatsapp_chat_viewer/
├── build.py                # Point d'entrée principal en ligne de commande (CLI)
├── src/
│   ├── config.py           # Gestion de la configuration (arguments CLI, .env, defaults, invites)
│   ├── constants.py        # Expressions régulières, formats de date, couleurs d'avatars
│   ├── i18n.py             # Internationalisation (traductions français / anglais)
│   ├── monitor.py          # Mesure des performances (RAM RSS/Peak, temps CPU)
│   ├── parser.py           # Analyseur syntaxique WhatsApp, markdown, dates, réactions
│   ├── renderer.py         # Assemblage du HTML, encodage Base64, génération de miniatures
│   ├── server.py           # Serveur HTTP léger avec upload streaming et support HTTP Range
│   ├── stats.py            # Calculs statistiques et rapports graphiques
│   ├── user_detector.py    # Détection automatique de l'expéditeur principal ("Moi")
│   ├── zip_handler.py      # Extraction sécurisée ZIP (anti-Zip Slip, anti-bombe ZIP)
│   └── templates/
│       ├── base.html       # Squelette HTML principal
│       ├── style.css       # Styles responsifs et palettes officielles WhatsApp
│       ├── app.js          # Logique client (recherche, audio, lightbox, réactions)
│       └── server_index.html # Interface Web locale Drag & Drop
├── tests/                  # Plus de 150 tests unitaires et d'intégration
├── .env.example            # Gabarit de configuration d'environnement
├── CONTRIBUTING.md         # Guide de contribution
├── CODE_OF_CONDUCT.md      # Code de conduite de la communauté
├── SECURITY.md             # Politique de sécurité et signalement de vulnérabilités
└── LICENSE                 # Licence MIT
```

---

## 🛠️ Démarrage rapide

### 1. Prérequis

* **Python 3.10+** (Python 3.10, 3.11, 3.12, 3.13, 3.14).
* Dépendances optionnelles recommandées (miniatures d'images et chargement de `.env`) :
  ```bash
  pip install -r requirements.txt
  ```

---

### 2. Mode Serveur Web Drag & Drop (Recommandé)

Lancez le serveur local et ouvrez l'interface dans votre navigateur :

```bash
# Démarre le serveur sur le port 8080
python3 build.py --serve

# Avec suivi détaillé des ressources et mode Ultra-Performance :
python3 build.py --serve -v --ultra-perf
```

1. Ouvrez `http://127.0.0.1:8080` dans votre navigateur.
2. Glissez-déposez votre archive `.zip` d'export WhatsApp.
3. Suivez en direct la progression de la décompression et la consommation des ressources.
4. Cliquez sur **Visualiser** ou téléchargez le fichier HTML généré !

---

### 3. En ligne de commande (CLI)

```bash
# 📦 Convertir directement une archive ZIP WhatsApp (iOS ou Android)
python3 build.py mon_export.zip

# 📄 Générer un fichier HTML UNIQUE autonome (Standalone - médias en Base64)
python3 build.py mon_export.zip --standalone -o chat_autonome.html

# 🎯 Spécifier le nom du fichier de sortie, votre pseudo, la langue et les miniatures
python3 build.py --zip export.zip --output chat.html --me "Alice" --lang fr --thumbs

# 📁 Convertir depuis un dossier déjà extrait
python3 build.py --dir /chemin/vers/dossier_extrait/

# ⚙️ Définir manuellement le fichier texte et le dossier des médias
python3 build.py --chat chat.txt --media media/ --output chat.html
```

#### Référence des options CLI

| Option | Raccourci | Description | Défaut |
| :--- | :--- | :--- | :--- |
| `input_target` | | Chemin positionnel vers `.zip`, `.txt` ou dossier d'export | Aucun |
| `--serve` | | Lance le serveur Web local avec interface Drag & Drop | `False` |
| `--port` | | Port d'écoute du serveur Web | `8080` |
| `--host` | | Adresse d'écoute du serveur Web | `127.0.0.1` |
| `--standalone` | `--embed` | Intègre les images, audios et stickers en Base64 | `False` |
| `--max-embed-size` | | Taille max en Mo par média intégré en standalone | `20` |
| `--zip` | `-z` | Chemin vers l'archive `.zip` | Aucun |
| `--extract-dir` | | Dossier cible d'extraction du ZIP | Nom de l'archive |
| `--dir` | `-d` | Dossier d'export WhatsApp décompressé | Aucun |
| `--chat` | `-c` | Chemin vers le fichier `.txt` de discussion | Aucun |
| `--media` | `-m` | Dossier contenant les médias | Aux côtés du chat |
| `--output` | `-o` | Chemin du fichier HTML généré | `output.html` |
| `--me` | `--your-name`| Votre nom dans la discussion (bulles vertes à droite) | Auto-détecté |
| `--lang` | `-l` | Langue de l'interface (`auto`, `en`, `fr`) | `auto` |
| `--thumbs` | | Génère des miniatures optimisées pour accélérer l'affichage | `False` |
| `--verbose` | `-v` | Affiche les détails d'extraction, la RAM (RSS) et le CPU | `False` |
| `--ultra-perf` | `--fast` | Décompression turbo (chunks 1 Mo) et encodage optimisé | `False` |

---

### 4. Configuration via fichier `.env`

Copiez [`.env.example`](.env.example) vers `.env` pour définir vos options par défaut sans passer d'arguments CLI :

```ini
ZIP_FILE=/chemin/vers/WhatsApp_Export.zip
OUTPUT_FILE=mon_chat.html
ME="Mon Nom"
LANG=fr
MAX_UNCOMPRESSED_SIZE=10737418240
```

Lancez ensuite simplement :
```bash
python3 build.py
```

---

## 🔒 Sécurité et protection des données

WhatsApp Chat Viewer applique des politiques défensives strictes pour traiter les archives non fiables :
* **Anti-Zip Slip** : Validation des chemins pour bloquer les tentatives de sortie de répertoire (`../`).
* **Interdiction des liens symboliques** : Rejet systématique des symlinks et nœuds de périphériques spéciaux.
* **Quotas stricts** : Plafond sur le nombre de fichiers (`MAX_ZIP_FILES=50000`) et la taille décompressée (`MAX_UNCOMPRESSED_SIZE=10GB`).
* **Gardes en streaming** : L'extraction surveille en continu les octets écrits et supprime immédiatement les fichiers partiels en cas d'anomalie.
* **Échappement HTML** : Tous les messages et noms de participants sont neutralisés pour prévenir toute injection de script (XSS).

Consultez [SECURITY.md](SECURITY.md) pour la politique complète et la procédure de signalement.

---

## 🧪 Tests unitaires et intégration

La suite de tests automatisée valide l'intégralité des modules :

```bash
# Exécuter l'ensemble des 150+ tests
python3 -m unittest discover -s tests -v

# Mesurer la couverture de code (optionnel)
pip install coverage
coverage run -m unittest discover -s tests
coverage report -m
```

---

## 🤝 Contribution

Les contributions sont chaleureusement bienvenues ! Veuillez consulter le guide [CONTRIBUTING.md](CONTRIBUTING.md) et notre [Code de Conduite](CODE_OF_CONDUCT.md) avant d'ouvrir une pull request.

---

## 📄 Licence

Ce projet est sous licence libre [MIT](LICENSE).  
Copyright (c) 2024-2026 BlueTechTG.
