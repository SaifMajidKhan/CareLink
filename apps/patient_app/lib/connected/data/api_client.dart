import 'dart:async';
import 'dart:convert';
import 'dart:io';

class ApiFailure implements Exception {
  ApiFailure(this.message, [this.status = 0]);
  final String message;
  final int status;
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
        const Duration(seconds: 15),
      );
      final text = await response
          .transform(utf8.decoder)
          .join()
          .timeout(const Duration(seconds: 15));
      final decoded = text.isEmpty ? null : jsonDecode(text);
      if (response.statusCode >= 400) {
        final detail = decoded is Map ? decoded['detail'] : null;
        throw ApiFailure(
          detail is String
              ? detail
              : 'Please check your entries (${response.statusCode}).',
          response.statusCode,
        );
      }
      return decoded;
    } on ApiFailure {
      rethrow;
    } catch (_) {
      throw ApiFailure(
        'Cannot reach the server. Check your connection and server address.',
      );
    } finally {
      client.close(force: true);
    }
  }
}
