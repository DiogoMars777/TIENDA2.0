!INC Local Scripts.EAConstants-JScript

// =====================================================================
// Script: Generar Diagramas de Análisis de Clases (Boundary - Control - Entity)
// Proyecto: T-Shirt Boutique ERP & E-Commerce (ECOMMERCE_TIENDA)
// Herramienta: Enterprise Architect 15 / 16 (Versión JavaScript / JScript)
// =====================================================================

function OnDiagramScript() {
    var currentPackage = Repository.GetTreeSelectedPackage();
    if (!currentPackage) {
        Session.Prompt("Por favor selecciona un Paquete en el Project Browser.", promptOK);
        return;
    }

    var casosUso = [
        getCU01(), getCU02(), getCU03(), getCU04(), getCU05(), getCU06(),
        getCU07(), getCU08(), getCU09(), getCU10(), getCU11(), getCU13(),
        getCU14(), getCU15()
    ];

    for (var i = 0; i < casosUso.length; i++) {
        var cu = casosUso[i];
        var nombreActor = cu[0];
        var metodosActor = cu[1];
        var clases = cu[2];
        var nombreDiagrama = "Análisis " + cu[3];

        crearDiagramaCasoUso(currentPackage, nombreActor, metodosActor, clases, nombreDiagrama);
    }

    Repository.RefreshModelView(0);
    Session.Prompt("¡Se generaron exitosamente los 14 diagramas de análisis de clases (CU01 al CU15)!", promptOK);
}

function getCU01() {
    return [
        "Cliente",
        ["+ ingresarCredenciales(): void", "+ enviarLogin(): void", "+ solicitarRecuperacion(): void", "+ restablecerPassword(): void"],
        [
            ["CU01 Autenticación: UI_Auth", ["- loginForm: Form", "- recoverForm: Form", "- inputEmail: string", "- inputPassword: string"], ["+ mostrarLogin(): void", "+ enviarCredenciales(): void", "+ mostrarRecuperar(): void", "+ mostrarMensaje(): void"]],
            ["CU01 Autenticación: AuthController", ["- authService: AuthService", "- jwtManager: JWTManager", "- emailService: EmailService"], ["+ login_user(email, password): TokenResponse", "+ request_password_recovery(email): void", "+ reset_password(token, newPass): void", "+ verify_otp_code(email, code): boolean"]],
            ["CU01 Autenticación: Usuario", ["- id: int", "- nombre: string", "- apellido: string", "- email: string", "- passwordHash: string", "- rolId: int", "- activo: boolean"], ["+ buscarPorEmail(email): Usuario", "+ verificarPassword(pass): boolean", "+ actualizarPassword(hash): void"]],
            ["CU01 Autenticación: Rol", ["- id: int", "- nombre: string", "- descripcion: string", "- activo: boolean"], ["+ obtenerPermisos(): List<string>"]]
        ],
        "CU01 - Gestionar Autenticacion"
    ];
}

function getCU02() {
    return [
        "Administrador",
        ["+ listarUsuarios(): void", "+ crearUsuario(): void", "+ editarUsuario(): void", "+ asignarRol(): void"],
        [
            ["CU02 Usuarios y Roles: UI_UserRole", ["- tablaUsuarios: DataTable", "- modalUsuario: FormModal", "- selectorRol: Dropdown"], ["+ mostrarUsuarios(): void", "+ abrirModalCrear(): void", "+ guardarUsuario(): void", "+ cambiarEstadoActivo(): void"]],
            ["CU02 Usuarios y Roles: UserController", ["- userService: UserService", "- roleController: RoleController"], ["+ get_all(): List<Usuario>", "+ create_user(datos): Usuario", "+ update_user(id, datos): Usuario", "+ toggle_active(id): void"]],
            ["CU02 Usuarios y Roles: Usuario", ["- id: int", "- nombre: string", "- apellido: string", "- email: string", "- rolId: int", "- sucursalId: int", "- activo: boolean"], ["+ crear(): void", "+ actualizar(): void", "+ cambiarEstado(activo): void"]],
            ["CU02 Usuarios y Roles: Rol", ["- id: int", "- nombre: string", "- descripcion: string", "- activo: boolean"], ["+ crear(): void", "+ listarRoles(): List<Rol>"]]
        ],
        "CU02 - Gestionar Usuarios y Roles"
    ];
}

