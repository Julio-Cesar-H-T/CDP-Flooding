[README.md](https://github.com/user-attachments/files/28656524/README.md)
# 📡 CDP Flooding — Ataque DoS mediante el Protocolo CDP

## 🎯 Objetivo del Laboratorio

Demostrar cómo un atacante puede saturar la tabla de vecinos CDP (*Cisco Discovery Protocol*) de un switch Cisco, provocando un consumo excesivo de CPU y memoria que degrada o interrumpe el funcionamiento normal del dispositivo.

Link a la lista de reproducción: https://www.youtube.com/playlist?list=PL1bMSHFyMPr7W7DrFd-INmRRQDjGquFIV
---

## 📋 Objetivo del Script

El script `CDP_DoS.py` genera y envía de forma masiva anuncios CDP falsos con MACs, IPs y nombres de dispositivo aleatorios hacia el switch víctima. Cada anuncio provoca que el switch registre un nuevo "vecino" en su tabla CDP, agotando sus recursos.

### Parámetros usados

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `INTERFACE` | `ens4` | Interfaz física conectada al trunk del switch |
| `PAQUETES` | `1500` | Número de anuncios CDP falsos a inyectar |
| `INTERVALO` | `0.005 s` | Tiempo entre envíos (~200 pkt/s) |

### Requisitos para utilizar la herramienta

```bash
# Sistema operativo
Kali Linux (KVM en PNETLab)

# Dependencias
pip install scapy

# Permisos
sudo python3 CDP_DoS.py   # Requiere root para abrir socket L2
```

---

## 🔧 Documentación del Funcionamiento del Script

### Flujo de ejecución

```
1. Se abre un socket L2 persistente sobre ens4
2. Por cada iteración se genera:
     - MAC origen aleatoria con OUI Cisco (00:00:0C:xx:xx:xx)
     - Nombre de dispositivo aleatorio (ROUTER-XXXXXX)
     - IP falsa en rango 10.x.x.x
3. Se construyen los TLVs CDP manualmente:
     TLV 0x0001 → Device-ID
     TLV 0x0002 → Addresses (IPv4)
     TLV 0x0003 → Port-ID
     TLV 0x0004 → Capabilities
     TLV 0x0005 → Software Version
     TLV 0x0006 → Platform
4. Se calcula el checksum real del frame CDP
5. El frame se encapsula en LLC/SNAP y se envía al
   multicast CDP: 01:00:0C:CC:CC:CC
```

### Estructura del frame CDP

```
[ Ethernet Header ]
  DA: 01:00:0C:CC:CC:CC  (Multicast CDP)
  SA: <MAC aleatoria Cisco>

[ LLC ]
  DSAP: 0xAA | SSAP: 0xAA | Ctrl: 0x03

[ SNAP ]
  OUI: 00:00:0C | Protocol: 0x2000 (CDP)

[ CDP Header ]
  Versión: 2 | TTL: 180s | Checksum: <calculado>

[ TLVs CDP ]
  Device-ID | Addresses | Port-ID | Capabilities | ...
```

### Impacto esperado

- La tabla CDP del switch crece hasta su límite máximo.
- El proceso CDP en el switch consume CPU de forma anormal.
- Los vecinos CDP legítimos pueden quedar desplazados.

---

## 🗺️ Documentación de la Red

### Topología

```
        [ R1 — IOU L3 ]
        192.168.10.254 (VLAN 10)
        192.168.20.254 (VLAN 20)
               |
           e0/0 (trunk)
               |
        [ SW-1 — IOL L2 ]  ←── STP Root (prioridad 4096)
         e0/1       e0/2       e0/3
          |           |           |
       [SW-3]       [SW-2]   [Atacante]
       VLAN 10      VLAN 20   ens4 → ens4 (access VLAN 10)
       VPC-1,4      VPC-2,3
```

### Interfaces y VLANs

| Dispositivo | Interfaz | Modo | VLAN / IP |
|-------------|----------|------|-----------|
| R1 | E0/0.10 | subinterfaz | 192.168.10.254/24 |
| R1 | E0/0.20 | subinterfaz | 192.168.20.254/24 |
| SW-1 | E0/0 | trunk | VLANs 1,10,20,99 |
| SW-1 | E0/1 | trunk | VLANs 1,10,20,99 |
| SW-1 | E0/2 | trunk | VLANs 1,20,99 |
| SW-1 | E0/3 | **access VLAN 10** | Atacante |
| SW-2 | E0/0-1 | access | VLAN 20 (VPC-2,3) |
| SW-3 | E0/0,2 | access | VLAN 10 (VPC-4,1) |
| Atacante | ens4 | access (VLAN 10) | 192.168.10.50/24 |

### Direccionamiento IP

| Dispositivo | IP | VLAN |
|-------------|-----|------|
| R1 GW VLAN 10 | 192.168.10.254 | 10 |
| R1 GW VLAN 20 | 192.168.20.254 | 20 |
| SW-1 SVI | 192.168.99.1 | 99 |
| Kali (atacante) | 192.168.10.50 | 10 |
| VPC-1, VPC-4 | DHCP 192.168.10.100+ | 10 |
| VPC-2, VPC-3 | DHCP 192.168.20.100+ | 20 |

---

## 🛡️ Contra-medidas

### Deshabilitar CDP globalmente

```
SW-1(config)# no cdp run
```

### Deshabilitar CDP por puerto (recomendado en puertos de acceso)

```
SW-1(config)# interface Ethernet0/3
SW-1(config-if)# no cdp enable
```

### Limitar la tasa de procesamiento CDP

```
SW-1(config)# cdp timer 60
SW-1(config)# cdp holdtime 180
```

### Verificación post-mitigación

```
SW-1# show cdp
SW-1# show cdp neighbors
SW-1# show cdp interface Ethernet0/3
```

> **Nota:** En entornos de producción, CDP debe deshabilitarse en todos los puertos orientados a usuarios finales. Solo debería estar activo en enlaces entre dispositivos de infraestructura Cisco.
