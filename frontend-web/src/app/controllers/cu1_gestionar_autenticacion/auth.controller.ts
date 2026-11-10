// ==============================================================================
// CAPA CONTROLADOR (MVC - CONTROLLER)
// Módulo: CU1 - Gestionar Autenticación (Multi-Tenant SaaS)
// Ubicación: frontend-web/src/app/controllers/cu1_gestionar_autenticacion/auth.controller.ts
// ==============================================================================

import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, tap, finalize } from 'rxjs';
import { AuthService } from '../../services/cu1_gestionar_autenticacion/auth.service';
import {
  RespuestaAutenticacionDTO,
  UsuarioDTO,
  TenantSesionDTO,
  RegistroUsuarioDTO
} from '../../models/cu1_gestionar_autenticacion/auth.model';

@Injectable({
  providedIn: 'root'
})
export class AuthController {
  // Estado reactivo del controlador
  private cargandoSubject = new BehaviorSubject<boolean>(false);
  public cargando$: Observable<boolean> = this.cargandoSubject.asObservable();
  public loading$: Observable<boolean> = this.cargando$;

  private errorSubject = new BehaviorSubject<string | null>(null);
  public error$: Observable<string | null> = this.errorSubject.asObservable();

  private usuarioActualSubject = new BehaviorSubject<UsuarioDTO | null>(null);
  public usuarioActual$: Observable<UsuarioDTO | null> = this.usuarioActualSubject.asObservable();
  public currentUser$: Observable<UsuarioDTO | null> = this.usuarioActual$;

  private tenantActualSubject = new BehaviorSubject<TenantSesionDTO | null>(null);
  public tenantActual$: Observable<TenantSesionDTO | null> = this.tenantActualSubject.asObservable();

  constructor(private authService: AuthService) {
    this.cargarSesionAlmacenada();
  }

  /**
   * Carga la sesión y el tenant desde localStorage al inicializar
   */
  private cargarSesionAlmacenada(): void {
    if (typeof window === 'undefined') return;

    const userStr = localStorage.getItem('usuario') || localStorage.getItem('user');
    if (userStr) {
      try {
        const user = JSON.parse(userStr);
        this.usuarioActualSubject.next(user);
      } catch (e) {
        console.error('Error al deserializar el usuario actual', e);
      }
    }

    const tenantIdStr = localStorage.getItem('tenant_id');
    const tenantSlug = localStorage.getItem('tenant_slug') || 'goldenstore';
    const tenantNombre = localStorage.getItem('tenant_nombre') || 'Shopyn Golden Store';

    if (tenantIdStr) {
      this.tenantActualSubject.next({
        id: parseInt(tenantIdStr, 10),
        slug: tenantSlug,
        nombre: tenantNombre
      });
    }
  }

  /**
   * Inicia sesión, almacena el token JWT, claims de tenant y perfil de usuario
   */
  iniciarSesion(email: string, pass: string, tenantSlug?: string): Observable<RespuestaAutenticacionDTO> {
    this.cargandoSubject.next(true);
    this.errorSubject.next(null);

    return this.authService.iniciarSesion(email, pass, tenantSlug).pipe(
      tap((res) => {
        const token = res.access_token;
        const user = res.usuario || res.user;
        const rol = res.rol || (user && user.rol ? user.rol : 'CLIENTE');
        const tenantId = res.tenant_id ? String(res.tenant_id) : '1';
        const tenantSlugVal = res.tenant_slug || 'goldenstore';
        const tenantNombreVal = res.tenant_nombre || 'Shopyn Golden Store';

        // Persistencia para compatibilidad
        localStorage.setItem('access_token', token);
        localStorage.setItem('token', token);
        localStorage.setItem('rol', rol);
        localStorage.setItem('user_role', rol);

        localStorage.setItem('tenant_id', tenantId);
        localStorage.setItem('tenant_slug', tenantSlugVal);
        localStorage.setItem('tenant_nombre', tenantNombreVal);
        if ((res as any).plan) {
          localStorage.setItem('tenant_plan', JSON.stringify((res as any).plan));
        } else {
          localStorage.removeItem('tenant_plan');
        }

        if (user) {
          const userObj = {
            ...user,
            rol: rol,
            tenant_id: parseInt(tenantId, 10),
            tenant_slug: tenantSlugVal,
            tenant_nombre: tenantNombreVal
          };
          localStorage.setItem('usuario', JSON.stringify(userObj));
          localStorage.setItem('user', JSON.stringify(userObj));
          this.usuarioActualSubject.next(userObj);
        }

        this.tenantActualSubject.next({
          id: parseInt(tenantId, 10),
          slug: tenantSlugVal,
          nombre: tenantNombreVal
        });
      }),
      finalize(() => this.cargandoSubject.next(false))
    );
  }

