import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../i18n.dart';
import '../state.dart';
import '../ui.dart';

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: app,
      builder: (context, _) {
        final p = app.profile;
        return Scaffold(
          appBar: AppBar(title: Text(app.t('settings'))),
          body: ListView(
            padding: const EdgeInsets.only(bottom: 40),
            children: [
              Panel(
                child: Row(children: [
                  const CircleAvatar(child: Icon(Icons.person)),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(p?['username']?.toString() ?? '', style: const TextStyle(fontWeight: FontWeight.w700)),
                      if ((p?['display_name']?.toString() ?? '').isNotEmpty) Text(p!['display_name'].toString()),
                    ]),
                  ),
                ]),
              ),
              Panel(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(app.t('language'), style: const TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 10),
                  Wrap(spacing: 8, children: [
                    for (final l in kLangs)
                      ChoiceChip(label: Text(kLangNames[l]!), selected: app.lang == l, onSelected: (_) => app.setLang(l)),
                  ]),
                ]),
              ),
              Panel(
                onTap: () => _profileSheet(context),
                child: Row(children: [
                  const Icon(Icons.badge_outlined),
                  const SizedBox(width: 12),
                  Expanded(child: Text(app.t('profile'))),
                  const Icon(Icons.chevron_right),
                ]),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 14, 20, 4),
                child: Row(children: [
                  Expanded(child: Text(app.t('accounts'), style: const TextStyle(fontWeight: FontWeight.w700))),
                  TextButton.icon(
                    onPressed: () => _accountSheet(context),
                    icon: const Icon(Icons.add),
                    label: Text(app.t('new_acc')),
                  ),
                ]),
              ),
              for (final a in app.accounts.where((a) => a['role'] == 'owner'))
                Panel(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  child: Row(children: [
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(a['name'].toString(), style: const TextStyle(fontWeight: FontWeight.w600)),
                        Text(
                          '${a['currency']}  •  ${app.t('budget')}: ${money(dbl(a['budget']), a['currency'].toString())}',
                          style: const TextStyle(fontSize: 12, color: Colors.black54),
                        ),
                      ]),
                    ),
                    IconButton(icon: const Icon(Icons.savings_outlined), onPressed: () => _budgetSheet(context, a)),
                    IconButton(
                      icon: const Icon(Icons.delete_outline, color: kExpense),
                      onPressed: () async {
                        if (!await confirmDialog(context, app.t('confirm_del'))) return;
                        try {
                          final ok = await sb.rpc('api_delete_account', params: {'p_acc': intOrNull(a['id'])});
                          if (ok != true) {
                            if (context.mounted) toast(context, app.t('noacc_del'));
                            return;
                          }
                          if (app.accId == intOrNull(a['id'])) app.accId = null;
                          await app.load(quiet: true);
                        } catch (e) {
                          if (context.mounted) toast(context, errText(e, app.lang));
                        }
                      },
                    ),
                  ]),
                ),
              Panel(
                onTap: () => _passwordSheet(context),
                child: Row(children: [
                  const Icon(Icons.lock_outline),
                  const SizedBox(width: 12),
                  Expanded(child: Text(app.t('change_pw'))),
                  const Icon(Icons.chevron_right),
                ]),
              ),
              Panel(
                onTap: () => app.signOut(),
                child: Row(children: [
                  const Icon(Icons.logout, color: kExpense),
                  const SizedBox(width: 12),
                  Text(app.t('logout'), style: const TextStyle(color: kExpense, fontWeight: FontWeight.w600)),
                ]),
              ),
            ],
          ),
        );
      },
    );
  }

  // ---------- small form sheets ----------

  Future<void> _form(
    BuildContext context, {
    required String title,
    required List<(String, TextEditingController, bool, bool)> fields, // label, controller, number, obscure
    required Future<void> Function() onSave,
    Widget? extra,
  }) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (c) => Padding(
        padding: EdgeInsets.fromLTRB(20, 18, 20, 20 + MediaQuery.of(c).viewInsets.bottom),
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
            const SizedBox(height: 14),
            for (final f in fields)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: TextField(
                  controller: f.$2,
                  obscureText: f.$4,
                  keyboardType: f.$3 ? const TextInputType.numberWithOptions(decimal: true) : TextInputType.text,
                  decoration: InputDecoration(labelText: f.$1, border: const OutlineInputBorder()),
                ),
              ),
            if (extra != null) extra,
            FilledButton(
              onPressed: () async {
                try {
                  await onSave();
                  if (c.mounted) Navigator.pop(c);
                  if (context.mounted) toast(context, app.t('saved'));
                } catch (e) {
                  if (c.mounted) toast(c, errText(e, app.lang));
                }
              },
              style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
              child: Text(app.t('save')),
            ),
          ]),
        ),
      ),
    );
  }

  Future<void> _profileSheet(BuildContext context) {
    final p = app.profile ?? {};
    final name = TextEditingController(text: p['display_name']?.toString() ?? '');
    final phone = TextEditingController(text: p['phone']?.toString() ?? '');
    final office = TextEditingController(text: p['office']?.toString() ?? '');
    return _form(
      context,
      title: app.t('profile'),
      fields: [
        (app.t('display_name'), name, false, false),
        (app.t('phone'), phone, false, false),
        (app.t('office'), office, false, false),
      ],
      onSave: () async {
        await sb.rpc('api_set_profile', params: {
          'p_display_name': name.text.trim(),
          'p_phone': phone.text.trim(),
          'p_office': office.text.trim(),
        });
        await app.loadProfile();
      },
    );
  }

  Future<void> _accountSheet(BuildContext context) {
    final name = TextEditingController();
    final opening = TextEditingController();
    var cur = 'IQD';
    return _form(
      context,
      title: app.t('new_acc'),
      fields: [
        (app.t('name'), name, false, false),
        (app.t('opening'), opening, true, false),
      ],
      extra: StatefulBuilder(
        builder: (c, setS) => Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: SegmentedButton<String>(
            segments: const [ButtonSegment(value: 'IQD', label: Text('IQD')), ButtonSegment(value: 'USD', label: Text('USD'))],
            selected: {cur},
            onSelectionChanged: (s) => setS(() => cur = s.first),
          ),
        ),
      ),
      onSave: () async {
        if (name.text.trim().isEmpty) throw Exception(app.t('name'));
        final id = await sb.rpc('api_new_account', params: {
          'p_name': name.text.trim(),
          'p_currency': cur,
          'p_opening': parseAmount(opening.text),
        });
        app.accId = intOrNull(id);
        await app.load(quiet: true);
      },
    );
  }

  Future<void> _budgetSheet(BuildContext context, Map<String, dynamic> a) {
    final b = TextEditingController(text: dbl(a['budget']) > 0 ? dbl(a['budget']).round().toString() : '');
    return _form(
      context,
      title: '${app.t('budget')} - ${a['name']}',
      fields: [(app.t('budget'), b, true, false)],
      onSave: () async {
        await sb.rpc('api_set_budget', params: {'p_acc': intOrNull(a['id']), 'p_budget': parseAmount(b.text)});
        await app.load(quiet: true);
      },
    );
  }

  Future<void> _passwordSheet(BuildContext context) {
    final pw = TextEditingController();
    return _form(
      context,
      title: app.t('change_pw'),
      fields: [(app.t('new_pw'), pw, false, true)],
      onSave: () async {
        if (pw.text.length < 6) throw Exception(app.t('short'));
        await sb.auth.updateUser(UserAttributes(password: pw.text));
      },
    );
  }
}
