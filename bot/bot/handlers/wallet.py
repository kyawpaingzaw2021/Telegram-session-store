import os, logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.config import ADMIN_IDS
from database import crud
from bot.keyboards.inline import get_back_button, get_wallet_menu_keyboard, get_topup_amount_keyboard, get_topup_approve_keyboard, get_withdraw_amount_keyboard, get_otp_request_keyboard
from utils.rate_limiter import check_rate_limit
from utils.otp_fetcher import fetch_otp_from_777000, check_new_login_from_777000

logger = logging.getLogger(__name__)

# ==================== PAY WITH WALLET ====================
async def pay_with_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not check_rate_limit(update.effective_user.id, "pay_wallet"):
        await query.edit_message_text("⏳ ကျေးဇူးပြု၍ စက္ကန့် ၆၀ စောင့်ပါ။", reply_markup=get_back_button())
        return
    user_id = update.effective_user.id
    quantity = context.user_data.get('bulk_quantity', 1)
    product_id = context.user_data.get('product_id')
    total_price = context.user_data.get('bulk_total', 0)
    if not product_id:
        await query.edit_message_text("❌ Product မတွေ့ပါ။", reply_markup=get_back_button())
        return
    product = crud.get_product(product_id)
    if not product:
        await query.edit_message_text("❌ Product မတွေ့ပါ။", reply_markup=get_back_button())
        return
    success, new_balance = crud.deduct_wallet_balance(user_id, total_price, None)
    if not success:
        await query.edit_message_text(f"❌ **Wallet Balance မလုံလောက်ပါ။**\n\n💰 သင်၏ Balance: {crud.get_wallet_balance(user_id)} MMK", reply_markup=get_back_button(), parse_mode="Markdown")
        return
    buyer_username = update.effective_user.username or "NoUsername"
    order = crud.create_order(user_id, buyer_username, product.id, quantity, "wallet")
    crud.update_order_status(order.id, "paid")
    await send_delivery_wallet(context, user_id, buyer_username, product, quantity, "💰 Wallet", order.id)

# ==================== PAY WITH SLIP ====================
async def pay_with_slip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['awaiting_slip'] = True
    kbz = crud.get_kbz_number()
    wave = crud.get_wave_number()
    total_price = context.user_data.get('bulk_total', 0)
    quantity = context.user_data.get('bulk_quantity', 1)
    await query.edit_message_text(
        f"💵 **{total_price} MMK ဖြင့် ငွေပေးချေရန်**\n\n📦 Quantity: {quantity} ခု\n💰 Total: {total_price} MMK\n\n🏦 KBZ Pay: `{kbz}`\n🏦 Wave Pay: `{wave}`\n\n📸 ငွေလွှဲပြီးပါက Screenshot (Photo) ကို ဤ Chat တွင် တိုက်ရိုက်တင်ပေးပါ။",
        reply_markup=get_back_button(),
        parse_mode="Markdown"
    )

# ==================== SEND DELIVERY (Wallet) ====================
async def send_delivery_wallet(context, buyer_id, buyer_username, product, quantity, payment_method, order_id):
    two_fa = crud.decrypt_2fa(product.encrypted_2fa)
    phone = os.path.splitext(product.name)[0]
    if not phone.startswith('+'):
        phone = '+' + phone
    if quantity == 1:
        crud.update_order_status(order_id, "login_required")
        await context.bot.send_message(
            chat_id=buyer_id,
            text=f"✅ ဝယ်ယူမှု အောင်မြင်ပါပြီ။\n\n📱 **Phone Number**: `{phone}`\n🔑 **2FA Code**: `{two_fa}`\n\n⚠️ 2FA Code ကို လုံခြုံစွာ သိမ်းဆည်းထားပါ။\n📝 OTP ရယူရန် အောက်ပါခလုတ်ကို နှိပ်ပါ။",
            reply_markup=get_otp_request_keyboard(order_id),
            parse_mode="Markdown"
        )
    else:
        text = f"✅ **Bulk Purchase Successful!**\n\n📦 **Quantity:** {quantity} ခု\n📱 **Phone Number:** `{phone}`\n🔑 **2FA Code:** `{two_fa}`\n\n📋 **Session List:**\n"
        for i in range(1, quantity + 1):
            text += f"{i}. `{phone}`\n"
        text += f"\n⚠️ 2FA Code ကို လုံခြုံစွာ သိမ်းဆည်းထားပါ။\n📝 OTP ရယူရန် အောက်ပါခလုတ်ကို နှိပ်ပါ။"
        await context.bot.send_message(
            chat_id=buyer_id,
            text=text,
            reply_markup=get_otp_request_keyboard(order_id),
            parse_mode="Markdown"
        )
    crud.update_order_status(order_id, "login_required")
    context.user_data['temp_order_id'] = order_id
    context.user_data['temp_product_id'] = product.id
    context.user_data['temp_phone'] = phone
    crud.deactivate_product(product.id)

