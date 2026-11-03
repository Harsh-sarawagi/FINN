from sqlalchemy import select

from app.database.connection import SessionLocal
from app.models import Company

COMPANIES = [
    ("RELIANCE", "Reliance Industries Limited", "NSE"),
    ("TCS", "Tata Consultancy Services Limited", "NSE"),
    ("INFY", "Infosys Limited", "NSE"),
    ("HDFCBANK", "HDFC Bank Limited", "NSE"),
    ("ICICIBANK", "ICICI Bank Limited", "NSE"),
    ("BHARTIARTL", "Bharti Airtel Limited", "NSE"),
    ("SBIN", "State Bank of India", "NSE"),
    ("ITC", "ITC Limited", "NSE"),
    ("LT", "Larsen & Toubro Limited", "NSE"),
    ("HINDUNILVR", "Hindustan Unilever Limited", "NSE"),
    ("AXISBANK", "Axis Bank Limited", "NSE"),
    ("KOTAKBANK", "Kotak Mahindra Bank Limited", "NSE"),
    ("MARUTI", "Maruti Suzuki India Limited", "NSE"),
    ("SUNPHARMA", "Sun Pharmaceutical Industries Limited", "NSE"),
    ("TATAMOTORS", "Tata Motors Limited", "NSE"),
    ("BAJFINANCE", "Bajaj Finance Limited", "NSE"),
    ("ASIANPAINT", "Asian Paints Limited", "NSE"),
    ("TITAN", "Titan Company Limited", "NSE"),
    ("NTPC", "NTPC Limited", "NSE"),
    ("POWERGRID", "Power Grid Corporation of India Limited", "NSE"),
]


def seed() -> None:
    with SessionLocal() as db:
        for ticker, name, exchange in COMPANIES:
            company = db.scalar(select(Company).where(Company.ticker == ticker, Company.exchange == exchange))
            if company is None:
                db.add(Company(ticker=ticker, name=name, exchange=exchange))
        db.commit()


if __name__ == "__main__":
    seed()
    print("Seed data added.")
