// ==============================================================================
// CU21 - ADMINISTRAR PLANES DE SUSCRIPCIÓN Y TENANTS -> CONTROLADOR (MVC)
// Ubicación: frontend-web/src/app/controllers/cu21_administrar_planes_suscripcion_tenants/suscripcion-tenant.controller.ts
// ==============================================================================

import { Injectable, signal, computed } from '@angular/core';
import { SuscripcionTenantService } from '../../services/cu21_administrar_planes_suscripcion_tenants/suscripcion-tenant.service';
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
export class SuscripcionTenantController {
  // Estado Reactivo con Angular Signals
  planes = signal<PlanSuscripcionDTO[]>([]);
  tenants = signal<TenantDTO[]>([]);
  kpis = signal<KpiSaaSDTO | null>(null);

  cargando = signal<boolean>(false);
  guardando = signal<boolean>(false);
  error = signal<string | null>(null);
  mensajeExito = signal<string | null>(null);

  // Navegación y Filtros
  tabActiva = signal<'tenants' | 'planes'>('tenants');
  filtroTexto = signal<string>('');

  // Modales
  modalTenantAbierto = signal<boolean>(false);
  modalPlanAbierto = signal<boolean>(false);
  modalCambiarPlanAbierto = signal<boolean>(false);
  modalRenovarAbierto = signal<boolean>(false);
  modalAsignarAdminAbierto = signal<boolean>(false);

  // Seleccionados para modal
  tenantSeleccionado = signal<TenantDTO | null>(null);
  planSeleccionado = signal<PlanSuscripcionDTO | null>(null);

  // Computado: lista filtrada de tenants
  tenantsFiltrados = computed(() => {
    const texto = this.filtroTexto().toLowerCase().trim();
    const list = this.tenants();
    if (!texto) return list;
    return list.filter(t =>
      t.nombre.toLowerCase().includes(texto) ||
      t.slug.toLowerCase().includes(texto) ||
      (t.nit_ruc && t.nit_ruc.includes(texto)) ||
      t.email_contacto.toLowerCase().includes(texto) ||
      (t.plan && t.plan.nombre.toLowerCase().includes(texto))
    );
  });

  constructor(private service: SuscripcionTenantService) {}

  // Carga inicial y refresco total
  cargarDatos(): void {
    this.cargando.set(true);
    this.error.set(null);

    // Cargar Planes
    this.service.listarPlanes().subscribe({
      next: (res) => {
        if (res.exito) this.planes.set(res.planes);
      },
      error: (err) => console.error('Error al cargar planes:', err)
    });

    // Cargar KPIs
    this.service.obtenerKpis().subscribe({
      next: (res) => {
        if (res.exito) this.kpis.set(res.kpis);
      },
      error: (err) => console.error('Error al cargar KPIs SaaS:', err)
    });

    // Cargar Tenants
    this.service.listarTenants().subscribe({
      next: (res) => {
        this.cargando.set(false);
        if (res.exito) this.tenants.set(res.tenants);
      },
      error: (err) => {
        this.cargando.set(false);
        this.error.set(err?.error?.detail || 'Error al cargar directorio de empresas tenants.');
      }
    });
  }

  // --- ACCIONES DE TENANT ---

  abrirModalNuevoTenant(): void {
    this.modalTenantAbierto.set(true);
    this.error.set(null);
  }

  cerrarModalNuevoTenant(): void {
    this.modalTenantAbierto.set(false);
  }

  crearTenant(payload: NuevoTenantRequest, onSuccess?: () => void): void {
    this.guardando.set(true);
    this.error.set(null);

    this.service.registrarTenant(payload).subscribe({
      next: (res) => {
        this.guardando.set(false);
        this.mostrarExito(`Empresa '${res.tenant.nombre}' dada de alta exitosamente.`);
        this.cerrarModalNuevoTenant();
        this.cargarDatos();
        if (onSuccess) onSuccess();
      },
      error: (err) => {
        this.guardando.set(false);
        this.error.set(err?.error?.detail || 'No se pudo registrar la nueva empresa.');
      }
    });
  }

  abrirModalCambiarPlan(tenant: TenantDTO): void {
    this.tenantSeleccionado.set(tenant);
    this.modalCambiarPlanAbierto.set(true);
    this.error.set(null);
  }

  cerrarModalCambiarPlan(): void {
    this.modalCambiarPlanAbierto.set(false);
    this.tenantSeleccionado.set(null);
  }

  ejecutarCambioPlan(nuevoPlanId: number, motivo?: string): void {
    const t = this.tenantSeleccionado();
    if (!t) return;

    this.guardando.set(true);
    this.service.cambiarPlanTenant(t.id, { nuevo_plan_id: nuevoPlanId, motivo }).subscribe({
      next: () => {
        this.guardando.set(false);
        this.mostrarExito(`Plan de la empresa '${t.nombre}' actualizado correctamente.`);
        this.cerrarModalCambiarPlan();
        this.cargarDatos();
      },
      error: (err) => {
        this.guardando.set(false);
        this.error.set(err?.error?.detail || 'Error al cambiar plan comercial.');
      }
    });
  }