# ==================== MY WALLET ====================
async def my_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not check_rate_limit(update.effective_user.id, "my_wallet"):
        await query.edit_message_text("⏳ ကျေးဇူးပြု၍ စက္ကန့် ၆၀ စောင့်ပါ။", reply_markup=get_back_button())
        return
    user_id = update.effective_user.id
    wallet = crud.get_wallet(user_id)
    txs = crud.get_wallet_transactions(user_id, limit=5)
    referrals = crud.get_referrals_by_referrer(user_id, limit=3)
    total_earned = crud.get_total_referral_earnings(user_id)
    ref_count = crud.get_referral_count(user_id)
    
    text = f"💰 **My Wallet**\n\n📊 သင်၏ လက်ကျန်ငွေ: **{wallet.balance:,} MMK**\n\n📜 နောက်ဆုံး ငွေလွှဲမှတ်တမ်း:\n"
    if txs:
        for tx in txs:
            if tx.amount > 0:
                text += f"✅ +{tx.amount:,} MMK | {tx.transaction_type}\n"
            else:
                text += f"❌ {tx.amount:,} MMK | {tx.transaction_type}\n"
    else:
        text += "မရှိသေးပါ။\n"
    
    text += f"\n👥 **Referral Stats**\n📤 Referred Friends: {ref_count}\n💰 Total Earned: {total_earned:,} MMK\n"
    if referrals:
        text += "📋 Recent Referrals:\n"
        for ref in referrals:
            status = "✅ Completed" if ref.status == "completed" else "⏳ Pending"
            text += f"  • ID {ref.referred_id} | {status}\n"
    
    await query.edit_message_text(text, reply_markup=get_wallet_menu_keyboard(), parse_mode="Markdown")

async def refresh_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await my_wallet(update, context)

# ==================== TOP-UP ====================
async def topup_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not check_rate_limit(update.effective_user.id, "topup_request"):
        await query.edit_message_text("⏳ ကျေးဇူးပြု၍ စက္ကန့် ၆၀ စောင့်ပါ။", reply_markup=get_back_button())
        return
    await query.edit_message_text("📤 **Top-up Request**\n\nထည့်သွင်းလိုသော ပမာဏကို ရွေးပါ။\n\n(ငွေလွှဲပြီးပါက Slip ကို ထပ်မံတင်ပေးရမည်)",
        reply_markup=get_topup_amount_keyboard(), parse_mode="Markdown")

async def topup_amount_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data == "topup_custom":
        await query.answer()
        context.user_data['awaiting_topup_custom'] = True
        await query.edit_message_text("📝 **Custom Amount**\n\nလိုချင်သော ပမာဏ (MMK) ကို ရိုက်ထည့်ပါ။", reply_markup=get_back_button(), parse_mode="Markdown")
        return
    amount = int(data.split("_")[1])
    await process_topup_request(update, context, amount, query)

async def receive_custom_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_topup_custom', False):
        return
    try:
        amount = int(update.message.text.strip())
        if amount < 100:
            await update.message.reply_text("❌ အနည်းဆုံး 100 MMK ဖြစ်ရပါမည်။")
            return
    except:
        await update.message.reply_text("❌ ဂဏန်းတစ်ခုသာ ရိုက်ထည့်ပါ။")
        return
    context.user_data['awaiting_topup_custom'] = False
    await process_topup_request(update, context, amount, None)

