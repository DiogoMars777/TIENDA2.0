// ==============================================================================
// CAPA CONTROLADOR (MVC - CONTROLLER EN FLUTTER / DART)
// Controlador de Estado para CU08: Catálogo, Selector Multi-Empresa y Modo Offline
// Ubicación: mobile-app/lib/controllers/product_controller.dart
// ==============================================================================

import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/product_model.dart';
import '../models/inventory_model.dart';
import '../config/api_config.dart';
import '../services/local_storage_service.dart';

class ProductController extends ChangeNotifier {
  static String get baseUrl => '${ApiConfig.baseUrl}/productos';
  static String get inventarioUrl => '${ApiConfig.baseUrl}/inventario';
  static String get tenantsUrl => '${ApiConfig.baseUrl}/suscripciones-tenants/empresas-disponibles';

  // Lista tradicional (compatibilidad)
  List<ProductModel> _productos = [];
  bool _cargando = false;
  String? _error;

  // Multi-Tenant: Empresas disponibles y empresa seleccionada
  List<EmpresaModel> _empresas = _defaultEmpresas();
  int _empresaSeleccionadaId = 1;

  // CU08: Catálogo enriquecido con disponibilidad por sucursal
  List<CatalogProductModel> _catalogo = [];
  List<CatalogProductModel> _catalogoCompletoCache = [];
  List<BranchModel> _sucursales = [];
  int? _sucursalSeleccionadaId;

  // Estado Offline
  bool _modoOfflineSimulado = false;
  bool _usandoCacheOffline = false;

  List<ProductModel> get productos => _productos;
  List<CatalogProductModel> get catalogo => _catalogo;
  List<BranchModel> get sucursales => _sucursales;
  int? get sucursalSeleccionadaId => _sucursalSeleccionadaId;
  List<EmpresaModel> get empresas => _empresas;
  int get empresaSeleccionadaId => _empresaSeleccionadaId;
  bool get cargando => _cargando;
  String? get error => _error;
  bool get modoOfflineSimulado => _modoOfflineSimulado;
  bool get usandoCacheOffline => _usandoCacheOffline || _modoOfflineSimulado;

  EmpresaModel get empresaActual {
    try {
      return _empresas.firstWhere((e) => e.id == _empresaSeleccionadaId);
    } catch (_) {
      return _empresas.isNotEmpty
          ? _empresas.first
          : EmpresaModel(id: 1, nombre: 'Shopyn Golden Store', slug: 'goldenstore');
    }
  }

  BranchModel? get sucursalActual {
    if (_sucursales.isEmpty) return null;
    try {
      return _sucursales.firstWhere((s) => s.id == _sucursalSeleccionadaId);
    } catch (_) {
      return _sucursales.first;
    }
  }

  ProductController() {
    _inicializar();
  }

  Future<void> _inicializar() async {
    // 1. Restaurar empresa seleccionada y caché local inmediatamente
    final savedTenantId = await LocalStorageService.readJson('empresa_activa_id');
    if (savedTenantId is int && savedTenantId > 0) {
      _empresaSeleccionadaId = savedTenantId;
    }

    final savedEmpresas = await LocalStorageService.readJson('empresas_disponibles');
    if (savedEmpresas is List && savedEmpresas.isNotEmpty) {
      _empresas = savedEmpresas
          .map((e) => EmpresaModel.fromJson(Map<String, dynamic>.from(e)))
          .toList();
    }

    await _cargarCacheLocalEmpresa(_empresaSeleccionadaId);
    notifyListeners();

    // 2. Actualizar desde el servidor en segundo plano si hay internet
    await fetchEmpresasDisponibles();
    await fetchSucursales();
    await fetchCatalogoConDisponibilidad();
    _precargarTodasLasEmpresasEnFondo();
  }

