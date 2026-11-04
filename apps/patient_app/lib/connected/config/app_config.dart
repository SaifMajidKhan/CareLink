/// Deployment settings belong to the build, not the patient's sign-in form.
class AppConfig {
  static const apiBase = String.fromEnvironment(
    'CARELINK_API',
    defaultValue: 'https://carelink-api-orjq.onrender.com',
  );
  static const callbackScheme = 'carelink';
  static const callbackHost = 'auth';
  static const callbackPath = '/callback';
}
