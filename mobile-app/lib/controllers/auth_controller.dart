// ==============================================================================
// CONTROLADOR DE AUTENTICACIÓN (MVC - CONTROLLER)
// Gestión de Estado y Servicios REST para Login, Registro, OTP y Sesión Offline
// ==============================================================================

import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/user_model.dart';
import '../config/api_config.dart';
import '../services/local_storage_service.dart';

class AuthController with ChangeNotifier {
  static String get baseUrl => '${ApiConfig.baseUrl}/auth';

  UserModel? _currentUser;
  bool _isLoading = false;
  String? _errorMessage;
  String? _successMessage;
  String? _lastDemoOtpCode;

  UserModel? get currentUser => _currentUser;
  bool get isLoggedIn => _currentUser != null;
  bool get isAuthenticated => isLoggedIn;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  String? get successMessage => _successMessage;
  String? get lastDemoOtpCode => _lastDemoOtpCode;

  AuthController() {
    _restaurarSesionLocal();
  }

  Future<void> _restaurarSesionLocal() async {
    final saved = await LocalStorageService.readJson('auth_current_user');
    if (saved is Map) {
      _currentUser = UserModel.fromJson(Map<String, dynamic>.from(saved));
      notifyListeners();
    }
  }

  void clearMessages() {
    _errorMessage = null;
    _successMessage = null;
    notifyListeners();
  }

  /// Permite ingresar en modo cliente/invitado para explorar y reservar (incluso sin internet)
  Future<void> loginInvitadoEmpresa({required int tenantId, required String empresaNombre}) async {
    _currentUser = UserModel(
      id: 1,
      nombre: 'Cliente Móvil ($empresaNombre)',
      email: 'cliente_t$tenantId@tienda.bo',
      activo: true,
      rol: 'CLIENTE',
      tenantId: tenantId,
      tenantNombre: empresaNombre,
    );
    await LocalStorageService.saveJson('auth_current_user', _currentUser!.toJson());
    notifyListeners();
  }

  /// Registrar nuevo Cliente desde la App Móvil (Genera código OTP)
  Future<bool> registerUser({
    required String nombre,
    required String apellido,
    required String email,
    required String password,
    required String telefono,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    _successMessage = null;
    _lastDemoOtpCode = null;
    notifyListeners();

    try {
      final uri = Uri.parse('$baseUrl/registro');
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'nombre': nombre,
          'apellido': apellido,
          'email': email,
          'password': password,
          'telefono': telefono,
        }),
      ).timeout(const Duration(seconds: 10));

      final data = json.decode(response.body);

