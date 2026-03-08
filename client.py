import platform
import socket
import psutil
import requests
import time
import os
import sys
import json
import winreg

# --- CONFIGURACIÓN ---
# URL donde se aloja el servidor en PythonAnywhere
SERVER_URL = "https://omarbk.pythonanywhere.com/api/report"
# ---------------------

def get_size(bytes, suffix="B"):
    """Convierte bytes a un formato legible (KB, MB, GB, etc.)"""
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f} {unit}{suffix}"
        bytes /= factor
    return f"{bytes:.2f} {unit}{suffix}"

def get_system_info():
    """Captura la información de Hardware y Sistema Operativo del equipo."""
    
    # 1. Sistema Operativo
    os_system = platform.system()
    os_release = platform.release()
    os_version = platform.version()

    # 2. Hostname
    hostname = socket.gethostname()

    # 3. Memoria RAM
    svmem = psutil.virtual_memory()
    ram_total = get_size(svmem.total)

    # 4. Discos
    partitions = psutil.disk_partitions()
    disk_info = []
    for partition in partitions:
        if 'cdrom' in partition.opts or partition.fstype == '':
            continue
        try:
            partition_usage = psutil.disk_usage(partition.mountpoint)
            disk_info.append(f"{partition.device} ({get_size(partition_usage.total)})")
        except PermissionError:
            continue

    # 5. CPU
    cpu_info = platform.processor() or "Desconocido"

    # 6. Dirección IP (Local)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
    except Exception:
        ip_address = "Desconocida"

    return {
        "computer_name": hostname,
        "ip_address": ip_address,
        "os_version": f"{os_system} {os_release} (Build: {os_version})",
        "cpu": cpu_info,
        "ram": ram_total,
        "disk": " | ".join(disk_info)
    }

def add_to_startup():
    """Registra el ejecutable en el Registro de Windows para que inicie con el sistema."""
    key_name = "AssetManagerClient"
    
    if getattr(sys, 'frozen', False):
        file_path = sys.executable
    else:
        file_path = os.path.abspath(sys.argv[0])

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, key_name, 0, winreg.REG_SZ, f'"{file_path}"')
        winreg.CloseKey(key)
        # print(f"[INFO] Persistencia configurada: {file_path}")
    except Exception:
        pass

def has_info_changed(current_info):
    """Compara la información actual con la guardada localmente para detectar cambios."""
    cache_file = os.path.join(os.path.expanduser("~"), ".asset_manager_cache.json")
    
    if not os.path.exists(cache_file):
        return True
    
    try:
        with open(cache_file, "r") as f:
            last_info = json.load(f)
        
        # Ignoramos la IP para la comparación de "cambios reales" si se desea, 
        # pero para ser exactos comparamos todo. 
        # Si el usuario quiere que solo se mande una vez "la info del equipo", 
        # los componentes de hardware casi nunca cambian.
        return current_info != last_info
    except:
        return True

def save_info_cache(info):
    """Guarda la información actual en un archivo de cache local."""
    cache_file = os.path.join(os.path.expanduser("~"), ".asset_manager_cache.json")
    try:
        with open(cache_file, "w") as f:
            json.dump(info, f)
    except:
        pass

def report_info():
    """Envía la información capturada al servidor web si ha habido cambios."""
    info = get_system_info()
    
    if not has_info_changed(info):
        return False

    try:
        response = requests.post(SERVER_URL, json=info, timeout=10)
        if response.status_code == 200:
            save_info_cache(info)
            return True
    except:
        pass
    return False

if __name__ == "__main__":
    # 1. Registrar en el inicio (persistencia)
    add_to_startup()
    
    # 2. Reporte Inmediato al iniciar
    report_info()
    
    # 3. Bucle de monitoreo discreto
    while True:
        # Esperar 60 segundos antes de la próxima comprobación de cambios
        # (Suficiente para detectar cambios de hardware/red sin saturar)
        time.sleep(60)
        report_info()
