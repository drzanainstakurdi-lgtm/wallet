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
  final TextEditingController _search = TextEditingController();
  String _q = '';
  String _filter = 'all'; // all | hearing | unpaid

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  void _openNew() => Navigator.push(context, MaterialPageRoute(builder: (_) => const NewCasePage()));

  bool _isHearing(Map<String, dynamic> c) => hearingInfo(c['hearing'])?.soon == true;
  bool _isUnpaid(Map<String, dynamic> c) => dbl(c['fee']) > dbl(c['inc']);

  bool _matches(Map<String, dynamic> c) {
    final q = _q.trim().toLowerCase();
    if (q.isNotEmpty) {
      final hay = '${c['name']} ${c['client']} ${c['party']} ${c['case_no']} ${c['court']}'.toLowerCase();
      if (!hay.contains(q)) return false;
    }
    if (_filter == 'hearing') return _isHearing(c);
    if (_filter == 'unpaid') return _isUnpaid(c);
    return true;
  }

  // ---------- header summary ----------

  Widget _stat(String value, String label, {Color color = Colors.white}) => Expanded(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(value, style: TextStyle(color: color, fontSize: 32, fontWeight: FontWeight.w800, height: 1)),
          const SizedBox(height: 6),
          Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.white70, fontSize: 12)),
        ]),
      );

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
    final soon = open.where(_isHearing).length;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: Colors.white.withValues(alpha: 0.14)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
          _stat('${open.length}', app.t('open_cases')),
          Container(width: 1, height: 44, margin: const EdgeInsets.symmetric(horizontal: 16), color: Colors.white24),
          _stat('$soon', app.t('f_hearing'), color: soon > 0 ? kBrassLight : Colors.white),
        ]),
        if (out.isNotEmpty) ...[
          const SizedBox(height: 14),
          Container(height: 1, color: Colors.white12),
          const SizedBox(height: 12),
          Text(app.t('outstanding'), style: const TextStyle(color: Colors.white70, fontSize: 12)),
          const SizedBox(height: 4),
          Wrap(spacing: 18, runSpacing: 2, children: [
            for (final e in out.entries)
              Text(money(e.value, e.key),
                  textDirection: TextDirection.ltr,
                  style: const TextStyle(color: kBrassLight, fontSize: 21, fontWeight: FontWeight.w800)),
          ]),
        ],
      ]),
    );
  }

  // ---------- search + filters ----------

  Widget _searchBox() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 18, 16, 12),
      child: Container(
        decoration: BoxDecoration(borderRadius: BorderRadius.circular(18), boxShadow: kSoftShadow),
        child: TextField(
          controller: _search,
          onChanged: (v) => setState(() => _q = v),
          decoration: InputDecoration(
            hintText: app.t('search'),
            hintStyle: const TextStyle(color: kSlate),
            prefixIcon: const Icon(Icons.search_rounded, color: kSlate),
            suffixIcon: _q.isEmpty
                ? null
                : IconButton(
                    icon: const Icon(Icons.close_rounded, color: kSlate, size: 20),
                    onPressed: () {
                      _search.clear();
                      setState(() => _q = '');
                    },
                  ),
            filled: true,
            fillColor: Colors.white,
            isDense: true,
            contentPadding: const EdgeInsets.symmetric(vertical: 15),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(18), borderSide: BorderSide.none),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(18), borderSide: BorderSide.none),
            focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(18), borderSide: const BorderSide(color: kInk, width: 1.2)),
          ),
        ),
      ),
    );
  }

  Widget _chip(String key, String label, int n) {
    final sel = _filter == key;
    return Padding(
      padding: const EdgeInsetsDirectional.only(end: 8),
      child: Material(
        color: sel ? kInk : Colors.white,
        borderRadius: BorderRadius.circular(30),
        child: InkWell(
          borderRadius: BorderRadius.circular(30),
          onTap: () => setState(() => _filter = key),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(30),
              border: Border.all(color: sel ? kInk : kLine),
            ),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Text(label, style: TextStyle(color: sel ? Colors.white : kInk, fontWeight: FontWeight.w700, fontSize: 13)),
              const SizedBox(width: 7),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(
                  color: sel ? Colors.white.withValues(alpha: 0.2) : kPaper,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text('$n', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: sel ? Colors.white : kSlate)),
              ),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _filters(List<Map<String, dynamic>> open) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(children: [
        _chip('all', app.t('f_all'), open.length),
        _chip('hearing', app.t('f_hearing'), open.where(_isHearing).length),
        _chip('unpaid', app.t('f_unpaid'), open.where(_isUnpaid).length),
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
                      headerIcon(Icons.add_rounded, _openNew, tip: app.t('new_case')),
                      headerIcon(Icons.settings_outlined, () => openSettings(context)),
                    ],
                    child: _summary(open),
                  ),
                ),
                SliverToBoxAdapter(child: _searchBox()),
                SliverToBoxAdapter(child: _filters(open)),
                const SliverToBoxAdapter(child: SizedBox(height: 18)),
                if (list.isEmpty)
                  SliverToBoxAdapter(child: _Empty(noCases: open.isEmpty, onCreate: _openNew))
                else
                  SliverList(
                    delegate: SliverChildBuilderDelegate(
                      (context, i) => TweenAnimationBuilder<double>(
                        tween: Tween(begin: 0, end: 1),
                        duration: Duration(milliseconds: 260 + (i > 6 ? 6 : i) * 45),
                        curve: Curves.easeOutCubic,
                        builder: (context, v, child) => Opacity(
                          opacity: v,
                          child: Transform.translate(offset: Offset(0, (1 - v) * 16), child: child),
                        ),
                        child: CaseFolder(
                          c: list[i],
                          onTap: () => Navigator.push(
                            context,
                            MaterialPageRoute(builder: (_) => CasePage(caseId: intOrNull(list[i]['id'])!)),
                          ),
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
      padding: const EdgeInsets.fromLTRB(32, 36, 32, 0),
      child: Column(children: [
        Container(
          width: 96,
          height: 96,
          decoration: BoxDecoration(color: kInk.withValues(alpha: 0.07), shape: BoxShape.circle),
          child: Icon(noCases ? Icons.create_new_folder_outlined : Icons.search_off_rounded, size: 44, color: kInk.withValues(alpha: 0.7)),
        ),
        const SizedBox(height: 18),
        Text(app.t(noCases ? 'empty_cases' : 'no_search'),
            textAlign: TextAlign.center, style: const TextStyle(color: kSlate, fontSize: 15, height: 1.5)),
        if (noCases) ...[
          const SizedBox(height: 20),
          FilledButton.icon(
            onPressed: onCreate,
            icon: const Icon(Icons.add_rounded),
            label: Text(app.t('new_case')),
            style: FilledButton.styleFrom(
              backgroundColor: kInk,
              padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 14),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            ),
          ),
        ],
      ]),
    );
  }
}
