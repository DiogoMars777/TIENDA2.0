// ==============================================================================
// SERVICIO DE BASE DE DATOS LOCAL MÓVIL (PERSISTENCIA OFFLINE EN DISPOSITIVO)
// Ubicación: mobile-app/lib/services/local_storage_service.dart
// ==============================================================================

import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';

class LocalStorageService {
  static final Map<String, String> _memoryFallback = {};

  static Future<File?> _getFile(String key) async {
    if (kIsWeb) return null;
    try {
      final dir = await getApplicationDocumentsDirectory();
      final safeKey = key.replaceAll(RegExp(r'[^a-zA-Z0-9_\-]'), '_');
      return File('${dir.path}/$safeKey.json');
    } catch (e) {
      debugPrint('LocalStorageService _getFile error: $e');
      return null;
    }
  }

  /// Guarda un objeto JSON (Map o List) en el almacenamiento interno del teléfono
  static Future<void> saveJson(String key, dynamic data) async {
    try {
      final raw = json.encode(data);
      _memoryFallback[key] = raw;
      final file = await _getFile(key);
      if (file != null) {
        await file.writeAsString(raw, flush: true);
      }
    } catch (e) {
      debugPrint('LocalStorageService saveJson($key) error: $e');
    }
  }

  /// Lee un objeto JSON (Map o List) desde el almacenamiento interno del teléfono
  static Future<dynamic> readJson(String key) async {
    try {
      final file = await _getFile(key);
      if (file != null && await file.exists()) {
        final raw = await file.readAsString();
        if (raw.trim().isNotEmpty) {
          _memoryFallback[key] = raw;
          return json.decode(raw);
        }
      }
      if (_memoryFallback.containsKey(key)) {
        return json.decode(_memoryFallback[key]!);
      }
    } catch (e) {
      debugPrint('LocalStorageService readJson($key) error: $e');
    }
    return null;
  }

  /// Elimina una clave del almacenamiento interno
  static Future<void> remove(String key) async {
    try {
      _memoryFallback.remove(key);
      final file = await _getFile(key);
      if (file != null && await file.exists()) {
        await file.delete();
      }
    } catch (e) {
      debugPrint('LocalStorageService remove($key) error: $e');
    }
  }
}