function getCU03() {
    return [
        "Administrador",
        ["+ verListaClientes(): void", "+ crearCliente(): void", "+ actualizarCliente(): void"],
        [
            ["CU03 Clientes: UI_Cliente", ["- tablaClientes: DataTable", "- formCliente: FormModal", "- buscadorInput: string"], ["+ mostrarClientes(): void", "+ cargarDatosCliente(): void", "+ guardarCliente(): void"]],
            ["CU03 Clientes: ClienteController", ["- clienteService: ClienteService"], ["+ listar_clientes(search): List<Cliente>", "+ obtener_cliente(id): Cliente", "+ crear_cliente(datos): Cliente", "+ actualizar_cliente(id, datos): Cliente"]],
            ["CU03 Clientes: Cliente", ["- id: int", "- usuarioId: int", "- nitCi: string", "- telefono: string", "- direccion: string", "- fechaRegistro: DateTime"], ["+ crear(): void", "+ actualizar(): void", "+ obtenerHistorialCompras(): List<Venta>"]],
            ["CU03 Clientes: Usuario", ["- id: int", "- nombre: string", "- apellido: string", "- email: string"], ["+ getDatosBasicos(): Usuario"]]
        ],
        "CU03 - Gestionar Clientes"
    ];
}

function getCU04() {
    return [
        "Administrador",
        ["+ verSucursales(): void", "+ registrarSucursal(): void", "+ editarSucursal(): void"],
        [
            ["CU04 Sucursales: UI_Sucursal", ["- tablaSucursales: DataTable", "- formSucursal: FormModal"], ["+ mostrarSucursales(): void", "+ abrirFormulario(): void", "+ guardarSucursal(): void"]],
            ["CU04 Sucursales: SucursalController", ["- sucursalService: SucursalService"], ["+ listar_sucursales(search, ciudad): List<Sucursal>", "+ crear_sucursal(datos): Sucursal", "+ actualizar_sucursal(id, datos): Sucursal", "+ baja_logica(id): void"]],
            ["CU04 Sucursales: Sucursal", ["- id: int", "- nombre: string", "- ciudad: string", "- direccion: string", "- telefono: string", "- latitud: decimal", "- longitud: decimal", "- activo: boolean"], ["+ crear(): void", "+ actualizar(): void", "+ cambiarEstado(activo): void"]]
        ],
        "CU04 - Gestionar Sucursales"
    ];
}

function getCU05() {
    return [
        "Administrador",
        ["+ verProductosAdmin(): void", "+ crearPolera(): void", "+ editarPolera(): void", "+ gestionarVariantes(): void"],
        [
            ["CU05 Productos: UI_Producto", ["- tablaProductos: DataTable", "- modalProducto: FormModal", "- gridVariantes: SubGrid"], ["+ mostrarProductos(): void", "+ abrirCrearProducto(): void", "+ guardarProducto(): void", "+ configurarVariantes(): void"]],
            ["CU05 Productos: ProductoController", ["- productoService: ProductoService"], ["+ listar_productos(search, catId): List<Producto>", "+ crear_producto(datos): Producto", "+ actualizar_producto(id, datos): Producto", "+ crear_variante(prodId, varData): Variante"]],
            ["CU05 Productos: Producto", ["- id: int", "- nombre: string", "- descripcion: string", "- precioBase: decimal", "- categoriaId: int", "- imagenPrincipal: string", "- activo: boolean"], ["+ crear(): void", "+ actualizar(): void", "+ bajaLogica(): void"]],
            ["CU05 Productos: VarianteProducto", ["- id: int", "- productoId: int", "- colorId: int", "- tallaId: int", "- sku: string", "- precioVenta: decimal"], ["+ crear(): void", "+ actualizarPrecio(): void"]]
        ],
        "CU05 - Gestionar Productos"
    ];
}

