from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.keyboards.inline import get_back_button
from database import crud

async def settings_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    settings = crud.get_all_settings_json()
    
    text = (
        f"⚙️ **Default Settings**\n\n"
        f"🔑 Default 2FA: `{settings.get('default_2fa', '123456')}`\n"
        f"💰 Default Price: {settings.get('default_price', '1000')} MMK\n\n"
        "ဤ Settings များကို Session Upload တိုင်းမှာ အသုံးပြုမည်။"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔑 Change Default 2FA", callback_data="settings_change_2fa")],
        [InlineKeyboardButton("💰 Change Default Price", callback_data="settings_change_price")],
        [InlineKeyboardButton("🏠 Back to Admin Panel", callback_data="admin_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def change_default_2fa_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['awaiting_default_2fa'] = True
    await query.edit_message_text(
        "🔑 **Change Default 2FA**\n\nဂဏန်း ၄-၈ လုံး ရိုက်ထည့်ပါ။",
        reply_markup=get_back_button(),
        parse_mode="Markdown"
    )

async def receive_default_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_default_2fa', False):
        return

    two_fa = update.message.text.strip()
    if not two_fa.isdigit() or len(two_fa) < 4:
        await update.message.reply_text("❌ ဂဏန်း ၄ လုံးထက်မနည်း ဖြစ်ရပါမည်။")
        return

    crud.update_setting('default_2fa', two_fa)
    context.user_data.clear()
    await update.message.reply_text(
        f"✅ Default 2FA ကို `{two_fa}` သို့ အောင်မြင်စွာ ပြောင်းလဲပြီးပါပြီ။",
        parse_mode="Markdown"
    )

async def change_default_price_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['awaiting_default_price'] = True
    await query.edit_message_text(
        "💰 **Change Default Price**\n\nPrice (MMK) ကို ရိုက်ထည့်ပါ။",
        reply_markup=get_back_button(),
        parse_mode="Markdown"
    )

async def receive_default_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_default_price', False):
        return

    try:
        price = int(update.message.text.strip())
        if price < 100:
            await update.message.reply_text("❌ အနည်းဆုံး 100 MMK ဖြစ်ရပါမည်။")
            return
    except:
        await update.message.reply_text("❌ ဂဏန်းတစ်ခုသာ ရိုက်ထည့်ပါ။")
        return

    crud.update_setting('default_price', str(price))
    context.user_data.clear()
    await update.message.reply_text(
        f"✅ Default Price ကို {price} MMK သို့ အောင်မြင်စွာ ပြောင်းလဲပြီးပါပြီ။"
    )
