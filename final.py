from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Literal
from sqlalchemy.orm import Session
from esg_engine import ESGCalculator 
from file_parser import parse_document
from database import engine, get_db
import db_models
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import matplotlib
import matplotlib.pyplot as plt
import io
import datetime

matplotlib.use('Agg')
app = FastAPI(title="ESG Scorer AI", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class CompanyProfile(BaseModel):
    industry: Literal[
        "Banking/Financial", "IT/Services", "Pharma/Healthcare", "Chemicals", 
        "FMCG", "Automobile", "Energy/Power", "Cement/Steel", "Textiles", 
        "Telecom", "Construction", "Mining", "Aviation", "Retail", "Logistics"
    ]
    annual_revenue_inr: float = Field(..., gt=0)
    total_employees: int = Field(..., gt=0)

class EnvironmentalData(BaseModel):
    scope_1_emissions_mt: float = Field(default=0, ge=0)
    scope_2_emissions_mt: float = Field(default=0, ge=0)
    scope_3_emissions_mt: float = Field(default=0, ge=0)
    total_energy_consumption_kwh: float = Field(..., ge=0)
    renewable_energy_kwh: float = Field(..., ge=0)
    total_water_consumption_liters: float = Field(..., ge=0)
    waste_generated_kg: float = Field(..., ge=0)
    waste_recycled_kg: float = Field(..., ge=0)

class SocialData(BaseModel):
    female_employees: int = Field(..., ge=0)
    employees_with_disabilities: int = Field(..., ge=0)
    safety_accidents_count: int = Field(..., ge=0)
    employees_trained_count: int = Field(..., ge=0)
    complaints_received_sexual_harassment: int = Field(..., ge=0)
    complaints_resolved_sexual_harassment: int = Field(default=0, ge=0)

class GovernanceData(BaseModel):
    has_sustainability_committee: bool
    brsr_filing_status: bool = Field(default=False)
    regulatory_fines_paid_inr: float = Field(..., ge=0)
    policies_implemented: List[str]

class ESGRequest(BaseModel):
    company_profile: CompanyProfile
    environmental: EnvironmentalData
    social: SocialData
    governance: GovernanceData

class SubmissionRequest(BaseModel):
    cin: str
    company_name: str
    financial_year: str
    esg_data: ESGRequest
def get_radar_chart_bytes(scores):
    categories = ['Env', 'Social', 'Gov']
    values = [scores['environmental'], scores['social'], scores['governance']]
    values += values[:1]
    angles = [n / float(len(categories)) * 2 * 3.14159 for n in range(len(categories))]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
    ax.fill(angles, values, color='#1f77b4', alpha=0.4)
    ax.plot(angles, values, color='#1f77b4', linewidth=2)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    ax.set_yticklabels([])
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf

def create_pdf_report(data):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    styles = getSampleStyleSheet()
    c.setFillColor(colors.darkblue)
    c.rect(0, height-100, width, 100, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height-60, "ESG & BRSR AUDIT REPORT")

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height-150, "Executive Summary")
    c.setFont("Helvetica", 14)
    c.drawString(50, height-180, f"Total Score: {data['scores']['total']} / 100")
    c.drawString(50, height-200, f"Industry: {data['company_profile']['industry']}")

    graph_buf = get_radar_chart_bytes(data['scores'])
    c.drawImage(ImageReader(graph_buf), 300, height-350, 250, 250, mask='auto')
    y = height-380
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Actionable Alerts & Recommendations:")
    y -= 20
    
    style = styles["Normal"]
    style.fontName = "Helvetica"
    style.fontSize = 10
    style.leading = 14
    
    if not data['recommendations']:
        p = Paragraph("• Excellent Compliance. No critical alerts detected.", style)
        w, h = p.wrap(width - 100, height)
        y -= h
        p.drawOn(c, 50, y)
    else:
        for rec in data['recommendations']:
            p = Paragraph(f"• {rec}", style)
            w, h = p.wrap(width - 100, height) 
            y -= h
            p.drawOn(c, 50, y)
            y -= 10
            
    y -= 20
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "NSE/BSE Top 1000 Peer Benchmarking:")
    y -= 20
    for narrative in data.get('peer_narratives', []):
        p = Paragraph(f"★ {narrative}", style)
        w, h = p.wrap(width - 100, height)
        y -= h
        p.drawOn(c, 50, y)
        y -= 10
            
    y -= 15
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "BRSR Principle Mapping Highlights:")
    y -= 25
    c.setFont("Helvetica", 10)
    
    for principle, metrics in data.get('brsr_mapping', {}).items():
        if metrics:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y, f"Principle {principle[1:]} ({principle}):")
            c.setFont("Helvetica", 10)
            y -= 15
            for item in metrics:
                val = round(item['value'], 2) if isinstance(item['value'], float) else item['value']
                c.drawString(70, y, f"- {item['metric']}: {val}")
                y -= 15
            y -= 5 

            if y < 50:
                c.showPage()
                y = height - 50
    
    c.save()
    buffer.seek(0)
    return buffer

