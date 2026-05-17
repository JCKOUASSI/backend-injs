import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/session_provider.dart';
import '../services/api_client.dart';
import '../theme/qr_badge_theme.dart';
import '../utils/open_privacy_policy.dart';
import '../utils/server_url.dart';
import '../widgets/qr_badge_logo.dart';
import 'change_password_page.dart';
import 'home_page.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _formKey = GlobalKey<FormState>();
  final _usernameCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _loading = false;
  bool _obscurePassword = true;
  String? _error;

  @override
  void dispose() {
    _usernameCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final session = context.read<SessionProvider>();
      await session.login(
        usernameInput: _usernameCtrl.text,
        passwordInput: _passwordCtrl.text,
      );
      if (!mounted) {
        return;
      }
      final next = session.mustChangePassword
          ? const ChangePasswordPage()
          : const HomePage();
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => next),
      );
    } catch (e) {
      final session = context.read<SessionProvider>();
      String msg;
      if (e is NetworkTimeoutException) {
        msg = 'Le serveur ne r\u00e9pond pas (${e.host}:${e.port}).\n\n'
            'V\u00e9rifiez que Django est d\u00e9marr\u00e9 et que '
            'API_BASE_URL dans app.env est correcte.';
      } else {
        final raw = e.toString().replaceFirst('Exception: ', '');
        if (isLoopbackServerUrl(session.baseUrl) &&
            looksLikeNetworkUnreachableToHost(raw)) {
          msg = 'Impossible de joindre le serveur\u00a0: avec 127.0.0.1 '
              '(ou localhost), le t\u00e9l\u00e9phone se connecte \u00e0 '
              'lui-m\u00eame, pas \u00e0 votre Mac.\n\n'
              'Mettez l\u2019IP LAN du Mac dans API_BASE_URL (app.env), '
              'ex. http://192.168.x.x:8001.';
        } else {
          msg = raw;
        }
      }
      setState(() => _error = msg);
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.ciLight,
      appBar: AppBar(
        centerTitle: false,
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const QrBadgeLogo(size: 28, color: Colors.white),
            const SizedBox(width: 10),
            Text(
              'QR Badge',
              style: Theme.of(context).appBarTheme.titleTextStyle,
            ),
          ],
        ),
      ),
      resizeToAvoidBottomInset: true,
      body: SafeArea(
        child: SingleChildScrollView(
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          padding: EdgeInsets.fromLTRB(
            20,
            8,
            20,
            24 + MediaQuery.viewInsetsOf(context).bottom,
          ),
          child: Align(
            alignment: Alignment.topCenter,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: Material(
                      elevation: 2,
                      shadowColor: Colors.black12,
                      borderRadius: BorderRadius.circular(20),
                      color: AppColors.cardBg,
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(24, 28, 24, 24),
                        child: Form(
                          key: _formKey,
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const QrBadgeLogo(
                                size: 72,
                                color: AppColors.ciGreenDark,
                                backgroundColor: AppColors.iconQrBg,
                              ),
                              const SizedBox(height: 20),
                              Text(
                                'Bienvenue',
                                style: Theme.of(context)
                                    .textTheme
                                    .headlineSmall
                                    ?.copyWith(
                                      fontWeight: FontWeight.w700,
                                      color: AppColors.textPrimary,
                                    ),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                'Connectez-vous à votre compte',
                                textAlign: TextAlign.center,
                                style: Theme.of(context)
                                    .textTheme
                                    .bodyMedium
                                    ?.copyWith(color: AppColors.textSecondary),
                              ),
                              const SizedBox(height: 24),
                              Align(
                                alignment: Alignment.centerLeft,
                                child: Text(
                                  'Nom d\u2019utilisateur',
                                  style: Theme.of(context)
                                      .textTheme
                                      .labelLarge
                                      ?.copyWith(
                                        fontWeight: FontWeight.w600,
                                        color: AppColors.textPrimary,
                                      ),
                                ),
                              ),
                              const SizedBox(height: 8),
                              TextFormField(
                                controller: _usernameCtrl,
                                decoration: const InputDecoration(
                                  hintText: 'Identifiant',
                                ),
                                textInputAction: TextInputAction.next,
                                validator: (v) =>
                                    (v == null || v.trim().isEmpty)
                                        ? 'Champ requis'
                                        : null,
                              ),
                              const SizedBox(height: 16),
                              Align(
                                alignment: Alignment.centerLeft,
                                child: Text(
                                  'Mot de passe',
                                  style: Theme.of(context)
                                      .textTheme
                                      .labelLarge
                                      ?.copyWith(
                                        fontWeight: FontWeight.w600,
                                        color: AppColors.textPrimary,
                                      ),
                                ),
                              ),
                              const SizedBox(height: 8),
                              TextFormField(
                                controller: _passwordCtrl,
                                obscureText: _obscurePassword,
                                decoration: InputDecoration(
                                  hintText: 'Mot de passe',
                                  suffixIcon: IconButton(
                                    tooltip: _obscurePassword
                                        ? 'Afficher'
                                        : 'Masquer',
                                    icon: Icon(
                                      _obscurePassword
                                          ? Icons.visibility_off_outlined
                                          : Icons.visibility_outlined,
                                      color: AppColors.textSecondary,
                                    ),
                                    onPressed: () => setState(
                                      () => _obscurePassword = !_obscurePassword,
                                    ),
                                  ),
                                ),
                                validator: (v) => (v == null || v.isEmpty)
                                    ? 'Champ requis'
                                    : null,
                                onFieldSubmitted: (_) => _submit(),
                              ),
                              Align(
                                alignment: Alignment.centerRight,
                                child: TextButton(
                                  onPressed: () {},
                                  style: TextButton.styleFrom(
                                    foregroundColor: AppColors.ciGreenDark,
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 0,
                                      vertical: 4,
                                    ),
                                  ),
                                  child: const Text('Mot de passe oublié ?'),
                                ),
                              ),
                              if (_error != null) ...[
                                const SizedBox(height: 8),
                                Text(
                                  _error!,
                                  style: TextStyle(
                                    color: Theme.of(context).colorScheme.error,
                                    fontSize: 13,
                                  ),
                                ),
                              ],
                              const SizedBox(height: 8),
                              SizedBox(
                                width: double.infinity,
                                child: FilledButton(
                                  onPressed: _loading ? null : _submit,
                                  child: _loading
                                      ? const SizedBox(
                                          height: 22,
                                          width: 22,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2,
                                            color: Colors.white,
                                          ),
                                        )
                                      : const Text('Connexion'),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                const SizedBox(height: 20),
                TextButton.icon(
                  onPressed: () => openPrivacyPolicy(
                    context,
                    context.read<SessionProvider>().baseUrl,
                  ),
                  icon: const Icon(
                    Icons.verified_user_outlined,
                    size: 18,
                    color: AppColors.ciGreenDark,
                  ),
                  label: const Text(
                    'Confidentialité',
                    style: TextStyle(
                      color: AppColors.ciGreenDark,
                      decoration: TextDecoration.underline,
                      decorationColor: AppColors.ciGreenDark,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
