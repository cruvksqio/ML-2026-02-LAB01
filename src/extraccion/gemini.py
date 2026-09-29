"""Extractor Gemini: texto limpio → JSON del contrato del laboratorio."""

from __future__ import annotations

import json
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path

from src.config import DIR_JSON, GEMINI_API_KEY, GEMINI_MODEL, PAUSA_ENTRE_REQUESTS
from src.modelos import NoticiaFuente


class ExtractorLLM(ABC):
    """Interfaz de cualquier extractor basado en modelo generativo."""

    @abstractmethod
    def construir_prompt(self, noticia: NoticiaFuente) -> str:
        """Arma el prompt con el esquema JSON y el texto de la noticia."""

    @abstractmethod
    def extraer(self, noticia: NoticiaFuente) -> dict:
        """Devuelve un diccionario que cumple el contrato JSON del laboratorio."""


class ExtractorGemini(ExtractorLLM):
    """Extractor oficial del laboratorio (Gemini)."""

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

    def __init__(self, dir_json: Path = DIR_JSON) -> None:
        self.dir_json = dir_json
        self.dir_json.mkdir(parents=True, exist_ok=True)
        self._cliente = None

    def construir_prompt(self, noticia: NoticiaFuente) -> str:
        campos = ", ".join(self.CAMPOS_OBLIGATORIOS)
        texto = (noticia.texto_limpio or "").strip()
        return (
            "Analiza la siguiente noticia delictual.\n\n"
            "Extrae solamente informacion explicita. No inventes datos, "
            "entidades, roles ni relaciones.\n"
            "Devuelve exclusivamente JSON valido, sin markdown ni explicaciones.\n\n"
            f"Campos obligatorios: {campos}.\n"
            "personas: lista de objetos con claves nombre y rol.\n"
            "objetos: lista de objetos con claves tipo, nombre, cantidad, unidad.\n"
            "relaciones: lista de objetos con claves origen, tipo, destino.\n"
            "Si un dato no aparece, usa null o una lista vacia.\n\n"
            f"id_noticia: {noticia.id_noticia}\n"
            f"fuente: {noticia.fuente}\n"
            f"url: {noticia.url}\n\n"
            "NOTICIA:\n"
            f"{texto}\n"
        )

    def extraer(self, noticia: NoticiaFuente) -> dict:
        ruta = self.dir_json / f"{noticia.id_noticia}.json"
        
        # Si ya se extrajo correctamente en una ejecución anterior, reutilizarlo
        if ruta.exists():
            print(f"    [Saltado] {noticia.id_noticia}.json ya existe.")
            return json.loads(ruta.read_text(encoding="utf-8"))

        if not GEMINI_API_KEY:
            raise RuntimeError(
                "Falta GEMINI_API_KEY. Copie .env.example a .env y complete la clave."
            )
        cliente = self._obtener_cliente()
        from google.genai import types

        # Aumentamos reintentos y tiempo de espera para superar el error 503
        max_reintentos = 5
        respuesta = None
        for intento in range(max_reintentos):
            try:
                respuesta = cliente.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=self.construir_prompt(noticia),
                    config=types.GenerateContentConfig(
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(
                            disable=True
                        ),
                        response_mime_type="application/json",
                        temperature=0,
                    ),
                )
                break
            except Exception as exc:
                es_error_temporal = any(
                    err in str(exc) for err in ["429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE"]
                )
                if es_error_temporal and intento < max_reintentos - 1:
                    tiempo_espera = (intento + 1) * 15
                    print(f"\n    [Aviso] Saturación en el servidor (503). Esperando {tiempo_espera}s...")
                    time.sleep(tiempo_espera)
                else:
                    raise exc

        bruto = (getattr(respuesta, "text", None) or "").strip()
        if not bruto:
            raise ValueError(
                f"Gemini devolvió una respuesta vacía para {noticia.id_noticia}."
            )
        data = self._parsear_json(bruto)
        data["id_noticia"] = noticia.id_noticia
        if not data.get("fuente"):
            data["fuente"] = noticia.fuente
        if not data.get("url"):
            data["url"] = noticia.url

        ruta.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        time.sleep(PAUSA_ENTRE_REQUESTS + 2)
        return data
    
    def _obtener_cliente(self):
        if self._cliente is None:
            from google import genai

            self._cliente = genai.Client(api_key=GEMINI_API_KEY)
        return self._cliente

    @staticmethod
    def _parsear_json(bruto: str) -> dict:
        texto = bruto.strip()
        cerca = re.search(r"```(?:json)?\s*(.*?)\s*```", texto, re.DOTALL)
        if cerca:
            texto = cerca.group(1)
        try:
            data = json.loads(texto)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Gemini no devolvió JSON válido: {exc}. "
                f"Respuesta: {texto[:300]!r}"
            ) from exc
        if not isinstance(data, dict):
            raise ValueError("La respuesta de Gemini no es un objeto JSON.")
        return data
    