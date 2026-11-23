import 'dart:io';

import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import 'state.dart';

/// Builds a CSV (opens in Excel, with Kurdish/Arabic text) for one case and
/// opens the phone's share sheet so it can be saved to Files / Drive / WhatsApp.
Future<void> shareCaseCsv(int caseId) async {
  final r = await sb.rpc('api_case_view', params: {'p_case': caseId});
  if (r == null) throw Exception('not found');
  final v = Map<String, dynamic>.from(r as Map);
  final c = Map<String, dynamic>.from(v['case'] as Map);
  final items = listOfMaps(v['items']);
  final cur = c['currency'].toString();

  String q(Object? x) => '"${(x ?? '').toString().replaceAll('"', '""')}"';
  final b = StringBuffer('\uFEFF'); // BOM so Excel reads UTF-8 correctly
  void row(List<Object?> cells) => b.write('${cells.map(q).join(',')}\r\n');

  String people(dynamic list, dynamic fallback) =>
      list is List ? list.join(' + ') : (fallback ?? '').toString();

  row([app.t('name'), c['name']]);
  row([app.t('clients'), people(c['clients'], c['client'])]);
  row([app.t('party'), people(c['parties'], c['party'])]);
  row([app.t('case_no'), c['case_no']]);
  row([app.t('court'), c['court']]);
  row([app.t('started'), c['started']]);
  row([app.t('hearing'), c['hearing']]);
  row([app.t('status'), app.t(c['status'] == 'closed' ? 'closed' : 'open')]);
  row([app.t('currency'), cur]);
  row([app.t('fee'), c['fee']]);
  row([app.t('received'), v['inc']]);
  row([app.t('spent'), v['exp']]);
  row([app.t('remaining'), (dbl(c['fee']) - dbl(v['inc'])).clamp(0, double.infinity)]);
  b.write('\r\n');
  row([app.t('date'), '${app.t('income_one')} / ${app.t('expense_one')}', app.t('label'), app.t('note'), app.t('amount')]);
  for (final it in items) {
    row([
      it['date'],
      app.t(it['type'] == 'income' ? 'income_one' : 'expense_one'),
      it['label'],
      it['note'],
      it['amount'],
    ]);
  }

  final dir = await getTemporaryDirectory();
  final file = File('${dir.path}/case_${c['id']}_${ymd(DateTime.now())}.csv');
  await file.writeAsString(b.toString());
  await Share.shareXFiles([XFile(file.path, mimeType: 'text/csv')]);
}
