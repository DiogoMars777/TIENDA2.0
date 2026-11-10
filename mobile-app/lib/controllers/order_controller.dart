// ==============================================================================
// CAPA CONTROLADOR (MVC - CONTROLLER EN FLUTTER / DART)
// Controlador para Historial de Pedidos / Compras Digitales (CU15)
// ==============================================================================

import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/order_model.dart';
import '../config/api_config.dart';
import '../services/local_storage_service.dart';

class OrderController extends ChangeNotifier {
  static String get baseUrl => '${ApiConfig.baseUrl}/ordenes';

  List<OrderModel> _ordenes = [];
  List<Map<String, dynamic>> _ordenesLocales = [];
  int _tenantActivo = 1;
  bool _cargando = false;
  String? _error;

  List<OrderModel> get ordenes => _ordenes;
  bool get cargando => _cargando;
  String? get error => _error;

  String _storageKey(int tenantId) => 'ordenes_locales_tenant_$tenantId';

  Future<void> _cargarLocales(int tenantId) async {
    try {
      final raw = await LocalStorageService.readJson(_storageKey(tenantId));
      if (raw is List) {
        _ordenesLocales = raw.map((e) => Map<String, dynamic>.from(e as Map)).toList();
      } else {
        _ordenesLocales = [];
      }
    } catch (_) {
      _ordenesLocales = [];
    }
  }

  Future<void> registrarOrdenLocal(Map<String, dynamic> ordenJson, {int? tenantId}) async {
    final tId = tenantId ?? _tenantActivo;
    _tenantActivo = tId;
    await _cargarLocales(tId);
    final codigo = ordenJson['codigoventa']?.toString() ?? '';
    if (codigo.isNotEmpty) {
      _ordenesLocales.removeWhere((o) => o['codigoventa']?.toString() == codigo);
    }
    _ordenesLocales.insert(0, ordenJson);
    await LocalStorageService.saveJson(_storageKey(tId), _ordenesLocales);
    _combinarOrdenes([]);
    notifyListeners();
  }

  void _combinarOrdenes(List<OrderModel> remotas) {
    final Map<String, OrderModel> mapa = {};
    for (final locJson in _ordenesLocales) {
      final ord = OrderModel.fromJson(locJson);
      mapa[ord.codigoVenta] = ord;
    }
    for (final rem in remotas) {
      mapa[rem.codigoVenta] = rem;
    }
    _ordenes = mapa.values.toList();
  }

  Future<void> fetchMisOrdenes(String? token, {int? tenantId}) async {
    if (tenantId != null) {
      _tenantActivo = tenantId;
    }
    _cargando = true;
    _error = null;
    notifyListeners();

    await _cargarLocales(_tenantActivo);

    try {
      final headers = <String, String>{
        'Content-Type': 'application/json',
        'X-Tenant-ID': '$_tenantActivo',
      };
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }

      final response = await http
          .get(
            Uri.parse('$baseUrl/me'),
            headers: headers,
          )
          .timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(utf8.decode(response.bodyBytes));
        final remotas = data.map((json) => OrderModel.fromJson(json)).toList();
        _combinarOrdenes(remotas);
      } else {
        _combinarOrdenes([]);
      }
    } catch (e) {
      debugPrint('Usando historial local de órdenes: $e');
      _combinarOrdenes([]);
    } finally {
      _cargando = false;
      notifyListeners();
    }
  }
}
