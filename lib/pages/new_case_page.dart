import 'package:flutter/material.dart';

import '../case_ui.dart';
import '../state.dart';
import '../ui.dart';
import 'case_page.dart';

class NewCasePage extends StatefulWidget {
  const NewCasePage({super.key});

  @override
  State<NewCasePage> createState() => _NewCasePageState();
}

class _NewCasePageState extends State<NewCasePage> {
  final _name = TextEditingController();
  final _client = TextEditingController();
  final _party = TextEditingController();
  final _no = TextEditingController();
  final _court = TextEditingController();
  final _fee = TextEditingController();
  final _advance = TextEditingController();
  String _cur = 'IQD';
  String _ctype = 'court';
  DateTime? _hearing;
  bool _busy = false;
  String? _err;

  @override
  void dispose() {
    for (final c in [_name, _client, _party, _no, _court, _fee, _advance]) {
      c.dispose();
    }
    super.dispose();
  }

  // "Ali + Sara" or "Ali, Sara" -> ['Ali', 'Sara']
  List<String> _people(String s) =>
      s.split(RegExp(r'[+,،]')).map((e) => e.trim()).where((e) => e.isNotEmpty).toList();

  Future<void> _save() async {
    if (_name.text.trim().isEmpty) {
      setState(() => _err = '${app.t('name')}?');
      return;
    }
    setState(() {
      _busy = true;
      _err = null;
    });
    try {
      final id = await sb.rpc('api_new_case', params: {
        'p_name': _name.text.trim(),
        'p_currency': _cur,
        'p_clients': _people(_client.text),
        'p_parties': _people(_party.text),
        'p_case_no': _no.text.trim(),
        'p_court': _court.text.trim(),
        'p_fee': parseAmount(_fee.text),
        'p_ctype': _ctype,
        'p_started': ymd(DateTime.now()),
        'p_hearing': _hearing == null ? null : ymd(_hearing!),
        'p_price': 0,
        'p_advance': parseAmount(_advance.text),
      });
      await app.load(quiet: true);
      if (!mounted) return;
      Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => CasePage(caseId: intOrNull(id)!)));
    } catch (e) {
      setState(() {
        _err = errText(e, app.lang);
        _busy = false;
      });
    }
  }

  Widget _section(String title, List<Widget> children) => SoftCard(
        padding: const EdgeInsets.fromLTRB(14, 14, 14, 6),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
          const SizedBox(height: 12),
          ...children,
        ]),
      );

  Widget _f(TextEditingController c, String label, {bool number = false, IconData? icon, String? hint}) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: TextField(
          controller: c,
          keyboardType: number ? const TextInputType.numberWithOptions(decimal: true) : TextInputType.text,
          textDirection: number ? TextDirection.ltr : null,
          decoration: InputDecoration(
            labelText: label,
            hintText: hint,
            prefixIcon: icon == null ? null : Icon(icon, size: 20, color: kSlate),
            filled: true,
            fillColor: kPaper,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
          ),
        ),
      );

  Widget _typeTiles() => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Row(children: [
          for (final k in ['court', 'house', 'car', 'other'])
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 3),
                child: InkWell(
                  borderRadius: BorderRadius.circular(12),
                  onTap: () => setState(() => _ctype = k),
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    decoration: BoxDecoration(
                      color: _ctype == k ? typeColor(k) : const Color(0xFFF6F7F9),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Column(children: [
                      Icon(typeIcon(k), color: _ctype == k ? Colors.white : kSlate),
                      const SizedBox(height: 4),
                      Text(app.t('ct_$k'),
                          style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: _ctype == k ? Colors.white : kSlate)),
                    ]),
                  ),
                ),
              ),
            ),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kPaper,
      body: Column(children: [
        PageHeader(title: app.t('new_case'), back: true),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.only(top: 12, bottom: 24),
            children: [
              _section(app.t('basics'), [
                _f(_name, app.t('name'), icon: Icons.folder_outlined),
                _typeTiles(),
              ]),
              _section(app.t('people'), [
                _f(_client, app.t('clients'), icon: Icons.person_outline, hint: app.t('hint_people')),
                _f(_party, app.t('party'), icon: Icons.people_outline, hint: app.t('hint_people')),
              ]),
              _section(app.t('court_info'), [
                _f(_no, app.t('case_no'), icon: Icons.tag),
                _f(_court, app.t('court'), icon: Icons.account_balance_outlined),
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: OutlinedButton.icon(
                    onPressed: () async {
                      final d = await showDatePicker(
                        context: context,
                        initialDate: _hearing ?? DateTime.now(),
                        firstDate: DateTime(2000),
                        lastDate: DateTime(DateTime.now().year + 5),
                      );
                      if (d != null) setState(() => _hearing = d);
                    },
                    icon: const Icon(Icons.event),
                    label: Text('${app.t('hearing')}: ${_hearing == null ? '-' : ymd(_hearing!)}'),
                    style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(48), foregroundColor: kInk),
                  ),
                ),
              ]),
              _section(app.t('money'), [
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: SegmentedButton<String>(
                    segments: const [ButtonSegment(value: 'IQD', label: Text('IQD')), ButtonSegment(value: 'USD', label: Text('USD'))],
                    selected: {_cur},
                    onSelectionChanged: (s) => setState(() => _cur = s.first),
                  ),
                ),
                _f(_fee, app.t('fee'), number: true, icon: Icons.payments_outlined),
                _f(_advance, app.t('advance'), number: true, icon: Icons.south_west),
              ]),
              if (_err != null)
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 4, 20, 0),
                  child: Text(_err!, style: const TextStyle(color: kExpense)),
                ),
            ],
          ),
        ),
        Container(
          color: Colors.white,
          padding: EdgeInsets.fromLTRB(16, 10, 16, 10 + MediaQuery.of(context).padding.bottom),
          child: FilledButton(
            onPressed: _busy ? null : _save,
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52), backgroundColor: kInk),
            child: _busy
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : Text(app.t('create'), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
          ),
        ),
      ]),
    );
  }
}
