import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'i18n.dart';

SupabaseClient get sb => Supabase.instance.client;

// ---------- small helpers ----------

double dbl(dynamic v) {
  if (v == null) return 0;
  if (v is num) return v.toDouble();
  return double.tryParse(v.toString()) ?? 0;
}

int? intOrNull(dynamic v) {
  if (v == null) return null;
  if (v is num) return v.toInt();
  return int.tryParse(v.toString());
}

List<Map<String, dynamic>> listOfMaps(dynamic v) {
  if (v is! List) return [];
  return v.map((e) => Map<String, dynamic>.from(e as Map)).toList();
}

String ymd(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

DateTime? parseYmd(dynamic v) {
  if (v == null) return null;
  return DateTime.tryParse(v.toString());
}

/// Accepts Arabic-Indic digits, commas and spaces: "١٢٬٥٠٠" -> 12500
double parseAmount(String s) {
  const ar = '٠١٢٣٤٥٦٧٨٩';
  const fa = '۰۱۲۳۴۵۶۷۸۹';
  final b = StringBuffer();
  for (final ch in s.split('')) {
    final i = ar.indexOf(ch);
    final j = fa.indexOf(ch);
    if (i >= 0) {
      b.write(i);
    } else if (j >= 0) {
      b.write(j);
    } else if (ch == '٫') {
      b.write('.');
    } else if (ch == ',' || ch == '٬' || ch == ' ') {
      continue;
    } else {
      b.write(ch);
    }
  }
  return double.tryParse(b.toString()) ?? 0;
}

String money(num v, String cur) {
  final usd = cur == 'USD';
  final neg = v < 0;
  final abs = v.abs();
  final fixed = usd ? abs.toStringAsFixed(2) : abs.round().toString();
  final parts = fixed.split('.');
  final ip = parts[0];
  final sbuf = StringBuffer();
  for (var i = 0; i < ip.length; i++) {
    if (i > 0 && (ip.length - i) % 3 == 0) sbuf.write(',');
    sbuf.write(ip[i]);
  }
  final body = parts.length > 1 ? '${sbuf.toString()}.${parts[1]}' : sbuf.toString();
  return '${neg ? '-' : ''}${usd ? '\$' : ''}$body${usd ? '' : ' IQD'}';
}

String errText(Object e, String lang) {
  final m = e is PostgrestException
      ? e.message
      : (e is AuthException ? e.message : e.toString());
  if (m.contains('taken')) return tr(lang, 'taken');
  if (m.contains('short')) return tr(lang, 'short');
  if (m.toLowerCase().contains('invalid login')) return tr(lang, 'bad_login');
  return '${tr(lang, 'error')}: $m';
}

// ---------- application state ----------

final AppState app = AppState();

class AppState extends ChangeNotifier {
  String lang = 'ku';
  Map<String, dynamic>? data; // result of api_dashboard
  Map<String, dynamic>? profile;
  int? accId;
  String period = 'month'; // today | week | month | all | range
  DateTimeRange? custom;
  bool loading = false;
  String? error;

  Future<void> init() async {
    final p = await SharedPreferences.getInstance();
    final l = p.getString('lang');
    if (l != null && kLangs.contains(l)) lang = l;
    notifyListeners();
  }

  String t(String k) => tr(lang, k);
  bool get rtl => lang != 'en';

  Future<void> setLang(String l) async {
    lang = l;
    final p = await SharedPreferences.getInstance();
    await p.setString('lang', l);
    notifyListeners();
  }

  void setPeriod(String p, {DateTimeRange? r}) {
    period = p;
    custom = r;
    load();
  }

  DateTime get _today {
    final n = DateTime.now();
    return DateTime(n.year, n.month, n.day);
  }

  (DateTime, DateTime) get _span {
    final td = _today;
    switch (period) {
      case 'today':
        return (td, td);
      case 'week':
        // weeks start on Saturday (same as the website)
        final py = td.weekday - 1; // Monday = 0
        return (DateTime(td.year, td.month, td.day - ((py - 5) % 7)), td);
      case 'all':
        return (DateTime(2000, 1, 1), DateTime(2100, 12, 31));
      case 'range':
        if (custom != null) return (custom!.start, custom!.end);
        return (DateTime(td.year, td.month, 1), td);
      default:
        return (DateTime(td.year, td.month, 1), DateTime(td.year, td.month + 1, 0));
    }
  }

  Future<void> load({bool quiet = false}) async {
    if (!quiet) {
      loading = true;
      error = null;
      notifyListeners();
    }
    try {
      final td = _today;
      final py = td.weekday - 1;
      final (from, to) = _span;
      final r = await sb.rpc('api_dashboard', params: {
        'p_acc': accId,
        'p_today': ymd(td),
        'p_week': ymd(DateTime(td.year, td.month, td.day - ((py - 5) % 7))),
        'p_month': ymd(DateTime(td.year, td.month, 1)),
        'p_from': ymd(from),
        'p_to': ymd(to),
      });
      data = Map<String, dynamic>.from(r as Map);
      accId = intOrNull(data!['acc']);
      error = null;
    } catch (e) {
      error = errText(e, lang);
    }
    loading = false;
    notifyListeners();
  }

  Future<void> loadProfile() async {
    try {
      final r = await sb.rpc('api_profile');
      profile = Map<String, dynamic>.from(r as Map);
      notifyListeners();
    } catch (_) {}
  }

  /// Called right after sign-in: makes sure the wallet profile exists.
  Future<void> bootstrap() async {
    final email = sb.auth.currentUser?.email ?? '';
    final name = email.split('@').first;
    await sb.rpc('app_bootstrap', params: {'p_username': name, 'p_account_name': lang == 'en' ? 'Main' : (lang == 'ar' ? 'الرئيسي' : 'سەرەکی')});
    await Future.wait([load(), loadProfile()]);
  }

  void reset() {
    data = null;
    profile = null;
    accId = null;
    error = null;
    notifyListeners();
  }

  // ---------- derived ----------

  List<Map<String, dynamic>> get accounts => listOfMaps(data?['accounts']);
  List<Map<String, dynamic>> get cases => listOfMaps(data?['cases']);

  Map<String, dynamic>? get account {
    for (final a in accounts) {
      if (intOrNull(a['id']) == accId) return a;
    }
    return accounts.isNotEmpty ? accounts.first : null;
  }

  String get currency => (account?['currency'] ?? 'IQD').toString();
  String get role => (account?['role'] ?? 'owner').toString();
  bool get canEdit => role != 'viewer';

  double get balance {
    for (final b in listOfMaps(data?['bal'])) {
      if (intOrNull(b['id']) == accId) return dbl(b['b']);
    }
    return 0;
  }

  Map<String, double> periodSums(String key) {
    final p = data?['periods'];
    if (p is Map && p[key] is Map) {
      return {'i': dbl((p[key] as Map)['i']), 'e': dbl((p[key] as Map)['e'])};
    }
    return {'i': 0, 'e': 0};
  }

  // ---------- actions ----------

  Future<void> selectAccount(int id) async {
    accId = id;
    await load();
  }

  Future<void> addTx(int acc, String type, double amount, String label, String note, DateTime date) async {
    await sb.rpc('api_add_tx', params: {
      'p_acc': acc,
      'p_type': type,
      'p_amount': amount,
      'p_label': label,
      'p_note': note,
      'p_date': ymd(date),
    });
    await load(quiet: true);
  }

  Future<void> editTx(int id, double amount, String label, String note, DateTime date) async {
    final ok = await sb.rpc('api_edit_tx', params: {
      'p_id': id,
      'p_amount': amount,
      'p_label': label,
      'p_note': note,
      'p_date': ymd(date),
    });
    if (ok != true) throw Exception('forbidden');
    await load(quiet: true);
  }

  Future<void> delTx(int id) async {
    await sb.rpc('api_del_tx', params: {'p_id': id});
    await load(quiet: true);
  }
}
