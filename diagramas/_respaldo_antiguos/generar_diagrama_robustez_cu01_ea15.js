!INC Local Scripts.EAConstants-JScript

// =====================================================================
// Script: Generar Diagrama de Robustez y Comunicación (BCE) - CU01
// Caso de Uso: CU01 - Gestionar Autenticación, Sesión y Recuperación
// Herramienta: Enterprise Architect 15 / 16 (Versión JavaScript / JScript)
// Proyecto: ECOMMERCE_TIENDA (SaaS Multi-Tenant)
// =====================================================================

function OnDiagramScript() {
    var currentPackage = Repository.GetTreeSelectedPackage();
    if (!currentPackage) {
        Session.Prompt("Por favor selecciona un Paquete en el Project Browser.", promptOK);
        return;
    }

    generarDiagramaRobustezCU01(currentPackage);

    Repository.RefreshModelView(0);
    Session.Prompt("¡Se generó exitosamente el Diagrama de Robustez y Comunicación del CU01!", promptOK);
}

function generarDiagramaRobustezCU01(pkg) {
    var nombreDiagrama = "CU01 - Robustez y Comunicación (Multi-Vistas)";
    var diagram = crearDiagramaLimpio(pkg, nombreDiagrama, "Analysis");

    // =================================================================
    // 1. CREACIÓN DE ELEMENTOS (ACTOR, BOUNDARIES, CONTROLS, ENTITIES)
    // =================================================================

    // --- ACTOR ---
    var actUsuario = crearElementoRobusto(pkg, "Usuario", "Actor", "");

    // --- BOUNDARIES (VISTAS Y SISTEMAS EXTERNOS) ---
    var bDashboard = crearElementoRobusto(pkg, "Page : Dashboard Principal", "Boundary", "boundary");
    var bLogin = crearElementoRobusto(pkg, "Page : Inicio de Sesion", "Boundary", "boundary");
    var bReset = crearElementoRobusto(pkg, "Page : Restablecer Contrasenia", "Boundary", "boundary");
    var bRecuperar = crearElementoRobusto(pkg, "Page : Recuperar Contrasenia", "Boundary", "boundary");
    var bSMTP = crearElementoRobusto(pkg, "Servidor : SMTP Gmail", "Boundary", "boundary");

    // --- CONTROLS (CONTROLADORES DE NEGOCIO Y SERVICIOS) ---
    var cAuth = crearElementoRobusto(pkg, "Gestor : Autenticacion", "Control", "control");
    var cRecov = crearElementoRobusto(pkg, "Gestor : Recuperacion Pass", "Control", "control");
    var cBitacora = crearElementoRobusto(pkg, "Gestor : Bitacora", "Control", "control");
    var cBcrypt = crearElementoRobusto(pkg, "Validador : Bcrypt Hasher", "Control", "control");
    var cJWT = crearElementoRobusto(pkg, "Gestor : Tokens JWT", "Control", "control");

    // --- ENTITIES (ENTIDADES DEL MODELO / DOMINIO) ---
    var eRol = crearElementoRobusto(pkg, "Rol", "Entity", "entity");
    var eTenant = crearElementoRobusto(pkg, "Empresa / Tenant", "Entity", "entity");
    var ePermiso = crearElementoRobusto(pkg, "Empresa Rol Permiso", "Entity", "entity");
    var eToken = crearElementoRobusto(pkg, "Sesion Token", "Entity", "entity");
    var eUser = crearElementoRobusto(pkg, "Usuario", "Entity", "entity");
    var eBitacora = crearElementoRobusto(pkg, "Bitacora", "Entity", "entity");

    // =================================================================
    // 2. DISPOSICIÓN ESPACIAL EN EL DIAGRAMA (COORDINATES EA)
    // =================================================================

    // Columna 1: Actor
    colocarElemento(diagram, actUsuario, 50, 160, -280, -390);

    // Columna 2: Vistas (Boundaries)
    colocarElemento(diagram, bDashboard, 280, 430, -70,  -140);
    colocarElemento(diagram, bLogin,     280, 430, -190, -260);
    colocarElemento(diagram, bReset,     280, 430, -320, -390);
    colocarElemento(diagram, bRecuperar, 280, 430, -450, -520);
    colocarElemento(diagram, bSMTP,      280, 430, -580, -650);

    // Columna 3: Controladores (Controls)
    colocarElemento(diagram, cAuth,     560, 710, -140, -220);
    colocarElemento(diagram, cRecov,    560, 710, -400, -480);
    colocarElemento(diagram, cBitacora, 810, 950, -80,  -150);
    colocarElemento(diagram, cBcrypt,   810, 950, -230, -300);
    colocarElemento(diagram, cJWT,      810, 950, -380, -450);

    // Columna 4: Entidades (Entities)
    colocarElemento(diagram, eRol,      1060, 1200, -50,  -120);
    colocarElemento(diagram, eTenant,   1060, 1200, -160, -230);
    colocarElemento(diagram, ePermiso,  1060, 1200, -270, -340);
    colocarElemento(diagram, eToken,    1060, 1200, -380, -450);
    colocarElemento(diagram, eUser,     1060, 1200, -490, -560);
    colocarElemento(diagram, eBitacora, 1060, 1200, -600, -670);

    // Nota informativa de arquitectura
    var nota = crearElemento(pkg, "Nota_Arquitectura", "Note");
    nota.Notes = "DIAGRAMA DE ROBUSTEZ Y COMUNICACIÓN (CU01):\n" +
                 "- Múltiples Vistas (Boundaries) y Controladores (Controls).\n" +
                 "- Flujo 1 (1-10): Login con Bcrypt, JWT y Tenant SaaS.\n" +
                 "- Flujo 2 (11-14): Recuperación con token temporal (15 min) y SMTP.\n" +
                 "- Flujo 3 (15-18): Restablecimiento de contraseña.\n" +
                 "- Flujo 4 (19-22): Logout y limpieza de sesión.\n" +
                 "- Auditoría transversal en Bitacora.";
    nota.Update();
    colocarElemento(diagram, nota, 50, 430, -690, -790);

    // =================================================================
    // 3. CONECTORES Y MENSAJES NUMERADOS (COMUNICACIÓN ROBUSTEZ)
    // =================================================================

    // --- ACTOR A VISTAS ---
    crearAsociacionMensaje(actUsuario, bLogin, "1: Iniciar Sesion(email, pass) >\n10: Mostrar Panel segun Rol() <\n21: Mostrar Login() <", "Bi-Directional");
    crearAsociacionMensaje(actUsuario, bDashboard, "19: Cerrar Sesion() >", "Source -> Destination");
    crearAsociacionMensaje(actUsuario, bRecuperar, "11: Solicitar Recuperacion(email) >", "Source -> Destination");
    crearAsociacionMensaje(actUsuario, bReset, "15: Abrir Enlace con Token(pass) >\n18: Contrasena Restablecida() <", "Bi-Directional");
    crearAsociacionMensaje(bSMTP, actUsuario, "14: Recibir Enlace en Buzon() >", "Source -> Destination");

    // --- VISTAS A CONTROLADORES ---
    crearAsociacionMensaje(bLogin, cAuth, "2: login(payload) >\n9: TokenResponse(token, usuario) <", "Bi-Directional");
    crearAsociacionMensaje(bDashboard, cAuth, "20: logout() >", "Source -> Destination");
    crearAsociacionMensaje(bRecuperar, cRecov, "12: solicitar_recuperacion(email) >", "Source -> Destination");
    crearAsociacionMensaje(bReset, cRecov, "16: reset_password(token, pass) >", "Source -> Destination");
    crearAsociacionMensaje(cRecov, bSMTP, "13: send_recovery_email(enlace) >", "Source -> Destination");

    // --- CONTROLADOR DE AUTENTICACIÓN A ENTIDADES ---
    crearAsociacionMensaje(cAuth, eTenant, "3: Validar Tenant Activo() >", "Source -> Destination");
    crearAsociacionMensaje(cAuth, eUser, "4: Consultar por Email() >\n5: Retornar Hash y Datos() <", "Bi-Directional");
    crearAsociacionMensaje(cAuth, eRol, "6: Cargar Rol de Usuario() >", "Source -> Destination");
    crearAsociacionMensaje(cAuth, ePermiso, "7: Obtener Permisos del Rol() >", "Source -> Destination");
    crearAsociacionMensaje(cAuth, eToken, "8: Guardar Session ID y Expiracion() >\n22: Limpiar Session ID() >", "Source -> Destination");

    // --- ORQUESTACIÓN ENTRE CONTROLADORES ---
    crearAsociacionMensaje(cAuth, cBcrypt, "verify_password(pass, hash) >", "Source -> Destination");
    crearAsociacionMensaje(cAuth, cJWT, "generar_tokens(claims, tenant) >", "Source -> Destination");
    crearAsociacionMensaje(cAuth, cBitacora, "log_bitacora(LOGIN) >\nlog_bitacora(LOGOUT) >", "Source -> Destination");

    crearAsociacionMensaje(cRecov, cJWT, "generar_token_reset() >\ndecodificar_token() >", "Source -> Destination");
    crearAsociacionMensaje(cRecov, cBcrypt, "get_password_hash(nueva_pass) >", "Source -> Destination");
    crearAsociacionMensaje(cRecov, cBitacora, "log_bitacora(RESET_PASS) >", "Source -> Destination");

    // --- CONTROLADOR DE RECUPERACIÓN A ENTIDADES ---
    crearAsociacionMensaje(cRecov, eUser, "Guardar Token Expiracion() >\n17: Actualizar PasswordHash() >", "Source -> Destination");

    // --- CONTROLADOR DE BITÁCORA A ENTIDAD ---
    crearAsociacionMensaje(cBitacora, eBitacora, "log_bitacora() >", "Source -> Destination");

    // =================================================================
    // 4. GUARDAR Y REFRESCAR DIAGRAMA
    // =================================================================
    Repository.SaveDiagram(diagram.DiagramID);
    Repository.ReloadDiagram(diagram.DiagramID);
    Repository.OpenDiagram(diagram.DiagramID);
}

