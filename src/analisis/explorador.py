"""Data Understanding sobre el corpus estructurado.

TODO(alumno): las visualizaciones no son decoración; deben revelar
cobertura, sesgos y problemas de calidad (nulos, JSON inválidos, nombres
inconsistentes).
"""

from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

from src.excepciones import EtapaPendienteAlumno

class ExploradorDatos:
    """Estadísticas y gráficos mínimos del laboratorio."""

    def __init__(self, ruta_json: str = "data/json", directorio_salida: str = "data/graficos"):
        self.ruta_json = Path(ruta_json)
        self.directorio_salida = Path(directorio_salida)
        self.directorio_salida.mkdir(parents=True, exist_ok=True)
        
        # Cargar todos los JSONs en una lista de diccionarios
        self.noticias = []
        for archivo in self.ruta_json.glob("*.json"):
            with open(archivo, "r", encoding="utf-8") as f:
                self.noticias.append(json.load(f))
                
        self.df = pd.DataFrame(self.noticias)

    def noticias_por_fuente(self) -> None:
        if "fuente" not in self.df.columns or self.df.empty:
            return
        
        conteo = self.df["fuente"].value_counts()
        plt.figure(figsize=(10, 6))
        conteo.plot(kind="bar", color="steelblue")
        plt.title("Cantidad de Noticias por Fuente")
        plt.xlabel("Fuente")
        plt.ylabel("Cantidad")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(self.directorio_salida / "noticias_por_fuente.png")
        plt.close()

    def delitos_frecuentes(self) -> None:
        if "delitos" not in self.df.columns or self.df.empty:
            return
            
        # Aplanar la lista de delitos
        todos_los_delitos = [delito for sublist in self.df["delitos"].dropna() for delito in sublist]
        if not todos_los_delitos:
            return
            
        serie_delitos = pd.Series(todos_los_delitos).value_counts().head(10)
        
        plt.figure(figsize=(10, 6))
        serie_delitos.sort_values().plot(kind="barh", color="indianred")
        plt.title("Top 10 Delitos Más Frecuentes")
        plt.xlabel("Frecuencia")
        plt.ylabel("Delito")
        plt.tight_layout()
        plt.savefig(self.directorio_salida / "delitos_frecuentes.png")
        plt.close()

    def lugares_frecuentes(self) -> None:
        if "lugares" not in self.df.columns or self.df.empty:
            return
            
        todos_los_lugares = [lugar for sublist in self.df["lugares"].dropna() for lugar in sublist]
        if not todos_los_lugares:
            return
            
        serie_lugares = pd.Series(todos_los_lugares).value_counts().head(10)
        
        plt.figure(figsize=(10, 6))
        serie_lugares.sort_values().plot(kind="barh", color="mediumseagreen")
        plt.title("Top 10 Lugares con Mayor Mención")
        plt.xlabel("Frecuencia")
        plt.ylabel("Lugar")
        plt.tight_layout()
        plt.savefig(self.directorio_salida / "lugares_frecuentes.png")
        plt.close()

    def campos_faltantes(self) -> None:
        campos_revisar = ["delitos", "personas", "organizaciones", "lugares", "objetos", "relaciones"]
        faltantes = {}
        
        if self.df.empty:
            return
            
        for campo in campos_revisar:
            if campo in self.df.columns:
                # Contamos como nulo si es None o si es una lista vacía
                nulos = self.df[campo].apply(lambda x: x is None or (isinstance(x, list) and len(x) == 0)).sum()
                faltantes[campo] = (nulos / len(self.df)) * 100
                
        serie_faltantes = pd.Series(faltantes)
        
        plt.figure(figsize=(10, 6))
        serie_faltantes.plot(kind="bar", color="coral")
        plt.title("Porcentaje de Campos Faltantes o Vacíos por Entidad (%)")
        plt.xlabel("Campo del JSON")
        plt.ylabel("Porcentaje Faltante (%)")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(self.directorio_salida / "campos_faltantes.png")
        plt.close()

    def evolucion_temporal(self) -> None:
        if "fecha_publicacion" not in self.df.columns or self.df.empty:
            return
            
        df_temporal = self.df.copy()
        df_temporal["fecha_publicacion"] = pd.to_datetime(df_temporal["fecha_publicacion"], errors='coerce')
        df_temporal = df_temporal.dropna(subset=["fecha_publicacion"])
        
        if df_temporal.empty:
            return
            
        conteo_mensual = df_temporal.groupby(df_temporal["fecha_publicacion"].dt.to_period("M")).size()
        
        plt.figure(figsize=(10, 6))
        conteo_mensual.plot(kind="line", marker="o", color="royalblue")
        plt.title("Evolución Temporal de Noticias Publicadas")
        plt.xlabel("Mes")
        plt.ylabel("Cantidad de Noticias")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(self.directorio_salida / "evolucion_temporal.png")
        plt.close()

    def ejecutar(self) -> None:
        """Corre todas las visualizaciones pedidas en la guía."""
        if self.df.empty:
            print("No se encontraron archivos JSON para analizar.")
            return
            
        self.noticias_por_fuente()
        self.delitos_frecuentes()
        self.lugares_frecuentes()
        self.campos_faltantes()
        self.evolucion_temporal()
        print("Análisis completado. Los gráficos se han guardado en la carpeta data/graficos.")