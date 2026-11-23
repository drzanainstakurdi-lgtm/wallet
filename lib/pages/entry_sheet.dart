import 'package:flutter/material.dart';

import '../state.dart';
import '../ui.dart';

/// Add a new entry (item == null) or edit an existing one.
/// For cases pass [accountId] (the case id); otherwise the selected account is used.
Future<void> showEntrySheet(
  BuildContext context, {
  String type = 'income',
  bool allowTypeChoice = false,
  Map<String, dynamic>? item,
  int? accountId,
  String? presetLabel,
}) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.white,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
    builder: (c) => _EntrySheet(
      type: item != null ? item['type'].toString() : type,
      allowTypeChoice: allowTypeChoice && item == null,
      item: item,
      accountId: accountId,
      presetLabel: presetLabel,
    ),
  );
}

class _EntrySheet extends StatefulWidget {
  const _EntrySheet({
    required this.type,
    required this.allowTypeChoice,
    this.item,
    this.accountId,
    this.presetLabel,
  });

  final String type;
  final bool allowTypeChoice;
  final Map<String, dynamic>? item;
  final int? accountId;
  final String? presetLabel;

  @override
  State<_EntrySheet> createState() => _EntrySheetState();
}

class _EntrySheetState extends State<_EntrySheet> {
  late String _type = widget.type;
  late final TextEditingController _amount;
  late final TextEditingController _label;
  late final TextEditingController _note;
  late DateTime _date;
  bool _busy = false;
  String? _err;

  @override
  void initState() {
    super.initState();
    final it = widget.item;
    _amount = TextEditingController(text: it == null ? '' : _plain(dbl(it['amount'])));
    _label = TextEditingController(text: it?['label']?.toString() ?? widget.presetLabel ?? '');
    _note = TextEditingController(text: it?['note']?.toString() ?? '');
    _date = parseYmd(it?['date']) ?? DateTime.now();
  }

  String _plain(double v) => v == v.roundToDouble() ? v.round().toString() : v.toString();

  @override
  void dispose() {
    _amount.dispose();
    _label.dispose();
    _note.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final d = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime(2000),
      lastDate: DateTime(DateTime.now().year + 2),
    );
    if (d != null) setState(() => _date = d);
  }

  Future<void> _save() async {
    final amt = parseAmount(_amount.text);
    if (amt <= 0) {
      setState(() => _err = app.t('amount'));
      return;
    }
    setState(() {
      _busy = true;
      _err = null;
    });
    try {
      final it = widget.item;
      if (it != null) {
        await app.editTx(intOrNull(it['id'])!, amt, _label.text.trim(), _note.text.trim(), _date);
      } else {
        final acc = widget.accountId ?? app.accId;
        if (acc == null) throw Exception('no account');
        await app.addTx(acc, _type, amt, _label.text.trim(), _note.text.trim(), _date);
      }
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      setState(() {
        _err = errText(e, app.lang);
        _busy = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottom = MediaQuery.of(context).viewInsets.bottom;
    final editing = widget.item != null;
    return Padding(
      padding: EdgeInsets.fromLTRB(20, 18, 20, 20 + bottom),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (widget.allowTypeChoice)
              SegmentedButton<String>(
                segments: [
                  ButtonSegment(value: 'income', label: Text(app.t('income_one'))),
                  ButtonSegment(value: 'expense', label: Text(app.t('expense_one'))),
                ],
                selected: {_type},
                onSelectionChanged: (s) => setState(() => _type = s.first),
              )
            else
              Text(
                app.t(_type == 'income' ? 'income_one' : 'expense_one'),
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                  color: _type == 'income' ? kIncome : kExpense,
                ),
              ),
            const SizedBox(height: 14),
            TextField(
              controller: _amount,
              autofocus: !editing,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              textDirection: TextDirection.ltr,
              decoration: InputDecoration(labelText: app.t('amount'), border: const OutlineInputBorder()),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _label,
              decoration: InputDecoration(labelText: app.t('label'), border: const OutlineInputBorder()),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _note,
              maxLines: 2,
              decoration: InputDecoration(labelText: app.t('note'), border: const OutlineInputBorder()),
            ),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: _pickDate,
              icon: const Icon(Icons.event),
              label: Text(ymd(_date)),
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
          ],
        ),
      ),
    );
  }
}
