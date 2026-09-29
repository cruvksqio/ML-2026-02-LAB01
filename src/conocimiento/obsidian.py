"""Persistencia final: red de notas Markdown para Obsidian.

No se usa SQLite, MongoDB ni Neo4j. Cada noticia y cada entidad debe
tener su propia nota, enlazada con [[wiki-links]].
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path

from src.config import DIR_VAULT
from src.conocimiento.utilidades import slugify  # Asumo que esta función ya está implementada
from src.excepciones import EtapaPendienteAlumno

class EscritorObsidian(ABC):
    @abstractmethod
    def escribir_noticia(self, data: dict) -> Path: ...
    @abstractmethod
    def escribir_entidades(self, noticias: list[dict]) -> None: ...
    @abstractmethod
    def escribir_indice(self, noticias: list[dict]) -> Path: ...
    @abstractmethod
    def escribir_vault(self, noticias: list[dict]) -> None: ...

class EscritorVaultObsidian(EscritorObsidian):
    """Implementación objetivo del laboratorio."""

    def __init__(self, vault: Path = DIR_VAULT) -> None:
        self.vault = vault
        self.carpetas = ["Noticias", "Delitos", "Personas", "Organizaciones", "Lugares", "Objetos", "Relaciones"]

    def _crear_carpetas(self):
        self.vault.mkdir(parents=True, exist_ok=True)
        for carpeta in self.carpetas:
            (self.vault / carpeta).mkdir(exist_ok=True)

    def escribir_noticia(self, data: dict) -> Path:
        id_noticia = data.get("id_noticia", "sin_id")
        ruta_archivo = self.vault / "Noticias" / f"{id_noticia}.md"
        
        contenido = [
            "---",
            f"id: {id_noticia}",
            f"fecha_publicacion: {data.get('fecha_publicacion', '')}",
            f"fuente: {data.get('fuente', '')}",
            f"url: {data.get('url', '')}",
            "---",
            f"# {data.get('titulo', 'Sin título')}\n",
            "## Resumen",
            f"{data.get('resumen', 'Sin resumen')}\n",
        ]
        
        # Delitos
        contenido.append("## Delitos")
        for delito in data.get("delitos", []):
            contenido.append(f"- [[{delito}]]")
        
        # Personas
        contenido.append("\n## Personas")
        for persona in data.get("personas", []):
            nombre = persona.get("nombre")
            if nombre:
                rol = persona.get("rol", "desconocido")
                contenido.append(f"- [[{nombre}]] ({rol})")
        
        # Organizaciones
        contenido.append("\n## Organizaciones")
        for org in data.get("organizaciones", []):
            contenido.append(f"- [[{org}]]")
            
        # Lugares
        contenido.append("\n## Lugares")
        for lugar in data.get("lugares", []):
            contenido.append(f"- [[{lugar}]]")
            
        # Objetos (Generalmente no se enlazan como entidades complejas, pero se listan)
        contenido.append("\n## Objetos")
        for obj in data.get("objetos", []):
            nombre = obj.get("nombre", "objeto")
            tipo = obj.get("tipo", "desconocido")
            contenido.append(f"- {nombre} ({tipo})")
            
        # Relaciones
        contenido.append("\n## Relaciones")
        for rel in data.get("relaciones", []):
            origen = rel.get("origen")
            destino = rel.get("destino")
            tipo = rel.get("tipo")
            if origen and destino:
                contenido.append(f"- [[{origen}]] -- {tipo} --> [[{destino}]]")
                
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            f.write("\n".join(contenido))
            
        return ruta_archivo

    def escribir_entidades(self, noticias: list[dict]) -> None:
        # Agrupar por entidad
        indices = {
            "Delitos": defaultdict(list),
            "Personas": defaultdict(list),
            "Organizaciones": defaultdict(list),
            "Lugares": defaultdict(list)
        }
        
        for data in noticias:
            id_noticia = data.get("id_noticia")
            
            for delito in data.get("delitos", []):
                indices["Delitos"][delito].append(id_noticia)
                
            for persona in data.get("personas", []):
                nombre = persona.get("nombre")
                if nombre:
                    indices["Personas"][nombre].append(id_noticia)
                    
            for org in data.get("organizaciones", []):
                indices["Organizaciones"][org].append(id_noticia)
                
            for lugar in data.get("lugares", []):
                indices["Lugares"][lugar].append(id_noticia)

        # Generar archivos
        for tipo_entidad, diccionario in indices.items():
            for nombre_entidad, ids in diccionario.items():
                nombre_archivo = f"{slugify(nombre_entidad)}.md"
                ruta = self.vault / tipo_entidad / nombre_archivo
                
                contenido = [
                    f"# {nombre_entidad}",
                    f"Tipo: {tipo_entidad[:-1]}",
                    "\n## Noticias relacionadas"
                ]
                for nid in set(ids):
                    contenido.append(f"- [[{nid}]]")
                    
                with open(ruta, "w", encoding="utf-8") as f:
                    f.write("\n".join(contenido))

    def escribir_indice(self, noticias: list[dict]) -> Path:
        ruta_indice = self.vault / "00_Indice.md"
        contenido = ["# Índice de Bóveda\n", "## Noticias Procesadas"]
        
        for data in noticias:
            id_noticia = data.get("id_noticia", "Desconocido")
            titulo = data.get("titulo", "Sin título")
            contenido.append(f"- [[{id_noticia}]] - {titulo}")
            
        with open(ruta_indice, "w", encoding="utf-8") as f:
            f.write("\n".join(contenido))
            
        return ruta_indice

    def escribir_vault(self, noticias: list[dict]) -> None:
        self._crear_carpetas()
        for noticia in noticias:
            self.escribir_noticia(noticia)
        self.escribir_entidades(noticias)
        self.escribir_indice(noticias)