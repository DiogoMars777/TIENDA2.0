// ==============================================================================
// CAPA CONTROLADOR (MVC - CONTROLLER EN FLUTTER / DART)
// Módulo: CU10 - Gestionar Reservas de Prendas (Con Soporte Offline-First y Sync)
// Ubicación: mobile-app/lib/controllers/reservation_controller.dart
// ==============================================================================

import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/reservation_model.dart';
import '../config/api_config.dart';
import '../services/local_storage_service.dart';

class ReservationController extends ChangeNotifier {
  static String get _reservasUrl => '${ApiConfig.baseUrl}/reservas';

  List<ReservaModel> _reservas = [];
  bool _cargando = false;
  bool _sincronizando = false;
  String? _error;
  String? _alertaCancelacionStock;
  int _tenantActivoId = 1;
  Timer? _autoSyncTimer;

  List<ReservaModel> get reservas => _reservas;
  bool get cargando => _cargando;
  bool get sincronizando => _sincronizando;
  String? get error => _error;
  String? get alertaCancelacionStock => _alertaCancelacionStock;

  void limpiarAlertaStock() {
    _alertaCancelacionStock = null;
    notifyListeners();
  }

  /// Solo cuenta las que están estrictamente pendientes en la cola local sin internet
  int get pendientesOfflineCount => _reservas.where((r) => r.esOffline).length;

  ReservationController() {
    _iniciarMonitorSincronizacion();
  }

  void _iniciarMonitorSincronizacion() {
    _autoSyncTimer?.cancel();
    _autoSyncTimer = Timer.periodic(const Duration(seconds: 8), (_) {
      if (pendientesOfflineCount > 0 && !_sincronizando) {
        sincronizarReservasOffline(tenantId: _tenantActivoId, silencioso: true);
      }
    });
  }

  @override
  void dispose() {
    _autoSyncTimer?.cancel();
    super.dispose();
  }

  String _generarCodigoOffline() {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    final rnd = Random();
    final sufijo = List.generate(6, (_) => chars[rnd.nextInt(chars.length)]).join();
    return 'RES-OFF-$sufijo';
  }

  // ============================================================================
  // PERSISTENCIA LOCAL (OFFLINE FIRST & HISTORIAL PERMANENTE DEL DISPOSITIVO)
  // ============================================================================

  /// Cola de reservas offline creadas en este móvil que están esperando sincronización con el servidor
  Future<List<ReservaModel>> _leerReservasOffline(int tenantId) async {
    try {
      final raw = await LocalStorageService.readJson('reservas_offline_tenant_$tenantId');
      if (raw is List) {
        return raw.map((j) => ReservaModel.fromJson(Map<String, dynamic>.from(j))).toList();
      }
    } catch (e) {
      debugPrint('Error leyendo cola de reservas offline: $e');
    }
    return [];
  }

  Future<void> _guardarReservasOffline(int tenantId, List<ReservaModel> lista) async {
    await LocalStorageService.saveJson(
      'reservas_offline_tenant_$tenantId',
      lista.map((r) => r.toJson()).toList(),
    );
  }

  /// Historial persistente local de todas las reservas originadas o consultadas en este móvil.
  /// Garantiza que ninguna reserva (cancelada, entregada o pendiente) desaparezca jamás del dispositivo.
  Future<List<ReservaModel>> _leerHistorialDispositivo(int tenantId) async {
    try {
      final raw = await LocalStorageService.readJson('reservas_historial_dispositivo_$tenantId');
      if (raw is List && raw.isNotEmpty) {
        return raw.map((j) => ReservaModel.fromJson(Map<String, dynamic>.from(j))).toList();
      }

      // Migración o auto-población inicial con lo que ya existía en caché y offline
      final offline = await _leerReservasOffline(tenantId);
      final cache = await _leerCacheOnline(tenantId);
      final unificadas = <String, ReservaModel>{};
      for (final r in [...offline, ...cache]) {
        unificadas[r.codigoReserva] = r;
      }
      final inicial = unificadas.values.toList();
      if (inicial.isNotEmpty) {
        await _guardarHistorialDispositivo(tenantId, inicial);
      }
      return inicial;
    } catch (e) {
      debugPrint('Error leyendo historial de reservas del dispositivo: $e');
      return [];
    }
  }

