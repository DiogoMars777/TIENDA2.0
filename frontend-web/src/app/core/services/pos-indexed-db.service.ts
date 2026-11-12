// ==============================================================================
// CORE SERVICE: MOTOR DE BASE DE DATOS LOCAL EN EL NAVEGADOR (INDEXEDDB)
// Módulo: CU14 / CU22 - Punto de Venta (POS) Offline-First con Sincronización
// Ubicación: frontend-web/src/app/core/services/pos-indexed-db.service.ts
// ==============================================================================

import { Injectable } from '@angular/core';

export interface VentaOfflineRecord {
  nro_recibo_provisional: string;
  uuid_operacion: string;
  sucursal_id: number;
  sucursal_nombre?: string;
  cliente_nombre: string;
  cliente_nit?: string;
  monto: number;
  moneda: string;
  metodo_pago_id: number;
  metodo_pago_nombre?: string;
  efectivo_recibido?: number;
  cambio?: number;
  observaciones?: string;
  fecha_cobro: string; // ISO String
  sincronizado: boolean;
  venta_id_nube?: number;
  fecha_sincronizacion?: string;
  items: Array<{
    variante_id?: number;
    producto_id?: number;
    producto_nombre: string;
    talla?: string;
    color?: string;
    cantidad: number;
    precio_unitario: number;
    subtotal: number;
  }>;
}

@Injectable({
  providedIn: 'root'
})
export class PosIndexedDbService {
  private readonly DB_NAME = 'ShopynPOS_DB';
  private readonly DB_VERSION = 1;

  private dbPromise: Promise<IDBDatabase> | null = null;

  constructor() {}

  /**
   * Abre o crea la base de datos IndexedDB de forma transaccional y singleton
   */
  public getDb(): Promise<IDBDatabase> {
    if (this.dbPromise) {
      return this.dbPromise;
    }

    this.dbPromise = new Promise<IDBDatabase>((resolve, reject) => {
      if (typeof window === 'undefined' || !window.indexedDB) {
        reject(new Error('IndexedDB no es soportado en este entorno de navegador'));
        return;
      }

      const request = window.indexedDB.open(this.DB_NAME, this.DB_VERSION);

      request.onupgradeneeded = (event: IDBVersionChangeEvent) => {
        const db = request.result;

        // 1. Almacén de catálogo / inventario de prendas
        if (!db.objectStoreNames.contains('catalogo_inventario')) {
          const store = db.createObjectStore('catalogo_inventario', { keyPath: 'id' });
          store.createIndex('sucursal_id', 'sucursal_id', { unique: false });
          store.createIndex('producto_nombre', 'producto_nombre', { unique: false });
          store.createIndex('variante_id', 'variante_id', { unique: false });
        }

        // 2. Almacén de ventas y recibos offline
        if (!db.objectStoreNames.contains('ventas_offline')) {
          const store = db.createObjectStore('ventas_offline', { keyPath: 'nro_recibo_provisional' });
          store.createIndex('sucursal_id', 'sucursal_id', { unique: false });
          store.createIndex('sincronizado', 'sincronizado', { unique: false });
          store.createIndex('fecha_cobro', 'fecha_cobro', { unique: false });
          store.createIndex('uuid_operacion', 'uuid_operacion', { unique: true });
        }

        // 3. Almacén de sucursales en caché
        if (!db.objectStoreNames.contains('sucursales')) {
          db.createObjectStore('sucursales', { keyPath: 'id' });
        }

        // 4. Almacén de métodos de pago en caché
        if (!db.objectStoreNames.contains('metodos_pago')) {
          db.createObjectStore('metodos_pago', { keyPath: 'id' });
        }
      };

      request.onsuccess = () => {
        resolve(request.result);
      };

      request.onerror = () => {
        console.error('Error al inicializar IndexedDB:', request.error);
        reject(request.error);
      };
    });

    return this.dbPromise;
  }

  // ============================================================================
  // CATÁLOGO E INVENTARIO EN INDEXEDDB
  // ============================================================================

