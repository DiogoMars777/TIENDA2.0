// ==============================================================================
// CU25 - GESTIONAR CAMBIOS Y DEVOLUCIONES DE PRENDAS -> CONTROLADOR REACTIVO (MVC - SIGNALS)
// Ubicación: frontend-web/src/app/controllers/cu25_gestionar_cambios_devoluciones/devolucion.controller.ts
// ==============================================================================

import { Injectable, signal, computed } from '@angular/core';
import { DevolucionService } from '../../services/cu25_gestionar_cambios_devoluciones/devolucion.service';
import {
  DevolucionResponse,
  DevolucionKpisDTO,
  ValidarVentaDevolucionResponse,
  SolicitudDevolucionRequest
} from '../../models/cu25_gestionar_cambios_devoluciones/devolucion.model';

@Injectable({
  providedIn: 'root'
})
export class DevolucionController {
  // Estado Reactivo Principal
  devoluciones = signal<DevolucionResponse[]>([]);
  kpis = signal<DevolucionKpisDTO | null>(null);
  cargando = signal<boolean>(false);
  guardando = signal<boolean>(false);
  validandoVenta = signal<boolean>(false);

  // Filtros y Búsqueda
  filtroTipo = signal<string>('TODOS');
  filtroBusqueda = signal<string>('');

  // Modales
  devolucionSeleccionada = signal<DevolucionResponse | null>(null);
  modalDetalleAbierto = signal<boolean>(false);
  modalNuevaSolicitudAbierto = signal<boolean>(false);
  modalComprobanteAbierto = signal<boolean>(false);
  comprobanteCreado = signal<DevolucionResponse | null>(null);

  // Formulario Asistente Nueva Devolución / Cambio
  ventaIdBusqueda = signal<string>('');
  ventaValidada = signal<ValidarVentaDevolucionResponse | null>(null);
  tipoDevolucion = signal<'CAMBIO_TALLA' | 'CAMBIO_PRENDA' | 'REEMBOLSO_TOTAL' | 'NOTA_CREDITO'>('CAMBIO_TALLA');
  motivoTexto = signal<string>('');
  itemSeleccionadoParaCambio = signal<any | null>(null);
  varianteNuevaId = signal<number | null>(null);
  estadoPrenda = signal<'PERFECTO_ESTADO' | 'DEFECTUOSO_FABRICA' | 'DAÑADO'>('PERFECTO_ESTADO');
  montoReembolso = signal<number>(0);

  // Feedback
  mensajeToast = signal<{ tipo: 'success' | 'error' | 'info'; texto: string } | null>(null);

  // Devoluciones Filtradas (Computed)
  devolucionesFiltradas = computed(() => {
    let items = this.devoluciones();
    const tipo = this.filtroTipo();
    const query = this.filtroBusqueda().trim().toLowerCase();

    if (tipo !== 'TODOS') {
      items = items.filter(d => d.tipo_devolucion === tipo);
    }

    if (query) {
      items = items.filter(d =>
        d.codigo_devolucion.toLowerCase().includes(query) ||
        (d.codigoventa && d.codigoventa.toLowerCase().includes(query)) ||
        (d.cliente_nombre && d.cliente_nombre.toLowerCase().includes(query)) ||
        (d.sucursal_nombre && d.sucursal_nombre.toLowerCase().includes(query)) ||
        d.motivo.toLowerCase().includes(query)
      );
    }

    return items;
  });

  constructor(private service: DevolucionService) {}

  cargarTodo(): void {
    this.cargando.set(true);

    // 1. Cargar KPIs
    this.service.obtenerKpis().subscribe({
      next: (k) => this.kpis.set(k),
      error: (err) => console.error('Error cargando KPIs CU25:', err)
    });

    // 2. Cargar Historial
    this.service.listarDevoluciones(undefined, this.filtroTipo()).subscribe({
      next: (list) => {
        this.devoluciones.set(list);
        this.cargando.set(false);
      },
      error: (err) => {
        this.cargando.set(false);
        this.mostrarToast('error', 'No se pudo cargar el historial de cambios y devoluciones.');
        console.error('Error cargando devoluciones CU25:', err);
      }
    });
  }

