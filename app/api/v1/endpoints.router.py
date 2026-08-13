from app.services.notification_service import notification_service

# --- Ejemplo de Notificación al finalizar una Copia por Aplicación ---
async def execute_app_backup_task(app_name: str):
    try:
        # 1. Tu lógica de backup existente aquí...
        # ...
        
        # 2. Notificación de Éxito
        await notification_service.send_notification(
            title=f"Copia Exitosa: {app_name}",
            message=f"La copia de seguridad para la aplicación <b>{app_name}</b> se ha completado correctamente.",
            status="success"
        )
    except Exception as e:
        # 3. Notificación de Error
        await notification_service.send_notification(
            title=f"Error en Copia: {app_name}",
            message=f"Ocurrió un fallo al respaldar <b>{app_name}</b>:\n<code>{str(e)}</code>",
            status="error"
        )

# --- Ejemplo de Notificación al finalizar Disaster Recovery ---
async def execute_full_backup_task():
    try:
        # 1. Tu lógica de backup completo existente aquí...
        # ...

        # 2. Notificación de Éxito
        await notification_service.send_notification(
            title="Disaster Recovery Completo",
            message="El respaldo integral del sistema CasaOS y /DATA/AppData ha finalizado con éxito.",
            status="success"
        )
    except Exception as e:
        # 3. Notificación de Error
        await notification_service.send_notification(
            title="Error en Disaster Recovery",
            message=f"Falló la copia completa del sistema:\n<code>{str(e)}</code>",
            status="error"
        )