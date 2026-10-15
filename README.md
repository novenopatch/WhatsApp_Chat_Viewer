# WhatsApp Chat Viewer
This project allows you to view exported WhatsApp chat logs in a clean HTML page, including messages, attachments (images, audio), and timestamps.

## Features
- Group consecutive messages by the same sender.
- Display images and audio attachments inline.
- Show individual timestamps for each message.
- Automatically generate a header with participants and conversation time range.

## Usage
1. Place your exported WhatsApp `.txt` files in the project folder.
2. Adjust `YOUR_NAME` in `build.py` to identify your messages.
3. Run the Python script to generate `output.html`:

Convertisseur d'exports WhatsApp (`.txt` + dossier médias) en visualiseur HTML interactif, moderne et réactif.

---

## 🚀 Fonctionnalités

- **Bulles groupées et adaptatives** : regroupement consécutif par participant, palette de couleurs automatique pour chaque interlocuteur (idéal en duo ou en conversation de groupe).
- **Support complet des médias** :
  - Images (lightbox intégrée avec navigation clavier et boutons précédent / suivant)
  - Vidéos (`.mp4`, `.mov`, `.3gp`)
  - Notes vocales et audios (`.opus`, `.mp3`, `.m4a`, etc.)
  - Stickers (`.webp`) stylisés
  - Documents (`.pdf`, etc.)
- **Formatage WhatsApp** : support du texte brut enrichi WhatsApp (`*gras*`, `_italique_`, `~barré~`, `monospace`, blocs de code ` ``` `).
- **Liens et annotations** : URLs cliquables (`target="_blank"`), détection des messages modifiés (`modifié`).
- **Messages système & événements** : rendu centré sous forme de pill stylisée (appels vocaux/vidéo/groupe, notifications de chiffrement, messages supprimés, etc.).
- **Recherche interactive & navigation** :
  - Surlignage temps réel
  - Navigation résultat par résultat avec les touches `Entrée` / `Shift+Entrée` ou les boutons haut/bas
  - Touche `Échap` pour réinitialiser
- **Boutons de défilement rapide** : retour en haut et saut en bas de conversation.
- **Section Statistiques détaillée** (pliable) :
  - Répartition des messages par participant (% et barres colorées)
  - Histogramme d'activité heure par heure (0h-23h)
  - Décompte des types de médias
  - Jour le plus actif et moyennes quotidiennes

---

## 🛠️ Utilisation

### 1. En ligne de commande (recommandé)

```bash
# Pointer directement vers un dossier d'export WhatsApp complet
python3 build.py --dir /chemin/vers/WhatsApp_Export/

# Ou spécifier les chemins individuellement
python3 build.py --chat /chemin/vers/_chat.txt --media /chemin/vers/media/ --output ma_conversation.html
```

Options disponibles (`python3 build.py --help`) :
- `-d, --dir DIR` : dossier d'export WhatsApp (détecte automatiquement le fichier `.txt` et le dossier `media/`)
- `-c, --chat FILE` : chemin vers le fichier de discussion `.txt`
- `-m, --media DIR` : dossier contenant les médias
- `-o, --output FILE` : chemin du fichier HTML produit (défaut : `output.html`)

---

### 2. Via fichier `.env`

Copiez [`.env.example`](.env.example) vers `.env` et adaptez les chemins :

```env
CHAT_DIR=/chemin/vers/WhatsApp_Export/
OUTPUT_FILE=output.html
```

Puis lancez simplement :
```bash
python3 build.py
```

---

### 3. Mode interactif

Si aucun argument CLI ni fichier `.env` n'est détecté et que `chat.txt` n'est pas dans le dossier courant, le script vous demandera simplement les chemins avec autocomplétion (touche `<Tab>`).
