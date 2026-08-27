from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.keyboards.inline import get_main_menu_keyboard, get_back_button
from bot.config import ADMIN_IDS, REFERRAL_BONUS

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("🏠 **Main Menu**\n\nကြိုဆိုပါတယ်။ အောက်ပါခလုတ်များထဲမှ တစ်ခုကို ရွေးပါ။",
            reply_markup=get_main_menu_keyboard(update.effective_user.id), parse_mode="Markdown")
    else:
        await update.message.reply_text("🏠 **Main Menu**\n\nကြိုဆိုပါတယ်။ အောက်ပါခလုတ်များထဲမှ တစ်ခုကို ရွေးပါ။",
            reply_markup=get_main_menu_keyboard(update.effective_user.id), parse_mode="Markdown")

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Returning to menu...")
    context.user_data.clear()
    await query.edit_message_text("🏠 **Main Menu**\n\nကြိုဆိုပါတယ်။ အောက်ပါခလုတ်များထဲမှ တစ်ခုကို ရွေးပါ။",
        reply_markup=get_main_menu_keyboard(update.effective_user.id), parse_mode="Markdown")

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("ℹ️ **Rules & Information**\n\n1. ဤ Session သည် တစ်ကြိမ်သာ အသုံးပြုရန်ဖြစ်သည်။\n2. 2FA Password ကို လုံခြုံစွာ သိမ်းဆည်းပါ။\n3. ငွေလွှဲပြီးပါက Screenshot တင်ရန် မမေ့ပါနှင့်။\n4. Admin မှ အတည်ပြုပြီးမှသာ ဆက်လက်လုပ်ဆောင်နိုင်မည်။\n5. Wallet System ဖြင့် ငွေကြိုသွင်းထားပြီး Auto Purchase ပြုလုပ်နိုင်သည်။\n6. သူငယ်ချင်းများကို ခေါ်လာပါက ဘောနပ်စ်ရရှိမည်။",
        reply_markup=get_back_button(), parse_mode="Markdown")

async def invite_friend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Invite Friend Button Handler"""
    query = update.callback_query
    if query:
        await query.answer()
    user_id = update.effective_user.id
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    text = (
        f"📤 **Invite Friend**\n\n"
        f"သင်၏ Invite Link:\n`{link}`\n\n"
        f"ဤ Link ကို သုံးပြီး သူငယ်ချင်းများ Bot ကို Join လာပါက "
        f"သူတို့ ပထမဆုံး ဝယ်ယူမှု ပြီးသွားတိုင်း သင့် Wallet ထဲကို **{REFERRAL_BONUS} MMK** ထည့်ပေးပါမည်။"
    )
    if query:
        await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=get_back_button(), parse_mode="Markdown")

async def send_message_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send Message ကိုနှိပ်ရင် Prompt ပြရန်"""
    query = update.callback_query
    await query.answer()
    context.user_data['awaiting_user_message'] = True
    await query.edit_message_text(
        "💬 **Send Message to Admin**\n\n"
        "Admin ကို ပို့လိုသော စာသားကို ရိုက်ထည့်ပါ။\n\n"
        "(ဥပမာ - ကျွန်တော် OTP မရပါ။ ကူညီပေးပါ။)",
        reply_markup=get_back_button(),
        parse_mode="Markdown"
    )

async def receive_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User က Message ရိုက်ထည့်လိုက်ရင် Admin ဆီပို့ရန်"""
    if not context.user_data.get('awaiting_user_message', False):
        return
    
    message_text = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.username or "NoUsername"
    
    for admin_id in ADMIN_IDS:
        await context.bot.send_message(
            chat_id=admin_id,
            text=(
                f"📩 **New Message from User**\n\n"
                f"👤 User: @{username} (ID: `{user_id}`)\n"
                f"📝 Message:\n{message_text}"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📩 Reply", callback_data=f"reply_user_{user_id}")]
            ]),
            parse_mode="Markdown"
        )
    
    context.user_data['awaiting_user_message'] = False
    await update.message.reply_text(
        "✅ သင်၏ Message ကို Admin ထံ ပေးပို့ပြီးပါပြီ။\n"
        "⏳ Admin မှ ပြန်လည်ဖြေကြားပါလိမ့်မည်။",
        reply_markup=get_back_button()
    )
