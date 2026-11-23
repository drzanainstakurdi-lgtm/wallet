import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../config.dart';
import '../i18n.dart';
import '../state.dart';
import '../ui.dart';

class AuthPage extends StatefulWidget {
  const AuthPage({super.key});

  @override
  State<AuthPage> createState() => _AuthPageState();
}

class _AuthPageState extends State<AuthPage> {
  final _user = TextEditingController();
  final _pass = TextEditingController();
  bool _register = false;
  bool _busy = false;
  String? _err;

  @override
  void dispose() {
    _user.dispose();
    _pass.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final u = _user.text.trim().toLowerCase();
    final p = _pass.text;
    if (!RegExp(r'^[a-z0-9._-]{3,30}$').hasMatch(u) || p.length < 6) {
      setState(() => _err = app.t('short'));
      return;
    }
    setState(() {
      _busy = true;
      _err = null;
    });
    final email = '$u@$usernameDomain';
    try {
      if (_register) {
        final free = await sb.rpc('app_username_free', params: {'p_username': u});
        if (free != true) {
          setState(() => _err = app.t('taken'));
          return;
        }
        final res = await sb.auth.signUp(email: email, password: p);
        if (res.session == null) {
          setState(() => _err = app.t('no_confirm'));
          return;
        }
      } else {
        await sb.auth.signInWithPassword(email: email, password: p);
      }
      // AuthGate (main.dart) takes over from here.
    } catch (e) {
      setState(() => _err = errText(e, app.lang));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: app,
      builder: (context, _) => Scaffold(
        body: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(28),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 420),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Icon(Icons.account_balance_wallet_rounded, size: 64, color: kGreen),
                    const SizedBox(height: 12),
                    Text(app.t('app'),
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w700)),
                    const SizedBox(height: 28),
                    TextField(
                      controller: _user,
                      autocorrect: false,
                      textDirection: TextDirection.ltr,
                      textInputAction: TextInputAction.next,
                      autofillHints: const [AutofillHints.username],
                      decoration: InputDecoration(
                        labelText: app.t('username'),
                        border: const OutlineInputBorder(),
                        filled: true,
                        fillColor: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _pass,
                      obscureText: true,
                      textDirection: TextDirection.ltr,
                      onSubmitted: (_) => _submit(),
                      autofillHints: const [AutofillHints.password],
                      decoration: InputDecoration(
                        labelText: app.t('password'),
                        border: const OutlineInputBorder(),
                        filled: true,
                        fillColor: Colors.white,
                      ),
                    ),
                    if (_err != null) ...[
                      const SizedBox(height: 12),
                      Text(_err!, style: const TextStyle(color: kExpense), textAlign: TextAlign.center),
                    ],
                    const SizedBox(height: 20),
                    FilledButton(
                      onPressed: _busy ? null : _submit,
                      style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(50)),
                      child: _busy
                          ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                          : Text(app.t(_register ? 'register' : 'login')),
                    ),
                    TextButton(
                      onPressed: () => setState(() {
                        _register = !_register;
                        _err = null;
                      }),
                      child: Text(app.t(_register ? 'login' : 'register')),
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      alignment: WrapAlignment.center,
                      spacing: 8,
                      children: [
                        for (final l in kLangs)
                          ChoiceChip(
                            label: Text(kLangNames[l]!),
                            selected: app.lang == l,
                            onSelected: (_) => app.setLang(l),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