  /**
   * Cierra sesión y remueve tokens y contexto de tenant
   */
  cerrarSesion(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('token');
      localStorage.removeItem('usuario');
      localStorage.removeItem('user');
      localStorage.removeItem('rol');
      localStorage.removeItem('user_role');
      localStorage.removeItem('tenant_id');
      localStorage.removeItem('tenant_slug');
      localStorage.removeItem('tenant_nombre');
      localStorage.removeItem('tenant_plan');
    }
    this.usuarioActualSubject.next(null);
    this.tenantActualSubject.next(null);
  }

  /**
   * Registra un nuevo usuario/cliente
   */
  registrarUsuario(datos: RegistroUsuarioDTO): Observable<any> {
    this.cargandoSubject.next(true);
    this.errorSubject.next(null);
    return this.authService.registrarUsuario(datos).pipe(
      finalize(() => this.cargandoSubject.next(false))
    );
  }

  /**
   * Valida el código OTP
   */
  verificarCodigoOtp(email: string, codigo: string): Observable<any> {
    this.cargandoSubject.next(true);
    this.errorSubject.next(null);
    return this.authService.verificarCodigoOtp(email, codigo).pipe(
      tap((res) => {
        if (res.access_token) {
          localStorage.setItem('access_token', res.access_token);
          localStorage.setItem('token', res.access_token);
        }
      }),
      finalize(() => this.cargandoSubject.next(false))
    );
  }

  /**
   * Solicita el restablecimiento de contraseña
   */
  solicitarRecuperacionContrasenia(email: string): Observable<any> {
    this.cargandoSubject.next(true);
    return this.authService.solicitarRecuperacionContrasenia(email).pipe(
      finalize(() => this.cargandoSubject.next(false))
    );
  }

  /**
   * Restablece la contraseña con el token
   */
  restablecerContrasenia(token: string, nuevaPass: string): Observable<any> {
    this.cargandoSubject.next(true);
    return this.authService.restablecerContrasenia(token, nuevaPass).pipe(
      finalize(() => this.cargandoSubject.next(false))
    );
  }

  /**
   * Getters auxiliares en español
   */
  obtenerUsuarioActual(): UsuarioDTO | null {
    return this.usuarioActualSubject.value;
  }

  obtenerTenantActual(): TenantSesionDTO | null {
    return this.tenantActualSubject.value;
  }

  estaAutenticado(): boolean {
    if (typeof window === 'undefined') return false;
    return !!(localStorage.getItem('access_token') || localStorage.getItem('token'));
  }

  esAdministrador(): boolean {
    const user = this.obtenerUsuarioActual();
    const rol = (localStorage.getItem('rol') || (user?.rol) || '').toUpperCase();
    return rol === 'SUPERADMIN' || rol === 'ADMIN' || rol === 'ADMINISTRADOR' || rol === 'SUPERVISOR';
  }

  esCliente(): boolean {
    const user = this.obtenerUsuarioActual();
    const rol = (localStorage.getItem('rol') || (user?.rol) || '').toUpperCase();
    return rol === 'CLIENTE' || (!this.esAdministrador() && this.estaAutenticado());
  }

  // ============================================================================
  // ALIASES DE COMPATIBILIDAD CON CÓDIGO EXISTENTE
  // ============================================================================
  get currentUser(): UsuarioDTO | null {
    return this.obtenerUsuarioActual();
  }

  get isAuthenticated(): boolean {
    return this.estaAutenticado();
  }

  login(email: string, pass: string): Observable<RespuestaAutenticacionDTO> {
    return this.iniciarSesion(email, pass);
  }

  logout(): void {
    this.cerrarSesion();
  }

  recoverPassword(email: string): Observable<any> {
    return this.solicitarRecuperacionContrasenia(email);
  }

  resetPassword(token: string, newPass: string): Observable<any> {
    return this.restablecerContrasenia(token, newPass);
  }
}
