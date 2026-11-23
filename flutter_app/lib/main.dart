import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'config.dart';
import 'pages/auth_page.dart';
import 'pages/cases_page.dart';
import 'pages/entries_page.dart';
import 'pages/entry_sheet.dart';
import 'pages/home_page.dart';
import 'state.dart';
import 'ui.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.dark,
    statusBarBrightness: Brightness.light,
  ));
  await Supabase.initialize(url: supabaseUrl, anonKey: supabaseAnonKey);
  await app.init();
  runApp(const WalletApp());
}

class WalletApp extends StatelessWidget {
  const WalletApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: app,
      builder: (context, _) => MaterialApp(
        title: app.t('app'),
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          useMaterial3: true,
          colorSchemeSeed: kGreen,
          scaffoldBackgroundColor: kCream,
          appBarTheme: const AppBarTheme(
            backgroundColor: kCream,
            surfaceTintColor: Colors.transparent,
            elevation: 0,
          ),
          navigationBarTheme: const NavigationBarThemeData(
            backgroundColor: Colors.white,
            surfaceTintColor: Colors.transparent,
          ),
        ),
        builder: (context, child) => Directionality(
          textDirection: app.rtl ? TextDirection.rtl : TextDirection.ltr,
          child: child!,
        ),
        home: const AuthGate(),
      ),
    );
  }
}

/// Shows the login screen or the app depending on the Supabase session.
class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  bool _started = false;

  @override
  void initState() {
    super.initState();
    if (sb.auth.currentSession != null) _boot();
    sb.auth.onAuthStateChange.listen((s) {
      if (s.event == AuthChangeEvent.signedOut) {
        app.reset();
        _started = false;
        if (mounted) setState(() {});
      } else if (s.session != null && !_started) {
        _boot();
      }
    });
  }

  Future<void> _boot() async {
    _started = true;
    try {
      await app.bootstrap();
    } catch (e) {
      app.error = errText(e, app.lang);
    }
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    if (sb.auth.currentSession == null) return const AuthPage();
    return const Shell();
  }
}

class Shell extends StatefulWidget {
  const Shell({super.key});

  @override
  State<Shell> createState() => _ShellState();
}

class _ShellState extends State<Shell> {
  int _tab = 0;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: app,
      builder: (context, _) {
        if (app.data == null) {
          return Scaffold(
            body: Center(
              child: app.error != null
                  ? Padding(
                      padding: const EdgeInsets.all(32),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(app.error!, textAlign: TextAlign.center),
                          const SizedBox(height: 16),
                          FilledButton(onPressed: app.bootstrap, child: Text(app.t('retry'))),
                          TextButton(onPressed: () => sb.auth.signOut(), child: Text(app.t('logout'))),
                        ],
                      ),
                    )
                  : const CircularProgressIndicator(),
            ),
          );
        }
        final pages = <Widget>[
          const HomePage(),
          const EntriesPage(type: 'income'),
          const SizedBox.shrink(),
          const EntriesPage(type: 'expense'),
          const CasesPage(),
        ];
        return Scaffold(
          body: IndexedStack(index: _tab, children: pages),
          floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
          floatingActionButton: app.canEdit && app.accId != null
              ? FloatingActionButton(
                  shape: const CircleBorder(),
                  onPressed: () => showEntrySheet(
                    context,
                    type: _tab == 3 ? 'expense' : 'income',
                    allowTypeChoice: true,
                  ),
                  child: const Icon(Icons.add),
                )
              : null,
          bottomNavigationBar: NavigationBar(
            selectedIndex: _tab,
            onDestinationSelected: (i) {
              if (i == 2) return;
              setState(() => _tab = i);
            },
            destinations: [
              NavigationDestination(icon: const Icon(Icons.home_outlined), selectedIcon: const Icon(Icons.home), label: app.t('home')),
              NavigationDestination(icon: const Icon(Icons.south_west), label: app.t('income')),
              const NavigationDestination(icon: SizedBox(width: 24), label: ''),
              NavigationDestination(icon: const Icon(Icons.north_east), label: app.t('expenses')),
              NavigationDestination(icon: const Icon(Icons.gavel_outlined), selectedIcon: const Icon(Icons.gavel), label: app.t('cases')),
            ],
          ),
        );
      },
    );
  }
}