function getCU06() {
    return [
        "Administrador",
        ["+ verCategorias(): void", "+ crearCategoria(): void", "+ crearTemporada(): void", "+ crearColeccion(): void"],
        [
            ["CU06 Clasificación: UI_Clasificacion", ["- tabsClasificacion: Tabs", "- tablaCategorias: Table", "- tablaTemporadas: Table", "- tablaColecciones: Table"], ["+ mostrarCategorias(): void", "+ mostrarTemporadas(): void", "+ guardarCategoria(): void", "+ guardarTemporada(): void"]],
            ["CU06 Clasificación: ClasificacionController", ["- clasificacionService: ClasificacionService"], ["+ listar_categorias(): List<Categoria>", "+ crear_categoria(datos): Categoria", "+ listar_temporadas(): List<Temporada>", "+ crear_temporada(datos): Temporada", "+ listar_colecciones(): List<Coleccion>"]],
            ["CU06 Clasificación: Categoria", ["- id: int", "- nombre: string", "- descripcion: string", "- activo: boolean"], ["+ crear(): void", "+ actualizar(): void"]],
            ["CU06 Clasificación: Temporada", ["- id: int", "- nombre: string", "- fechaInicio: Date", "- fechaFin: Date", "- activo: boolean"], ["+ crear(): void", "+ actualizar(): void"]],
            ["CU06 Clasificación: Coleccion", ["- id: int", "- nombre: string", "- temporadaId: int", "- activo: boolean"], ["+ crear(): void"]]
        ],
        "CU06 - Gestionar Clasificacion de Prendas"
    ];
}

function getCU07() {
    return [
        "Administrador",
        ["+ verProveedores(): void", "+ registrarProveedor(): void", "+ vincularSuministro(): void"],
        [
            ["CU07 Proveedores: UI_Proveedor", ["- tablaProveedores: Table", "- modalProveedor: FormModal", "- panelSuministros: SubTable"], ["+ mostrarProveedores(): void", "+ nuevoProveedor(): void", "+ guardarProveedor(): void", "+ vincularProducto(): void"]],
            ["CU07 Proveedores: ProveedorController", ["- proveedorService: ProveedorService"], ["+ listar_proveedores(): List<Proveedor>", "+ crear_proveedor(datos): Proveedor", "+ actualizar_proveedor(id, datos): Proveedor", "+ vincular_producto(provId, prodId, costo, cant): void"]],
            ["CU07 Proveedores: Proveedor", ["- id: int", "- nombre: string", "- razonSocial: string", "- nit: string", "- contacto: string", "- telefono: string", "- activo: boolean"], ["+ crear(): void", "+ actualizar(): void", "+ bajaLogica(): void"]],
            ["CU07 Proveedores: ProductoProveedor", ["- idProducto: int", "- idProveedor: int", "- costoCompra: decimal", "- cantidad: int"], ["+ vincular(): void"]]
        ],
        "CU07 - Gestionar Proveedores y Suministros"
    ];
}

