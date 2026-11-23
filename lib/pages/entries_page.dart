import 'package:flutter/material.dart';

import '../nav.dart';
import '../state.dart';
import '../ui.dart';
import 'home_page.dart';

class EntriesPage extends StatefulWidget {
  const EntriesPage({super.key, required this.type});

  final String type; // income | expense

  @override
  State<EntriesPage> createState() => _EntriesPageState();
}

class _EntriesPageState extends State<EntriesPage> {
  String _q = '';

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: app,
      builder: (context, _) {
        final income = widget.type == 'income';
        final all = listOfMaps(app.data?[income ? 'items_in' : 'items_ex']);
        final q = _q.trim().toLowerCase();
        final items = q.isEmpty
            ? all
            : all.where((e) => '${e['label']} ${e['note']} ${e['amount']}'.toLowerCase().contains(q)).toList();
        final total = items.fold<double>(0, (s, e) => s + dbl(e['amount']));

        return Scaffold(
          appBar: AppBar(
            title: Text(app.t(income ? 'income' : 'expenses')),
            actions: [
              IconButton(icon: const Icon(Icons.settings_outlined), onPressed: () => openSettings(context)),
            ],
          ),
          body: RefreshIndicator(
            onRefresh: () => app.load(quiet: true),
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.only(bottom: 110),
              children: [
                const PeriodBar(),
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 10, 16, 4),
                  child: TextField(
                    onChanged: (v) => setState(() => _q = v),
                    decoration: InputDecoration(
                      hintText: app.t('search'),
                      prefixIcon: const Icon(Icons.search),
                      filled: true,
                      fillColor: Colors.white,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
                      isDense: true,
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 8, 20, 4),
                  child: Text(
                    money(total, app.currency),
                    style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: income ? kIncome : kExpense),
                  ),
                ),
                if (items.isEmpty)
                  Padding(padding: const EdgeInsets.all(32), child: Center(child: Text(app.t('nodata')))),
                for (final it in items)
                  app.canEdit
                      ? Dismissible(
                          key: ValueKey('tx${it['id']}'),
                          direction: DismissDirection.endToStart,
                          background: Container(
                            color: kExpense,
                            alignment: Alignment.centerRight,
                            padding: const EdgeInsets.symmetric(horizontal: 24),
                            child: const Icon(Icons.delete, color: Colors.white),
                          ),
                          confirmDismiss: (_) async {
                            final ok = await confirmDialog(context, app.t('confirm_del'));
                            if (!ok) return false;
                            try {
                              await app.delTx(intOrNull(it['id'])!);
                            } catch (e) {
                              if (context.mounted) toast(context, errText(e, app.lang));
                            }
                            return false; // the list is rebuilt from fresh data
                          },
                          child: EntryTile(item: it),
                        )
                      : EntryTile(item: it),
              ],
            ),
          ),
        );
      },
    );
  }
}
