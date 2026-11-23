import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'state.dart';
import 'ui.dart';

// ---------- case types ----------

Color typeColor(String t) {
  switch (t) {
    case 'house':
      return kBrass;
    case 'car':
      return kTeal;
    case 'other':
      return kSlate;
    default:
      return kInk;
  }
}

IconData typeIcon(String t) {
  switch (t) {
    case 'house':
      return Icons.home_work_outlined;
    case 'car':
      return Icons.directions_car_outlined;
    case 'other':
      return Icons.folder_open_outlined;
    default:
      return Icons.gavel;
  }
}

// ---------- hearing countdown ----------

class Hearing {
  const Hearing(this.text, this.color, this.soon);
  final String text;
  final Color color;
  final bool soon;
}

Hearing? hearingInfo(dynamic v) {
  final h = parseYmd(v);
  if (h == null) return null;
  final now = DateTime.now();
  final d = DateTime.utc(h.year, h.month, h.day).difference(DateTime.utc(now.year, now.month, now.day)).inDays;
  if (d < 0) return Hearing(app.t('passed'), kSlate, false);
  if (d == 0) return Hearing(app.t('today'), kExpense, true);
  if (d == 1) return Hearing(app.t('tomorrow'), kExpense, true);
  return Hearing(app.t('in_days').replaceAll('%d', '$d'), d <= 7 ? kBrass : kSlate, d <= 7);
}

// ---------- header band (navy, rounded bottom) ----------

class PageHeader extends StatelessWidget {
  const PageHeader({
    super.key,
    required this.title,
    this.actions = const [],
    this.back = false,
    this.child,
  });

  final String title;
  final List<Widget> actions;
  final bool back;
  final Widget? child;

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Container(
        width: double.infinity,
        decoration: const BoxDecoration(
          color: kInk,
          borderRadius: BorderRadius.vertical(bottom: Radius.circular(28)),
        ),
        padding: EdgeInsets.fromLTRB(8, MediaQuery.of(context).padding.top + 6, 8, 20),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            if (back) const BackButton(color: Colors.white) else const SizedBox(width: 12),
            Expanded(
              child: Text(
                title,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w800, height: 1.25),
              ),
            ),
            ...actions,
          ]),
          if (child != null) Padding(padding: const EdgeInsets.fromLTRB(12, 14, 12, 0), child: child),
        ]),
      ),
    );
  }
}

Widget headerIcon(IconData i, VoidCallback f, {String? tip}) =>
    IconButton(icon: Icon(i, color: Colors.white), tooltip: tip, onPressed: f);

/// Small translucent label used on the navy band.
class BandChip extends StatelessWidget {
  const BandChip(this.icon, this.text, {super.key});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 14, color: Colors.white),
        const SizedBox(width: 5),
        Text(text, style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600)),
      ]),
    );
  }
}

const TextStyle _tab = TextStyle(fontFeatures: [FontFeature.tabularFigures()]);

// ---------- the folder card ----------

class CaseFolder extends StatelessWidget {
  const CaseFolder({super.key, required this.c, required this.onTap});

  final Map<String, dynamic> c;
  final VoidCallback onTap;

  Widget _line(IconData icon, String text) => Padding(
        padding: const EdgeInsets.only(top: 6),
        child: Row(children: [
          Icon(icon, size: 15, color: kSlate),
          const SizedBox(width: 6),
          Expanded(child: Text(text, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: kSlate, fontSize: 13))),
        ]),
      );

  Widget _num(String label, String value, Color color) => Expanded(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(label, style: const TextStyle(fontSize: 11, color: kSlate)),
          const SizedBox(height: 2),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: AlignmentDirectional.centerStart,
            child: Text(value, style: _tab.copyWith(fontSize: 14, fontWeight: FontWeight.w700, color: color)),
          ),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final type = (c['ctype'] ?? 'court').toString();
    final color = typeColor(type);
    final cur = c['currency'].toString();
    final fee = dbl(c['fee']);
    final inc = dbl(c['inc']);
    final exp = dbl(c['exp']);
    final remaining = fee > inc ? fee - inc : 0.0;
    final h = c['status'] == 'closed' ? null : hearingInfo(c['hearing']);
    final no = (c['case_no'] ?? '').toString().trim();
    final client = (c['client'] ?? '').toString().trim();
    final court = (c['court'] ?? '').toString().trim();

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // the folder tab
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(color: color, borderRadius: const BorderRadius.vertical(top: Radius.circular(12))),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(typeIcon(type), size: 15, color: Colors.white),
            const SizedBox(width: 6),
            Text(no.isEmpty ? app.t('ct_$type') : no, style: _tab.copyWith(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w700)),
          ]),
        ),
        // the folder body (square corner under the tab)
        Material(
          color: Colors.white,
          clipBehavior: Clip.antiAlias,
          shape: RoundedRectangleBorder(
            borderRadius: const BorderRadiusDirectional.only(
              topEnd: Radius.circular(16),
              bottomStart: Radius.circular(16),
              bottomEnd: Radius.circular(16),
            ),
            side: BorderSide(color: color.withValues(alpha: 0.4)),
          ),
          child: InkWell(
            onTap: onTap,
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Expanded(
                    child: Text(c['name'].toString(),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800, height: 1.3)),
                  ),
                  if (h != null) ...[const SizedBox(width: 8), HearingPill(h)],
                ]),
                if (client.isNotEmpty) _line(Icons.person_outline, client),
                if (court.isNotEmpty) _line(Icons.account_balance_outlined, court),
                const SizedBox(height: 12),
                if (fee > 0) ...[
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: (inc / fee).clamp(0.0, 1.0),
                      minHeight: 5,
                      color: inc >= fee ? kIncome : kBrass,
                      backgroundColor: kLine,
                    ),
                  ),
                  const SizedBox(height: 10),
                ],
                Row(children: [
                  if (fee > 0) _num(app.t('fee'), money(fee, cur), kInk),
                  _num(app.t('received'), money(inc, cur), kIncome),
                  if (fee > 0)
                    _num(app.t('remaining'), money(remaining, cur), remaining > 0 ? kExpense : kSlate)
                  else
                    _num(app.t('spent'), money(exp, cur), kExpense),
                ]),
              ]),
            ),
          ),
        ),
      ]),
    );
  }
}

class HearingPill extends StatelessWidget {
  const HearingPill(this.h, {super.key});

  final Hearing h;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(color: h.color.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(Icons.event, size: 13, color: h.color),
        const SizedBox(width: 4),
        Text(h.text, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: h.color)),
      ]),
    );
  }
}