@app.post("/calculate_score")
async def calculate_esg(request: ESGRequest):
    try:
        return await ESGCalculator(request.dict()).compute()
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/generate_graph")
async def generate_graph(request: ESGRequest):
    try:
        res = await ESGCalculator(request.dict()).compute()
        return StreamingResponse(get_radar_chart_bytes(res['scores']), media_type="image/png")
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/generate_report")
async def generate_report(request: ESGRequest):
    try:
        req_data = request.dict()
        res = await ESGCalculator(req_data).compute()
        res['company_profile'] = req_data['company_profile']
        
        pdf_buffer = create_pdf_report(res)
        
        return StreamingResponse(
            pdf_buffer, 
            media_type='application/pdf', 
            headers={"Content-Disposition": "attachment; filename=esg_brsr_report.pdf"}
        )
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/extract_from_file")
async def extract_from_file(files: List[UploadFile] = File(...)):
    combined_data = {
        "company_profile": {"industry": "IT/Services", "annual_revenue_inr": 0, "total_employees": 0},
        "environmental": {
            "scope_1_emissions_mt": 0, "scope_2_emissions_mt": 0, "scope_3_emissions_mt": 0,
            "total_energy_consumption_kwh": 0, "renewable_energy_kwh": 0, 
            "total_water_consumption_liters": 0, "waste_generated_kg": 0, "waste_recycled_kg": 0
        },
        "social": {
            "female_employees": 0, "employees_with_disabilities": 0, "safety_accidents_count": 0, 
            "employees_trained_count": 0, "complaints_received_sexual_harassment": 0,
            "complaints_resolved_sexual_harassment": 0
        },
        "governance": {
            "has_sustainability_committee": False, "brsr_filing_status": False,
            "regulatory_fines_paid_inr": 0, "policies_implemented": []
        }
    }
    
    for file in files:
        content = await file.read()
        extracted = parse_document(content, file.filename)
        if 'annual_revenue_inr' in extracted: combined_data['company_profile']['annual_revenue_inr'] = extracted['annual_revenue_inr']
        if 'total_employees' in extracted: combined_data['company_profile']['total_employees'] = extracted['total_employees']
        if 'industry' in extracted: combined_data['company_profile']['industry'] = extracted['industry']
        if 'total_energy_consumption_kwh' in extracted: combined_data['environmental']['total_energy_consumption_kwh'] = extracted['total_energy_consumption_kwh']
        
    return combined_data

@app.post("/submit_brsr")
async def submit_brsr(request: SubmissionRequest, db: Session = Depends(get_db)):
    company = db.query(db_models.Company).filter(db_models.Company.cin == request.cin).first()
    
    if not company:
        company = db_models.Company(
            cin=request.cin,
            name=request.company_name,
            industry=request.esg_data.company_profile.industry
        )
        db.add(company)
        db.commit()
        db.refresh(company)

    calc = ESGCalculator(request.esg_data.dict())
    results = await calc.compute()
    
    total_fields = 15
    filled_fields = 0
    
    env_data = request.esg_data.environmental.dict()
    for key, val in env_data.items():
        if val > 0:
            filled_fields += 1
            
    soc_data = request.esg_data.social.dict()
    for key, val in soc_data.items():
        if val > 0:
            filled_fields += 1
            
    gov_data = request.esg_data.governance.dict()
    if gov_data.get('has_sustainability_committee'):
        filled_fields += 1
    if gov_data.get('brsr_filing_status'):
        filled_fields += 1
    if len(gov_data.get('policies_implemented', [])) > 0:
        filled_fields += 1
            
    completeness = round((filled_fields / total_fields) * 100, 2)

    new_submission = db_models.Submission(
        company_id=company.id,
        financial_year=request.financial_year,
        annual_revenue_inr=request.esg_data.company_profile.annual_revenue_inr,
        total_employees=request.esg_data.company_profile.total_employees,
        score_environmental=results['scores']['environmental'],
        score_social=results['scores']['social'],
        score_governance=results['scores']['governance'],
        score_total=results['scores']['total'],
        raw_metrics=request.esg_data.dict(),
        brsr_completeness_pct=completeness
    )
    
    db.add(new_submission)
    db.commit()
    
    return {
        "message": "Submission saved successfully", 
        "brsr_completeness": f"{completeness}%", 
        "scores": results['scores']
    }

@app.get("/yoy_trend/{cin}")
def get_yoy_trend(cin: str, db: Session = Depends(get_db)):
    company = db.query(db_models.Company).filter(db_models.Company.cin == cin).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
        
    submissions = db.query(db_models.Submission).filter(
        db_models.Submission.company_id == company.id
    ).order_by(db_models.Submission.financial_year).all()
    
    trends = []
    for sub in submissions:
        trends.append({
            "financial_year": sub.financial_year,
            "total_score": sub.score_total,
            "environmental_score": sub.score_environmental,
            "social_score": sub.score_social,
            "governance_score": sub.score_governance,
            "completeness_pct": sub.brsr_completeness_pct
        })
        
    return {
        "company_name": company.name, 
        "cin": company.cin,
        "industry": company.industry,
        "historical_trends": trends
    }