  Future<void> _guardarHistorialDispositivo(int tenantId, List<ReservaModel> lista) async {
    try {
      await LocalStorageService.saveJson(
        'reservas_historial_dispositivo_$tenantId',
        lista.map((r) => r.toJson()).toList(),
      );
    } catch (e) {
      debugPrint('Error guardando historial de reservas del dispositivo: $e');
    }
  }

  Future<void> _guardarEnHistorialDispositivo(int tenantId, ReservaModel res) async {
    try {
      final hist = await _leerHistorialDispositivo(tenantId);
      final idx = hist.indexWhere((r) => r.codigoReserva == res.codigoReserva);
      if (idx != -1) {
        hist[idx] = res;
      } else {
        hist.insert(0, res);
      }
      await _guardarHistorialDispositivo(tenantId, hist);
    } catch (e) {
      debugPrint('Error guardando en historial de dispositivo: $e');
    }
  }

  Future<List<ReservaModel>> _leerCacheOnline(int tenantId) async {
    try {
      final raw = await LocalStorageService.readJson('reservas_cache_tenant_$tenantId');
      if (raw is List) {
        return raw.map((j) => ReservaModel.fromJson(Map<String, dynamic>.from(j))).toList();
      }
    } catch (_) {}
    return [];
  }

  Future<void> _guardarCacheOnline(int tenantId) async {
    try {
      final onlineOnly = _reservas.where((r) => !r.esOffline).toList();
      await LocalStorageService.saveJson(
        'reservas_cache_tenant_$tenantId',
        onlineOnly.map((r) => r.toJson()).toList(),
      );
    } catch (_) {}
  }

  /// Inserta una notificación en la base local del móvil para alertar al usuario (CU19)
  Future<void> _agregarNotificacionLocal({
    required int tenantId,
    required String titulo,
    required String mensaje,
    required String tipo,
    String? enlace,
  }) async {
    try {
      final raw = await LocalStorageService.readJson('notificaciones_locales_tenant_$tenantId');
      final List<Map<String, dynamic>> notifs = (raw is List)
          ? raw.map((e) => Map<String, dynamic>.from(e as Map)).toList()
          : [];

      final ahora = DateTime.now();
      final fechaFormateada =
          '${ahora.day.toString().padLeft(2, '0')}/${ahora.month.toString().padLeft(2, '0')}/${ahora.year} ${ahora.hour.toString().padLeft(2, '0')}:${ahora.minute.toString().padLeft(2, '0')}';

      final nueva = {
        'id': ahora.millisecondsSinceEpoch,
        'titulo': titulo,
        'mensaje': mensaje,
        'tipo': tipo,
        'leido': false,
        'enlace': enlace ?? '/mis-reservas',
        'fecha': fechaFormateada,
        'tenant_id': tenantId,
      };

      notifs.removeWhere((n) => n['titulo'] == titulo);
      notifs.insert(0, nueva);

      await LocalStorageService.saveJson('notificaciones_locales_tenant_$tenantId', notifs);
    } catch (e) {
      debugPrint('Error guardando notificación local de reserva: $e');
    }
  }

