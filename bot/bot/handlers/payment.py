import os, logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.config import ADMIN_IDS
from database import crud
from bot.keyboards.inline import get_back_button, get_otp_request_keyboard, get_otp_result_keyboard
from utils.otp_fetcher import fetch_otp_from_777000
from utils.rate_limiter import check_rate_limit

logger = logging.getLogger(__name__)

# ==================== RECEIVE TOP-UP SLIP ====================
async def receive_topup_slip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Top-up အတွက် Slip ကိုလက်ခံပါ"""
    if not context.user_data.get('awaiting_topup_slip', False):
        return
    if not update.message.photo:
        await update.message.reply_text("❌ ကျေးဇူးပြု၍ Photo (Screenshot) ကိုသာ တင်ပေးပါ။")
        return
    photo = update.message.photo[-1]
    buyer_id = update.message.chat_id
    buyer_username = update.message.from_user.username or "NoUsername"
    tx_id = context.user_data.get('topup_tx_id')
    amount = context.user_data.get('topup_amount')
    if not tx_id:
        await update.message.reply_text("❌ Top-up Request မတွေ့ပါ။ /start နှိပ်ပြီး ပြန်စပါ။")
        context.user_data.clear()
        return
    for admin_id in ADMIN_IDS:
        await context.bot.send_photo(
            chat_id=admin_id,
            photo=photo.file_id,
            caption=f"📩 **Top-up Slip Received**\n👤 User: @{buyer_username} (ID: {buyer_id})\n💰 Amount: {amount:,} MMK\n🆔 Request ID: {tx_id}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve Top-up", callback_data=f"approve_topup_{tx_id}")],
                [InlineKeyboardButton("❌ Reject", callback_data=f"reject_topup_{tx_id}")]
            ]),
            parse_mode="Markdown"
        )
    await update.message.reply_text(f"✅ သင်၏ Top-up Slip ကို လက်ခံရရှိပါပြီ။\n💰 ပမာဏ: {amount:,} MMK\n🆔 Request ID: {tx_id}\n⏳ Admin အတည်ပြုချက်ကို စောင့်ဆိုင်းပေးပါ။", parse_mode="Markdown")
    context.user_data.clear()

# ==================== RECEIVE PAYMENT SLIP ====================
async def receive_payment_slip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Payment Slip ကိုလက်ခံပါ (ပုံမှန် Order အတွက်)"""
    if context.user_data.get('awaiting_topup_slip', False):
        await receive_topup_slip(update, context)
        return
    if not context.user_data.get('awaiting_slip', False):
        await update.message.reply_text("⏳ ကျေးဇူးပြု၍ ငွေပေးချေမှုကို အတည်ပြုနေပါသည်...")
        context.user_data['awaiting_slip'] = True
    if not update.message.photo:
        await update.message.reply_text("❌ ကျေးဇူးပြု၍ Photo (Screenshot) ကိုသာ တင်ပေးပါ။")
        return
    photo = update.message.photo[-1]
    buyer_id = update.message.chat_id
    buyer_username = update.message.from_user.username or "NoUsername"
    product_id = context.user_data.get('product_id')
    quantity = context.user_data.get('bulk_quantity', 1)
    if not product_id:
        product = crud.get_active_product()
        if not product:
            await update.message.reply_text("❌ လက်ရှိ ရောင်းချရန် ကုန်ပစ္စည်း မရှိပါ။")
            return
        product_id = product.id
    product = crud.get_product(product_id)
    if not product:
        await update.message.reply_text("❌ Product မတွေ့ပါ။")
        return
    order = crud.create_order(buyer_id, buyer_username, product.id, quantity, "slip", photo.file_id)
    context.user_data['awaiting_slip'] = False
    for admin_id in ADMIN_IDS:
        await context.bot.send_photo(
            chat_id=admin_id,
            photo=photo.file_id,
            caption=f"📥 **New Slip Payment Request**\n🆔 Order ID: `{order.id}`\n👤 Buyer: @{buyer_username}\n📦 Quantity: {quantity} ခု\n💵 Total: {quantity * (product.price or 1000)} MMK",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve & Deliver", callback_data=f"approve_order_{order.id}")]
            ]),
            parse_mode="Markdown"
        )
    await update.message.reply_text(
        f"✅ သက်သေခံပုံကို လက်ခံရရှိပါပြီ။\n🆔 Order ID: `{order.id}`\n⏳ Admin အတည်ပြုချက်ကို စောင့်ဆိုင်းပေးပါ။",
        parse_mode="Markdown"
    )

