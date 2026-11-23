import 'package:flutter/material.dart';

import '../nav.dart';
import '../state.dart';
import '../ui.dart';
import 'entry_sheet.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: app,
      builder: (context, _) {
        final cur = app.currency;
        final sel = app.periodSums('range');
        final acc = app.account;
        final budget = dbl(acc?['budget']);
        final monthSpent = app.periodSums('month')['e'] ?? 0;

        final recent = <Map<String, dynamic>>[
          ...listOfMaps(app.data?['items_in']),
          ...listOfMaps(app.data?['items_ex']),
        ]..sort((a, b) {
            final c = b['date'].toString().compareTo(a['date'].toString());
            return c != 0 ? c : (intOrNull(b['id']) ?? 0).compareTo(intOrNull(a['id']) ?? 0);
          });

        // next court hearing in the coming 7 days
        final now = DateTime.now();
        final today = DateTime(now.year, now.month, now.day);
        final upcoming = app.cases.where((c) {
          final h = parseYmd(c['hearing']);
          if (h == null || c['status'] == 'closed') return false;
          final diff = h.difference(today).inDays;
          return diff >= 0 && diff <= 7;
        }).toList();

        return Scaffold(
          appBar: AppBar(
            title: const AccountTitle(),
            actions: [
              IconButton(icon: const Icon(Icons.bar_chart_rounded), onPressed: () => openCharts(context)),
              IconButton(icon: const Icon(Icons.settings_outlined), onPressed: () => openSettings(context)),
            ],
          ),
          body: RefreshIndicator(
            onRefresh: () => app.load(quiet: true),
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.only(bottom: 110),
              children: [
                if (app.error != null)
                  Padding(padding: const EdgeInsets.all(16), child: Text(app.error!, style: const TextStyle(color: kExpense))),
                Panel(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(app.t('balance'), style: const TextStyle(color: Colors.black54)),
                    const SizedBox(height: 4),
                    Text(money(app.balance, cur),
                        style: const TextStyle(fontSize: 32, fontWeight: FontWeight.w800)),
                    if (budget > 0) ...[
                      const SizedBox(height: 14),
                      Text('${app.t('budget')}: ${money(monthSpent, cur)} / ${money(budget, cur)}',
                          style: const TextStyle(fontSize: 13, color: Colors.black54)),
                      const SizedBox(height: 6),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(6),
                        child: LinearProgressIndicator(
                          value: (monthSpent / budget).clamp(0.0, 1.0),
                          minHeight: 8,
                          color: monthSpent > budget ? kExpense : kGreen,
                          backgroundColor: Colors.black12,
                        ),
                      ),
                    ],
                  ]),
                ),
                if (upcoming.isNotEmpty)
                  Panel(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Row(children: [
                        const Icon(Icons.event_available, size: 18, color: kGreen),
                        const SizedBox(width: 8),
                        Text(app.t('upcoming'), style: const TextStyle(fontWeight: FontWeight.w700)),
                      ]),
                      const SizedBox(height: 6),
                      for (final c in upcoming) Text('${c['name']}  •  ${c['hearing']}'),
                    ]),
                  ),
                const SizedBox(height: 6),
                const PeriodBar(),
                Row(children: [
                  Expanded(child: _Stat(label: app.t('income'), value: money(sel['i'] ?? 0, cur), color: kIncome)),
                  Expanded(child: _Stat(label: app.t('expenses'), value: money(sel['e'] ?? 0, cur), color: kExpense)),
                ]),
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 14, 20, 4),
                  child: Text('${app.t('today')} / ${app.t('week')} / ${app.t('month')}',
                      style: const TextStyle(color: Colors.black54, fontSize: 13)),
                ),
                for (final k in ['today', 'week', 'month'])
                  Panel(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    child: Row(children: [
                      SizedBox(width: 70, child: Text(app.t(k))),
                      Expanded(
                        child: Text('+${money(app.periodSums(k)['i'] ?? 0, cur)}',
                            style: const TextStyle(color: kIncome, fontWeight: FontWeight.w600)),
                      ),
                      Text('-${money(app.periodSums(k)['e'] ?? 0, cur)}',
                          style: const TextStyle(color: kExpense, fontWeight: FontWeight.w600)),
                    ]),
                  ),
                const SizedBox(height: 8),
                if (recent.isEmpty)
                  Padding(padding: const EdgeInsets.all(24), child: Center(child: Text(app.t('nodata')))),
                for (final it in recent.take(8)) EntryTile(item: it),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat({required this.label, required this.value, required this.color});

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Panel(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label, style: const TextStyle(color: Colors.black54, fontSize: 13)),
        const SizedBox(height: 4),
        FittedBox(
          fit: BoxFit.scaleDown,
          alignment: AlignmentDirectional.centerStart,
          child: Text(value, style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: color)),
        ),
      ]),
    );
  }
}

/// One income / expense row. Tap to edit (if allowed).
class EntryTile extends StatelessWidget {
  const EntryTile({super.key, required this.item, this.accountId, this.cur});

  final Map<String, dynamic> item;
  final int? accountId;
  final String? cur;

  @override
  Widget build(BuildContext context) {
    final income = item['type'] == 'income';
    final c = cur ?? app.currency;
    final title = (item['label']?.toString().trim().isNotEmpty ?? false) ? item['label'].toString() : '-';
    final sub = [
      item['date'].toString(),
      if ((item['note']?.toString() ?? '').isNotEmpty) item['note'].toString(),
      if (item['by_user'] != null && app.account?['shared'] == true) '${app.t('by')} ${item['by_user']}',
    ].join('  •  ');
    return Panel(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      onTap: app.canEdit ? () => showEntrySheet(context, item: item) : null,
      child: Row(children: [
        CircleAvatar(
          radius: 18,
          backgroundColor: (income ? kIncome : kExpense).withValues(alpha: 0.12),
          child: Icon(income ? Icons.south_west : Icons.north_east, size: 18, color: income ? kIncome : kExpense),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w600)),
            Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, color: Colors.black54)),
          ]),
        ),
        Text(
          '${income ? '+' : '-'}${money(dbl(item['amount']), c)}',
          style: TextStyle(fontWeight: FontWeight.w700, color: income ? kIncome : kExpense),
          textDirection: TextDirection.ltr,
        ),
      ]),
    );
  }
}
