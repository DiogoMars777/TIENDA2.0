// ==============================================================================
// CAPA SERVICIO (MVC - SERVICE EN FRONTEND ANGULAR)
// Módulo: CU10 - Gestionar Reservas de Prendas
// Ubicación: frontend-web/src/app/services/cu10_gestionar_reservas_prendas/reservation.service.ts
// ==============================================================================

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, of, catchError, forkJoin, map } from 'rxjs';
import { Reserva, CrearReservaDTO, CancelarReservaDTO } from '../../models/cu10_gestionar_reservas_prendas/reservation.model';
import { CartService } from '../cu9_gestionar_carrito_compras/cart.service';
import { InventoryService } from '../cu8_consultar_catalogo_disponibilidad/inventory.service';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ReservationService {
  private apiUrl = `${environment.apiUrl}/reservas`;

  constructor(
    private http: HttpClient,
    private cartService: CartService,
    private inventoryService: InventoryService
  ) {
    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => {
        if (!this.inventoryService.isOffline()) {
          this.sincronizarReservasOffline().subscribe();
        }
      });
    }
  }

  private getPendingKey(): string {
    const tenantId = localStorage.getItem('tenant_id') || '1';
    return `cu10_reservas_offline_pendientes_tenant_${tenantId}`;
  }

  private getCacheKey(): string {
    const tenantId = localStorage.getItem('tenant_id') || '1';
    return `cu10_reservas_cache_tenant_${tenantId}`;
  }

  public obtenerReservasOfflinePendientes(): Reserva[] {
    try {
      const raw = localStorage.getItem(this.getPendingKey());
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  private guardarReservasOfflinePendientes(lista: Reserva[]): void {
    try {
      localStorage.setItem(this.getPendingKey(), JSON.stringify(lista));
    } catch {}
  }

  private obtenerCacheReservas(): Reserva[] {
    try {
      const raw = localStorage.getItem(this.getCacheKey());
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  private guardarCacheReservas(lista: Reserva[]): void {
    try {
      localStorage.setItem(this.getCacheKey(), JSON.stringify(lista));
    } catch {}
  }

  /** Crea una reserva localmente en el dispositivo cuando no hay internet */
  public crearReservaOfflineLocal(datos: CrearReservaDTO): Reserva {
    const localCart = this.cartService.getLocalCart();
    const sucs = this.inventoryService.getCachedSucursales();
    const suc = sucs.find(s => s.id === Number(datos.sucursal_id)) || sucs[0] || {
      id: Number(datos.sucursal_id) || 1,
      nombre: localCart.sucursal_nombre || 'Sucursal Central',
      ciudad: 'Santa Cruz',
      direccion: 'Av. Principal'
    };

    const randCode = Math.random().toString(36).substring(2, 6).toUpperCase();
    const ahora = new Date();
    const exp = new Date(ahora.getTime() + 48 * 3600 * 1000);

    const detalles = (localCart.items || []).map(it => ({
      variante_id: it.variante_id,
      producto_nombre: it.producto_nombre,
      talla: it.talla,
      color: it.color,
      codigo_hex: it.codigohex || '#1e293b',
      imagen_url: it.imagen_url || undefined,
      precio_unitario: it.precio_unitario,
      cantidad: it.cantidad,
      subtotal: it.subtotal
    }));

    const totalItems = detalles.reduce((s, d) => s + d.cantidad, 0);
    const totalEstimado = Number(detalles.reduce((s, d) => s + d.subtotal, 0).toFixed(2));
    const userName = localStorage.getItem('user_name') || 'Cliente Local';
    const userEmail = localStorage.getItem('user_email') || 'cliente@tienda.com';

    const nuevaReservaOffline: Reserva = {
      id: Date.now(),
      codigo_reserva: `RES-OFF-${randCode}`,
      fecha_reserva: ahora.toISOString(),
      fecha_expiracion: exp.toISOString(),
      horas_restantes: 48,
      estado: 'PENDIENTE',
      observaciones: `[RESERVA OFFLINE PENDIENTE DE SINCRONIZAR] ${datos.observaciones || ''}`.trim(),
      cliente_nombre: userName,
      cliente_email: userEmail,
      sucursal: {
        id: suc.id,
        nombre: suc.nombre,
        ciudad: suc.ciudad || 'Santa Cruz',
        direccion: suc.direccion || 'Sucursal Física',
        telefono: suc.telefono
      },
      detalles: detalles,
      total_items: totalItems,
      total_estimado: totalEstimado
    };

    const pendientes = this.obtenerReservasOfflinePendientes();
    pendientes.unshift(nuevaReservaOffline);
    this.guardarReservasOfflinePendientes(pendientes);

    // Vaciar el carrito local tras convertirlo en reserva offline
    this.cartService.vaciarCarrito().subscribe();
    return nuevaReservaOffline;
  }

  /** Sincroniza con el backend todas las reservas creadas sin internet */
  public sincronizarReservasOffline(): Observable<Reserva[]> {
    const pendientes = this.obtenerReservasOfflinePendientes();
    if (pendientes.length === 0 || this.inventoryService.isOffline()) {
      return of([]);
    }

    const peticiones = pendientes.map(r => {
      const payload: any = {
        sucursal_id: r.sucursal?.id || 1,
        observaciones: (r.observaciones || '').replace('[RESERVA OFFLINE PENDIENTE DE SINCRONIZAR]', '[Sincronizada desde Reserva Offline]').trim(),
        items: (r.detalles || []).map(d => ({
          variante_id: d.variante_id,
          cantidad: d.cantidad
        }))
      };
      return this.http.post<Reserva>(this.apiUrl, payload).pipe(
        catchError(err => {
          console.warn('Error sincronizando reserva offline:', err);
          return of(null as any);
        })
      );
    });

    return forkJoin(peticiones).pipe(
      map(resultados => resultados.filter(Boolean)),
      tap(creadas => {
        if (creadas.length > 0) {
          this.guardarReservasOfflinePendientes([]);
        }
      })
    );
  }

  /** CU10: Convierte el carrito en una reserva en sucursal física (soporta modo offline) */
  crearReserva(datos: CrearReservaDTO): Observable<Reserva> {
    if (this.inventoryService.isOffline()) {
      return of(this.crearReservaOfflineLocal(datos));
    }

    const localCart = this.cartService.getLocalCart();
    const payload: any = {
      ...datos,
      items: (localCart.items || []).map(it => ({
        variante_id: it.variante_id,
        cantidad: it.cantidad
      }))
    };

    return this.http.post<Reserva>(this.apiUrl, payload).pipe(
      tap(() => this.cartService.vaciarCarrito().subscribe()),
      catchError(() => of(this.crearReservaOfflineLocal(datos)))
    );
  }

  /** CU10: Consulta el listado de reservas del cliente actual combinando pendientes offline */
  getMisReservas(): Observable<Reserva[]> {
    const offlinePendientes = this.obtenerReservasOfflinePendientes();
    if (this.inventoryService.isOffline()) {
      return of([...offlinePendientes, ...this.obtenerCacheReservas()]);
    }

    return this.http.get<Reserva[]>(`${this.apiUrl}/mis-reservas`).pipe(
      tap(remotas => this.guardarCacheReservas(remotas)),
      map(remotas => [...offlinePendientes, ...remotas]),
      catchError(() => of([...offlinePendientes, ...this.obtenerCacheReservas()]))
    );
  }

  /** CU10: Consulta una reserva específica por ID o código único */
  getReserva(idOCodigo: string | number): Observable<Reserva> {
    const pendientes = this.obtenerReservasOfflinePendientes();
    const localMatch = pendientes.find(r => r.id === Number(idOCodigo) || r.codigo_reserva === String(idOCodigo).toUpperCase());
    if (localMatch) return of(localMatch);
    return this.http.get<Reserva>(`${this.apiUrl}/${idOCodigo}`);
  }

  /** CU10: Cancela una reserva pendiente y libera el stock reservado */
  cancelarReserva(reservaId: number, motivo?: string): Observable<Reserva> {
    const pendientes = this.obtenerReservasOfflinePendientes();
    const idx = pendientes.findIndex(r => r.id === reservaId);
    if (idx !== -1) {
      const cancelada = { ...pendientes[idx], estado: 'CANCELADA' as const };
      pendientes.splice(idx, 1);
      this.guardarReservasOfflinePendientes(pendientes);
      return of(cancelada);
    }

    const payload: CancelarReservaDTO = { motivo };
    return this.http.patch<Reserva>(`${this.apiUrl}/${reservaId}/cancelar`, payload);
  }

  /** CU11: Listado general de reservas para administración y encargados de sucursal */
  getReservasAdmin(sucursalId?: number | null, estado?: string | null): Observable<Reserva[]> {
    const offlinePendientes = this.obtenerReservasOfflinePendientes();
    if (this.inventoryService.isOffline()) {
      let combinadas = [...offlinePendientes, ...this.obtenerCacheReservas()];
      if (sucursalId) combinadas = combinadas.filter(r => r.sucursal?.id === sucursalId);
      if (estado && estado !== 'TODAS') combinadas = combinadas.filter(r => r.estado === estado);
      return of(combinadas);
    }

    let params: any = {};
    if (sucursalId) params.sucursal_id = sucursalId;
    if (estado && estado !== 'TODAS') params.estado = estado;
    return this.http.get<Reserva[]>(`${this.apiUrl}/admin/listado`, { params }).pipe(
      tap(remotas => {
        if (!sucursalId && (!estado || estado === 'TODAS')) {
          this.guardarCacheReservas(remotas);
        }
      }),
      map(remotas => {
        let pendientesFiltradas = offlinePendientes;
        if (sucursalId) pendientesFiltradas = pendientesFiltradas.filter(r => r.sucursal?.id === sucursalId);
        if (estado && estado !== 'TODAS') pendientesFiltradas = pendientesFiltradas.filter(r => r.estado === estado);
        return [...pendientesFiltradas, ...remotas];
      }),
      catchError(() => {
        let combinadas = [...offlinePendientes, ...this.obtenerCacheReservas()];
        if (sucursalId) combinadas = combinadas.filter(r => r.sucursal?.id === sucursalId);
        if (estado && estado !== 'TODAS') combinadas = combinadas.filter(r => r.estado === estado);
        return of(combinadas);
      })
    );
  }

  /** CU11: Búsqueda rápida por código alfanumérico para el punto de atención */
  buscarPorCodigo(codigo: string): Observable<Reserva> {
    const codigoLimpio = codigo.trim().toUpperCase();
    const todasLocal = [...this.obtenerReservasOfflinePendientes(), ...this.obtenerCacheReservas()];
    const localMatch = todasLocal.find(r => r.codigo_reserva.toUpperCase() === codigoLimpio);

    if (this.inventoryService.isOffline() && localMatch) {
      return of(localMatch);
    }

    return this.http.get<Reserva>(`${this.apiUrl}/admin/buscar/${codigoLimpio}`).pipe(
      catchError(err => {
        if (localMatch) return of(localMatch);
        throw err;
      })
    );
  }

  /** Marca una reserva en caché local como ENTREGADA tras un Pago Offline en Caja */
  public marcarPagadaOfflineEnCache(reservaId: number, nroReciboOffline: string): void {
    const cache = this.obtenerCacheReservas();
    const item = cache.find(r => r.id === reservaId);
    if (item) {
      item.observaciones = `${item.observaciones || ''} [Cobro Offline Emitido: ${nroReciboOffline}]`.trim();
      this.guardarCacheReservas(cache);
    }
    const pendientes = this.obtenerReservasOfflinePendientes();
    const pItem = pendientes.find(r => r.id === reservaId);
    if (pItem) {
      pItem.observaciones = `${pItem.observaciones || ''} [Cobro Offline Emitido: ${nroReciboOffline}]`.trim();
      this.guardarReservasOfflinePendientes(pendientes);
    }
  }

  /** CU11: Atender reserva en caja/mostrador (Entregar y cobrar o Cancelar) */
  atenderReserva(reservaId: number, accion: 'ENTREGAR' | 'CANCELAR', observaciones?: string): Observable<Reserva> {
    const payload = {
      accion: accion,
      observaciones: observaciones
    };
    return this.http.post<Reserva>(`${this.apiUrl}/${reservaId}/atender`, payload);
  }
}
