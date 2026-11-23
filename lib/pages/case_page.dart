import 'package:flutter/material.dart';

import '../case_ui.dart';
import '../export.dart';
import '../state.dart';
import '../ui.dart';
import 'entry_sheet.dart';

const TextStyle _tab = TextStyle(fontFeatures: [FontFeature.tabularFigures()]);

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

  Future<void> _entry(String type, {Map<String, dynamic>? item}) async {
    await showEntrySheet(
      context,
      type: type,
      item: item,
      accountId: widget.caseId,
      presetLabel: (type == 'income' && item == null) ? app.t('received') : null,
    );
    await _load();
  }

  Future<bool> _ask(String title, String msg, String okLabel) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: Text(title),
        content: Text(msg),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: Text(app.t('cancel'))),
          TextButton(onPressed: () => Navigator.pop(d, true), child: Text(okLabel)),
        ],
      ),
    );
    return ok == true;
  }

  Future<int> _archiveDays() async {
    final a = await sb.rpc('api_archive');
    return intOrNull((a as Map)['days']) ?? 0;
  }

  Future<void> _menu(String sel) async {
    try {
      if (sel == 'download') {
        await shareCaseCsv(widget.caseId);
      } else if (sel == 'finish') {
        final days = await _archiveDays();
        final msg = days > 0 ? app.t('finish_msg').replaceAll('%d', '$days') : app.t('finish_keep');
        if (!mounted) return;
        if (await _ask(app.t('finish'), msg, app.t('finish_do'))) {
          await sb.rpc('api_case_status', params: {'p_case': widget.caseId, 'p_status': 'closed'});
          await app.load(quiet: true);
          if (mounted) Navigator.pop(context);
        }
      } else if (sel == 'reopen') {
        await sb.rpc('api_case_status', params: {'p_case': widget.caseId, 'p_status': 'open'});
        await app.load(quiet: true);
        await _load();
      } else if (sel == 'delete') {
        final days = await _archiveDays();
        final msg = days > 0 ? app.t('delete_msg').replaceAll('%d', '$days') : app.t('delete_keep');
        if (!mounted) return;
        if (await _ask(app.t('delete'), msg, app.t('delete'))) {
          await sb.rpc('api_delete_case', params: {'p_case': widget.caseId});
          await app.load(quiet: true);
          if (mounted) Navigator.pop(context);
        }
      } else if (sel == 'purge') {
        if (await _ask(app.t('purge_now'), app.t('purge_msg'), app.t('purge_now'))) {
          await sb.rpc('api_purge_case', params: {'p_case': widget.caseId});
          await app.load(quiet: true);
          if (mounted) Navigator.pop(context);
        }
      }
    } catch (e) {
      if (mounted) toast(context, errText(e, app.lang));
    }
  }

  // ---------- pieces ----------

  Widget _mini(String label, String value, Color color) => Expanded(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 12),
          decoration: BoxDecoration(color: color.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(16)),
          child: Column(children: [
            Text(label, style: const TextStyle(fontSize: 12, color: kSlate)),
            const SizedBox(height: 4),
            FittedBox(
              fit: BoxFit.scaleDown,
              child: Text(value, style: _tab.copyWith(fontSize: 15, fontWeight: FontWeight.w800, color: color)),
            ),
          ]),
        ),
      );

  Widget _kv(IconData icon, String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(12)),
            child: Icon(icon, size: 18, color: kInk),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(label, style: const TextStyle(color: kSlate, fontSize: 12)),
              const SizedBox(height: 1),
              Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14.5)),
            ]),
          ),
        ]),
      );

  Widget _entryRow(Map<String, dynamic> it, String cur, bool canEdit) {
    final income = it['type'] == 'income';
    final color = income ? kIncome : kExpense;
    final label = (it['label']?.toString() ?? '').trim();
    final note = (it['note']?.toString() ?? '').trim();
    final row = Container(
      margin: const EdgeInsetsDirectional.only(start: 26, end: 16),
      decoration: const BoxDecoration(border: BorderDirectional(start: BorderSide(color: Color(0xFFD5D9E1), width: 2))),
      child: Stack(clipBehavior: Clip.none, children: [
        PositionedDirectional(
          start: -7,
          top: 19,
          child: Container(
            width: 12,
            height: 12,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle, border: Border.all(color: kPaper, width: 2)),
          ),
        ),
        InkWell(
          onTap: canEdit ? () => _entry(income ? 'income' : 'expense', item: it) : null,
          child: Padding(
            padding: const EdgeInsetsDirectional.only(start: 16, top: 10, bottom: 10),
            child: Row(children: [
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(label.isEmpty ? app.t(income ? 'income_one' : 'expense_one') : label,
                      maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700)),
                  Text(note.isEmpty ? it['date'].toString() : '${it['date']}  -  $note',
                      maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, color: kSlate)),
                ]),
              ),
              Text('${income ? '+' : '-'}${money(dbl(it['amount']), cur)}',
                  textDirection: TextDirection.ltr, style: _tab.copyWith(fontWeight: FontWeight.w800, color: color)),
            ]),
          ),
        ),
      ]),
    );
    if (!canEdit) return row;
    return Dismissible(
      key: ValueKey('ct${it['id']}'),
      direction: DismissDirection.endToStart,
      background: Container(
        color: kExpense,
        alignment: AlignmentDirectional.centerEnd,
        padding: const EdgeInsets.symmetric(horizontal: 24),
        child: const Icon(Icons.delete, color: Colors.white),
      ),
      confirmDismiss: (_) async {
        if (!await confirmDialog(context, app.t('confirm_del'))) return false;
        try {
          await app.delTx(intOrNull(it['id'])!);
          await _load();
        } catch (e) {
          if (mounted) toast(context, errText(e, app.lang));
        }
        return false;
      },
      child: row,
    );
  }

  @override
  Widget build(BuildContext context) {
    final v = _v;
    if (v == null) {
      return Scaffold(
        backgroundColor: kPaper,
        appBar: AppBar(),
        body: Center(child: _err != null ? Text(_err!) : const CircularProgressIndicator()),
      );
    }
    final c = Map<String, dynamic>.from(v['case'] as Map);
    final cur = c['currency'].toString();
    final role = v['role']?.toString() ?? 'owner';
    final canEdit = role != 'viewer';
    final owner = role == 'owner';
    final closed = c['status'] == 'closed';
    final type = (c['ctype'] ?? 'court').toString();
    final fee = dbl(c['fee']);
    final inc = dbl(v['inc']);
    final exp = dbl(v['exp']);
    final remaining = fee > inc ? fee - inc : 0.0;
    final net = inc - exp;
    final price = dbl(c['price']);
    final items = listOfMaps(v['items']);
    final clients = (c['clients'] is List && (c['clients'] as List).isNotEmpty)
        ? (c['clients'] as List).join(' + ')
        : (c['client'] ?? '').toString();
    final parties = (c['parties'] is List && (c['parties'] as List).isNotEmpty)
        ? (c['parties'] as List).join(' + ')
        : (c['party'] ?? '').toString();
    final no = (c['case_no'] ?? '').toString().trim();
    final court = (c['court'] ?? '').toString().trim();
    final hearing = closed ? null : hearingInfo(c['hearing']);

    // group the entries by month
    final groups = <String, List<Map<String, dynamic>>>{};
    for (final it in items) {
      final d = it['date'].toString();
      (groups[d.length >= 7 ? d.substring(0, 7) : d] ??= []).add(it);
    }

    return Scaffold(
      backgroundColor: kPaper,
      body: RefreshIndicator(
        onRefresh: _load,
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverToBoxAdapter(
              child: PageHeader(
                title: c['name'].toString(),
                back: true,
                actions: [
                  PopupMenuButton<String>(
                    iconColor: Colors.white,
                    onSelected: _menu,
                    itemBuilder: (_) => [
                      PopupMenuItem(value: 'download', child: Text(app.t('download'))),
                      if (owner) PopupMenuItem(value: closed ? 'reopen' : 'finish', child: Text(app.t(closed ? 'reopen' : 'finish'))),
                      if (owner && !closed) PopupMenuItem(value: 'delete', child: Text(app.t('delete'))),
                      if (owner && closed) PopupMenuItem(value: 'purge', child: Text(app.t('purge_now'))),
                    ],
                  ),
                ],
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Wrap(spacing: 8, runSpacing: 8, children: [
                    BandChip(typeIcon(type), app.t('ct_$type')),
                    BandChip(closed ? Icons.inventory_2_outlined : Icons.lock_open_outlined, app.t(closed ? 'closed' : 'open')),
                    if (no.isNotEmpty) BandChip(Icons.tag, no),
                  ]),
                  if (clients.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Row(children: [
                      const Icon(Icons.person_outline, size: 16, color: Colors.white70),
                      const SizedBox(width: 6),
                      Expanded(child: Text(clients, style: const TextStyle(color: Colors.white, fontSize: 14))),
                    ]),
                  ],
                  if (hearing != null) ...[
                    const SizedBox(height: 14),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      decoration: BoxDecoration(
                        color: kBrass.withValues(alpha: 0.24),
                        borderRadius: BorderRadius.circular(18),
                        border: Border.all(color: kBrassLight.withValues(alpha: 0.35)),
                      ),
                      child: Row(children: [
                        const Icon(Icons.event, color: kBrassLight, size: 20),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text('${app.t('hearing')}: ${c['hearing']}',
                              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
                        ),
                        Text(hearing.text, style: const TextStyle(color: kBrassLight, fontWeight: FontWeight.w800)),
                      ]),
                    ),
                  ],
                ]),
              ),
            ),
            // money
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.only(top: 12),
                child: SoftCard(
                  padding: const EdgeInsets.all(18),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    if (fee > 0) ...[
                      Row(children: [
                        Expanded(
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text(app.t('remaining'), style: const TextStyle(color: kSlate, fontSize: 13)),
                            const SizedBox(height: 2),
                            FittedBox(
                              fit: BoxFit.scaleDown,
                              alignment: AlignmentDirectional.centerStart,
                              child: Text(money(remaining, cur),
                                  style: _tab.copyWith(fontSize: 30, fontWeight: FontWeight.w800, color: remaining > 0 ? kInk : kIncome)),
                            ),
                            const SizedBox(height: 4),
                            Text('${app.t('fee')}: ${money(fee, cur)}', style: const TextStyle(color: kSlate, fontSize: 13)),
                          ]),
                        ),
                        const SizedBox(width: 12),
                        SizedBox(
                          width: 70,
                          height: 70,
                          child: Stack(alignment: Alignment.center, children: [
                            SizedBox(
                              width: 70,
                              height: 70,
                              child: CircularProgressIndicator(
                                value: (inc / fee).clamp(0.0, 1.0),
                                strokeWidth: 8,
                                strokeCap: StrokeCap.round,
                                color: inc >= fee ? kIncome : kBrass,
                                backgroundColor: kLine,
                              ),
                            ),
                            Text('${((inc / fee).clamp(0.0, 1.0) * 100).round()}%',
                                style: _tab.copyWith(fontSize: 14, fontWeight: FontWeight.w800, color: inc >= fee ? kIncome : kInk)),
                          ]),
                        ),
                      ]),
                      const SizedBox(height: 18),
                    ],
                    Row(children: [
                      _mini(app.t('received'), money(inc, cur), kIncome),
                      const SizedBox(width: 8),
                      _mini(app.t('spent'), money(exp, cur), kExpense),
                      const SizedBox(width: 8),
                      _mini(app.t('net'), money(net, cur), net >= 0 ? kInk : kExpense),
                    ]),
                  ]),
                ),
              ),
            ),
            // details
            SliverToBoxAdapter(
              child: SoftCard(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
                child: Column(children: [
                  if (parties.isNotEmpty) _kv(Icons.people_outline, app.t('party'), parties),
                  if (court.isNotEmpty) _kv(Icons.account_balance_outlined, app.t('court'), court),
                  if (price > 0) _kv(Icons.sell_outlined, app.t('price'), money(price, cur)),
                  _kv(Icons.event_note_outlined, app.t('started'), c['started']?.toString() ?? '-'),
                  if (c['hearing'] != null) _kv(Icons.event, app.t('hearing'), c['hearing'].toString()),
                ]),
              ),
            ),
            // timeline
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 18, 20, 6),
                child: Row(children: [
                  Text(app.t('entries'), style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800, color: kInk)),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                    decoration: BoxDecoration(color: kInk.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(10)),
                    child: Text('${items.length}', style: _tab.copyWith(fontSize: 12, fontWeight: FontWeight.w800, color: kInk)),
                  ),
                ]),
              ),
            ),
            if (items.isEmpty)
              SliverToBoxAdapter(child: Padding(padding: const EdgeInsets.all(28), child: Center(child: Text(app.t('nodata')))))
            else
              SliverList(
                delegate: SliverChildListDelegate([
                  for (final g in groups.entries) ...[
                    Padding(
                      padding: const EdgeInsetsDirectional.fromSTEB(20, 12, 20, 4),
                      child: Align(
                        alignment: AlignmentDirectional.centerStart,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 4),
                          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border.all(color: kLine)),
                          child: Text(g.key, style: _tab.copyWith(color: kSlate, fontWeight: FontWeight.w700, fontSize: 12.5)),
                        ),
                      ),
                    ),
                    for (final it in g.value) _entryRow(it, cur, canEdit),
                  ],
                ]),
              ),
            const SliverToBoxAdapter(child: SizedBox(height: 24)),
          ],
        ),
      ),
      bottomNavigationBar: canEdit
          ? Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
                boxShadow: [BoxShadow(color: kInk.withValues(alpha: 0.08), blurRadius: 20, offset: const Offset(0, -6))],
              ),
              padding: EdgeInsets.fromLTRB(16, 12, 16, 12 + MediaQuery.of(context).padding.bottom),
              child: Row(children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: () => _entry('income'),
                    icon: const Icon(Icons.south_west),
                    label: Text(app.t('received')),
                    style: FilledButton.styleFrom(backgroundColor: kIncome, minimumSize: const Size.fromHeight(52), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16))),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: FilledButton.icon(
                    onPressed: () => _entry('expense'),
                    icon: const Icon(Icons.north_east),
                    label: Text(app.t('spent')),
                    style: FilledButton.styleFrom(backgroundColor: kExpense, minimumSize: const Size.fromHeight(52), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16))),
                  ),
                ),
              ]),
            )
          : null,
    );
  }
}
