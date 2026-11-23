import 'package:flutter/material.dart';

import 'pages/charts_page.dart';
import 'pages/settings_page.dart';

/// Opens the charts / settings pages from the app bar icons.
void openCharts(BuildContext c) => Navigator.push(c, MaterialPageRoute(builder: (_) => const ChartsPage()));
void openSettings(BuildContext c) => Navigator.push(c, MaterialPageRoute(builder: (_) => const SettingsPage()));