  /// Activa o desactiva la simulación manual de Modo Sin Internet
  void toggleModoOffline({bool? forzar}) {
    _modoOfflineSimulado = forzar ?? !_modoOfflineSimulado;
    if (_modoOfflineSimulado) {
      _usandoCacheOffline = true;
      _error = null;
      if (_catalogo.isEmpty) {
        _cargarCacheLocalEmpresa(_empresaSeleccionadaId);
      }
    } else {
      _usandoCacheOffline = false;
      fetchProductos(forceRefresh: true);
    }
    notifyListeners();
  }

  /// Obtiene la lista de empresas (tenants) activas del servidor o caché local
  Future<void> fetchEmpresasDisponibles() async {
    if (_modoOfflineSimulado) return;
    try {
      final response = await http.get(Uri.parse(tenantsUrl)).timeout(const Duration(seconds: 6));
      if (response.statusCode == 200) {
        final decoded = json.decode(utf8.decode(response.bodyBytes));
        final List<dynamic> rawList = decoded is Map ? (decoded['empresas'] ?? []) : [];
        if (rawList.isNotEmpty) {
          _empresas = rawList
              .map((j) => EmpresaModel.fromJson(Map<String, dynamic>.from(j)))
              .toList();
          await LocalStorageService.saveJson(
            'empresas_disponibles',
            _empresas.map((e) => e.toJson()).toList(),
          );
          if (!_empresas.any((e) => e.id == _empresaSeleccionadaId)) {
            _empresaSeleccionadaId = _empresas.first.id;
          }
          notifyListeners();
        }
      }
    } catch (e) {
      debugPrint('Usando lista de empresas en caché local: $e');
    }
  }

  /// Cambia la empresa (Tenant) activa y recarga su catálogo y sucursales (Online u Offline)
  Future<void> seleccionarEmpresa(int tenantId) async {
    _empresaSeleccionadaId = tenantId;
    _sucursalSeleccionadaId = null;
    _error = null;
    await LocalStorageService.saveJson('empresa_activa_id', tenantId);

    // Cargar primero desde la base local del teléfono para respuesta instantánea (y soporte offline)
    await _cargarCacheLocalEmpresa(tenantId);
    notifyListeners();

    if (!_modoOfflineSimulado) {
      await fetchSucursales();
      await fetchCatalogoConDisponibilidad(forceRefresh: true);
    }
  }

  /// Carga las sucursales y el catálogo de una empresa desde la memoria local del teléfono
  Future<void> _cargarCacheLocalEmpresa(int tenantId) async {
    final cachedSucs = await LocalStorageService.readJson('sucursales_tenant_$tenantId');
    if (cachedSucs is List && cachedSucs.isNotEmpty) {
      _sucursales = cachedSucs
          .map((s) => BranchModel.fromJson(Map<String, dynamic>.from(s)))
          .toList();
    } else {
      // Buscar sucursales dentro de _empresas o fallback por defecto
      final emp = _empresas.where((e) => e.id == tenantId).toList();
      if (emp.isNotEmpty && emp.first.sucursales.isNotEmpty) {
        _sucursales = List.from(emp.first.sucursales);
      } else {
        _sucursales = _fallbackSucursalesPorTenant(tenantId);
      }
    }

    if (_sucursales.isNotEmpty) {
      _sucursalSeleccionadaId = _sucursales.first.id;
    }

    final cachedCat = await LocalStorageService.readJson('catalogo_tenant_$tenantId');
    if (cachedCat is List && cachedCat.isNotEmpty) {
      _catalogoCompletoCache = cachedCat
          .map((c) => CatalogProductModel.fromJson(Map<String, dynamic>.from(c)))
          .toList();
      _catalogo = List.from(_catalogoCompletoCache);
    } else {
      _catalogoCompletoCache = _fallbackCatalogoPorTenant(tenantId);
      _catalogo = List.from(_catalogoCompletoCache);
    }

    _sincronizarProductosCompatibilidad();
  }

