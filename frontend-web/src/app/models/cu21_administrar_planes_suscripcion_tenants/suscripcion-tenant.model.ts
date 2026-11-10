// ==============================================================================
// CU21 - ADMINISTRAR PLANES DE SUSCRIPCIÓN Y TENANTS -> MODELOS TYPESCRIPT
// Ubicación: frontend-web/src/app/models/cu21_administrar_planes_suscripcion_tenants/suscripcion-tenant.model.ts
// ==============================================================================

export interface PlanSuscripcionDTO {
  id: number;
  nombre: string;
  descripcion?: string;
  precio_mensual: number;
  limite_sucursales: number;
  limite_usuarios: number;
  limite_productos: number;
  habilitar_reportes_ia?: boolean;
  habilitar_vestidor_ia: boolean;
  activo: boolean;
  fechacreacion?: string;
}

export interface PlanSuscripcionCreateDTO {
  nombre: string;
  descripcion?: string;
  precio_mensual: number;
  limite_sucursales: number;
  limite_usuarios: number;
  limite_productos: number;
  habilitar_reportes_ia?: boolean;
  habilitar_vestidor_ia: boolean;
  activo: boolean;
}

export interface MetricasUsoTenantDTO {
  sucursales_usadas: number;
  sucursales_limite: number;
  usuarios_usados: number;
  usuarios_limite: number;
  productos_usados: number;
  productos_limite: number;
  porcentaje_sucursales: number;
  porcentaje_usuarios: number;
}

export interface TenantSuscripcionDTO {
  id: number;
  plan_id: number;
  plan_nombre?: string;
  fecha_inicio: string;
  fecha_fin: string;
  estado: string; // 'ACTIVA' | 'SUSPENDIDA' | 'VENCIDA'
  monto_pagado: number;
  metodo_pago?: string;
}

export interface TenantDTO {
  id: number;
  uuid: string;
  nombre: string;
  slug: string;
  dominio_personalizado?: string;
  nit_ruc?: string;
  email_contacto: string;
  telefono_contacto?: string;
  direccion_fiscal?: string;
  logo_url?: string;
  plan_id?: number;
  plan?: PlanSuscripcionDTO;
  activo: boolean;
  fechacreacion?: string;
  suscripcion_actual?: TenantSuscripcionDTO;
  metricas_uso?: MetricasUsoTenantDTO;
  administrador?: {
    id: number;
    nombre: string;
    apellido?: string;
    email: string;
    activo?: boolean;
  };
}

export interface NuevoTenantRequest {
  nombre: string;
  slug: string;
  nit_ruc?: string;
  email_contacto: string;
  telefono_contacto?: string;
  direccion_fiscal?: string;
  plan_id: number;
  meses_suscripcion: number;
  admin_nombre?: string;
  admin_apellido?: string;
  admin_email?: string;
  admin_password?: string;
}

export interface AsignarAdminTenantRequest {
  nombre: string;
  apellido?: string;
  email: string;
  password: string;
}

export interface CambiarPlanRequest {
  nuevo_plan_id: number;
  motivo?: string;
}

export interface RenovarSuscripcionRequest {
  meses: number;
  metodo_pago: string;
}

export interface KpiSaaSDTO {
  total_tenants: number;
  tenants_activos: number;
  tenants_suspendidos: number;
  mrr_estimado: number;
  total_planes: number;
  distribucion_planes: Record<string, number>;
}
