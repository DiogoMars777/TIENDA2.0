// ==============================================================================
// MODELO DE USUARIO (MVC - MODEL)
// DTO de Usuario para la aplicación móvil con soporte Multi-Tenant
// ==============================================================================

class UserModel {
  final int id;
  final String nombre;
  final String email;
  final bool activo;
  final String? rol;
  final String? token;
  final String? refreshToken;
  final int? tenantId;
  final String? tenantNombre;

  UserModel({
    required this.id,
    required this.nombre,
    required this.email,
    required this.activo,
    this.rol,
    this.token,
    this.refreshToken,
    this.tenantId,
    this.tenantNombre,
  });

  factory UserModel.fromJson(Map<String, dynamic> json, {String? token, String? refreshToken, String? rol}) {
    final usuarioData = json['usuario'] is Map<String, dynamic> ? json['usuario'] : json;

    return UserModel(
      id: usuarioData['id'] ?? 0,
      nombre: usuarioData['nombre'] ?? '',
      email: usuarioData['email'] ?? '',
      activo: usuarioData['activo'] ?? true,
      rol: rol ?? json['rol'] ?? usuarioData['rol'],
      token: token ?? json['access_token'] ?? json['token'],
      refreshToken: refreshToken ?? json['refresh_token'] ?? json['refreshToken'],
      tenantId: usuarioData['tenant_id'] ?? json['tenant_id'] ?? json['tenantId'],
      tenantNombre: usuarioData['tenant_nombre'] ?? json['tenant_nombre'] ?? json['tenantNombre'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'nombre': nombre,
      'email': email,
      'activo': activo,
      'rol': rol,
      'token': token,
      'refreshToken': refreshToken,
      'tenantId': tenantId,
      'tenantNombre': tenantNombre,
    };
  }
}
