// ==============================================================================
// SERVICIO DE DETECCIÓN ACTIVA DE RED E INTERNET / WI-FI
// Módulo: Conectividad Inteligente para Sincronización Automática Offline-First
// Ubicación: mobile-app/lib/services/network_connectivity_service.dart
// ==============================================================================

import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';

class NetworkConnectivityService {
  /// Permite forzar el modo offline de forma simulada en la UI
  static bool modoOfflineForzado = false;

  static bool _ultimoEstadoOnline = false;
  static final StreamController<bool> _streamController = StreamController<bool>.broadcast();

  /// Stream público para escuchar cambios en tiempo real de la conexión
  static Stream<bool> get onConnectivityChanged => _streamController.stream;

  /// Retorna el último estado conocido de conectividad a internet/Wi-Fi
  static bool get estaOnline => _ultimoEstadoOnline && !modoOfflineForzado;

  /// Verifica activamente si el dispositivo cuenta con acceso real a Internet / Wi-Fi.
  /// No se limita a la interfaz física; verifica que haya resolución DNS o enrutamiento activo.
  static Future<bool> verificarConexion() async {
    // Si el usuario forzó el modo offline en la app, reportar siempre falso
    if (modoOfflineForzado) {
      if (_ultimoEstadoOnline != false) {
        _ultimoEstadoOnline = false;
        _streamController.add(false);
      }
      return false;
    }

    bool online = false;

    // 1. DNS Lookup ultrarrápido a google.com (timeout 1.5s)
    try {
      final res = await InternetAddress.lookup('google.com')
          .timeout(const Duration(milliseconds: 1500));
      if (res.isNotEmpty && res[0].rawAddress.isNotEmpty) {
        online = true;
      }
    } catch (_) {
      // 2. Fallback a servidor DNS público 1.1.1.1 (Cloudflare)
      try {
        final res = await InternetAddress.lookup('one.one.one.one')
            .timeout(const Duration(milliseconds: 1500));
        if (res.isNotEmpty && res[0].rawAddress.isNotEmpty) {
          online = true;
        }
      } catch (_) {
        // 3. Fallback a ping rápido de salud del backend de Tienda
        try {
          final uri = Uri.parse('${ApiConfig.baseUrl}/health');
          final resp = await http.get(uri).timeout(const Duration(milliseconds: 2000));
          if (resp.statusCode >= 200 && resp.statusCode < 500) {
            online = true;
          }
        } catch (_) {
          online = false;
        }
      }
    }

    if (online != _ultimoEstadoOnline) {
      _ultimoEstadoOnline = online;
      _streamController.add(online);
      debugPrint('[NetworkConnectivityService] Cambio de conectividad: online=$online (offlineForzado=$modoOfflineForzado)');
    }

    return online;
  }
}

