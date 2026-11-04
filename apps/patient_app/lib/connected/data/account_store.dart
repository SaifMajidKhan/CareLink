import 'dart:convert';
import 'dart:math';

import 'package:path/path.dart' as path;
import 'package:sqflite/sqflite.dart';

import 'api_client.dart';

String dayKey(DateTime date) =>
    '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
String requestId() => List.generate(
  24,
  (_) => Random.secure().nextInt(256).toRadixString(16).padLeft(2, '0'),
).join();

/// Account- and server-scoped cache; legacy fictional records are never uploaded.
class AccountStore {
  AccountStore(this.api, this.userId, {this.factory, this.databasePath});
  final DatabaseFactory? factory;
  final String? databasePath;
  final ApiClient api;
  final String userId;
  Database? _db;
  Future<Database>? _opening;
  String get scope => '${api.baseUrl}|$userId';
  Future<Database> open() async {
    try {
      return await (_opening ??= _open());
    } catch (_) {
      _opening = null;
      rethrow;
    }
  }

  Future<Database> _open() async {
    final selectedFactory = factory ?? databaseFactory;
    return _db = await selectedFactory.openDatabase(
      databasePath ??
          path.join(
            await selectedFactory.getDatabasesPath(),
            'carelink_accounts_v1.db',
          ),
      options: OpenDatabaseOptions(
        version: 1,
        onCreate: (db, _) async {
          await db.execute(
            'CREATE TABLE cache(scope TEXT, key TEXT, body TEXT NOT NULL, updated TEXT NOT NULL, PRIMARY KEY(scope,key))',
          );
          await db.execute(
            'CREATE TABLE outbox(scope TEXT, key TEXT, body TEXT NOT NULL, error TEXT, PRIMARY KEY(scope,key))',
          );
        },
      ),
    );
  }

  Future<void> cache(String key, dynamic body) async => (await open())
      .insert('cache', {
        'scope': scope,
        'key': key,
        'body': jsonEncode(body),
        'updated': DateTime.now().toUtc().toIso8601String(),
      }, conflictAlgorithm: ConflictAlgorithm.replace)
      .then((_) {});
  Future<Map<String, dynamic>?> cached(String key) async {
    final rows = await (await open()).query(
      'cache',
      where: 'scope=? AND key=?',
      whereArgs: [scope, key],
    );
    if (rows.isEmpty) return null;
    return {
      'data': jsonDecode(rows.first['body'] as String),
      'updated': rows.first['updated'],
    };
  }

  Future<List<Map<String, dynamic>>> pending() async {
    final rows = await (await open()).query(
      'outbox',
      where: 'scope=?',
      whereArgs: [scope],
    );
    return rows
        .map(
          (r) => {
            'key': r['key'],
            'body': jsonDecode(r['body'] as String),
            'error': r['error'],
          },
        )
        .toList();
  }

  Future<void> queue(String key, Map<String, dynamic> body) async {
    await (await open()).insert('outbox', {
      'scope': scope,
      'key': key,
      'body': jsonEncode(body),
    }, conflictAlgorithm: ConflictAlgorithm.abort);
  }

  bool _syncing = false;
  Future<void> sync() async {
    if (_syncing) return;
    _syncing = true;
    try {
      for (final entry in await pending()) {
        try {
          final saved = await api.call('POST', '/reports', entry['body']);
          // Persist acknowledgement before removing the queue item.
          await cache('report:${entry['key']}', saved);
          await (await open()).delete(
            'outbox',
            where: 'scope=? AND key=?',
            whereArgs: [scope, entry['key']],
          );
        } on ApiFailure catch (e) {
          await (await open()).update(
            'outbox',
            {'error': e.message},
            where: 'scope=? AND key=?',
            whereArgs: [scope, entry['key']],
          );
          if (e.status == 0 || e.status == 401) break;
        }
      }
    } finally {
      _syncing = false;
    }
  }

  Future<void> discardConflict(String key) async {
    await (await open()).delete(
      'outbox',
      where: 'scope=? AND key=?',
      whereArgs: [scope, key],
    );
  }

  Future<void> clear() async {
    final db = await open();
    await db.transaction((txn) async {
      await txn.delete('cache', where: 'scope=?', whereArgs: [scope]);
      await txn.delete('outbox', where: 'scope=?', whereArgs: [scope]);
    });
  }

  Future<void> close() async {
    await _db?.close();
  }
}
