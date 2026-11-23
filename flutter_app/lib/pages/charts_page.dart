import 'package:flutter/material.dart';

import '../state.dart';
import '../ui.dart';

class ChartsPage extends StatelessWidget {
  const ChartsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: app,
      builder: (context, _) {
        final cur = app.currency;
        final daily = listOfMaps(app.data?['daily']);
        final cats = listOfMaps(app.data?['cats']);
        final inCats = cats.where((c) => c['t'] == 'income').toList();
        final exCats = cats.where((c) => c['t'] == 'expense').toList();
        // keep the bars readable: last 31 days of the selected period
        final days = daily.length > 31 ? daily.sublist(daily.length - 31) : daily;

        return Scaffold(
          appBar: AppBar(title: Text(app.t('charts'))),
          body: ListView(
            padding: const EdgeInsets.only(bottom: 40),
            children: [
              const SizedBox(height: 4),
              const PeriodBar(),
              Panel(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(app.t('daily'), style: const TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 12),
                  if (days.isEmpty)
                    Padding(padding: const EdgeInsets.all(16), child: Center(child: Text(app.t('nodata'))))
                  else
                    _DailyBars(days: days),
                ]),
              ),
              _CatPanel(title: '${app.t('income')} - ${app.t('cats')}', rows: inCats, color: kIncome, cur: cur),
              _CatPanel(title: '${app.t('expenses')} - ${app.t('cats')}', rows: exCats, color: kExpense, cur: cur),
            ],
          ),
        );
      },
    );
  }
}

class _DailyBars extends StatelessWidget {
  const _DailyBars({required this.days});

  final List<Map<String, dynamic>> days;

  @override
  Widget build(BuildContext context) {
    var maxV = 1.0;
    for (final d in days) {
      final i = dbl(d['i']);
      final e = dbl(d['e']);
      if (i > maxV) maxV = i;
      if (e > maxV) maxV = e;
    }
    const h = 140.0;
    return SizedBox(
      height: h + 22,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            for (final d in days)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 3),
                child: Column(mainAxisAlignment: MainAxisAlignment.end, children: [
                  Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                    Container(
                      width: 9,
                      height: (dbl(d['i']) / maxV * h).clamp(2.0, h),
                      decoration: BoxDecoration(color: kIncome, borderRadius: BorderRadius.circular(3)),
                    ),
                    const SizedBox(width: 2),
                    Container(
                      width: 9,
                      height: (dbl(d['e']) / maxV * h).clamp(2.0, h),
                      decoration: BoxDecoration(color: kExpense, borderRadius: BorderRadius.circular(3)),
                    ),
                  ]),
                  const SizedBox(height: 4),
                  Text(d['d'].toString().substring(8), style: const TextStyle(fontSize: 10, color: Colors.black54)),
                ]),
              ),
          ],
        ),
      ),
    );
  }
}

class _CatPanel extends StatelessWidget {
  const _CatPanel({required this.title, required this.rows, required this.color, required this.cur});

  final String title;
  final List<Map<String, dynamic>> rows;
  final Color color;
  final String cur;

  @override
  Widget build(BuildContext context) {
    if (rows.isEmpty) return const SizedBox.shrink();
    final top = rows.take(10).toList();
    final maxV = top.map((r) => dbl(r['v'])).fold<double>(1, (a, b) => b > a ? b : a);
    return Panel(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 10),
        for (final r in top)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text(r['l'].toString(), overflow: TextOverflow.ellipsis)),
                Text(money(dbl(r['v']), cur), style: TextStyle(color: color, fontWeight: FontWeight.w600), textDirection: TextDirection.ltr),
              ]),
              const SizedBox(height: 4),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(value: dbl(r['v']) / maxV, minHeight: 6, color: color, backgroundColor: Colors.black12),
              ),
            ]),
          ),
      ]),
    );
  }
}