async def process_topup_request(update, context, amount, query=None):
    user_id = update.effective_user.id
    user_username = update.effective_user.username or "NoUsername"
    tx_id = crud.create_topup_request(user_id, amount)
    kbz = crud.get_kbz_number()
    wave = crud.get_wave_number()
    context.user_data['awaiting_topup_slip'] = True
    context.user_data['topup_tx_id'] = tx_id
    context.user_data['topup_amount'] = amount
    text = f"💵 **Top-up Request**\n\n📝 ပမာဏ: {amount:,} MMK\n🆔 Request ID: {tx_id}\n\n🏦 KBZ Pay: `{kbz}`\n🏦 Wave Pay: `{wave}`\n\n📸 ငွေလွှဲပြီးပါက Screenshot (Photo) ကို ဤ Chat တွင် တိုက်ရိုက်တင်ပေးပါ။"
    if query:
        await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=get_back_button(), parse_mode="Markdown")

# ==================== ✅ APPROVE TOP-UP ====================
async def approve_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ အတည်ပြုနေပါသည်...")
    
    try:
        parts = query.data.split("_")
        tx_id = int(parts[2])
        logger.info(f"✅ Approving top-up: {tx_id}")
    except (IndexError, ValueError) as e:
        logger.error(f"❌ Error parsing tx_id from {query.data}: {e}")
        await query.answer("❌ Request ID မှားနေပါသည်။", show_alert=True)
        return
    
    success = crud.approve_topup(tx_id)
    
    if success:
        tx = crud.get_wallet_transaction(tx_id)
        if tx:
            try:
                await context.bot.send_message(
                    chat_id=tx.user_id,
                    text=f"✅ **Top-up Approved!**\n💰 {tx.amount:,} MMK ကို သင်၏ Wallet ထဲ ထည့်သွင်းပြီးပါပြီ။\n📊 လက်ကျန်ငွေ: {crud.get_wallet_balance(tx.user_id):,} MMK",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"❌ Failed to notify user {tx.user_id}: {e}")
        
        # ✅ ဒီမှာ caption ကိုပြင်ပါ
        try:
            await query.edit_message_caption(
                caption=f"✅ **Top-up Request #{tx_id} ကို အတည်ပြုပြီးပါပြီ။**",
                parse_mode="Markdown"
            )
        except Exception as e:
            # မပြင်နိုင်ရင် text message ပို့ပါ
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ **Top-up Request #{tx_id} ကို အတည်ပြုပြီးပါပြီ။**",
                parse_mode="Markdown"
            )
        logger.info(f"✅ Top-up {tx_id} approved successfully")
    else:
        try:
            await query.edit_message_caption(
                caption=f"❌ **Top-up Request #{tx_id} ကို အတည်ပြုရာတွင် အမှားရှိသည်။**\n\nအကြောင်းရင်း: Request မရှိပါ သို့မဟုတ် ပြီးသွားပါပြီ။",
                parse_mode="Markdown"
            )
        except:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ **Top-up Request #{tx_id} ကို အတည်ပြုရာတွင် အမှားရှိသည်။**",
                parse_mode="Markdown"
            )
        logger.warning(f"❌ Failed to approve top-up {tx_id}")

# ==================== ❌ REJECT TOP-UP (ပြင်ဆင်ပြီး) ====================
async def reject_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    try:
        parts = query.data.split("_")
        tx_id = int(parts[2])
        logger.info(f"❌ Rejecting top-up: {tx_id}")
    except (IndexError, ValueError) as e:
        logger.error(f"❌ Error parsing tx_id from {query.data}: {e}")
        await query.answer("❌ Request ID မှားနေပါသည်။", show_alert=True)
        return
    
    # ✅ ဒီမှာ caption ကိုပြင်ပါ (edit_message_caption)
    try:
        await query.edit_message_caption(
            caption=f"❌ **Top-up Request #{tx_id} ကို ပယ်ချလိုက်ပါပြီ။**",
            parse_mode="Markdown"
        )
    except Exception as e:
        # မပြင်နိုင်ရင် text message ပို့ပါ
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ **Top-up Request #{tx_id} ကို ပယ်ချလိုက်ပါပြီ။**",
            parse_mode="Markdown"
        )
    logger.info(f"❌ Top-up {tx_id} rejected")

