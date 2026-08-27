from telegram import Update
from telegram.ext import ContextTypes
from database import crud
from bot.keyboards.inline import get_back_button, get_quantity_keyboard, get_payment_method_keyboard
from utils.rate_limiter import check_rate_limit

async def buy_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not check_rate_limit(update.effective_user.id, "buy"):
        await query.edit_message_text("⏳ ကျေးဇူးပြု၍ စက္ကန့် ၆၀ စောင့်ပါ။", reply_markup=get_back_button())
        return
    product = crud.get_active_product()
    if not product:
        await query.edit_message_text("❌ လက်ရှိ ရောင်းချရန် Session မရှိပါ။", reply_markup=get_back_button())
        return
    context.user_data['product_id'] = product.id
    await query.edit_message_text(f"📄 **Telegram Session**\n\n💰 Price per session: {product.price or 1000} MMK\n📦 ဘယ်နှစ်ခု ဝယ်ချင်လဲ ရွေးပါ။\n(၁-၅၀)",
        reply_markup=get_quantity_keyboard(), parse_mode="Markdown")

async def select_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data == "qty_custom":
        await query.answer()
        context.user_data['awaiting_custom_qty'] = True
        await query.edit_message_text("📝 **Custom Quantity**\n\nလိုချင်သော အရေအတွက် (၁-၅၀) ကို ရိုက်ထည့်ပါ။", reply_markup=get_back_button(), parse_mode="Markdown")
        return
    quantity = int(data.split("_")[1])
    await process_quantity(update, context, quantity, query)

async def receive_custom_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_custom_qty', False):
        return
    try:
        quantity = int(update.message.text.strip())
        if quantity < 1 or quantity > 50:
            await update.message.reply_text("❌ ၁ ခုမှ ၅၀ ခုအထိသာ ဝယ်လို့ရပါတယ်။")
            return
    except:
        await update.message.reply_text("❌ ဂဏန်းတစ်ခုသာ ရိုက်ထည့်ပါ။")
        return
    context.user_data['awaiting_custom_qty'] = False
    await process_quantity(update, context, quantity, None)

async def process_quantity(update, context, quantity, query=None):
    product_id = context.user_data.get('product_id')
    product = crud.get_product(product_id)
    if not product:
        msg = "❌ Product မတွေ့ပါ။ /start နှိပ်ပြီး ပြန်စပါ။"
        if query:
            await query.edit_message_text(msg, reply_markup=get_back_button())
        else:
            await update.message.reply_text(msg, reply_markup=get_back_button())
        return
    total_price = quantity * (product.price or 1000)
    context.user_data['bulk_quantity'] = quantity
    context.user_data['bulk_total'] = total_price
    text = f"🛒 **Order Summary**\n\n📦 Session: {product.name}\n📝 Quantity: {quantity} ခု\n💰 Unit Price: {product.price or 1000} MMK\n💵 Total Price: {total_price} MMK\n\nငွေပေးချေရန် နည်းလမ်းကို ရွေးပါ။"
    user_id = update.effective_user.id
    wallet_balance = crud.get_wallet_balance(user_id)
    if query:
        await query.edit_message_text(text, reply_markup=get_payment_method_keyboard(wallet_balance, total_price), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=get_payment_method_keyboard(wallet_balance, total_price), parse_mode="Markdown")

async def bulk_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not check_rate_limit(update.effective_user.id, "bulk_confirm"):
        await query.edit_message_text("⏳ ကျေးဇူးပြု၍ စက္ကန့် ၆၀ စောင့်ပါ။", reply_markup=get_back_button())
        return
    quantity = context.user_data.get('bulk_quantity', 1)
    product_id = context.user_data.get('product_id')
    total_price = context.user_data.get('bulk_total', 0)
    if not product_id:
        await query.edit_message_text("❌ Product မတွေ့ပါ။ /start နှိပ်ပြီး ပြန်စပါ။", reply_markup=get_back_button())
        return
    product = crud.get_product(product_id)
    if not product:
        await query.edit_message_text("❌ Product မတွေ့ပါ။", reply_markup=get_back_button())
        return
    context.user_data['awaiting_slip'] = True
    kbz = crud.get_kbz_number()
    wave = crud.get_wave_number()
    user_id = update.effective_user.id
    wallet_balance = crud.get_wallet_balance(user_id)
    text = f"💵 **{total_price} MMK ဖြင့် ငွေပေးချေရန်**\n\n📦 Quantity: {quantity} ခု\n💰 Total: {total_price} MMK\n\n🏦 KBZ Pay: `{kbz}`\n🏦 Wave Pay: `{wave}`\n\n📸 ငွေလွှဲပြီးပါက Screenshot (Photo) ကို ဤ Chat တွင် တိုက်ရိုက်တင်ပေးပါ။"
    if wallet_balance >= total_price:
        text += f"\n\n💰 သင်၏ Wallet Balance: {wallet_balance} MMK\n💡 Wallet ဖြင့် ချက်ချင်းပေးချေနိုင်ပါသည်။"
    await query.edit_message_text(text, reply_markup=get_payment_method_keyboard(wallet_balance, total_price), parse_mode="Markdown")
