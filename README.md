# Agente analista del DENUE · Tampico y Ciudad Madero

- **Alumno:** COMPLETAR
- **Número de control:** COMPLETAR
- **Asignatura:** Desarrollo de Agentes Inteligentes (ACD-2504), grupo 850P-A
- **Docente:** D. C. C. Alejandro Estrada Padilla
- **Trabajo:** Proyecto · Unidad 1
- **Entrega:** 30 de septiembre de 2026

## Qué hace y por qué es un agente

COMPLETAR: un párrafo. Qué preguntas responde y qué decide el modelo. Explique qué hace el código y por qué el modelo nunca ve los datos.

## Los datos

COMPLETAR: fuente (INEGI, DENUE 05/2026), recorte, columnas principales y lo que los datos no tienen.

## Arquitectura

COMPLETAR: un diagrama en texto o Mermaid del ciclo. Incluya pregunta, modelo, herramientas, resultados, guardia, respuesta y bitácora.

## Herramientas

COMPLETAR: una tabla con las 4 herramientas: qué reciben, qué devuelven y cuándo las usa el modelo.

## Requisitos e instalación

COMPLETAR: comandos exactos, desde `git clone` hasta `pip install -r requirements.txt`.

## Variables de entorno

COMPLETAR: cada variable de `.env.example`. Deje claro que `.env` no se sube.

## Cómo usarlo

COMPLETAR: comandos exactos para lo siguiente:

- una pregunta, simulada y real;
- el lote con `--desde` y `--hasta`;
- las pruebas;
- `calcular_esperadas`;
- `evaluar`.

## Bot de Telegram

COMPLETAR:

- cómo crear el bot con @BotFather;
- dónde va el token (sólo en `.env`);
- cómo obtener su identificador y agregarlo a `TELEGRAM_USUARIOS_PERMITIDOS`;
- el comando para correr el bot, simulado y real;
- los comandos que atiende.

Incluya la captura `evidencia/telegram.png`. **Nunca escriba aquí el token.**

## Estructura del proyecto

COMPLETAR: el árbol de carpetas con una línea por archivo.

## Decisiones de diseño

COMPLETAR: de 5 a 10 renglones. Cubra estos puntos:

- los límites de turnos y herramientas;
- cómo filtra `codigo_act`;
- qué hace la guardia y por qué da una sola corrección;
- cómo evita que el modelo ejecute código.

## Resultados

COMPLETAR: cinco renglones con los números de `evaluacion/analisis.md`:

- aprobadas automáticas y manuales;
- llamadas totales;
- casos analizados.

## Límites y ética

COMPLETAR: qué no puede responder el agente. Incluya el uso de datos públicos del INEGI con cita de la fuente y que no hay datos personales.

## Declaración de uso de IA

COMPLETAR: qué herramienta usó, para qué parte y qué tuvo que corregirle.
