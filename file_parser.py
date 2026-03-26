import pandas as pd
import io
import re
from pypdf import PdfReader

def parse_document(file_contents, filename):
    filename = filename.lower()
    if filename.endswith(('.xlsx', '.xls')):
        return parse_excel(file_contents)
    elif filename.endswith('.pdf'):
        return parse_pdf(file_contents)
    return {}

def parse_excel(content):
    try:
        df = pd.read_excel(io.BytesIO(content))
        # Convert entire sheet to string to search keywords easily
        return extract_variables_from_text(df.to_string().lower())
    except:
        return {}

def parse_pdf(content):
    try:
        reader = PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return extract_variables_from_text(text.lower())
    except:
        return {}

def extract_variables_from_text(text):
    extracted = {}
    
    def find_val(keywords):
        for k in keywords:
            # Improved Regex:
            # 1. Look for keyword
            # 2. Allow up to 20 chars of filler (e.g., ":", " is ", "INR")
            # 3. Capture the number (allowing commas and decimals)
            pattern = rf"{k}.{{0,20}}?([\d,]+\.?\d*)"
            match = re.search(pattern, text)
            if match:
                try:
                    val_str = match.group(1).replace(',', '')
                    return float(val_str)
                except:
                    continue
        return 0

    # Map text patterns to JSON keys
    extracted['annual_revenue_inr'] = find_val(['revenue', 'turnover'])
    extracted['total_employees'] = int(find_val(['employees', 'workforce']))
    extracted['total_energy_consumption_kwh'] = find_val(['energy', 'electricity'])
    extracted['renewable_energy_kwh'] = find_val(['renewable', 'solar'])
    extracted['waste_generated_kg'] = find_val(['waste generated'])
    extracted['waste_recycled_kg'] = find_val(['recycled'])
    
    # Text matching for Industry
    if 'cement' in text or 'steel' in text: extracted['industry'] = 'Cement/Steel'
    elif 'pharma' in text: extracted['industry'] = 'Pharma'
    elif 'retail' in text: extracted['industry'] = 'Retail'
    elif 'manufacturing' in text: extracted['industry'] = 'Manufacturing'
    else: extracted['industry'] = 'IT/Services'

    return extracted