  void _sincronizarProductosCompatibilidad() {
    _productos = _catalogo.map((c) => ProductModel(
      id: c.id,
      nombre: c.nombre,
      descripcion: c.descripcion,
      precio: c.preciobase,
      stock: c.stockSucursal,
      imagenUrl: c.imagenprincipal,
      activo: c.disponible,
    )).toList();
  }

  /// CU08: Obtiene las tiendas físicas de la empresa activa
  Future<void> fetchSucursales() async {
    if (_modoOfflineSimulado) return;
    try {
      final response = await http.get(
        Uri.parse('$inventarioUrl/sucursales'),
        headers: {'X-Tenant-ID': '$_empresaSeleccionadaId'},
      ).timeout(const Duration(seconds: 6));

      if (response.statusCode == 200) {
        final raw = utf8.decode(response.bodyBytes);
        final List<dynamic> data = json.decode(raw);
        final lista = data.map((j) => BranchModel.fromJson(Map<String, dynamic>.from(j))).toList();
        if (lista.isNotEmpty) {
          _sucursales = lista;
          await LocalStorageService.saveJson(
            'sucursales_tenant_$_empresaSeleccionadaId',
            _sucursales.map((s) => s.toJson()).toList(),
          );
          if (_sucursalSeleccionadaId == null || !_sucursales.any((s) => s.id == _sucursalSeleccionadaId)) {
            _sucursalSeleccionadaId = _sucursales.first.id;
          }
          notifyListeners();
        }
      }
    } catch (e) {
      debugPrint('Usando sucursales locales para tenant $_empresaSeleccionadaId: $e');
    }
  }

  /// CU08: Cambia la sucursal activa y refresca el inventario
  void seleccionarSucursal(int? sucursalId) {
    _sucursalSeleccionadaId = sucursalId;
    notifyListeners();
    fetchCatalogoConDisponibilidad(sucursalId: sucursalId, forceRefresh: true);
  }

  /// CU08: Consulta el catálogo con existencias y variantes por sucursal (con soporte Offline-First)
  Future<void> fetchCatalogoConDisponibilidad({int? sucursalId, String? search, bool forceRefresh = false}) async {
    final bool isSearch = search != null && search.trim().isNotEmpty;

    // Si estamos en modo offline simulado, filtramos directamente sobre la base local del teléfono
    if (_modoOfflineSimulado) {
      _usandoCacheOffline = true;
      _error = null;
      _filtrarCatalogoLocal(search);
      notifyListeners();
      return;
    }

    if (_catalogo.isEmpty) {
      _cargando = true;
      _error = null;
      notifyListeners();
    }

    try {
      var uri = Uri.parse('$inventarioUrl/catalogo');
      Map<String, String> params = {};

      int? targetSucursal = sucursalId ?? _sucursalSeleccionadaId;
      if (targetSucursal != null) {
        params['sucursal_id'] = targetSucursal.toString();
      }
      if (isSearch) {
        params['search'] = search.trim();
      }

      if (params.isNotEmpty) {
        uri = uri.replace(queryParameters: params);
      }

      final response = await http.get(
        uri,
        headers: {'X-Tenant-ID': '$_empresaSeleccionadaId'},
      ).timeout(const Duration(seconds: 7));

      if (response.statusCode == 200) {
        final rawBody = utf8.decode(response.bodyBytes);
        final List<dynamic> data = json.decode(rawBody);
        final onlineCatalog = data
            .map((j) => CatalogProductModel.fromJson(Map<String, dynamic>.from(j)))
            .toList();

        _catalogo = onlineCatalog;
        if (!isSearch && onlineCatalog.isNotEmpty) {
          _catalogoCompletoCache = List.from(onlineCatalog);
          await LocalStorageService.saveJson(
            'catalogo_tenant_$_empresaSeleccionadaId',
            onlineCatalog.map((c) => c.toJson()).toList(),
          );
        }

        _sincronizarProductosCompatibilidad();
        _usandoCacheOffline = false;
        _error = null;
      } else {
        _activarFallbackOffline(search);
      }
    } catch (e) {
      debugPrint('Sin conexión al servidor, activando catálogo local del móvil: $e');
      _activarFallbackOffline(search);
    } finally {
      _cargando = false;
      notifyListeners();
    }
  }

