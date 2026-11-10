// ==============================================================================
// CU23 - SINCRONIZAR OPERACIONES OFFLINE -> SERVICIO HTTP & LOCAL CACHE (FRONTEND)
// Ubicación: frontend-web/src/app/services/cu23_sincronizar_operaciones_offline/sincronizacion-offline.service.ts
// ==============================================================================

import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  SyncOperacionItem,
  SyncLoteResponse,
  SyncLogDTO,
  SyncKpisDTO,
  SincronizarPendientesRequest,
  ResolverConflictoRequest
} from '../../models/cu23_sincronizar_operaciones_offline/sincronizacion-offline.model';

@Injectable({
  providedIn: 'root'
})
export class SincronizacionOfflineService {
  private readonly apiUrl = `${environment.apiUrl}/sincronizacion-offline`;
  private readonly LOCAL_STORAGE_KEY = 'cobros_offline_queue';

  constructor(private http: HttpClient) {}

  /**
   * Sincroniza todos los cobros en contingencia (CU22) acumulados en el servidor.
   */
  sincronizarPendientes(
    estrategia: string = 'PRIORIZAR_TIENDA_FISICA',
    sucursalId?: number
  ): Observable<SyncLoteResponse> {
    const body: SincronizarPendientesRequest = {
      estrategia_preferida: estrategia,
      sucursal_id: sucursalId
    };
    return this.http.post<SyncLoteResponse>(`${this.apiUrl}/sincronizar-pendientes`, body);
  }

  /**
   * Envía un lote de operaciones directas guardadas en la caché offline del navegador.
   */
  enviarLote(
    sucursalId: number,
    operaciones: SyncOperacionItem[],
    estrategia: string = 'PRIORIZAR_TIENDA_FISICA'
  ): Observable<SyncLoteResponse> {
    return this.http.post<SyncLoteResponse>(`${this.apiUrl}/lote`, {
      sucursal_id: sucursalId,
      estrategia_preferida: estrategia,
      operaciones: operaciones
    });
  }

  /**
   * Obtiene métricas ejecutivas en tiempo real del motor de sincronización.
   */
  obtenerKpis(): Observable<SyncKpisDTO> {
    return this.http.get<SyncKpisDTO>(`${this.apiUrl}/kpis`);
  }

  /**
   * Recupera el registro histórico de operaciones sincronizadas y resolución de conflictos.
   */
  obtenerHistorial(limite: number = 50, estado?: string): Observable<SyncLogDTO[]> {
    let params = new HttpParams().set('limite', limite.toString());
    if (estado && estado !== 'TODOS') {
      params = params.set('estado', estado);
    }
    return this.http.get<SyncLogDTO[]>(`${this.apiUrl}/historial`, { params });
  }

  /**
   * Permite resolver manualmente una discrepancia o conflicto retenido en cola.
   */
  resolverConflicto(
    syncId: number,
    estrategia: string,
    notas?: string
  ): Observable<{ exito: boolean; mensaje: string; sync_id: number; estado: string }> {
    const body: ResolverConflictoRequest = {
      estrategia: estrategia,
      notas: notas
    };
    return this.http.post<{ exito: boolean; mensaje: string; sync_id: number; estado: string }>(
      `${this.apiUrl}/${syncId}/resolver-conflicto`,
      body
    );
  }

  // ============================================================================
  // GESTIÓN DE COLA LOCAL (OFFLINE LOCALSTORAGE CACHE POR TENANT)
  // ============================================================================

  private getStorageKey(): string {
    const tenantId = localStorage.getItem('tenant_id') || '1';
    return `shopyn_contingencia_cobros_offline_tenant_${tenantId}`;
  }

  obtenerColaLocal(): any[] {
    try {
      const data = localStorage.getItem(this.getStorageKey());
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  }

  limpiarColaLocal(): void {
    localStorage.removeItem(this.getStorageKey());
  }
}
