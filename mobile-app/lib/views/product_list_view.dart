// ==============================================================================
// CAPA VISTA (MVC - VIEW EN FLUTTER / DART)
// Pantalla de Catálogo y Disponibilidad de Inventario Multitienda (CU08 & CU15)
// Ubicación: mobile-app/lib/views/product_list_view.dart
// ==============================================================================

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../controllers/product_controller.dart';
import '../controllers/cart_controller.dart';
import '../controllers/auth_controller.dart';
import '../controllers/notification_controller.dart';
import '../models/product_model.dart';
import '../models/inventory_model.dart';
import 'my_reservations_view.dart';
import 'orders_history_view.dart';
import 'virtual_fitting_room_view.dart';

class ProductListView extends StatefulWidget {
  const ProductListView({super.key});

  @override
  State<ProductListView> createState() => _ProductListViewState();
}

class _ProductListViewState extends State<ProductListView> {
  final TextEditingController _searchCtrl = TextEditingController();
  Timer? _debounceTimer;

  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      if (mounted) {
        final prodCtrl = context.read<ProductController>();
        prodCtrl.fetchProductos();
        final auth = context.read<AuthController>();
        context.read<NotificationController>().fetchNotificaciones(
              auth.currentUser?.token,
              tenantId: prodCtrl.empresaSeleccionadaId,
            );
      }
    });
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    _searchCtrl.dispose();
    super.dispose();
  }

  void _onSearchChanged(String query) {
    _debounceTimer?.cancel();
    _debounceTimer = Timer(const Duration(milliseconds: 350), () {
      if (mounted) {
        context.read<ProductController>().fetchCatalogoConDisponibilidad(search: query);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final productCtrl = Provider.of<ProductController>(context);
    final cartCtrl = Provider.of<CartController>(context);
    final authCtrl = Provider.of<AuthController>(context, listen: false);

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: Text(
          productCtrl.empresaActual.nombre,
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        backgroundColor: const Color(0xFF0F172A),
        foregroundColor: Colors.white,
        elevation: 2,
        actions: [
          // Botón Simular Sin Internet / Modo Offline
          IconButton(
            icon: Icon(
              productCtrl.usandoCacheOffline ? Icons.wifi_off : Icons.wifi,
              color: productCtrl.usandoCacheOffline ? Colors.amber : Colors.greenAccent,
            ),
            tooltip: productCtrl.usandoCacheOffline ? 'Volver a Online' : 'Simular Sin Internet',
            onPressed: () {
              productCtrl.toggleModoOffline();
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(
                    productCtrl.modoOfflineSimulado
                        ? '📡 Modo Sin Internet activado: Usando catálogo y reservas en base local del móvil'
                        : '🌐 Modo Online activado: Sincronizando con el servidor...',
                  ),
                  backgroundColor: productCtrl.modoOfflineSimulado ? Colors.amber.shade800 : Colors.teal,
                  duration: const Duration(seconds: 2),
                ),
              );
            },
          ),

          // Botón Notificaciones con Contador (CU19)
          Consumer<NotificationController>(
            builder: (ctx, notifCtrl, _) {
              return Stack(
                alignment: Alignment.center,
                children: [
                  IconButton(
                    icon: const Icon(Icons.notifications_none),
                    tooltip: 'Notificaciones (CU19)',
                    onPressed: () => _mostrarNotificacionesSheet(context),
                  ),
                  if (notifCtrl.noLeidasCount > 0)
                    Positioned(
                      right: 6,
                      top: 6,
                      child: CircleAvatar(
                        radius: 8,
                        backgroundColor: Colors.redAccent,
                        child: Text(
                          '${notifCtrl.noLeidasCount}',
                          style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.white),
                        ),
                      ),
                    ),
                ],
              );
            },
          ),

          // Botón Carrito con Contador
          Stack(
            alignment: Alignment.center,
            children: [
              IconButton(
                icon: const Icon(Icons.shopping_bag_outlined),
                tooltip: 'Carrito de Compras',
                onPressed: () {
                  Navigator.pushNamed(context, '/cart');
                },
              ),
              if (cartCtrl.totalItemCount > 0)
                Positioned(
                  right: 8,
                  top: 8,
                  child: CircleAvatar(
                    radius: 9,
                    backgroundColor: const Color(0xFF38BDF8),
                    child: Text(
                      '${cartCtrl.totalItemCount}',
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF0F172A),
                      ),
                    ),
                  ),
                )
            ],
          ),

          // Botón Mis Reservas (CU10)
          IconButton(
            icon: const Icon(Icons.bookmark_border),
            tooltip: 'Mis Reservas (CU10)',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const MyReservationsView()),
              );
            },
          ),

          // Botón Mis Pedidos Digitales (CU15)
          IconButton(
            icon: const Icon(Icons.receipt_long),
            tooltip: 'Mis Pedidos (CU15)',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const OrdersHistoryView()),
              );
            },
          ),

          // Botón Cerrar Sesión
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Cerrar Sesión / Cambiar Empresa',
            onPressed: () {
              authCtrl.logout();
              cartCtrl.limpiarCarrito();
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Sesión cerrada correctamente'),
                  duration: Duration(seconds: 2),
                ),
              );
              Navigator.pushReplacementNamed(context, '/login');
            },
          ),
        ],
      ),
      body: Column(
        children: [
          // Banner de Modo Sin Internet (cuando está sin red o en modo offline simulado)
          if (productCtrl.usandoCacheOffline)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              color: const Color(0xFFD97706),
              child: const Row(
                children: [
                  Icon(Icons.wifi_off, color: Colors.white, size: 18),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'SIN INTERNET: Viendo catálogo local del móvil. Puedes agregar prendas y hacer Reservas Offline.',
                      style: TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
            ),

          // Selector de Empresa Disponible (Multi-Tenant) + Sucursal Física (CU08)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            color: const Color(0xFF1E293B),
            child: Column(
              children: [
                Row(
                  children: [
                    const Icon(Icons.apartment, color: Colors.amber, size: 20),
                    const SizedBox(width: 8),
                    const Text(
                      'Empresa:',
                      style: TextStyle(color: Colors.white70, fontSize: 12.5, fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton<int>(
                          isDense: true,
                          dropdownColor: const Color(0xFF0F172A),
                          value: productCtrl.empresaSeleccionadaId,
                          icon: const Icon(Icons.keyboard_arrow_down, color: Colors.amber),
                          isExpanded: true,
                          style: const TextStyle(color: Colors.amber, fontWeight: FontWeight.bold, fontSize: 13),
                          items: productCtrl.empresas.map((emp) {
                            return DropdownMenuItem<int>(
                              value: emp.id,
                              child: Text(emp.nombre, overflow: TextOverflow.ellipsis),
                            );
                          }).toList(),
                          onChanged: (nuevoTenantId) async {
                            if (nuevoTenantId != null && nuevoTenantId != productCtrl.empresaSeleccionadaId) {
                              cartCtrl.limpiarCarrito();
                              await productCtrl.seleccionarEmpresa(nuevoTenantId);
                              if (context.mounted) {
                                context.read<NotificationController>().fetchNotificaciones(
                                      authCtrl.currentUser?.token,
                                      tenantId: nuevoTenantId,
                                    );
                              }
                              if (productCtrl.sucursalActual != null) {
                                cartCtrl.setSucursal(
                                  productCtrl.sucursalActual!.id,
                                  productCtrl.sucursalActual!.nombre,
                                );
                              }
                            }
                          },
                        ),
                      ),
                    ),
                  ],
                ),
                const Divider(color: Colors.white12, height: 10),
                Row(
                  children: [
                    const Icon(Icons.storefront, color: Color(0xFF38BDF8), size: 20),
                    const SizedBox(width: 8),
                    const Text(
                      'Sucursal:',
                      style: TextStyle(color: Colors.white70, fontSize: 12.5, fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton<int>(
                          isDense: true,
                          dropdownColor: const Color(0xFF1E293B),
                          value: productCtrl.sucursalSeleccionadaId,
                          icon: const Icon(Icons.keyboard_arrow_down, color: Color(0xFF38BDF8)),
                          isExpanded: true,
                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                          items: productCtrl.sucursales.map((b) {
                            return DropdownMenuItem<int>(
                              value: b.id,
                              child: Text('${b.nombre} (${b.ciudad ?? "Bolivia"})', overflow: TextOverflow.ellipsis),
                            );
                          }).toList(),
                          onChanged: (newId) {
                            productCtrl.seleccionarSucursal(newId);
                            if (newId != null) {
                              final suc = productCtrl.sucursales.where((s) => s.id == newId).toList();
                              if (suc.isNotEmpty) {
                                cartCtrl.setSucursal(suc.first.id, suc.first.nombre);
                              }
                            }
                          },
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Barra de Búsqueda
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 6),
            child: TextField(
              controller: _searchCtrl,
              decoration: InputDecoration(
                hintText: 'Buscar poleras, modelos, marcas...',
                prefixIcon: const Icon(Icons.search, color: Colors.grey),
                suffixIcon: _searchCtrl.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchCtrl.clear();
                          productCtrl.fetchCatalogoConDisponibilidad(search: '');
                        },
                      )
                    : null,
                filled: true,
                fillColor: Colors.white,
                contentPadding: const EdgeInsets.symmetric(vertical: 0, horizontal: 16),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
                ),
              ),
              onChanged: _onSearchChanged,
              onSubmitted: (term) {
                productCtrl.fetchCatalogoConDisponibilidad(search: term);
              },
            ),
          ),

          // Lista de Productos con Disponibilidad
          Expanded(
            child: productCtrl.cargando
                ? const Center(child: CircularProgressIndicator())
                : productCtrl.error != null
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.cloud_off, size: 48, color: Colors.grey),
                            const SizedBox(height: 12),
                            Text(productCtrl.error!, textAlign: TextAlign.center),
                            const SizedBox(height: 12),
                            ElevatedButton(
                              onPressed: () => productCtrl.fetchProductos(),
                              child: const Text('Reintentar'),
                            )
                          ],
                        ),
                      )
                    : productCtrl.catalogo.isEmpty
                        ? RefreshIndicator(
                            onRefresh: () => productCtrl.fetchProductos(forceRefresh: true),
                            child: ListView(
                              physics: const AlwaysScrollableScrollPhysics(),
                              children: const [
                                SizedBox(height: 120),
                                Center(child: Text('No hay productos disponibles con estos filtros.')),
                              ],
                            ),
                          )
                        : RefreshIndicator(
                            onRefresh: () => productCtrl.fetchProductos(forceRefresh: true),
                            child: ListView.builder(
                              physics: const AlwaysScrollableScrollPhysics(),
                              padding: const EdgeInsets.all(12),
                              itemCount: productCtrl.catalogo.length,
                            itemBuilder: (ctx, i) {
                              final prod = productCtrl.catalogo[i];
                              final bool enStock = prod.disponible && prod.stockSucursal > 0;

                              return Card(
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                                elevation: 2,
                                margin: const EdgeInsets.symmetric(vertical: 7),
                                child: Padding(
                                  padding: const EdgeInsets.all(12),
                                  child: Row(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      // Imagen del producto
                                      ClipRRect(
                                        borderRadius: BorderRadius.circular(10),
                                        child: (prod.imagenprincipal != null && prod.imagenprincipal!.isNotEmpty)
                                            ? Image.network(
                                                prod.imagenprincipal!,
                                                width: 85,
                                                height: 95,
                                                fit: BoxFit.cover,
                                                errorBuilder: (_, __, ___) => Container(
                                                  width: 85,
                                                  height: 95,
                                                  color: Colors.grey[200],
                                                  child: const Icon(Icons.checkroom, color: Colors.grey),
                                                ),
                                              )
                                            : Container(
                                                width: 85,
                                                height: 95,
                                                color: Colors.grey[200],
                                                child: const Icon(Icons.checkroom, color: Colors.grey),
                                              ),
                                      ),
                                      const SizedBox(width: 14),

                                      // Detalles y Stock
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            if (prod.marca != null)
                                              Text(
                                                prod.marca!.toUpperCase(),
                                                style: TextStyle(
                                                  fontSize: 10,
                                                  fontWeight: FontWeight.bold,
                                                  letterSpacing: 0.5,
                                                  color: Colors.grey[600],
                                                ),
                                              ),
                                            Text(
                                              prod.nombre,
                                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                                              maxLines: 2,
                                              overflow: TextOverflow.ellipsis,
                                            ),
                                            const SizedBox(height: 4),
                                            Text(
                                              'Bs. ${prod.preciobase.toStringAsFixed(2)}',
                                              style: const TextStyle(
                                                fontSize: 16,
                                                fontWeight: FontWeight.w800,
                                                color: Color(0xFF0F172A),
                                              ),
                                            ),
                                            if (prod.coloresUnicos.isNotEmpty) ...[
                                              const SizedBox(height: 5),
                                              Wrap(
                                                spacing: 4,
                                                crossAxisAlignment: WrapCrossAlignment.center,
                                                children: [
                                                  Text(
                                                    'Colores:',
                                                    style: TextStyle(
                                                      fontSize: 10.5,
                                                      fontWeight: FontWeight.bold,
                                                      color: Colors.grey[600],
                                                    ),
                                                  ),
                                                  ...prod.coloresUnicos.map((col) {
                                                    return Container(
                                                      width: 13,
                                                      height: 13,
                                                      decoration: BoxDecoration(
                                                        color: _colorFromHex(col['hex'] ?? '#000000'),
                                                        shape: BoxShape.circle,
                                                        border: Border.all(color: Colors.grey.shade400, width: 0.8),
                                                      ),
                                                    );
                                                  }),
                                                ],
                                              ),
                                            ],
                                            const SizedBox(height: 6),

                                            // Badge de disponibilidad por tienda
                                            Container(
                                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                              decoration: BoxDecoration(
                                                color: enStock ? const Color(0xFFDCFCE7) : const Color(0xFFFEE2E2),
                                                borderRadius: BorderRadius.circular(6),
                                              ),
                                              child: Row(
                                                mainAxisSize: MainAxisSize.min,
                                                children: [
                                                  Icon(
                                                    enStock ? Icons.check_circle : Icons.cancel,
                                                    size: 14,
                                                    color: enStock ? const Color(0xFF16A34A) : const Color(0xFFDC2626),
                                                  ),
                                                  const SizedBox(width: 4),
                                                  Text(
                                                    enStock
                                                        ? 'Stock en tienda: ${prod.stockSucursal} uds'
                                                        : 'Agotado en esta tienda',
                                                    style: TextStyle(
                                                      fontSize: 11,
                                                      fontWeight: FontWeight.w600,
                                                      color: enStock ? const Color(0xFF16A34A) : const Color(0xFFDC2626),
                                                    ),
                                                  ),
                                                ],
                                              ),
                                            ),
                                            const SizedBox(height: 10),

                                            // Botones de Acción: CU12 (Vestidor Virtual), CU08 (Otras tiendas) y Agregar
                                            Wrap(
                                              alignment: WrapAlignment.end,
                                              crossAxisAlignment: WrapCrossAlignment.center,
                                              spacing: 6,
                                              runSpacing: 6,
                                              children: [
                                                // Botón CU12: Vestidor Virtual
                                                SizedBox(
                                                  height: 32,
                                                  child: OutlinedButton.icon(
                                                    style: OutlinedButton.styleFrom(
                                                      padding: const EdgeInsets.symmetric(horizontal: 7),
                                                      side: const BorderSide(color: Color(0xFF6366F1), width: 1.2),
                                                      foregroundColor: const Color(0xFF4F46E5),
                                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                                    ),
                                                    icon: const Icon(Icons.checkroom, size: 13, color: Color(0xFF4F46E5)),
                                                    label: const Text('Vestidor', style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold)),
                                                    onPressed: () {
                                                      final pmodel = ProductModel(
                                                        id: prod.id,
                                                        nombre: prod.nombre,
                                                        descripcion: prod.descripcion,
                                                        precio: prod.preciobase,
                                                        stock: prod.stockSucursal,
                                                        imagenUrl: prod.imagenprincipal,
                                                        activo: prod.disponible,
                                                      );
                                                      Navigator.push(
                                                        context,
                                                        MaterialPageRoute(
                                                          builder: (_) => VirtualFittingRoomView(producto: pmodel),
                                                        ),
                                                      );
                                                    },
                                                  ),
                                                ),

                                                // Botón Consultar Otras Tiendas
                                                SizedBox(
                                                  height: 32,
                                                  child: OutlinedButton.icon(
                                                    style: OutlinedButton.styleFrom(
                                                      padding: const EdgeInsets.symmetric(horizontal: 7),
                                                      side: const BorderSide(color: Color(0xFFCBD5E1)),
                                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                                    ),
                                                    icon: const Icon(Icons.storefront, size: 13, color: Color(0xFF0F172A)),
                                                    label: const Text('Tiendas', style: TextStyle(fontSize: 10.5, color: Color(0xFF0F172A))),
                                                    onPressed: () => _mostrarDisponibilidadModal(context, prod),
                                                  ),
                                                ),

                                                // Botón Agregar
                                                SizedBox(
                                                  height: 32,
                                                  child: ElevatedButton.icon(
                                                    style: ElevatedButton.styleFrom(
                                                      backgroundColor: const Color(0xFF0F172A),
                                                      foregroundColor: Colors.white,
                                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                                      padding: const EdgeInsets.symmetric(horizontal: 8),
                                                    ),
                                                    icon: const Icon(Icons.add_shopping_cart, size: 13),
                                                    label: Text(enStock ? 'Agregar' : 'Agotado', style: const TextStyle(fontSize: 10.5)),
                                                    onPressed: enStock
                                                        ? () {
                                                            if (prod.variantes.length > 1) {
                                                              _mostrarSelectorVariantesModal(context, prod, cartCtrl);
                                                            } else {
                                                              final v = prod.variantes.isNotEmpty ? prod.variantes.first : null;
                                                              final pmodel = ProductModel(
                                                                id: prod.id,
                                                                nombre: prod.nombre,
                                                                descripcion: prod.descripcion,
                                                                precio: prod.preciobase,
                                                                stock: prod.stockSucursal,
                                                                imagenUrl: prod.imagenprincipal,
                                                                activo: prod.disponible,
                                                                varianteId: v?.varianteId,
                                                                colorSeleccionado: v?.color,
                                                                tallaSeleccionada: v?.talla,
                                                                hexSeleccionado: v?.codigohex,
                                                              );
                                                              cartCtrl.agregarProducto(pmodel);
                                                              ScaffoldMessenger.of(context).showSnackBar(
                                                                SnackBar(
                                                                  content: Text('${prod.nombre} añadido al carrito'),
                                                                  duration: const Duration(milliseconds: 900),
                                                                  backgroundColor: const Color(0xFF0F172A),
                                                                ),
                                                              );
                                                            }
                                                          }
                                                        : null,
                                                  ),
                                                ),

                                                // Botón Reservar Directo (Funciona Online y Sin Internet)
                                                if (enStock)
                                                  SizedBox(
                                                    height: 32,
                                                    child: ElevatedButton.icon(
                                                      style: ElevatedButton.styleFrom(
                                                        backgroundColor: const Color(0xFF0284C7),
                                                        foregroundColor: Colors.white,
                                                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                                        padding: const EdgeInsets.symmetric(horizontal: 8),
                                                      ),
                                                      icon: const Icon(Icons.bookmark_add, size: 13),
                                                      label: const Text('Reservar', style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold)),
                                                      onPressed: () {
                                                        if (prod.variantes.length > 1) {
                                                          _mostrarSelectorVariantesModal(context, prod, cartCtrl);
                                                        } else {
                                                          final v = prod.variantes.isNotEmpty ? prod.variantes.first : null;
                                                          final pmodel = ProductModel(
                                                            id: prod.id,
                                                            nombre: prod.nombre,
                                                            descripcion: prod.descripcion,
                                                            precio: prod.preciobase,
                                                            stock: prod.stockSucursal,
                                                            imagenUrl: prod.imagenprincipal,
                                                            activo: prod.disponible,
                                                            varianteId: v?.varianteId,
                                                            colorSeleccionado: v?.color,
                                                            tallaSeleccionada: v?.talla,
                                                            hexSeleccionado: v?.codigohex,
                                                          );
                                                          cartCtrl.agregarProducto(pmodel);
                                                          Navigator.pushNamed(context, '/cart');
                                                        }
                                                      },
                                                    ),
                                                  ),
                                              ],
                                            ),
                                          ],
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
          ),
        ],
      ),
    );
  }

  /// CU08: Modal interactivo que consulta la disponibilidad multitienda en tiempo real
  void _mostrarDisponibilidadModal(BuildContext context, CatalogProductModel prod) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return Container(
          height: MediaQuery.of(context).size.height * 0.72,
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Column(
            children: [
              Container(
                margin: const EdgeInsets.only(top: 12, bottom: 8),
                width: 40,
                height: 5,
                decoration: BoxDecoration(
                  color: Colors.grey[300],
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                child: Row(
                  children: [
                    const Icon(Icons.storefront, color: Color(0xFF0F172A), size: 26),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            prod.nombre,
                            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          const Text(
                            'Disponibilidad en Tiendas Físicas (CU08)',
                            style: TextStyle(fontSize: 12, color: Colors.grey),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.pop(ctx),
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              Expanded(
                child: FutureBuilder<ProductAvailabilityModel?>(
                  future: context.read<ProductController>().fetchDisponibilidadProducto(prod.id),
                  builder: (context, snapshot) {
                    if (snapshot.connectionState == ConnectionState.waiting) {
                      return const Center(child: CircularProgressIndicator());
                    }
                    if (snapshot.hasError || snapshot.data == null) {
                      return const Center(
                        child: Text('No se pudo cargar la disponibilidad en otras tiendas.'),
                      );
                    }
                    final disp = snapshot.data!;
                    return ListView.separated(
                      padding: const EdgeInsets.all(16),
                      itemCount: disp.sucursales.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 12),
                      itemBuilder: (context, index) {
                        final suc = disp.sucursales[index];
                        final bool hasStock = suc.stockTotal > 0;
                        return Container(
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: const Color(0xFFF8FAFC),
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(
                              color: hasStock ? const Color(0xFFCBD5E1) : const Color(0xFFF1F5F9),
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Expanded(
                                    child: Row(
                                      children: [
                                        Icon(
                                          Icons.store,
                                          size: 18,
                                          color: hasStock ? const Color(0xFF0F172A) : Colors.grey,
                                        ),
                                        const SizedBox(width: 8),
                                        Expanded(
                                          child: Text(
                                            '${suc.sucursalNombre} (${suc.ciudad ?? "Bolivia"})',
                                            style: TextStyle(
                                              fontWeight: FontWeight.bold,
                                              fontSize: 14,
                                              color: hasStock ? const Color(0xFF0F172A) : Colors.grey,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                    decoration: BoxDecoration(
                                      color: hasStock ? const Color(0xFFDCFCE7) : const Color(0xFFFEE2E2),
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Text(
                                      hasStock ? '${suc.stockTotal} disponibles' : 'Agotado',
                                      style: TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.bold,
                                        color: hasStock ? const Color(0xFF16A34A) : const Color(0xFFDC2626),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              if (suc.direccion != null) ...[
                                const SizedBox(height: 4),
                                Text(
                                  suc.direccion!,
                                  style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                                ),
                              ],
                              if (hasStock && suc.variantes.isNotEmpty) ...[
                                const SizedBox(height: 10),
                                Wrap(
                                  spacing: 6,
                                  runSpacing: 6,
                                  children: suc.variantes.where((v) => v.stock > 0).map((v) {
                                    return Chip(
                                      labelPadding: const EdgeInsets.symmetric(horizontal: 4),
                                      visualDensity: VisualDensity.compact,
                                      label: Text(
                                        '${v.talla ?? "M"} - ${v.color ?? "Color"} (${v.stock} uds)',
                                        style: const TextStyle(fontSize: 11),
                                      ),
                                      backgroundColor: Colors.white,
                                      side: const BorderSide(color: Color(0xFFE2E8F0)),
                                    );
                                  }).toList(),
                                ),
                              ],
                            ],
                          ),
                        );
                      },
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  void _mostrarNotificacionesSheet(BuildContext context) {
    final notifCtrl = Provider.of<NotificationController>(context, listen: false);
    final auth = Provider.of<AuthController>(context, listen: false);
    final prodCtrl = Provider.of<ProductController>(context, listen: false);
    notifCtrl.fetchNotificaciones(
      auth.currentUser?.token,
      tenantId: prodCtrl.empresaSeleccionadaId,
    );

    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return Consumer<NotificationController>(
          builder: (_, ctrl, __) {
            return Container(
              padding: const EdgeInsets.all(16),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.notifications, color: Color(0xFF0F172A)),
                          SizedBox(width: 8),
                          Text('Notificaciones (CU19)', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                        ],
                      ),
                      if (ctrl.notificaciones.isNotEmpty)
                        TextButton(
                          onPressed: () => ctrl.marcarTodasLeidas(
                            auth.currentUser?.token,
                            tenantId: prodCtrl.empresaSeleccionadaId,
                          ),
                          child: const Text('Marcar leídas', style: TextStyle(fontSize: 12)),
                        ),
                    ],
                  ),
                  const Divider(),
                  if (ctrl.cargando && ctrl.notificaciones.isEmpty)
                    const Center(child: Padding(padding: EdgeInsets.all(20), child: CircularProgressIndicator()))
                  else if (ctrl.notificaciones.isEmpty)
                    const Padding(
                      padding: EdgeInsets.all(30),
                      child: Center(
                        child: Text('No tienes notificaciones pendientes', style: TextStyle(color: Colors.grey)),
                      ),
                    )
                  else
                    Flexible(
                      child: ListView.builder(
                        shrinkWrap: true,
                        itemCount: ctrl.notificaciones.length,
                        itemBuilder: (_, i) {
                          final n = ctrl.notificaciones[i];
                          final esCompra = n.tipo == 'COMPRA_EXITOSA' || n.titulo.contains('Compra');
                          final esReserva = n.tipo == 'RESERVA_EXITOSA' || n.titulo.contains('Reserva') || n.titulo.contains('Apartado');
                          return Container(
                            margin: const EdgeInsets.symmetric(vertical: 3),
                            decoration: BoxDecoration(
                              color: n.leido ? Colors.transparent : const Color(0xFFF0FDF4),
                              borderRadius: BorderRadius.circular(10),
                              border: n.leido ? null : Border.all(color: Colors.green.shade200),
                            ),
                            child: ListTile(
                              contentPadding: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
                              leading: CircleAvatar(
                                backgroundColor: esCompra
                                    ? Colors.green.shade100
                                    : (esReserva
                                        ? Colors.teal.shade100
                                        : (n.tipo == 'RESERVA_EXPIRANDO'
                                            ? Colors.orange.shade100
                                            : (n.tipo == 'STOCK_CRITICO' ? Colors.red.shade100 : Colors.blue.shade100))),
                                child: Icon(
                                  esCompra
                                      ? Icons.shopping_bag
                                      : (esReserva
                                          ? Icons.bookmark_added
                                          : (n.tipo == 'RESERVA_EXPIRANDO'
                                              ? Icons.timer
                                              : (n.tipo == 'STOCK_CRITICO' ? Icons.warning : Icons.info_outline))),
                                  color: esCompra
                                      ? Colors.green.shade800
                                      : (esReserva
                                          ? Colors.teal.shade800
                                          : (n.tipo == 'RESERVA_EXPIRANDO'
                                              ? Colors.orange.shade900
                                              : (n.tipo == 'STOCK_CRITICO' ? Colors.red.shade900 : Colors.blue.shade900))),
                                  size: 20,
                                ),
                              ),
                              title: Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      n.titulo,
                                      style: TextStyle(
                                        fontWeight: n.leido ? FontWeight.w600 : FontWeight.w800,
                                        fontSize: 13,
                                      ),
                                    ),
                                  ),
                                  if (!n.leido)
                                    Container(
                                      width: 8,
                                      height: 8,
                                      decoration: const BoxDecoration(
                                        color: Colors.green,
                                        shape: BoxShape.circle,
                                      ),
                                    ),
                                ],
                              ),
                              subtitle: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const SizedBox(height: 2),
                                  Text(n.mensaje, style: const TextStyle(fontSize: 12)),
                                  if (n.fecha.isNotEmpty)
                                    Padding(
                                      padding: const EdgeInsets.only(top: 3),
                                      child: Text(n.fecha, style: const TextStyle(fontSize: 10, color: Colors.grey)),
                                    ),
                                ],
                              ),
                              onTap: () {
                                ctrl.marcarLeida(
                                  n.id,
                                  auth.currentUser?.token,
                                  tenantId: prodCtrl.empresaSeleccionadaId,
                                );
                                Navigator.pop(ctx);
                                if (n.enlace == '/mis-reservas') {
                                  Navigator.push(context, MaterialPageRoute(builder: (_) => const MyReservationsView()));
                                } else if (n.enlace == '/mis-pedidos' || esCompra) {
                                  Navigator.push(context, MaterialPageRoute(builder: (_) => const OrdersHistoryView()));
                                }
                              },
                            ),
                          );
                        },
                      ),
                    ),
                ],
              ),
            );
          },
        );
      },
    );
  }
  static Color _colorFromHex(String hex) {
    try {
      String clean = hex.replaceAll('#', '').trim();
      if (clean.length == 6) clean = 'FF$clean';
      return Color(int.parse(clean, radix: 16));
    } catch (_) {
      return const Color(0xFF0F172A);
    }
  }

  void _mostrarSelectorVariantesModal(
    BuildContext context,
    CatalogProductModel prod,
    CartController cartCtrl,
  ) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => _SelectorVarianteSheet(prod: prod, cartCtrl: cartCtrl),
    );
  }
}

class _SelectorVarianteSheet extends StatefulWidget {
  final CatalogProductModel prod;
  final CartController cartCtrl;

  const _SelectorVarianteSheet({
    required this.prod,
    required this.cartCtrl,
  });

  @override
  State<_SelectorVarianteSheet> createState() => _SelectorVarianteSheetState();
}

class _SelectorVarianteSheetState extends State<_SelectorVarianteSheet> {
  late ProductVariantModel _selectedVariant;

  @override
  void initState() {
    super.initState();
    final conStock = widget.prod.variantes.where((v) => v.stock > 0).toList();
    _selectedVariant = conStock.isNotEmpty ? conStock.first : widget.prod.variantes.first;
  }

  @override
  Widget build(BuildContext context) {
    final tieneStock = _selectedVariant.stock > 0;

    return Container(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.only(bottom: 16),
              decoration: BoxDecoration(
                color: Colors.grey[300],
                borderRadius: BorderRadius.circular(10),
              ),
            ),
          ),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: widget.prod.imagenprincipal != null
                    ? Image.network(
                        widget.prod.imagenprincipal!,
                        width: 70,
                        height: 80,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => Container(
                          width: 70,
                          height: 80,
                          color: Colors.grey[200],
                          child: const Icon(Icons.checkroom),
                        ),
                      )
                    : Container(
                        width: 70,
                        height: 80,
                        color: Colors.grey[200],
                        child: const Icon(Icons.checkroom),
                      ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.prod.nombre,
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Bs. ${widget.prod.preciobase.toStringAsFixed(2)}',
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF0F172A),
                      ),
                    ),
                    const SizedBox(height: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: tieneStock ? const Color(0xFFDCFCE7) : const Color(0xFFFEE2E2),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        tieneStock
                            ? '${_selectedVariant.stock} disponibles en esta tienda'
                            : 'Agotado en esta tienda',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: tieneStock ? const Color(0xFF16A34A) : const Color(0xFFDC2626),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const Divider(height: 28),
          const Text(
            'Elige Color y Talla:',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Color(0xFF0F172A)),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: widget.prod.variantes.map((v) {
              final isSelected = v.varianteId == _selectedVariant.varianteId;
              final colHex = v.codigohex ?? '#000000';
              final conExistencia = v.stock > 0;

              return InkWell(
                borderRadius: BorderRadius.circular(10),
                onTap: () {
                  setState(() {
                    _selectedVariant = v;
                  });
                },
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 180),
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
                  decoration: BoxDecoration(
                    color: isSelected ? const Color(0xFF0F172A) : Colors.grey[50],
                    border: Border.all(
                      color: isSelected
                          ? const Color(0xFF0F172A)
                          : (conExistencia ? Colors.grey.shade300 : Colors.red.shade200),
                      width: isSelected ? 1.8 : 1.0,
                    ),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 14,
                        height: 14,
                        decoration: BoxDecoration(
                          color: _ProductListViewState._colorFromHex(colHex),
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: isSelected ? Colors.white : Colors.grey.shade400,
                            width: 1,
                          ),
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        '${v.color ?? "Color"} • ${v.talla ?? "M"}',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                          color: isSelected ? Colors.white : Colors.black87,
                        ),
                      ),
                      const SizedBox(width: 4),
                      Text(
                        conExistencia ? '(${v.stock})' : '(0)',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: isSelected
                              ? (conExistencia ? Colors.greenAccent : Colors.redAccent)
                              : (conExistencia ? Colors.green[700] : Colors.red),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            height: 46,
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: tieneStock ? const Color(0xFF0F172A) : Colors.grey[400],
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              icon: Icon(tieneStock ? Icons.shopping_bag_outlined : Icons.block, size: 18),
              label: Text(
                tieneStock
                    ? 'Añadir al Carrito (${_selectedVariant.color} - ${_selectedVariant.talla})'
                    : 'Agotado en esta combinación',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13.5),
              ),
              onPressed: tieneStock
                  ? () {
                      final pmodel = ProductModel(
                        id: widget.prod.id,
                        nombre: widget.prod.nombre,
                        descripcion: widget.prod.descripcion,
                        precio: widget.prod.preciobase,
                        stock: _selectedVariant.stock,
                        imagenUrl: widget.prod.imagenprincipal,
                        activo: widget.prod.disponible,
                        varianteId: _selectedVariant.varianteId,
                        colorSeleccionado: _selectedVariant.color,
                        tallaSeleccionada: _selectedVariant.talla,
                        hexSeleccionado: _selectedVariant.codigohex,
                      );
                      widget.cartCtrl.agregarProducto(pmodel);
                      Navigator.pop(context);
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            '${widget.prod.nombre} (${_selectedVariant.color} - ${_selectedVariant.talla}) añadido al carrito',
                          ),
                          backgroundColor: const Color(0xFF0F172A),
                          duration: const Duration(seconds: 2),
                        ),
                      );
                    }
                  : null,
            ),
          ),
          if (tieneStock) ...[
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              height: 46,
              child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF0284C7),
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                icon: const Icon(Icons.bookmark_add, size: 18),
                label: Text(
                  'Reservar Ahora (${_selectedVariant.color} - ${_selectedVariant.talla})',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13.5),
                ),
                onPressed: () {
                  final pmodel = ProductModel(
                    id: widget.prod.id,
                    nombre: widget.prod.nombre,
                    descripcion: widget.prod.descripcion,
                    precio: widget.prod.preciobase,
                    stock: _selectedVariant.stock,
                    imagenUrl: widget.prod.imagenprincipal,
                    activo: widget.prod.disponible,
                    varianteId: _selectedVariant.varianteId,
                    colorSeleccionado: _selectedVariant.color,
                    tallaSeleccionada: _selectedVariant.talla,
                    hexSeleccionado: _selectedVariant.codigohex,
                  );
                  widget.cartCtrl.agregarProducto(pmodel);
                  Navigator.pop(context);
                  Navigator.pushNamed(context, '/cart');
                },
              ),
            ),
          ],
        ],
      ),
    );
  }
}