  void _activarFallbackOffline(String? search) {
    _usandoCacheOffline = true;
    _error = null;
    if (_catalogoCompletoCache.isEmpty) {
      _catalogoCompletoCache = _fallbackCatalogoPorTenant(_empresaSeleccionadaId);
    }
    _filtrarCatalogoLocal(search);
  }

  void _filtrarCatalogoLocal(String? search) {
    if (search == null || search.trim().isEmpty) {
      _catalogo = List.from(_catalogoCompletoCache);
    } else {
      final q = search.trim().toLowerCase();
      _catalogo = _catalogoCompletoCache.where((p) {
        return p.nombre.toLowerCase().contains(q) ||
            (p.marca?.toLowerCase().contains(q) ?? false) ||
            (p.descripcion?.toLowerCase().contains(q) ?? false);
      }).toList();
    }
    _sincronizarProductosCompatibilidad();
  }

  /// Precarga en segundo plano los catálogos de todas las empresas para tenerlos listos sin internet
  Future<void> _precargarTodasLasEmpresasEnFondo() async {
    if (_modoOfflineSimulado) return;
    for (final emp in _empresas) {
      try {
        final sucsResp = await http.get(
          Uri.parse('$inventarioUrl/sucursales'),
          headers: {'X-Tenant-ID': '${emp.id}'},
        ).timeout(const Duration(seconds: 5));
        if (sucsResp.statusCode == 200) {
          final List<dynamic> sData = json.decode(utf8.decode(sucsResp.bodyBytes));
          if (sData.isNotEmpty) {
            await LocalStorageService.saveJson('sucursales_tenant_${emp.id}', sData);
          }
        }

        final catResp = await http.get(
          Uri.parse('$inventarioUrl/catalogo'),
          headers: {'X-Tenant-ID': '${emp.id}'},
        ).timeout(const Duration(seconds: 6));
        if (catResp.statusCode == 200) {
          final List<dynamic> cData = json.decode(utf8.decode(catResp.bodyBytes));
          if (cData.isNotEmpty) {
            await LocalStorageService.saveJson('catalogo_tenant_${emp.id}', cData);
          }
        }
      } catch (_) {}
    }
  }

  /// CU08: Consulta la disponibilidad detallada de un producto en todas las sucursales
  Future<ProductAvailabilityModel?> fetchDisponibilidadProducto(int productoId) async {
    if (!_modoOfflineSimulado) {
      try {
        final response = await http.get(
          Uri.parse('$inventarioUrl/producto/$productoId/disponibilidad'),
          headers: {'X-Tenant-ID': '$_empresaSeleccionadaId'},
        ).timeout(const Duration(seconds: 5));
        if (response.statusCode == 200) {
          final Map<String, dynamic> data = json.decode(utf8.decode(response.bodyBytes));
          return ProductAvailabilityModel.fromJson(data);
        }
      } catch (e) {
        debugPrint('Disponibilidad offline fallback: $e');
      }
    }

    // Fallback offline usando los datos locales del producto y sucursales de la empresa
    try {
      final prod = _catalogo.firstWhere((p) => p.id == productoId);
      final sucs = _sucursales.isNotEmpty ? _sucursales : _fallbackSucursalesPorTenant(_empresaSeleccionadaId);
      return ProductAvailabilityModel(
        productoId: prod.id,
        productoNombre: prod.nombre,
        marca: prod.marca,
        preciobase: prod.preciobase,
        imagenprincipal: prod.imagenprincipal,
        sucursales: sucs.map((s) => BranchAvailabilityDetailModel(
          sucursalId: s.id,
          sucursalNombre: s.nombre,
          ciudad: s.ciudad,
          direccion: s.direccion,
          telefono: s.telefono,
          stockTotal: prod.stockSucursal,
          variantes: prod.variantes,
        )).toList(),
      );
    } catch (_) {
      return null;
    }
  }

