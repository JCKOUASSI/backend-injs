import 'package:flutter/material.dart';

abstract final class AppColors {
  // Design System Unifié INJS-LMD 2026 — Institut National de la Jeunesse et des Sports
  // Source: frontend/src/index.css :root
  // Bleu Nuit (foncé) + Bleu Clair (institutionnel)
  static const Color navy = Color(0xFF0B1F3A);        // --navy #0B1F3A bleu nuit profond
  static const Color navyMid = Color(0xFF0F274A);     // --navy-mid #0F274A
  static const Color navySoft = Color(0xFF123E6A);    // --navy-soft / --ci-blue-dark #123E6A
  static const Color blue = Color(0xFF1E62D0);        // --ci-blue #1E62D0 bleu clair principal
  static const Color blueLight = Color(0xFF2F80ED);   // variante claire
  static const Color blueSoft = Color(0xFFEBF3FF);    // fond très clair bleuté
  static const Color bluePale = Color(0xFFDCE6F2);    // --ci-light #dce6f2
  static const Color dusty = Color(0xFFC5D2E4);       // --dusty
  static const Color bgColor = Color(0xFFEDF4FB);     // --bg-color #EDF4FB mesh lumineux

  // Couleurs héritées (compatibilité) — réalignées sur INJS
  static const Color ciWarning = Color(0xFFF59E0B);      // --ci-warning #F59E0B
  static const Color ciWarningDark = Color(0xFFD97706);  // --ci-warning-dark
  static const Color ciSuccess = blue;                   // bleu clair devient success principal
  static const Color ciSuccessDark = navy;               // bleu nuit devient success dark
  static const Color ciWhite = Color(0xFFFFFFFF);
  static const Color ciLight = bgColor;                  // fond app = bleu très clair

  static const Color ciDanger = Color(0xFFEF4444);       // --ci-danger #EF4444
  static const Color ciBlue = blue;                      // --ci-blue
  static const Color ciPurple = Color(0xFF7B1FA2);

  static const Color textPrimary = Color(0xFF0F172A);    // --text-primary
  static const Color textSecondary = Color(0xFF475569);  // --text-secondary
  static const Color borderColor = Color(0xFFCBD5E1);    // --border-color

  // Aliases (compat) — éviter des changements en cascade dans les pages.
  static const Color textMuted = textSecondary;
  static const Color accentWarning = ciWarning;

  // Surfaces
  static const Color cardBg = ciWhite;
  static const Color cardCream = bgColor;
  static const Color cardGrey = Color(0xFFF7FAFC);

  // Accents utilisés dans l’app mobile — version INJS bleue
  static const Color navIndicator = blueSoft;            // #EBF3FF indicateur nav
  static const Color badgeWarningBg = Color(0xFFFFF8E0);
  static const Color badgeWarningFg = ciWarningDark;
  static const Color iconQrBg = blueSoft;                // #EBF3FF fond icône QR
}

ThemeData buildQrBadgeTheme() {
  const seed = AppColors.navy;
  final scheme = ColorScheme.fromSeed(
    seedColor: seed,
    primary: AppColors.navy,           // bleu foncé #0B1F3A
    secondary: AppColors.blue,         // bleu clair #1E62D0
    tertiary: AppColors.blueLight,     // bleu clair light #2F80ED
    error: AppColors.ciDanger,
    brightness: Brightness.light,
    surface: AppColors.ciWhite,
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme.copyWith(
      primary: AppColors.navy,
      onPrimary: Colors.white,
      secondary: AppColors.blue,
      onSecondary: Colors.white,
      surface: AppColors.ciWhite,
      background: AppColors.bgColor,
    ),
    scaffoldBackgroundColor: AppColors.bgColor, // #EDF4FB fond mesh lumineux
    dividerColor: AppColors.borderColor,
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.navy, // #0B1F3A bleu nuit
      foregroundColor: Colors.white,
      elevation: 0,
      centerTitle: true,
      titleTextStyle: TextStyle(
        color: Colors.white,
        fontSize: 20,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.2,
      ),
      iconTheme: IconThemeData(color: Colors.white),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: AppColors.ciWhite,
      indicatorColor: AppColors.navIndicator, // #EBF3FF
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        final selected = states.contains(WidgetState.selected);
        return TextStyle(
          fontSize: 12,
          fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
          color: selected ? AppColors.navy : AppColors.textSecondary,
        );
      }),
      iconTheme: WidgetStateProperty.resolveWith((states) {
        final selected = states.contains(WidgetState.selected);
        return IconThemeData(
          color: selected ? AppColors.navy : AppColors.textSecondary,
          size: 24,
        );
      }),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.ciWhite,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppColors.borderColor),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppColors.borderColor),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppColors.blue, width: 2),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: AppColors.navy, // #0B1F3A bouton principal bleu foncé
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        elevation: 0,
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.blue, // #1E62D0 bouton secondaire bleu clair
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        elevation: 2,
      ),
    ),
    cardTheme: CardThemeData(
      color: AppColors.ciWhite,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: const BorderSide(color: Color(0xFFE2E8F0), width: 1),
      ),
      shadowColor: const Color(0x140B1F3A),
    ),
  );
}
