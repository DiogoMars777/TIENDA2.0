// ==============================================================================
// CAPA VISTA / CONTROLADOR (MVC - VIEW & CONTROLLER EN FRONTEND ANGULAR)
// Módulo: CU11 - Atender Reservas en Sucursal
// Ubicación: frontend-web/src/app/views/admin/reservas/admin-reservas.component.ts
// ==============================================================================

import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';

import { ReservationService } from '../../../services/cu10_gestionar_reservas_prendas/reservation.service';
import { InventoryService } from '../../../services/cu8_consultar_catalogo_disponibilidad/inventory.service';
import { CobroOfflineController } from '../../../controllers/cu22_registrar_cobros_contado_offline/cobro-offline.controller';
import { CobroOfflineDTO, RegistroCobroOfflineRequest } from '../../../models/cu22_registrar_cobros_contado_offline/cobro-offline.model';
import { Reserva } from '../../../models/cu10_gestionar_reservas_prendas/reservation.model';
import { SucursalItem } from '../../../models/cu8_consultar_catalogo_disponibilidad/inventory.model';

@Component({
  selector: 'app-admin-reservas',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule
  ],
  templateUrl: './admin-reservas.component.html',
  styleUrls: ['./admin-reservas.component.css']
})
export class AdminReservasComponent implements OnInit {
  reservas: Reserva[] = [];
  sucursales: SucursalItem[] = [];
  tenantNombre: string = 'Mi Empresa';

  // Filtros
  sucursalIdFiltro: number | null = null;
  estadoFiltro: string = 'TODAS';
  codigoBusqueda: string = '';

  // Estados de carga
  loading = true;
  buscando = false;
  procesandoAccion = false;
  sincronizandoOffline = false;

  // Modal de Atención
  reservaSeleccionada: Reserva | null = null;
  mostrarModalAtencion = false;
  notasAtencion = '';

  // Sub-panel de Pago Offline en Caja (CU22 Contingencia)
  modoPagoOffline = false;
  folioOfflineProvisional = '';
  clienteNitOffline = '0';
  efectivoRecibidoOffline = 0;
  cambioOffline = 0;
  reciboOfflineEmitido: CobroOfflineDTO | null = null;

  constructor(
    public reservationService: ReservationService,
    public inventoryService: InventoryService,
    public cobroOfflineCtrl: CobroOfflineController,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    this.tenantNombre = localStorage.getItem('tenant_nombre') || 'Shopyn Golden Store';
    this.cargarSucursales();
    this.cargarReservas();

    this.route.queryParams.subscribe(params => {
      if (params['codigo']) {
        this.codigoBusqueda = params['codigo'];
        setTimeout(() => this.buscarPorCodigo(), 200);
      }
    });
  }

  get pendientesOfflineCount(): number {
    return this.reservationService.obtenerReservasOfflinePendientes().length;
  }

  sincronizarReservasLocales(): void {
    if (this.inventoryService.isOffline()) {
      alert('⚠️ El dispositivo sigue en modo Sin Internet. Desactiva el modo offline para sincronizar con el servidor.');
      return;
    }
    this.sincronizandoOffline = true;
    this.reservationService.sincronizarReservasOffline().subscribe({
      next: (creadas) => {
        this.sincronizandoOffline = false;
        alert(`✅ Se sincronizaron ${creadas.length} reserva(s) offline con el servidor central.`);
        this.cargarReservas();
      },
      error: () => {
        this.sincronizandoOffline = false;
      }
    });
  }

  cargarSucursales(): void {
    this.inventoryService.getSucursales().subscribe({
      next: (data) => this.sucursales = data,
      error: (err: any) => console.error('Error al cargar sucursales:', err)
    });
  }

  cargarReservas(): void {
    this.loading = true;
    this.reservationService.getReservasAdmin(this.sucursalIdFiltro, this.estadoFiltro).subscribe({
      next: (data) => {
        this.reservas = data;
        this.loading = false;
      },
      error: (err: any) => {
        console.error('Error al cargar reservas:', err);
        this.loading = false;
      }
    });
  }

  buscarPorCodigo(): void {
    const code = this.codigoBusqueda.trim().toUpperCase();
    if (!code) {
      this.cargarReservas();
      return;
    }

    this.buscando = true;
    this.reservationService.buscarPorCodigo(code).subscribe({
      next: (reserva) => {
        this.buscando = false;
        // Abrir directamente el modal de atención con la reserva encontrada
        this.abrirAtencion(reserva);
      },
      error: (err: any) => {
        this.buscando = false;
        alert(err.error?.detail || `No se encontró reserva con código "${code}"`);
      }
    });
  }