  /// Consulta tradicional de productos (con carga de empresas y sucursales)
  Future<void> fetchProductos({bool forceRefresh = false}) async {
    await fetchEmpresasDisponibles();
    await fetchSucursales();
    await fetchCatalogoConDisponibilidad(forceRefresh: forceRefresh);
  }

  static List<EmpresaModel> _defaultEmpresas() {
    return [
      EmpresaModel(
        id: 1,
        nombre: 'Shopyn Golden Store',
        slug: 'goldenstore',
        planNombre: 'Enterprise',
        sucursales: _fallbackSucursalesPorTenant(1),
      ),
      EmpresaModel(
        id: 2,
        nombre: 'Saint Seya',
        slug: 'saint-seya',
        planNombre: 'Profesional',
        sucursales: _fallbackSucursalesPorTenant(2),
      ),
    ];
  }

  static List<BranchModel> _fallbackSucursalesPorTenant(int tenantId) {
    if (tenantId == 2) {
      return [
        BranchModel(
          id: 4,
          nombre: 'Sucursal Central - Saint Seya',
          ciudad: 'Santa Cruz',
          direccion: 'Av. Los Caballeros #100',
          telefono: '70012345',
        ),
      ];
    }
    return [
      BranchModel(
        id: 1,
        nombre: 'Sucursal Central (Principal)',
        ciudad: 'Santa Cruz',
        direccion: 'Av. Cristo Redentor #450',
        telefono: '33445566',
      ),
      BranchModel(
        id: 2,
        nombre: 'Sucursal Equipetrol',
        ciudad: 'Santa Cruz',
        direccion: 'Calle 3 Este, Equipetrol Norte',
        telefono: '33445577',
      ),
      BranchModel(
        id: 3,
        nombre: 'Sucursal Norte',
        ciudad: 'Santa Cruz',
        direccion: 'Av. Banzer 4to Anillo',
        telefono: '33445588',
      ),
    ];
  }

