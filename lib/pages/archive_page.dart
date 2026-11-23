import 'package:flutter/material.dart';

import '../case_ui.dart';
import '../export.dart';
import '../state.dart';
import '../ui.dart';
import 'case_page.dart';

class ArchivePage extends StatefulWidget {
  const ArchivePage({super.key});

  @override
  State<ArchivePage> createState() => _ArchivePageState();
}

class _ArchivePageState extends State<ArchivePage> {
  List<Map<String, dynamic>>? _items;
  List<Map<String, dynamic>> _log = [];
  int _days = 30;
  String? _err;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await sb.rpc('api_archive');
      final m = Map<String, dynamic>.from(r as Map);
      if (mounted) {
        setState(() {
          _items = listOfMaps(m['items']);
          _log = listOfMaps(m['log']);
          _days = intOrNull(m['days']) ?? 30;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _err = errText(e, app.lang));
    }
  }

  Future<void> _reopen(Map<String, dynamic> c) async {
    try {
      await sb.rpc('api_case_status', params: {'p_case': intOrNull(c['id']), 'p_status': 'open'});
      await app.load(quiet: true);
      await _load();
    } catch (e) {
      if (mounted) toast(context, errText(e, app.lang));
    }
  }

  Future<void> _purge(Map<String, dynamic> c) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: Text(app.t('purge_now')),
        content: Text(app.t('purge_msg')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: Text(app.t('cancel'))),
          TextButton(onPressed: () => Navigator.pop(d, true), child: Text(app.t('purge_now'))),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await sb.rpc('api_purge_case', params: {'p_case': intOrNull(c['id'])});
      await app.load(quiet: true);
      await _load();
    } catch (e) {
      if (mounted) toast(context, errText(e, app.lang));
    }
  }

  Future<void> _download(Map<String, dynamic> c) async {
    try {
      await shareCaseCsv(intOrNull(c['id'])!);
    } catch (e) {
      if (mounted) toast(context, errText(e, app.lang));
    }
  }

  @override
  Widget build(BuildContext context) {
    final items = _items;
    return Scaffold(
      backgroundColor: kPaper,
      body: Column(children: [
        PageHeader(
          title: app.t('archive'),
          back: true,
          child: items == null
              ? null
              : Text('${items.length}', style: const TextStyle(color: kBrassLight, fontSize: 30, fontWeight: FontWeight.w800)),
        ),
        Expanded(
          child: items == null
              ? Center(child: _err != null ? Text(_err!) : const CircularProgressIndicator())
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.only(top: 12, bottom: 40),
                    children: [
                      if (items.isEmpty)
                        Padding(
                          padding: const EdgeInsets.all(40),
                          child: Column(children: [
                            Icon(Icons.inventory_2_outlined, size: 52, color: kSlate.withValues(alpha: 0.6)),
                            const SizedBox(height: 12),
                            Text(app.t('archive_empty'), style: const TextStyle(color: kSlate)),
                          ]),
                        ),
                      for (final c in items) _tile(c),
                      if (_log.isNotEmpty) ..._history(),
                    ],
                  ),
                ),
        ),
      ]),
    );
  }

  Widget _tile(Map<String, dynamic> c) {
    final cur = c['currency'].toString();
    final left = intOrNull(c['days_left']);
    final deleted = c['kind'] == 'deleted';
    final closed = (c['closed_at'] ?? '').toString();
    final closedDay = closed.length >= 10 ? closed.substring(0, 10) : closed;
    final urgent = left != null && left <= 7;
    final tagColor = deleted ? kExpense : kSlate;
    return SoftCard(
      onTap: () => Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => CasePage(caseId: intOrNull(c['id'])!)),
      ).then((_) => _load()),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text(c['name'].toString(), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800))),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
            decoration: BoxDecoration(color: tagColor.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
            child: Text(app.t(deleted ? 'tag_deleted' : 'tag_finished'),
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: tagColor)),
          ),
        ]),
        if ((c['client']?.toString() ?? '').isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(c['client'].toString(), style: const TextStyle(color: kSlate, fontSize: 13)),
          ),
        const SizedBox(height: 12),
        if (left != null) ...[
          Row(children: [
            Icon(Icons.timer_outlined, size: 16, color: urgent ? kExpense : kSlate),
            const SizedBox(width: 6),
            Text('$left ${app.t('days_left')}',
                style: TextStyle(fontWeight: FontWeight.w700, color: urgent ? kExpense : kInk)),
            const Spacer(),
            Text('${app.t('archived_on')}: $closedDay', style: const TextStyle(fontSize: 12, color: kSlate)),
          ]),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: _days > 0 ? (left / _days).clamp(0.0, 1.0) : 1,
              minHeight: 5,
              color: urgent ? kExpense : kBrass,
              backgroundColor: kLine,
            ),
          ),
          const SizedBox(height: 12),
        ],
        Row(children: [
          Expanded(
            child: Text('${app.t('received')}: ${money(dbl(c['inc']), cur)}',
                style: const TextStyle(fontSize: 13, color: kIncome, fontWeight: FontWeight.w600)),
          ),
          Expanded(
            child: Text('${app.t('spent')}: ${money(dbl(c['exp']), cur)}',
                style: const TextStyle(fontSize: 13, color: kExpense, fontWeight: FontWeight.w600)),
          ),
        ]),
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 4, children: [
          OutlinedButton.icon(
            onPressed: () => _download(c),
            icon: const Icon(Icons.download, size: 18),
            label: Text(app.t('download')),
            style: OutlinedButton.styleFrom(foregroundColor: kInk),
          ),
          TextButton.icon(
            onPressed: () => _reopen(c),
            icon: const Icon(Icons.restore, size: 18),
            label: Text(app.t('reopen')),
          ),
          TextButton.icon(
            onPressed: () => _purge(c),
            icon: const Icon(Icons.delete_forever, size: 18, color: kExpense),
            label: Text(app.t('purge_now'), style: const TextStyle(color: kExpense)),
          ),
        ]),
      ]),
    );
  }

  List<Widget> _history() => [
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 22, 20, 6),
          child: Text(app.t('history'), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
        ),
        for (final l in _log)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
            child: Row(children: [
              Expanded(child: Text('${l['name'] ?? '-'}  -  ${app.t('ev_${l['event']}')}', style: const TextStyle(fontSize: 13))),
              Text(l['at'].toString().substring(0, 10), style: const TextStyle(fontSize: 12, color: kSlate)),
            ]),
          ),
      ];
}