  abrirAtencion(reserva: Reserva): void {
    this.reservaSeleccionada = reserva;
    this.notasAtencion = '';
    this.modoPagoOffline = false;
    this.reciboOfflineEmitido = null;
    this.mostrarModalAtencion = true;
  }

  activarModoPagoOffline(): void {
    if (!this.reservaSeleccionada) return;
    this.modoPagoOffline = true;
    const rand = Math.floor(1000 + Math.random() * 9000);
    this.folioOfflineProvisional = `REC-${this.reservaSeleccionada.codigo_reserva}-${rand}`;
    this.clienteNitOffline = '0';
    this.efectivoRecibidoOffline = Math.ceil(this.reservaSeleccionada.total_estimado / 10) * 10;
    this.calcularCambioOffline();
  }

  calcularCambioOffline(): void {
    if (!this.reservaSeleccionada) return;
    const total = Number(this.reservaSeleccionada.total_estimado) || 0;
    const rec = Number(this.efectivoRecibidoOffline) || 0;
    this.cambioOffline = Math.max(0, Number((rec - total).toFixed(2)));
  }

  confirmarPagoOfflineReserva(): void {
    if (!this.reservaSeleccionada) return;
    const r = this.reservaSeleccionada;
    if (this.efectivoRecibidoOffline < r.total_estimado) {
      alert('El efectivo recibido no puede ser menor al total de la reserva.');
      return;
    }

    this.procesandoAccion = true;
    const payload: RegistroCobroOfflineRequest = {
      sucursal_id: r.sucursal?.id || 1,
      monto: r.total_estimado,
      moneda: 'BOB',
      nro_recibo_provisional: this.folioOfflineProvisional,
      uuid_operacion: `pos-res-off-${r.id}-${Date.now()}`,
      cliente_nombre: r.cliente_nombre || 'Cliente Reserva',
      cliente_nit: this.clienteNitOffline || '0',
      efectivo_recibido: this.efectivoRecibidoOffline,
      cambio: this.cambioOffline,
      observaciones: `Pago Offline de Reserva ${r.codigo_reserva}. ${this.notasAtencion || ''}`.trim(),
      items: (r.detalles || []).map(d => ({
        variante_id: d.variante_id,
        producto_nombre: d.producto_nombre,
        talla: d.talla || 'M',
        color: d.color || 'Estándar',
        cantidad: d.cantidad,
        precio_unitario: d.precio_unitario,
        subtotal: d.subtotal
      }))
    };

    this.cobroOfflineCtrl.registrarCobro(payload, (cobroCreado: CobroOfflineDTO) => {
      this.procesandoAccion = false;
      this.reservationService.marcarPagadaOfflineEnCache(r.id, cobroCreado.nro_recibo_provisional);
      this.reciboOfflineEmitido = cobroCreado;
      this.cargarReservas();
    });
  }

  imprimirReciboOffline(): void {
    window.print();
  }

  cerrarModal(): void {
    if (this.procesandoAccion) return;
    this.mostrarModalAtencion = false;
    this.reservaSeleccionada = null;
    this.modoPagoOffline = false;
    this.reciboOfflineEmitido = null;
  }

  procesarEntrega(accion: 'ENTREGAR' | 'CANCELAR'): void {
    if (!this.reservaSeleccionada) return;

    const accionTexto = accion === 'ENTREGAR' ? 'CONFIRMAR ENTREGA Y COBRO' : 'CANCELAR RESERVA';
    const confirmMsg = accion === 'ENTREGAR'
      ? `¿Confirmar entrega y cobro de Bs. ${this.reservaSeleccionada.total_estimado.toFixed(2)} para la reserva ${this.reservaSeleccionada.codigo_reserva}?\n\n(Se descontará el stock físico definitivamente).`
      : `¿Cancelar la reserva ${this.reservaSeleccionada.codigo_reserva}?\n\n(El stock reservado será liberado para venta).`;

    if (!confirm(confirmMsg)) return;

    this.procesandoAccion = true;
    this.reservationService.atenderReserva(
      this.reservaSeleccionada.id,
      accion,
      this.notasAtencion.trim() || undefined
    ).subscribe({
      next: (reservaActualizada) => {
        this.procesandoAccion = false;
        this.mostrarModalAtencion = false;
        this.reservaSeleccionada = null;

        const resultado = accion === 'ENTREGAR'
          ? `¡Reserva ${reservaActualizada.codigo_reserva} ENTREGADA con éxito! Stock físico descontado.`
          : `Reserva ${reservaActualizada.codigo_reserva} CANCELADA. Stock reservado liberado.`;
        alert(resultado);

        this.cargarReservas();
      },
      error: (err: any) => {
        this.procesandoAccion = false;
        alert(err.error?.detail || 'Error al procesar la reserva');
      }
    });
  }
}