# ==================== ADMIN APPROVE SLIP ====================
async def admin_approve_slip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if "topup" in query.data:
        return
    try:
        parts = query.data.split("_")
        order_id = int(parts[2])
        logger.info(f"✅ Approving order: {order_id}")
    except (IndexError, ValueError) as e:
        logger.error(f"❌ Error parsing order_id from {query.data}: {e}")
        await query.answer("❌ Order ID မှားနေပါသည်။", show_alert=True)
        return
    order = crud.get_order(order_id)
    if not order:
        await query.answer("❌ Order မတွေ့ပါ။", show_alert=True)
        return
    product = crud.get_product(order.product_id)
    if not product:
        await query.answer("❌ Product မတွေ့ပါ။", show_alert=True)
        return
    quantity = order.quantity or 1
    try:
        await query.edit_message_caption(
            caption=f"✅ Order `{order_id}` ကို အတည်ပြုပြီးပါပြီ။\n📦 {quantity} ခုကို ဝယ်သူဆီ ပို့ပြီးပါပြီ။",
            parse_mode="Markdown"
        )
    except:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ Order `{order_id}` ကို အတည်ပြုပြီးပါပြီ။\n📦 {quantity} ခုကို ဝယ်သူဆီ ပို့ပြီးပါပြီ။",
            parse_mode="Markdown"
        )
    crud.update_order_status(order_id, "paid")
    await send_delivery(context, order.buyer_id, order.buyer_username, product, quantity, "📸 Slip", order.id)

# ==================== SEND DELIVERY ====================
async def send_delivery(context, buyer_id, buyer_username, product, quantity, payment_method, order_id):
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

# ==================== GET OTP CODE ====================
async def get_otp_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ OTP ကိုရှာနေပါသည်...")
    if not check_rate_limit(update.effective_user.id, "get_otp"):
        await query.edit_message_text("⏳ ကျေးဇူးပြု၍ စက္ကန့် ၆၀ စောင့်ပါ။", reply_markup=get_otp_result_keyboard(order_id))
        return
    try:
        order_id = int(query.data.split("_")[2])
    except:
        await query.edit_message_text("❌ Order ID မှားနေပါသည်။")
        return
    order = crud.get_order(order_id)
    if not order:
        await query.edit_message_text("❌ Order မတွေ့ပါ။")
        return
    product = crud.get_product(order.product_id)
    if not product:
        await query.edit_message_text("❌ Product မတွေ့ပါ။")
        return
    if not product.file_path or not os.path.exists(product.file_path):
        await query.edit_message_text("❌ Session ဖိုင် မတွေ့ပါ။", reply_markup=get_otp_result_keyboard(order_id))
        return
    try:
        otp_code = await fetch_otp_from_777000(product.file_path)
    except Exception as e:
        await query.answer(f"❌ OTP ရယူရာတွင် အမှားရှိသည်: {str(e)[:50]}", show_alert=True)
        return
    try:
        await query.message.delete()
    except:
        pass
    if otp_code:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🔑 **OTP Code**: `{otp_code}`\n\n📱 Phone: `{os.path.splitext(product.name)[0]}`\n\nဤ Code ကို သုံးပြီး Telegram သို့ ဝင်ရောက်ပါ။\nဝင်ရောက်ပြီးပါက '✅ Login Success' ကိုနှိပ်ပါ။",
            reply_markup=get_otp_result_keyboard(order_id),
            parse_mode="Markdown"
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ **OTP ကို ရှာမတွေ့ပါ။**\n\nအကြောင်းရင်းများ:\n1️⃣ သင်သည် ဤနံပါတ်ဖြင့် Login မလုပ်ရသေးပါ။\n2️⃣ 777000 မှ Code ကို မပို့ရသေးပါ။\n\n💡 ကျေးဇူးပြု၍ Admin ကို ဆက်သွယ်ပါ။",
            reply_markup=get_otp_result_keyboard(order_id),
            parse_mode="Markdown"
        )