  /// Fusiona inteligentemente:
  /// - Servidor (online)
  /// - Historial permanente del móvil
  /// - Cola pendiente offline (SOLO las que están aquí llevan esOffline = true)
  List<ReservaModel> _combinarReservas({
    required List<ReservaModel> pendientesOffline,
    required List<ReservaModel> historialDispositivo,
    required List<ReservaModel> onlineReservas,
  }) {
    final Map<String, ReservaModel> mapa = {};

    // 1. Añadir reservas del servidor (siempre esOffline: false)
    for (final r in onlineReservas) {
      mapa[r.codigoReserva] = r.copyWith(esOffline: false);
    }

    // 2. Fusionar con el historial permanente del teléfono
    for (final r in historialDispositivo) {
      if (!mapa.containsKey(r.codigoReserva)) {
        mapa[r.codigoReserva] = r.copyWith(esOffline: false);
      } else {
        final server = mapa[r.codigoReserva]!;
        // El servidor manda sobre el estado final (PAGADA, ENTREGADA, CANCELADA)
        mapa[r.codigoReserva] = server.copyWith(esOffline: false);
      }
    }

    // 3. Superponer ÚNICAMENTE las que siguen pendientes en la cola offline sin internet
    for (final r in pendientesOffline) {
      mapa[r.codigoReserva] = r.copyWith(esOffline: true);
    }

    final lista = mapa.values.toList();
    // Ordenar de más reciente a más antigua
    lista.sort((a, b) => b.id.compareTo(a.id));
    return lista;
  }

  // ============================================================================
  // OPERACIONES PRINCIPALES DE RESERVA (CU10 / CU23)
  // ============================================================================

  /// CU10: Convierte el carrito activo en una reserva física (Online o Guardada en Base Local Offline)
  Future<ReservaModel?> crearReserva({
    int? sucursalId,
    String? sucursalNombre,
    String? sucursalDireccion,
    int? tenantId,
    String? empresaNombre,
    String? observaciones,
    String? token,
    bool forzarOffline = false,
    List<Map<String, dynamic>>? items,
  }) async {
    _cargando = true;
    _error = null;
    final targetTenant = tenantId ?? _tenantActivoId;
    _tenantActivoId = targetTenant;
    notifyListeners();

    // 1. Si NO está forzado el modo offline, intentamos crearla en el servidor primero
    if (!forzarOffline) {
      try {
        final headers = <String, String>{
          'Content-Type': 'application/json',
          'X-Tenant-ID': '$targetTenant',
        };
        if (token != null && token.isNotEmpty) {
          headers['Authorization'] = 'Bearer $token';
        }

        final payloadItems = (items ?? []).map((it) => {
          'producto_id': it['producto_id'],
          'variante_id': it['variante_id'],
          'cantidad': it['cantidad'] ?? 1,
        }).toList();

        final response = await http.post(
          Uri.parse(_reservasUrl),
          headers: headers,
          body: json.encode({
            if (sucursalId != null) 'sucursal_id': sucursalId,
            if (observaciones != null) 'observaciones': observaciones,
            if (payloadItems.isNotEmpty) 'items': payloadItems,
          }),
        ).timeout(const Duration(seconds: 6));

        if (response.statusCode == 201 || response.statusCode == 200) {
          final data = json.decode(utf8.decode(response.bodyBytes));
          final nuevaReserva = ReservaModel.fromJson(data).copyWith(esOffline: false);
          await _guardarEnHistorialDispositivo(targetTenant, nuevaReserva);
          _reservas.insert(0, nuevaReserva);
          await _guardarCacheOnline(targetTenant);
          _cargando = false;
          notifyListeners();
          return nuevaReserva;
        }
      } catch (e) {
        debugPrint('Sin internet al crear reserva, guardando en base local móvil: $e');
      }
    }

    // 2. MODO OFFLINE: Guardar la reserva en la base de datos local del móvil
    try {
      final codigoOff = _generarCodigoOffline();
      final ahora = DateTime.now().toIso8601String();
      final detallesOffline = <ReservaDetalleItem>[];
      int totalUds = 0;
      double totalBs = 0.0;

      for (final it in (items ?? [])) {
        final cant = (it['cantidad'] is num) ? (it['cantidad'] as num).toInt() : 1;
        final precio = (it['precio_unitario'] is num)
            ? (it['precio_unitario'] as num).toDouble()
            : 100.0;
        final sub = precio * cant;
        totalUds += cant;
        totalBs += sub;

        detallesOffline.add(
          ReservaDetalleItem(
            varianteId: (it['variante_id'] is num) ? (it['variante_id'] as num).toInt() : 0,
            productoId: (it['producto_id'] is num) ? (it['producto_id'] as num).toInt() : null,
            productoNombre: it['producto_nombre']?.toString() ?? 'Prenda Reservada',
            talla: it['talla']?.toString() ?? 'M',
            color: it['color']?.toString(),
            imagenUrl: it['imagen_url']?.toString(),
            precioUnitario: precio,
            cantidad: cant,
            subtotal: sub,
          ),
        );
      }

      final reservaLocal = ReservaModel(
        id: DateTime.now().millisecondsSinceEpoch,
        codigoReserva: codigoOff,
        fechaReserva: ahora,
        estado: 'PENDIENTE',
        observaciones: observaciones ?? '[RESERVA CREADA SIN INTERNET EN APP MÓVIL]',
        sucursalId: sucursalId,
        sucursalNombre: sucursalNombre ?? 'Sucursal Principal',
        sucursalDireccion: sucursalDireccion,
        tenantId: targetTenant,
        empresaNombre: empresaNombre,
        esOffline: true,
        detalles: detallesOffline,
        totalItems: totalUds,
        totalEstimado: totalBs,
      );

      // Guardar en cola pendiente offline
      final pendientes = await _leerReservasOffline(targetTenant);
      pendientes.insert(0, reservaLocal);
      await _guardarReservasOffline(targetTenant, pendientes);

      // Guardar en historial permanente del dispositivo
      await _guardarEnHistorialDispositivo(targetTenant, reservaLocal);

      _reservas.insert(0, reservaLocal);
      _error = null;
      _cargando = false;
      notifyListeners();
      return reservaLocal;
    } catch (e) {
      _error = 'No se pudo guardar la reserva local: $e';
      _cargando = false;
      notifyListeners();
      return null;
    }
  }

