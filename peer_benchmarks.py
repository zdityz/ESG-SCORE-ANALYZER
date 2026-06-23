class PeerBenchmarkEngine:
    def __init__(self):
        self.benchmarks = {
            "IT/Services": {
                "ghg_intensity_mt_cr": {"P25": 4.5, "P50": 2.1, "P75": 0.8},
                "water_intensity_l_cr": {"P25": 15000, "P50": 8500, "P75": 3200}, 
                "renewable_pct": {"P25": 5.0, "P50": 18.0, "P75": 45.0},
                "female_pct": {"P25": 22.0, "P50": 31.0, "P75": 38.0} 
            },
            "Banking/Financial": {
                "ghg_intensity_mt_cr": {"P25": 3.0, "P50": 1.2, "P75": 0.4},
                "water_intensity_l_cr": {"P25": 10000, "P50": 5000, "P75": 2000},
                "renewable_pct": {"P25": 2.0, "P50": 10.0, "P75": 30.0},
                "female_pct": {"P25": 18.0, "P50": 26.0, "P75": 35.0}
            },
            "Pharma/Healthcare": {
                "ghg_intensity_mt_cr": {"P25": 35.0, "P50": 18.5, "P75": 9.0},
                "water_intensity_l_cr": {"P25": 120000, "P50": 65000, "P75": 30000},
                "renewable_pct": {"P25": 8.0, "P50": 22.0, "P75": 50.0},
                "female_pct": {"P25": 12.0, "P50": 19.0, "P75": 28.0}
            },
            "Cement/Steel": {
                "ghg_intensity_mt_cr": {"P25": 850.0, "P50": 520.0, "P75": 310.0},
                "water_intensity_l_cr": {"P25": 500000, "P50": 280000, "P75": 150000},
                "renewable_pct": {"P25": 10.0, "P50": 25.0, "P75": 55.0},
                "female_pct": {"P25": 4.0, "P50": 8.0, "P75": 14.0}
            },
            "FMCG": {
                "ghg_intensity_mt_cr": {"P25": 25.0, "P50": 12.0, "P75": 5.5},
                "water_intensity_l_cr": {"P25": 90000, "P50": 45000, "P75": 18000},
                "renewable_pct": {"P25": 12.0, "P50": 28.0, "P75": 60.0},
                "female_pct": {"P25": 15.0, "P50": 22.0, "P75": 32.0}
            }
        }
        
        self.fallback_sector = {
            "ghg_intensity_mt_cr": {"P25": 50.0, "P50": 25.0, "P75": 10.0},
            "water_intensity_l_cr": {"P25": 100000, "P50": 50000, "P75": 20000},
            "renewable_pct": {"P25": 5.0, "P50": 20.0, "P75": 45.0},
            "female_pct": {"P25": 10.0, "P50": 20.0, "P75": 30.0}
        }

    def _calculate_percentile(self, val, p25, p50, p75, invert=False):
        if invert:
            if val <= p75:
                return min(99, int(75 + ((p75 - val) / p75) * 24))
            elif val <= p50:
                return int(50 + ((p50 - val) / (p50 - p75)) * 25)
            elif val <= p25:
                return int(25 + ((p25 - val) / (p25 - p50)) * 25)
            else:
                return max(1, int(25 - ((val - p25) / p25) * 24))
        else:
            if val >= p75:
                return min(99, int(75 + ((val - p75) / p75) * 24))
            elif val >= p50:
                return int(50 + ((val - p50) / (p75 - p50)) * 25)
            elif val >= p25:
                return int(25 + ((val - p25) / (p50 - p25)) * 25)
            else:
                return max(1, int((val / p25) * 25))

    def get_peer_ranking(self, industry, revenue_cr, metrics):
        sector_data = self.benchmarks.get(industry, self.fallback_sector)
        ghg_intensity = metrics.get('total_ghg', 0) / max(1, revenue_cr)
        water_intensity = metrics.get('water_liters', 0) / max(1, revenue_cr)
        
        ghg_rank = self._calculate_percentile(
            ghg_intensity, 
            sector_data['ghg_intensity_mt_cr']['P25'], 
            sector_data['ghg_intensity_mt_cr']['P50'], 
            sector_data['ghg_intensity_mt_cr']['P75'], 
            invert=True
        )
        
        water_rank = self._calculate_percentile(
            water_intensity, 
            sector_data['water_intensity_l_cr']['P25'], 
            sector_data['water_intensity_l_cr']['P50'], 
            sector_data['water_intensity_l_cr']['P75'], 
            invert=True
        )
        
        ren_rank = self._calculate_percentile(
            metrics.get('renewable_pct', 0), 
            sector_data['renewable_pct']['P25'], 
            sector_data['renewable_pct']['P50'], 
            sector_data['renewable_pct']['P75']
        )
        
        female_rank = self._calculate_percentile(
            metrics.get('female_pct', 0), 
            sector_data['female_pct']['P25'], 
            sector_data['female_pct']['P50'], 
            sector_data['female_pct']['P75']
        )
        
        return {
            "ghg_intensity_percentile": ghg_rank,
            "water_intensity_percentile": water_rank,
            "renewable_energy_percentile": ren_rank,
            "diversity_percentile": female_rank,
            "sector_medians": {
                "ghg_intensity_mt_cr": sector_data['ghg_intensity_mt_cr']['P50'],
                "water_intensity_l_cr": sector_data['water_intensity_l_cr']['P50'],
                "renewable_pct": sector_data['renewable_pct']['P50'],
                "female_pct": sector_data['female_pct']['P50']
            }
        }