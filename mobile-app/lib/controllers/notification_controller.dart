// ==============================================================================
// CAPA CONTROLADOR (MVC - CONTROLLER EN FLUTTER / DART)
// CU19 - Gestionar Notificaciones (Web y Móvil - Con Persistencia Local y Servidor)
// Ubicación: mobile-app/lib/controllers/notification_controller.dart
// ==============================================================================

import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../services/local_storage_service.dart';

class NotificacionItem {
  final int id;
  final String titulo;
  final String mensaje;
  final String tipo;
  final bool leido;
  final String? enlace;
  final String fecha;
  final int tenantId;

  NotificacionItem({
    required this.id,
    required this.titulo,
    required this.mensaje,
    required this.tipo,
    required this.leido,
    this.enlace,
    required this.fecha,
    this.tenantId = 1,
  });

  factory NotificacionItem.fromJson(Map<String, dynamic> json) {
    return NotificacionItem(
      id: json['id'] is int ? json['id'] : int.tryParse(json['id']?.toString() ?? '0') ?? 0,
      titulo: json['titulo'] ?? '',
      mensaje: json['mensaje'] ?? '',
      tipo: json['tipo'] ?? 'INFO',
      leido: json['leido'] ?? false,
      enlace: json['enlace'],
      fecha: json['fecha'] ?? '',
      tenantId: json['tenant_id'] is int ? json['tenant_id'] : int.tryParse(json['tenant_id']?.toString() ?? '1') ?? 1,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'titulo': titulo,
      'mensaje': mensaje,
      'tipo': tipo,
      'leido': leido,
      'enlace': enlace,
      'fecha': fecha,
      'tenant_id': tenantId,
    };
  }
}

class NotificationController extends ChangeNotifier {
  static String get _host => ApiConfig.baseUrl;

  List<NotificacionItem> _notificaciones = [];
  List<NotificacionItem> _locales = [];
  int _tenantActivo = 1;
  bool _cargando = false;
  String? _error;

  List<NotificacionItem> get notificaciones => _notificaciones;
  bool get cargando => _cargando;
  String? get error => _error;

  int get noLeidasCount => _notificaciones.where((n) => !n.leido).length;

  String _storageKey(int tenantId) => 'notificaciones_locales_tenant_$tenantId';

  Future<void> _cargarLocales(int tenantId) async {
    try {
      final raw = await LocalStorageService.readJson(_storageKey(tenantId));
      if (raw is List) {
        _locales = raw
            .map((e) => NotificacionItem.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList();
      } else {
        _locales = [];
      }
    } catch (e) {
      debugPrint('Error cargando notificaciones locales: $e');
      _locales = [];
    }
  }

  Future<void> _guardarLocales(int tenantId) async {
    try {
      await LocalStorageService.saveJson(
        _storageKey(tenantId),
        _locales.map((n) => n.toJson()).toList(),
      );
    } catch (e) {
      debugPrint('Error guardando notificaciones locales: $e');
    }
  }

  String _extraerCodigoOrden(String texto) {
    final match = RegExp(r'(ORD-[A-Z0-9\-]+|RES-[A-Z0-9\-]+|VTA-[A-Z0-9\-]+)').firstMatch(texto);
    return match?.group(0) ?? '';
  }

  void _combinarListas(List<NotificacionItem> remotas) {
    final Map<String, NotificacionItem> mapaUnico = {};

    // 1. Primero insertamos las locales para preservar el estado inmediato
    for (final loc in _locales) {
      final code = _extraerCodigoOrden('${loc.titulo} ${loc.mensaje}');
      final key = code.isNotEmpty ? 'CODE_$code' : 'TITLE_${loc.titulo}';
      mapaUnico[key] = loc;
    }

    // 2. Fusionamos las remotas del servidor sin sobrescribir ni borrar las locales
    for (final rem in remotas) {
      final code = _extraerCodigoOrden('${rem.titulo} ${rem.mensaje}');
      final key = code.isNotEmpty ? 'CODE_$code' : 'TITLE_${rem.titulo}_${rem.id}';
      if (mapaUnico.containsKey(key)) {
        final existente = mapaUnico[key]!;
        mapaUnico[key] = NotificacionItem(
          id: rem.id,
          titulo: existente.titulo.isNotEmpty ? existente.titulo : rem.titulo,
          mensaje: existente.mensaje.isNotEmpty ? existente.mensaje : rem.mensaje,
          tipo: existente.tipo != 'INFO' ? existente.tipo : rem.tipo,
          leido: existente.leido || rem.leido,
          enlace: existente.enlace ?? rem.enlace,
          fecha: rem.fecha.isNotEmpty ? rem.fecha : existente.fecha,
          tenantId: _tenantActivo,
        );
      } else {
        mapaUnico[key] = rem;
      }
    }

    _notificaciones = mapaUnico.values.toList();
  }

  Future<void> fetchNotificaciones(String? token, {int? tenantId}) async {
    if (tenantId != null) {
      _tenantActivo = tenantId;
    }
    _cargando = true;
    _error = null;
    notifyListeners();

    await _cargarLocales(_tenantActivo);

    try {
      final headers = <String, String>{
        'X-Tenant-ID': '$_tenantActivo',
      };
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }

      final res = await http
          .get(
            Uri.parse('$_host/notificaciones?tenant_id=$_tenantActivo'),
            headers: headers,
          )
          .timeout(const Duration(seconds: 6));

      if (res.statusCode == 200) {
        final List data = json.decode(utf8.decode(res.bodyBytes));
        final remotas = data.map((n) => NotificacionItem.fromJson(n)).toList();
        _combinarListas(remotas);
        await _guardarLocales(_tenantActivo);
      } else {
        _combinarListas([]);
      }
    } catch (e) {
      debugPrint('Usando notificaciones locales por modo offline o red: $e');
      _combinarListas([]);
    } finally {
      _cargando = false;
      notifyListeners();
    }
  }

