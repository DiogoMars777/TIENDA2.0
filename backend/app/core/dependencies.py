from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_token, oauth2_scheme
from app.models.models import UsuarioModel

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    email = verify_token(token)
    if email is None:
        raise credentials_exception
    user = db.query(UsuarioModel).filter(UsuarioModel.email == email.strip().lower()).first()
    if user is None:
        user = db.query(UsuarioModel).filter(UsuarioModel.email == email).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: UsuarioModel = Depends(get_current_user)):
    if not current_user.activo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo")
    return current_user

def require_roles(*allowed_roles: str):
    """Verifica que el usuario activo tenga al menos uno de los roles autorizados"""
    def role_checker(
        current_user: UsuarioModel = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> UsuarioModel:
        # Rol ID 1 es siempre el Administrador principal del sistema
        if current_user.rolid == 1:
            return current_user

        rol_nombre = None
        if current_user.rol:
            rol_nombre = current_user.rol.nombre
        elif current_user.rolid:
            from app.models.models import RolModel
            rol_obj = db.query(RolModel).filter(RolModel.id == current_user.rolid).first()
            if rol_obj:
                rol_nombre = rol_obj.nombre
        
        normalized_allowed = [r.strip().upper() for r in allowed_roles]
        if not rol_nombre or rol_nombre.strip().upper() not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: se requieren permisos administrativos para esta operación"
            )
        return current_user
    return role_checker

obtener_usuario_actual = get_current_user
obtener_usuario_activo = get_current_active_user

def obtener_tenant_actual(
    current_user: UsuarioModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtiene y valida el Tenant asignado al usuario activo actual"""
    from app.models.models import TenantModel
    tenant_id = getattr(current_user, 'tenant_id', 1) or 1
    tenant = db.query(TenantModel).filter(TenantModel.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La organización o tenant asignada no existe"
        )
    if not tenant.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La organización o tenant se encuentra suspendida o inactiva"
        )
    return tenant

get_current_tenant = obtener_tenant_actual
get_current_tenant_user = get_current_active_user

require_admin = require_roles("Superadmin", "SUPERADMIN", "Super Administrador", "Administrador", "Admin", "Supervisor", "Gerente")
require_staff = require_roles("Superadmin", "SUPERADMIN", "Super Administrador", "Administrador", "Supervisor", "Cajero", "Admin", "Gerente")



