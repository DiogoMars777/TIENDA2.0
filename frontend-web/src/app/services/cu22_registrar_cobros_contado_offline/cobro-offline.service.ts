// ==============================================================================
// CU22 - REGISTRAR COBROS DE CONTADO SIN CONEXIÓN -> SERVICIO HTTP Y CACHE LOCAL
// Ubicación: frontend-web/src/app/services/cu22_registrar_cobros_contado_offline/cobro-offline.service.ts
// ==============================================================================

import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  CobroOfflineDTO,
  RegistroCobroOfflineRequest,
  CobroOfflineKPIsDTO
} from '../../models/cu22_registrar_cobros_contado_offline/cobro-offline.model';

@Injectable({
  providedIn: 'root'
})
export class CobroOfflineService {
  private readonly apiUrl = `${environment.apiUrl}/cobros-offline`;
  private readonly STORAGE_KEY = 'shopyn_contingencia_cobros_offline';

  constructor(private http: HttpClient) {}

  // --- API BACKEND ---

  registrarCobro(payload: RegistroCobroOfflineRequest): Observable<{ exito: boolean; cobro_offline: CobroOfflineDTO }> {
    return this.http.post<{ exito: boolean; cobro_offline: CobroOfflineDTO }>(`${this.apiUrl}/registrar`, payload);
  }

  listarCobros(sucursalId?: number, soloPendientes: boolean = false): Observable<{ exito: boolean; cobros: CobroOfflineDTO[] }> {
    let params = new HttpParams().set('solo_pendientes', soloPendientes.toString());
    if (sucursalId) {
      params = params.set('sucursal_id', sucursalId.toString());
    }
    return this.http.get<{ exito: boolean; cobros: CobroOfflineDTO[] }>(this.apiUrl, { params });
  }

  listarPendientes(sucursalId?: number): Observable<{ exito: boolean; pendientes: CobroOfflineDTO[] }> {
    const url = sucursalId ? `${this.apiUrl}/pendientes?sucursal_id=${sucursalId}` : `${this.apiUrl}/pendientes`;
    return this.http.get<{ exito: boolean; pendientes: CobroOfflineDTO[] }>(url);
  }

  obtenerKpis(sucursalId?: number): Observable<{ exito: boolean; kpis: CobroOfflineKPIsDTO }> {
    const url = sucursalId ? `${this.apiUrl}/kpis?sucursal_id=${sucursalId}` : `${this.apiUrl}/kpis`;
    return this.http.get<{ exito: boolean; kpis: CobroOfflineKPIsDTO }>(url);
  }

  obtenerRecibo(cobroId: number): Observable<{ exito: boolean; recibo: CobroOfflineDTO }> {
    return this.http.get<{ exito: boolean; recibo: CobroOfflineDTO }>(`${this.apiUrl}/${cobroId}`);
  }

  subirLote(cobros: RegistroCobroOfflineRequest[]): Observable<{ exito: boolean; procesados: number; cobros: CobroOfflineDTO[] }> {
    return this.http.post<{ exito: boolean; procesados: number; cobros: CobroOfflineDTO[] }>(`${this.apiUrl}/lote`, { cobros });
  }

  // --- ALMACENAMIENTO DE CONTINGENCIA LOCAL POR TENANT (LOCALSTORAGE) ---

  private getStorageKey(): string {
    const tenantId = localStorage.getItem('tenant_id') || '1';
    return `${this.STORAGE_KEY}_tenant_${tenantId}`;
  }

  guardarEnLocalStorage(registro: RegistroCobroOfflineRequest, sucursalNombre?: string): CobroOfflineDTO {
    const cobrosLocales = this.obtenerDeLocalStorage();
    const mockId = Date.now();
    const tenantId = Number(localStorage.getItem('tenant_id') || '1');
    const itemGuardado: CobroOfflineDTO = {
      id: mockId,
      tenant_id: tenantId,
      sucursal_id: registro.sucursal_id,
      sucursal_nombre: sucursalNombre || 'Sucursal Central',
      monto: registro.monto,
      moneda: registro.moneda || 'BOB',
      nro_recibo_provisional: registro.nro_recibo_provisional,
      uuid_operacion: registro.uuid_operacion || `offline-uuid-${mockId}`,
      cliente_nombre: registro.cliente_nombre || 'Cliente Mostrador',
      cliente_nit: registro.cliente_nit || '0',
      fecha_cobro: registro.fecha_cobro || new Date().toISOString(),
      sincronizado: false,
      items: registro.items,
      efectivo_recibido: registro.efectivo_recibido,
      cambio: registro.cambio,
      observaciones: registro.observaciones,
      almacenado_local: true
    };

    cobrosLocales.unshift(itemGuardado);
    localStorage.setItem(this.getStorageKey(), JSON.stringify(cobrosLocales));
    return itemGuardado;
  }

  obtenerDeLocalStorage(): CobroOfflineDTO[] {
    try {
      const data = localStorage.getItem(this.getStorageKey());
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  }

  limpiarLocalStorage(): void {
    localStorage.removeItem(this.getStorageKey());
  }
}
