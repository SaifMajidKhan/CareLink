import 'dart:async';
import 'dart:convert';
import 'dart:io';

class ApiFailure implements Exception {
  ApiFailure(this.message, [this.status = 0, this.fieldErrors = const {}]);
  final String message;
  final int status;
  final Map<String, String> fieldErrors;

  factory ApiFailure.response(int status, dynamic payload) {
    final detail = payload is Map ? payload['detail'] : null;
    if (detail is String) return ApiFailure(detail, status);
    final fields = <String, String>{};
    if (detail is List) {
      for (final entry in detail.whereType<Map>()) {
        final location = entry['loc'];
        final field = location is List && location.length > 1
            ? '${location[1]}'
            : '';
        final type = entry['type'];
        final context = entry['ctx'];
        var message = '${entry['msg'] ?? 'Check this value.'}'.replaceFirst(
          RegExp(r'^Value error,\s*'),
          '',
        );
        if (type == 'string_too_short' && context is Map) {
          message = 'Use at least ${context['min_length']} characters.';
        } else if (type == 'string_too_long' && context is Map) {
          message = 'Use ${context['max_length']} characters or fewer.';
        }
        if (field.isNotEmpty) fields.putIfAbsent(field, () => message);
      }
    }
    final message = fields.isNotEmpty
        ? fields.entries.map((e) => '${_label(e.key)}: ${e.value}').join('\n')
        : status >= 500
        ? 'CareLink is temporarily unavailable. Please try again shortly.'
        : 'Please check your details and try again.';
    return ApiFailure(message, status, fields);
  }

  static String _label(String field) => switch (field) {
    'email' => 'Email',
    'password' => 'Password',
    'name' => 'Name',
    _ => field.replaceAll('_', ' '),
  };
  @override
  String toString() => message;
}

class ApiClient {
  ApiClient(this.baseUrl, {this.token});
  final String baseUrl;
  String? token;
  Future<dynamic> call(String method, String path, [Object? body]) async {
    final base = Uri.parse(baseUrl);
    if (base.scheme != 'https' &&
        !(base.scheme == 'http' &&
            ['localhost', '127.0.0.1', '10.0.2.2'].contains(base.host))) {
      throw ApiFailure(
        'Use HTTPS for remote servers. HTTP is allowed only for local development.',
      );
    }
    final client = HttpClient()
      ..connectionTimeout = const Duration(seconds: 10);
    try {
      final request = await client
          .openUrl(method, Uri.parse('$baseUrl$path'))
          .timeout(const Duration(seconds: 12));
      request.headers.contentType = ContentType.json;
      if (token != null) request.headers.set('Authorization', 'Bearer $token');
      if (body != null) request.write(jsonEncode(body));
      final response = await request.close().timeout(
        const Duration(seconds: 75),
      );
      final text = await response
          .transform(utf8.decoder)
          .join()
          .timeout(const Duration(seconds: 15));
      dynamic decoded;
      if (text.isNotEmpty) {
        try {
          decoded = jsonDecode(text);
        } on FormatException {
          if (response.statusCode < 400) {
            throw ApiFailure(
              'The server returned an unexpected response. Please try again.',
            );
          }
        }
      }
      if (response.statusCode >= 400) {
        throw ApiFailure.response(response.statusCode, decoded);
      }
      return decoded;
    } on ApiFailure {
      rethrow;
    } on TimeoutException {
      throw ApiFailure(
        'CareLink is taking longer to respond. Please try again shortly.',
      );
    } catch (_) {
      throw ApiFailure(
        'Cannot reach the server. Check your connection and server address.',
      );
    } finally {
      client.close(force: true);
    }
  }
}
