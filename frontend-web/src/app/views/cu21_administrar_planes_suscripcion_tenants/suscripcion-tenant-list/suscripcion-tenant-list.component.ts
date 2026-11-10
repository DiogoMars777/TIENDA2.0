// ==============================================================================
// CU21 - ADMINISTRAR PLANES DE SUSCRIPCIÓN Y TENANTS -> COMPONENTE VISTA
// Ubicación: frontend-web/src/app/views/cu21_administrar_planes_suscripcion_tenants/suscripcion-tenant-list/suscripcion-tenant-list.component.ts
// ==============================================================================

import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';

import { SuscripcionTenantController } from '../../../controllers/cu21_administrar_planes_suscripcion_tenants/suscripcion-tenant.controller';
import {
  NuevoTenantRequest,
  PlanSuscripcionCreateDTO,
  PlanSuscripcionDTO,
  TenantDTO,
  AsignarAdminTenantRequest
} from '../../../models/cu21_administrar_planes_suscripcion_tenants/suscripcion-tenant.model';

@Component({
  selector: 'app-suscripcion-tenant-list',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule],
  templateUrl: './suscripcion-tenant-list.component.html',
  styleUrls: ['./suscripcion-tenant-list.component.css']
})
export class SuscripcionTenantListComponent implements OnInit {

  // Formulario Nuevo Tenant + Administrador del Tenant
  nuevoTenantForm: NuevoTenantRequest = {
    nombre: '',
    slug: '',
    nit_ruc: '',
    email_contacto: '',
    telefono_contacto: '',
    direccion_fiscal: '',
    plan_id: 1,
    meses_suscripcion: 12,
    admin_nombre: '',
    admin_apellido: '',
    admin_email: '',
    admin_password: 'Admin123.'
  };

  // Formulario Asignar / Cambiar Administrador de Tenant existente
  adminTenantForm: AsignarAdminTenantRequest = {
    nombre: '',
    apellido: '',
    email: '',
    password: 'Admin123.'
  };

  // Formulario Cambio de Plan
  cambioPlanNuevoId: number = 1;
  cambioPlanMotivo: string = '';

  // Formulario Renovación
  renovacionMeses: number = 12;
  renovacionMetodo: string = 'TRANSFERENCIA_BANCARIA';

  // Formulario Plan
  planForm: PlanSuscripcionCreateDTO = {
    nombre: '',
    descripcion: '',
    precio_mensual: 120.00,
    limite_sucursales: 2,
    limite_usuarios: 5,
    limite_productos: 200,
    habilitar_reportes_ia: false,
    habilitar_vestidor_ia: false,
    activo: true
  };

  constructor(public ctrl: SuscripcionTenantController) {}

  ngOnInit(): void {
    this.ctrl.cargarDatos();
  }

  actualizarFiltro(event: Event): void {
    const valor = (event.target as HTMLInputElement).value;
    this.ctrl.filtroTexto.set(valor);
  }

  autoGenerarSlug(): void {
    if (!this.nuevoTenantForm.nombre) return;
    this.nuevoTenantForm.slug = this.nuevoTenantForm.nombre
      .toLowerCase()
      .trim()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]/g, '-')
      .replace(/-+/g, '-');
    if (!this.nuevoTenantForm.admin_email && this.nuevoTenantForm.slug) {
      this.nuevoTenantForm.admin_email = `admin@${this.nuevoTenantForm.slug.replace(/-/g, '')}.com`;
      this.nuevoTenantForm.email_contacto = this.nuevoTenantForm.admin_email;
    }
    if (!this.nuevoTenantForm.admin_nombre) {
      this.nuevoTenantForm.admin_nombre = `Admin ${this.nuevoTenantForm.nombre}`;
    }
  }

  guardarNuevoTenant(): void {
    if (this.nuevoTenantForm.admin_email && !this.nuevoTenantForm.email_contacto) {
      this.nuevoTenantForm.email_contacto = this.nuevoTenantForm.admin_email;
    }
    this.ctrl.crearTenant(this.nuevoTenantForm, () => {
      this.nuevoTenantForm = {
        nombre: '',
        slug: '',
        nit_ruc: '',
        email_contacto: '',
        telefono_contacto: '',
        direccion_fiscal: '',
        plan_id: this.ctrl.planes()[0]?.id || 1,
        meses_suscripcion: 12,
        admin_nombre: '',
        admin_apellido: '',
        admin_email: '',
        admin_password: 'Admin123.'
      };
    });
  }

  abrirModalAdmin(t: TenantDTO): void {
    this.adminTenantForm = {
      nombre: t.administrador?.nombre || `Admin ${t.nombre}`,
      apellido: t.administrador?.apellido || 'Gerencia',
      email: t.administrador?.email || t.email_contacto || `admin@${t.slug}.com`,
      password: 'Admin123.'
    };
    this.ctrl.abrirModalAsignarAdmin(t);
  }

  confirmarAsignarAdmin(): void {
    this.ctrl.ejecutarAsignarAdmin(this.adminTenantForm);
  }

  abrirModalNuevoPlan(): void {
    this.planForm = {
      nombre: '',
      descripcion: '',
      precio_mensual: 120.00,
      limite_sucursales: 2,
      limite_usuarios: 5,
      limite_productos: 200,
      habilitar_reportes_ia: false,
      habilitar_vestidor_ia: false,
      activo: true
    };
    this.ctrl.abrirModalNuevoPlan();
  }

  abrirModalEditarPlan(p: PlanSuscripcionDTO): void {
    this.planForm = {
      nombre: p.nombre,
      descripcion: p.descripcion || '',
      precio_mensual: Number(p.precio_mensual),
      limite_sucursales: p.limite_sucursales,
      limite_usuarios: p.limite_usuarios,
      limite_productos: p.limite_productos,
      habilitar_reportes_ia: p.habilitar_reportes_ia ?? p.habilitar_vestidor_ia,
      habilitar_vestidor_ia: p.habilitar_vestidor_ia,
      activo: p.activo
    };
    this.ctrl.abrirModalEditarPlan(p);
  }

  confirmarCambioPlan(): void {
    this.ctrl.ejecutarCambioPlan(this.cambioPlanNuevoId, this.cambioPlanMotivo);
  }

  confirmarRenovacion(): void {
    this.ctrl.ejecutarRenovacion(this.renovacionMeses, this.renovacionMetodo);
  }

  confirmarGuardarPlan(): void {
    this.planForm.habilitar_vestidor_ia = !!this.planForm.habilitar_reportes_ia;
    const planSel = this.ctrl.planSeleccionado();
    this.ctrl.guardarPlan(this.planForm, planSel?.id);
  }
}
