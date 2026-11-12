// ==============================================================================
// CU22 - REGISTRAR COBROS DE CONTADO SIN CONEXIÓN -> COMPONENTE VISTA
// Ubicación: frontend-web/src/app/views/cu22_registrar_cobros_contado_offline/cobro-offline-list/cobro-offline-list.component.ts
// ==============================================================================

import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';

import { CobroOfflineController } from '../../../controllers/cu22_registrar_cobros_contado_offline/cobro-offline.controller';
import {
  RegistroCobroOfflineRequest,
  ItemCobroOfflineDTO,
  CobroOfflineDTO
} from '../../../models/cu22_registrar_cobros_contado_offline/cobro-offline.model';
import { SucursalService } from '../../../services/cu4_gestionar_sucursales/sucursal.service';
import { Sucursal } from '../../../models/cu4_gestionar_sucursales/sucursal.model';
import { InventarioService } from '../../../services/cu13_gestionar_inventario_movimientos/inventario.service';
import { ProductService } from '../../../services/cu5_gestionar_productos/product.service';

export interface PrendaCatalogoOffline {
  variante_id: number;
  nombre: string;
  talla: string;
  color: string;
  precio: number;
}

@Component({
  selector: 'app-cobro-offline-list',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule],
  templateUrl: './cobro-offline-list.component.html',
  styleUrls: ['./cobro-offline-list.component.css']
})
export class CobroOfflineListComponent implements OnInit {

  tenantNombre: string = 'Mi Tienda';
  tenantId: string = '1';
  sucursales: Sucursal[] = [];

  // Catálogo dinámico de prendas pertenecientes exclusivamente al Tenant actual
  catalogoPrendas: PrendaCatalogoOffline[] = [];

  itemSeleccionadoIdx: number = 0;

  // Formulario de Cobro en Contingencia
  cobroForm: RegistroCobroOfflineRequest = {
    sucursal_id: 1,
    monto: 0,
    moneda: 'BOB',
    nro_recibo_provisional: '',
    uuid_operacion: '',
    cliente_nombre: 'Cliente Mostrador',
    cliente_nit: '0',
    efectivo_recibido: 0,
    cambio: 0,
    observaciones: 'Cobro de contado generado bajo régimen de contingencia offline',
    items: []
  };

  constructor(
    public ctrl: CobroOfflineController,
    private sucursalService: SucursalService,
    private inventarioService: InventarioService,
    private productService: ProductService
  ) {}

  ngOnInit(): void {
    this.tenantId = localStorage.getItem('tenant_id') || '1';
    this.tenantNombre = localStorage.getItem('tenant_nombre') || 'Mi Empresa';

    // Cargar caché local de productos e inventario del tenant por si está en modo offline
    this.cargarCacheCatalogoTenant();

    this.sucursalService.obtenerSucursales(undefined, undefined, true).subscribe({
      next: (sucs) => {
        if (sucs && sucs.length > 0) {
          this.sucursales = sucs;
          this.cobroForm.sucursal_id = sucs[0].id;
          localStorage.setItem(`sucursales_offline_tenant_${this.tenantId}`, JSON.stringify(sucs));
          this.cargarProductosDelTenant(sucs[0].id);
        } else {
          this.cargarProductosDelTenant();
        }
      },
      error: () => {
        this.cargarProductosDelTenant();
      }
    });
    this.ctrl.cargarTodo();
  }

  private cargarCacheCatalogoTenant(): void {
    try {
      const sucsCache = localStorage.getItem(`sucursales_offline_tenant_${this.tenantId}`);
      if (sucsCache) {
        this.sucursales = JSON.parse(sucsCache);
        if (this.sucursales.length > 0) {
          this.cobroForm.sucursal_id = this.sucursales[0].id;
        }
      }
      const catCache = localStorage.getItem(`catalogo_offline_tenant_${this.tenantId}`);
      if (catCache) {
        this.catalogoPrendas = JSON.parse(catCache);
      }
    } catch {}
  }

  cargarProductosDelTenant(sucursalId?: number): void {
    this.inventarioService.getInventario(sucursalId).subscribe({
      next: (items) => {
        if (items && items.length > 0) {
          const mapa = new Map<number, PrendaCatalogoOffline>();
          for (const it of items) {
            if (!mapa.has(it.variante_id)) {
              mapa.set(it.variante_id, {
                variante_id: it.variante_id,
                nombre: it.producto_nombre,
                talla: it.talla || it.talla_nombre || 'M',
                color: it.color || it.color_nombre || 'Estándar',
                precio: Number(it.producto_precio) || 100
              });
            }
          }
          this.catalogoPrendas = Array.from(mapa.values());
          this.itemSeleccionadoIdx = 0;
          localStorage.setItem(`catalogo_offline_tenant_${this.tenantId}`, JSON.stringify(this.catalogoPrendas));
        } else {
          this.cargarDesdeProductosFallback();
        }
      },
      error: () => {
        this.cargarDesdeProductosFallback();
      }
    });
  }

