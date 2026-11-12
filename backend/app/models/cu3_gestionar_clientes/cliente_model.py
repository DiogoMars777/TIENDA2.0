# ==============================================================================
# CU3 - GESTIONAR CLIENTES -> CAPA MODELO
# Ubicacion: backend/app/models/cu3_gestionar_clientes/cliente_model.py
# ==============================================================================

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Date, event, select, insert
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.timezone import get_bolivia_now
from app.models.cu1_gestionar_autenticacion.usuario_rol_model import Usuario, Rol, UsuarioModel, RolModel


class Cliente(Base):
    __tablename__ = "cliente"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, default=1)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=True)
    email = Column(String(150), nullable=True)
    telefono = Column(String(20), nullable=True)
    fechanac = Column(Date, nullable=True)
    genero = Column(String(30), nullable=True)
    activo = Column(Boolean, default=True)
    fecharegistro = Column(DateTime, default=get_bolivia_now)
    usuarioid = Column(Integer, ForeignKey("usuario.id", ondelete="CASCADE"), nullable=True)

    usuario = relationship("Usuario")


# ==============================================================================
# ALIASES DE COMPATIBILIDAD (DIAGRAMAS Y CODIGO EXISTENTE)
# ==============================================================================
ClienteModel = Cliente
cliente = Cliente


@event.listens_for(Usuario, "after_insert")
def _crear_perfil_cliente(mapper, connection, target):
    """
    CU3: cada vez que se crea un usuario con rol "Cliente" -ya sea por
    auto-registro (CU1 - auth_controller.registrar_usuario) o alta desde el
    panel admin (CU3 - cliente_service.create)- se crea automáticamente su
    fila en la tabla `cliente` (perfil extendido: fechanac, genero). El
    cliente completa esos campos faltantes despues via PUT /clientes/me.
    """
    rol_nombre = connection.execute(
        select(Rol.nombre).where(Rol.id == target.rolid)
    ).scalar()

    if not rol_nombre or rol_nombre.strip().lower() != "cliente":
        return

    ya_existe = connection.execute(
        select(Cliente.id).where(Cliente.usuarioid == target.id)
    ).first()
    if ya_existe:
        return

    connection.execute(
        insert(Cliente).values(
            tenant_id=getattr(target, "tenant_id", 1),
            nombre=target.nombre,
            apellido=target.apellido,
            email=target.email,
            telefono=target.telefono,
            usuarioid=target.id,
            activo=True,
        )
    )
