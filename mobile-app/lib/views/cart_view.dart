// ==============================================================================
// CAPA VISTA (MVC - VIEW EN FLUTTER / DART)
// Pantalla de Carrito de Compras (CU09 & CU15)
// Ubicación: mobile-app/lib/views/cart_view.dart
// ==============================================================================

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../controllers/cart_controller.dart';
import '../controllers/auth_controller.dart';
import '../controllers/reservation_controller.dart';
import '../controllers/payment_controller.dart';
import '../controllers/recommendation_controller.dart';
import '../controllers/notification_controller.dart';
import '../controllers/product_controller.dart';
import '../controllers/order_controller.dart';
import '../widgets/simulated_qr_widget.dart';
import 'my_reservations_view.dart';
import 'orders_history_view.dart';

class CartView extends StatefulWidget {
  const CartView({super.key});

  @override
  State<CartView> createState() => _CartViewState();
}

class _CartViewState extends State<CartView> {
  int _metodoPagoSeleccionado = 5; // 5: PayPal, 2: Tarjeta Visa, 3: QR Simple

  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      if (!mounted) return;
      final cart = context.read<CartController>();
      if (cart.items.isNotEmpty) {
        context.read<RecommendationController>().fetchRecomendaciones(
          carritoIds: cart.productIds,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final cartCtrl = Provider.of<CartController>(context);
    final productCtrl = Provider.of<ProductController>(context);
    final authCtrl = Provider.of<AuthController>(context, listen: false);
    final resCtrl = Provider.of<ReservationController>(context, listen: false);
    final payCtrl = Provider.of<PaymentController>(context, listen: false);
    final sucursalActivaNombre =
        cartCtrl.sucursalNombre ?? productCtrl.sucursalActual?.nombre ?? 'Sucursal Central';
    final sucursalActivaId =
        cartCtrl.sucursalId ?? productCtrl.sucursalSeleccionadaId ?? productCtrl.sucursalActual?.id ?? 1;

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text('🛒 Carrito de Compras'),
        backgroundColor: const Color(0xFF0F172A),
        foregroundColor: Colors.white,
        elevation: 2,
        actions: [
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
          IconButton(
            icon: const Icon(Icons.receipt_long),
            tooltip: 'Historial de Pedidos (CU15)',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const OrdersHistoryView()),
              );
            },
          ),
          if (cartCtrl.items.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.delete_sweep),
              tooltip: 'Vaciar Carrito',
              onPressed: () {
                showDialog(
                  context: context,
                  builder: (ctx) => AlertDialog(
                    title: const Text('¿Vaciar carrito?'),
                    content: const Text('Se eliminarán todas las prendas seleccionadas.'),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.pop(ctx),
                        child: const Text('Cancelar'),
                      ),
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
                        onPressed: () {
                          cartCtrl.limpiarCarrito();
                          Navigator.pop(ctx);
                        },
                        child: const Text('Vaciar'),
                      ),
                    ],
                  ),
                );
              },
            ),
        ],
      ),
      body: cartCtrl.items.isEmpty
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.remove_shopping_cart_outlined, size: 70, color: Colors.grey),
                  const SizedBox(height: 16),
                  const Text(
                    'Tu carrito está vacío',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Añade prendas desde el catálogo para continuar.',
                    style: TextStyle(color: Colors.grey),
                  ),
                  const SizedBox(height: 20),
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF0F172A),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                    ),
                    icon: const Icon(Icons.arrow_back),
                    label: const Text('Volver al Catálogo'),
                    onPressed: () => Navigator.pop(context),
                  )
                ],
              ),
            )
          : Column(
              children: [
                // Lista de Prendas
                Expanded(
                  child: ListView.builder(
                    padding: const EdgeInsets.all(12),
                    itemCount: cartCtrl.items.length,
                    itemBuilder: (ctx, i) {
                      final item = cartCtrl.items.values.toList()[i];
                      return Card(
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                        margin: const EdgeInsets.symmetric(vertical: 6),
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Row(
                            children: [
                              ClipRRect(
                                borderRadius: BorderRadius.circular(8),
                                child: item.product.imagenUrl != null
                                    ? Image.network(
                                        item.product.imagenUrl!,
                                        width: 65,
                                        height: 75,
                                        fit: BoxFit.cover,
                                        errorBuilder: (_, __, ___) => Container(
                                          width: 65,
                                          height: 75,
                                          color: Colors.grey[200],
                                          child: const Icon(Icons.image_not_supported),
                                        ),
                                      )
                                    : Container(
                                        width: 65,
                                        height: 75,
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
                                      item.product.nombre,
                                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      'Bs. ${item.product.precio.toStringAsFixed(2)} c/u',
                                      style: const TextStyle(color: Colors.grey, fontSize: 12),
                                    ),
                                    if (item.product.colorSeleccionado != null) ...[
                                      const SizedBox(height: 3),
                                      Row(
                                        children: [
                                          if (item.product.hexSeleccionado != null)
                                            Container(
                                              width: 10,
                                              height: 10,
                                              margin: const EdgeInsets.only(right: 5),
                                              decoration: BoxDecoration(
                                                color: _hexToColorSeguro(item.product.hexSeleccionado!),
                                                shape: BoxShape.circle,
                                                border: Border.all(color: Colors.grey.shade400, width: 0.8),
                                              ),
                                            ),
                                          Text(
                                            '${item.product.colorSeleccionado} • Talla ${item.product.tallaSeleccionada ?? "M"}',
                                            style: TextStyle(
                                              fontSize: 11,
                                              fontWeight: FontWeight.w600,
                                              color: Colors.grey[700],
                                            ),
                                          ),
                                        ],
                                      ),
                                    ],
                                    const SizedBox(height: 8),

                                    // Controles Stepper + y -
                                    Row(
                                      children: [
                                        Container(
                                          decoration: BoxDecoration(
                                            border: Border.all(color: Colors.grey.shade300),
                                            borderRadius: BorderRadius.circular(8),
                                          ),
                                          child: Row(
                                            children: [
                                              InkWell(
                                                onTap: () => cartCtrl.decrementar(item.product.id),
                                                child: const Padding(
                                                  padding: EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                                  child: Icon(Icons.remove, size: 16),
                                                ),
                                              ),
                                              Text(
                                                '${item.cantidad}',
                                                style: const TextStyle(fontWeight: FontWeight.bold),
                                              ),
                                              InkWell(
                                                onTap: () {
                                                  final ok = cartCtrl.incrementar(item.product.id);
                                                  if (!ok) {
                                                    ScaffoldMessenger.of(context).hideCurrentSnackBar();
                                                    ScaffoldMessenger.of(context).showSnackBar(
                                                      SnackBar(
                                                        content: Text('Límite de stock alcanzado (${item.product.stock} uds. disponibles)'),
                                                        backgroundColor: Colors.orange.shade800,
                                                        duration: const Duration(seconds: 2),
                                                      ),
                                                    );
                                                  }
                                                },
                                                child: const Padding(
                                                  padding: EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                                  child: Icon(Icons.add, size: 16),
                                                ),
                                              ),
                                            ],
                                          ),
                                        ),
                                        const Spacer(),
                                        Text(
                                          'Bs. ${item.subtotal.toStringAsFixed(2)}',
                                          style: const TextStyle(
                                            fontWeight: FontWeight.bold,
                                            fontSize: 15,
                                            color: Color(0xFF0F172A),
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

                // CU18: Recomendaciones Stylist IA (Completa tu Outfit)
                Consumer<RecommendationController>(
                  builder: (_, recCtrl, __) {
                    if (recCtrl.recomendaciones.isEmpty) return const SizedBox.shrink();
                    return Container(
                      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: const Color(0xFFFAF5FF),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xFFE9D5FF)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Row(
                                children: [
                                  const Icon(Icons.auto_awesome, color: Color(0xFF7E22CE), size: 16),
                                  const SizedBox(width: 6),
                                  Text(
                                    'Stylist IA: Completa tu Outfit',
                                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Colors.purple.shade900),
                                  ),
                                ],
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(color: Colors.purple.shade700, borderRadius: BorderRadius.circular(8)),
                                child: const Text('CU18 Gemini', style: TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.bold)),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          SizedBox(
                            height: 80,
                            child: ListView.builder(
                              scrollDirection: Axis.horizontal,
                              itemCount: recCtrl.recomendaciones.length,
                              itemBuilder: (ctx, idx) {
                                final rec = recCtrl.recomendaciones[idx];
                                return Container(
                                  width: 180,
                                  margin: const EdgeInsets.only(right: 8),
                                  padding: const EdgeInsets.all(8),
                                  decoration: BoxDecoration(
                                    color: Colors.white,
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(color: const Color(0xFFF3E8FF)),
                                  ),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Text(
                                        rec.nombre,
                                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 11),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                      Text(
                                        rec.razonEstilo,
                                        style: TextStyle(fontSize: 9, color: Colors.purple.shade800),
                                        maxLines: 2,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                      Text(
                                        'Bs. ${rec.precio.toStringAsFixed(2)}',
                                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: Color(0xFF7E22CE)),
                                      ),
                                    ],
                                  ),
                                );
                              },
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),

                // Panel Inferior de Checkout / Reserva
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: const BoxDecoration(
                    color: Colors.white,
                    boxShadow: [
                      BoxShadow(
                        color: Color(0x0F000000),
                        offset: Offset(0, -4),
                        blurRadius: 10,
                      )
                    ],
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Selector de Sucursal para Retiro / Reserva (Dinámico por Empresa)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        margin: const EdgeInsets.only(bottom: 12),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF8FAFC),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: const Color(0xFFE2E8F0)),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.storefront, size: 20, color: Color(0xFF0F172A)),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'SUCURSAL DE RETIRO (${productCtrl.empresaActual.nombre.toUpperCase()})',
                                    style: const TextStyle(fontSize: 10, color: Colors.grey, fontWeight: FontWeight.w700, letterSpacing: 0.5),
                                  ),
                                  Text(
                                    sucursalActivaNombre,
                                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                                  ),
                                ],
                              ),
                            ),
                            if (productCtrl.sucursales.isNotEmpty)
                              PopupMenuButton<int>(
                                tooltip: 'Cambiar Sucursal',
                                icon: const Icon(Icons.swap_horiz, color: Color(0xFF0F172A)),
                                onSelected: (id) {
                                  final suc = productCtrl.sucursales.where((s) => s.id == id).toList();
                                  if (suc.isNotEmpty) {
                                    cartCtrl.setSucursal(id, suc.first.nombre);
                                    productCtrl.seleccionarSucursal(id);
                                  }
                                },
                                itemBuilder: (ctx) => productCtrl.sucursales
                                    .map((s) => PopupMenuItem<int>(
                                          value: s.id,
                                          child: Text(s.nombre),
                                        ))
                                    .toList(),
                              ),
                          ],
                        ),
                      ),

                      // Selector de Método de Pago (CU16 - PayPal, QR, Efectivo)
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'MÉTODO DE PAGO:',
                            style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.grey, letterSpacing: 0.5),
                          ),
                          const SizedBox(height: 6),
                          Row(
                            children: [
                              _buildMetodoChip(5, 'PayPal', Icons.payment, const Color(0xFF003087)),
                              const SizedBox(width: 6),
                              _buildMetodoChip(2, 'Tarjeta Visa', Icons.credit_card, const Color(0xFF1E3A8A)),
                              const SizedBox(width: 6),
                              _buildMetodoChip(3, 'QR Simple', Icons.qr_code_2, const Color(0xFF6D28D9)),
                            ],
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),

                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text(
                            'TOTAL:',
                            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.grey),
                          ),
                          Text(
                            'Bs. ${cartCtrl.totalMonto.toStringAsFixed(2)}',
                            style: const TextStyle(
                              fontSize: 22,
                              fontWeight: FontWeight.w800,
                              color: Color(0xFF0F172A),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),

                      // Botón 1: Comprar Online (CU15 & CU16)
                      SizedBox(
                        width: double.infinity,
                        height: 46,
                        child: ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFFE11D48),
                            foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          ),
                          icon: const Icon(Icons.payment),
                          label: const Text('Pagar', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                          onPressed: () async {
                            if (!authCtrl.isAuthenticated) {
                              await authCtrl.loginInvitadoEmpresa(
                                tenantId: productCtrl.empresaSeleccionadaId,
                                empresaNombre: productCtrl.empresaActual.nombre,
                              );
                            }

                            // Extraer datos de la compra antes de procesar
                            final nombresPrendas = cartCtrl.items.values.map((it) => it.product.nombre).toList();
                            final double totalCompra = cartCtrl.totalMonto;
                            final String resumenPrendas = nombresPrendas.take(2).join(', ') +
                                (nombresPrendas.length > 2 ? ' y ${nombresPrendas.length - 2} prendas más' : '');

                            showDialog(
                              context: context,
                              barrierDismissible: false,
                              builder: (_) => const Center(child: CircularProgressIndicator()),
                            );

                            final order = await cartCtrl.procesarCompra(
                              "Av. Principal #123, Santa Cruz",
                              authToken: authCtrl.currentUser?.token,
                              metodoId: _metodoPagoSeleccionado,
                              sucursalIdOverride: sucursalActivaId,
                              tenantId: productCtrl.empresaSeleccionadaId,
                            );

                            if (!context.mounted) return;
                            Navigator.pop(context); // Cerrar spinner

                            if (order != null && order['id'] != null) {
                              final ventaId = order['id'] as int;
                              final codigoVenta = order['codigoventa'] ?? 'ORD-$ventaId';

                              // Registrar orden y notificación inmediatamente en el móvil
                              try {
                                final orderCtrl = Provider.of<OrderController>(context, listen: false);
                                await orderCtrl.registrarOrdenLocal(
                                  order,
                                  tenantId: productCtrl.empresaSeleccionadaId,
                                );
                                final notifCtrl = Provider.of<NotificationController>(context, listen: false);
                                final metodoLabel = _metodoPagoSeleccionado == 5
                                    ? 'PayPal'
                                    : (_metodoPagoSeleccionado == 2 ? 'Tarjeta Visa' : 'QR Simple');
                                await notifCtrl.agregarNotificacion(
                                  titulo: '🛍️ ¡Compra Realizada! #$codigoVenta',
                                  mensaje:
                                      'Compra registrada en ${productCtrl.empresaActual.nombre}: $resumenPrendas por Bs. ${totalCompra.toStringAsFixed(2)} ($metodoLabel).',
                                  tipo: 'COMPRA_EXITOSA',
                                  enlace: '/mis-pedidos',
                                  tenantId: productCtrl.empresaSeleccionadaId,
                                );
                                HapticFeedback.mediumImpact();
                              } catch (_) {}

                              final pagoInfo = await payCtrl.iniciarPago(
                                ventaId: ventaId,
                                metodoId: _metodoPagoSeleccionado,
                                token: authCtrl.currentUser?.token,
                              );

                              if (!context.mounted) return;

                              if (_metodoPagoSeleccionado == 5) {
                                _mostrarDialogoPayPal(context, ventaId, codigoVenta, resumenPrendas, totalCompra, pagoInfo, payCtrl);
                              } else if (_metodoPagoSeleccionado == 2) {
                                _mostrarDialogoTarjeta(context, ventaId, codigoVenta, resumenPrendas, totalCompra, pagoInfo, payCtrl);
                              } else {
                                _mostrarDialogoQR(context, ventaId, codigoVenta, resumenPrendas, totalCompra, pagoInfo, payCtrl);
                              }
                            } else {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text('No se pudo procesar la orden. Verifica stock o conexión.'),
                                  backgroundColor: Colors.red,
                                ),
                              );
                            }
                          },
                        ),
                      ),

                      const SizedBox(height: 10),

                      // Botón 2: Reservar en Sucursal Física (CU10 - Funciona Con y Sin Internet)
                      SizedBox(
                        width: double.infinity,
                        height: 48,
                        child: ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: productCtrl.usandoCacheOffline
                                ? const Color(0xFFD97706)
                                : const Color(0xFF0F172A),
                            foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          ),
                          icon: Icon(productCtrl.usandoCacheOffline ? Icons.wifi_off : Icons.storefront),
                          label: Text(
                            productCtrl.usandoCacheOffline
                                ? 'Guardar Reserva Offline (Sin Internet)'
                                : 'Apartar y Pagar en Tienda (CU10)',
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                          onPressed: () async {
                            if (!authCtrl.isAuthenticated) {
                              await authCtrl.loginInvitadoEmpresa(
                                tenantId: productCtrl.empresaSeleccionadaId,
                                empresaNombre: productCtrl.empresaActual.nombre,
                              );
                            }

                            // Extraer prendas completas para el apartado (Online u Offline)
                            final itemsPayload = cartCtrl.items.values.map((it) => {
                              'producto_id': it.product.id,
                              'variante_id': it.product.varianteId ?? 0,
                              'cantidad': it.cantidad,
                              'producto_nombre': it.product.nombre,
                              'talla': it.product.tallaSeleccionada ?? 'M',
                              'color': it.product.colorSeleccionado ?? 'Estándar',
                              'precio_unitario': it.product.precio,
                              'imagen_url': it.product.imagenUrl,
                            }).toList();
                            final nombresPrendas = cartCtrl.items.values.map((it) => it.product.nombre).toList();
                            final String resumenPrendas = nombresPrendas.take(2).join(', ') +
                                (nombresPrendas.length > 2 ? ' y ${nombresPrendas.length - 2} prendas más' : '');

                            showDialog(
                              context: context,
                              barrierDismissible: false,
                              builder: (_) => const Center(child: CircularProgressIndicator()),
                            );

                            final nuevaReserva = await resCtrl.crearReservaDesdeCarrito(
                              sucursalId: sucursalActivaId,
                              sucursalNombre: sucursalActivaNombre,
                              sucursalDireccion: productCtrl.sucursalActual?.direccion,
                              tenantId: productCtrl.empresaSeleccionadaId,
                              empresaNombre: productCtrl.empresaActual.nombre,
                              forzarOffline: productCtrl.modoOfflineSimulado,
                              items: itemsPayload,
                              token: authCtrl.currentUser?.token,
                            );

                            if (!context.mounted) return;
                            Navigator.pop(context); // Cerrar loading

                            if (nuevaReserva != null) {
                              if (!nuevaReserva.esOffline) {
                                try {
                                  context.read<ProductController>().fetchCatalogoConDisponibilidad(forceRefresh: true);
                                } catch (_) {}
                              }

                              // Notificación inmediata en móvil
                              try {
                                final notifCtrl = Provider.of<NotificationController>(context, listen: false);
                                await notifCtrl.agregarNotificacion(
                                  titulo: nuevaReserva.esOffline
                                      ? '📡 Reserva Offline Guardada #${nuevaReserva.codigoReserva}'
                                      : '🏪 ¡Apartado en Tienda! #${nuevaReserva.codigoReserva}',
                                  mensaje: nuevaReserva.esOffline
                                      ? 'Se guardó tu reserva de $resumenPrendas en la base local de tu teléfono. Se sincronizará automáticamente al reconectar internet.'
                                      : 'Has apartado exitosamente: $resumenPrendas. Código de retiro: #${nuevaReserva.codigoReserva}.',
                                  tipo: 'RESERVA_EXITOSA',
                                  enlace: '/mis-reservas',
                                  tenantId: productCtrl.empresaSeleccionadaId,
                                );
                                HapticFeedback.mediumImpact();
                              } catch (_) {}

                              cartCtrl.limpiarCarrito();
                              showDialog(
                                context: context,
                                builder: (ctx) => AlertDialog(
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                                  title: Row(
                                    children: [
                                      Icon(
                                        nuevaReserva.esOffline ? Icons.cloud_upload : Icons.check_circle,
                                        color: nuevaReserva.esOffline ? Colors.amber.shade800 : Colors.green,
                                      ),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: Text(
                                          nuevaReserva.esOffline
                                              ? '¡Reserva Offline Guardada!'
                                              : '¡Apartado Exitoso!',
                                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 17),
                                        ),
                                      ),
                                    ],
                                  ),
                                  content: Column(
                                    mainAxisSize: MainAxisSize.min,
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        nuevaReserva.esOffline
                                            ? 'Código Temporal Offline (${productCtrl.empresaActual.nombre}):'
                                            : 'Código de Retiro en Tienda (${productCtrl.empresaActual.nombre}):',
                                        style: const TextStyle(color: Colors.black54, fontSize: 12),
                                      ),
                                      const SizedBox(height: 6),
                                      Container(
                                        width: double.infinity,
                                        padding: const EdgeInsets.symmetric(vertical: 12),
                                        decoration: BoxDecoration(
                                          color: nuevaReserva.esOffline
                                              ? const Color(0xFFFEF3C7)
                                              : const Color(0xFFEFF6FF),
                                          borderRadius: BorderRadius.circular(8),
                                          border: Border.all(
                                            color: nuevaReserva.esOffline
                                                ? const Color(0xFFF59E0B)
                                                : const Color(0xFFBFDBFE),
                                          ),
                                        ),
                                        child: Text(
                                          nuevaReserva.codigoReserva,
                                          textAlign: TextAlign.center,
                                          style: TextStyle(
                                            color: nuevaReserva.esOffline
                                                ? const Color(0xFF92400E)
                                                : const Color(0xFF1E3A8A),
                                            fontSize: 23,
                                            fontWeight: FontWeight.w900,
                                            letterSpacing: 1.5,
                                            fontFamily: 'monospace',
                                          ),
                                        ),
                                      ),
                                      const SizedBox(height: 12),
                                      Text(
                                        nuevaReserva.esOffline
                                            ? 'Tu reserva se guardó en la memoria local de tu teléfono porque no tienes internet. En cuanto actives tu Wi-Fi o datos móviles, se sincronizará automáticamente con la tienda.'
                                            : 'Tus prendas han quedado reservadas en inventario. Presenta este código en caja al visitar la sucursal para cancelar y retirar.',
                                        style: const TextStyle(color: Colors.black87, fontSize: 13),
                                      ),
                                    ],
                                  ),
                                  actions: [
                                    ElevatedButton(
                                      style: ElevatedButton.styleFrom(
                                        backgroundColor: const Color(0xFF0F172A),
                                        foregroundColor: Colors.white,
                                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                      ),
                                      onPressed: () {
                                        Navigator.pop(ctx);
                                        Navigator.push(
                                          context,
                                          MaterialPageRoute(builder: (_) => const MyReservationsView()),
                                        );
                                      },
                                      child: const Text('Ver Mis Reservas'),
                                    ),
                                  ],
                                ),
                              );
                            } else {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text(resCtrl.error ?? 'Error al procesar reserva'),
                                  backgroundColor: Colors.redAccent,
                                ),
                              );
                            }
                          },
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildMetodoChip(int id, String label, IconData icon, Color activeColor) {
    final isSelected = _metodoPagoSeleccionado == id;
    return Expanded(
      child: InkWell(
        onTap: () => setState(() => _metodoPagoSeleccionado = id),
        borderRadius: BorderRadius.circular(10),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: isSelected ? activeColor.withAlpha(25) : const Color(0xFFF1F5F9),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: isSelected ? activeColor : const Color(0xFFE2E8F0),
              width: isSelected ? 2 : 1,
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 20, color: isSelected ? activeColor : Colors.grey[700]),
              const SizedBox(height: 2),
              Text(
                label,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                  color: isSelected ? activeColor : Colors.grey[800],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _mostrarDialogoPayPal(
    BuildContext context,
    int ventaId,
    String codigoVenta,
    String resumenPrendas,
    double totalCompra,
    Map<String, dynamic>? pagoInfo,
    PaymentController payCtrl,
  ) {
    final paypalUrl = pagoInfo?['paypal_url'] ?? pagoInfo?['url_redireccion'] ?? 'https://www.sandbox.paypal.com/checkoutnow';
    final montoUsd = pagoInfo?['monto_usd'] ?? (totalCompra / 6.96).toStringAsFixed(2);

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Row(
          children: [
            Icon(Icons.payment, color: Color(0xFF003087), size: 24),
            SizedBox(width: 10),
            Text('PayPal Checkout', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Serás redirigido a la pasarela segura de PayPal para completar tu pago con cuenta PayPal o tarjeta de débito/crédito internacional.',
              style: TextStyle(fontSize: 13, color: Colors.black87),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFEFF6FF),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFFBFDBFE)),
              ),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Orden:', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                      Text(codigoVenta, style: const TextStyle(fontWeight: FontWeight.bold, fontFamily: 'monospace', color: Color(0xFF003087))),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Monto en Bs:', style: TextStyle(fontSize: 12, color: Colors.black54)),
                      Text('Bs. ${totalCompra.toStringAsFixed(2)}', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                    ],
                  ),
                  const Divider(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Total a pagar (USD):', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: Color(0xFF003087))),
                      Text('\$$montoUsd USD', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: Color(0xFF003087))),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const OrdersHistoryView()));
            },
            child: const Text('Ver Mis Pedidos'),
          ),
          ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF003087),
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
            icon: const Icon(Icons.open_in_new, size: 16),
            label: const Text('Ir a Pagar en PayPal'),
            onPressed: () async {
              // Disparar notificación oficial de compra realizada
              try {
                final notifCtrl = Provider.of<NotificationController>(context, listen: false);
                final authCtrl = Provider.of<AuthController>(context, listen: false);
                final prodCtrl = Provider.of<ProductController>(context, listen: false);
                await notifCtrl.agregarNotificacion(
                  titulo: '🛍️ ¡Compra Realizada! #$codigoVenta',
                  mensaje: 'Has comprado exitosamente: $resumenPrendas. Total: Bs. ${totalCompra.toStringAsFixed(2)} (\$$montoUsd USD). Abriendo pasarela PayPal.',
                  tipo: 'COMPRA_EXITOSA',
                  enlace: '/mis-pedidos',
                  tenantId: prodCtrl.empresaSeleccionadaId,
                );
                await notifCtrl.fetchNotificaciones(
                  authCtrl.currentUser?.token,
                  tenantId: prodCtrl.empresaSeleccionadaId,
                );
              } catch (_) {}

              await payCtrl.abrirPayPal(paypalUrl);
            },
          ),
        ],
      ),
    );
  }

  void _mostrarDialogoQR(
    BuildContext context,
    int ventaId,
    String codigoVenta,
    String resumenPrendas,
    double totalCompra,
    Map<String, dynamic>? pagoInfo,
    PaymentController payCtrl,
  ) {
    final qrBase64 = (pagoInfo?['qr_base64'] ?? pagoInfo?['qr_image']) as String?;
    final expiracion = pagoInfo?['tiempo_expiracion_minutos'] ?? 15;
    final datosQr = 'BCP_SIMPLE_QR|VENTA:$ventaId|COD:$codigoVenta|MONTO:${totalCompra.toStringAsFixed(2)}|BANCO:BCP|CTA:1000004928371|TITULAR:BOUTIQUE_FASHIONSTORE';

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Row(
          children: [
            Icon(Icons.qr_code_2, color: Color(0xFF6D28D9), size: 24),
            SizedBox(width: 8),
            Text('Pago Simple por QR', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          ],
        ),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Escanea este código desde la app móvil de cualquier banco (BCP, BNB, Banco Sol, etc.) para pagar al instante.',
                style: TextStyle(fontSize: 12, color: Colors.black54),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),

              // Renderizado de código QR (Imagen base64 o Pintor simulado de alta fidelidad)
              if (qrBase64 != null && qrBase64.contains(','))
                ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.memory(
                    base64Decode(qrBase64.split(',').last),
                    width: 180,
                    height: 180,
                    fit: BoxFit.contain,
                  ),
                )
              else
                SimulatedQrWidget(
                  data: datosQr,
                  size: 180,
                  foregroundColor: const Color(0xFF4C1D95),
                  centerIcon: const Icon(Icons.qr_code_2, color: Color(0xFF6D28D9), size: 24),
                ),

              const SizedBox(height: 10),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                decoration: BoxDecoration(
                  color: const Color(0xFFF5F3FF),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFFDDD6FE)),
                ),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Total a pagar:', style: TextStyle(fontSize: 12, color: Colors.black54)),
                        Text('Bs. ${totalCompra.toStringAsFixed(2)}', style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w900, color: Color(0xFF6D28D9))),
                      ],
                    ),
                    const SizedBox(height: 2),
                    const Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text('Banco destino:', style: TextStyle(fontSize: 11, color: Colors.black54)),
                        Text('BCP - 1000004928371', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, fontFamily: 'monospace')),
                      ],
                    ),
                    const SizedBox(height: 2),
                    const Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text('Titular:', style: TextStyle(fontSize: 11, color: Colors.black54)),
                        Text('FashionStore S.R.L.', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600)),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.amber.shade50,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: Colors.amber.shade300),
                ),
                child: Text(
                  '⏱️ Válido por $expiracion minutos',
                  style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.amber.shade900),
                ),
              ),
            ],
          ),
        ),
        actions: [
          OutlinedButton.icon(
            icon: const Icon(Icons.receipt, size: 16),
            label: const Text('Ver Recibo'),
            onPressed: () async {
              final url = payCtrl.getComprobanteHtmlUrl(ventaId);
              await payCtrl.abrirPayPal(url);
            },
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF6D28D9),
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
            onPressed: () async {
              // Disparar notificación oficial de compra realizada por QR
              try {
                final notifCtrl = Provider.of<NotificationController>(context, listen: false);
                final authCtrl = Provider.of<AuthController>(context, listen: false);
                final prodCtrl = Provider.of<ProductController>(context, listen: false);
                await notifCtrl.agregarNotificacion(
                  titulo: '🛍️ ¡Compra Realizada! #$codigoVenta',
                  mensaje: 'Has comprado exitosamente: $resumenPrendas. Transferencia QR de Bs. ${totalCompra.toStringAsFixed(2)} confirmada y en preparación.',
                  tipo: 'COMPRA_EXITOSA',
                  enlace: '/mis-pedidos',
                  tenantId: prodCtrl.empresaSeleccionadaId,
                );
                await notifCtrl.fetchNotificaciones(
                  authCtrl.currentUser?.token,
                  tenantId: prodCtrl.empresaSeleccionadaId,
                );
              } catch (_) {}

              if (!context.mounted) return;
              Navigator.pop(ctx);
              Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const OrdersHistoryView()));
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('🔔 Notificación recibida: Compra #$codigoVenta confirmada por QR.'),
                  backgroundColor: Colors.green.shade800,
                ),
              );
            },
            child: const Text('¡Ya transferí! Confirmar'),
          ),
        ],
      ),
    );
  }

  void _mostrarDialogoTarjeta(
    BuildContext context,
    int ventaId,
    String codigoVenta,
    String resumenPrendas,
    double totalCompra,
    Map<String, dynamic>? pagoInfo,
    PaymentController payCtrl,
  ) {
    final numeroTarjetaCtrl = TextEditingController(text: '4532 8920 1144 7820');
    final titularCtrl = TextEditingController(text: 'CONSUMIDOR FINAL');
    final venceCtrl = TextEditingController(text: '12/28');
    final cvvCtrl = TextEditingController(text: '884');

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setModalState) {
          return AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            title: const Row(
              children: [
                Icon(Icons.credit_card, color: Color(0xFF1E3A8A)),
                SizedBox(width: 8),
                Text('Pago con Tarjeta Visa', style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
              ],
            ),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF0F172A), Color(0xFF1E3A8A)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Icon(Icons.nfc, color: Colors.amber, size: 24),
                            Text('VISA', style: TextStyle(color: Colors.white, fontStyle: FontStyle.italic, fontWeight: FontWeight.w900, fontSize: 18)),
                          ],
                        ),
                        const SizedBox(height: 14),
                        Text(
                          numeroTarjetaCtrl.text.isNotEmpty ? numeroTarjetaCtrl.text : '•••• •••• •••• 7820',
                          style: const TextStyle(color: Colors.white, fontSize: 16, letterSpacing: 2, fontFamily: 'monospace'),
                        ),
                        const SizedBox(height: 12),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              titularCtrl.text.isNotEmpty ? titularCtrl.text.toUpperCase() : 'CONSUMIDOR FINAL',
                              style: const TextStyle(color: Colors.white70, fontSize: 11, fontWeight: FontWeight.bold),
                            ),
                            Text('VENCE ${venceCtrl.text}', style: const TextStyle(color: Colors.white70, fontSize: 11)),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  TextField(
                    controller: numeroTarjetaCtrl,
                    onChanged: (_) => setModalState(() {}),
                    decoration: InputDecoration(
                      labelText: 'Número de Tarjeta',
                      prefixIcon: const Icon(Icons.credit_card),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    ),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: titularCtrl,
                    onChanged: (_) => setModalState(() {}),
                    decoration: InputDecoration(
                      labelText: 'Nombre del Titular',
                      prefixIcon: const Icon(Icons.person_outline),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: venceCtrl,
                          onChanged: (_) => setModalState(() {}),
                          decoration: InputDecoration(
                            labelText: 'Vence (MM/AA)',
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: TextField(
                          controller: cvvCtrl,
                          obscureText: true,
                          decoration: InputDecoration(
                            labelText: 'CVV',
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF1F5F9),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Monto total a cobrar:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                        Text('Bs. ${totalCompra.toStringAsFixed(2)}', style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Color(0xFF1E3A8A))),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Cancelar'),
              ),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF1E3A8A),
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                icon: const Icon(Icons.lock, size: 16),
                label: Text('Pagar Bs. ${totalCompra.toStringAsFixed(2)}'),
                onPressed: () async {
                  // Simulación de procesamiento de tarjeta bancaria
                  showDialog(
                    context: context,
                    barrierDismissible: false,
                    builder: (_) => const Center(
                      child: Card(
                        margin: EdgeInsets.all(32),
                        child: Padding(
                          padding: EdgeInsets.all(24.0),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              CircularProgressIndicator(color: Color(0xFF1E3A8A)),
                              SizedBox(height: 16),
                              Text('Procesando pago con red Visa...', style: TextStyle(fontWeight: FontWeight.bold)),
                              SizedBox(height: 6),
                              Text('Verificando fondos y autorizando transacción...', style: TextStyle(fontSize: 11, color: Colors.grey)),
                            ],
                          ),
                        ),
                      ),
                    ),
                  );

                  await Future.delayed(const Duration(milliseconds: 1400));
                  if (!context.mounted) return;

                  Navigator.pop(context); // Cierra spinner de simulación
                  Navigator.pop(ctx); // Cierra diálogo de tarjeta

                  // Disparar notificación oficial de compra realizada con tarjeta
                  try {
                    final notifCtrl = Provider.of<NotificationController>(context, listen: false);
                    final authCtrl = Provider.of<AuthController>(context, listen: false);
                    final prodCtrl = Provider.of<ProductController>(context, listen: false);
                    await notifCtrl.agregarNotificacion(
                      titulo: '🛍️ ¡Compra Realizada! #$codigoVenta',
                      mensaje: 'Has comprado exitosamente: $resumenPrendas. Pago de Bs. ${totalCompra.toStringAsFixed(2)} aprobado con tarjeta Visa terminada en 7820.',
                      tipo: 'COMPRA_EXITOSA',
                      enlace: '/mis-pedidos',
                      tenantId: prodCtrl.empresaSeleccionadaId,
                    );
                    await notifCtrl.fetchNotificaciones(
                      authCtrl.currentUser?.token,
                      tenantId: prodCtrl.empresaSeleccionadaId,
                    );
                  } catch (_) {}

                  if (!context.mounted) return;
                  Navigator.pushReplacement(
                    context,
                    MaterialPageRoute(builder: (_) => const OrdersHistoryView()),
                  );
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('🔔 Notificación recibida: Compra #$codigoVenta aprobada con Visa.'),
                      backgroundColor: Colors.green.shade800,
                    ),
                  );
                },
              ),
            ],
          );
        },
      ),
    );
  }

  static Color _hexToColorSeguro(String hex) {
    try {
      String clean = hex.replaceAll('#', '').trim();
      if (clean.length == 6) clean = 'FF$clean';
      return Color(int.parse(clean, radix: 16));
    } catch (_) {
      return const Color(0xFF0F172A);
    }
  }

}