  private cargarDesdeProductosFallback(): void {
    this.productService.obtenerProductos(undefined, undefined, undefined, true).subscribe({
      next: (prods) => {
        if (prods && prods.length > 0) {
          this.catalogoPrendas = prods.map(p => ({
            variante_id: p.id,
            nombre: p.nombre,
            talla: 'M',
            color: 'Estándar',
            precio: Number(p.preciobase) || 100
          }));
          this.itemSeleccionadoIdx = 0;
          localStorage.setItem(`catalogo_offline_tenant_${this.tenantId}`, JSON.stringify(this.catalogoPrendas));
        }
      },
      error: () => {}
    });
  }

  onCambioSucursalCobro(): void {
    if (this.cobroForm.sucursal_id && !this.ctrl.enModoOffline()) {
      this.cargarProductosDelTenant(Number(this.cobroForm.sucursal_id));
    }
  }

  actualizarFiltro(event: Event): void {
    const valor = (event.target as HTMLInputElement).value;
    this.ctrl.filtroTexto.set(valor);
  }

  abrirModalNuevoCobro(): void {
    const ahora = new Date();
    // Obtener fecha oficial en la zona horaria de Bolivia (America/La_Paz, UTC-4)
    const fechaBolivia = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'America/La_Paz',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    }).format(ahora);
    const fechaStr = fechaBolivia.replace(/-/g, '');
    const randNum = Math.floor(1000 + Math.random() * 9000);
    const defaultSucId = this.sucursales.length > 0 ? this.sucursales[0].id : 1;

    this.cobroForm = {
      sucursal_id: defaultSucId,
      monto: 0,
      moneda: 'BOB',
      nro_recibo_provisional: `REC-OFF-${fechaStr}-${randNum}`,
      uuid_operacion: `pos-off-${Date.now()}-${randNum}`,
      cliente_nombre: 'Cliente Mostrador',
      cliente_nit: '0',
      efectivo_recibido: 0,
      cambio: 0,
      observaciones: 'Cobro de contado emitido bajo contingencia de red',
      fecha_cobro: ahora.toISOString(),
      items: []
    };

    // Agregar prenda inicial por conveniencia
    this.agregarPrendaSeleccionada();
    this.ctrl.abrirModalNuevoCobro();
  }

  agregarPrendaSeleccionada(): void {
    const sel = this.catalogoPrendas[this.itemSeleccionadoIdx];
    if (!sel) return;

    if (!this.cobroForm.items) {
      this.cobroForm.items = [];
    }

    const itemExistente = this.cobroForm.items.find(it => it.variante_id === sel.variante_id);
    if (itemExistente) {
      itemExistente.cantidad += 1;
      itemExistente.subtotal = itemExistente.cantidad * itemExistente.precio_unitario;
    } else {
      this.cobroForm.items.push({
        variante_id: sel.variante_id,
        producto_nombre: sel.nombre,
        talla: sel.talla,
        color: sel.color,
        cantidad: 1,
        precio_unitario: sel.precio,
        subtotal: sel.precio
      });
    }

    this.recalcularTotales();
  }

  eliminarItem(index: number): void {
    if (!this.cobroForm.items) return;
    this.cobroForm.items.splice(index, 1);
    this.recalcularTotales();
  }

  recalcularTotales(): void {
    if (!this.cobroForm.items || this.cobroForm.items.length === 0) {
      this.cobroForm.monto = 0;
      this.calcularCambio();
      return;
    }

    let total = 0;
    for (const it of this.cobroForm.items) {
      it.subtotal = it.cantidad * it.precio_unitario;
      total += it.subtotal;
    }
    this.cobroForm.monto = total;

    // Si aún no se ingresó efectivo o es menor, ajustar sugerencia
    if (!this.cobroForm.efectivo_recibido || this.cobroForm.efectivo_recibido < total) {
      this.cobroForm.efectivo_recibido = Math.ceil(total / 10) * 10;
    }
    this.calcularCambio();
  }

  calcularCambio(): void {
    const recibido = this.cobroForm.efectivo_recibido || 0;
    const monto = this.cobroForm.monto || 0;
    this.cobroForm.cambio = Math.max(0, recibido - monto);
  }

  confirmarCobroOffline(): void {
    this.ctrl.registrarCobro(this.cobroForm, (cobroCreado: CobroOfflineDTO) => {
      // Abrir inmediatamente la vista de ticket para entrega al cliente
      this.ctrl.verTicket(cobroCreado);
    });
  }

  calcularTotalMonto(): number {
    return this.ctrl.cobros().reduce((sum, c) => sum + (Number(c.monto) || 0), 0);
  }

  calcularPendientesCount(): number {
    return this.ctrl.cobros().filter(c => !c.sincronizado).length;
  }
}
