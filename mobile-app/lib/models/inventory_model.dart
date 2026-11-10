// ==============================================================================
// CAPA MODELO (MVC - MODEL EN FLUTTER / DART)
// Módulo: CU08 - Consultar Catálogo y Disponibilidad de Inventario + Multi-Tenant
// Ubicación: mobile-app/lib/models/inventory_model.dart
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

class EmpresaModel {
  final int id;
  final String nombre;
  final String slug;
  final String? planNombre;
  final List<BranchModel> sucursales;

  EmpresaModel({
    required this.id,
    required this.nombre,
    required this.slug,
    this.planNombre,
    this.sucursales = const [],
  });

  factory EmpresaModel.fromJson(Map<String, dynamic> json) {
    final rawSucs = json['sucursales'] as List? ?? [];
    return EmpresaModel(
      id: _parseInt(json['id'], 1),
      nombre: json['nombre']?.toString() ?? 'Tienda',
      slug: json['slug']?.toString() ?? 'tienda',
      planNombre: json['plan_nombre']?.toString(),
      sucursales: rawSucs.map((s) => BranchModel.fromJson(Map<String, dynamic>.from(s))).toList(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'nombre': nombre,
      'slug': slug,
      'plan_nombre': planNombre,
      'sucursales': sucursales.map((s) => s.toJson()).toList(),
    };
  }
}

class BranchModel {
  final int id;
  final String nombre;
  final String? ciudad;
  final String? direccion;
  final String? telefono;

  BranchModel({
    required this.id,
    required this.nombre,
    this.ciudad,
    this.direccion,
    this.telefono,
  });

  factory BranchModel.fromJson(Map<String, dynamic> json) {
    return BranchModel(
      id: _parseInt(json['id']),
      nombre: json['nombre']?.toString() ?? '',
      ciudad: json['ciudad']?.toString(),
      direccion: json['direccion']?.toString(),
      telefono: json['telefono']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'nombre': nombre,
      'ciudad': ciudad,
      'direccion': direccion,
      'telefono': telefono,
    };
  }
}

class ProductVariantModel {
  final int varianteId;
  final String? sku;
  final String? talla;
  final String? color;
  final String? codigohex;
  final double precio;
  final int stock;
  final bool disponible;

  ProductVariantModel({
    required this.varianteId,
    this.sku,
    this.talla,
    this.color,
    this.codigohex,
    required this.precio,
    required this.stock,
    required this.disponible,
  });

  factory ProductVariantModel.fromJson(Map<String, dynamic> json) {
    return ProductVariantModel(
      varianteId: _parseInt(json['variante_id']),
      sku: json['sku']?.toString(),
      talla: json['talla']?.toString(),
      color: json['color']?.toString(),
      codigohex: json['codigohex']?.toString(),
      precio: _parseDouble(json['precio'] ?? json['precioventa']),
      stock: _parseInt(json['stock']),
      disponible: json['disponible'] ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'variante_id': varianteId,
      'sku': sku,
      'talla': talla,
      'color': color,
      'codigohex': codigohex,
      'precio': precio,
      'stock': stock,
      'disponible': disponible,
    };
  }
}

class BranchAvailabilityDetailModel {
  final int sucursalId;
  final String sucursalNombre;
  final String? ciudad;
  final String? direccion;
  final String? telefono;
  final int stockTotal;
  final List<ProductVariantModel> variantes;

  BranchAvailabilityDetailModel({
    required this.sucursalId,
    required this.sucursalNombre,
    this.ciudad,
    this.direccion,
    this.telefono,
    required this.stockTotal,
    required this.variantes,
  });

  factory BranchAvailabilityDetailModel.fromJson(Map<String, dynamic> json) {
    var rawVars = json['variantes'] as List? ?? [];
    return BranchAvailabilityDetailModel(
      sucursalId: _parseInt(json['sucursal_id']),
      sucursalNombre: json['sucursal_nombre']?.toString() ?? '',
      ciudad: json['ciudad']?.toString(),
      direccion: json['direccion']?.toString(),
      telefono: json['telefono']?.toString(),
      stockTotal: _parseInt(json['stock_total']),
      variantes: rawVars.map((v) => ProductVariantModel.fromJson(Map<String, dynamic>.from(v))).toList(),
    );
  }
}

class ProductAvailabilityModel {
  final int productoId;
  final String productoNombre;
  final String? marca;
  final double preciobase;
  final String? imagenprincipal;
  final List<BranchAvailabilityDetailModel> sucursales;

