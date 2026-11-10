// ==============================================================================
// CAPA VISTA (MVC - VIEW EN FLUTTER / DART)
// Pantalla de Historial de Compras y Pedidos del Cliente (CU15)
// ==============================================================================

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../controllers/order_controller.dart';
import '../controllers/auth_controller.dart';
import '../controllers/payment_controller.dart';
import '../controllers/product_controller.dart';
import '../controllers/notification_controller.dart';
import '../models/order_model.dart';
import '../widgets/simulated_qr_widget.dart';

class OrdersHistoryView extends StatefulWidget {
  const OrdersHistoryView({super.key});

  @override
  State<OrdersHistoryView> createState() => _OrdersHistoryViewState();
}

class _OrdersHistoryViewState extends State<OrdersHistoryView> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => _cargarOrdenes());
  }

  void _cargarOrdenes() {
    final authCtrl = Provider.of<AuthController>(context, listen: false);
    final prodCtrl = Provider.of<ProductController>(context, listen: false);
    final token = authCtrl.currentUser?.token;
    Provider.of<OrderController>(context, listen: false).fetchMisOrdenes(
      token,
      tenantId: prodCtrl.empresaSeleccionadaId,
    );
    Provider.of<NotificationController>(context, listen: false).fetchNotificaciones(
      token,
      tenantId: prodCtrl.empresaSeleccionadaId,
    );
  }

  Widget _buildPurchasedItems(List<OrderItemModel> items) {
    if (items.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 4.0),
        child: Text(
          'Detalle de prendas registrado en el comprobante digital.',
          style: TextStyle(fontSize: 12, color: Colors.grey.shade600, fontStyle: FontStyle.italic),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Text(
            'PRENDAS COMPRADAS (${items.length}):',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.5,
              color: Colors.grey.shade600,
            ),
          ),
        ),
        Container(
          decoration: BoxDecoration(
            color: Colors.grey.shade50,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.grey.shade200),
          ),
          child: ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: items.length,
            separatorBuilder: (_, __) => Divider(height: 1, color: Colors.grey.shade200),
            itemBuilder: (context, idx) {
              final it = items[idx];
              return Padding(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    // Miniatura o icono de prenda
                    ClipRRect(
                      borderRadius: BorderRadius.circular(6),
                      child: Container(
                        width: 42,
                        height: 42,
                        color: Colors.white,
                        child: it.imagenUrl != null && it.imagenUrl!.isNotEmpty
                            ? Image.network(
                                it.imagenUrl!,
                                fit: BoxFit.cover,
                                errorBuilder: (_, __, ___) => const Icon(Icons.checkroom, color: Colors.indigo, size: 24),
                              )
                            : const Icon(Icons.checkroom, color: Colors.indigo, size: 24),
                      ),
                    ),
                    const SizedBox(width: 10),
                    // Descripción y variantes
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            it.productoNombre,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              color: Color(0xFF1E293B),
                            ),
                          ),
                          const SizedBox(height: 2),
                          Row(
                            children: [
                              if (it.talla != null && it.talla!.isNotEmpty)
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                                  margin: const EdgeInsets.only(right: 6),
                                  decoration: BoxDecoration(
                                    color: Colors.indigo.shade50,
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: Text(
                                    'Talla: ${it.talla}',
                                    style: TextStyle(fontSize: 10, color: Colors.indigo.shade700, fontWeight: FontWeight.w600),
                                  ),
                                ),
                              if (it.color != null && it.color!.isNotEmpty)
                                Text(
                                  it.color!,
                                  style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                                ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    // Cantidad y subtotal
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(
                          '${it.cantidad}x Bs. ${it.precioUnitario.toStringAsFixed(2)}',
                          style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Bs. ${it.subtotal.toStringAsFixed(2)}',
                          style: const TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: Color(0xFF0F172A),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  void _mostrarNotificacionesModal(BuildContext context) {
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
                          Icon(Icons.notifications_active, color: Colors.indigo),
                          SizedBox(width: 8),
                          Text('Notificaciones de Compra (CU19)', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
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
                  if (ctrl.notificaciones.isEmpty)
                    const Padding(
                      padding: EdgeInsets.all(30),
                      child: Center(
                        child: Text('No tienes notificaciones registradas', style: TextStyle(color: Colors.grey)),
                      ),
                    )
                  else
                    Flexible(
                      child: ListView.builder(
                        shrinkWrap: true,
                        itemCount: ctrl.notificaciones.length,
                        itemBuilder: (_, i) {
                          final n = ctrl.notificaciones[i];
                          return Container(
                            margin: const EdgeInsets.symmetric(vertical: 4),
                            decoration: BoxDecoration(
                              color: n.leido ? Colors.grey.shade50 : const Color(0xFFF0FDF4),
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(
                                color: n.leido ? Colors.grey.shade200 : Colors.green.shade300,
                              ),
                            ),
                            child: ListTile(
                              leading: CircleAvatar(
                                backgroundColor: Colors.green.shade100,
                                child: Icon(Icons.shopping_bag, color: Colors.green.shade800, size: 20),
                              ),
                              title: Text(
                                n.titulo,
                                style: TextStyle(
                                  fontWeight: n.leido ? FontWeight.w600 : FontWeight.w800,
                                  fontSize: 13,
                                ),
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

  @override
  Widget build(BuildContext context) {
    final orderCtrl = Provider.of<OrderController>(context);
    final notifCtrl = Provider.of<NotificationController>(context);
    final ultimaNoLeida = notifCtrl.notificaciones.where((n) => !n.leido).toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text('📦 Mis Pedidos'),
        backgroundColor: Colors.indigo,
        foregroundColor: Colors.white,
        elevation: 1,
        actions: [
          Stack(
            alignment: Alignment.center,
            children: [
              IconButton(
                icon: const Icon(Icons.notifications_none),
                tooltip: 'Ver Notificaciones (CU19)',
                onPressed: () => _mostrarNotificacionesModal(context),
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
          ),
        ],
      ),
      body: Column(
        children: [
          if (ultimaNoLeida.isNotEmpty)
            InkWell(
              onTap: () => _mostrarNotificacionesModal(context),
              child: Container(
                width: double.infinity,
                margin: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: const Color(0xFFDCFCE7),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFF22C55E)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.notifications_active, color: Color(0xFF15803D), size: 22),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            ultimaNoLeida.first.titulo,
                            style: const TextStyle(
                              fontWeight: FontWeight.w800,
                              fontSize: 13,
                              color: Color(0xFF14532D),
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            ultimaNoLeida.first.mensaje,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontSize: 11.5, color: Color(0xFF166534)),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    const Text(
                      'Ver',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                        color: Color(0xFF15803D),
                        decoration: TextDecoration.underline,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          Expanded(
            child: RefreshIndicator(
        onRefresh: () async => _cargarOrdenes(),
        child: orderCtrl.cargando
            ? const Center(child: CircularProgressIndicator())
            : orderCtrl.error != null
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24.0),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.error_outline, size: 56, color: Colors.red),
                          const SizedBox(height: 12),
                          Text(
                            orderCtrl.error!,
                            textAlign: TextAlign.center,
                            style: const TextStyle(fontSize: 16, color: Colors.black87),
                          ),
                          const SizedBox(height: 16),
                          ElevatedButton.icon(
                            onPressed: _cargarOrdenes,
                            icon: const Icon(Icons.refresh),
                            label: const Text('Reintentar'),
                          )
                        ],
                      ),
                    ),
                  )
                : orderCtrl.ordenes.isEmpty
                    ? Center(
                        child: Padding(
                          padding: const EdgeInsets.all(32.0),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.receipt_long_outlined, size: 72, color: Colors.grey.shade400),
                              const SizedBox(height: 16),
                              const Text(
                                'Aún no tienes pedidos registrados',
                                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.black87),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                'Tus compras online aparecerán aquí con su estado y desglose en tiempo real.',
                                textAlign: TextAlign.center,
                                style: TextStyle(fontSize: 14, color: Colors.grey.shade600),
                              ),
                              const SizedBox(height: 24),
                              ElevatedButton(
                                style: ElevatedButton.styleFrom(backgroundColor: Colors.indigo, foregroundColor: Colors.white),
                                onPressed: () => Navigator.pop(context),
                                child: const Text('Explorar Catálogo'),
                              ),
                            ],
                          ),
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        itemCount: orderCtrl.ordenes.length,
                        itemBuilder: (ctx, index) {
                          final orden = orderCtrl.ordenes[index];
                          final fechaStr = orden.fecha != null
                              ? '${orden.fecha!.day.toString().padLeft(2, '0')}/${orden.fecha!.month.toString().padLeft(2, '0')}/${orden.fecha!.year} ${orden.fecha!.hour.toString().padLeft(2, '0')}:${orden.fecha!.minute.toString().padLeft(2, '0')}'
                              : 'Reciente';

                          return Card(
                            elevation: 2,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            margin: const EdgeInsets.symmetric(vertical: 8),
                            child: Padding(
                              padding: const EdgeInsets.all(16.0),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                        decoration: BoxDecoration(
                                          color: Colors.indigo.shade50,
                                          borderRadius: BorderRadius.circular(6),
                                        ),
                                        child: Text(
                                          orden.codigoVenta,
                                          style: TextStyle(
                                            fontFamily: 'monospace',
                                            fontWeight: FontWeight.bold,
                                            color: Colors.indigo.shade800,
                                            fontSize: 13,
                                          ),
                                        ),
                                      ),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                        decoration: BoxDecoration(
                                          color: orden.estado.toUpperCase().contains('ENTREGAD')
                                              ? Colors.green.shade100
                                              : Colors.blue.shade100,
                                          borderRadius: BorderRadius.circular(20),
                                        ),
                                        child: Row(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            Icon(
                                              orden.estado.toUpperCase().contains('ENTREGAD')
                                                  ? Icons.done_all
                                                  : Icons.check_circle,
                                              size: 14,
                                              color: orden.estado.toUpperCase().contains('ENTREGAD')
                                                  ? Colors.green.shade800
                                                  : Colors.blue.shade800,
                                            ),
                                            const SizedBox(width: 4),
                                            Text(
                                              orden.estado.toUpperCase().contains('ENTREGAD') ? 'Entregado' : 'Comprado',
                                              style: TextStyle(
                                                color: orden.estado.toUpperCase().contains('ENTREGAD')
                                                    ? Colors.green.shade900
                                                    : Colors.blue.shade900,
                                                fontWeight: FontWeight.w700,
                                                fontSize: 12,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 12),
                                  Row(
                                    children: [
                                      Icon(Icons.access_time, size: 16, color: Colors.grey.shade600),
                                      const SizedBox(width: 6),
                                      Text(
                                        fechaStr,
                                        style: TextStyle(fontSize: 13, color: Colors.grey.shade700),
                                      ),
                                      const Spacer(),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: Colors.grey.shade200,
                                          borderRadius: BorderRadius.circular(4),
                                        ),
                                        child: Text(
                                          orden.tipoVenta,
                                          style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Colors.grey.shade800),
                                        ),
                                      )
                                    ],
                                  ),
                                  const SizedBox(height: 14),
                                  // Detalle de Prendas Compradas
                                  _buildPurchasedItems(orden.items),
                                  const Divider(height: 20),
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      const Text(
                                        'Total Pagado:',
                                        style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: Colors.black54),
                                      ),
                                      Text(
                                        'Bs. ${orden.total.toStringAsFixed(2)}',
                                        style: const TextStyle(
                                          fontSize: 18,
                                          fontWeight: FontWeight.w800,
                                          color: Colors.indigo,
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 10),
                                  SizedBox(
                                    width: double.infinity,
                                    child: OutlinedButton.icon(
                                      style: OutlinedButton.styleFrom(
                                        foregroundColor: Colors.indigo.shade800,
                                        side: BorderSide(color: Colors.indigo.shade200),
                                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                      ),
                                      icon: const Icon(Icons.receipt_long, size: 16),
                                      label: const Text('Ver Recibo Oficial (PDF / QR)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                                      onPressed: () {
                                        _mostrarReciboDigitalModal(context, orden, fechaStr);
                                      },
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

  void _mostrarReciboDigitalModal(BuildContext context, OrderModel orden, String fechaStr) {
    final subtotalSinIva = orden.total / 1.13;
    final iva13 = orden.total - subtotalSinIva;
    final codigoAut = 'AUT-${orden.id * 8372}-${orden.fecha?.millisecondsSinceEpoch ?? 2026}';
    final datosQrFiscal = 'FASHIONSTORE|NIT:1029384756|RECIBO:${orden.codigoVenta}|TOTAL:${orden.total.toStringAsFixed(2)}|FECHA:$fechaStr|ESTADO:PAGADO';

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.88,
        minChildSize: 0.5,
        maxChildSize: 0.96,
        builder: (_, scrollController) => Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Column(
            children: [
              Container(
                margin: const EdgeInsets.only(top: 12, bottom: 8),
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(6),
                          decoration: BoxDecoration(
                            color: Colors.indigo.shade50,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Icon(Icons.receipt_long, color: Colors.indigo.shade700, size: 20),
                        ),
                        const SizedBox(width: 8),
                        const Text(
                          'Recibo Digital Oficial',
                          style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                        ),
                      ],
                    ),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.pop(ctx),
                      color: Colors.grey.shade700,
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              Expanded(
                child: ListView(
                  controller: scrollController,
                  padding: const EdgeInsets.all(20),
                  children: [
                    Container(
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        color: const Color(0xFFFAFAFC),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: Colors.grey.shade300),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withAlpha(8),
                            blurRadius: 10,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.center,
                        children: [
                          const Text(
                            'BOUTIQUE FASHIONSTORE S.R.L.',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 0.5,
                              color: Color(0xFF0F172A),
                            ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'NIT: 1029384756 | Santa Cruz, Bolivia',
                            style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                          ),
                          Text(
                            'Av. San Martín #450 • Tel: +591 70000000',
                            style: TextStyle(fontSize: 11, color: Colors.grey.shade500),
                          ),
                          const SizedBox(height: 12),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                            decoration: BoxDecoration(
                              color: Colors.green.shade50,
                              borderRadius: BorderRadius.circular(20),
                              border: Border.all(color: Colors.green.shade300),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(Icons.check_circle, size: 14, color: Colors.green.shade700),
                                const SizedBox(width: 4),
                                Text(
                                  'PAGO VERIFICADO Y REGISTRADO',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                    color: Colors.green.shade800,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 16),
                          const _DashedLine(),
                          const SizedBox(height: 14),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('Nº DE RECIBO:', style: TextStyle(fontSize: 11, color: Colors.grey.shade600, fontWeight: FontWeight.w600)),
                                  Text(
                                    orden.codigoVenta,
                                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, fontFamily: 'monospace', color: Colors.indigo),
                                  ),
                                ],
                              ),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.end,
                                children: [
                                  Text('FECHA Y HORA:', style: TextStyle(fontSize: 11, color: Colors.grey.shade600, fontWeight: FontWeight.w600)),
                                  Text(
                                    fechaStr,
                                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.black87),
                                  ),
                                ],
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('MODALIDAD:', style: TextStyle(fontSize: 11, color: Colors.grey.shade600, fontWeight: FontWeight.w600)),
                                  Text(
                                    'Compra Digital (${orden.tipoVenta})',
                                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.black87),
                                  ),
                                ],
                              ),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.end,
                                children: [
                                  Text('AUTORIZACIÓN:', style: TextStyle(fontSize: 11, color: Colors.grey.shade600, fontWeight: FontWeight.w600)),
                                  Text(
                                    codigoAut.substring(0, codigoAut.length > 14 ? 14 : codigoAut.length),
                                    style: TextStyle(fontSize: 11, fontFamily: 'monospace', color: Colors.grey.shade700),
                                  ),
                                ],
                              ),
                            ],
                          ),
                          const SizedBox(height: 14),
                          const _DashedLine(),
                          const SizedBox(height: 14),
                          Align(
                            alignment: Alignment.centerLeft,
                            child: Text(
                              'DETALLE DE PRENDAS COMPRADAS',
                              style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 0.5, color: Colors.grey.shade700),
                            ),
                          ),
                          const SizedBox(height: 8),
                          if (orden.items.isEmpty)
                            Padding(
                              padding: const EdgeInsets.symmetric(vertical: 8),
                              child: Text(
                                'Prendas registradas en la transacción #${orden.id}',
                                style: TextStyle(fontSize: 12, color: Colors.grey.shade600, fontStyle: FontStyle.italic),
                              ),
                            )
                          else
                            ...orden.items.map((it) => Padding(
                              padding: const EdgeInsets.symmetric(vertical: 6),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          it.productoNombre,
                                          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Color(0xFF1E293B)),
                                        ),
                                        Text(
                                          'Talla: ${it.talla ?? 'M'}  |  Color: ${it.color ?? 'Estándar'}  |  Cant: ${it.cantidad}',
                                          style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                                        ),
                                      ],
                                    ),
                                  ),
                                  Text(
                                    'Bs. ${it.subtotal.toStringAsFixed(2)}',
                                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                                  ),
                                ],
                              ),
                            )),
                          const SizedBox(height: 14),
                          const _DashedLine(),
                          const SizedBox(height: 14),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text('Subtotal Base:', style: TextStyle(fontSize: 13, color: Colors.grey.shade700)),
                              Text('Bs. ${subtotalSinIva.toStringAsFixed(2)}', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text('IVA Débito Fiscal (13% Ley):', style: TextStyle(fontSize: 13, color: Colors.grey.shade700)),
                              Text('Bs. ${iva13.toStringAsFixed(2)}', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                            ],
                          ),
                          const SizedBox(height: 10),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                            decoration: BoxDecoration(
                              color: Colors.indigo.shade50,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                const Text(
                                  'TOTAL PAGADO:',
                                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: Colors.indigo),
                                ),
                                Text(
                                  'Bs. ${orden.total.toStringAsFixed(2)}',
                                  style: TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.w900,
                                    color: Colors.indigo.shade900,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 18),
                          const _DashedLine(),
                          const SizedBox(height: 16),
                          SimulatedQrWidget(
                            data: datosQrFiscal,
                            size: 150,
                            foregroundColor: const Color(0xFF0F172A),
                            centerIcon: Icon(Icons.verified, color: Colors.blue.shade700, size: 22),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'CÓDIGO DE CONTROL FISCAL DIGITAL',
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                              letterSpacing: 0.5,
                              color: Colors.grey.shade700,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            codigoAut,
                            style: TextStyle(fontSize: 10, fontFamily: 'monospace', color: Colors.grey.shade500),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Este comprobante digital acredita la compra legal y entrega en FashionStore.',
                            textAlign: TextAlign.center,
                            style: TextStyle(fontSize: 10, color: Colors.grey.shade500, fontStyle: FontStyle.italic),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 18),
                    SizedBox(
                      width: double.infinity,
                      height: 48,
                      child: ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF0F172A),
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                        icon: const Icon(Icons.open_in_browser, size: 18),
                        label: const Text('Abrir Versión Web Imprimible', style: TextStyle(fontWeight: FontWeight.bold)),
                        onPressed: () async {
                          final payCtrl = Provider.of<PaymentController>(context, listen: false);
                          final url = payCtrl.getComprobanteHtmlUrl(orden.id);
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('Abriendo comprobante oficial en el navegador...'),
                              duration: Duration(seconds: 2),
                            ),
                          );
                          await payCtrl.abrirPayPal(url);
                        },
                      ),
                    ),
                    const SizedBox(height: 8),
                    SizedBox(
                      width: double.infinity,
                      child: TextButton(
                        onPressed: () => Navigator.pop(ctx),
                        child: Text('Cerrar Recibo', style: TextStyle(color: Colors.grey.shade700, fontWeight: FontWeight.bold)),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DashedLine extends StatelessWidget {
  const _DashedLine();

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final boxWidth = constraints.constrainWidth();
        const dashWidth = 5.0;
        const dashHeight = 1.0;
        final dashCount = (boxWidth / (2 * dashWidth)).floor();
        return Flex(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          direction: Axis.horizontal,
          children: List.generate(dashCount, (_) {
            return SizedBox(
              width: dashWidth,
              height: dashHeight,
              child: DecoratedBox(
                decoration: BoxDecoration(color: Colors.grey.shade300),
              ),
            );
          }),
        );
      },
    );
  }
}