  validarVentaParaDevolucion(): void {
    const rawVal = this.ventaIdBusqueda().trim();
    if (!rawVal) {
      this.mostrarToast('error', 'Ingrese el Código de Venta (ej: VTA-SYNC-...) o su ID numérico.');
      return;
    }

    this.validandoVenta.set(true);
    this.ventaValidada.set(null);
    this.itemSeleccionadoParaCambio.set(null);

    this.service.validarVenta(rawVal).subscribe({
      next: (res) => {
        this.validandoVenta.set(false);
        this.ventaValidada.set(res);
        if (!res.venta_valida) {
          this.mostrarToast('error', res.mensaje || 'Venta no válida o no encontrada.');
        } else if (!res.dentro_de_plazo) {
          this.mostrarToast('info', `Aviso: ${res.mensaje}`);
        } else {
          this.mostrarToast('success', 'Venta localizada y apta para cambio o devolución.');
        }
      },
      error: (err) => {
        this.validandoVenta.set(false);
        this.mostrarToast('error', `Error validando venta: ${err.message || 'Error de red'}`);
      }
    });
  }

  seleccionarItemVenta(item: any): void {
    this.itemSeleccionadoParaCambio.set(item);
    if (this.tipoDevolucion() === 'REEMBOLSO_TOTAL' || this.tipoDevolucion() === 'NOTA_CREDITO') {
      this.montoReembolso.set(item.subtotal || item.precio_unitario);
    } else {
      this.montoReembolso.set(0);
    }
  }

  procesarSolicitud(): void {
    const v = this.ventaValidada();
    const it = this.itemSeleccionadoParaCambio();
    const motivo = this.motivoTexto().trim();

    if (!v || !v.venta_valida) {
      this.mostrarToast('error', 'Debe validar primero una venta comercial válida.');
      return;
    }
    if (!it) {
      this.mostrarToast('error', 'Seleccione la prenda de la venta que el cliente desea cambiar o devolver.');
      return;
    }
    if (!motivo) {
      this.mostrarToast('error', 'Por favor detalle el motivo del cambio o devolución.');
      return;
    }

    const payload: SolicitudDevolucionRequest = {
      venta_id: v.venta_id,
      sucursal_id: 1, // Sucursal actual de atención
      tipo_devolucion: this.tipoDevolucion(),
      motivo: motivo,
      monto_reembolso: this.montoReembolso(),
      items: [
        {
          variante_devuelta_id: it.variante_id,
          variante_nueva_id: this.varianteNuevaId() || undefined,
          cantidad: 1,
          precio_unitario: it.precio_unitario,
          subtotal: it.precio_unitario,
          estado_prenda: this.estadoPrenda()
        }
      ]
    };

    this.guardando.set(true);
    this.service.solicitarDevolucion(payload).subscribe({
      next: (res) => {
        this.guardando.set(false);
        this.comprobanteCreado.set(res);
        this.modalNuevaSolicitudAbierto.set(false);
        this.modalComprobanteAbierto.set(true);
        this.mostrarToast('success', `Operación procesada con éxito. Comprobante: ${res.codigo_devolucion}`);
        this.cargarTodo();
      },
      error: (err) => {
        this.guardando.set(false);
        this.mostrarToast('error', `Error procesando cambio/devolución: ${err.error?.detail || err.message}`);
      }
    });
  }

  abrirModalNuevaSolicitud(): void {
    this.ventaIdBusqueda.set('');
    this.ventaValidada.set(null);
    this.itemSeleccionadoParaCambio.set(null);
    this.motivoTexto.set('');
    this.montoReembolso.set(0);
    this.tipoDevolucion.set('CAMBIO_TALLA');
    this.estadoPrenda.set('PERFECTO_ESTADO');
    this.modalNuevaSolicitudAbierto.set(true);
  }

  cerrarModalNuevaSolicitud(): void {
    this.modalNuevaSolicitudAbierto.set(false);
  }

  abrirDetalle(dev: DevolucionResponse): void {
    this.devolucionSeleccionada.set(dev);
    this.modalDetalleAbierto.set(true);
  }

  cerrarDetalle(): void {
    this.modalDetalleAbierto.set(false);
    this.devolucionSeleccionada.set(null);
  }

  cerrarComprobante(): void {
    this.modalComprobanteAbierto.set(false);
    this.comprobanteCreado.set(null);
  }

  imprimirComprobante(): void {
    window.print();
  }

  setFiltroTipo(tipo: string): void {
    this.filtroTipo.set(tipo);
    this.cargarTodo();
  }

  setFiltroBusqueda(val: string): void {
    this.filtroBusqueda.set(val);
  }

  mostrarToast(tipo: 'success' | 'error' | 'info', texto: string): void {
    this.mensajeToast.set({ tipo, texto });
    setTimeout(() => {
      if (this.mensajeToast()?.texto === texto) {
        this.mensajeToast.set(null);
      }
    }, 6000);
  }

  limpiarToast(): void {
    this.mensajeToast.set(null);
  }
}
