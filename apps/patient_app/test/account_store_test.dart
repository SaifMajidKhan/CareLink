import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:carelink_patient/connected/data/account_store.dart';
import 'package:carelink_patient/connected/data/api_client.dart';

class StubApi extends ApiClient {
  StubApi(super.baseUrl);
  int? failure;
  int uploads = 0;
  @override
  Future<dynamic> call(String method, String path, [Object? body]) async {
    uploads++;
    if (failure != null) throw ApiFailure('Upload failed', failure!);
    return {...body! as Map<String, dynamic>, 'version': 1};
  }
}

void main() {
  sqfliteFfiInit();
  test(
    'pending reports survive restart and disappear only after acknowledgement',
    () async {
      final folder = await Directory.systemTemp.createTemp('carelink-outbox-');
      final file = '${folder.path}/test.db';
      final api = StubApi('http://localhost:8000')..failure = 0;
      AccountStore create() => AccountStore(
        api,
        'patient-a',
        factory: databaseFactoryFfi,
        databasePath: file,
      );
      var store = create();
      await store.queue('dose-a', {
        'request_id': 'stable-request',
        'outcome': 'taken',
      });
      await store.sync();
      expect((await store.pending()).single['error'], 'Upload failed');
      await store.close();
      store = create();
      expect(
        (await store.pending()).single['body']['request_id'],
        'stable-request',
      );
      api.failure = null;
      await store.sync();
      expect(await store.pending(), isEmpty);
      expect(
        (await store.cached('report:dose-a'))!['data']['outcome'],
        'taken',
      );
      await store.close();
      await folder.delete(recursive: true);
    },
  );
  test('accounts and server addresses have separate local caches', () async {
    final folder = await Directory.systemTemp.createTemp('carelink-scope-');
    final file = '${folder.path}/test.db';
    final a = AccountStore(
      StubApi('http://server-a'),
      'patient',
      factory: databaseFactoryFfi,
      databasePath: file,
    );
    final b = AccountStore(
      StubApi('http://server-a'),
      'other',
      factory: databaseFactoryFfi,
      databasePath: file,
    );
    final c = AccountStore(
      StubApi('http://server-b'),
      'patient',
      factory: databaseFactoryFfi,
      databasePath: file,
    );
    await a.cache('doses', [
      {'name': 'Private'},
    ]);
    expect(await b.cached('doses'), isNull);
    expect(await c.cached('doses'), isNull);
    await a.close();
    await b.close();
    await c.close();
    await folder.delete(recursive: true);
  });
  test('conflict retains the local report and duplicate queue taps do not overwrite it', () async {
    final store = AccountStore(
      StubApi('http://server')..failure = 409,
      'patient',
      factory: databaseFactoryFfi,
      databasePath: inMemoryDatabasePath,
    );
    await store.queue('dose', {'outcome': 'taken'});
    await expectLater(
      store.queue('dose', {'outcome': 'skipped'}),
      throwsA(isA<DatabaseException>()),
    );
    await store.sync();
    expect((await store.pending()).single['body']['outcome'], 'taken');
    await store.close();
  });
}
