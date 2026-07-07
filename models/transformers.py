import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

class RegionStatsEncoder(BaseEstimator, TransformerMixin):
    """
    Transformador personalizado para calcular agregaciones regionales
    (Data Leakage prevention).
    Calcula:
        - siniestros_por_region
        - dist_media_region_km
        - pct_fatal_region
    Ajustado SOLO sobre el conjunto de entrenamiento (X_train, y_train),
    y luego mapea los valores al conjunto de test (o inferencia).
    """
    def __init__(self, region_col="region_dpa"):
        self.region_col = region_col
        self.stats_ = {}
        self.fallback_ = {}
        
    def fit(self, X, y=None):
        df = X.copy()
        if y is not None:
            df['target_gravedad'] = y
            
        # Agrupaciones básicas
        agg = df.groupby(self.region_col, observed=True).agg(
            siniestros_por_region=(self.region_col, "count"),
            dist_media_region_km=("distancia_hospital_km", "mean")
        )
        
        # Agrupación condicional (solo si hay Y)
        if y is not None:
            fatales = df['target_gravedad'] == 'Fatal'
            # Evitar error si no hay fatales
            pct = df[fatales].groupby(self.region_col, observed=True).size() / df.groupby(self.region_col, observed=True).size()
            agg['pct_fatal_region'] = pct.fillna(0.0) * 100.0
        else:
            agg['pct_fatal_region'] = 0.0
            
        self.stats_ = agg.to_dict('index')
        
        # Fallback values para regiones desconocidas en test/inferencia
        self.fallback_ = {
            "siniestros_por_region": agg["siniestros_por_region"].median(),
            "dist_media_region_km": agg["dist_media_region_km"].median(),
            "pct_fatal_region": agg["pct_fatal_region"].median() if 'pct_fatal_region' in agg else 0.0
        }
        return self
        
    def transform(self, X):
        X_out = X.copy()

        mapped = X_out[self.region_col].map(self.stats_)

        for col in ["siniestros_por_region", "dist_media_region_km", "pct_fatal_region"]:
            X_out[col] = mapped.apply(
            lambda v: v[col] if isinstance(v, dict) else self.fallback_[col]
        )

        return X_out
