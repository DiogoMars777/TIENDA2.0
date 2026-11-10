// ==============================================================================
// CAPA VISTA / CONTROLADOR (MVC - VIEW & CONTROLLER EN FRONTEND ANGULAR)
// Módulo: CU08 - Consultar Catálogo y Disponibilidad de Inventario
// Ubicación: frontend-web/src/app/views/cu8_consultar_catalogo_disponibilidad/product-catalog/product-catalog.component.ts
// ==============================================================================

import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

import { InventoryService } from '../../../services/cu8_consultar_catalogo_disponibilidad/inventory.service';
import { CartService } from '../../../services/cu9_gestionar_carrito_compras/cart.service';
import { ReservationService } from '../../../services/cu10_gestionar_reservas_prendas/reservation.service';
import { AuthService } from '../../../core/services/auth.service';
import { VirtualFittingModalComponent } from '../../cu12_vestidor_virtual_ia/virtual-fitting-modal/virtual-fitting-modal.component';
import {
  ProductoCatalogoItem,
  SucursalItem,
  DisponibilidadProducto,
  DisponibilidadVariante
} from '../../../models/cu8_consultar_catalogo_disponibilidad/catalogo.model';

@Component({
  selector: 'app-product-catalog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatIconModule,
    MatButtonModule,
    MatSelectModule,
    MatFormFieldModule,
    MatInputModule,
    MatChipsModule,
    MatTooltipModule,
    VirtualFittingModalComponent
  ],
  templateUrl: './product-catalog.component.html',
  styleUrls: ['./product-catalog.component.css']
})
export class ProductCatalogComponent implements OnInit, OnDestroy {
  // Datos principales
  productos: ProductoCatalogoItem[] = [];
  sucursales: SucursalItem[] = [];
  loading = true;

  // CU12: Probador Virtual con IA
  vestidorModalAbierto = false;
  productoParaVestidor: any = null;
  varianteParaVestidor: any = null;

  // Estado reactivo offline y de datos desactualizados (CU08 Requerimiento)
  datosDesactualizados = false;
  offlineMode = false;
  ultimaSincronizacion: string | null = null;
  private subs: Subscription = new Subscription();

  // Filtros interactivos y búsqueda reactiva
  sucursalSeleccionadaId: number | null = null;
  generoSeleccionado: string = 'TODOS';
  searchTerm: string = '';
  soloDisponibles: boolean = false;
  private searchSubject = new Subject<string>();

  // Mapa de variante seleccionada por producto (id_producto -> variante)
  variantesSeleccionadas: { [productoId: number]: DisponibilidadVariante } = {};

  // Estado del Modal de Disponibilidad Multitienda
  modalDisponibilidadAbierto = false;
  productoDisponibilidad: DisponibilidadProducto | null = null;
  cargandoDisponibilidad = false;

  // Carrito local rápido (contador para el header)
  itemsCarritoCount = 0;
  isAdmin = false;
  isAdminView = false;
  tenantNombre = 'Mi Tienda';

  constructor(
    public inventoryService: InventoryService,
    private cartService: CartService,
    private reservationService: ReservationService,
    public authService: AuthService,
    private router: Router
  ) {
    this.isAdminView = this.router.url.startsWith('/admin');
  }

  ngOnInit(): void {
    this.isAdmin = this.authService.isAdmin();
    this.tenantNombre = localStorage.getItem('tenant_nombre') || 'Shopyn Golden Store';
    this.cargarSucursales();
    this.cargarCatalogo();

    // Sincronizar contador del carrito
    this.subs.add(
      this.cartService.cartCount$.subscribe((count: number) => {
        this.itemsCarritoCount = count;
      })
    );

    // Búsqueda con debounce reactivo de 300ms
    this.subs.add(
      this.searchSubject.pipe(
        debounceTime(300),
        distinctUntilChanged()
      ).subscribe((term: string) => {
        this.searchTerm = term;
        this.cargarCatalogo();
      })
    );

    // Suscripción al estado de sincronización y offline (CU08)
    this.subs.add(
      this.inventoryService.datosDesactualizados$.subscribe((desactualizados: boolean) => {
        this.datosDesactualizados = desactualizados;
      })
    );
    this.subs.add(
      this.inventoryService.offlineMode$.subscribe((offline: boolean) => {
        this.offlineMode = offline;
      })
    );
    this.subs.add(
      this.inventoryService.ultimaSincronizacion$.subscribe((ts: string | null) => {
        this.ultimaSincronizacion = ts;
      })
    );
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
  }

  cargarSucursales(): void {
    this.inventoryService.obtenerSucursales().subscribe({
      next: (data: SucursalItem[]) => {
        this.sucursales = data;
        // Por defecto pre-seleccionar la primera sucursal si existe y ninguna estaba seleccionada
        if (data && data.length > 0 && !this.sucursalSeleccionadaId) {
          this.sucursalSeleccionadaId = data[0].id;
          this.cargarCatalogo();
        }
      },
      error: (err: any) => console.error('[CU08 VIEW] Error al cargar sucursales:', err)
    });
  }

