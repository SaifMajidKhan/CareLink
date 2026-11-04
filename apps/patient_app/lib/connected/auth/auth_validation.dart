/// Keep these limits in sync with the backend's Credentials and Registration.
class AuthValidation {
  static String? name(String? value) {
    final text = (value ?? '').trim();
    if (text.isEmpty) return 'Enter your name.';
    if (text.runes.length > 80) return 'Use 80 characters or fewer.';
    return null;
  }

  static String? email(String? value) {
    final text = (value ?? '').trim();
    if (text.isEmpty) return 'Enter your email address.';
    if (text.length > 254 ||
        !RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$').hasMatch(text)) {
      return 'Enter a valid email address.';
    }
    return null;
  }

  static String? password(String? value) {
    final length = (value ?? '').runes.length;
    if (length < 10) return 'Use at least 10 characters.';
    if (length > 128) return 'Use 128 characters or fewer.';
    return null;
  }
}