      if (response.statusCode == 201 || response.statusCode == 200) {
        _lastDemoOtpCode = data['codigo_demo'];
        _successMessage = '¡Código de 6 dígitos enviado a tu correo!';
        _isLoading = false;
        notifyListeners();
        return true;
      } else {
        _errorMessage = data['detail'] ?? 'No se pudo completar el registro.';
        _isLoading = false;
        notifyListeners();
        return false;
      }
    } catch (e) {
      _errorMessage = 'Error de conexión con el servidor ($e)';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  /// Verificar Código OTP de 6 dígitos
  Future<bool> verifyOtpCode(String email, String codigo) async {
    _isLoading = true;
    _errorMessage = null;
    _successMessage = null;
    notifyListeners();

    try {
      final uri = Uri.parse('$baseUrl/verificar-codigo');
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'email': email,
          'codigo': codigo,
        }),
      ).timeout(const Duration(seconds: 10));

      final data = json.decode(response.body);

      if (response.statusCode == 200) {
        _currentUser = UserModel.fromJson(data);
        await LocalStorageService.saveJson('auth_current_user', _currentUser!.toJson());
        _successMessage = '¡Cuenta verificada exitosamente! Bienvenido.';
        _isLoading = false;
        notifyListeners();
        return true;
      } else {
        _errorMessage = data['detail'] ?? 'Código de verificación incorrecto o expirado.';
        _isLoading = false;
        notifyListeners();
        return false;
      }
    } catch (e) {
      _errorMessage = 'Error de conexión con el servidor ($e)';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  /// Iniciar Sesión usando la API REST (con respaldo Offline si no hay internet)
  Future<bool> login(String email, String password, {int? selectedTenantId, String? selectedEmpresaNombre}) async {
    _isLoading = true;
    _errorMessage = null;
    _successMessage = null;
    notifyListeners();

    try {
      final uri = Uri.parse('$baseUrl/login');
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: {
          'username': email,
          'password': password,
        },
      ).timeout(const Duration(seconds: 7));

      final data = json.decode(utf8.decode(response.bodyBytes));

      if (response.statusCode == 200) {
        _currentUser = UserModel.fromJson(data);
        await LocalStorageService.saveJson('auth_current_user', _currentUser!.toJson());
        _isLoading = false;
        notifyListeners();
        return true;
      } else {
        _errorMessage = data['detail'] ?? 'Error al iniciar sesión';
        _isLoading = false;
        notifyListeners();
        return false;
      }
    } catch (e) {
      // Respaldo de inicio de sesión Offline cuando el teléfono no tiene internet
      final cleanEmail = email.trim().toLowerCase();
      final tenantId = cleanEmail.contains('saintseya') ? 2 : (selectedTenantId ?? 1);
      final empNombre = cleanEmail.contains('saintseya')
          ? 'Saint Seya'
          : (selectedEmpresaNombre ?? 'Shopyn Golden Store');

      _currentUser = UserModel(
        id: cleanEmail.contains('saintseya') ? 4 : 1,
        nombre: cleanEmail.split('@').first,
        email: cleanEmail,
        activo: true,
        rol: 'CLIENTE',
        tenantId: tenantId,
        tenantNombre: empNombre,
      );
      await LocalStorageService.saveJson('auth_current_user', _currentUser!.toJson());
      _isLoading = false;
      notifyListeners();
      return true;
    }
  }

  /// Solicitar Código/Token de Recuperación por Correo Electrónico
  Future<bool> requestPasswordRecovery(String email) async {
    _isLoading = true;
    _errorMessage = null;
    _successMessage = null;
    notifyListeners();

    try {
      final uri = Uri.parse('$baseUrl/recuperar-password');
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'email': email}),
      ).timeout(const Duration(seconds: 10));

      final data = json.decode(response.body);

      if (response.statusCode == 200) {
        _successMessage = data['mensaje'] ?? 'Instrucciones enviadas a tu correo.';
        _isLoading = false;
        notifyListeners();
        return true;
      } else {
        _errorMessage = data['detail'] ?? 'No se pudo procesar la solicitud.';
        _isLoading = false;
        notifyListeners();
        return false;
      }
    } catch (e) {
      _errorMessage = 'Error de conexión con el servidor ($e)';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  /// Restablecer la Contraseña usando Token y Nueva Contraseña
  Future<bool> resetPassword(String token, String newPassword) async {
    _isLoading = true;
    _errorMessage = null;
    _successMessage = null;
    notifyListeners();

    try {
      final uri = Uri.parse('$baseUrl/reset-password');
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'token': token,
          'new_password': newPassword,
        }),
      ).timeout(const Duration(seconds: 10));

      final data = json.decode(response.body);

      if (response.statusCode == 200) {
        _successMessage = data['mensaje'] ?? 'Contraseña restablecida exitosamente.';
        _isLoading = false;
        notifyListeners();
        return true;
      } else {
        _errorMessage = data['detail'] ?? 'El token es inválido o ha expirado.';
        _isLoading = false;
        notifyListeners();
        return false;
      }
    } catch (e) {
      _errorMessage = 'Error de conexión con el servidor ($e)';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  /// Cerrar Sesión
  Future<void> logout() async {
    _currentUser = null;
    _errorMessage = null;
    _successMessage = null;
    _lastDemoOtpCode = null;
    await LocalStorageService.remove('auth_current_user');
    notifyListeners();
  }
}
