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

    // Si NO está forzado el modo offline, intentamos crearla en el servidor primero
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
          final nuevaReserva = ReservaModel.fromJson(data);
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

    // MODO OFFLINE: Guardar la reserva en la base de datos local del móvil
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

      final pendientes = await _leerReservasOffline(targetTenant);
      pendientes.insert(0, reservaLocal);
      await _guardarReservasOffline(targetTenant, pendientes);

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

  Future<List<ReservaModel>> _leerReservasOffline(int tenantId) async {
    final raw = await LocalStorageService.readJson('reservas_offline_tenant_$tenantId');
    if (raw is List) {
      return raw.map((j) => ReservaModel.fromJson(Map<String, dynamic>.from(j))).toList();
    }
    return [];
  }

  Future<void> _guardarReservasOffline(int tenantId, List<ReservaModel> lista) async {
    await LocalStorageService.saveJson(
      'reservas_offline_tenant_$tenantId',
      lista.map((r) => r.toJson()).toList(),
    );
  }

  Future<List<ReservaModel>> _leerCacheOnline(int tenantId) async {
    final raw = await LocalStorageService.readJson('reservas_cache_tenant_$tenantId');
    if (raw is List) {
      return raw.map((j) => ReservaModel.fromJson(Map<String, dynamic>.from(j))).toList();
    }
    return [];
  }

  Future<void> _guardarCacheOnline(int tenantId) async {
    final onlineOnly = _reservas.where((r) => !r.esOffline).toList();
    await LocalStorageService.saveJson(
      'reservas_cache_tenant_$tenantId',
      onlineOnly.map((r) => r.toJson()).toList(),
    );
  }

  /// Sincroniza automáticamente las reservas creadas sin internet cuando vuelve la conexión
  Future<int> sincronizarReservasOffline({
    int? tenantId,
    String? token,
    bool silencioso = false,
  }) async {
    final targetTenant = tenantId ?? _tenantActivoId;
    final pendientes = await _leerReservasOffline(targetTenant);
    if (pendientes.isEmpty) return 0;

    if (!silencioso) {
      _sincronizando = true;
      notifyListeners();
    } else {
      _sincronizando = true;
    }

    int sincronizadas = 0;
    final restantes = <ReservaModel>[];

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
        ).timeout(const Duration(seconds: 6));

        if (resp.statusCode == 201 || resp.statusCode == 200) {
          sincronizadas++;
          try {
            final Map<String, dynamic> data = json.decode(utf8.decode(resp.bodyBytes));
            final bool canceladaSinStock = (data['cancelada_sin_stock'] == true) || (data['estado'] == 'CANCELADA');
            if (canceladaSinStock) {
              _alertaCancelacionStock = data['mensaje'] ??
                  'No hay stock disponible para ${resOff.codigoReserva}. La última unidad ya fue adquirida o reservada previamente por otro cliente.';
              _error = _alertaCancelacionStock;
            }
          } catch (_) {}
        } else {
          try {
            final Map<String, dynamic> errData = json.decode(utf8.decode(resp.bodyBytes));
            final String detail = errData['detail']?.toString() ?? '';
            if (detail.toLowerCase().contains('stock') || detail.toLowerCase().contains('insuficiente')) {
              _alertaCancelacionStock = 'Reserva ${resOff.codigoReserva} cancelada: $detail';
              _error = _alertaCancelacionStock;
              // Stock en 0: no volver a meter a la cola para evitar bucles infinitos
              continue;
            }
          } catch (_) {}
          restantes.add(resOff);
        }
      } catch (_) {
        restantes.add(resOff);
      }
    }

    await _guardarReservasOffline(targetTenant, restantes);
    _sincronizando = false;

    if (sincronizadas > 0) {
      await cargarMisReservas(token: token, tenantId: targetTenant);
    } else {
      notifyListeners();
    }

    return sincronizadas;
  }

  /// CU10: Consulta el listado de reservas del usuario (combinando Online + Base Local Offline)
  Future<void> cargarMisReservas({String? token, int? tenantId, bool modoOfflineSimulado = false}) async {
    final targetTenant = tenantId ?? _tenantActivoId;
    _tenantActivoId = targetTenant;
    _cargando = true;
    _error = null;

    // 1. Cargar primero lo que hay en la base local del teléfono (Offline + Caché)
    final offlineList = await _leerReservasOffline(targetTenant);
    final cachedOnline = await _leerCacheOnline(targetTenant);
    _reservas = [...offlineList, ...cachedOnline];
    notifyListeners();

    if (modoOfflineSimulado) {
      _cargando = false;
      notifyListeners();
      return;
    }

    try {
      // 2. Si hay reservas offline pendientes y ya hay internet, sincronizarlas primero
      if (offlineList.isNotEmpty) {
        await sincronizarReservasOffline(tenantId: targetTenant, token: token, silencioso: true);
      }

      // 3. Consultar las reservas reales del servidor
      final headers = <String, String>{
        'X-Tenant-ID': '$targetTenant',
      };
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
      final response = await http
          .get(Uri.parse('$_reservasUrl/mis-reservas'), headers: headers)
          .timeout(const Duration(seconds: 7));

      if (response.statusCode == 200) {
        final List data = json.decode(utf8.decode(response.bodyBytes));
        final onlineReservas = data
            .map((j) => ReservaModel.fromJson(Map<String, dynamic>.from(j)))
            .toList();
        await LocalStorageService.saveJson(
          'reservas_cache_tenant_$targetTenant',
          onlineReservas.map((r) => r.toJson()).toList(),
        );
        final offRestantes = await _leerReservasOffline(targetTenant);
        _reservas = [...offRestantes, ...onlineReservas];
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

    // Si es una reserva offline local, eliminarla de la base local
    final offList = await _leerReservasOffline(targetTenant);
    final idxOff = offList.indexWhere((r) => r.id == id || (codigoReserva != null && r.codigoReserva == codigoReserva));
    if (idxOff != -1) {
      offList.removeAt(idxOff);
      await _guardarReservasOffline(targetTenant, offList);
      _reservas.removeWhere((r) => r.id == id || (codigoReserva != null && r.codigoReserva == codigoReserva));
      notifyListeners();
      return true;
    }

    try {
      final headers = <String, String>{
        'Content-Type': 'application/json',
        'X-Tenant-ID': '$targetTenant',
      };
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
      final response = await http.patch(
        Uri.parse('$_reservasUrl/$id/cancelar'),
        headers: headers,
        body: json.encode({'motivo': motivo ?? 'Cancelado desde app móvil'}),
      );
      if (response.statusCode == 200) {
        await cargarMisReservas(token: token, tenantId: targetTenant);
        return true;
      }
      return false;
    } catch (e) {
      debugPrint('Error al cancelar reserva: $e');
      return false;
    }
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
