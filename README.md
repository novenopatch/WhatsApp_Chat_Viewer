# WhatsApp Chat Viewer

Convertisseur d'exports WhatsApp (`.txt` + dossier médias) en visualiseur HTML interactif, moderne, fluide et réactif.

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
- **Bulles groupées et adaptatives** : regroupement consécutif par participant, palette de couleurs automatique pour chaque interlocuteur (idéal en duo ou en conversation de groupe).
- **Support complet des médias** :
  - Images (lightbox intégrée avec navigation clavier et boutons précédent / suivant)
  - Vidéos (`.mp4`, `.mov`, `.3gp`)
  - Notes vocales et audios (`.opus`, `.mp3`, `.m4a`, etc.) avec réglage de vitesse
  - Stickers (`.webp`) stylisés
  - Documents (`.pdf`, etc.)
- **Formatage WhatsApp** : support du texte brut enrichi WhatsApp (`*gras*`, `_italique_`, `~barré~`, `monospace`, blocs de code ` ``` `).
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
│   ├── test_parser.py
│   ├── test_stats.py
│   ├── test_config.py
│   └── test_renderer.py
└── .github/workflows/      # Intégration continue (CI)
    └── ci.yml
```

---

## 🛠️ Utilisation

### 1. En ligne de commande (recommandé)

```bash
# Pointer directement vers un dossier d'export WhatsApp complet
python3 build.py --dir /chemin/vers/WhatsApp_Export/

# Ou spécifier les chemins individuellement
python3 build.py --chat /chemin/vers/_chat.txt --media /chemin/vers/media/ --output ma_conversation.html --me "Mon Nom"
```

Options disponibles (`python3 build.py --help`) :
- `-d, --dir DIR` : dossier d'export WhatsApp (détecte automatiquement le fichier `.txt` et le dossier `media/`)
- `-c, --chat FILE` : chemin vers le fichier de discussion `.txt`
- `-m, --media DIR` : dossier contenant les médias
- `-o, --output FILE` : chemin du fichier HTML produit (défaut : `output.html`)
- `--me, --your-name NAME` : votre nom ou pseudo dans la conversation (place vos messages à droite sur fond vert)

---

### 2. Via fichier `.env`

Copiez [`.env.example`](.env.example) vers `.env` et adaptez les chemins :

```env
CHAT_DIR=/chemin/vers/WhatsApp_Export/
OUTPUT_FILE=output.html
ME="Mon Nom"
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