# ==================== ✅ LOGIN SUCCESS (ပြင်ဆင်ပြီး - New login မစစ်တော့ဘူး) ====================
async def login_success(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ဝယ်သူက Login Success နှိပ်ရင် New login စာသားမစစ်ဘဲ ချက်ချင်းဖျက်ပါ"""
    query = update.callback_query
    await query.answer("⏳ အကောင့်ဝင်မှုကို အတည်ပြုနေပါသည်...")
    
    order_id = context.user_data.get('temp_order_id')
    product_id = context.user_data.get('temp_product_id')
    phone = context.user_data.get('temp_phone', '')
    
    if not order_id:
        await query.edit_message_text("❌ Order မတွေ့ပါ။")
        return
    
    # ✅ Order ကို Completed ပြောင်းပါ
    crud.update_order_login_status(order_id, 1)
    
    # ✅ Session ဖိုင်နဲ့ DB Record ကို ချက်ချင်းဖျက်ပါ
    if product_id:
        crud.permanently_delete_product(product_id)
        logger.info(f"🗑️ Product #{product_id} permanently deleted after login success")
    
    # ✅ Referral Bonus ကို စစ်ဆေးပြီး ထည့်ပေးပါ
    buyer_id = update.effective_user.id
    referrer_id = crud.apply_referral_bonus(buyer_id)
    if referrer_id:
        await context.bot.send_message(
            chat_id=referrer_id,
            text=f"🎉 **Referral Bonus!**\n\nသင် ခေါ်လာတဲ့ သူငယ်ချင်း ဝယ်ယူမှု အောင်မြင်သွားပါပြီ။\n💰 သင့် Wallet ထဲကို 5 MMK ထည့်သွင်းပြီးပါပြီ။",
            parse_mode="Markdown"
        )
    
    context.user_data.clear()
    
    await query.edit_message_text(
        f"✅ **Login အောင်မြင်ပြီး အတည်ပြုပြီးပါပြီ။**\n\n📱 Phone: `{phone}`\n\n🔒 ဤ Session ကို လုံခြုံစွာ သိမ်းဆည်းထားပါ။",
        parse_mode="Markdown"
    )

# ==================== MY ORDERS ====================
async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    orders = crud.get_orders_by_buyer(user_id, limit=10)
    if not orders:
        await query.edit_message_text(
            "📊 **My Orders**\n\nသင်၏ Order မရှိသေးပါ။",
            reply_markup=get_back_button(),
            parse_mode="Markdown"
        )
        return
    text = "📊 **My Orders**\n\n"
    for order in orders:
        status_emoji = "⏳" if order.status == "pending" else "✅" if order.status == "delivered" else "🔐" if order.status == "login_required" else "📦" if order.status == "paid" else "✔️"
        text += f"{status_emoji} Order #{order.id} | {order.payment_method} | {order.status}\n"
    text += "\n📌 **Status Legend:**\n"
    text += "⏳ Pending = Admin အတည်ပြုချက်ကို စောင့်ဆိုင်းနေပါသည်\n"
    text += "📦 Paid = ငွေပေးချေပြီးပါပြီ\n"
    text += "🔐 Login Required = OTP ရယူရန် စောင့်ဆိုင်းနေပါသည်\n"
    text += "✅ Completed = Login အောင်မြင်ပြီး Session ကိုဖျက်ပြီးပါပြီ"
    await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="Markdown")