function getCU08() {
    return [
        "Cliente",
        ["+ navegarCatalogo(): void", "+ seleccionarSucursal(): void", "+ filtrarTallaColor(): void", "+ verDetallePrenda(): void"],
        [
            ["CU08 Catálogo: UI_Catalogo", ["- gridPoleras: List<Card>", "- selectorSucursal: Dropdown", "- chipsTallas: ChipGroup", "- buscadorTexto: string"], ["+ mostrarCatalogo(): void", "+ filtrarPorSucursal(): void", "+ seleccionarTallaColor(): void", "+ verDetalle(): void"]],
            ["CU08 Catálogo: InventarioController", ["- catalogoService: CatalogoService", "- stockService: StockService"], ["+ listar_catalogo(sucursalId, catId, genero): List<ProductoCatalogoItem>", "+ verificar_stock_variante(varId, sucId): int"]],
            ["CU08 Catálogo: Producto", ["- id: int", "- nombre: string", "- precioBase: decimal", "- categoriaId: int", "- imagenPrincipal: string"], ["+ listarActivos(): List<Producto>"]],
            ["CU08 Catálogo: VarianteProducto", ["- id: int", "- productoId: int", "- colorId: int", "- tallaId: int", "- sku: string", "- precioVenta: decimal"], ["+ getDisponibilidad(): int"]],
            ["CU08 Catálogo: Inventario", ["- id: int", "- varianteId: int", "- sucursalId: int", "- stock: int", "- stockMinimo: int"], ["+ estaDisponible(): boolean", "+ getStockSucursal(): int"]]
        ],
        "CU08 - Consultar Catalogo y Disponibilidad"
    ];
}

function getCU09() {
    return [
        "Cliente",
        ["+ verCarrito(): void", "+ agregarItem(): void", "+ modificarCantidad(): void", "+ eliminarItem(): void"],
        [
            ["CU09 Carrito: UI_Carrito", ["- itemsCarrito: List<ItemCard>", "- selectorSucursalRetiro: Dropdown", "- subtotalLabel: Label", "- btnCheckout: Button"], ["+ mostrarCarrito(): void", "+ actualizarCantidad(): void", "+ eliminarItem(): void", "+ seleccionarModalidad(): void"]],
            ["CU09 Carrito: CarritoController", ["- carritoService: CarritoService", "- inventarioService: InventarioService"], ["+ obtener_carrito_dto(clienteId): CarritoDTO", "+ agregar_item(clienteId, varId, cant): void", "+ actualizar_item(clienteId, varId, cant): void", "+ eliminar_item(clienteId, varId): void"]],
            ["CU09 Carrito: Carrito", ["- id: int", "- clienteId: int", "- sucursalId: int", "- estado: string", "- fechaActualizacion: DateTime"], ["+ agregarItem(): void", "+ calcularSubtotal(): decimal", "+ vaciar(): void"]],
            ["CU09 Carrito: CarritoItem", ["- carritoId: int", "- varianteId: int", "- cantidad: int", "- precioUnitario: decimal"], ["+ calcularTotalLinea(): decimal"]]
        ],
        "CU09 - Gestionar Carrito de Compras"
    ];
}

function getCU10() {
    return [
        "Cliente",
        ["+ apartarPrendas(): void", "+ elegirSucursalRetiro(): void", "+ confirmarReserva(): void", "+ verMisReservas(): void", "+ cancelarReserva(): void"],
        [
            ["CU10 Reservas: UI_Reservas", ["- listaReservas: List<ReservaCard>", "- modalDetalleReserva: Modal", "- btnConfirmarReserva: Button"], ["+ mostrarMisReservas(): void", "+ verCodigoReserva(): void", "+ confirmarReserva(): void", "+ solicitarCancelacion(): void"]],
            ["CU10 Reservas: ReservaController", ["- reservaService: ReservaService", "- inventarioController: InventarioController"], ["+ crear_reserva(clienteId, datos): Reserva", "+ listar_reservas_usuario(clienteId): List<Reserva>", "+ cancelar_reserva(reservaId, clienteId): boolean"]],
            ["CU10 Reservas: Reserva", ["- id: int", "- codigoReserva: string", "- clienteId: int", "- sucursalId: int", "- estado: string", "- fechaCreacion: DateTime", "- fechaExpiracion: DateTime"], ["+ crear(): void", "+ cancelar(): void", "+ bloquearStock(): void"]],
            ["CU10 Reservas: ReservaDetalle", ["- id: int", "- reservaId: int", "- varianteId: int", "- cantidad: int", "- precioUnitario: decimal"], ["+ registrarItem(): void"]],
            ["CU10 Reservas: Inventario", ["- varianteId: int", "- sucursalId: int", "- stock: int"], ["+ reservarStock(cant): void", "+ liberarStock(cant): void"]]
        ],
        "CU10 - Gestionar Reservas de Prendas"
    ];
}

