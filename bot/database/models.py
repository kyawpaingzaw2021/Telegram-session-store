import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, BigInteger, Text, Index, text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    file_id = Column(String)
    file_path = Column(String, nullable=True)
    encrypted_2fa = Column(Text)
    price = Column(Integer, default=1000)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (Index('idx_products_is_active', 'is_active'),)

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    buyer_id = Column(BigInteger)
    buyer_username = Column(String)
    product_id = Column(Integer)
    quantity = Column(Integer, default=1)
    payment_method = Column(String)
    status = Column(String)
    slip_file_id = Column(String, nullable=True)
    login_code = Column(String, nullable=True)
    is_logged_in = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        Index('idx_orders_buyer_id', 'buyer_id'),
        Index('idx_orders_status', 'status'),
        Index('idx_orders_created_at', 'created_at'),
    )

class Setting(Base):
    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True)
    value = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Wallet(Base):
    __tablename__ = 'wallets'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True)
    balance = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (Index('idx_wallets_user_id', 'user_id'),)

class WalletTransaction(Base):
    __tablename__ = 'wallet_transactions'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    amount = Column(Integer)
    transaction_type = Column(String)
    order_id = Column(Integer, nullable=True)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        Index('idx_wallet_transactions_user_id', 'user_id'),
        Index('idx_wallet_transactions_created_at', 'created_at'),
    )

class Referral(Base):
    __tablename__ = 'referrals'
    id = Column(Integer, primary_key=True)
    referrer_id = Column(BigInteger)
    referred_id = Column(BigInteger, unique=True)
    bonus_earned = Column(Integer, default=0)
    status = Column(String, default="pending")  # pending, completed
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        Index('idx_referrals_referrer_id', 'referrer_id'),
        Index('idx_referrals_referred_id', 'referred_id', unique=True),
    )

# ဘယ် Server / Hosting မှာမဆို Permission Error လုံးဝမတက်စေရန် /tmp ကို အသုံးပြုထားပါသည်
DB_PATH = "/tmp/bot.db"
engine = create_engine(f'sqlite:///{DB_PATH}', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)

def enable_wal():
    try:
        conn = engine.connect()
        conn.execute(text("PRAGMA journal_mode=WAL;"))
        conn.execute(text("PRAGMA synchronous=NORMAL;"))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ WAL mode warning: {e}")

enable_wal()
print(f"✅ Database initialized at: {DB_PATH}")
