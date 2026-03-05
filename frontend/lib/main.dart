import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

const String apiBaseUrl =
    String.fromEnvironment('API_BASE_URL', defaultValue: 'http://localhost:8000');

void main() {
  runApp(const ProviderScope(child: HooThatShowApp()));
}

class HooThatShowApp extends StatelessWidget {
  const HooThatShowApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'HooThatShow AI',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal),
        useMaterial3: true,
      ),
      home: const AuthGate(),
    );
  }
}

class ApiClient {
  ApiClient(this.baseUrl);
  final String baseUrl;

  Future<Map<String, dynamic>> register(String email, String password) async {
    final resp = await http.post(
      Uri.parse('$baseUrl/api/v1/auth/register'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );
    _ensureOk(resp);
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> login(String email, String password) async {
    final resp = await http.post(
      Uri.parse('$baseUrl/api/v1/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );
    _ensureOk(resp);
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> analyze(
    String token,
    String title,
    List<String> sources,
    bool forceRefresh,
  ) async {
    final resp = await http.post(
      Uri.parse('$baseUrl/api/v1/analyze'),
      headers: _authHeaders(token),
      body: jsonEncode({
        'title': title,
        'sources': sources,
        'force_refresh': forceRefresh,
      }),
    );
    _ensureOk(resp);
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> fetchAnalysis(String token, String id) async {
    final resp = await http.get(
      Uri.parse('$baseUrl/api/v1/analyze/$id'),
      headers: _authHeaders(token),
    );
    _ensureOk(resp);
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<List<dynamic>> history(String token) async {
    final resp = await http.get(
      Uri.parse('$baseUrl/api/v1/history'),
      headers: _authHeaders(token),
    );
    _ensureOk(resp);
    final decoded = jsonDecode(resp.body) as Map<String, dynamic>;
    return decoded['results'] as List<dynamic>? ?? [];
  }

  Map<String, String> _authHeaders(String token) => {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      };

  void _ensureOk(http.Response resp) {
    if (resp.statusCode >= 200 && resp.statusCode < 300) {
      return;
    }
    throw Exception('Request failed: ${resp.statusCode} ${resp.body}');
  }
}

final apiProvider = Provider<ApiClient>((ref) => ApiClient(apiBaseUrl));

class AuthState {
  const AuthState({this.token, this.email, this.loading = false, this.error});
  final String? token;
  final String? email;
  final bool loading;
  final String? error;

  AuthState copyWith({String? token, String? email, bool? loading, String? error}) {
    return AuthState(
      token: token ?? this.token,
      email: email ?? this.email,
      loading: loading ?? this.loading,
      error: error,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier(this._api) : super(const AuthState()) {
    _load();
  }

  final ApiClient _api;

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('token');
    final email = prefs.getString('email');
    if (token != null) {
      state = state.copyWith(token: token, email: email);
    }
  }

  Future<void> register(String email, String password) async {
    state = state.copyWith(loading: true, error: null);
    try {
      await _api.register(email, password);
      await login(email, password);
    } catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }

  Future<void> login(String email, String password) async {
    state = state.copyWith(loading: true, error: null);
    try {
      final data = await _api.login(email, password);
      final token = data['access'] as String?;
      if (token == null) throw Exception('Missing token');
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('token', token);
      await prefs.setString('email', email);
      state = state.copyWith(token: token, email: email, loading: false);
    } catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('token');
    await prefs.remove('email');
    state = const AuthState();
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(ref.read(apiProvider));
});

class AnalysisState {
  const AnalysisState({
    this.loading = false,
    this.error,
    this.current,
  });

  final bool loading;
  final String? error;
  final Map<String, dynamic>? current;

  AnalysisState copyWith({bool? loading, String? error, Map<String, dynamic>? current}) {
    return AnalysisState(
      loading: loading ?? this.loading,
      error: error,
      current: current ?? this.current,
    );
  }
}

class AnalysisNotifier extends StateNotifier<AnalysisState> {
  AnalysisNotifier(this._api) : super(const AnalysisState());
  final ApiClient _api;
  Timer? _pollTimer;

  Future<void> analyze(String token, String title, List<String> sources, bool forceRefresh) async {
    state = state.copyWith(loading: true, error: null);
    try {
      final data = await _api.analyze(token, title, sources, forceRefresh);
      state = state.copyWith(current: data, loading: false);
      _startPolling(token, data['id'] as String);
    } catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }

  void _startPolling(String token, String id) {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 3), (timer) async {
      final data = await _api.fetchAnalysis(token, id);
      state = state.copyWith(current: data);
      if (data['status'] == 'done' || data['status'] == 'failed') {
        timer.cancel();
      }
    });
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }
}

final analysisProvider =
    StateNotifierProvider<AnalysisNotifier, AnalysisState>((ref) => AnalysisNotifier(ref.read(apiProvider)));

class AuthGate extends ConsumerWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    if (auth.token != null) {
      return const HomePage();
    }
    return const AuthPage();
  }
}

class AuthPage extends ConsumerStatefulWidget {
  const AuthPage({super.key});

  @override
  ConsumerState<AuthPage> createState() => _AuthPageState();
}

class _AuthPageState extends ConsumerState<AuthPage> {
  bool isLogin = true;
  final emailCtrl = TextEditingController();
  final passCtrl = TextEditingController();

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('HooThatShow AI', style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: 16),
                  TextField(controller: emailCtrl, decoration: const InputDecoration(labelText: 'Email')),
                  const SizedBox(height: 12),
                  TextField(
                    controller: passCtrl,
                    decoration: const InputDecoration(labelText: 'Password'),
                    obscureText: true,
                  ),
                  const SizedBox(height: 16),
                  if (auth.error != null)
                    Text(auth.error!, style: const TextStyle(color: Colors.red)),
                  const SizedBox(height: 8),
                  FilledButton(
                    onPressed: auth.loading
                        ? null
                        : () {
                            if (isLogin) {
                              ref.read(authProvider.notifier).login(emailCtrl.text, passCtrl.text);
                            } else {
                              ref.read(authProvider.notifier).register(emailCtrl.text, passCtrl.text);
                            }
                          },
                    child: Text(isLogin ? 'Login' : 'Register'),
                  ),
                  TextButton(
                    onPressed: () => setState(() => isLogin = !isLogin),
                    child: Text(isLogin ? 'Need an account? Register' : 'Have an account? Login'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class HomePage extends ConsumerStatefulWidget {
  const HomePage({super.key});

  @override
  ConsumerState<HomePage> createState() => _HomePageState();
}

class _HomePageState extends ConsumerState<HomePage> {
  int index = 0;

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('HooThatShow AI'),
        actions: [
          TextButton(
            onPressed: () => ref.read(authProvider.notifier).logout(),
            child: const Text('Logout'),
          ),
        ],
      ),
      body: index == 0 ? const SearchScreen() : const HistoryScreen(),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (value) => setState(() => index = value),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.search), label: 'Search'),
          NavigationDestination(icon: Icon(Icons.history), label: 'History'),
        ],
      ),
    );
  }
}