function getCU11() {
    return [
        "Encargado",
        ["+ consultarReservasSucursal(): void", "+ buscarCodigo(): void", "+ entregarPrendas(): void"],
        [
            ["CU11 Atender Reservas: UI_AtenderReservas", ["- inputCodigoAlfanumerico: string", "- cardDetalleReserva: Card", "- btnConfirmarEntrega: Button"], ["+ buscarCodigo(): void", "+ verificarPrendas(): void", "+ confirmarEntrega(): void", "+ cancelarPorNoRetiro(): void"]],
            ["CU11 Atender Reservas: AtenderReservaController", ["- reservaService: ReservaService", "- inventarioService: InventarioService"], ["+ buscar_reserva_por_codigo(codigo): Reserva", "+ listar_reservas_admin(sucursalId, estado): List<Reserva>", "+ atender_reserva(reservaId, accion): Reserva"]],
            ["CU11 Atender Reservas: Reserva", ["- id: int", "- codigoReserva: string", "- sucursalId: int", "- estado: string", "- fechaEntrega: DateTime"], ["+ marcarEntregada(): void", "+ marcarCancelada(): void"]],
            ["CU11 Atender Reservas: Inventario", ["- varianteId: int", "- sucursalId: int", "- stock: int"], ["+ descontarFisico(cant): void"]]
        ],
        "CU11 - Atender Reservas en Sucursal"
    ];
}

function getCU13() {
    return [
        "Administrador",
        ["+ verExistencias(): void", "+ verKardex(): void", "+ registrarIngreso(): void", "+ registrarAjuste(): void"],
        [
            ["CU13 Inventario Kardex: UI_InventarioKardex", ["- tablaInventario: DataTable", "- tablaMovimientos: DataTable", "- modalMovimiento: FormModal"], ["+ verExistencias(): void", "+ verKardex(): void", "+ registrarIngreso(): void", "+ registrarAjuste(): void"]],
            ["CU13 Inventario Kardex: InventarioController", ["- kardexService: KardexService"], ["+ listar_inventario(sucursalId): List<Inventario>", "+ registrar_movimiento(datosMov): MovimientoInventario", "+ ajustar_stock(varId, sucId, cant): void"]],
            ["CU13 Inventario Kardex: Inventario", ["- id: int", "- varianteId: int", "- sucursalId: int", "- stock: int", "- stockMinimo: int"], ["+ actualizarStock(cant): void", "+ alertaStockMinimo(): boolean"]],
            ["CU13 Inventario Kardex: MovimientoInventario", ["- id: int", "- inventarioId: int", "- tipoMovimiento: string", "- cantidad: int", "- motivoId: int", "- fecha: DateTime"], ["+ registrar(): void"]]
        ],
        "CU13 - Gestionar Inventario y Movimientos"
    ];
}