# ==================== WITHDRAW ====================
async def withdraw_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    balance = crud.get_wallet_balance(user_id)
    if balance < 100:
        await query.edit_message_text(f"❌ အနည်းဆုံး 100 MMK ရှိမှ ထုတ်ယူနိုင်ပါသည်။\n💰 သင်၏ Balance: {balance:,} MMK", reply_markup=get_back_button(), parse_mode="Markdown")
        return
    await query.edit_message_text(
        f"💸 **Withdraw Wallet**\n\n💰 သင်၏ Balance: {balance:,} MMK\n\nထုတ်ယူလိုသော ပမာဏကို ရွေးပါ။",
        reply_markup=get_withdraw_amount_keyboard(),
        parse_mode="Markdown"
    )

async def withdraw_amount_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data == "withdraw_custom":
        await query.answer()
        context.user_data['awaiting_withdraw'] = True
        await query.edit_message_text(
            "📝 **Custom Withdrawal Amount**\n\nထုတ်ယူလိုသော ပမာဏ (MMK) ကို ရိုက်ထည့်ပါ။",
            reply_markup=get_back_button(),
            parse_mode="Markdown"
        )
        return
    amount = int(data.split("_")[1])
    await process_withdrawal(update, context, amount, query)

async def receive_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_withdraw', False):
        return
    try:
        amount = int(update.message.text.strip())
        if amount < 100:
            await update.message.reply_text("❌ အနည်းဆုံး 100 MMK ဖြစ်ရပါမည်။")
            return
    except:
        await update.message.reply_text("❌ ဂဏန်းတစ်ခုသာ ရိုက်ထည့်ပါ။")
        return
    context.user_data['awaiting_withdraw'] = False
    await process_withdrawal(update, context, amount, None)

async def process_withdrawal(update, context, amount, query=None):
    user_id = update.effective_user.id
    balance = crud.get_wallet_balance(user_id)
    if amount > balance:
        msg = f"❌ သင်၏ Balance ထက် မပိုရပါ။\n💰 Balance: {balance:,} MMK"
        if query:
            await query.edit_message_text(msg, reply_markup=get_back_button(), parse_mode="Markdown")
        else:
            await update.message.reply_text(msg, reply_markup=get_back_button(), parse_mode="Markdown")
        return
    success, new_balance = crud.deduct_wallet_balance(user_id, amount, None)
    if not success:
        msg = "❌ Balance မလုံလောက်ပါ။"
        if query:
            await query.edit_message_text(msg, reply_markup=get_back_button())
        else:
            await update.message.reply_text(msg, reply_markup=get_back_button())
        return
    for admin_id in ADMIN_IDS:
        await context.bot.send_message(
            chat_id=admin_id,
            text=f"📤 **Withdrawal Request**\n👤 User: @{update.effective_user.username or 'NoUsername'} (ID: {user_id})\n💰 Amount: {amount:,} MMK",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve Withdrawal", callback_data=f"approve_withdraw_{user_id}_{amount}")],
                [InlineKeyboardButton("❌ Reject", callback_data=f"reject_withdraw_{user_id}_{amount}")]
            ]),
            parse_mode="Markdown"
        )
    msg = f"✅ သင်၏ Withdrawal Request ( {amount:,} MMK ) ကို Admin ထံ ပေးပို့ပြီးပါပြီ။\n⏳ Admin အတည်ပြုချက်ကို စောင့်ဆိုင်းပါ။"
    if query:
        await query.edit_message_text(msg, reply_markup=get_back_button(), parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, reply_markup=get_back_button(), parse_mode="Markdown")