  Future<void> marcarLeida(int id, String? token, {int? tenantId}) async {
    final tId = tenantId ?? _tenantActivo;
    try {
      final index = _notificaciones.indexWhere((n) => n.id == id);
      if (index != -1) {
        final old = _notificaciones[index];
        _notificaciones[index] = NotificacionItem(
          id: old.id,
          titulo: old.titulo,
          mensaje: old.mensaje,
          tipo: old.tipo,
          leido: true,
          enlace: old.enlace,
          fecha: old.fecha,
          tenantId: old.tenantId,
        );
      }
      final locIndex = _locales.indexWhere((n) => n.id == id);
      if (locIndex != -1) {
        final oldLoc = _locales[locIndex];
        _locales[locIndex] = NotificacionItem(
          id: oldLoc.id,
          titulo: oldLoc.titulo,
          mensaje: oldLoc.mensaje,
          tipo: oldLoc.tipo,
          leido: true,
          enlace: oldLoc.enlace,
          fecha: oldLoc.fecha,
          tenantId: oldLoc.tenantId,
        );
        await _guardarLocales(tId);
      }
      notifyListeners();

      final headers = <String, String>{
        'X-Tenant-ID': '$tId',
      };
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
      await http.patch(
        Uri.parse('$_host/notificaciones/$id/leer'),
        headers: headers,
      );
    } catch (e) {
      debugPrint('Error marcar leida: $e');
    }
  }

  Future<void> marcarTodasLeidas(String? token, {int? tenantId}) async {
    final tId = tenantId ?? _tenantActivo;
    try {
      _notificaciones = _notificaciones
          .map((n) => NotificacionItem(
                id: n.id,
                titulo: n.titulo,
                mensaje: n.mensaje,
                tipo: n.tipo,
                leido: true,
                enlace: n.enlace,
                fecha: n.fecha,
                tenantId: n.tenantId,
              ))
          .toList();

      _locales = _locales
          .map((n) => NotificacionItem(
                id: n.id,
                titulo: n.titulo,
                mensaje: n.mensaje,
                tipo: n.tipo,
                leido: true,
                enlace: n.enlace,
                fecha: n.fecha,
                tenantId: n.tenantId,
              ))
          .toList();

      await _guardarLocales(tId);
      notifyListeners();

      final headers = <String, String>{
        'X-Tenant-ID': '$tId',
      };
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
      await http.post(
        Uri.parse('$_host/notificaciones/marcar-todas-leidas'),
        headers: headers,
      );
    } catch (e) {
      debugPrint('Error marcar todas: $e');
    }
  }

  /// Añade una notificación inmediata en el móvil y la persiste localmente por empresa
  Future<void> agregarNotificacion({
    required String titulo,
    required String mensaje,
    String tipo = 'COMPRA_EXITOSA',
    String? enlace = '/mis-pedidos',
    int? tenantId,
  }) async {
    final tId = tenantId ?? _tenantActivo;
    _tenantActivo = tId;

    await _cargarLocales(tId);

    final ahora = DateTime.now();
    final fechaFormateada =
        '${ahora.day.toString().padLeft(2, '0')}/${ahora.month.toString().padLeft(2, '0')}/${ahora.year} ${ahora.hour.toString().padLeft(2, '0')}:${ahora.minute.toString().padLeft(2, '0')}';

    final nueva = NotificacionItem(
      id: ahora.millisecondsSinceEpoch,
      titulo: titulo,
      mensaje: mensaje,
      tipo: tipo,
      leido: false,
      enlace: enlace,
      fecha: fechaFormateada,
      tenantId: tId,
    );

    final code = _extraerCodigoOrden('$titulo $mensaje');
    if (code.isNotEmpty) {
      _locales.removeWhere((n) => _extraerCodigoOrden('${n.titulo} ${n.mensaje}') == code);
      _notificaciones.removeWhere((n) => _extraerCodigoOrden('${n.titulo} ${n.mensaje}') == code);
    }

    _locales.insert(0, nueva);
    _notificaciones.insert(0, nueva);
    await _guardarLocales(tId);
    notifyListeners();
  }
}