  static List<CatalogProductModel> _fallbackCatalogoPorTenant(int tenantId) {
    if (tenantId == 2) {
      return [
        CatalogProductModel(
          id: 6,
          nombre: 'Polera Pegaso Seiya Meteoros',
          descripcion: 'Polera edición especial Saint Seya bronce',
          marca: 'Saint Seya Official',
          genero: 'Unisex',
          preciobase: 135.0,
          imagenprincipal: 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600',
          categoriaNombre: 'Armaduras de Bronce',
          stockSucursal: 15,
          stockTotal: 15,
          disponible: true,
          variantes: [
            ProductVariantModel(varianteId: 58, sku: 'SS-PEG-M', talla: 'M', color: 'Blanco', codigohex: '#FFFFFF', precio: 135.0, stock: 15, disponible: true),
          ],
        ),
        CatalogProductModel(
          id: 7,
          nombre: 'Polera Dragón Shiryu Negra',
          descripcion: 'Polera estampado Dragón Naciente',
          marca: 'Saint Seya Official',
          genero: 'Unisex',
          preciobase: 145.0,
          imagenprincipal: 'https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=600',
          categoriaNombre: 'Armaduras de Bronce',
          stockSucursal: 15,
          stockTotal: 15,
          disponible: true,
          variantes: [
            ProductVariantModel(varianteId: 59, sku: 'SS-DRA-L', talla: 'L', color: 'Negro', codigohex: '#111827', precio: 145.0, stock: 15, disponible: true),
          ],
        ),
        CatalogProductModel(
          id: 8,
          nombre: 'Polera Armadura Dorada Sagitario',
          descripcion: 'Polera premium bordado dorado Sagitario Aioros',
          marca: 'Saint Seya Gold',
          genero: 'Unisex',
          preciobase: 180.0,
          imagenprincipal: 'https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=600',
          categoriaNombre: 'Armaduras Doradas',
          stockSucursal: 15,
          stockTotal: 15,
          disponible: true,
          variantes: [
            ProductVariantModel(varianteId: 60, sku: 'SS-SAG-M', talla: 'M', color: 'Dorado', codigohex: '#F59E0B', precio: 180.0, stock: 15, disponible: true),
          ],
        ),
        CatalogProductModel(
          id: 9,
          nombre: 'Polera Fénix Ikki Edición Fuego',
          descripcion: 'Polera algodón peruano Ave Fénix',
          marca: 'Saint Seya Official',
          genero: 'Unisex',
          preciobase: 150.0,
          imagenprincipal: 'https://images.unsplash.com/photo-1562157873-818bc0726f68?w=600',
          categoriaNombre: 'Armaduras de Bronce',
          stockSucursal: 15,
          stockTotal: 15,
          disponible: true,
          variantes: [
            ProductVariantModel(varianteId: 61, sku: 'SS-FEN-M', talla: 'M', color: 'Rojo', codigohex: '#EF4444', precio: 150.0, stock: 15, disponible: true),
          ],
        ),
        CatalogProductModel(
          id: 10,
          nombre: 'Polera Caballero Cisne Hyoga Blanca',
          descripcion: 'Polera Polvo de Diamantes Cisne Hyoga',
          marca: 'Saint Seya Official',
          genero: 'Unisex',
          preciobase: 130.0,
          imagenprincipal: 'https://images.unsplash.com/photo-1529374255404-311a2a4f1fd9?w=600',
          categoriaNombre: 'Armaduras de Bronce',
          stockSucursal: 15,
          stockTotal: 15,
          disponible: true,
          variantes: [
            ProductVariantModel(varianteId: 62, sku: 'SS-CIS-S', talla: 'S', color: 'Azul', codigohex: '#3B82F6', precio: 130.0, stock: 15, disponible: true),
          ],
        ),
      ];
    }

    return [
      CatalogProductModel(
        id: 1,
        nombre: 'Polera Básica Algodón',
        descripcion: 'Polera 100% algodón peruano suave',
        marca: 'Golden Brand',
        genero: 'Unisex',
        preciobase: 85.0,
        imagenprincipal: 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600',
        categoriaNombre: 'Básicas',
        stockSucursal: 25,
        stockTotal: 50,
        disponible: true,
        variantes: [
          ProductVariantModel(varianteId: 1, sku: 'POL-BAS-M', talla: 'M', color: 'Blanco', codigohex: '#FFFFFF', precio: 85.0, stock: 25, disponible: true),
        ],
      ),
      CatalogProductModel(
        id: 2,
        nombre: 'Polera Oversize Urbana',
        descripcion: 'Corte holgado urbano tendencia streetwear',
        marca: 'Golden Street',
        genero: 'Unisex',
        preciobase: 120.0,
        imagenprincipal: 'https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=600',
        categoriaNombre: 'Oversize',
        stockSucursal: 20,
        stockTotal: 40,
        disponible: true,
        variantes: [
          ProductVariantModel(varianteId: 2, sku: 'POL-OVR-L', talla: 'L', color: 'Negro', codigohex: '#111827', precio: 120.0, stock: 20, disponible: true),
        ],
      ),
      CatalogProductModel(
        id: 3,
        nombre: 'Polera Deportiva DryFit',
        descripcion: 'Tela respirable secado rápido para entrenamiento',
        marca: 'Golden Sport',
        genero: 'Hombre',
        preciobase: 95.0,
        imagenprincipal: 'https://images.unsplash.com/photo-1581655353564-df123a1eb820?w=600',
        categoriaNombre: 'Deportivas',
        stockSucursal: 18,
        stockTotal: 35,
        disponible: true,
        variantes: [
          ProductVariantModel(varianteId: 3, sku: 'POL-DRY-M', talla: 'M', color: 'Azul Marino', codigohex: '#1E3A8A', precio: 95.0, stock: 18, disponible: true),
        ],
      ),
    ];
  }
}
