/// The code identifies a patient for a request. It is not an access token.
abstract final class PatientCode {
  static const _prefix = 'carelink:patient:';
  static final _idPattern = RegExp(r'^CL-[0-9A-F]{16}$');

  static String encode(String id) => '$_prefix$id';

  static String? fromScan(String? value) {
    if (value == null || !value.startsWith(_prefix)) return null;
    return _parseId(value.substring(_prefix.length));
  }

  static String? fromInput(String value) {
    final input = value.trim();
    return input.startsWith(_prefix) ? fromScan(input) : _parseId(input);
  }

  static String? _parseId(String value) {
    final id = value.trim().toUpperCase();
    return _idPattern.hasMatch(id) ? id : null;
  }
}