  /// Alias de conveniencia para invocar desde la vista del carrito
  Future<ReservaModel?> crearReservaDesdeCarrito({
    int? sucursalId,
    String? sucursalNombre,
    String? sucursalDireccion,
    int? tenantId,
    String? empresaNombre,
    String? observaciones,
    String? token,
    bool forzarOffline = false,
    List<Map<String, dynamic>>? items,
  }) async {
    return crearReserva(
      sucursalId: sucursalId,
      sucursalNombre: sucursalNombre,
      sucursalDireccion: sucursalDireccion,
      tenantId: tenantId,
      empresaNombre: empresaNombre,
      observaciones: observaciones,
      token: token,
      forzarOffline: forzarOffline,
      items: items,
    );
  }

  /// CU23: Sincroniza automáticamente las reservas creadas sin internet cuando vuelve la conexión
  Future<int> sincronizarReservasOffline({
    int? tenantId,
    String? token,
    bool silencioso = false,
  }) async {
    final targetTenant = tenantId ?? _tenantActivoId;
    final pendientes = await _leerReservasOffline(targetTenant);
    if (pendientes.isEmpty) return 0;

    _sincronizando = true;
    if (!silencioso) {
      notifyListeners();
    }

    int sincronizadas = 0;
    final restantes = <ReservaModel>[];
    final historial = await _leerHistorialDispositivo(targetTenant);

    for (final resOff in pendientes) {
      try {
        final headers = <String, String>{
          'Content-Type': 'application/json',
          'X-Tenant-ID': '${resOff.tenantId ?? targetTenant}',
        };
        if (token != null && token.isNotEmpty) {
          headers['Authorization'] = 'Bearer $token';
        }

        final payloadItems = resOff.detalles.map((d) => {
          if (d.productoId != null) 'producto_id': d.productoId,
          if (d.varianteId > 0) 'variante_id': d.varianteId,
          'cantidad': d.cantidad,
        }).toList();

        final resp = await http.post(
          Uri.parse(_reservasUrl),
          headers: headers,
          body: json.encode({
            if (resOff.sucursalId != null) 'sucursal_id': resOff.sucursalId,
            'codigo_reserva': resOff.codigoReserva,
            'es_offline': true,
            'fecha_reserva': resOff.fechaReserva,
            'observaciones': resOff.observaciones ?? '[SINCRONIZADA DESDE MÓVIL OFFLINE ${resOff.codigoReserva}]',
            'items': payloadItems,
          }),
        ).timeout(const Duration(seconds: 7));

        if (resp.statusCode == 201 || resp.statusCode == 200) {
          sincronizadas++;
          final Map<String, dynamic> data = json.decode(utf8.decode(resp.bodyBytes));
          final bool canceladaSinStock = (data['cancelada_sin_stock'] == true) || (data['estado'] == 'CANCELADA');
          final String nuevoEstado = canceladaSinStock ? 'CANCELADA' : (data['estado'] ?? 'PENDIENTE');
          final int nuevoId = (data['id'] is num) ? (data['id'] as num).toInt() : resOff.id;
          final String nuevoObs = data['observaciones'] ??
              (canceladaSinStock
                  ? 'CANCELADA AUTOMÁTICAMENTE: Stock agotado al sincronizar. La última unidad ya fue adquirida por otro cliente.'
                  : resOff.observaciones);

          // Actualizar en el historial del móvil con estado sincronizado y esOffline en false
          final syncedReserva = resOff.copyWith(
            id: nuevoId,
            esOffline: false,
            estado: nuevoEstado,
            observaciones: nuevoObs,
          );

          final idxHist = historial.indexWhere((r) => r.codigoReserva == resOff.codigoReserva);
          if (idxHist != -1) {
            historial[idxHist] = syncedReserva;
          } else {
            historial.insert(0, syncedReserva);
          }

          if (canceladaSinStock) {
            _alertaCancelacionStock = data['mensaje'] ??
                'Reserva ${resOff.codigoReserva} cancelada: Stock agotado. La última unidad ya fue adquirida por otro cliente.';
            _error = _alertaCancelacionStock;
            await _agregarNotificacionLocal(
              tenantId: resOff.tenantId ?? targetTenant,
              titulo: '❌ Reserva #${resOff.codigoReserva} Cancelada por Stock',
              mensaje: 'Tu reserva #${resOff.codigoReserva} fue cancelada automáticamente porque ya no hay unidades disponibles en inventario.',
              tipo: 'CANCELADA',
            );
          } else {
            await _agregarNotificacionLocal(
              tenantId: resOff.tenantId ?? targetTenant,
              titulo: '✅ Reserva Sincronizada #${resOff.codigoReserva}',
              mensaje: 'Tu reserva #${resOff.codigoReserva} fue confirmada en tienda física con stock apartado. Tienes 48 hrs para recogerla.',
              tipo: 'RESERVA_SINCRONIZADA',
            );
          }
          // Éxito: NO se agrega a 'restantes', por lo que sale de la cola pendiente offline
        } else {
          // Comprobar si el servidor rechazó por stock en cero
          bool esFaltaStock = false;
          String errorMsg = '';
          try {
            final Map<String, dynamic> errData = json.decode(utf8.decode(resp.bodyBytes));
            final String detail = errData['detail']?.toString() ?? '';
            if (detail.toLowerCase().contains('stock') ||
                detail.toLowerCase().contains('insuficiente') ||
                detail.toLowerCase().contains('agotado')) {
              esFaltaStock = true;
              errorMsg = detail;
            }
          } catch (_) {}

          if (esFaltaStock) {
            _alertaCancelacionStock = 'Reserva ${resOff.codigoReserva} cancelada: $errorMsg';
            _error = _alertaCancelacionStock;
            final cancelledReserva = resOff.copyWith(
              esOffline: false,
              estado: 'CANCELADA',
              observaciones: 'CANCELADA AUTOMÁTICAMENTE: $errorMsg',
            );
            final idxHist = historial.indexWhere((r) => r.codigoReserva == resOff.codigoReserva);
            if (idxHist != -1) {
              historial[idxHist] = cancelledReserva;
            } else {
              historial.insert(0, cancelledReserva);
            }
            await _agregarNotificacionLocal(
              tenantId: resOff.tenantId ?? targetTenant,
              titulo: '❌ Reserva #${resOff.codigoReserva} Cancelada por Stock',
              mensaje: 'Tu reserva #${resOff.codigoReserva} fue cancelada por falta de stock: $errorMsg',
              tipo: 'CANCELADA',
            );
            // Stock agotado: NO volver a meter a cola de reintentos
          } else {
            // Error de conexión o indisponibilidad temporal
            restantes.add(resOff);
          }
        }
      } catch (e) {
        // Error de red temporal al conectar
        restantes.add(resOff);
      }
    }

    await _guardarReservasOffline(targetTenant, restantes);
    await _guardarHistorialDispositivo(targetTenant, historial);
    _sincronizando = false;

    await cargarMisReservas(token: token, tenantId: targetTenant);
    return sincronizadas;
  }

