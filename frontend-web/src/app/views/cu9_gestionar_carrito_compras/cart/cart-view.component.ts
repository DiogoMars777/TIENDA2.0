// ==============================================================================
// CAPA VISTA / CONTROLADOR (MVC - VIEW & CONTROLLER EN FRONTEND ANGULAR)
// Módulo: CU09 - Gestionar Carrito de Compras
// Ubicación: frontend-web/src/app/views/cart/cart-view.component.ts
// ==============================================================================

import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router, ActivatedRoute } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';

import { CartService } from '../../../services/cu9_gestionar_carrito_compras/cart.service';
import { InventoryService } from '../../../services/cu8_consultar_catalogo_disponibilidad/inventory.service';
import { ReservationService } from '../../../services/cu10_gestionar_reservas_prendas/reservation.service';
import { CompraDigitalService, OrdenResponseDTO } from '../../../services/cu15_realizar_compras_digitales/compra-digital.service';
import { PagoService, MetodoPagoDTO, IniciarPagoResponseDTO } from '../../../services/cu16_gestionar_pagos_comprobantes/pago.service';
import { RecomendacionService, RecomendacionOutfitDTO } from '../../../services/cu18_gestionar_recomendaciones_ia/recomendacion.service';
import { Carrito, CarritoItem } from '../../../models/cu9_gestionar_carrito_compras/cart.model';
import { SucursalItem } from '../../../models/cu8_consultar_catalogo_disponibilidad/inventory.model';
import { Reserva } from '../../../models/cu10_gestionar_reservas_prendas/reservation.model';

@Component({
  selector: 'app-cart-view',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule
  ],
  templateUrl: './cart-view.component.html',
  styleUrls: ['./cart-view.component.css']
})
export class CartViewComponent implements OnInit {
  carrito: Carrito | null = null;
  sucursales: SucursalItem[] = [];
  loading = true;
  procesandoId: number | null = null;

  // Estado del Modal de Reserva en Tienda Física (CU10)
  mostrarModalReserva = false;
  observacionesReserva = '';
  procesandoReserva = false;
  reservaExitosa: Reserva | null = null;

  // Estado del Modal de Compra Digital con Envío a Domicilio (CU15 y CU16)
  mostrarModalCompra = false;
  direccionEnvio = 'Av. San Martín #450, Equipetrol, Santa Cruz';
  metodoPagoDigital = 'TARJETA_DEBITO';
  procesandoCompra = false;
  compraExitosa: OrdenResponseDTO | null = null;

  // CU16: Gestión de Pagos (PayPal, QR, Efectivo) y Comprobantes
  metodosPago: MetodoPagoDTO[] = [];
  metodoSeleccionadoId = 6; // PayPal por defecto o primer activo
  qrData: IniciarPagoResponseDTO | null = null;
  mostrarModalQR = false;
  urlComprobante = '';
  redireccionandoPayPal = false;
  // CU18: Recomendaciones Stylist IA
  recomendaciones: RecomendacionOutfitDTO[] = [];
  cargandoRecomendaciones = false;
  isAdminView = false;

  constructor(
    private cartService: CartService,
    private inventoryService: InventoryService,
    private reservationService: ReservationService,
    private compraDigitalService: CompraDigitalService,
    private pagoService: PagoService,
    private recomendacionService: RecomendacionService,
    private router: Router,
    private route: ActivatedRoute
  ) {
    this.isAdminView = this.router.url.startsWith('/admin');
  }