  /**
   * Guarda o actualiza en IndexedDB todo el catálogo de productos de una sucursal
   */
  async guardarCatalogoSucursal(sucursalId: number, items: any[]): Promise<void> {
    const db = await this.getDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('catalogo_inventario', 'readwrite');
      const store = tx.objectStore('catalogo_inventario');

      // Limpiar ítems previos de esta sucursal primero
      const index = store.index('sucursal_id');
      const range = IDBKeyRange.only(sucursalId);
      const cursorRequest = index.openCursor(range);

      cursorRequest.onsuccess = () => {
        const cursor = cursorRequest.result;
        if (cursor) {
          cursor.delete();
          cursor.continue();
        } else {
          // Inserción en lote de los nuevos productos
          for (const it of items) {
            store.put({
              ...it,
              sucursal_id: sucursalId
            });
          }
        }
      };

      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  /**
   * Recupera todos los productos disponibles en IndexedDB para la sucursal seleccionada
   */
  async obtenerCatalogoSucursal(sucursalId: number): Promise<any[]> {
    const db = await this.getDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('catalogo_inventario', 'readonly');
      const store = tx.objectStore('catalogo_inventario');
      const index = store.index('sucursal_id');
      const request = index.getAll(IDBKeyRange.only(sucursalId));

      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Descuenta stock en la base de datos IndexedDB local cuando se realiza una venta offline
   */
  async descontarStockLocal(
    sucursalId: number,
    itemsVendidos: Array<{ inventarioId?: number; varianteId?: number; cantidad: number }>
  ): Promise<void> {
    const db = await this.getDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('catalogo_inventario', 'readwrite');
      const store = tx.objectStore('catalogo_inventario');

      for (const vend of itemsVendidos) {
        if (vend.inventarioId) {
          const req = store.get(vend.inventarioId);
          req.onsuccess = () => {
            const item = req.result;
            if (item) {
              item.stockfisico = Math.max(0, (item.stockfisico || 0) - vend.cantidad);
              if (item.stockdisponible !== undefined) {
                item.stockdisponible = Math.max(0, item.stockdisponible - vend.cantidad);
              }
              store.put(item);
            }
          };
        }
      }

      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  // ============================================================================
  // GESTIÓN DE VENTAS OFFLINE EN INDEXEDDB
  // ============================================================================

  /**
   * Registra una venta en IndexedDB en modo contingencia (sin internet)
   */
  async guardarVentaOffline(venta: VentaOfflineRecord): Promise<void> {
    const db = await this.getDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('ventas_offline', 'readwrite');
      const store = tx.objectStore('ventas_offline');
      store.put(venta);

      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  /**
   * Obtiene todas las ventas guardadas en IndexedDB (opcionalmente filtrando por sucursal)
   */
  async obtenerVentasOffline(sucursalId?: number): Promise<VentaOfflineRecord[]> {
    const db = await this.getDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('ventas_offline', 'readonly');
      const store = tx.objectStore('ventas_offline');

      if (sucursalId !== undefined) {
        const index = store.index('sucursal_id');
        const req = index.getAll(IDBKeyRange.only(sucursalId));
        req.onsuccess = () => resolve(req.result || []);
        req.onerror = () => reject(req.error);
      } else {
        const req = store.getAll();
        req.onsuccess = () => resolve(req.result || []);
        req.onerror = () => reject(req.error);
      }
    });
  }

  /**
   * Obtiene exclusivamente las ventas offline que están pendientes de sincronizar con la nube
   */
  async obtenerVentasPendientes(): Promise<VentaOfflineRecord[]> {
    const db = await this.getDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('ventas_offline', 'readonly');
      const store = tx.objectStore('ventas_offline');
      const req = store.getAll();

      req.onsuccess = () => {
        const all: VentaOfflineRecord[] = req.result || [];
        // Filtrar pendientes (sincronizado == false)
        const pendientes = all.filter(v => !v.sincronizado);
        resolve(pendientes);
      };
      req.onerror = () => reject(req.error);
    });
  }

  /**
   * Marca un conjunto de recibos como sincronizados con el backend en la nube
   */
  async marcarVentasSincronizadas(
    foliosMap: Array<{ nro_recibo_provisional: string; venta_id_nube?: number }>
  ): Promise<void> {
    const db = await this.getDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('ventas_offline', 'readwrite');
      const store = tx.objectStore('ventas_offline');
      const ahora = new Date().toISOString();

      for (const item of foliosMap) {
        const req = store.get(item.nro_recibo_provisional);
        req.onsuccess = () => {
          const venta = req.result as VentaOfflineRecord;
          if (venta) {
            venta.sincronizado = true;
            venta.fecha_sincronizacion = ahora;
            if (item.venta_id_nube) {
              venta.venta_id_nube = item.venta_id_nube;
            }
            store.put(venta);
          }
        };
      }

      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  /**
   * Retorna el número de ventas que están pendientes de sincronizar a la nube
   */
  async contarVentasPendientes(): Promise<number> {
    const pendientes = await this.obtenerVentasPendientes();
    return pendientes.length;
  }

  // ============================================================================
  // CACHÉ DE SUCURSALES Y MÉTODOS DE PAGO EN INDEXEDDB
  // ============================================================================

  async guardarSucursales(sucursales: any[]): Promise<void> {
    const db = await this.getDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('sucursales', 'readwrite');
      const store = tx.objectStore('sucursales');
      store.clear();
      for (const s of sucursales) {
        store.put(s);
      }
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  async obtenerSucursales(): Promise<any[]> {
    const db = await this.getDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('sucursales', 'readonly');
      const store = tx.objectStore('sucursales');
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  }

  async guardarMetodosPago(metodos: any[]): Promise<void> {
    const db = await this.getDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('metodos_pago', 'readwrite');
      const store = tx.objectStore('metodos_pago');
      store.clear();
      for (const m of metodos) {
        store.put(m);
      }
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  async obtenerMetodosPago(): Promise<any[]> {
    const db = await this.getDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('metodos_pago', 'readonly');
      const store = tx.objectStore('metodos_pago');
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  }
}