class SearchScreen extends ConsumerStatefulWidget {
  const SearchScreen({super.key});

  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  final titleCtrl = TextEditingController();
  final sources = <String, bool>{
    'imdb': true,
    'rotten': true,
    'metacritic': true,
    'letterboxd': false,
    'reddit': true,
  };
  bool forceRefresh = false;

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);
    final analysis = ref.watch(analysisProvider);
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        TextField(
          controller: titleCtrl,
          decoration: const InputDecoration(labelText: 'Movie / Show Title'),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 12,
          children: sources.keys
              .map((source) => FilterChip(
                    label: Text(source),
                    selected: sources[source] ?? false,
                    onSelected: (value) => setState(() => sources[source] = value),
                  ))
              .toList(),
        ),
        const SizedBox(height: 12),
        SwitchListTile(
          value: forceRefresh,
          onChanged: (value) => setState(() => forceRefresh = value),
          title: const Text('Force refresh'),
        ),
        const SizedBox(height: 12),
        FilledButton(
          onPressed: analysis.loading
              ? null
              : () {
                  final selected = sources.entries.where((e) => e.value).map((e) => e.key).toList();
                  ref.read(analysisProvider.notifier).analyze(
                        auth.token!,
                        titleCtrl.text,
                        selected,
                        forceRefresh,
                      );
                },
          child: const Text('Analyze'),
        ),
        const SizedBox(height: 24),
        if (analysis.error != null) Text(analysis.error!, style: const TextStyle(color: Colors.red)),
        if (analysis.current != null) AnalysisResultCard(data: analysis.current!),
      ],
    );
  }
}

class AnalysisResultCard extends StatelessWidget {
  const AnalysisResultCard({super.key, required this.data});
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final status = data['status'] as String? ?? 'unknown';
    final result = data['result'] as Map<String, dynamic>?;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Status: $status', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            if (result != null) ...[
              Text(result['summary'] ?? '', style: Theme.of(context).textTheme.bodyLarge),
              const SizedBox(height: 12),
              Text('Criticisms', style: Theme.of(context).textTheme.titleSmall),
              const SizedBox(height: 8),
              for (final item in (result['criticisms'] as List<dynamic>? ?? []))
                Text('• ${item['label'] ?? 'Unknown'}'),
            ],
          ],
        ),
      ),
    );
  }
}

class HistoryScreen extends ConsumerWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return FutureBuilder<List<dynamic>>(
      future: ref.read(apiProvider).history(ref.read(authProvider).token!),
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        final items = snapshot.data!;
        if (items.isEmpty) {
          return const Center(child: Text('No history yet'));
        }
        return ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: items.length,
          itemBuilder: (context, index) {
            final item = items[index] as Map<String, dynamic>;
            return ListTile(
              title: Text(item['title'] ?? ''),
              subtitle: Text('Status: ${item['status']}'),
            );
          },
        );
      },
    );
  }
}
