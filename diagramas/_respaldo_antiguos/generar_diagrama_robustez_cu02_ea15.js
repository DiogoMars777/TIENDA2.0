!INC Local Scripts.EAConstants-JScript

// =====================================================================
// Script: Generar Diagrama de Robustez y Comunicación (BCE) - CU02
// Caso de Uso: CU02 - Gestionar Usuarios y Roles (Multi-Tenant SaaS)
// Herramienta: Enterprise Architect 15 / 16 (Versión JavaScript / JScript)
// Proyecto: ECOMMERCE_TIENDA (SaaS Multi-Tenant)
// =====================================================================

function OnDiagramScript() {
    var currentPackage = Repository.GetTreeSelectedPackage();
    if (!currentPackage) {
        Session.Prompt("Por favor selecciona un Paquete en el Project Browser.", promptOK);
        return;
    }

    generarDiagramaRobustezCU02(currentPackage);

    Repository.RefreshModelView(0);
    Session.Prompt("¡Se generó exitosamente el Diagrama de Robustez y Comunicación del CU02 (Usuarios y Roles)!", promptOK);
}

function generarDiagramaRobustezCU02(pkg) {
    var nombreDiagrama = "CU02 - Robustez y Comunicación (Multi-Vistas)";
    var diagram = crearDiagramaLimpio(pkg, nombreDiagrama, "Analysis");

    // =================================================================
    // 1. CREACIÓN DE ELEMENTOS (ACTOR, BOUNDARIES, CONTROLS, ENTITIES)
    // =================================================================

    // --- ACTOR ---
    var actAdmin = crearElementoRobusto(pkg, "Administrador", "Actor", "");

    // --- BOUNDARIES (VISTAS ANGULAR) ---
    var bUserDetail = crearElementoRobusto(pkg, "Page : Modal Detalle y Estado", "Boundary", "boundary");
    var bUserList = crearElementoRobusto(pkg, "Page : Lista de Usuarios", "Boundary", "boundary");
    var bUserModal = crearElementoRobusto(pkg, "Page : Modal Formulario Usuario", "Boundary", "boundary");
    var bRoleList = crearElementoRobusto(pkg, "Page : Lista de Roles", "Boundary", "boundary");
    var bRolePerms = crearElementoRobusto(pkg, "Page : Modal Permisos de Rol", "Boundary", "boundary");

    // --- CONTROLS (CONTROLADORES DE NEGOCIO Y REGLAS) ---
    var cUser = crearElementoRobusto(pkg, "Gestor : Usuarios", "Control", "control");
    var cRole = crearElementoRobusto(pkg, "Gestor : Roles y Permisos", "Control", "control");
    var cPlan = crearElementoRobusto(pkg, "Validador : Plan Suscripcion", "Control", "control");
    var cBcrypt = crearElementoRobusto(pkg, "Validador : Bcrypt Hasher", "Control", "control");
    var cBitacora = crearElementoRobusto(pkg, "Gestor : Bitacora", "Control", "control");

    // --- ENTITIES (ENTIDADES DEL MODELO / DOMINIO) ---
    var eUser = crearElementoRobusto(pkg, "Usuario", "Entity", "entity");
    var eRol = crearElementoRobusto(pkg, "Rol", "Entity", "entity");
    var eTenant = crearElementoRobusto(pkg, "Empresa / Tenant", "Entity", "entity");
    var ePlan = crearElementoRobusto(pkg, "Plan Suscripcion", "Entity", "entity");
    var ePermiso = crearElementoRobusto(pkg, "Empresa Rol Permiso", "Entity", "entity");
    var eBitacora = crearElementoRobusto(pkg, "Bitacora", "Entity", "entity");

    // =================================================================
    // 2. DISPOSICIÓN ESPACIAL EN EL DIAGRAMA (COORDINATES EA)
    // =================================================================

    // Columna 1: Actor
    colocarElemento(diagram, actAdmin, 50, 160, -280, -390);

    // Columna 2: Vistas (Boundaries)
    colocarElemento(diagram, bUserDetail, 280, 440, -80,  -150);
    colocarElemento(diagram, bUserList,   280, 440, -200, -270);
    colocarElemento(diagram, bUserModal,  280, 440, -320, -390);
    colocarElemento(diagram, bRoleList,   280, 440, -440, -510);
    colocarElemento(diagram, bRolePerms,  280, 440, -560, -630);

    // Columna 3: Controladores (Controls)
    colocarElemento(diagram, cUser,      560, 710, -200, -280);
    colocarElemento(diagram, cRole,      560, 710, -480, -560);
    colocarElemento(diagram, cBcrypt,    810, 950, -90,  -160);
    colocarElemento(diagram, cPlan,      810, 950, -240, -320);
    colocarElemento(diagram, cBitacora,  810, 950, -410, -480);

    // Columna 4: Entidades (Entities)
    colocarElemento(diagram, eUser,      1060, 1200, -50,  -120);
    colocarElemento(diagram, eTenant,    1060, 1200, -170, -240);
    colocarElemento(diagram, ePlan,      1060, 1200, -290, -360);
    colocarElemento(diagram, ePermiso,   1060, 1200, -410, -480);
    colocarElemento(diagram, eRol,       1060, 1200, -520, -590);
    colocarElemento(diagram, eBitacora,  1060, 1200, -640, -710);

    // Nota informativa de arquitectura
    var nota = crearElemento(pkg, "Nota_Arquitectura_CU02", "Note");
    nota.Notes = "DIAGRAMA DE ROBUSTEZ Y COMUNICACIÓN (CU02):\n" +
                 "- Múltiples Vistas (Boundaries) y Controladores (Controls).\n" +
                 "- Flujo 1 (1-8): Listado y filtrado de usuarios por Tenant.\n" +
                 "- Flujo 2 (9-21): Creación de colaboradores con validación de cuota según PlanSuscripcion y hash Bcrypt.\n" +
                 "- Flujo 3 (22-28): Cambio de estado (activar/suspender) y reasignación de Rol.\n" +
                 "- Flujo 4 (29-37): Administración de catálogo de Roles y matriz de Permisos.\n" +
                 "- Auditoría transversal en Bitacora.";
    nota.Update();
    colocarElemento(diagram, nota, 50, 440, -670, -780);

    // =================================================================
    // 3. CONECTORES Y MENSAJES NUMERADOS (COMUNICACIÓN ROBUSTEZ)
    // =================================================================

    // --- ACTOR A VISTAS ---
    crearAsociacionMensaje(actAdmin, bUserList, "1: Consultar Usuarios(search, rol, activo) >\n8: Mostrar Tabla de Usuarios() <", "Bi-Directional");
    crearAsociacionMensaje(actAdmin, bUserModal, "9: Registrar Nuevo Usuario(form) >", "Source -> Destination");
    crearAsociacionMensaje(actAdmin, bUserDetail, "22: Cambiar Estado / Asignar Rol() >", "Source -> Destination");
    crearAsociacionMensaje(actAdmin, bRoleList, "29: Consultar Catalogo de Roles() >", "Source -> Destination");
    crearAsociacionMensaje(actAdmin, bRolePerms, "33: Configurar Permisos por Rol() >", "Source -> Destination");

    // --- VISTAS A CONTROLADORES ---
    crearAsociacionMensaje(bUserList, cUser, "2: listar_usuarios(tenant_id, filtros) >\n7: ListaUsuariosResponse(items) <", "Bi-Directional");
    crearAsociacionMensaje(bUserModal, cUser, "10: crear_usuario(payload) >\n20: UsuarioCreado(id, email) <", "Bi-Directional");
    crearAsociacionMensaje(bUserModal, bUserList, "21: Actualizar Tabla() >", "Source -> Destination");
    crearAsociacionMensaje(bUserDetail, cUser, "23: cambiar_estado(activo) / asignar_rol(rol_id) >\n28: EstadoActualizado() <", "Bi-Directional");
    crearAsociacionMensaje(bRoleList, cRole, "30: listar_roles() >\n32: Retornar Roles() <", "Bi-Directional");
    crearAsociacionMensaje(bRolePerms, cRole, "34: obtener_permisos_rol(rol_id) >\n37: PermisosActualizados() <", "Bi-Directional");

    // --- CONTROLADOR DE USUARIOS A ENTIDADES Y TENANT ---
    crearAsociacionMensaje(cUser, eTenant, "3: Validar Tenant Activo() >", "Source -> Destination");
    crearAsociacionMensaje(cUser, eUser, "4: Buscar Usuarios Filtrados() >\n5: Retornar Lista Usuarios() <\n17: Guardar Nuevo UsuarioModel() >\n24: Validar No Autosuspendido() >\n26: Actualizar Estado / Rol() >", "Bi-Directional");
    crearAsociacionMensaje(cUser, eRol, "6: Cargar Nombres de Rol() >\n25: Validar Existencia Rol() >", "Source -> Destination");

    // --- ORQUESTACIÓN CON VALIDADOR DE PLAN DE SUSCRIPCIÓN ---
    crearAsociacionMensaje(cUser, cPlan, "11: validar_cuota_colaboradores(tenant_id) >\n14: CuotaPermitida(bool) <", "Bi-Directional");
    crearAsociacionMensaje(cPlan, ePlan, "12: Consultar LimiteUsuarios del Plan() >", "Source -> Destination");
    crearAsociacionMensaje(cPlan, eUser, "13: Contar Colaboradores Activos() >", "Source -> Destination");

    // --- ORQUESTACIÓN CON CRIPTOGRAFÍA BCRYPT ---
    crearAsociacionMensaje(cUser, cBcrypt, "15: get_password_hash(pass) >\n16: Retornar PasswordHash <", "Bi-Directional");

    // --- CONTROLADOR DE ROLES Y PERMISOS CON ENTIDADES ---
    crearAsociacionMensaje(cRole, eRol, "31: Consultar / Guardar Rol() >", "Source -> Destination");
    crearAsociacionMensaje(cRole, ePermiso, "35: Consultar / Actualizar Permisos() >", "Source -> Destination");

    // --- AUDITORÍA TRANSVERSAL EN BITÁCORA ---
    crearAsociacionMensaje(cUser, cBitacora, "18: log_bitacora(CREAR) >\n27: log_bitacora(CAMBIO_ESTADO/ROL) >", "Source -> Destination");
    crearAsociacionMensaje(cRole, cBitacora, "36: log_bitacora(EDITAR_PERMISOS) >", "Source -> Destination");
    crearAsociacionMensaje(cBitacora, eBitacora, "19: Guardar Log Auditoria() >", "Source -> Destination");

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
