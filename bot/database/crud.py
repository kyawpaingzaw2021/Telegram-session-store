import os, base64, hashlib
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker
from .models import engine, Product, Order, Setting, Wallet, WalletTransaction, Referral
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from bot.config import ENCRYPTION_KEY, REFERRAL_BONUS

Session = sessionmaker(bind=engine)

# ==================== ENCRYPTION ====================
def get_cipher_key():
    return hashlib.sha256(ENCRYPTION_KEY.encode()).digest()

def encrypt_text(plain_text: str) -> str:
    key = get_cipher_key()
    cipher = AES.new(key, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(plain_text.encode('utf-8'), AES.block_size))
    iv = base64.b64encode(cipher.iv).decode('utf-8')
    ct = base64.b64encode(ct_bytes).decode('utf-8')
    return iv + ":" + ct

def decrypt_text(encrypted_text: str) -> str:
    try:
        key = get_cipher_key()
        iv, ct = encrypted_text.split(":")
        iv = base64.b64decode(iv); ct = base64.b64decode(ct)
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        pt = unpad(cipher.decrypt(ct), AES.block_size)
        return pt.decode('utf-8')
    except:
        return None

# ==================== PRODUCT CRUD ====================
def create_product(name, file_id, two_fa_plain, price, file_path=None):
    encrypted = encrypt_text(two_fa_plain)
    session = Session()
    product = Product(name=name, file_id=file_id, file_path=file_path, encrypted_2fa=encrypted, price=price)
    session.add(product); session.commit(); session.refresh(product); session.close()
    return product

def get_active_product():
    session = Session()
    product = session.query(Product).filter_by(is_active=1).first()
    session.close()
    return product

def get_product(product_id):
    session = Session()
    product = session.query(Product).filter_by(id=product_id).first()
    session.close()
    return product

def get_all_products():
    session = Session()
    products = session.query(Product).all()
    session.close()
    return products

def deactivate_product(product_id):
    session = Session()
    product = session.query(Product).filter_by(id=product_id).first()
    if product:
        product.is_active = 0
        session.commit(); session.close()
        return True
    session.close()
    return False

def activate_product(product_id):
    session = Session()
    product = session.query(Product).filter_by(id=product_id).first()
    if product:
        product.is_active = 1
        session.commit(); session.close()
        return True
    session.close()
    return False

def permanently_delete_product(product_id):
    session = Session()
    product = session.query(Product).filter_by(id=product_id).first()
    if product:
        if product.file_path and os.path.exists(product.file_path):
            os.remove(product.file_path)
        session.delete(product)
        session.commit(); session.close()
        return True
    session.close()
    return False

def decrypt_2fa(encrypted_text):
    return decrypt_text(encrypted_text)

# ==================== ORDER CRUD ====================
def create_order(buyer_id, buyer_username, product_id, quantity, payment_method, slip_file_id=None):
    session = Session()
    order = Order(buyer_id=buyer_id, buyer_username=buyer_username, product_id=product_id,
                  quantity=quantity, payment_method=payment_method, status="pending",
                  slip_file_id=slip_file_id)
    session.add(order); session.commit(); session.refresh(order); session.close()
    return order

def get_order(order_id):
    session = Session()
    order = session.query(Order).filter_by(id=order_id).first()
    session.close()
    return order

def get_orders_by_buyer(buyer_id, limit=10):
    session = Session()
    orders = session.query(Order).filter_by(buyer_id=buyer_id).order_by(Order.id.desc()).limit(limit).all()
    session.close()
    return orders

def update_order_status(order_id, status):
    session = Session()
    order = session.query(Order).filter_by(id=order_id).first()
    if order:
        order.status = status
        session.commit()
    session.close()

def update_order_login_status(order_id, is_logged_in):
    session = Session()
    order = session.query(Order).filter_by(id=order_id).first()
    if order:
        order.is_logged_in = is_logged_in
        if is_logged_in == 1:
            order.status = "completed"
        session.commit()
    session.close()

