// ==============================================================================
// CAPA MODELO (MVC - MODEL EN FLUTTER / DART)
// Módulo: CU10 - Gestionar Reservas de Prendas (Con Soporte Offline-First)
// Ubicación: mobile-app/lib/models/reservation_model.dart
// ==============================================================================

double _parseDouble(dynamic value, [double defaultValue = 0.0]) {
  if (value == null) return defaultValue;
  if (value is num) return value.toDouble();
  return double.tryParse(value.toString()) ?? defaultValue;
}

int _parseInt(dynamic value, [int defaultValue = 0]) {
  if (value == null) return defaultValue;
  if (value is num) return value.toInt();
  return int.tryParse(value.toString()) ?? defaultValue;
}

class ReservaDetalleItem {
  final int varianteId;
  final int? productoId;
  final String productoNombre;
  final String? talla;
  final String? color;
  final String? imagenUrl;
  final double precioUnitario;
  final int cantidad;
  final double subtotal;

  ReservaDetalleItem({
    required this.varianteId,
    this.productoId,
    required this.productoNombre,
    this.talla,
    this.color,
    this.imagenUrl,
    required this.precioUnitario,
    required this.cantidad,
    required this.subtotal,
  });

  factory ReservaDetalleItem.fromJson(Map<String, dynamic> json) {
    return ReservaDetalleItem(
      varianteId: _parseInt(json['variante_id'] ?? json['id']),
      productoId: json['producto_id'] != null ? _parseInt(json['producto_id']) : null,
      productoNombre: json['producto_nombre']?.toString() ?? json['producto']?.toString() ?? 'Prenda',
      talla: json['talla']?.toString(),
      color: json['color']?.toString(),
      imagenUrl: json['imagen_url']?.toString(),
      precioUnitario: _parseDouble(json['precio_unitario']),
      cantidad: _parseInt(json['cantidad'], 1),
      subtotal: _parseDouble(json['subtotal']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'variante_id': varianteId,
      'producto_id': productoId,
      'producto_nombre': productoNombre,
      'talla': talla,
      'color': color,
      'imagen_url': imagenUrl,
      'precio_unitario': precioUnitario,
      'cantidad': cantidad,
      'subtotal': subtotal,
    };
  }
}

class ReservaModel {
  final int id;
  final String codigoReserva;
  final String fechaReserva;
  final String estado;
  final String? observaciones;
  final int? sucursalId;
  final String? sucursalNombre;
  final String? sucursalDireccion;
  final int? tenantId;
  final String? empresaNombre;
  final bool esOffline;
  final List<ReservaDetalleItem> detalles;
  final int totalItems;
  final double totalEstimado;

  ReservaModel({
    required this.id,
    required this.codigoReserva,
    required this.fechaReserva,
    required this.estado,
    this.observaciones,
    this.sucursalId,
    this.sucursalNombre,
    this.sucursalDireccion,
    this.tenantId,
    this.empresaNombre,
    this.esOffline = false,
    required this.detalles,
    required this.totalItems,
    required this.totalEstimado,
  });

  factory ReservaModel.fromJson(Map<String, dynamic> json) {
    var sucursal = json['sucursal'];
    var rawDetalles = json['detalles'] as List? ?? json['items'] as List? ?? [];
    List<ReservaDetalleItem> detallesList =
        rawDetalles.map((d) => ReservaDetalleItem.fromJson(Map<String, dynamic>.from(d))).toList();

    final codigo = json['codigo_reserva']?.toString() ?? '';
    final isOff = (json['es_offline'] == true);

    return ReservaModel(
      id: _parseInt(json['id']),
      codigoReserva: codigo,
      fechaReserva: json['fecha_reserva']?.toString() ?? '',
      estado: json['estado']?.toString() ?? 'PENDIENTE',
      observaciones: json['observaciones']?.toString(),
      sucursalId: sucursal != null ? _parseInt(sucursal['id']) : (json['sucursal_id'] != null ? _parseInt(json['sucursal_id']) : null),
      sucursalNombre: sucursal != null ? sucursal['nombre']?.toString() : json['sucursal_nombre']?.toString(),
      sucursalDireccion: sucursal != null ? sucursal['direccion']?.toString() : json['sucursal_direccion']?.toString(),
      tenantId: json['tenant_id'] != null ? _parseInt(json['tenant_id']) : null,
      empresaNombre: json['empresa_nombre']?.toString(),
      esOffline: isOff,
      detalles: detallesList,
      totalItems: _parseInt(json['total_items'] ?? detallesList.fold<int>(0, (s, d) => s + d.cantidad)),
      totalEstimado: _parseDouble(json['total_estimado']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'codigo_reserva': codigoReserva,
      'fecha_reserva': fechaReserva,
      'estado': estado,
      'observaciones': observaciones,
      'sucursal_id': sucursalId,
      'sucursal_nombre': sucursalNombre,
      'sucursal_direccion': sucursalDireccion,
      'tenant_id': tenantId,
      'empresa_nombre': empresaNombre,
      'es_offline': esOffline,
      'detalles': detalles.map((d) => d.toJson()).toList(),
      'total_items': totalItems,
      'total_estimado': totalEstimado,
    };
  }

  ReservaModel copyWith({
    int? id,
    String? codigoReserva,
    String? fechaReserva,
    String? estado,
    String? observaciones,
    int? sucursalId,
    String? sucursalNombre,
    String? sucursalDireccion,
    int? tenantId,
    String? empresaNombre,
    bool? esOffline,
    List<ReservaDetalleItem>? detalles,
    int? totalItems,
    double? totalEstimado,
  }) {
    return ReservaModel(
      id: id ?? this.id,
      codigoReserva: codigoReserva ?? this.codigoReserva,
      fechaReserva: fechaReserva ?? this.fechaReserva,
      estado: estado ?? this.estado,
      observaciones: observaciones ?? this.observaciones,
      sucursalId: sucursalId ?? this.sucursalId,
      sucursalNombre: sucursalNombre ?? this.sucursalNombre,
      sucursalDireccion: sucursalDireccion ?? this.sucursalDireccion,
      tenantId: tenantId ?? this.tenantId,
      empresaNombre: empresaNombre ?? this.empresaNombre,
      esOffline: esOffline ?? this.esOffline,
      detalles: detalles ?? this.detalles,
      totalItems: totalItems ?? this.totalItems,
      totalEstimado: totalEstimado ?? this.totalEstimado,
    );
  }
}