// =====================================================================
// FUNCIONES AUXILIARES DE AUTOMATIZACIÓN DE ENTERPRISE ARCHITECT
// =====================================================================

function crearElementoRobusto(pkg, name, tipo, stereotype) {
    for (var i = 0; i < pkg.Elements.Count; i++) {
        var el = pkg.Elements.GetAt(i);
        if (el.Name == name) return el;
    }
    var newEl = pkg.Elements.AddNew(name, tipo);
    if (stereotype && stereotype != "") {
        newEl.Stereotype = stereotype;
    }
    newEl.Update();
    pkg.Elements.Refresh();
    return newEl;
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

function crearDiagramaLimpio(pkg, name, tipo) {
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
    var newDiag = pkg.Diagrams.AddNew(name, tipo);
    newDiag.Update();
    pkg.Diagrams.Refresh();
    return newDiag;
}

function colocarElemento(diag, el, left, right, top, bottom) {
    var diagObj = diag.DiagramObjects.AddNew("l=" + left + ";r=" + right + ";t=" + top + ";b=" + bottom + ";", "");
    diagObj.ElementID = el.ElementID;
    diagObj.Update();
}

function crearAsociacionMensaje(origen, destino, nombreMensaje, direccion) {
    for (var i = 0; i < origen.Connectors.Count; i++) {
        var con = origen.Connectors.GetAt(i);
        if (con.SupplierID == destino.ElementID && con.Name == nombreMensaje) return con;
    }
    var newCon = origen.Connectors.AddNew(nombreMensaje, "Association");
    newCon.SupplierID = destino.ElementID;
    if (direccion && direccion != "") {
        newCon.Direction = direccion;
    } else {
        newCon.Direction = "Source -> Destination";
    }
    newCon.Update();
    origen.Connectors.Refresh();
    return newCon;
}

OnDiagramScript();
