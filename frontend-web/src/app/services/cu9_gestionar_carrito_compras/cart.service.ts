// ==============================================================================
// CAPA SERVICIO (MVC - SERVICE EN FRONTEND ANGULAR)
// Módulo: CU09 - Gestionar Carrito de Compras
// Ubicación: frontend-web/src/app/services/cu9_gestionar_carrito_compras/cart.service.ts
// ==============================================================================

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap, map, of, catchError } from 'rxjs';
import { Carrito, CarritoItem, AgregarItemCarritoDTO } from '../../models/cu9_gestionar_carrito_compras/carrito.model';
import { InventoryService } from '../cu8_consultar_catalogo_disponibilidad/inventory.service';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class CartService {
  private apiUrl = `${environment.apiUrl}/carrito`;

  // Estado reactivo del Carrito
  private cartSubject = new BehaviorSubject<Carrito | null>(null);
  public cart$ = this.cartSubject.asObservable();
  public carrito$ = this.cart$; // Alias canónico en español

  // Observables derivados para la UI
  public cartCount$ = this.cart$.pipe(map(c => c ? c.total_items : 0));
  public totalItems$ = this.cartCount$; // Alias canónico en español

  public cartTotal$ = this.cart$.pipe(map(c => c ? c.total_precio : 0));
  public totalPrecio$ = this.cartTotal$; // Alias canónico en español

  constructor(
    private http: HttpClient,
    private inventoryService: InventoryService
  ) {
    this.obtenerCarrito().subscribe({
      error: (err: any) => console.warn('[CU09 SERVICE] Inicialización de carrito silenciosa:', err)
    });
  }

  private getCartKey(): string {
    const tenantId = localStorage.getItem('tenant_id') || '1';
    return `cu09_carrito_cache_tenant_${tenantId}`;
  }

  public getLocalCart(): Carrito {
    try {
      const raw = localStorage.getItem(this.getCartKey());
      if (raw) {
        return JSON.parse(raw);
      }
    } catch {}
    const sucs = this.inventoryService.getCachedSucursales();
    const defaultSuc = sucs.length > 0 ? sucs[0] : null;
    return {
      carrito_id: 1,
      sucursal_id: defaultSuc ? defaultSuc.id : 1,
      sucursal_nombre: defaultSuc ? defaultSuc.nombre : 'Sucursal Central',
      items: [],
      total_items: 0,
      total_precio: 0,
      tiene_alertas_stock: false
    };
  }

  private saveLocalCart(c: Carrito): Carrito {
    c.total_items = c.items.reduce((sum, it) => sum + it.cantidad, 0);
    c.total_precio = Number(c.items.reduce((sum, it) => sum + (it.cantidad * it.precio_unitario), 0).toFixed(2));
    c.tiene_alertas_stock = c.items.some(it => !it.stock_suficiente);
    try {
      localStorage.setItem(this.getCartKey(), JSON.stringify(c));
    } catch {}
    this.cartSubject.next(c);
    return c;
  }

  /** Consulta el carrito activo desde la API de FastAPI o caché local si está offline */
  obtenerCarrito(): Observable<Carrito> {
    if (this.inventoryService.isOffline()) {
      const local = this.getLocalCart();
      this.cartSubject.next(local);
      return of(local);
    }

    return this.http.get<Carrito>(this.apiUrl).pipe(
      tap(carrito => {
        this.saveLocalCart(carrito);
      }),
      catchError(() => {
        const local = this.getLocalCart();
        this.cartSubject.next(local);
        return of(local);
      })
    );
  }

  /** Alias retrocompatible para obtenerCarrito */
  cargarCarrito(): Observable<Carrito> {
    return this.obtenerCarrito();
  }

  /** Agrega una prenda o variante al carrito (soporta modo offline) */
  agregarItem(varianteId: number, cantidad: number = 1, sucursalId?: number | null): Observable<Carrito> {
    if (this.inventoryService.isOffline()) {
      return of(this.agregarItemLocal(varianteId, cantidad, sucursalId));
    }

    const payload: AgregarItemCarritoDTO = {
      variante_id: varianteId,
      cantidad: cantidad,
      sucursal_id: sucursalId
    };

    return this.http.post<Carrito>(`${this.apiUrl}/items`, payload).pipe(
      tap(carrito => this.saveLocalCart(carrito)),
      catchError(() => of(this.agregarItemLocal(varianteId, cantidad, sucursalId)))
    );
  }

  private agregarItemLocal(varianteId: number, cantidad: number, sucursalId?: number | null): Carrito {
    const cart = this.getLocalCart();
    if (sucursalId) {
      cart.sucursal_id = sucursalId;
      const suc = this.inventoryService.getCachedSucursales().find(s => s.id === sucursalId);
      if (suc) cart.sucursal_nombre = suc.nombre;
    }

    const existente = cart.items.find(it => it.variante_id === varianteId);
    if (existente) {
      existente.cantidad += cantidad;
      existente.subtotal = Number((existente.cantidad * existente.precio_unitario).toFixed(2));
      existente.stock_suficiente = existente.cantidad <= existente.stock_disponible;
      return this.saveLocalCart(cart);
    }

    // Buscar datos de la prenda en la caché local del catálogo
    const catalogo = this.inventoryService.getCachedCatalogoItems();
    let prodMatch: any = null;
    let varMatch: any = null;
    for (const p of catalogo) {
      const v = (p.variantes || []).find(vx => vx.variante_id === varianteId);
      if (v) {
        prodMatch = p;
        varMatch = v;
        break;
      }
    }

    const precio = varMatch ? Number(varMatch.precio) : (prodMatch ? Number(prodMatch.preciobase) : 120);
    const stockDisp = varMatch ? Number(varMatch.stock) : 10;
    const nuevoItem: CarritoItem = {
      item_id: Date.now(),
      variante_id: varianteId,
      producto_id: prodMatch ? prodMatch.id : varianteId,
      producto_nombre: prodMatch ? prodMatch.nombre : `Prenda #${varianteId}`,
      sku: varMatch?.sku || `SKU-${varianteId}`,
      talla: varMatch?.talla || 'M',
      color: varMatch?.color || 'Estándar',
      codigohex: varMatch?.codigohex || '#1e293b',
      imagen_url: prodMatch?.imagenprincipal || null,
      precio_unitario: precio,
      cantidad: cantidad,
      subtotal: Number((precio * cantidad).toFixed(2)),
      stock_disponible: stockDisp,
      stock_suficiente: cantidad <= stockDisp
    };
    cart.items.push(nuevoItem);
    return this.saveLocalCart(cart);
  }

  /** Modifica la cantidad solicitada de una prenda */
  actualizarCantidad(varianteId: number, cantidad: number): Observable<Carrito> {
    if (this.inventoryService.isOffline()) {
      const cart = this.getLocalCart();
      const it = cart.items.find(x => x.variante_id === varianteId);
      if (it) {
        it.cantidad = cantidad;
        it.subtotal = Number((it.cantidad * it.precio_unitario).toFixed(2));
        it.stock_suficiente = it.cantidad <= it.stock_disponible;
      }
      return of(this.saveLocalCart(cart));
    }

    return this.http.put<Carrito>(`${this.apiUrl}/items/${varianteId}`, { cantidad }).pipe(
      tap(carrito => this.saveLocalCart(carrito)),
      catchError(() => {
        const cart = this.getLocalCart();
        const it = cart.items.find(x => x.variante_id === varianteId);
        if (it) {
          it.cantidad = cantidad;
          it.subtotal = Number((it.cantidad * it.precio_unitario).toFixed(2));
          it.stock_suficiente = it.cantidad <= it.stock_disponible;
        }
        return of(this.saveLocalCart(cart));
      })
    );
  }

  /** Elimina una prenda del carrito */
  eliminarItem(varianteId: number): Observable<Carrito> {
    if (this.inventoryService.isOffline()) {
      const cart = this.getLocalCart();
      cart.items = cart.items.filter(x => x.variante_id !== varianteId);
      return of(this.saveLocalCart(cart));
    }

    return this.http.delete<Carrito>(`${this.apiUrl}/items/${varianteId}`).pipe(
      tap(carrito => this.saveLocalCart(carrito)),
      catchError(() => {
        const cart = this.getLocalCart();
        cart.items = cart.items.filter(x => x.variante_id !== varianteId);
        return of(this.saveLocalCart(cart));
      })
    );
  }

  /** Asigna la tienda física de retiro o compra */
  asignarSucursal(sucursalId: number): Observable<Carrito> {
    if (this.inventoryService.isOffline()) {
      const cart = this.getLocalCart();
      cart.sucursal_id = sucursalId;
      const suc = this.inventoryService.getCachedSucursales().find(s => s.id === sucursalId);
      if (suc) cart.sucursal_nombre = suc.nombre;
      return of(this.saveLocalCart(cart));
    }

    return this.http.patch<Carrito>(`${this.apiUrl}/sucursal`, { sucursal_id: sucursalId }).pipe(
      tap(carrito => this.saveLocalCart(carrito)),
      catchError(() => {
        const cart = this.getLocalCart();
        cart.sucursal_id = sucursalId;
        const suc = this.inventoryService.getCachedSucursales().find(s => s.id === sucursalId);
        if (suc) cart.sucursal_nombre = suc.nombre;
        return of(this.saveLocalCart(cart));
      })
    );
  }

  /** Vacía todos los ítems del carrito */
  vaciarCarrito(): Observable<Carrito> {
    if (this.inventoryService.isOffline()) {
      const cart = this.getLocalCart();
      cart.items = [];
      return of(this.saveLocalCart(cart));
    }

    return this.http.delete<Carrito>(this.apiUrl).pipe(
      tap(carrito => this.saveLocalCart(carrito)),
      catchError(() => {
        const cart = this.getLocalCart();
        cart.items = [];
        return of(this.saveLocalCart(cart));
      })
    );
  }
}
