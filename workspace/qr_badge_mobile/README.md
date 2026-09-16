# QR Badge (mobile + PWA)

Application Flutter pour le badgeage sécurisé (scan QR, géolocalisation, heartbeat) connectée au backend Sygep.

## PWA (Web)

```bash
flutter build web
```

Les fichiers générés sont dans `build/web/`. Servez-les **en HTTPS** (obligatoire pour la géolocalisation et l’installation « Ajouter à l’écran d’accueil »).

Exemple local après build :

```bash
cd build/web && python3 -m http.server 8080
```

Pour un sous-chemin (ex. `/qr-badge/`), utilisez :

```bash
flutter build web --base-href /qr-badge/
```

### Limites navigateur

- Pas de service en avant-plan Android / flux iOS : le **heartbeat** ne tourne que tant que l’onglet reste actif (comportement Web normal).
- Sur Web, l’app enregistre un `device_id` préfixé **`FLUTTER_PWA_`** : le backend **n’applique pas** les sanctions liées à `MOBILE_HEARTBEAT_*` (suspect / sortie auto) sur ces pointages, contrairement à l’app native `MOBILE_…`.
- Les jetons sur Web utilisent le stockage adapté de `flutter_secure_storage` (navigateur), moins fort que le Keychain matériel.

## Mobile (Android / iOS)

Voir la documentation Flutter habituelle (`flutter run`, Xcode, Android Studio).

### Play Store — signature **release** (obligatoire)

Si la console affiche *« signature en mode débogage »*, crée un keystore **upload** une seule fois, puis configure Gradle.

1. **Keystore** (dans le dossier `android/`, une seule fois) :

```bash
cd android
keytool -genkey -v -keystore upload-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload
```

Conserve `upload-keystore.jks` et les mots de passe en lieu sûr (perte = impossible de mettre à jour l’app sous le même package sans contacter le support Google).

2. **Fichier `android/key.properties`** (copier depuis `key.properties.example`) :

```properties
storePassword=...
keyPassword=...
keyAlias=upload
storeFile=upload-keystore.jks
```

3. **Build AAB** :

```bash
cd ..   # racine qr_badge_mobile
flutter build appbundle --release
```

**Réduire la taille du livrable** :

- **Dart** (recommandé) : obfuscation + symboles hors bundle :

```bash
flutter build appbundle --release --obfuscate --split-debug-info=build/debug-info
```

Conserve **`build/debug-info/`** (hors store) pour symboliser les crashs **Dart** (distinct du mapping Java ci‑dessous).

- **Android R8** : activé en release (`minifyEnabled` / `shrinkResources`). Dépendances Play **v2** (`feature-delivery`, `core-common`) — pas le monolithe `com.google.android.play:core:1.x` (déconseillé / rejet Play). Les règles ProGuard incluent `-dontwarn` sur `com.google.android.play.core.tasks.*` (références résiduelles de l’embedding Flutter aux composants différés ; sans effet si vous n’utilisez pas les modules dynamiques Play).

- **Play Console — fichier de désobscurcissement** : après `flutter build appbundle --release`, importez **`build/app/outputs/mapping/release/mapping.txt`** (même version que l’AAB publié) dans la fiche de la version (ANR / plantages Java/Kotlin). Cela supprime l’avertissement « aucun fichier de désobscurcissement » pour la couche Android.

- **Analyser** : `flutter build apk --release --analyze-size`

**Play Console — politique de confidentialité** : si l’app déclare `CAMERA`, Google exige une **URL HTTPS** (Contenu de l’appli → Politique de confidentialité).

Le backend Django du projet expose une page prête à l’emploi (à adapter si besoin avec ton juriste / ton administration) :

`https://<TON_DOMAINE>/dashboard/legal/confidentialite-qr-badge/`

Remplace `<TON_DOMAINE>` par l’URL publique du serveur (ex. `sygep.example.ci`). Copie cette URL exacte dans la Play Console.

**Dans l’app** : un lien discret « Confidentialité » (souligné, petit texte) sous le formulaire de connexion, et la même entrée dans le menu **⋮** de l’écran principal. Ouverture dans le **navigateur externe**. URL = `PRIVACY_POLICY_URL` (app.env / dart-define) ou `{API_BASE_URL}/dashboard/legal/confidentialite-qr-badge/`.

Fichier : `build/app/outputs/bundle/release/app-release.aab` — à importer dans Play Console (tests internes, etc.).

Sans `key.properties`, le build release reste signé en **debug** (pratique en local uniquement).
