import ollama
import asyncio

class ESGAdvisor:
    def __init__(self, model_name='llama3.2'):
        self.model_name = model_name

    async def generate_recommendations(self, company_name, industry, scores, metrics, benchmarks):
        prompt = f"""
        You are an elite ESG (Environmental, Social, and Governance) consultant. 
        Analyze the following company data and provide exactly 3 highly specific, actionable recommendations to improve their ESG performance.
        
        Company Context:
        - Name: {company_name}
        - Industry: {industry}
        - Overall ESG Score: {scores['total']}/100
        
        Key Metrics vs Industry Median (P50):
        - Their Renewable Energy: {metrics.get('renewable_pct', 0):.1f}% (Sector Median: {benchmarks['sector_medians']['renewable_pct']}%)
        - Their Female Workforce: {metrics.get('female_pct', 0):.1f}% (Sector Median: {benchmarks['sector_medians']['female_pct']}%)
        - Their GHG Intensity Percentile: {benchmarks['ghg_intensity_percentile']} (Higher is better)
        
        Strict Rules for your response:
        1. Format as exactly 3 bullet points. No intro or outro text.
        2. Identify specific gaps where they fall below the median.
        3. Suggest a realistic corporate action to close the gap.
        4. Do not use markdown bolding (**) in the bullet points.
        """
        
        try:
            client = ollama.AsyncClient()
            response = await client.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': prompt}]
            )
            raw_text = response['message']['content']
            recs = [line.strip().lstrip('*-• ') for line in raw_text.split('\n') if line.strip()]
            return recs[:3]
        except Exception as e:
            print(f"Ollama Error: {e}")
            return ["Increase renewable energy purchasing agreements.", "Conduct a gender diversity audit.", "Implement stricter tracking."]