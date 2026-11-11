# Fábrica de Sprites Automatizada

Herramienta local que procesa un lote de fotografías y genera sprites transparentes
normalizados, una spritesheet, un retrato y un archivo de configuración JSON para
un personaje de videojuego 2D.

![Licencia MIT](https://img.shields.io/badge/license-MIT-blue.svg)

## Equipo

- Juan Marcano

## Requisitos

- Probado en Windows con Python 3.14.10.
- Las instrucciones de Fedora se incluyen, pero Fedora y otras versiones de
  Python todavía no se han validado.
- Conexión a Internet en la primera ejecución para descargar el modelo de `rembg`.

## Instalación

### Windows (PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Fedora Linux

Las siguientes instrucciones están pendientes de validación en Fedora.

```bash
sudo dnf install -y python3 python3-pip
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Entrada y ejecución

Coloque una imagen por pose en `assets/raw_photos/`. Se aceptan PNG (`.png`),
JPEG (`.jpg`, `.jpeg`) y WEBP (`.webp`); se recomienda PNG para evitar artefactos
de compresión. Use fotos nítidas, bien iluminadas, de cuerpo completo, con una
sola persona visible y sin partes importantes cortadas u ocultas. Un fondo simple
y distinto del sujeto facilita la eliminación automática, aunque el resultado
puede variar según la foto.

Los nombres no son obligatorios para procesar las imágenes, pero determinan el
orden y cómo se agrupan en `animations`. Recomendamos un prefijo numérico de dos
dígitos para el orden y un nombre de acción en minúsculas:

| Nombre de archivo sugerido | Grupo en `animations` | Uso |
|---|---|---|
| `01_reposo.png` | `reposo` | Pose de referencia; se prefiere para el retrato |
| `02_caminar_01.png`, `02_caminar_02.png` | `caminar` | Cuadros de caminar |
| `03_salto.png` | `salto` | Pose de salto |
| `04_golpe_inicio.png` | `golpe` | Inicio del golpe |
| `05_golpe_activo_01.png` | `golpe` | Fase activa; recibe una hitbox estimada |
| `06_golpe_impacto_01.png` | `golpe` | Impacto; recibe una hitbox estimada |
| `07_golpe_fin.png` | `golpe` | Fin del golpe |
| `08_derrota.png` | `derrota` | Pose de derrota |

Se pueden añadir cuadros numerados, por ejemplo `02_caminar_03.png`. Los
archivos que empiezan con `golpe_activo` o `golpe_impacto` (después del prefijo
numérico opcional) reciben una hitbox aproximada; otros nombres que comienzan
con `golpe_` se agrupan en la acción `golpe`, pero no reciben esa hitbox.
Use nombres únicos aunque cambie la extensión: no se permiten dos archivos con
el mismo nombre base. Si no hay una pose agrupada como `reposo`, el retrato se
crea a partir de la primera imagen en orden alfabético.

El repositorio no incluye fotografías de personas. Agregue sus imágenes a
`assets/raw_photos/` antes de ejecutar el programa; esa carpeta se conserva vacía
en Git. Antes de compartir fotografías de personas, obtenga su consentimiento y
confirme que tiene permiso para publicarlas.

La licencia MIT de este proyecto cubre el código, no concede derechos sobre las
fotografías; consulte también las condiciones del modelo descargado por `rembg`.

Desde la raíz del proyecto:

```bash
python src/sprite_factory.py
```

También se puede especificar entrada, salida, plantilla y modelo (el comando de
una sola línea funciona en PowerShell y Bash):

```text
python src/sprite_factory.py --input assets/raw_photos --output assets/output --template template_base.json --model u2net
```

En Windows, se pueden ejecutar los mismos comandos con `python`; las barras
inclinadas de las rutas relativas también son aceptadas.

## Resultados

La carpeta `assets/output/` contiene:

- `spritesheet.png`: sprites en una cuadrícula transparente, escalados a 250 px
  de alto.
- `portrait.png`: retrato cuadrado de 256 × 256 px.
- `fighter_config.json`: plantilla de estadísticas complementada con
  animaciones, coordenadas, hurtboxes, hitboxes estimadas y pivote.

Las cajas de colisión son aproximaciones automáticas y deben revisarse antes de
usarlas como datos definitivos de juego. El procesamiento de imágenes ocurre
localmente; la primera ejecución puede descargar el modelo de segmentación.

## Documentación y licencia

La arquitectura y el flujo se describen en [docs/arquitectura.md](docs/arquitectura.md).
La licencia del proyecto es MIT; consulte [LICENSE](LICENSE).