function getCU14() {
    return [
        "Cajero",
        ["+ escanearVariante(): void", "+ seleccionarMetodoCobro(): void", "+ emitirRecibo(): void"],
        [
            ["CU14 Ventas Presenciales POS: UI_POS", ["- lectorCodigoBarra: Scanner", "- tablaLineasVenta: DataTable", "- calculadorCambio: VueltoCalc", "- selectorMetodoPago: Dropdown"], ["+ escanearVariante(): void", "+ calcularCambio(): decimal", "+ procesarCobro(): void", "+ imprimirRecibo(): void"]],
            ["CU14 Ventas Presenciales POS: VentaPresencialController", ["- ventaService: VentaService", "- inventarioService: InventarioService", "- reciboService: ReciboService"], ["+ registrar_venta_presencial(datosVenta): Venta", "+ procesar_pago(ventaId, metodoId, monto): Pago", "+ emitir_recibo(ventaId): Recibo"]],
            ["CU14 Ventas Presenciales POS: Venta", ["- id: int", "- sucursalId: int", "- usuarioId: int", "- clienteId: int", "- total: decimal", "- tipoVenta: string", "- estado: string"], ["+ crear(): void", "+ calcularTotales(): decimal"]],
            ["CU14 Ventas Presenciales POS: DetalleVenta", ["- id: int", "- ventaId: int", "- varianteId: int", "- cantidad: int", "- precioUnitario: decimal", "- subtotal: decimal"], ["+ registrarLinea(): void"]],
            ["CU14 Ventas Presenciales POS: Pago", ["- id: int", "- ventaId: int", "- metodoPagoId: int", "- monto: decimal", "- estado: string"], ["+ registrar(): void"]],
            ["CU14 Ventas Presenciales POS: Recibo", ["- id: int", "- ventaId: int", "- numeroRecibo: string", "- fechaEmision: DateTime"], ["+ generarRecibo(): void"]]
        ],
        "CU14 - Registrar Ventas Presenciales (POS)"
    ];
}

function getCU15() {
    return [
        "Cliente",
        ["+ realizarCheckoutOnline(): void", "+ verMisPedidos(): void", "+ verTrackingOrden(): void"],
        [
            ["CU15 Compras Digitales: UI_ComprasDigitales", ["- listaMisPedidos: List<OrderCard>", "- modalTracking: TimelineModal", "- btnDescargarRecibo: Button"], ["+ verMisPedidos(): void", "+ verTrackingOrden(): void", "+ descargarComprobante(): void"]],
            ["CU15 Compras Digitales: CompraDigitalController", ["- ventaService: VentaService", "- carritoService: CarritoService"], ["+ realizar_compra_digital(clienteId, datosCompra): Venta", "+ listar_mis_ordenes(clienteId): List<Venta>", "+ consultar_tracking(ventaId): EstadoTrackingDTO"]],
            ["CU15 Compras Digitales: Venta", ["- id: int", "- clienteId: int", "- total: decimal", "- tipoVenta: string", "- estado: string", "- fechaVenta: DateTime"], ["+ crearOrdenDigital(): void", "+ actualizarEstado(): void"]],
            ["CU15 Compras Digitales: DetalleVenta", ["- id: int", "- ventaId: int", "- varianteId: int", "- cantidad: int", "- precioUnitario: decimal"], ["+ agregarItem(): void"]],
            ["CU15 Compras Digitales: Carrito", ["- id: int", "- clienteId: int", "- estado: string"], ["+ vaciar(): void"]]
        ],
        "CU15 - Realizar Compras Digitales"
    ];
}

