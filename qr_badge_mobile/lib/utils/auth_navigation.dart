import 'package:flutter/material.dart';

import '../pages/splash_page.dart';

/// Remet la pile de navigation sur [SplashPage], qui affiche login / accueil
/// selon l'état de [SessionProvider].
void resetToAuthRoot(BuildContext context) {
  Navigator.of(context).pushAndRemoveUntil(
    MaterialPageRoute(builder: (_) => const SplashPage()),
    (_) => false,
  );
}
