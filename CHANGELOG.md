# Changelog

Toutes les modifications notables de ce projet sont documentées dans ce fichier.
Format basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/), ce projet respecte le [Versionnement Sémantique](https://semver.org/lang/fr/).

## [Non publié]

## [1.4.0] — 2026-10-20
### Ajouté
- Génération de miniatures (thumbnails) parallélisée via `ThreadPoolExecutor` (×4–8 plus rapide).
- Index de recherche pré-calculé côté serveur (JSON injecté, temps d'ouverture < 5ms) avec normalisation diacritique des accents.
- Lecture audio différée (lazy audio) : stubs légers remplaçant les éléments `<audio>` jusqu'au premier clic pour alléger le DOM initial.
- Compression Brotli optionnelle (`output.html.br`, ratio jusqu'à -86% vs brut) activée automatiquement si `brotli` est installé (`pip install brotli`).

### Amélioré
- Algorithme de résolution des citations et réactions : passage de complexité quadratique O(N²) à linéaire O(N) via fenêtre glissante (lookback max 300 messages).
- Mode Standalone : compression automatique en mémoire des images volumineuses avant encodage Base64 (max 1600×1600, JPEG qualité 82) générant un fichier HTML 40% à 60% plus léger.
- Intégration du virtual scroller et de l'audio lazy : dispatch de l'événement `wa-nodes-restored` lors du re-montage des fragments de messages.

## [1.3.0] — 2026-10-19
### Ajouté
- Mode Serveur Web interactif avec Drag & Drop (`--serve` / `python3 build.py --serve`) servi sur `http://localhost:8080`.
- Mode Fichier Unique Autonome (`--standalone`) intégrant toutes les images et polices en Base64.
- Export PDF paginé propre avec feuille de style `@media print` et règles d'évitement de coupure de bulles de messages.

## [1.2.0] — 2026-10-18
### Ajouté
- Fichier `requirements.txt` documenté avec dépendances facultatives et obligatoires.
- Section d'installation et de prise en main détaillée dans le `README.md`.

## [1.1.0] — 2026-10-17
### Ajouté
- Prise en charge sécurisée des archives `.zip` exportées directement depuis WhatsApp.
- Protections strictes contre les attaques par décompression (zip bombs, dépassement de taille 500 Mo, limite à 10 000 fichiers).
- Détection et résolution interactive des messages cités (citations) avec navigation vers le message source.
- Détection et agrégation visuelle des réactions emoji sous les bulles de discussion.

## [1.0.0] — 2026-10-16
### Ajouté
- Filtres médias granulaires (images, vidéos, notes vocales/audio, documents, liens).
- Sélecteur de plage de dates (date range picker) interactif.
- Scrubber chronologique latéral pour navigation rapide dans le fil de discussion.
- Thème et design authentiques calqués sur WhatsApp Web (mode clair & sombre, bulles, typographie, doodle wallpaper).

## [0.4.0] — 2026-10-15
### Ajouté
- Galerie de médias dédiée avec visionneuse Lightbox (zoom haute définition 1:1, pan, plein écran).
- Filtres avancés par type de messages et recherche textuelle.

## [0.3.0] — 2026-10-14
### Ajouté
- Analyseur de messages en flux continu (streaming parser) pour faible empreinte RAM.
- Génération automatique des miniatures d'images pour optimiser l'affichage web.
- Compression Gzip automatique du fichier HTML généré (`output.html.gz`).
- Cycle de vie intelligent et auto-pause des vidéos hors du champ de vision.

## [0.2.0] — 2026-10-13
### Ajouté
- Suite de tests automatisée complète (sécurité, régression golden, CLI, parseur, stats).

## [0.1.0] — 2026-10-12
### Ajouté
- Version initiale du convertisseur d'export WhatsApp `.txt` vers une page HTML interactive.

[Non publié]: https://github.com/bluetechtg/whatsapp_chat_viewer/compare/v1.4.0...HEAD
[1.4.0]: https://github.com/bluetechtg/whatsapp_chat_viewer/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/bluetechtg/whatsapp_chat_viewer/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/bluetechtg/whatsapp_chat_viewer/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/bluetechtg/whatsapp_chat_viewer/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/bluetechtg/whatsapp_chat_viewer/compare/v0.4.0...v1.0.0
[0.4.0]: https://github.com/bluetechtg/whatsapp_chat_viewer/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/bluetechtg/whatsapp_chat_viewer/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/bluetechtg/whatsapp_chat_viewer/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/bluetechtg/whatsapp_chat_viewer/releases/tag/v0.1.0