def get_recent_orders(limit=10):
    session = Session()
    orders = session.query(Order).order_by(Order.id.desc()).limit(limit).all()
    session.close()
    return orders

def get_all_orders():
    session = Session()
    orders = session.query(Order).all()
    session.close()
    return orders

def clear_all_orders():
    session = Session()
    session.query(Order).delete()
    session.commit()
    session.close()

def get_pending_orders():
    session = Session()
    count = session.query(Order).filter_by(status="pending").count()
    session.close()
    return count

def get_total_orders():
    session = Session()
    count = session.query(Order).count()
    session.close()
    return count

def get_today_orders():
    session = Session()
    today = datetime.now().date()
    count = session.query(Order).filter(func.date(Order.created_at) == today).count()
    session.close()
    return count

def get_total_mmk_income():
    session = Session()
    total = session.query(func.sum(Product.price * Order.quantity)).join(Order, Product.id == Order.product_id)\
        .filter(Order.payment_method == "slip", Order.status == "completed").scalar()
    session.close()
    return total or 0

def get_total_wallet_income():
    session = Session()
    total = session.query(func.sum(Product.price * Order.quantity)).join(Order, Product.id == Order.product_id)\
        .filter(Order.payment_method == "wallet", Order.status == "completed").scalar()
    session.close()
    return total or 0

def get_all_users():
    session = Session()
    users = session.query(Order.buyer_id).distinct().all()
    session.close()
    return [u[0] for u in users]

# ==================== WALLET CRUD (ပြင်ဆင်ပြီး) ====================
def get_wallet(user_id):
    session = Session()
    wallet = session.query(Wallet).filter_by(user_id=user_id).first()
    if not wallet:
        wallet = Wallet(user_id=user_id, balance=0)
        session.add(wallet)
        session.commit()
        session.refresh(wallet)
    session.close()
    return wallet

def get_wallet_balance(user_id):
    wallet = get_wallet(user_id)
    return wallet.balance

def add_wallet_balance(user_id, amount, transaction_type, order_id=None):
    session = Session()
    wallet = session.query(Wallet).filter_by(user_id=user_id).first()
    if not wallet:
        wallet = Wallet(user_id=user_id, balance=0)
        session.add(wallet)
    
    wallet.balance += amount
    wallet.updated_at = datetime.utcnow()
    
    tx = WalletTransaction(
        user_id=user_id,
        amount=amount,
        transaction_type=transaction_type,
        order_id=order_id,
        status="completed"
    )
    session.add(tx)
    session.commit()
    session.close()
    return wallet.balance

def deduct_wallet_balance(user_id, amount, order_id):
    session = Session()
    wallet = session.query(Wallet).filter_by(user_id=user_id).first()
    if not wallet:
        wallet = Wallet(user_id=user_id, balance=0)
        session.add(wallet)
        session.commit()
        session.refresh(wallet)
    
    if wallet.balance < amount:
        session.close()
        return False, wallet.balance
    
    wallet.balance -= amount
    wallet.updated_at = datetime.utcnow()
    
    tx = WalletTransaction(
        user_id=user_id,
        amount=-amount,
        transaction_type="purchase",
        order_id=order_id,
        status="completed"
    )
    session.add(tx)
    session.commit()
    
    # ✅ session မပိတ်ခင် balance ကိုသိမ်းပါ
    new_balance = wallet.balance
    session.close()
    return True, new_balance

def create_topup_request(user_id, amount):
    session = Session()
    tx = WalletTransaction(user_id=user_id, amount=amount, transaction_type="topup", order_id=None, status="pending")
    session.add(tx)
    session.commit()
    session.refresh(tx)
    session.close()
    return tx.id

def approve_topup(tx_id):
    session = Session()
    tx = session.query(WalletTransaction).filter_by(id=tx_id).first()
    if not tx or tx.status != "pending":
        session.close()
        return False
    
    wallet = session.query(Wallet).filter_by(user_id=tx.user_id).first()
    if not wallet:
        wallet = Wallet(user_id=tx.user_id, balance=0)
        session.add(wallet)
    
    wallet.balance += tx.amount
    wallet.updated_at = datetime.utcnow()
    tx.status = "completed"
    session.commit()
    session.close()
    return True

