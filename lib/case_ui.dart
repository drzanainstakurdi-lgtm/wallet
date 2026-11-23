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

// ---------- shared look ----------

const Color kInkSoft = Color(0xFF24396B); // gradient end of the header

final List<BoxShadow> kSoftShadow = [
  BoxShadow(color: kInk.withValues(alpha: 0.07), blurRadius: 22, offset: const Offset(0, 8)),
];

const TextStyle _tab = TextStyle(fontFeatures: [FontFeature.tabularFigures()]);

/// White rounded card with a soft shadow (replaces the bordered Panel in the cases section).
class SoftCard extends StatelessWidget {
  const SoftCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.margin = const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
    this.onTap,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final EdgeInsetsGeometry margin;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: margin,
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(22), boxShadow: kSoftShadow),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(22),
        child: Material(
          color: Colors.white,
          child: InkWell(onTap: onTap, child: Padding(padding: padding, child: child)),
        ),
      ),
    );
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

// ---------- header band (gradient, rounded bottom, soft orbs) ----------

class _Orb extends StatelessWidget {
  const _Orb(this.size, this.color);

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) => IgnorePointer(
        child: Container(width: size, height: size, decoration: BoxDecoration(shape: BoxShape.circle, color: color)),
      );
}

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
      child: ClipRRect(
        borderRadius: const BorderRadius.vertical(bottom: Radius.circular(34)),
        child: Container(
          width: double.infinity,
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: AlignmentDirectional.topStart,
              end: AlignmentDirectional.bottomEnd,
              colors: [kInk, kInkSoft],
            ),
          ),
          child: Stack(children: [
            PositionedDirectional(end: -50, top: -60, child: _Orb(200, kBrass.withValues(alpha: 0.16))),
            PositionedDirectional(start: -40, bottom: -70, child: _Orb(170, Colors.white.withValues(alpha: 0.05))),
            Padding(
              padding: EdgeInsets.fromLTRB(8, MediaQuery.of(context).padding.top + 8, 8, 22),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  if (back)
                    Padding(
                      padding: const EdgeInsetsDirectional.only(start: 4, end: 4),
                      child: Material(
                        color: Colors.white.withValues(alpha: 0.12),
                        shape: const CircleBorder(),
                        child: const BackButton(color: Colors.white),
                      ),
                    )
                  else
                    const SizedBox(width: 14),
                  Expanded(
                    child: Text(
                      title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Colors.white, fontSize: 26, fontWeight: FontWeight.w800, height: 1.25),
                    ),
                  ),
                  ...actions,
                ]),
                if (child != null) Padding(padding: const EdgeInsets.fromLTRB(12, 16, 12, 0), child: child),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}

Widget headerIcon(IconData i, VoidCallback f, {String? tip}) => Padding(
      padding: const EdgeInsetsDirectional.only(end: 6),
      child: Material(
        color: Colors.white.withValues(alpha: 0.12),
        shape: const CircleBorder(),
        child: IconButton(icon: Icon(i, color: Colors.white, size: 21), tooltip: tip, onPressed: f),
      ),
    );

/// Small translucent label used on the header band.
class BandChip extends StatelessWidget {
  const BandChip(this.icon, this.text, {super.key});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.13),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 14, color: Colors.white),
        const SizedBox(width: 5),
        Text(text, style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600)),
      ]),
    );
  }
}

// ---------- the case card ----------

class CaseFolder extends StatelessWidget {
  const CaseFolder({super.key, required this.c, required this.onTap});

  final Map<String, dynamic> c;
  final VoidCallback onTap;