  cargarCatalogo(): void {
    this.loading = true;
    this.inventoryService.consultarCatalogo(
      this.sucursalSeleccionadaId,
      null,
      this.generoSeleccionado,
      this.searchTerm,
      this.soloDisponibles
    ).subscribe({
      next: (data: ProductoCatalogoItem[]) => {
        this.productos = data;
        // Auto-seleccionar la primera variante con stock para cada producto
        this.productos.forEach((p: ProductoCatalogoItem) => {
          if (p.variantes && p.variantes.length > 0) {
            const conStock = p.variantes.find((v: DisponibilidadVariante) => v.stock > 0);
            this.variantesSeleccionadas[p.id] = conStock || p.variantes[0];
          }
        });
        this.loading = false;
      },
      error: (err: any) => {
        console.error('[CU08 VIEW] Error al consultar catálogo:', err);
        this.loading = false;
      }
    });
  }

  onCambioSucursal(): void {
    this.cargarCatalogo();
  }

  onFiltroGenero(genero: string): void {
    this.generoSeleccionado = genero;
    this.cargarCatalogo();
  }

  onBusqueda(): void {
    this.searchSubject.next(this.searchTerm);
  }

  toggleSoloDisponibles(): void {
    this.soloDisponibles = !this.soloDisponibles;
    this.cargarCatalogo();
  }

  seleccionarVariante(productoId: number, variante: DisponibilidadVariante): void {
    this.variantesSeleccionadas[productoId] = variante;
  }

  getVarianteSeleccionada(productoId: number): DisponibilidadVariante | null {
    return this.variantesSeleccionadas[productoId] || null;
  }

  getNombreSucursalActual(): string {
    if (!this.sucursalSeleccionadaId) return 'Todas las sucursales';
    const suc = this.sucursales.find((s: SucursalItem) => s.id === this.sucursalSeleccionadaId);
    return suc ? suc.nombre : 'Sucursal seleccionada';
  }

  // --- CU08: Modal de Disponibilidad Multitienda ---
  abrirModalDisponibilidad(productoId: number): void {
    this.cargandoDisponibilidad = true;
    this.modalDisponibilidadAbierto = true;
    this.productoDisponibilidad = null;

    this.inventoryService.consultarDisponibilidad(productoId).subscribe({
      next: (data: DisponibilidadProducto) => {
        this.productoDisponibilidad = data;
        this.cargandoDisponibilidad = false;
      },
      error: (err: any) => {
        console.error('[CU08 VIEW] Error al consultar disponibilidad:', err);
        this.cargandoDisponibilidad = false;
      }
    });
  }

  cerrarModalDisponibilidad(): void {
    this.modalDisponibilidadAbierto = false;
    this.productoDisponibilidad = null;
  }

  toggleModoOffline(): void {
    const ahoraOffline = this.inventoryService.toggleModoOfflineSimulado();
    if (!ahoraOffline) {
      this.reservationService.sincronizarReservasOffline().subscribe({
        next: (creadas) => {
          if (creadas && creadas.length > 0) {
            alert(`🟢 Conexión restablecida: Se sincronizaron automáticamente ${creadas.length} reserva(s) creada(s) sin internet con el servidor central.`);
          }
          this.cargarSucursales();
          this.cargarCatalogo();
        }
      });
    } else {
      this.cargarCatalogo();
    }
  }

  agregarAlCarrito(producto: ProductoCatalogoItem): void {
    const variante = this.getVarianteSeleccionada(producto.id);
    if (!variante || variante.stock <= 0) return;

    this.cartService.agregarItem(variante.variante_id, 1, this.sucursalSeleccionadaId).subscribe({
      next: () => {
        const modoTxt = this.offlineMode ? ' (Guardado en Carrito Local Offline)' : '';
        alert(`¡Añadido al carrito${modoTxt}!\n${producto.nombre}\nTalla: ${variante.talla} | Color: ${variante.color}`);
      },
      error: (err: any) => {
        alert(err.error?.detail || 'Error al agregar al carrito');
      }
    });
  }

  // --- CU12: Métodos de Probador Virtual con IA ---
  abrirVestidor(producto: ProductoCatalogoItem): void {
    this.productoParaVestidor = producto;
    this.varianteParaVestidor = this.getVarianteSeleccionada(producto.id) || (producto.variantes && producto.variantes[0]) || null;
    this.vestidorModalAbierto = true;
  }

  cerrarVestidor(): void {
    this.vestidorModalAbierto = false;
    this.productoParaVestidor = null;
    this.varianteParaVestidor = null;
  }

  onAgregarDesdeVestidor(event: any): void {
    if (!event.producto) return;
    const matchVar = event.producto.variantes?.find((v: any) => v.talla === event.talla && v.color === event.color)
      || event.producto.variantes?.[0];

    if (matchVar) {
      this.cartService.agregarItem(matchVar.variante_id, 1, this.sucursalSeleccionadaId).subscribe({
        next: () => {
          alert(`¡Prenda probada en el Vestidor Virtual añadida a tu carrito con éxito!\n${event.producto.nombre}\nTalla: ${event.talla} | Color: ${event.color}`);
        },
        error: (err: any) => alert(err.error?.detail || 'Error al agregar al carrito')
      });
    } else {
      alert('Prenda seleccionada añadida al carrito.');
    }
  }
}