  ngOnInit(): void {
    // 1. Cargar tiendas físicas
    this.inventoryService.getSucursales().subscribe({
      next: (s) => this.sucursales = s,
      error: (e: any) => console.error('Error al cargar sucursales:', e)
    });

    // 2. Cargar métodos de pago activos (CU16)
    this.pagoService.getMetodosPago().subscribe({
      next: (m) => {
        this.metodosPago = m;
        const paypal = m.find(x => x.nombre.toLowerCase().includes('paypal'));
        if (paypal) {
          this.metodoSeleccionadoId = paypal.id;
        } else if (m.length > 0) {
          this.metodoSeleccionadoId = m[0].id;
        }
      },
      error: (e: any) => console.error('Error al cargar métodos de pago:', e)
    });

    // 3. Detectar si regresa de la pasarela oficial de PayPal
    this.route.queryParams.subscribe(params => {
      if (params['pago_status'] === 'exito' && params['orden_id']) {
        const ordenId = Number(params['orden_id']);
        this.pagoService.capturarPayPal(ordenId, params['token']).subscribe({
          next: (res) => {
            this.compraExitosa = {
              id: ordenId,
              codigoventa: res.codigo_venta,
              total: res.monto,
              estado: 'Completada',
              tipoventa: 'Digital',
              subtotal: res.monto,
              descuento: 0,
              mensaje: '¡Pago capturado y confirmado a través de PayPal!'
            };
            this.urlComprobante = this.pagoService.getComprobanteUrl(ordenId);
            this.mostrarModalCompra = true;
          },
          error: (err: any) => {
            console.error('Error capturando PayPal:', err);
          }
        });
      }
    });

    // 4. Suscribirse reactivamente al carrito
    this.cartService.cart$.subscribe({
      next: (c) => {
        this.carrito = c;
        this.loading = false;
        if (c && c.items && c.items.length > 0) {
          this.cargarRecomendacionesIA();
        } else {
          this.recomendaciones = [];
        }
      },
      error: (e: any) => {
        console.error('Error al cargar carrito:', e);
        this.loading = false;
      }
    });

    // Carga inicial
    this.cartService.cargarCarrito().subscribe();
  }

  cargarRecomendacionesIA(): void {
    if (!this.carrito || this.carrito.items.length === 0) return;
    const ids = this.carrito.items.map(i => i.producto_id);
    this.cargandoRecomendaciones = true;
    this.recomendacionService.obtenerRecomendacionOutfit(undefined, ids, 3).subscribe({
      next: (data) => {
        this.recomendaciones = data;
        this.cargandoRecomendaciones = false;
      },
      error: (e: any) => {
        console.warn('Error recomendaciones:', e);
        this.cargandoRecomendaciones = false;
      }
    });
  }

  agregarRecomendado(rec: RecomendacionOutfitDTO): void {
    this.router.navigate([this.isAdminView ? '/admin/catalogo' : '/catalogo'], { queryParams: { q: rec.nombre } });
  }

  incrementar(item: CarritoItem): void {
    if (item.cantidad >= item.stock_disponible) {
      alert(`No puedes agregar más unidades. Stock disponible en tienda: ${item.stock_disponible} uds.`);
      return;
    }
    this.procesandoId = item.variante_id;
    this.cartService.actualizarCantidad(item.variante_id, item.cantidad + 1).subscribe({
      next: () => this.procesandoId = null,
      error: (err: any) => {
        this.procesandoId = null;
        alert(err.error?.detail || 'Error al actualizar cantidad');
      }
    });
  }

  decrementar(item: CarritoItem): void {
    this.procesandoId = item.variante_id;
    if (item.cantidad <= 1) {
      this.eliminar(item);
      return;
    }

    this.cartService.actualizarCantidad(item.variante_id, item.cantidad - 1).subscribe({
      next: () => this.procesandoId = null,
      error: (err: any) => {
        this.procesandoId = null;
        alert(err.error?.detail || 'Error al decrementar cantidad');
      }
    });
  }

  eliminar(item: CarritoItem): void {
    if (confirm(`¿Quitar ${item.producto_nombre} (Talla: ${item.talla}) del carrito?`)) {
      this.procesandoId = item.variante_id;
      this.cartService.eliminarItem(item.variante_id).subscribe({
        next: () => this.procesandoId = null,
        error: (err: any) => {
          this.procesandoId = null;
          alert(err.error?.detail || 'Error al eliminar ítem');
        }
      });
    }
  }

  onCambioSucursal(event: any): void {
    const sucursalId = Number(event.target.value);
    if (!sucursalId) return;

    this.cartService.asignarSucursal(sucursalId).subscribe({
      next: () => {},
      error: (err: any) => alert(err.error?.detail || 'Error al cambiar sucursal')
    });
  }

  vaciar(): void {
    if (confirm('¿Estás seguro de que deseas vaciar todo el carrito?')) {
      this.cartService.vaciarCarrito().subscribe();
    }
  }

  procederAReserva(): void {
    if (!this.carrito || this.carrito.items.length === 0) return;

    if (!this.carrito.sucursal_id) {
      alert('Por favor selecciona la sucursal física donde retirarás tu pedido antes de continuar.');
      return;
    }

    if (this.carrito.tiene_alertas_stock) {
      alert('Hay prendas en tu carrito que superan el stock de la sucursal seleccionada. Por favor ajusta las cantidades.');
      return;
    }

    this.observacionesReserva = '';
    this.reservaExitosa = null;
    this.mostrarModalReserva = true;
  }