def get_wallet_transaction(tx_id):
    session = Session()
    tx = session.query(WalletTransaction).filter_by(id=tx_id).first()
    session.close()
    return tx

def get_wallet_transactions(user_id, limit=10):
    session = Session()
    txs = session.query(WalletTransaction).filter_by(user_id=user_id).order_by(WalletTransaction.id.desc()).limit(limit).all()
    session.close()
    return txs

def get_all_wallets():
    session = Session()
    wallets = session.query(Wallet).all()
    session.close()
    return wallets

def reset_user_wallet(user_id):
    session = Session()
    session.query(WalletTransaction).filter_by(user_id=user_id).delete()
    wallet = session.query(Wallet).filter_by(user_id=user_id).first()
    if wallet:
        session.delete(wallet)
    session.commit()
    session.close()

# ==================== REFERRAL CRUD ====================
def create_referral(referrer_id: int, referred_id: int):
    session = Session()
    existing = session.query(Referral).filter_by(referred_id=referred_id).first()
    if existing:
        session.close()
        return None
    referral = Referral(referrer_id=referrer_id, referred_id=referred_id, status="pending")
    session.add(referral)
    session.commit()
    session.refresh(referral)
    session.close()
    return referral

def get_referral_by_referred(referred_id: int):
    session = Session()
    referral = session.query(Referral).filter_by(referred_id=referred_id).first()
    session.close()
    return referral

def get_referrals_by_referrer(referrer_id: int, limit=10):
    session = Session()
    referrals = session.query(Referral).filter_by(referrer_id=referrer_id).order_by(Referral.id.desc()).limit(limit).all()
    session.close()
    return referrals

def get_total_referral_earnings(referrer_id: int):
    session = Session()
    total = session.query(func.sum(Referral.bonus_earned)).filter_by(referrer_id=referrer_id, status="completed").scalar()
    session.close()
    return total or 0

def get_referral_count(referrer_id: int):
    session = Session()
    count = session.query(Referral).filter_by(referrer_id=referrer_id, status="completed").count()
    session.close()
    return count

def complete_referral(referred_id: int):
    session = Session()
    referral = session.query(Referral).filter_by(referred_id=referred_id).first()
    if not referral or referral.status == "completed":
        session.close()
        return False
    referral.status = "completed"
    referral.bonus_earned = REFERRAL_BONUS
    session.commit()
    session.close()
    return True

def apply_referral_bonus(buyer_id: int) -> int | None:
    referral = get_referral_by_referred(buyer_id)
    if not referral or referral.status == "completed":
        return None
    
    add_wallet_balance(referral.referrer_id, REFERRAL_BONUS, "referral", None)
    complete_referral(buyer_id)
    return referral.referrer_id

# ==================== SETTINGS ====================
_settings_cache = {}

def get_setting(key, default=None):
    if key in _settings_cache:
        return _settings_cache[key]
    session = Session()
    setting = session.query(Setting).filter_by(key=key).first()
    session.close()
    value = setting.value if setting else default
    _settings_cache[key] = value
    return value

def update_setting(key, value):
    session = Session()
    setting = session.query(Setting).filter_by(key=key).first()
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        session.add(setting)
    session.commit()
    session.close()
    _settings_cache[key] = value

def get_all_settings_json():
    session = Session()
    settings = session.query(Setting).all()
    session.close()
    result = {}
    for setting in settings:
        result[setting.key] = setting.value
        _settings_cache[setting.key] = setting.value
    return result

def get_default_2fa():
    return get_setting('default_2fa', '123456')

def get_default_price():
    try:
        return int(get_setting('default_price', '1000'))
    except:
        return 1000

def get_kbz_number():
    return get_setting('kbz_number', '09255477757')

def get_wave_number():
    return get_setting('wave_number', '09255477757')
