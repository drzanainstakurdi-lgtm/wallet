import 'package:flutter/material.dart';

import 'state.dart';

const Color kCream = Color(0xFFFAF9F5);
const Color kGreen = Color(0xFF2F6B4F);
const Color kIncome = Color(0xFF2E7D32);
const Color kExpense = Color(0xFFC62828);

Future<bool> confirmDialog(BuildContext context, String message) async {
  final r = await showDialog<bool>(
    context: context,
    builder: (c) => AlertDialog(
      content: Text(message),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(app.t('cancel'))),
        TextButton(onPressed: () => Navigator.pop(c, true), child: Text(app.t('delete'))),
      ],
    ),
  );
  return r == true;
}

void toast(BuildContext context, String msg) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(msg)));
}

class Panel extends StatelessWidget {
  const Panel({super.key, required this.child, this.padding = const EdgeInsets.all(16), this.onTap});

  final Widget child;
  final EdgeInsets padding;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: Colors.white,
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: BorderSide(color: Colors.black.withValues(alpha: 0.06)),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: onTap,
        child: Padding(padding: padding, child: child),
      ),
    );
  }
}

/// Today / Week / Month / All / custom range selector.
class PeriodBar extends StatelessWidget {
  const PeriodBar({super.key});

  Future<void> _pickRange(BuildContext context) async {
    final now = DateTime.now();
    final r = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2000),
      lastDate: DateTime(now.year + 2),
      initialDateRange: app.custom,
    );
    if (r != null) app.setPeriod('range', r: r);
  }

  @override
  Widget build(BuildContext context) {
    Widget chip(String key, String label) => Padding(
          padding: const EdgeInsetsDirectional.only(end: 8),
          child: ChoiceChip(
            label: Text(label),
            selected: app.period == key,
            onSelected: (_) => key == 'range' ? _pickRange(context) : app.setPeriod(key),
          ),
        );
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(children: [
        chip('today', app.t('today')),
        chip('week', app.t('week')),
        chip('month', app.t('month')),
        chip('all', app.t('all')),
        chip('range', app.t('range')),
      ]),
    );
  }
}

class AccountTitle extends StatelessWidget {
  const AccountTitle({super.key});

  @override
  Widget build(BuildContext context) {
    final a = app.account;
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: () => showModalBottomSheet(
        context: context,
        builder: (c) => SafeArea(
          child: ListView(
            shrinkWrap: true,
            children: [
              Padding(
                padding: const EdgeInsets.all(16),
                child: Text(app.t('switch_acc'), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
              ),
              for (final x in app.accounts)
                ListTile(
                  title: Text(x['name'].toString()),
                  subtitle: Text(x['currency'].toString() + (x['shared'] == true ? '  •  ${x['owner']}' : '')),
                  trailing: intOrNull(x['id']) == app.accId ? const Icon(Icons.check, color: kGreen) : null,
                  onTap: () {
                    Navigator.pop(c);
                    app.selectAccount(intOrNull(x['id'])!);
                  },
                ),
            ],
          ),
        ),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Flexible(child: Text(a?['name']?.toString() ?? app.t('app'), overflow: TextOverflow.ellipsis)),
        const Icon(Icons.arrow_drop_down),
      ]),
    );
  }
}
