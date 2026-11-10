import { inject } from '@angular/core';
import { Router, CanActivateFn } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const adminGuard: CanActivateFn = (route, state) => {
  const router = inject(Router);
  const authService = inject(AuthService);

  if (!authService.isAuthenticated()) {
    router.navigate(['/login']);
    return false;
  }

  if (authService.isAdmin()) {
    return true;
  }

  // Si es un cliente u otro rol sin privilegios administrativos, lo redirigimos a la tienda
  router.navigate(['/catalogo']);
  return false;
};

export const superAdminGuard: CanActivateFn = (route, state) => {
  const router = inject(Router);
  const authService = inject(AuthService);

  if (!authService.isAuthenticated()) {
    router.navigate(['/login']);
    return false;
  }

  if (authService.esSuperAdmin()) {
    return true;
  }

  // Si es un Admin de Tenant, lo redirigimos a su propio negocio
  if (authService.isAdmin()) {
    router.navigate(['/admin/users']);
    return false;
  }

  router.navigate(['/catalogo']);
  return false;
};

