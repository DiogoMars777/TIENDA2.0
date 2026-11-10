import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface TenantInfo {
  id: number;
  slug: string;
  nombre: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = `${environment.apiUrl}/auth`;

  constructor(private http: HttpClient) {}

  /**
   * Inicia sesión vía OAuth2 Form o JSON
   */
  iniciarSesion(email: string, password: string, tenantSlug?: string): Observable<any> {
    const payload = {
      email: email.trim().toLowerCase(),
      password: (password || '').trim(),
      tenant_slug: tenantSlug
    };
    return this.http.post(`${this.apiUrl}/login/json`, payload);
  }

  solicitarRecuperacionContrasenia(email: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/recuperar-password`, { email: email.trim().toLowerCase() });
  }

  restablecerContrasenia(token: string, newPassword: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/reset-password`, {
      token: token.trim(),
      new_password: newPassword
    });
  }

  obtenerToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('access_token') || localStorage.getItem('token');
  }

  estaAutenticado(): boolean {
    return !!this.obtenerToken();
  }

  obtenerUsuarioActual(): any {
    if (typeof window === 'undefined') return null;
    const userStr = localStorage.getItem('usuario') || localStorage.getItem('user');
    if (!userStr) return null;
    try {
      return JSON.parse(userStr);
    } catch {
      return null;
    }
  }

  obtenerTenantActual(): TenantInfo | null {
    if (typeof window === 'undefined') return null;
    const tenantIdStr = localStorage.getItem('tenant_id');
    const tenantSlug = localStorage.getItem('tenant_slug') || 'goldenstore';
    const tenantNombre = localStorage.getItem('tenant_nombre') || 'Shopyn Golden Store';
    if (!tenantIdStr) return null;
    return {
      id: parseInt(tenantIdStr, 10),
      slug: tenantSlug,
      nombre: tenantNombre
    };
  }

  obtenerRolUsuario(): string {
    if (typeof window === 'undefined') return '';
    const directRol = localStorage.getItem('rol') || localStorage.getItem('user_role');
    if (directRol) return directRol.toUpperCase();

    const user = this.obtenerUsuarioActual();
    if (user) {
      if (typeof user.rol === 'string') return user.rol.toUpperCase();
      if (user.rol && typeof user.rol.nombre === 'string') return user.rol.nombre.toUpperCase();
      if (user.rol_id === 1 || user.rolid === 1) return 'ADMIN';
      if (user.rol_id === 2 || user.rolid === 2) return 'CLIENTE';
    }
    return '';
  }

  esAdministrador(): boolean {
    const role = this.obtenerRolUsuario();
    return role === 'SUPERADMIN' || role === 'ADMIN' || role === 'ADMINISTRADOR' || role === 'SUPERVISOR';
  }

  esSuperAdmin(): boolean {
    const role = this.obtenerRolUsuario();
    return role === 'SUPERADMIN';
  }

  esCliente(): boolean {
    const role = this.obtenerRolUsuario();
    return role === 'CLIENTE' || (!this.esAdministrador() && this.estaAutenticado());
  }

  cerrarSesion(): void {
    if (typeof window === 'undefined') return;
    localStorage.removeItem('access_token');
    localStorage.removeItem('token');
    localStorage.removeItem('usuario');
    localStorage.removeItem('user');
    localStorage.removeItem('rol');
    localStorage.removeItem('user_role');
    localStorage.removeItem('tenant_id');
    localStorage.removeItem('tenant_slug');
    localStorage.removeItem('tenant_nombre');
  }

  // ============================================================================
  // ALIASES DE COMPATIBILIDAD
  // ============================================================================
  login(email: string, password: string): Observable<any> {
    return this.iniciarSesion(email, password);
  }

  requestPasswordRecovery(email: string): Observable<any> {
    return this.solicitarRecuperacionContrasenia(email);
  }

  resetPassword(token: string, newPassword: string): Observable<any> {
    return this.restablecerContrasenia(token, newPassword);
  }

  getToken(): string | null {
    return this.obtenerToken();
  }

  isAuthenticated(): boolean {
    return this.estaAutenticado();
  }

  getCurrentUser(): any {
    return this.obtenerUsuarioActual();
  }

  getUserRole(): string {
    return this.obtenerRolUsuario();
  }

  isAdmin(): boolean {
    return this.esAdministrador();
  }

  isCliente(): boolean {
    return this.esCliente();
  }

  logout(): void {
    this.cerrarSesion();
  }
}
