// ==============================================================================
// CAPA VISTA (MVC - VIEW COMPONENT)
// Módulo: CU1 - Gestionar Autenticación
// Ubicación: frontend-web/src/app/views/cu1_gestionar_autenticacion/login/login.component.ts
// ==============================================================================

import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthController } from '../../../controllers/cu1_gestionar_autenticacion/auth.controller';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent {
  loginForm: FormGroup;
  isLoading = false;
  errorMessage = '';
  showPassword = false;

  constructor(
    private fb: FormBuilder, 
    private router: Router,
    private authController: AuthController
  ) {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required]]
    });
  }

  onSubmit() {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }
    this.isLoading = true;
    this.errorMessage = '';
    
    const { email, password } = this.loginForm.value;

    this.authController.iniciarSesion(email, password).subscribe({
      next: (response) => {
        this.isLoading = false;
        
        const rol = (response.rol || 'CLIENTE').toUpperCase();
        
        // Redirigir según el rol del usuario
        if (rol === 'SUPERADMIN' || (response as any).es_superadmin) {
          this.router.navigate(['/admin/suscripciones-tenants']);
        } else if (rol === 'ADMIN' || rol === 'ADMINISTRADOR' || rol === 'SUPERVISOR') {
          this.router.navigate(['/admin/users']);
        } else {
          this.router.navigate(['/catalogo']);
        }
      },
      error: (err) => {
        this.isLoading = false;
        console.error('Error de login:', err);
        this.errorMessage = err.error?.detail || 'Error al iniciar sesión. Verifique sus credenciales.';
      }
    });
  }
}