  ProductAvailabilityModel({
    required this.productoId,
    required this.productoNombre,
    this.marca,
    required this.preciobase,
    this.imagenprincipal,
    required this.sucursales,
  });

  factory ProductAvailabilityModel.fromJson(Map<String, dynamic> json) {
    var rawSucs = json['sucursales'] as List? ?? [];
    return ProductAvailabilityModel(
      productoId: _parseInt(json['producto_id']),
      productoNombre: json['producto_nombre']?.toString() ?? '',
      marca: json['marca']?.toString(),
      preciobase: _parseDouble(json['preciobase'] ?? json['precio']),
      imagenprincipal: json['imagenprincipal']?.toString(),
      sucursales: rawSucs.map((s) => BranchAvailabilityDetailModel.fromJson(Map<String, dynamic>.from(s))).toList(),
    );
  }
}

class CatalogProductModel {
  final int id;
  final String nombre;
  final String? descripcion;
  final String? marca;
  final String? genero;
  final double preciobase;
  final String? imagenprincipal;
  final String? categoriaNombre;
  final int stockSucursal;
  final int stockTotal;
  final bool disponible;
  final List<ProductVariantModel> variantes;

  CatalogProductModel({
    required this.id,
    required this.nombre,
    this.descripcion,
    this.marca,
    this.genero,
    required this.preciobase,
    this.imagenprincipal,
    this.categoriaNombre,
    required this.stockSucursal,
    required this.stockTotal,
    required this.disponible,
    required this.variantes,
  });

  factory CatalogProductModel.fromJson(Map<String, dynamic> json) {
    var rawVariantes = json['variantes'] as List? ?? [];
    List<ProductVariantModel> listVariantes =
        rawVariantes.map((v) => ProductVariantModel.fromJson(Map<String, dynamic>.from(v))).toList();

    return CatalogProductModel(
      id: _parseInt(json['id']),
      nombre: json['nombre']?.toString() ?? '',
      descripcion: json['descripcion']?.toString(),
      marca: json['marca']?.toString(),
      genero: json['genero']?.toString(),
      preciobase: _parseDouble(json['preciobase'] ?? json['precio']),
      imagenprincipal: json['imagenprincipal']?.toString(),
      categoriaNombre: json['categoria_nombre']?.toString(),
      stockSucursal: _parseInt(json['stock_sucursal']),
      stockTotal: _parseInt(json['stock_total']),
      disponible: json['disponible'] ?? false,
      variantes: listVariantes,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'nombre': nombre,
      'descripcion': descripcion,
      'marca': marca,
      'genero': genero,
      'preciobase': preciobase,
      'imagenprincipal': imagenprincipal,
      'categoria_nombre': categoriaNombre,
      'stock_sucursal': stockSucursal,
      'stock_total': stockTotal,
      'disponible': disponible,
      'variantes': variantes.map((v) => v.toJson()).toList(),
    };
  }

  /// Lista de colores únicos disponibles para esta prenda
  List<Map<String, String>> get coloresUnicos {
    final seen = <String>{};
    final result = <Map<String, String>>[];
    for (final v in variantes) {
      if (v.color != null && v.color!.isNotEmpty && !seen.contains(v.color)) {
        seen.add(v.color!);
        result.add({
          'nombre': v.color!,
          'hex': v.codigohex ?? '#000000',
        });
      }
    }
    return result;
  }

  /// Lista de tallas únicas disponibles para esta prenda
  List<String> get tallasUnicas {
    final seen = <String>{};
    final result = <String>[];
    for (final v in variantes) {
      if (v.talla != null && v.talla!.isNotEmpty && !seen.contains(v.talla)) {
        seen.add(v.talla!);
        result.add(v.talla!);
      }
    }
    return result;
  }
}
