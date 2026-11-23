import 'package:flutter/material.dart';

import '../case_ui.dart';
import '../nav.dart';
import '../state.dart';
import '../ui.dart';
import 'archive_page.dart';
import 'case_page.dart';
import 'new_case_page.dart';

class CasesPage extends StatefulWidget {
  const CasesPage({super.key});

  @override
  State<CasesPage> createState() => _CasesPageState();
}

class _CasesPageState extends State<CasesPage> {
  String _q = '';
  String _filter = 'all'; // all | hearing | unpaid

  void _openNew() => Navigator.push(context, MaterialPageRoute(builder: (_) => const NewCasePage()));

  bool _matches(Map<String, dynamic> c) {
    final q = _q.trim().toLowerCase();
    if (q.isNotEmpty) {
      final hay = '${c['name']} ${c['client']} ${c['party']} ${c['case_no']} ${c['court']}'.toLowerCase();
      if (!hay.contains(q)) return false;
    }
    if (_filter == 'hearing') return hearingInfo(c['hearing'])?.soon == true;
    if (_filter == 'unpaid') return dbl(c['fee']) > dbl(c['inc']);
    return true;
  }

  Widget _summary(List<Map<String, dynamic>> open) {
    final out = <String, double>{};
    for (final c in open) {
      final fee = dbl(c['fee']);
      final rem = fee - dbl(c['inc']);
      if (fee > 0 && rem > 0) {
        final cur = c['currency'].toString();
        out[cur] = (out[cur] ?? 0) + rem;
      }
    }
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(16)),
      child: Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
        Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${open.length}', style: const TextStyle(color: Colors.white, fontSize: 34, fontWeight: FontWeight.w800, height: 1)),
          const SizedBox(height: 4),
          Text(app.t('open_cases'), style: const TextStyle(color: Colors.white70, fontSize: 12)),
        ]),
        Container(width: 1, height: 44, margin: const EdgeInsets.symmetric(horizontal: 16), color: Colors.white24),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(app.t('outstanding'), style: const TextStyle(color: Colors.white70, fontSize: 12)),
            const SizedBox(height: 4),
            if (out.isEmpty)
              const Text('-', style: TextStyle(color: Colors.white, fontSize: 18))
            else
              for (final e in out.entries)
                FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: AlignmentDirectional.centerStart,
                  child: Text(money(e.value, e.key),
                      style: const TextStyle(color: kBrassLight, fontSize: 19, fontWeight: FontWeight.w800)),
                ),
          ]),
        ),
      ]),
    );
  }

  Widget _filters() {
    Widget chip(String key, String label) => Padding(
          padding: const EdgeInsetsDirectional.only(end: 8),
          child: ChoiceChip(
            label: Text(label),
            selected: _filter == key,
            showCheckmark: false,
            selectedColor: kInk,
            backgroundColor: Colors.white,
            labelStyle: TextStyle(color: _filter == key ? Colors.white : kInk, fontWeight: FontWeight.w600),
            side: const BorderSide(color: kLine),
            onSelected: (_) => setState(() => _filter = key),
          ),
        );
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(children: [
        chip('all', app.t('f_all')),
        chip('hearing', app.t('f_hearing')),
        chip('unpaid', app.t('f_unpaid')),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: app,
      builder: (context, _) {
        final open = app.cases.where((c) => c['status'] != 'closed').toList();
        final list = open.where(_matches).toList();
        return Scaffold(
          backgroundColor: kPaper,
          body: RefreshIndicator(
            onRefresh: () => app.load(quiet: true),
            child: CustomScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              slivers: [
                SliverToBoxAdapter(
                  child: PageHeader(
                    title: app.t('cases'),
                    actions: [
                      headerIcon(Icons.inventory_2_outlined,
                          () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ArchivePage())),
                          tip: app.t('archive')),
                      headerIcon(Icons.add_circle_outline, _openNew, tip: app.t('new_case')),
                      headerIcon(Icons.settings_outlined, () => openSettings(context)),
                    ],
                    child: _summary(open),
                  ),
                ),
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 10),
                    child: TextField(
                      onChanged: (v) => setState(() => _q = v),
                      decoration: InputDecoration(
                        hintText: app.t('search'),
                        prefixIcon: const Icon(Icons.search, color: kSlate),
                        filled: true,
                        fillColor: Colors.white,
                        isDense: true,
                        contentPadding: const EdgeInsets.symmetric(vertical: 14),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: kLine)),
                        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: kLine)),
                      ),
                    ),
                  ),
                ),
                SliverToBoxAdapter(child: _filters()),
                const SliverToBoxAdapter(child: SizedBox(height: 14)),
                if (list.isEmpty)
                  SliverToBoxAdapter(child: _Empty(noCases: open.isEmpty, onCreate: _openNew))
                else
                  SliverList(
                    delegate: SliverChildBuilderDelegate(
                      (context, i) => CaseFolder(
                        c: list[i],
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => CasePage(caseId: intOrNull(list[i]['id'])!)),
                        ),
                      ),
                      childCount: list.length,
                    ),
                  ),
                const SliverToBoxAdapter(child: SizedBox(height: 110)),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _Empty extends StatelessWidget {
  const _Empty({required this.noCases, required this.onCreate});

  final bool noCases;
  final VoidCallback onCreate;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(32, 40, 32, 0),
      child: Column(children: [
        Icon(noCases ? Icons.create_new_folder_outlined : Icons.search_off, size: 56, color: kSlate.withValues(alpha: 0.6)),
        const SizedBox(height: 14),
        Text(app.t(noCases ? 'empty_cases' : 'no_search'), textAlign: TextAlign.center, style: const TextStyle(color: kSlate, fontSize: 15)),
        if (noCases) ...[
          const SizedBox(height: 18),
          FilledButton.icon(onPressed: onCreate, icon: const Icon(Icons.add), label: Text(app.t('new_case'))),
        ],
      ]),
    );
  }
}
