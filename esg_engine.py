import pandas as pd
from peer_benchmarks import PeerBenchmarkEngine
from llm_advisor import ESGAdvisor

class ESGCalculator:
    def __init__(self, data):
        self.data = data
        self.scores = {"environmental": 0, "social": 0, "governance": 0, "total": 0}
        self.recommendations = []
        self.brsr_mapping = {"P1": [], "P2": [], "P3": [], "P4": [], "P5": [], "P6": [], "P7": [], "P8": [], "P9": []}
        
        self.industry_map = {
            "Banking/Financial": {"E": 0.1, "S": 0.4, "G": 0.5},
            "IT/Services": {"E": 0.2, "S": 0.5, "G": 0.3},
            "Pharma/Healthcare": {"E": 0.4, "S": 0.3, "G": 0.3},
            "Chemicals": {"E": 0.5, "S": 0.2, "G": 0.3},
            "FMCG": {"E": 0.4, "S": 0.3, "G": 0.3},
            "Automobile": {"E": 0.5, "S": 0.3, "G": 0.2},
            "Energy/Power": {"E": 0.6, "S": 0.2, "G": 0.2},
            "Cement/Steel": {"E": 0.6, "S": 0.2, "G": 0.2},
            "Textiles": {"E": 0.4, "S": 0.4, "G": 0.2},
            "Telecom": {"E": 0.2, "S": 0.4, "G": 0.4},
            "Construction": {"E": 0.5, "S": 0.3, "G": 0.2},
            "Mining": {"E": 0.6, "S": 0.2, "G": 0.2},
            "Aviation": {"E": 0.6, "S": 0.2, "G": 0.2},
            "Retail": {"E": 0.3, "S": 0.4, "G": 0.3},
            "Logistics": {"E": 0.5, "S": 0.3, "G": 0.2}
        }
        
        ind = self.data['company_profile']['industry']
        self.base_weights = self.industry_map.get(ind, {"E": 0.33, "S": 0.33, "G": 0.34})

    def _calculate_environmental(self):
        env = self.data['environmental']
        prof = self.data['company_profile']
        score = 0
        
        rev = max(1, prof['annual_revenue_inr'] / 10000000)
        
        scope1 = env.get('scope_1_emissions_mt', 0)
        scope2 = env.get('scope_2_emissions_mt', 0)
        scope3 = env.get('scope_3_emissions_mt', 0)
        total_emissions = scope1 + scope2 + scope3
        
        if total_emissions > 0:
            intensity = total_emissions / rev
            score += min(40, max(0, 40 - (intensity * 2)))
            self.brsr_mapping["P6"].append({"metric": "GHG Emissions", "value": total_emissions})
        else:
            self.recommendations.append("Missing Scope 1/2/3 emissions data.")

        water = env.get('total_water_consumption_liters', 0)
        if water > 0:
            water_intensity = water / rev
            score += min(20, max(0, 20 - (water_intensity / 1000)))
            self.brsr_mapping["P6"].append({"metric": "Water Intensity", "value": water_intensity})
        
        actual_energy = max(1, env.get('total_energy_consumption_kwh', 1))
        ren_pct = (env.get('renewable_energy_kwh', 0) / actual_energy) * 100
        score += min(20, (ren_pct / 40) * 20)
        self.brsr_mapping["P6"].append({"metric": "Renewable Energy %", "value": ren_pct})

        gen = max(1, env.get('waste_generated_kg', 1))
        score += (env.get('waste_recycled_kg', 0) / gen) * 20
        self.brsr_mapping["P6"].append({"metric": "Waste Recycled %", "value": (env.get('waste_recycled_kg', 0) / gen) * 100})
            
        self.scores['environmental'] = round(score, 2)

    def _calculate_social(self):
        soc = self.data['social']
        total_emp = max(1, self.data['company_profile']['total_employees'])
        score = 0
        
        div_pct = (soc.get('female_employees', 0) / total_emp) * 100
        score += min(20, (div_pct / 40) * 20)
        self.brsr_mapping["P3"].append({"metric": "Female Employee %", "value": div_pct})
        
        dis_pct = (soc.get('employees_with_disabilities', 0) / total_emp) * 100
        score += min(10, (dis_pct / 5) * 10)
        self.brsr_mapping["P3"].append({"metric": "Employees with Disabilities %", "value": dis_pct})

        accidents = soc.get('safety_accidents_count', 0)
        if accidents == 0:
            score += 20
        else:
            score += max(0, 20 - (accidents * 5))
            self.recommendations.append(f"Safety Alert: {accidents} accidents reported.")
        self.brsr_mapping["P3"].append({"metric": "Safety Accidents", "value": accidents})

        train_pct = (soc.get('employees_trained_count', 0) / total_emp) * 100
        score += min(20, (train_pct / 80) * 20)
        self.brsr_mapping["P3"].append({"metric": "Employees Trained %", "value": train_pct})

        harassment = soc.get('complaints_received_sexual_harassment', 0)
        resolved = soc.get('complaints_resolved_sexual_harassment', 0)
        
        if harassment == 0:
            score += 30
        else:
            resolution_rate = resolved / harassment
            score += (resolution_rate * 30)
            if resolution_rate < 1:
                self.recommendations.append(f"POSH Alert: {harassment - resolved} unresolved sexual harassment complaints.")
        self.brsr_mapping["P5"].append({"metric": "POSH Complaints", "value": harassment})

        self.scores['social'] = min(100, round(score, 2))

    def _calculate_governance(self):
        gov = self.data['governance']
        score = 0
        
        policies = len(gov.get('policies_implemented', []))
        score += min(30, policies * 10)
        self.brsr_mapping["P1"].append({"metric": "Policies Implemented", "value": policies})
        
        if gov.get('regulatory_fines_paid_inr', 0) == 0:
            score += 30
        else:
            self.recommendations.append("Compliance Alert: Regulatory fines detected.")
        self.brsr_mapping["P1"].append({"metric": "Regulatory Fines", "value": gov.get('regulatory_fines_paid_inr', 0)})
        
        if gov.get('has_sustainability_committee', False):
            score += 20
        self.brsr_mapping["P7"].append({"metric": "Sustainability Committee", "value": gov.get('has_sustainability_committee', False)})
        
        if gov.get('brsr_filing_status', False):
            score += 20
        self.brsr_mapping["P1"].append({"metric": "BRSR Filing", "value": gov.get('brsr_filing_status', False)})
        
        self.scores['governance'] = min(100, round(score, 2))

    async def compute(self):
        self._calculate_environmental()
        self._calculate_social()
        self._calculate_governance()
        
        w = self.base_weights
        final = (self.scores['environmental'] * w['E']) + \
                (self.scores['social'] * w['S']) + \
                (self.scores['governance'] * w['G'])
        
        self.scores['total'] = round(final, 2)
        
        revenue_cr = self.data['company_profile']['annual_revenue_inr'] / 10000000
        total_emp = max(1, self.data['company_profile']['total_employees'])
        actual_energy = max(1, self.data['environmental'].get('total_energy_consumption_kwh', 1))
        
        peer_input_metrics = {
            "total_ghg": self.data['environmental'].get('scope_1_emissions_mt', 0) + \
                         self.data['environmental'].get('scope_2_emissions_mt', 0) + \
                         self.data['environmental'].get('scope_3_emissions_mt', 0),
            "water_liters": self.data['environmental'].get('total_water_consumption_liters', 0),
            "renewable_pct": (self.data['environmental'].get('renewable_energy_kwh', 0) / actual_energy) * 100,
            "female_pct": (self.data['social'].get('female_employees', 0) / total_emp) * 100
        }
        
        benchmark_engine = PeerBenchmarkEngine()
        peer_ranks = benchmark_engine.get_peer_ranking(
            self.data['company_profile']['industry'], 
            revenue_cr, 
            peer_input_metrics
        )
        
        ind_name = self.data['company_profile']['industry']
        company_name = self.data.get('company_name', 'The Company')
        
        peer_narratives = [
            f"Carbon Footprint: You rank better than {peer_ranks['ghg_intensity_percentile']}% of {ind_name} peers.",
            f"Water Efficiency: You rank better than {peer_ranks['water_intensity_percentile']}% of {ind_name} peers.",
            f"Workforce Diversity: Your female representation is better than {peer_ranks['diversity_percentile']}% of the market."
        ]
        
        advisor = ESGAdvisor()
        ai_recommendations = await advisor.generate_recommendations(
            company_name=company_name,
            industry=ind_name,
            scores=self.scores,
            metrics=peer_input_metrics,
            benchmarks=peer_ranks
        )
        
        final_recommendations = self.recommendations + ai_recommendations
        
        return {
            "scores": self.scores, 
            "recommendations": final_recommendations,
            "brsr_mapping": self.brsr_mapping,
            "peer_benchmarks": peer_ranks,
            "peer_narratives": peer_narratives
        }