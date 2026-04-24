import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';

/// Demande l'autorisation de localisation (runtime iOS/Android).
/// Affiche une boîte de dialogue explicative avant le prompt système,
/// et propose d'ouvrir les réglages si l'utilisateur a refusé définitivement.
///
/// Retourne `true` si la permission est accordée (whileInUse ou always).
Future<bool> ensureLocationPermission(BuildContext context) async {
  final serviceOn = await Geolocator.isLocationServiceEnabled();
  if (!serviceOn) {
    if (!context.mounted) {
      return false;
    }
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Localisation désactivée'),
        content: const Text(
          'Le service de localisation est désactivé sur l\u2019appareil. '
          'Activez-le dans les réglages pour pouvoir badger.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('OK'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              Geolocator.openLocationSettings();
            },
            child: const Text('Réglages'),
          ),
        ],
      ),
    );
    return false;
  }

  var perm = await Geolocator.checkPermission();
  if (perm == LocationPermission.always ||
      perm == LocationPermission.whileInUse) {
    return true;
  }

  if (perm == LocationPermission.deniedForever) {
    if (!context.mounted) {
      return false;
    }
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Localisation refusée'),
        content: const Text(
          'L\u2019accès à la position GPS est nécessaire pour badger '
          '(entrée, sortie, suivi de présence). '
          'Vous pouvez l\u2019activer dans les réglages de l\u2019application.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('OK'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              openAppSettings();
            },
            child: const Text('Réglages'),
          ),
        ],
      ),
    );
    return false;
  }

  // Explication avant le prompt natif
  if (!context.mounted) {
    return false;
  }
  final proceed = await showDialog<bool>(
    context: context,
    barrierDismissible: false,
    builder: (ctx) => AlertDialog(
      title: const Text('Autoriser la localisation'),
      content: const Text(
        'QR Badge a besoin de votre position GPS pour valider votre présence '
        'sur le site de formation lors du badgeage et du suivi de session.',
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(ctx, false),
          child: const Text('Plus tard'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(ctx, true),
          child: const Text('Continuer'),
        ),
      ],
    ),
  );
  if (proceed != true) {
    return false;
  }

  perm = await Geolocator.requestPermission();
  return perm == LocationPermission.always ||
      perm == LocationPermission.whileInUse;
}
