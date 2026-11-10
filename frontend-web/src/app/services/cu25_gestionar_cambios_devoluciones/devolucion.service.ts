// ==============================================================================
// CU25 - GESTIONAR CAMBIOS Y DEVOLUCIONES DE PRENDAS -> SERVICIO HTTP (FRONTEND)
// Ubicación: frontend-web/src/app/services/cu25_gestionar_cambios_devoluciones/devolucion.service.ts
// ==============================================================================

import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  DevolucionResponse,
  SolicitudDevolucionRequest,
  ValidarVentaDevolucionResponse,
  DevolucionKpisDTO
} from '../../models/cu25_gestionar_cambios_devoluciones/devolucion.model';

@Injectable({
  providedIn: 'root'
})
export class DevolucionService {
  private readonly apiUrl = `${environment.apiUrl}/devoluciones`;

  constructor(private http: HttpClient) {}

  /**
   * Recupera el histórico de cambios de talla/modelo y devoluciones.
   */
  listarDevoluciones(sucursalId?: number, tipo?: string): Observable<DevolucionResponse[]> {
    let params = new HttpParams();
    if (sucursalId) params = params.set('sucursal_id', sucursalId.toString());
    if (tipo && tipo !== 'TODOS') params = params.set('tipo', tipo);

    return this.http.get<DevolucionResponse[]>(`${this.apiUrl}/`, { params });
  }

  /**
   * Registra y ejecuta la devolución o cambio de prendas.
   */
  solicitarDevolucion(payload: SolicitudDevolucionRequest): Observable<DevolucionResponse> {
    return this.http.post<DevolucionResponse>(`${this.apiUrl}/solicitar`, payload);
  }

  /**
   * Valida si una venta califica para cambio dentro del plazo de garantía (15 días).
   * Acepta tanto el Código de Venta (ej: VTA-SYNC-REC-OFF-...) como el ID numérico.
   */
  validarVenta(ventaIdOrCodigo: string | number, plazoDias: number = 15): Observable<ValidarVentaDevolucionResponse> {
    const params = new HttpParams().set('plazo_dias', plazoDias.toString());
    const cleanRef = encodeURIComponent(String(ventaIdOrCodigo).trim());
    return this.http.get<ValidarVentaDevolucionResponse>(`${this.apiUrl}/validar-venta/${cleanRef}`, { params });
  }

  /**
   * Obtiene indicadores ejecutivos del módulo CU25.
   */
  obtenerKpis(plazoDias: number = 15): Observable<DevolucionKpisDTO> {
    const params = new HttpParams().set('plazo_dias', plazoDias.toString());
    return this.http.get<DevolucionKpisDTO>(`${this.apiUrl}/kpis`, { params });
  }
}