  abrirModalRenovar(tenant: TenantDTO): void {
    this.tenantSeleccionado.set(tenant);
    this.modalRenovarAbierto.set(true);
    this.error.set(null);
  }

  cerrarModalRenovar(): void {
    this.modalRenovarAbierto.set(false);
    this.tenantSeleccionado.set(null);
  }

  ejecutarRenovacion(meses: number, metodoPago: string): void {
    const t = this.tenantSeleccionado();
    if (!t) return;

    this.guardando.set(true);
    this.service.renovarSuscripcion(t.id, { meses, metodo_pago: metodoPago }).subscribe({
      next: () => {
        this.guardando.set(false);
        this.mostrarExito(`Suscripción de '${t.nombre}' renovada por ${meses} meses.`);
        this.cerrarModalRenovar();
        this.cargarDatos();
      },
      error: (err) => {
        this.guardando.set(false);
        this.error.set(err?.error?.detail || 'Error al renovar suscripción.');
      }
    });
  }

  abrirModalAsignarAdmin(tenant: TenantDTO): void {
    this.tenantSeleccionado.set(tenant);
    this.modalAsignarAdminAbierto.set(true);
    this.error.set(null);
  }

  cerrarModalAsignarAdmin(): void {
    this.modalAsignarAdminAbierto.set(false);
    this.tenantSeleccionado.set(null);
  }

  ejecutarAsignarAdmin(payload: AsignarAdminTenantRequest): void {
    const t = this.tenantSeleccionado();
    if (!t) return;

    this.guardando.set(true);
    this.service.asignarAdministradorTenant(t.id, payload).subscribe({
      next: (res) => {
        this.guardando.set(false);
        this.mostrarExito(`Administrador '${res.administrador.email}' asignado exitosamente a '${t.nombre}'.`);
        this.cerrarModalAsignarAdmin();
        this.cargarDatos();
      },
      error: (err) => {
        this.guardando.set(false);
        this.error.set(err?.error?.detail || 'Error al asignar administrador al tenant.');
      }
    });
  }

  toggleEstadoTenant(tenant: TenantDTO): void {
    const nuevoEstado = !tenant.activo;
    const accion = nuevoEstado ? 'reactivar' : 'suspender';
    if (!confirm(`¿Estás seguro de que deseas ${accion} el acceso para '${tenant.nombre}'?`)) {
      return;
    }

    this.service.toggleEstadoTenant(tenant.id, nuevoEstado, `Acción ejecutada desde consola admin`).subscribe({
      next: () => {
        this.mostrarExito(`Empresa '${tenant.nombre}' ha sido ${nuevoEstado ? 'reactivada' : 'suspendida'}.`);
        this.cargarDatos();
      },
      error: (err) => {
        this.error.set(err?.error?.detail || `Error al modificar estado de la empresa.`);
      }
    });
  }

  // --- ACCIONES DE PLANES ---

  abrirModalNuevoPlan(): void {
    this.planSeleccionado.set(null);
    this.modalPlanAbierto.set(true);
    this.error.set(null);
  }

  abrirModalEditarPlan(plan: PlanSuscripcionDTO): void {
    this.planSeleccionado.set(plan);
    this.modalPlanAbierto.set(true);
    this.error.set(null);
  }

  cerrarModalPlan(): void {
    this.modalPlanAbierto.set(false);
    this.planSeleccionado.set(null);
  }

  guardarPlan(formData: PlanSuscripcionCreateDTO, planId?: number): void {
    this.guardando.set(true);
    this.error.set(null);

    if (planId) {
      this.service.actualizarPlan(planId, formData).subscribe({
        next: (res) => {
          this.guardando.set(false);
          this.mostrarExito(`Plan comercial '${res.plan.nombre}' actualizado.`);
          this.cerrarModalPlan();
          this.cargarDatos();
        },
        error: (err) => {
          this.guardando.set(false);
          this.error.set(err?.error?.detail || 'Error al actualizar plan.');
        }
      });
    } else {
      this.service.crearPlan(formData).subscribe({
        next: (res) => {
          this.guardando.set(false);
          this.mostrarExito(`Nuevo plan '${res.plan.nombre}' creado exitosamente.`);
          this.cerrarModalPlan();
          this.cargarDatos();
        },
        error: (err) => {
          this.guardando.set(false);
          this.error.set(err?.error?.detail || 'Error al registrar plan.');
        }
      });
    }
  }

  private mostrarExito(msg: string): void {
    this.mensajeExito.set(msg);
    setTimeout(() => {
      this.mensajeExito.set(null);
    }, 4500);
  }
}
