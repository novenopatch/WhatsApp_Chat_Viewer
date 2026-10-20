# WhatsApp Chat Viewer

[![Version](https://img.shields.io/badge/version-1.4.0-brightgreen.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](requirements.txt)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](LICENSE)

Convertisseur d'exports WhatsApp (`.txt` ou archive `.zip` + dossier médias) en visualiseur HTML interactif, moderne, autonome, fluide et ultra-performant.

---

## 🚀 Fonctionnalités

- **Performances & Fluidité (optimisé pour les gros exports de dizaines de milliers de messages)** :
  - Rendu CSS optimisé avec `content-visibility: auto` (seuls les messages visibles sont calculés par le moteur de rendu, fluidité garantie à 60/120 fps).
  - Moteur de recherche JavaScript non-destructif avec **debounce** (200ms) évitant tout gel du navigateur.
  - Chargement asynchrone et différé (`loading="lazy"`, `decoding="async"`, `preload="none"`) sur l'ensemble des médias.
  - Rendu propre pour impression (`@media print`).
- **Différenciation "Moi" vs "Autres" (Bulles droite / gauche)** :
  - Vos messages sont alignés à droite avec la couleur verte WhatsApp (`#d9fdd3` en mode clair, `#005c4b` en mode sombre).
  - Les messages reçus sont alignés à gauche sur fond blanc (`#ffffff` en mode clair, `#202c33` en mode sombre) avec avatar et nom coloré.
  - Configuration facile via `--me` / `--your-name` ou variable `ME` dans `.env`, détection automatique intelligente, et **sélecteur interactif dans le header** pour changer d'interlocuteur à la volée sans recharger la page.
- **Mode Sombre officiel WhatsApp (Dark Mode)** :
  - Détection automatique du thème système (`prefers-color-scheme: dark`) avec mémorisation de votre choix (`localStorage`).
  - Bouton switch interactif ☀️/🌙 dans la barre supérieure.
  - Palette officielle WhatsApp Dark : fond `#111b21`, bulles reçues `#202c33`, bulles envoyées `#005c4b`.
- **Notes vocales & Audios avec sélecteur de vitesse** :
  - Bouton de vitesse intégré sur les notes vocales (`.opus`, `.mp3`, etc.) permettant de basculer en un clic entre **1x**, **1.5x** et **2x**, comme sur l'application WhatsApp.
- **Messages cités & Réponses (Quotes / Citations)** :
  - Support de la syntaxe officielle WhatsApp (`> `) avec ou sans mention d'auteur (`> Auteur: texte`).
  - Boîte de citation stylisée authentique avec barre d'accentuation colorée, fond contrasté et texte d'aperçu.
  - **Navigation instantanée** : un clic sur une citation fait défiler la conversation jusqu'au message d'origine avec animation d'impulsion (`jump-pulse`).
- **Réactions Emojis WhatsApp (badges & picker interactif)** :
  - Détection automatique et absorption des réactions depuis les exports (`❤️ to "..."`, `a réagi par 👍 à "..."`, tags `[❤️]`, etc.) directement rattachées sous forme de badges sous les bulles cibles.
  - **Barre de réactions interactive intégrée** : au survol d'un message, un bouton smiley `😊` permet d'ouvrir la capsule officielle flottante (`👍 ❤️ 😂 😮 😢 🙏`) pour réagir en direct avec persistance dans le `localStorage` du navigateur.
  - Tooltip dynamique indiquant qui a réagi et décompte par emoji.
- **Bulles groupées et adaptatives** : regroupement consécutif par participant, palette de couleurs automatique pour chaque interlocuteur (idéal en duo ou en conversation de groupe).
- **Support complet des médias** :
  - Images (lightbox intégrée avec navigation clavier et boutons précédent / suivant)
  - Vidéos (`.mp4`, `.mov`, `.3gp`)
  - Notes vocales et audios (`.opus`, `.mp3`, `.m4a`, etc.) avec réglage de vitesse
  - Stickers (`.webp`) stylisés
  - Documents (`.pdf`, etc.)
- **Formatage WhatsApp** : support du texte brut enrichi WhatsApp (`*gras*`, `_italique_`, `~barré~`, `monospace`, blocs de code ` ``` `, citations `> `).
- **Liens et annotations** : URLs cliquables (`target="_blank"`), détection des messages modifiés (`modifié`).
- **Messages système & événements** : rendu centré sous forme de pill stylisée (appels vocaux/vidéo/groupe, notifications de chiffrement, messages supprimés, etc.).
- **Recherche interactive & navigation** :
  - Surlignage temps réel fluide
  - Navigation résultat par résultat avec les touches `Entrée` / `Shift+Entrée` ou les boutons haut/bas
  - Touche `Échap` pour réinitialiser
- **Boutons de défilement rapide** : retour en haut et saut en bas de conversation.
- **Section Statistiques détaillée** (pliable) :
  - Répartition des messages par participant (% et barres colorées)
  - Histogramme d'activité heure par heure (0h-23h)
  - Décompte des types de médias
  - Jour le plus actif et moyennes quotidiennes

---

## 🏗️ Architecture du projet

Le projet est structuré de façon modulaire et maintenable :

```
whatsapp_chat_viewer/
├── build.py                # Point d'entrée CLI principal (rétro-compatible)
├── src/
│   ├── zip_handler.py      # Extraction sécurisée des archives .zip (anti-Zip Slip & anti-bombe ZIP)
│   ├── parser.py           # Parsing des fichiers WhatsApp, dates, markdown et annotations
│   ├── stats.py            # Calculs statistiques et génération du rapport
│   ├── config.py           # Chargement de la configuration (CLI, .env, defaults, prompt)
│   ├── user_detector.py    # Détection et résolution automatique de l'expéditeur "Moi"
│   ├── renderer.py         # Assemblage du visualiseur HTML
│   └── templates/
│       ├── base.html       # Squelette HTML
│       ├── style.css       # Feuilles de style (variables CSS, Dark Mode, responsive)
│       └── app.js          # Moteur JS haute performance (recherche debouncée, audio, lightbox)
├── tests/                  # Suite de tests unitaires complète
│   ├── test_zip_handler.py
│   ├── test_parser.py
│   ├── test_stats.py
│   ├── test_config.py
│   └── test_renderer.py
└── .github/workflows/      # Intégration continue (CI)
    └── ci.yml
```

---

## 🛠️ Installation & Utilisation

### 0. Prérequis & Installation

Le projet fonctionne nativement avec la bibliothèque standard Python 3 (Python >= 3.10) sans dépendance obligatoire.

Pour bénéficier de l'accélération des images et de la génération des miniatures (`--thumbs`) :
```bash
pip install -r requirements.txt
```

### 1. Mode Serveur Web Drag & Drop (Le plus simple)

Pour visualiser et convertir une archive sans aucune ligne de commande complexe :
```bash
python3 build.py --serve

# Avec mode verbeux (RAM RSS, CPU user, décompression) et mode Ultra-Performance :
python3 build.py --serve -v --ultra-perf
```
* Ouvre automatiquement votre navigateur sur `http://127.0.0.1:8080`.
* Glissez-déposez simplement votre archive `.zip` WhatsApp.
* Suivi en temps réel de la **décompression** et des ressources (barre de progression, RAM RSS, CPU utilisateur).
* Visualisez le chat instantanément ou téléchargez le fichier HTML généré !

---

### 2. En ligne de commande (CLI)

```bash
# 📦 Exploiter directement une archive ZIP générée par WhatsApp (iOS ou Android)
python3 build.py mon_export.zip

# 📄 Générer un fichier HTML UNIQUE autonome (Standalone - photos & audios en Base64)
python3 build.py mon_export.zip --standalone -o chat_autonome.html

# Ou avec options spécifiques
python3 build.py --zip mon_export.zip --output ma_conversation.html --me "Mon Nom"

# Pointer vers un dossier d'export WhatsApp déjà extrait
python3 build.py --dir /chemin/vers/WhatsApp_Export/

# Ou spécifier les chemins individuellement
python3 build.py --chat /chemin/vers/_chat.txt --media /chemin/vers/media/ --output ma_conversation.html --me "Mon Nom"
```

Options disponibles (`python3 build.py --help`) :
- `input_target` : fichier `.zip`, `.txt` ou dossier d'export WhatsApp passé directement en argument
- `--serve` : lance l'interface Web locale avec Drag & Drop (port par défaut : 8080)
- `--port PORT` : port pour le serveur Web (défaut : 8080)
- `--host HOST` : hôte d'écoute pour le serveur Web (défaut : 127.0.0.1)
- `--standalone, --embed` : intègre les images, stickers et audios en Base64 pour obtenir **un seul fichier HTML 100% autonome** transportable par email ou clé USB
- `--max-embed-size MB` : taille maximale en Mo par média intégré en standalone (défaut : 20 Mo)
- `-z, --zip FILE` : archive `.zip` d'export WhatsApp (auto-extraction sécurisée et détection de la discussion)
- `--extract-dir DIR` : dossier cible pour l'extraction du zip (défaut : dossier au nom de l'archive)
- `-d, --dir DIR` : dossier d'export WhatsApp (détecte automatiquement le fichier `.txt` et le dossier `media/`)
- `-c, --chat FILE` : chemin vers le fichier de discussion `.txt`
- `-m, --media DIR` : dossier contenant les médias
- `-o, --output FILE` : chemin du fichier HTML produit (défaut : `output.html`)
- `--me, --your-name NAME` : votre nom ou pseudo dans la conversation (place vos messages à droite sur fond vert)
- `-l, --lang {auto,en,fr}` : langue de l'interface (`auto` par défaut selon la langue du système, ou forcé à `en` / `fr`)
- `--thumbs` : génère des miniatures optimisées pour accélérer le chargement initial
- `-v, --verbose` : mode verbeux affichant le suivi détaillé de l'extraction, la RAM (RSS) et le temps CPU utilisateur
- `--ultra-perf, --fast` : mode ultra-performance (décompression turbo en chunks 1 Mo, parsing accéléré, encodage Base64 mis en cache)

---

### 3. Impression et Export PDF paginé

Le visualiseur intègre une feuille de style d'impression publication-ready (`@media print`) :
* Bouton `🖨️` dédié dans la barre supérieure (ou raccourci clavier `Ctrl+P` / `Cmd+P`).
* **Pagination propre** : aucun découpage de bulle de message ou d'image au milieu d'une page (`break-inside: avoid`).
* **En-tête de document** élégant reprenant les participants, la date et le nombre de messages.
* Masquage automatique des éléments interactifs (recherche, menus, boutons, audio players).
* Numérotation des pages automatique en pied de page.

---

### 4. Via fichier `.env`

Copiez [`.env.example`](.env.example) vers `.env` et adaptez les chemins :

```env
CHAT_DIR=/chemin/vers/WhatsApp_Export/
OUTPUT_FILE=output.html
ME="Mon Nom"
LANG=auto   # 'auto' (défaut système), 'en' ou 'fr'
```

Puis lancez simplement :
```bash
python3 build.py
```

---

### 3. Mode interactif

Si aucun argument CLI ni fichier `.env` n'est détecté et que `chat.txt` n'est pas dans le dossier courant, le script vous demandera simplement les chemins avec autocomplétion (touche `<Tab>`).

---

## 🧪 Tests unitaires

Une suite de tests unitaires intégrée valide l'ensemble des modules (parser, statistiques, configuration, détection et rendu HTML) :

```bash
python3 -m unittest discover -s tests -v
```

---

## 📜 Versionnement & Notes de version

Ce projet suit le [Versionnement Sémantique (SemVer)](https://semver.org/lang/fr/). Pour consulter l'historique complet des versions, les fonctionnalités ajoutées et les correctifs, consultez le fichier [CHANGELOG.md](CHANGELOG.md).

