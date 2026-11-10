// ==============================================================================
// CAPA VISTA (MVC - VIEW EN FLUTTER / DART)
// Módulo: CU10 - Gestionar Reservas de Prendas
// Ubicación: mobile-app/lib/views/my_reservations_view.dart
// ==============================================================================

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../controllers/reservation_controller.dart';
import '../controllers/auth_controller.dart';
import '../controllers/product_controller.dart';
import '../models/reservation_model.dart';

class MyReservationsView extends StatefulWidget {
  const MyReservationsView({super.key});

  @override
  State<MyReservationsView> createState() => _MyReservationsViewState();
}

class _MyReservationsViewState extends State<MyReservationsView> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final token = context.read<AuthController>().currentUser?.token;
      final prodCtrl = context.read<ProductController>();
      context.read<ReservationController>().cargarMisReservas(
        token: token,
        tenantId: prodCtrl.empresaSeleccionadaId,
        modoOfflineSimulado: prodCtrl.modoOfflineSimulado,
      );
    });
  }

  void _mostrarTicketDigital(BuildContext context, ReservaModel reserva) {
    showDialog(
      context: context,
      builder: (ctx) => Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        backgroundColor: const Color(0xFF1E293B),
        child: Padding(
          padding: const EdgeInsets.all(22.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.confirmation_number_outlined, color: Color(0xFF38BDF8), size: 22),
                      SizedBox(width: 8),
                      Text('TICKET DIGITAL', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                    ],
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, color: Colors.white60, size: 20),
                    onPressed: () => Navigator.pop(ctx),
                  ),
                ],
              ),
              const Divider(color: Colors.white24, height: 24),
              const Text(
                'Presenta este código al cajero en sucursal:',
                style: TextStyle(color: Colors.white70, fontSize: 13),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFF38BDF8), width: 1.5),
                ),
                child: Column(
                  children: [
                    Text(
                      reserva.codigoReserva,
                      style: const TextStyle(
                        fontFamily: 'monospace',
                        color: Color(0xFF38BDF8),
                        fontSize: 26,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 3,
                      ),
                    ),
                    const SizedBox(height: 8),
                    // Simulación visual de código de barras
                    const Text(
                      '║▌│█║▌│ █║▌│█│║▌║▌│█',
                      style: TextStyle(
                        fontFamily: 'monospace',
                        color: Colors.white38,
                        fontSize: 20,
                        letterSpacing: 2,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFF38BDF8),
                  side: const BorderSide(color: Color(0xFF38BDF8)),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                icon: const Icon(Icons.copy, size: 16),
                label: const Text('Copiar Código'),
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: reserva.codigoReserva));
                  HapticFeedback.lightImpact();
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('¡Código de reserva copiado al portapapeles!'),
                      backgroundColor: Colors.teal,
                      duration: Duration(seconds: 2),
                    ),
                  );
                },
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.amber.withAlpha(25),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.amber.withAlpha(80)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.timer_outlined, color: Colors.amber, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Válido por 48 horas en ${reserva.sucursalNombre ?? "Sucursal Central"}. Las prendas se reservan automáticamente.',
                        style: const TextStyle(color: Colors.amber, fontSize: 11),
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

  Color _getStatusColor(String estado) {
    switch (estado.toUpperCase()) {
      case 'PENDIENTE':
        return Colors.amber.shade700;
      case 'CONFIRMADA':
        return Colors.blue.shade600;
      case 'PAGADA':
        return const Color(0xFF10B981);
      case 'ENTREGADA':
        return Colors.green.shade600;
      case 'CANCELADA':
        return Colors.red.shade600;
      default:
        return Colors.grey.shade600;
    }
  }

  void _mostrarDialogoPagarReserva(BuildContext context, ReservaModel reserva) {
    String metodoSeleccionado = 'PayPal';

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setModalState) {
          return AlertDialog(
            backgroundColor: const Color(0xFF1E293B),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            title: const Row(
              children: [
                Icon(Icons.payment, color: Color(0xFF38BDF8)),
                SizedBox(width: 8),
                Text('Pagar Reserva Online', style: TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.bold)),
              ],
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Reserva: ${reserva.codigoReserva}',
                  style: const TextStyle(color: Color(0xFF38BDF8), fontWeight: FontWeight.bold, fontSize: 14),
                ),
                const SizedBox(height: 4),
                Text(
                  'Total a Pagar: Bs. ${reserva.totalEstimado.toStringAsFixed(2)}',
                  style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 14),
                const Text(
                  'Selecciona la forma de pago:',
                  style: TextStyle(color: Colors.white70, fontSize: 12),
                ),
                const SizedBox(height: 8),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.payment, color: Color(0xFF003087)),
                  title: const Text('PayPal', style: TextStyle(color: Colors.white, fontSize: 14)),
                  trailing: Radio<String>(
                    value: 'PayPal',
                    groupValue: metodoSeleccionado,
                    activeColor: const Color(0xFF38BDF8),
                    onChanged: (v) => setModalState(() => metodoSeleccionado = v!),
                  ),
                  onTap: () => setModalState(() => metodoSeleccionado = 'PayPal'),
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.credit_card, color: Color(0xFF1E3A8A)),
                  title: const Text('Tarjeta de Débito / Crédito', style: TextStyle(color: Colors.white, fontSize: 14)),
                  trailing: Radio<String>(
                    value: 'Tarjeta',
                    groupValue: metodoSeleccionado,
                    activeColor: const Color(0xFF38BDF8),
                    onChanged: (v) => setModalState(() => metodoSeleccionado = v!),
                  ),
                  onTap: () => setModalState(() => metodoSeleccionado = 'Tarjeta'),
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.qr_code_2, color: Color(0xFF6D28D9)),
                  title: const Text('QR Simple / Transferencia', style: TextStyle(color: Colors.white, fontSize: 14)),
                  trailing: Radio<String>(
                    value: 'QR',
                    groupValue: metodoSeleccionado,
                    activeColor: const Color(0xFF38BDF8),
                    onChanged: (v) => setModalState(() => metodoSeleccionado = v!),
                  ),
                  onTap: () => setModalState(() => metodoSeleccionado = 'QR'),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Cancelar', style: TextStyle(color: Colors.white60)),
              ),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF10B981),
                  foregroundColor: Colors.white,
                ),
                icon: const Icon(Icons.check, size: 16),
                label: const Text('Confirmar Pago'),
                onPressed: () async {
                  Navigator.pop(ctx);
                  final ok = await context.read<ReservationController>().pagarReserva(
                    reserva.id,
                    metodoPago: metodoSeleccionado,
                  );
                  if (context.mounted) {
                    if (ok) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('¡Reserva PAGADA exitosamente! Puedes retirarla en sucursal mostrando tu código.'),
                          backgroundColor: Color(0xFF10B981),
                          duration: Duration(seconds: 4),
                        ),
                      );
                    } else {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('No se pudo procesar el pago de la reserva.'),
                          backgroundColor: Colors.redAccent,
                        ),
                      );
                    }
                  }
                },
              ),
            ],
          );
        },
      ),
    );
  }


  @override
  Widget build(BuildContext context) {
    final prodCtrl = Provider.of<ProductController>(context);

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
        title: Text(
          'Reservas - ${prodCtrl.empresaActual.nombre}',
          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
        ),
        iconTheme: const IconThemeData(color: Colors.white),
        actions: [
          IconButton(
            icon: const Icon(Icons.sync, color: Color(0xFF38BDF8)),
            tooltip: 'Sincronizar Reservas',
            onPressed: () async {
              final token = context.read<AuthController>().currentUser?.token;
              final syncCount = await context.read<ReservationController>().sincronizarReservasOffline(
                tenantId: prodCtrl.empresaSeleccionadaId,
                token: token,
              );
              await context.read<ReservationController>().cargarMisReservas(
                token: token,
                tenantId: prodCtrl.empresaSeleccionadaId,
                modoOfflineSimulado: prodCtrl.modoOfflineSimulado,
              );
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(
                      syncCount > 0
                          ? '¡$syncCount reserva(s) offline sincronizadas con el servidor!'
                          : 'Listado de reservas actualizado.',
                    ),
                    backgroundColor: Colors.teal,
                  ),
                );
              }
            },
          ),
        ],
      ),
      body: Consumer<ReservationController>(
        builder: (context, controller, child) {
          if (controller.cargando && controller.reservas.isEmpty) {
            return const Center(
              child: CircularProgressIndicator(color: Colors.indigoAccent),
            );
          }

          if (controller.reservas.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.event_seat_outlined, size: 80, color: Colors.blueGrey.shade600),
                  const SizedBox(height: 16),
                  const Text(
                    'No tienes reservas registradas',
                    style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Agrega prendas al carrito y resérvalas (incluso sin internet).',
                    style: TextStyle(color: Colors.white60),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            );
          }

          return Column(
            children: [
              if (controller.pendientesOfflineCount > 0)
                Container(
                  width: double.infinity,
                  margin: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF92400E).withAlpha(110),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.amber),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.cloud_upload_outlined, color: Colors.amber, size: 22),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          'Tienes ${controller.pendientesOfflineCount} reserva(s) guardadas sin internet en tu móvil.',
                          style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600),
                        ),
                      ),
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.amber,
                          foregroundColor: const Color(0xFF0F172A),
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        ),
                        onPressed: controller.sincronizando
                            ? null
                            : () async {
                                if (prodCtrl.modoOfflineSimulado) {
                                  prodCtrl.toggleModoOffline(forzar: false);
                                }
                                final token = context.read<AuthController>().currentUser?.token;
                                final count = await controller.sincronizarReservasOffline(
                                  tenantId: prodCtrl.empresaSeleccionadaId,
                                  token: token,
                                );
                                if (context.mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text(
                                        count > 0
                                            ? '¡$count reserva(s) offline sincronizadas exitosamente con la tienda!'
                                            : 'Aún sin conexión al servidor. Se sincronizarán al conectar internet.',
                                      ),
                                      backgroundColor: count > 0 ? Colors.green : Colors.orange.shade800,
                                    ),
                                  );
                                }
                              },
                        child: Text(
                          controller.sincronizando ? 'Sincronizando...' : 'Sincronizar',
                          style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ],
                  ),
                ),
              Expanded(
                child: RefreshIndicator(
                  onRefresh: () async {
                    final token = context.read<AuthController>().currentUser?.token;
                    await controller.cargarMisReservas(
                      token: token,
                      tenantId: prodCtrl.empresaSeleccionadaId,
                      modoOfflineSimulado: prodCtrl.modoOfflineSimulado,
                    );
                  },
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: controller.reservas.length,
                    itemBuilder: (context, index) {
                      final reserva = controller.reservas[index];
                      final statusColor = reserva.esOffline
                          ? Colors.amber
                          : _getStatusColor(reserva.estado);

                      return Container(
                        margin: const EdgeInsets.only(bottom: 16),
                        decoration: BoxDecoration(
                          color: const Color(0xFF1E293B),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(
                            color: reserva.esOffline ? Colors.amber.withAlpha(140) : const Color(0x14FFFFFF),
                          ),
                        ),
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Header con Código y Estado
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        reserva.esOffline ? 'RESERVA LOCAL OFFLINE' : 'CÓDIGO DE RESERVA',
                                        style: TextStyle(
                                          color: reserva.esOffline ? Colors.amber : Colors.white60,
                                          fontSize: 11,
                                          letterSpacing: 0.8,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                      const SizedBox(height: 2),
                                      Text(
                                        reserva.codigoReserva,
                                        style: TextStyle(
                                          color: reserva.esOffline ? Colors.amber : const Color(0xFF38BDF8),
                                          fontSize: 20,
                                          fontWeight: FontWeight.bold,
                                          fontFamily: 'monospace',
                                        ),
                                      ),
                                    ],
                                  ),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                                    decoration: BoxDecoration(
                                      color: statusColor.withAlpha(38),
                                      borderRadius: BorderRadius.circular(20),
                                      border: Border.all(color: statusColor.withAlpha(102)),
                                    ),
                                    child: Text(
                                      reserva.esOffline ? 'OFFLINE (PENDIENTE SYNC)' : reserva.estado,
                                      style: TextStyle(
                                        color: statusColor,
                                        fontWeight: FontWeight.bold,
                                        fontSize: 11,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                        const Divider(color: Colors.white12, height: 24),

                        // Sucursal
                        if (reserva.sucursalNombre != null) ...[
                          Row(
                            children: [
                              const Icon(Icons.storefront, size: 18, color: Colors.indigoAccent),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  '${reserva.sucursalNombre!} (${reserva.sucursalDireccion ?? ''})',
                                  style: const TextStyle(color: Colors.white, fontSize: 13),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                        ],

                        // Desglose de ítems
                        Text(
                          'Prendas (${reserva.totalItems} uds):',
                          style: const TextStyle(color: Colors.white70, fontSize: 12, fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 6),
                        ...reserva.detalles.map((det) => Padding(
                              padding: const EdgeInsets.symmetric(vertical: 3),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    '${det.cantidad}x ${det.productoNombre} ${det.talla != null ? '(${det.talla})' : ''}',
                                    style: const TextStyle(color: Colors.white, fontSize: 13),
                                  ),
                                  Text(
                                    'Bs. ${det.subtotal.toStringAsFixed(2)}',
                                    style: const TextStyle(color: Colors.greenAccent, fontSize: 13),
                                  ),
                                ],
                              ),
                            )),

                        if (reserva.estado == 'PAGADA') ...[
                          const SizedBox(height: 8),
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                            decoration: BoxDecoration(
                              color: const Color(0xFF10B981).withAlpha(30),
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: const Color(0xFF10B981).withAlpha(100)),
                            ),
                            child: const Row(
                              children: [
                                Icon(Icons.verified, color: Color(0xFF10B981), size: 16),
                                SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    'PAGADA DESDE TU TELÉFONO • Puedes recoger tus prendas en la sucursal mostrando tu ticket.',
                                    style: TextStyle(color: Color(0xFF10B981), fontSize: 11, fontWeight: FontWeight.w600),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],

                        const Divider(color: Colors.white12, height: 24),

                        // Footer con Total y Acciones
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  reserva.estado == 'PAGADA' ? 'Total Pagado:' : 'Total en caja:',
                                  style: const TextStyle(color: Colors.white60, fontSize: 11),
                                ),
                                Text(
                                  'Bs. ${reserva.totalEstimado.toStringAsFixed(2)}',
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 18,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                            Row(
                              children: [
                                if (reserva.estado == 'PENDIENTE') ...[
                                  ElevatedButton.icon(
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: const Color(0xFF10B981),
                                      foregroundColor: Colors.white,
                                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                      elevation: 0,
                                    ),
                                    onPressed: () => _mostrarDialogoPagarReserva(context, reserva),
                                    icon: const Icon(Icons.payment, size: 16),
                                    label: const Text('Pagar', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                                  ),
                                  const SizedBox(width: 6),
                                ],
                                ElevatedButton.icon(
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: const Color(0xFF0284C7),
                                    foregroundColor: Colors.white,
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                    elevation: 0,
                                  ),
                                  onPressed: () => _mostrarTicketDigital(context, reserva),
                                  icon: const Icon(Icons.qr_code_2, size: 16),
                                  label: const Text('Ticket', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                                ),

                                if (reserva.estado == 'PENDIENTE') ...[
                                  const SizedBox(width: 4),
                                  TextButton.icon(
                                    onPressed: () async {
                                      final confirmar = await showDialog<bool>(
                                        context: context,
                                        builder: (ctx) => AlertDialog(
                                          title: const Text('Cancelar Reserva'),
                                          content: Text('¿Deseas cancelar la reserva ${reserva.codigoReserva}? El stock apartado será liberado.'),
                                          actions: [
                                            TextButton(
                                              onPressed: () => Navigator.pop(ctx, false),
                                              child: const Text('No'),
                                            ),
                                            ElevatedButton(
                                              style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
                                              onPressed: () => Navigator.pop(ctx, true),
                                              child: const Text('Sí, Cancelar'),
                                            ),
                                          ],
                                        ),
                                      );

                                      if (confirmar == true) {
                                        final token = context.read<AuthController>().currentUser?.token;
                                        await controller.cancelarReserva(
                                          reserva.id,
                                          codigoReserva: reserva.codigoReserva,
                                          token: token,
                                          tenantId: prodCtrl.empresaSeleccionadaId,
                                        );
                                      }
                                    },
                                    icon: const Icon(Icons.cancel_outlined, size: 14, color: Colors.redAccent),
                                    label: const Text(
                                      'Cancelar',
                                      style: TextStyle(color: Colors.redAccent, fontSize: 12),
                                    ),
                                  ),
                                ],
                              ],
                            ),
                          ],
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
    );
  },
),
    );
  }
}
