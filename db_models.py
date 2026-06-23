from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    cin = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, index=True)
    industry = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    submissions = relationship("Submission", back_populates="company", cascade="all, delete-orphan")

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    financial_year = Column(String, index=True)
    annual_revenue_inr = Column(Float)
    total_employees = Column(Integer)
    score_environmental = Column(Float)
    score_social = Column(Float)
    score_governance = Column(Float)
    score_total = Column(Float)
    raw_metrics = Column(JSON)
    brsr_completeness_pct = Column(Float)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="submissions")

class SectorBenchmark(Base):
    __tablename__ = "sector_benchmarks"

    id = Column(Integer, primary_key=True, index=True)
    industry = Column(String, index=True)
    metric_name = Column(String)
    
    p25_value = Column(Float)
    p50_value = Column(Float)
    p75_value = Column(Float)
    
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())