  cerrarModalReserva(): void {
    if (this.procesandoReserva) return;
    this.mostrarModalReserva = false;
  }

  confirmarReserva(): void {
    if (!this.carrito || !this.carrito.sucursal_id) return;

    this.procesandoReserva = true;
    this.reservationService.crearReserva({
      sucursal_id: this.carrito.sucursal_id,
      observaciones: this.observacionesReserva.trim() || undefined
    }).subscribe({
      next: (nuevaReserva) => {
        this.procesandoReserva = false;
        this.reservaExitosa = nuevaReserva;
      },
      error: (err: any) => {
        this.procesandoReserva = false;
        alert(err.error?.detail || 'Error al procesar la reserva. Por favor intenta de nuevo.');
      }
    });
  }

  irAMisReservas(): void {
    this.mostrarModalReserva = false;
    this.router.navigate([this.isAdminView ? '/admin/mis-reservas' : '/mis-reservas']);
  }

  // --- CU15: Métodos para Compra Digital con Envío a Domicilio ---
  procederACompra(): void {
    if (!this.carrito || this.carrito.items.length === 0) return;

    if (this.carrito.tiene_alertas_stock) {
      alert('Hay prendas en tu carrito que superan el stock disponible. Por favor ajusta las cantidades antes de continuar.');
      return;
    }

    this.compraExitosa = null;
    this.mostrarModalCompra = true;
  }

  cerrarModalCompra(): void {
    if (this.procesandoCompra) return;
    this.mostrarModalCompra = false;
  }

  confirmarCompra(): void {
    if (!this.carrito || this.carrito.items.length === 0) return;
    if (!this.direccionEnvio.trim()) {
      alert('Por favor ingresa una dirección de envío válida.');
      return;
    }

    this.procesandoCompra = true;
    const dto = {
      direccion_envio: this.direccionEnvio.trim(),
      sucursal_id: this.carrito.sucursal_id || undefined,
      items: this.carrito.items.map(item => ({
        producto_id: item.producto_id,
        cantidad: item.cantidad,
        variante_id: item.variante_id
      }))
    };

    this.compraDigitalService.crearOrdenDigital(dto).subscribe({
      next: (orden) => {
        // CU16: Iniciar pago con el método seleccionado (PayPal, QR o Efectivo)
        this.pagoService.iniciarPago(orden.id, this.metodoSeleccionadoId).subscribe({
          next: (pagoRes) => {
            this.procesandoCompra = false;
            this.cartService.vaciarCarrito().subscribe();

            if (pagoRes.requiere_redireccion && pagoRes.url_redireccion) {
              // 1. Redirección OFICIAL a PayPal (Login o Pagar con Tarjeta)
              this.redireccionandoPayPal = true;
              window.location.href = pagoRes.url_redireccion;
            } else if (pagoRes.metodo === 'QR') {
              // 2. Mostrar código QR dinámico con cuenta BCP
              this.compraExitosa = orden;
              this.qrData = pagoRes;
              this.mostrarModalQR = true;
              this.urlComprobante = this.pagoService.getComprobanteUrl(orden.id);
            } else {
              // 3. Pago en Efectivo al retirar en sucursal
              this.compraExitosa = orden;
              this.urlComprobante = this.pagoService.getComprobanteUrl(orden.id);
            }
          },
          error: (err: any) => {
            this.procesandoCompra = false;
            alert(err.error?.detail || 'Error al iniciar el pago.');
          }
        });
      },
      error: (err: any) => {
        this.procesandoCompra = false;
        alert(err.error?.detail || 'Error al procesar la orden digital.');
      }
    });
  }

  cerrarModalQR(): void {
    this.mostrarModalQR = false;
    this.mostrarModalCompra = true;
  }

  abrirComprobante(ordenId?: number): void {
    const id = ordenId || this.compraExitosa?.id;
    if (id) {
      window.open(this.pagoService.getComprobanteUrl(id), '_blank');
    }
  }

  irAMisPedidos(): void {
    this.mostrarModalCompra = false;
    this.mostrarModalQR = false;
    this.router.navigate([this.isAdminView ? '/admin/mis-pedidos' : '/mis-pedidos']);
  }
}