  Widget _meta(IconData icon, String text) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
        decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(10)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, size: 14, color: kSlate),
          const SizedBox(width: 5),
          Flexible(
            child: Text(text, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: kSlate, fontSize: 12.5, fontWeight: FontWeight.w500)),
          ),
        ]),
      );

  Widget _num(String label, String value, Color color) => Expanded(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(label, style: const TextStyle(fontSize: 11, color: kSlate)),
          const SizedBox(height: 3),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: AlignmentDirectional.centerStart,
            child: Text(value, style: _tab.copyWith(fontSize: 14.5, fontWeight: FontWeight.w800, color: color)),
          ),
        ]),
      );

  Widget _vline() => Container(width: 1, height: 30, margin: const EdgeInsets.symmetric(horizontal: 10), color: kLine);

  @override
  Widget build(BuildContext context) {
    final type = (c['ctype'] ?? 'court').toString();
    final color = typeColor(type);
    final cur = c['currency'].toString();
    final fee = dbl(c['fee']);
    final inc = dbl(c['inc']);
    final exp = dbl(c['exp']);
    final remaining = fee > inc ? fee - inc : 0.0;
    final pct = fee > 0 ? (inc / fee).clamp(0.0, 1.0) : 0.0;
    final h = c['status'] == 'closed' ? null : hearingInfo(c['hearing']);
    final no = (c['case_no'] ?? '').toString().trim();
    final client = (c['client'] ?? '').toString().trim();
    final court = (c['court'] ?? '').toString().trim();

    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(24), boxShadow: kSoftShadow),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: Material(
          color: Colors.white,
          child: InkWell(
            onTap: onTap,
            child: Stack(children: [
              Padding(
                padding: const EdgeInsetsDirectional.fromSTEB(20, 16, 16, 16),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Container(
                      width: 46,
                      height: 46,
                      decoration: BoxDecoration(color: color.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(15)),
                      child: Icon(typeIcon(type), color: color, size: 23),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(c['name'].toString(),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontSize: 16.5, fontWeight: FontWeight.w800, height: 1.3, color: kInk)),
                        const SizedBox(height: 3),
                        Text(no.isEmpty ? app.t('ct_$type') : '${app.t('ct_$type')}  •  $no',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: _tab.copyWith(fontSize: 12, color: color, fontWeight: FontWeight.w700)),
                      ]),
                    ),
                    if (h != null) ...[const SizedBox(width: 8), HearingPill(h)],
                  ]),
                  if (client.isNotEmpty || court.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Wrap(spacing: 8, runSpacing: 8, children: [
                      if (client.isNotEmpty) _meta(Icons.person_outline, client),
                      if (court.isNotEmpty) _meta(Icons.account_balance_outlined, court),
                    ]),
                  ],
                  const SizedBox(height: 14),
                  Container(
                    padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
                    decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(16)),
                    child: Column(children: [
                      if (fee > 0) ...[
                        Row(children: [
                          Expanded(
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(6),
                              child: LinearProgressIndicator(
                                value: pct,
                                minHeight: 7,
                                color: inc >= fee ? kIncome : kBrass,
                                backgroundColor: Colors.white,
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Text('${(pct * 100).round()}%',
                              style: _tab.copyWith(fontSize: 12, fontWeight: FontWeight.w800, color: inc >= fee ? kIncome : kBrass)),
                        ]),
                        const SizedBox(height: 12),
                      ],
                      Row(children: [
                        if (fee > 0) ...[_num(app.t('fee'), money(fee, cur), kInk), _vline()],
                        _num(app.t('received'), money(inc, cur), kIncome),
                        _vline(),
                        if (fee > 0)
                          _num(app.t('remaining'), money(remaining, cur), remaining > 0 ? kExpense : kSlate)
                        else
                          _num(app.t('spent'), money(exp, cur), kExpense),
                      ]),
                    ]),
                  ),
                ]),
              ),
              // colored edge strip
              PositionedDirectional(
                start: 0,
                top: 0,
                bottom: 0,
                child: Container(width: 6, color: color),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

class HearingPill extends StatelessWidget {
  const HearingPill(this.h, {super.key});

  final Hearing h;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(color: h.color.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(Icons.event, size: 13, color: h.color),
        const SizedBox(width: 4),
        Text(h.text, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: h.color)),
      ]),
    );
  }
}
