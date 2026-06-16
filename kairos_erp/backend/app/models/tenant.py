from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    users = relationship("User", back_populates="company")
    feature_flags = relationship("CompanyFeatureFlag", back_populates="company", uselist=False)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="users")

class CompanyFeatureFlag(Base):
    __tablename__ = "company_feature_flags"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), unique=True)

    # Feature Toggles (True = enabled, False = disabled)
    module_meeting_parsing = Column(Boolean, default=False)
    module_contact_ocr = Column(Boolean, default=False)
    module_finance_sync = Column(Boolean, default=False)
    module_tax_invoice = Column(Boolean, default=False)
    module_mail_assistant = Column(Boolean, default=False)
    module_slack_bot = Column(Boolean, default=False)

    company = relationship("Company", back_populates="feature_flags")
