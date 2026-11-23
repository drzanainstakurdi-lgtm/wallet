import 'package:flutter/material.dart';

import '../nav.dart';
import '../state.dart';
import '../ui.dart';
import 'case_page.dart';

class CasesPage extends StatelessWidget {
  const CasesPage({super.key});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: app,
      builder: (context, _) {
        final cases = app.cases;
        return Scaffold(
          appBar: AppBar(
            title: Text(app.t('cases')),
            actions: [
              IconButton(icon: const Icon(Icons.add_circle_outline), onPressed: () => showNewCase(context)),
              IconButton(icon: const Icon(Icons.settings_outlined), onPressed: () => openSettings(context)),
            ],
          ),
          body: RefreshIndicator(
            onRefresh: () => app.load(quiet: true),
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.only(bottom: 110, top: 8),
              children: [
                if (cases.isEmpty)
                  Padding(padding: const EdgeInsets.all(32), child: Center(child: Text(app.t('nodata')))),
                for (final c in cases) _CaseTile(c: c),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _CaseTile extends StatelessWidget {
  const _CaseTile({required this.c});

  final Map<String, dynamic> c;

  @override
  Widget build(BuildContext context) {
    final cur = c['currency'].toString();
    final fee = dbl(c['fee']);
    final inc = dbl(c['inc']);
    final exp = dbl(c['exp']);
    final closed = c['status'] == 'closed';
    final remaining = (fee - inc).clamp(0, double.infinity);
    return Panel(
      onTap: () => Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => CasePage(caseId: intOrNull(c['id'])!)),
      ),
      child: Opacity(
        opacity: closed ? 0.6 : 1,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(
              child: Text(c['name'].toString(),
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700), overflow: TextOverflow.ellipsis),
            ),
            if (closed)
              Chip(label: Text(app.t('closed')), visualDensity: VisualDensity.compact, padding: EdgeInsets.zero),
          ]),
          if ((c['client']?.toString() ?? '').isNotEmpty)
            Text(c['client'].toString(), style: const TextStyle(color: Colors.black54)),
          if ((c['case_no']?.toString() ?? '').isNotEmpty || (c['court']?.toString() ?? '').isNotEmpty)
            Text('${c['case_no'] ?? ''}  ${c['court'] ?? ''}'.trim(),
                style: const TextStyle(color: Colors.black54, fontSize: 13)),
          const SizedBox(height: 10),
          if (fee > 0)
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(
                value: (inc / fee).clamp(0.0, 1.0),
                minHeight: 6,
                color: kGreen,
                backgroundColor: Colors.black12,
              ),
            ),
          const SizedBox(height: 8),
          Wrap(spacing: 14, runSpacing: 4, children: [
            Text('${app.t('fee')}: ${money(fee, cur)}', style: const TextStyle(fontSize: 13)),
            Text('${app.t('received')}: ${money(inc, cur)}', style: const TextStyle(fontSize: 13, color: kIncome)),
            Text('${app.t('spent')}: ${money(exp, cur)}', style: const TextStyle(fontSize: 13, color: kExpense)),
            if (fee > 0) Text('${app.t('remaining')}: ${money(remaining.toDouble(), cur)}', style: const TextStyle(fontSize: 13)),
          ]),
        ]),
      ),
    );
  }
}

Future<void> showNewCase(BuildContext context) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.white,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
    builder: (c) => const _NewCaseSheet(),
  );
}

class _NewCaseSheet extends StatefulWidget {
  const _NewCaseSheet();

  @override
  State<_NewCaseSheet> createState() => _NewCaseSheetState();
}

class _NewCaseSheetState extends State<_NewCaseSheet> {
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
      setState(() => _err = app.t('name'));
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
      Navigator.pop(context);
      Navigator.push(context, MaterialPageRoute(builder: (_) => CasePage(caseId: intOrNull(id)!)));
    } catch (e) {
      setState(() {
        _err = errText(e, app.lang);
        _busy = false;
      });
    }
  }

  Widget _field(TextEditingController c, String key, {bool number = false}) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: TextField(
          controller: c,
          keyboardType: number ? const TextInputType.numberWithOptions(decimal: true) : TextInputType.text,
          decoration: InputDecoration(labelText: app.t(key), border: const OutlineInputBorder()),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final bottom = MediaQuery.of(context).viewInsets.bottom;
    return Padding(
      padding: EdgeInsets.fromLTRB(20, 18, 20, 20 + bottom),
      child: SingleChildScrollView(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text(app.t('new_case'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
          const SizedBox(height: 14),
          _field(_name, 'name'),
          _field(_client, 'client'),
          _field(_party, 'party'),
          _field(_no, 'case_no'),
          _field(_court, 'court'),
          _field(_fee, 'fee', number: true),
          _field(_advance, 'advance', number: true),
          SegmentedButton<String>(
            segments: const [ButtonSegment(value: 'IQD', label: Text('IQD')), ButtonSegment(value: 'USD', label: Text('USD'))],
            selected: {_cur},
            onSelectionChanged: (s) => setState(() => _cur = s.first),
          ),
          const SizedBox(height: 10),
          SegmentedButton<String>(
            segments: [
              for (final k in ['court', 'house', 'car', 'other']) ButtonSegment(value: k, label: Text(app.t('ct_$k'))),
            ],
            selected: {_ctype},
            onSelectionChanged: (s) => setState(() => _ctype = s.first),
          ),
          const SizedBox(height: 10),
          OutlinedButton.icon(
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
          ),
          if (_err != null) ...[
            const SizedBox(height: 10),
            Text(_err!, style: const TextStyle(color: kExpense)),
          ],
          const SizedBox(height: 14),
          FilledButton(
            onPressed: _busy ? null : _save,
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
            child: _busy
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : Text(app.t('save')),
          ),
        ]),
      ),
    );
  }
}
