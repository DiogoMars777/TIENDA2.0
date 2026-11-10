// ==============================================================================
// CU21 - ADMINISTRAR PLANES DE SUSCRIPCIÓN Y TENANTS -> SERVICIO HTTP (ANGULAR)
// Ubicación: frontend-web/src/app/services/cu21_administrar_planes_suscripcion_tenants/suscripcion-tenant.service.ts
// ==============================================================================

import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  PlanSuscripcionDTO,
  PlanSuscripcionCreateDTO,
  TenantDTO,
  NuevoTenantRequest,
  CambiarPlanRequest,
  RenovarSuscripcionRequest,
  AsignarAdminTenantRequest,
  KpiSaaSDTO
} from '../../models/cu21_administrar_planes_suscripcion_tenants/suscripcion-tenant.model';

@Injectable({
  providedIn: 'root'
})
export class SuscripcionTenantService {
  private readonly apiUrl = `${environment.apiUrl}/suscripciones-tenants`;

  constructor(private http: HttpClient) {}

  // --- PLANES ---
  listarPlanes(soloActivos: boolean = false): Observable<{ exito: boolean; planes: PlanSuscripcionDTO[] }> {
    const params = new HttpParams().set('solo_activos', soloActivos.toString());
    return this.http.get<{ exito: boolean; planes: PlanSuscripcionDTO[] }>(`${this.apiUrl}/planes`, { params });
  }

  crearPlan(payload: PlanSuscripcionCreateDTO): Observable<{ exito: boolean; plan: PlanSuscripcionDTO }> {
    return this.http.post<{ exito: boolean; plan: PlanSuscripcionDTO }>(`${this.apiUrl}/planes`, payload);
  }

  actualizarPlan(planId: number, payload: Partial<PlanSuscripcionCreateDTO>): Observable<{ exito: boolean; plan: PlanSuscripcionDTO }> {
    return this.http.put<{ exito: boolean; plan: PlanSuscripcionDTO }>(`${this.apiUrl}/planes/${planId}`, payload);
  }

  // --- TENANTS ---
  listarTenants(): Observable<{ exito: boolean; tenants: TenantDTO[] }> {
    return this.http.get<{ exito: boolean; tenants: TenantDTO[] }>(`${this.apiUrl}/tenants`);
  }

  obtenerTenant(tenantId: number): Observable<{ exito: boolean; data: any }> {
    return this.http.get<{ exito: boolean; data: any }>(`${this.apiUrl}/tenants/${tenantId}`);
  }

  registrarTenant(payload: NuevoTenantRequest): Observable<{ exito: boolean; tenant: TenantDTO }> {
    return this.http.post<{ exito: boolean; tenant: TenantDTO }>(`${this.apiUrl}/tenants`, payload);
  }

  cambiarPlanTenant(tenantId: number, payload: CambiarPlanRequest): Observable<{ exito: boolean; tenant: TenantDTO }> {
    return this.http.put<{ exito: boolean; tenant: TenantDTO }>(`${this.apiUrl}/tenants/${tenantId}/plan`, payload);
  }

  toggleEstadoTenant(tenantId: number, activo: boolean, motivo?: string): Observable<{ exito: boolean; tenant: TenantDTO }> {
    return this.http.put<{ exito: boolean; tenant: TenantDTO }>(`${this.apiUrl}/tenants/${tenantId}/estado`, { activo, motivo });
  }

  renovarSuscripcion(tenantId: number, payload: RenovarSuscripcionRequest): Observable<{ exito: boolean; suscripcion: any }> {
    return this.http.post<{ exito: boolean; suscripcion: any }>(`${this.apiUrl}/tenants/${tenantId}/renovar`, payload);
  }

  asignarAdministradorTenant(tenantId: number, payload: AsignarAdminTenantRequest): Observable<{ exito: boolean; administrador: any }> {
    return this.http.post<{ exito: boolean; administrador: any }>(`${this.apiUrl}/tenants/${tenantId}/administrador`, payload);
  }

  obtenerMiPlan(): Observable<{ exito: boolean; tenant: any }> {
    return this.http.get<{ exito: boolean; tenant: any }>(`${this.apiUrl}/mi-plan`);
  }

  // --- KPIS ---
  obtenerKpis(): Observable<{ exito: boolean; kpis: KpiSaaSDTO }> {
    return this.http.get<{ exito: boolean; kpis: KpiSaaSDTO }>(`${this.apiUrl}/kpis`);
  }
}
