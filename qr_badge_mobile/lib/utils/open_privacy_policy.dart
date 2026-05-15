import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../config/app_env.dart';

/// Ouvre la politique de confidentialité dans le navigateur (discret, hors navigation in-app).
Future<void> openPrivacyPolicy(BuildContext context, String apiBaseUrl) async {
  final uri = Uri.parse(AppEnv.privacyPolicyUrlForApiBase(apiBaseUrl));
  try {
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } else if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Lien indisponible : $uri')),
      );
    }
  } catch (_) {
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Ouverture du lien impossible.')),
      );
    }
  }
}
