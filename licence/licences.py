import requests
import uuid
import json
import re
import subprocess
import os
from pathlib import Path
from datetime import datetime
import certifi
import urllib3
from app_paths import get_app_data_path

URL_API = "https://script.google.com/macros/s/AKfycbxce6gUv_mc7_tGuFAtGrQrnHwn4RqX8jlpicO5UqvF6b36FQ1f42vUovzw0LqGmeoY/exec"

def get_license_file_path():
    local_app_data = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    app_folder = Path(local_app_data) / "ReciboPro"
    licence_folder = app_folder / "licence"
    licence_folder.mkdir(parents=True, exist_ok=True)
    return licence_folder / "licenca.json"

LICENSE_FILE = get_license_file_path()
MAC_DEBUG_FILE = get_app_data_path("mac_debug.log")
LICENSE_DEBUG_FILE = get_app_data_path("licence_debug.log")

def log_mac_debug(message):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(MAC_DEBUG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass

def log_license_debug(message):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LICENSE_DEBUG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass

def get_mac():
    def normalize(mac_text):
        clean = mac_text.strip().upper().replace("-", ":")
        if re.fullmatch(r"([0-9A-F]{2}:){5}[0-9A-F]{2}", clean):
            return clean
        return None

    def valid_candidate(mac):
        return mac and mac != "00:00:00:00:00:00"

    def run_command(command):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="cp1252",
                errors="ignore",
                check=False,
                timeout=6,
            )
            return result.stdout or ""
        except Exception:
            return ""

    patterns = [
        r"[0-9A-Fa-f]{2}(?:-[0-9A-Fa-f]{2}){5}",
        r"[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}",
    ]

    command_outputs = [
        ("getmac_system32", run_command(["C:\\Windows\\System32\\getmac.exe", "/fo", "csv", "/nh"])),
        ("getmac_path", run_command(["getmac", "/fo", "csv", "/nh"])),
        ("ipconfig_all", run_command(["ipconfig", "/all"])),
        ("wmic_nic", run_command(["wmic", "nic", "where", "NetEnabled=true", "get", "MACAddress"])),
    ]

    for source, output in command_outputs:
        if not output:
            log_mac_debug(f"{source}: sem saída")
            continue

        log_mac_debug(f"{source}: saída recebida ({len(output)} chars)")
        for pattern in patterns:
            for match in re.findall(pattern, output):
                mac = normalize(match)
                if valid_candidate(mac):
                    log_mac_debug(f"MAC detectado via {source}: {mac}")
                    return mac

    fallback = uuid.getnode()
    fallback_mac = ":".join(f"{(fallback >> elements) & 0xFF:02X}" for elements in range(40, -1, -8))
    log_mac_debug(f"MAC fallback uuid.getnode(): {fallback_mac}")
    return fallback_mac

def validar_online(chave):
    mac = get_mac()
    dados = {
        "chave": chave,
        "mac": mac,
        "mac_raw": mac.replace(":", "")
    }

    attempts = [
        ("json_default", lambda: requests.post(URL_API, json=dados, timeout=12)),
        ("json_certifi", lambda: requests.post(URL_API, json=dados, timeout=12, verify=certifi.where())),
        ("form_default", lambda: requests.post(URL_API, data=dados, timeout=12)),
    ]

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    attempts.append(("json_insecure", lambda: requests.post(URL_API, json=dados, timeout=12, verify=False)))

    for attempt_name, request_fn in attempts:
        try:
            response = request_fn()
            text = (response.text or "").strip()
            log_license_debug(
                f"{attempt_name}: status={response.status_code} body={text[:220]}"
            )
            if text:
                return text
        except Exception as exc:
            log_license_debug(f"{attempt_name}: excecao={type(exc).__name__} detalhe={exc}")

    return "ERRO_CONEXAO"

def retorno_eh_ok(resultado):
    if resultado is None:
        return False

    if isinstance(resultado, dict):
        status = str(resultado.get("status", "")).strip().upper()
        return status == "OK"

    texto = str(resultado).strip().strip('"').strip("'").upper()
    return texto == "OK" or '"STATUS":"OK"' in texto or "STATUS:OK" in texto

def salvar_licenca(chave):
    with open(LICENSE_FILE, "w", encoding="utf-8") as f:
        json.dump({"chave": chave}, f)

def possui_arquivo_licenca():
    return LICENSE_FILE.exists()

def ler_chave_salva():
    if not possui_arquivo_licenca():
        return None

    with open(LICENSE_FILE, "r", encoding="utf-8") as f:
        dados = json.load(f)
    return dados.get("chave")

def verificar_licenca_salva_online():
    chave = ler_chave_salva()
    if not chave:
        return False

    resultado = validar_online(chave)
    return retorno_eh_ok(resultado)

def ativar_licenca(chave):
    resultado = validar_online(chave)
    if retorno_eh_ok(resultado):
        salvar_licenca(chave)
        return True, "Licença ativada com sucesso."

    mensagens = {
        "ERRO_CONEXAO": "Falha de conexão com o servidor de licença.",
        "CHAVE_INVALIDA": "Chave de licença inválida.",
        "MAC_INVALIDO": "Dispositivo não autorizado para esta licença.",
    }
    return False, mensagens.get(resultado, f"Falha na ativação: {resultado}")
