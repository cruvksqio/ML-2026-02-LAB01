"""Validación del JSON producido por el LLM.

El LLM no es la fuente de verdad: el código debe verificar el esquema.
"""

from __future__ import annotations

import json
from pathlib import Path


class ValidadorJSON:
    """Comprueba que cada archivo JSON cumpla el contrato de datos."""

    CAMPOS_OBLIGATORIOS = [
        "id_noticia",
        "titulo",
        "fecha_publicacion",
        "fuente",
        "url",
        "resumen",
        "delitos",
        "personas",
        "organizaciones",
        "lugares",
        "objetos",
        "relaciones",
    ]

    CAMPOS_LISTA = [
        "delitos",
        "personas",
        "organizaciones",
        "lugares",
        "objetos",
        "relaciones",
    ]

    def validar(self, ruta: str | Path) -> dict:
        """Lee, parsea y valida un JSON. Lanza ValueError si el contrato no se cumple."""
        archivo = Path(ruta)
        try:
            data = json.loads(archivo.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON inválido en {archivo}: {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError(f"{archivo} no contiene un objeto JSON.")

        # 1. Validar campos obligatorios presentes
        faltantes = [campo for campo in self.CAMPOS_OBLIGATORIOS if campo not in data]
        if faltantes:
            raise ValueError(f"{archivo}: faltan campos {faltantes}")

        # 2. Validar que las listas sean efectivamente listas
        for campo in self.CAMPOS_LISTA:
            if not isinstance(data[campo], list):
                raise ValueError(f"{archivo}: '{campo}' debe ser una lista")

        # 3. Validar estructuras de objetos internos
        for elem in data.get("personas", []):
            if isinstance(elem, dict) and ("nombre" not in elem or "rol" not in elem):
                raise ValueError(f"{archivo}: elementos en 'personas' requieren 'nombre' y 'rol'")

        for elem in data.get("relaciones", []):
            if isinstance(elem, dict) and not all(k in elem for k in ("origen", "tipo", "destino")):
                raise ValueError(f"{archivo}: elementos en 'relaciones' requieren 'origen', 'tipo' y 'destino'")

        return data
    