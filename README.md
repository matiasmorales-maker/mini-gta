# GTA Mini

**GTA Mini** es un juego en Python con Pygame inspirado en la saga Grand Theft Auto.  
Permite conducir vehículos, robar autos, disparar armas, y enfrentarse a policías en un mapa grande.

---

## 📌 Características

- Mapa grande con cámara dinámica.
- Jugador caminando o conduciendo vehículos.
- Vehículos robables y conducibles.
- Policía que persigue al jugador.
- Misiones básicas (robar autos y entregarlos).
- Armas: pistola y escopeta con munición limitada.
- Sistema de disparo y cooldown.
- HUD con salud y mensajes.
- Guardar y cargar partida (`K` y `L`).
- Mensajes en pantalla para misiones y acciones.

---

## 🛠️ Requisitos

- Python 3.10+  
- [Pygame](https://www.pygame.org/news)  

Instala Pygame con:

```bash
pip install pygame
 Cómo jugar

Clona o descarga el repositorio.

Ejecuta el juego:

python "gta mini.py"


Controles:

Tecla	Acción
W/A/S/D o flechas	Mover jugador
Mouse	Apuntar
Click izquierdo	Disparar
1/2	Cambiar arma
E	Entrar/salir de vehículo
M	Mostrar/ocultar minimapa
Q	Iniciar misión de robar auto
K	Guardar partida
L	Cargar partida
ESC	Salir del juego
 Guardar y cargar

Guardar: presiona K

Cargar: presiona L
Se guarda un archivo savegame.json con la posición del jugador, salud y dinero.

 Estructura del proyecto
gta-mini/
│
├─ gta mini.py        # Código principal del juego
├─ assets/            # Carpeta para sonidos, imágenes u otros assets
└─ savegame.json      # Archivo generado al guardar partida

 Mejoras futuras

IA policial avanzada con patrullas.

Nuevas armas y munición.

Vehículos adicionales y mejoras en físicas.

Misiones más complejas estilo GTA moderno.

 Licencia

Este proyecto es libre para uso educativo y personal. No comercializar sin permiso del autor.