function crearDiagramaCasoUso(package, nombreActor, metodosActor, clases, nombreDiagrama) {
    var actor = crearElemento(package, nombreActor, "Actor");
    for (var m = 0; m < metodosActor.length; m++) {
        agregarMetodo(actor, metodosActor[m]);
    }

    var listaClases = [];
    for (var c = 0; c < clases.length; c++) {
        var cInfo = clases[c];
        var cObj = crearClase(package, cInfo[0]);
        for (var a = 0; a < cInfo[1].length; a++) {
            agregarAtributo(cObj, cInfo[1][a]);
        }
        for (var me = 0; me < cInfo[2].length; me++) {
            agregarMetodo(cObj, cInfo[2][me]);
        }
        listaClases.push(cObj);
    }

    var diagram = crearDiagramaLimpio(package, nombreDiagrama);
    colocarElemento(diagram, actor, "50", "150", "-50", "-200");

    var x = 250;
    var y = -100;
    for (var i = 0; i < listaClases.length; i++) {
        var cl = listaClases[i];
        var altura = 120 + (cl.Methods.Count * 20) + (cl.Attributes.Count * 18);
        colocarElemento(diagram, cl, x.toString(), (x + 220).toString(), y.toString(), (y - altura).toString());
        x += 260;
    }

    if (listaClases.length > 0) {
        crearAsociacion(actor, listaClases[0], "");
        for (var j = 0; j < listaClases.length - 1; j++) {
            crearAsociacion(listaClases[j], listaClases[j + 1], "");
        }
    }

    Repository.SaveDiagram(diagram.DiagramID);
    Repository.ReloadDiagram(diagram.DiagramID);
    Repository.OpenDiagram(diagram.DiagramID);
}

function crearElemento(pkg, name, tipo) {
    for (var i = 0; i < pkg.Elements.Count; i++) {
        var el = pkg.Elements.GetAt(i);
        if (el.Name == name && el.Type == tipo) return el;
    }
    var newEl = pkg.Elements.AddNew(name, tipo);
    newEl.Update();
    pkg.Elements.Refresh();
    return newEl;
}

function crearClase(pkg, name) {
    for (var i = 0; i < pkg.Elements.Count; i++) {
        var el = pkg.Elements.GetAt(i);
        if (el.Name == name && el.Type == "Class") return el;
    }
    var newEl = pkg.Elements.AddNew(name, "Class");
    newEl.Update();
    pkg.Elements.Refresh();
    return newEl;
}

function agregarAtributo(clase, nombre) {
    for (var i = 0; i < clase.Attributes.Count; i++) {
        if (clase.Attributes.GetAt(i).Name == nombre) return;
    }
    var attr = clase.Attributes.AddNew(nombre, "");
    attr.Update();
    clase.Attributes.Refresh();
}

function agregarMetodo(el, nombre) {
    for (var i = 0; i < el.Methods.Count; i++) {
        if (el.Methods.GetAt(i).Name == nombre) return;
    }
    var method = el.Methods.AddNew(nombre, "");
    method.Update();
    el.Methods.Refresh();
}

function crearDiagramaLimpio(pkg, name) {
    for (var i = 0; i < pkg.Diagrams.Count; i++) {
        var diag = pkg.Diagrams.GetAt(i);
        if (diag.Name == name) {
            for (var o = diag.DiagramObjects.Count - 1; o >= 0; o--) {
                diag.DiagramObjects.Delete(o);
            }
            for (var l = diag.DiagramLinks.Count - 1; l >= 0; l--) {
                diag.DiagramLinks.Delete(l);
            }
            diag.DiagramObjects.Refresh();
            diag.DiagramLinks.Refresh();
            diag.Update();
            return diag;
        }
    }
    var newDiag = pkg.Diagrams.AddNew(name, "Class");
    newDiag.Update();
    pkg.Diagrams.Refresh();
    return newDiag;
}

function colocarElemento(diag, el, left, right, top, bottom) {
    var diagObj = diag.DiagramObjects.AddNew("l=" + left + ";r=" + right + ";t=" + top + ";b=" + bottom + ";", "");
    diagObj.ElementID = el.ElementID;
    diagObj.Update();
}

function crearAsociacion(origen, destino, estereotipo) {
    for (var i = 0; i < origen.Connectors.Count; i++) {
        var con = origen.Connectors.GetAt(i);
        if (con.SupplierID == destino.ElementID && con.Type == "Association") return;
    }
    var newCon = origen.Connectors.AddNew("", "Association");
    newCon.SupplierID = destino.ElementID;
    if (estereotipo != "") newCon.Stereotype = estereotipo;
    newCon.Update();
    origen.Connectors.Refresh();
}

OnDiagramScript();
