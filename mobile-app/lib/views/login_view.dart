// ==============================================================================
// VISTA DE LOGIN CON SELECTOR MULTI-EMPRESA (MVC - VIEW)
// Interfaz de Autenticación y Selección de Empresa (Tenant) para App Móvil
// ==============================================================================

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../controllers/auth_controller.dart';
import '../controllers/product_controller.dart';
import '../controllers/cart_controller.dart';
import '../controllers/reservation_controller.dart';
import 'register_view.dart';

class LoginView extends StatefulWidget {
  const LoginView({super.key});

  @override
  State<LoginView> createState() => _LoginViewState();
}

class _LoginViewState extends State<LoginView> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;
  bool _rememberMe = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        context.read<ProductController>().fetchEmpresasDisponibles();
      }
    });
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    if (!_formKey.currentState!.validate()) return;

    final authController = Provider.of<AuthController>(context, listen: false);
    final productController = Provider.of<ProductController>(context, listen: false);
    final cartController = Provider.of<CartController>(context, listen: false);
    final resController = Provider.of<ReservationController>(context, listen: false);

    final selectedEmpresaId = productController.empresaSeleccionadaId;
    final selectedEmpresaNombre = productController.empresaActual.nombre;

    final success = await authController.login(
      _emailController.text.trim(),
      _passwordController.text.trim(),
      selectedTenantId: selectedEmpresaId,
      selectedEmpresaNombre: selectedEmpresaNombre,
    );

    if (success && mounted) {
      // Si el correo pertenece explícitamente a un administrador de otra empresa, sincronizar o respetar la empresa elegida
      final emailLower = _emailController.text.trim().toLowerCase();
      int targetTenantId = selectedEmpresaId;
      if (emailLower.contains('saintseya')) {
        targetTenantId = 2;
      } else if (emailLower == 'admin@goldenstore.com') {
        targetTenantId = 1;
      }

      await productController.seleccionarEmpresa(targetTenantId);
      cartController.limpiarCarrito();
      if (productController.sucursalActual != null) {
        cartController.setSucursal(
          productController.sucursalActual!.id,
          productController.sucursalActual!.nombre,
        );
      }
      resController.cargarMisReservas(
        token: authController.currentUser?.token,
        tenantId: targetTenantId,
        modoOfflineSimulado: productController.modoOfflineSimulado,
      );

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '¡Bienvenido ${authController.currentUser?.nombre} a ${productController.empresaActual.nombre}!',
          ),
          backgroundColor: Colors.green.shade600,
        ),
      );
      Navigator.pushReplacementNamed(context, '/');
    }
  }

  Future<void> _entrarDirectoAEmpresa() async {
    final authController = Provider.of<AuthController>(context, listen: false);
    final productController = Provider.of<ProductController>(context, listen: false);
    final cartController = Provider.of<CartController>(context, listen: false);
    final resController = Provider.of<ReservationController>(context, listen: false);

    final emp = productController.empresaActual;
    if (!authController.isAuthenticated) {
      await authController.loginInvitadoEmpresa(
        tenantId: emp.id,
        empresaNombre: emp.nombre,
      );
    }
    await productController.seleccionarEmpresa(emp.id);
    cartController.limpiarCarrito();
    if (productController.sucursalActual != null) {
      cartController.setSucursal(
        productController.sucursalActual!.id,
        productController.sucursalActual!.nombre,
      );
    }
    resController.cargarMisReservas(
      token: authController.currentUser?.token,
      tenantId: emp.id,
      modoOfflineSimulado: productController.modoOfflineSimulado,
    );

    if (!mounted) return;
    Navigator.pushReplacementNamed(context, '/');
  }

  @override
  Widget build(BuildContext context) {
    final authController = Provider.of<AuthController>(context);
    final productController = Provider.of<ProductController>(context);
    final empresaActual = productController.empresaActual;

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 22.0, vertical: 16.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Header Logo / Branding dinámico según la empresa seleccionada
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: empresaActual.id == 2 ? const Color(0xFFFEF3C7) : const Color(0xFFFFE4E6),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    empresaActual.id == 2 ? Icons.auto_awesome : Icons.checkroom_outlined,
                    size: 44,
                    color: empresaActual.id == 2 ? const Color(0xFFD97706) : const Color(0xFFE11D48),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  empresaActual.nombre,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 25,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF0F172A),
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Selecciona la empresa a la que deseas ingresar',
                  style: TextStyle(
                    fontSize: 13,
                    color: Colors.grey.shade600,
                  ),
                ),
                const SizedBox(height: 18),

                // ==============================================================
                // SELECTOR DE EMPRESA DISPONIBLE (MULTI-TENANT)
                // ==============================================================
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF0F172A), Color(0xFF1E293B)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: const [
                      BoxShadow(color: Colors.black12, blurRadius: 8, offset: Offset(0, 3)),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.apartment, color: Color(0xFF38BDF8), size: 20),
                          const SizedBox(width: 8),
                          const Expanded(
                            child: Text(
                              'EMPRESA / TIENDA DISPONIBLE:',
                              style: TextStyle(
                                color: Color(0xFF38BDF8),
                                fontSize: 11.5,
                                fontWeight: FontWeight.w800,
                                letterSpacing: 0.6,
                              ),
                            ),
                          ),
                          IconButton(
                            visualDensity: VisualDensity.compact,
                            padding: EdgeInsets.zero,
                            constraints: const BoxConstraints(),
                            icon: const Icon(Icons.refresh, color: Colors.white70, size: 18),
                            tooltip: 'Actualizar empresas disponibles',
                            onPressed: () => productController.fetchEmpresasDisponibles(),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
                        decoration: BoxDecoration(
                          color: Colors.white.withAlpha(22),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: const Color(0xFF38BDF8).withAlpha(110)),
                        ),
                        child: DropdownButtonHideUnderline(
                          child: DropdownButton<int>(
                            dropdownColor: const Color(0xFF0F172A),
                            value: productController.empresaSeleccionadaId,
                            isExpanded: true,
                            icon: const Icon(Icons.keyboard_arrow_down, color: Color(0xFF38BDF8)),
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 15,
                              fontWeight: FontWeight.bold,
                            ),
                            items: productController.empresas.map((emp) {
                              return DropdownMenuItem<int>(
                                value: emp.id,
                                child: Row(
                                  children: [
                                    Icon(
                                      emp.id == 2 ? Icons.auto_awesome : Icons.storefront,
                                      size: 18,
                                      color: emp.id == 2 ? Colors.amber : const Color(0xFF38BDF8),
                                    ),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: Text(
                                        emp.nombre,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                                  ],
                                ),
                              );
                            }).toList(),
                            onChanged: (nuevoTenantId) {
                              if (nuevoTenantId != null) {
                                productController.seleccionarEmpresa(nuevoTenantId);
                              }
                            },
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF38BDF8),
                            foregroundColor: const Color(0xFF0F172A),
                            padding: const EdgeInsets.symmetric(vertical: 11),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                          icon: const Icon(Icons.shopping_bag_outlined, size: 18),
                          label: Text(
                            'Entrar al Catálogo de ${empresaActual.nombre}',
                            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13),
                          ),
                          onPressed: _entrarDirectoAEmpresa,
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 18),

                // Card Contenedor del Formulario de Login
                Card(
                  elevation: 2,
                  shadowColor: Colors.black12,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                  color: Colors.white,
                  child: Padding(
                    padding: const EdgeInsets.all(22.0),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Text(
                            'Iniciar Sesión en ${empresaActual.nombre}',
                            style: const TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.bold,
                              color: Color(0xFF0F172A),
                            ),
                          ),
                          const SizedBox(height: 14),

                          // Alerta de Error
                          if (authController.errorMessage != null) ...[
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: const Color(0xFFFEF2F2),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: const Color(0xFFFCA5A5)),
                              ),
                              child: Row(
                                children: [
                                  const Icon(Icons.error_outline, color: Color(0xFFEF4444), size: 20),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Text(
                                      authController.errorMessage!,
                                      style: const TextStyle(
                                        color: Color(0xFF991B1B),
                                        fontSize: 13,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 16),
                          ],

                          // Campo Correo Electrónico
                          const Text(
                            'Correo Electrónico',
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              color: Color(0xFF334155),
                            ),
                          ),
                          const SizedBox(height: 8),
                          TextFormField(
                            controller: _emailController,
                            keyboardType: TextInputType.emailAddress,
                            decoration: InputDecoration(
                              hintText: empresaActual.id == 2 ? 'admin@saintseya.com' : 'cliente@goldenstore.com',
                              prefixIcon: const Icon(Icons.email_outlined, size: 20),
                              filled: true,
                              fillColor: const Color(0xFFF8FAFC),
                              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(10),
                                borderSide: BorderSide(color: Colors.grey.shade300),
                              ),
                              enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(10),
                                borderSide: BorderSide(color: Colors.grey.shade300),
                              ),
                            ),
                            validator: (val) {
                              if (val == null || val.trim().isEmpty) return 'Ingresa tu correo';
                              if (!val.contains('@')) return 'Ingresa un correo válido';
                              return null;
                            },
                          ),
                          const SizedBox(height: 16),

                          // Campo Contraseña
                          const Text(
                            'Contraseña',
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              color: Color(0xFF334155),
                            ),
                          ),
                          const SizedBox(height: 8),
                          TextFormField(
                            controller: _passwordController,
                            obscureText: _obscurePassword,
                            decoration: InputDecoration(
                              hintText: '••••••••',
                              prefixIcon: const Icon(Icons.lock_outline, size: 20),
                              suffixIcon: IconButton(
                                icon: Icon(
                                  _obscurePassword ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                                  size: 20,
                                ),
                                onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                              ),
                              filled: true,
                              fillColor: const Color(0xFFF8FAFC),
                              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(10),
                                borderSide: BorderSide(color: Colors.grey.shade300),
                              ),
                              enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(10),
                                borderSide: BorderSide(color: Colors.grey.shade300),
                              ),
                            ),
                            validator: (val) {
                              if (val == null || val.isEmpty) return 'Ingresa tu contraseña';
                              return null;
                            },
                          ),
                          const SizedBox(height: 12),

                          // Recordarme & Olvidaste Contraseña
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Row(
                                children: [
                                  SizedBox(
                                    height: 24,
                                    width: 24,
                                    child: Checkbox(
                                      value: _rememberMe,
                                      onChanged: (val) => setState(() => _rememberMe = val ?? false),
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  const Text(
                                    'Recordarme',
                                    style: TextStyle(fontSize: 13, color: Color(0xFF64748B)),
                                  ),
                                ],
                              ),
                              GestureDetector(
                                onTap: () {
                                  authController.clearMessages();
                                  Navigator.pushNamed(context, '/recover-password');
                                },
                                child: const Text(
                                  '¿Olvidaste tu contraseña?',
                                  style: TextStyle(
                                    fontSize: 13,
                                    fontWeight: FontWeight.w600,
                                    color: Color(0xFFE11D48),
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 20),

                          // Botón Iniciar Sesión
                          ElevatedButton(
                            onPressed: authController.isLoading ? null : _handleLogin,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFFE11D48),
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(vertical: 14),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(10),
                              ),
                              elevation: 0,
                            ),
                            child: authController.isLoading
                                ? const SizedBox(
                                    height: 20,
                                    width: 20,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                                    ),
                                  )
                                : const Text(
                                    'Iniciar Sesión',
                                    style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                                  ),
                          ),
                          const SizedBox(height: 16),

                          // Enlace para crear nueva cuenta de Cliente
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Text(
                                '¿No tienes cuenta? ',
                                style: TextStyle(fontSize: 13, color: Color(0xFF64748B)),
                              ),
                              GestureDetector(
                                onTap: () {
                                  authController.clearMessages();
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(builder: (context) => const RegisterView()),
                                  );
                                },
                                child: const Text(
                                  'Registrarme Gratis',
                                  style: TextStyle(
                                    fontSize: 13,
                                    fontWeight: FontWeight.bold,
                                    color: Color(0xFFE11D48),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
