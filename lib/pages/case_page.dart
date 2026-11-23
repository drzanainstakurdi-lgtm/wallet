import 'package:flutter/material.dart';

import '../state.dart';
import '../ui.dart';

class CasePage extends StatefulWidget {
  const CasePage({super.key, required this.caseId});

  final int caseId;

  @override
  State<CasePage> createState() => _CasePageState();
}

class _CasePageState extends State<CasePage> {
  Map<String, dynamic>? _v;
  String? _err;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await sb.rpc('api_case_view', params: {'p_case': widget.caseId});
      if (r == null) throw Exception('not found');
      if (mounted) setState(() => _v = Map<String, dynamic>.from(r as Map));
    } catch (e) {
      if (mounted) setState(() => _err = errText(e, app.lang));
    }
  }

  Future<void> _add(String type) async {
    final cont = TextEditingController();
    final label = TextEditingController(text: type == 'income' ? app.t('received') : '');
    final amountCtl = cont;
    DateTime date = DateTime.now();
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (c) => StatefulBuilder(
        builder: (c, setS) => Padding(
          padding: EdgeInsets.fromLTRB(20, 18, 20, 20 + MediaQuery.of(c).viewInsets.bottom),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text(app.t(type == 'income' ? 'received' : 'spent'),
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: type == 'income' ? kIncome : kExpense)),
            const SizedBox(height: 12),
            TextField(
              controller: amountCtl,
              autofocus: true,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              textDirection: TextDirection.ltr,
              decoration: InputDecoration(labelText: app.t('amount'), border: const OutlineInputBorder()),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: label,
              decoration: InputDecoration(labelText: app.t('label'), border: const OutlineInputBorder()),
            ),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: () async {
                final d = await showDatePicker(
                  context: c,
                  initialDate: date,
                  firstDate: DateTime(2000),
                  lastDate: DateTime(DateTime.now().year + 2),
                );
                if (d != null) setS(() => date = d);
              },
              icon: const Icon(Icons.event),
              label: Text(ymd(date)),
            ),
            const SizedBox(height: 14),
            FilledButton(
              onPressed: () => Navigator.pop(c, true),
              style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
              child: Text(app.t('save')),
            ),
          ]),
        ),
      ),
    );
    final amt = parseAmount(amountCtl.text);
    final lbl = label.text.trim();
    if (ok != true || amt <= 0) return;
    try {
      await app.addTx(widget.caseId, type, amt, lbl, '', date);
      await _load();
    } catch (e) {
      if (mounted) toast(context, errText(e, app.lang));
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = _v;
    if (v == null) {
      return Scaffold(
        appBar: AppBar(),
        body: Center(child: _err != null ? Text(_err!) : const CircularProgressIndicator()),
      );
    }
    final c = Map<String, dynamic>.from(v['case'] as Map);
    final cur = c['currency'].toString();
    final role = v['role']?.toString() ?? 'owner';
    final canEdit = role != 'viewer';
    final owner = role == 'owner';
    final fee = dbl(c['fee']);
    final inc = dbl(v['inc']);
    final exp = dbl(v['exp']);
    final closed = c['status'] == 'closed';
    final items = listOfMaps(v['items']);
    final clients = (c['clients'] is List) ? (c['clients'] as List).join(' + ') : (c['client'] ?? '').toString();
    final parties = (c['parties'] is List) ? (c['parties'] as List).join(' + ') : (c['party'] ?? '').toString();

    Widget info(String k, String? val) => (val == null || val.isEmpty)
        ? const SizedBox.shrink()
        : Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              SizedBox(width: 110, child: Text(app.t(k), style: const TextStyle(color: Colors.black54))),
              Expanded(child: Text(val)),
            ]),
          );

    return Scaffold(
      appBar: AppBar(
        title: Text(c['name'].toString(), overflow: TextOverflow.ellipsis),
        actions: [
          if (owner)
            PopupMenuButton<String>(
              onSelected: (s) async {
                try {
                  if (s == 'status') {
                    await sb.rpc('api_case_status', params: {'p_case': widget.caseId, 'p_status': closed ? 'open' : 'closed'});
                    await app.load(quiet: true);
                    await _load();
                  } else if (s == 'delete') {
                    if (await confirmDialog(context, app.t('confirm_del'))) {
                      await sb.rpc('api_delete_case', params: {'p_case': widget.caseId});
                      await app.load(quiet: true);
                      if (mounted) Navigator.pop(context);
                    }
                  }
                } catch (e) {
                  if (mounted) toast(context, errText(e, app.lang));
                }
              },
              itemBuilder: (_) => [
                PopupMenuItem(value: 'status', child: Text(app.t(closed ? 'open' : 'closed'))),
                PopupMenuItem(value: 'delete', child: Text(app.t('delete'))),
              ],
            ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.only(bottom: 40),
          children: [
            Panel(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                info('clients', clients),
                info('party', parties),
                info('case_no', c['case_no']?.toString()),
                info('court', c['court']?.toString()),
                info('hearing', c['hearing']?.toString()),
                info('started', c['started']?.toString()),
                info('status', app.t(closed ? 'closed' : 'open')),
              ]),
            ),
            Panel(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${app.t('fee')}: ${money(fee, cur)}', style: const TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                if (fee > 0)
                  ClipRRect(
                    borderRadius: BorderRadius.circular(6),
                    child: LinearProgressIndicator(
                        value: (inc / fee).clamp(0.0, 1.0), minHeight: 8, color: kGreen, backgroundColor: Colors.black12),
                  ),
                const SizedBox(height: 8),
                Text('${app.t('received')}: ${money(inc, cur)}', style: const TextStyle(color: kIncome)),
                Text('${app.t('spent')}: ${money(exp, cur)}', style: const TextStyle(color: kExpense)),
                if (fee > 0) Text('${app.t('remaining')}: ${money((fee - inc).clamp(0, double.infinity).toDouble(), cur)}'),
              ]),
            ),
            if (canEdit)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                child: Row(children: [
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: () => _add('income'),
                      icon: const Icon(Icons.south_west),
                      label: Text(app.t('received')),
                      style: FilledButton.styleFrom(backgroundColor: kIncome),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: () => _add('expense'),
                      icon: const Icon(Icons.north_east),
                      label: Text(app.t('spent')),
                      style: FilledButton.styleFrom(backgroundColor: kExpense),
                    ),
                  ),
                ]),
              ),
            if (items.isEmpty) Padding(padding: const EdgeInsets.all(24), child: Center(child: Text(app.t('nodata')))),
            for (final it in items)
              Dismissible(
                key: ValueKey('ct${it['id']}'),
                direction: canEdit ? DismissDirection.endToStart : DismissDirection.none,
                background: Container(
                  color: kExpense,
                  alignment: Alignment.centerRight,
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: const Icon(Icons.delete, color: Colors.white),
                ),
                confirmDismiss: (_) async {
                  if (!await confirmDialog(context, app.t('confirm_del'))) return false;
                  try {
                    await app.delTx(intOrNull(it['id'])!);
                    await _load();
                  } catch (e) {
                    if (context.mounted) toast(context, errText(e, app.lang));
                  }
                  return false;
                },
                child: _CaseEntry(item: it, cur: cur),
              ),
          ],
        ),
      ),
    );
  }
}

class _CaseEntry extends StatelessWidget {
  const _CaseEntry({required this.item, required this.cur});

  final Map<String, dynamic> item;
  final String cur;

  @override
  Widget build(BuildContext context) {
    final income = item['type'] == 'income';
    final label = (item['label']?.toString() ?? '').isEmpty ? '-' : item['label'].toString();
    return Panel(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(children: [
        Icon(income ? Icons.south_west : Icons.north_east, size: 18, color: income ? kIncome : kExpense),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w600)),
            Text(item['date'].toString(), style: const TextStyle(fontSize: 12, color: Colors.black54)),
          ]),
        ),
        Text('${income ? '+' : '-'}${money(dbl(item['amount']), cur)}',
            style: TextStyle(fontWeight: FontWeight.w700, color: income ? kIncome : kExpense),
            textDirection: TextDirection.ltr),
      ]),
    );
  }
}