  /// CU10: Consulta el listado de reservas del usuario (combinando Online + Historial Local Móvil)
  Future<void> cargarMisReservas({String? token, int? tenantId, bool modoOfflineSimulado = false}) async {
    final targetTenant = tenantId ?? _tenantActivoId;
    _tenantActivoId = targetTenant;
    _cargando = true;
    _error = null;

    // 1. Cargar historial persistente del teléfono y cola pendiente offline
    final pendientesOffline = await _leerReservasOffline(targetTenant);
    final historialDispositivo = await _leerHistorialDispositivo(targetTenant);

    // Pintar de inmediato en pantalla sin parpadeos
    _reservas = _combinarReservas(
      pendientesOffline: pendientesOffline,
      historialDispositivo: historialDispositivo,
      onlineReservas: [],
    );
    notifyListeners();

    if (modoOfflineSimulado) {
      _cargando = false;
      notifyListeners();
      return;
    }

    try {
      // 2. Si hay reservas pendientes en cola offline y tenemos conexión, sincronizarlas de inmediato
      if (pendientesOffline.isNotEmpty) {
        await sincronizarReservasOffline(tenantId: targetTenant, token: token, silencioso: true);
        return; // sincronizarReservasOffline ya invoca cargarMisReservas al culminar
      }

      // 3. Consultar las reservas reales del backend omnicanal (por cliente y por códigos locales del móvil)
      final codigosHistorial = (await _leerHistorialDispositivo(targetTenant))
          .map((r) => r.codigoReserva)
          .where((c) => c.isNotEmpty)
          .toSet()
          .toList();

      final headers = <String, String>{
        'X-Tenant-ID': '$targetTenant',
      };
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }

      String url = '$_reservasUrl/mis-reservas';
      if (codigosHistorial.isNotEmpty) {
        url += '?codigos=${Uri.encodeComponent(codigosHistorial.join(','))}';
      }

      final response = await http
          .get(Uri.parse(url), headers: headers)
          .timeout(const Duration(seconds: 7));

      if (response.statusCode == 200) {
        final List data = json.decode(utf8.decode(response.bodyBytes));
        final onlineReservas = data
            .map((j) => ReservaModel.fromJson(Map<String, dynamic>.from(j)).copyWith(esOffline: false))
            .toList();

        // Actualizar el historial persistente del dispositivo con los estados frescos del servidor
        final updatedHistorial = await _leerHistorialDispositivo(targetTenant);
        for (int i = 0; i < updatedHistorial.length; i++) {
          final matchServer = onlineReservas.firstWhere(
            (s) => s.codigoReserva == updatedHistorial[i].codigoReserva,
            orElse: () => updatedHistorial[i],
          );
          if (matchServer.id != updatedHistorial[i].id ||
              matchServer.estado != updatedHistorial[i].estado ||
              (matchServer.observaciones != null && matchServer.observaciones != updatedHistorial[i].observaciones)) {
            updatedHistorial[i] = matchServer.copyWith(esOffline: false);
          }
        }
        await _guardarHistorialDispositivo(targetTenant, updatedHistorial);
        await _guardarCacheOnline(targetTenant);

        final remainingPending = await _leerReservasOffline(targetTenant);
        _reservas = _combinarReservas(
          pendientesOffline: remainingPending,
          historialDispositivo: updatedHistorial,
          onlineReservas: onlineReservas,
        );
        _error = null;
      }
    } catch (e) {
      debugPrint('Mostrando reservas desde base local del teléfono: $e');
      _error = null;
    } finally {
      _cargando = false;
      notifyListeners();
    }
  }

  /// CU10: Cancela una reserva pendiente (Online o Local Offline)
  Future<bool> cancelarReserva(int id, {String? codigoReserva, String? motivo, String? token, int? tenantId}) async {
    final targetTenant = tenantId ?? _tenantActivoId;

    // 1. Si estaba en la cola de pendientes offline, removerla
    final offList = await _leerReservasOffline(targetTenant);
    final idxOff = offList.indexWhere((r) => r.id == id || (codigoReserva != null && r.codigoReserva == codigoReserva));
    if (idxOff != -1) {
      offList.removeAt(idxOff);
      await _guardarReservasOffline(targetTenant, offList);
    }

    // 2. En el historial permanente del teléfono, marcarla como CANCELADA (no borrarla para que quede constancia)
    final hist = await _leerHistorialDispositivo(targetTenant);
    final idxHist = hist.indexWhere((r) => r.id == id || (codigoReserva != null && r.codigoReserva == codigoReserva));
    if (idxHist != -1) {
      hist[idxHist] = hist[idxHist].copyWith(
        estado: 'CANCELADA',
        observaciones: motivo ?? 'Cancelado desde app móvil por el usuario',
        esOffline: false,
      );
      await _guardarHistorialDispositivo(targetTenant, hist);
    }

    // 3. Notificar al servidor si hay conexión
    try {
      final headers = <String, String>{
        'Content-Type': 'application/json',
        'X-Tenant-ID': '$targetTenant',
      };
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
      await http.patch(
        Uri.parse('$_reservasUrl/$id/cancelar'),
        headers: headers,
        body: json.encode({'motivo': motivo ?? 'Cancelado desde app móvil'}),
      ).timeout(const Duration(seconds: 5));
    } catch (e) {
      debugPrint('Cancelación enviada al servidor o diferida: $e');
    }

    await cargarMisReservas(token: token, tenantId: targetTenant);
    return true;
  }

  /// CU11: Atender reserva en sucursal (ENTREGAR o CANCELAR)
  Future<bool> atenderReserva(int id, String accion, {String? notas}) async {
    try {
      final response = await http.post(
        Uri.parse('$_reservasUrl/$id/atender'),
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': '$_tenantActivoId',
        },
        body: json.encode({
          'accion': accion,
          if (notas != null) 'observaciones': notas,
        }),
      );
      if (response.statusCode == 200) {
        await cargarMisReservas(tenantId: _tenantActivoId);
        return true;
      }
      return false;
    } catch (e) {
      debugPrint('Error al atender reserva: $e');
      return false;
    }
  }

  /// CU10 / CU16: Pagar reserva desde el teléfono móvil
  Future<bool> pagarReserva(int id, {required String metodoPago, String? referencia, String? token}) async {
    _cargando = true;
    _error = null;
    notifyListeners();

    try {
      final headers = <String, String>{
        'Content-Type': 'application/json',
        'X-Tenant-ID': '$_tenantActivoId',
      };
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }

      final response = await http.post(
        Uri.parse('$_reservasUrl/$id/pagar'),
        headers: headers,
        body: json.encode({
          'metodo_pago': metodoPago,
          if (referencia != null) 'referencia': referencia,
          'origen': 'MOVIL',
        }),
      );

      if (response.statusCode == 200) {
        await cargarMisReservas(token: token, tenantId: _tenantActivoId);
        return true;
      } else {
        final err = json.decode(utf8.decode(response.bodyBytes));
        _error = err['detail'] ?? 'Error al procesar el pago de la reserva';
        return false;
      }
    } catch (e) {
      _error = 'Error de conexión: $e';
      return false;
    } finally {
      _cargando = false;
      notifyListeners();
    }
  }
}
