// Supabase > Project Settings > API: copy "Project URL" and the "anon public" key.
// The anon key is meant to be public. NEVER put the service_role key in the app.
//
// You can either edit the two defaults below, or pass them at build time:
//   --dart-define=SUPABASE_URL=...  --dart-define=SUPABASE_ANON_KEY=...
const String supabaseUrl = String.fromEnvironment(
  'SUPABASE_URL',
  defaultValue: 'https://YOUR-PROJECT.supabase.co',
);
const String supabaseAnonKey = String.fromEnvironment(
  'SUPABASE_ANON_KEY',
  defaultValue: 'YOUR-ANON-KEY',
);

// Usernames are stored as "<username>@<domain>" inside Supabase Auth.
const String usernameDomain = 'wallet-dana.app';

// Google sign-in (leave empty to hide the button). See README_KU.md.
const String googleWebClientId = String.fromEnvironment('GOOGLE_WEB_CLIENT_ID');
const String googleIosClientId = String.fromEnvironment('GOOGLE_IOS_CLIENT_ID');
