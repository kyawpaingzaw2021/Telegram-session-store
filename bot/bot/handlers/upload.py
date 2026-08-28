import os
from telegram import Update
from telegram.ext import ContextTypes
from bot.config import is_admin
from bot.keyboards.inline import get_back_button
from database import crud

# /tmp အောက်သို့ ပြောင်းလဲထားပါသည် (Permission error ရှင်းရန်)
SESSION_DIR = "/tmp/sessions"
if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR, exist_ok=True)
DOWNLOAD_TIMEOUT = 300

async def admin_upload_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        await query.answer("ခွင့်ပြုချက်မရှိပါ။", show_alert=True)
        return
    context.user_data['awaiting_upload'] = True
    await query.edit_message_text(
        "📤 `.session` ဖိုင်ကို တင်ပေးပါ။\n\n"
        "⚠️ ဖိုင်ကြီးပါက စက္ကန့် ၆၀ ခန့် စောင့်ဆိုင်းရနိုင်ပါသည်။",
        reply_markup=get_back_button()
    )

async def receive_uploaded_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("ခွင့်ပြုချက်မရှိပါ။")
        return
    if not context.user_data.get('awaiting_upload', False):
        await update.message.reply_text("⏳ ကျေးဇူးပြု၍ 'Upload' ခလုတ်မှ ပြန်လည်စတင်ပါ။")
        return
    document = update.message.document
    if not document or not document.file_name.endswith('.session'):
        await update.message.reply_text("❌ `.session` ဖိုင်ကိုသာ တင်ပေးပါ။")
        return
    status_msg = await update.message.reply_text(f"⏳ `{document.file_name}` ကို ဒေါင်းလုဒ်ဆွဲနေပါသည်...")
    
    file_path = "" # Exception အတွက် ကြိုတင်သတ်မှတ်ခြင်း
    try:
        file = await context.bot.get_file(
            document.file_id,
            read_timeout=DOWNLOAD_TIMEOUT,
            write_timeout=DOWNLOAD_TIMEOUT,
            connect_timeout=DOWNLOAD_TIMEOUT
        )
        file_name = document.file_name
        file_path = os.path.join(SESSION_DIR, file_name)
        await file.download_to_drive(file_path)
        default_2fa = crud.get_default_2fa()
        default_price = crud.get_default_price()
        product = crud.create_product(
            name=file_name,
            file_id=document.file_id,
            two_fa_plain=default_2fa,
            price=default_price,
            file_path=file_path
        )
        context.user_data['awaiting_upload'] = False
        context.user_data.clear()
        await status_msg.edit_text(
            f"✅ **အောင်မြင်ပါပြီ။**\n\n"
            f"📄 File: `{file_name}`\n"
            f"🔑 2FA: `{default_2fa}` (Default)\n"
            f"💰 Price: {default_price} MMK (Default)\n"
            f"📊 Status: ✅ Active\n\n"
            f"🆔 Product ID: `{product.id}`\n\n"
            f"ဝယ်သူများ ယခု `🛒 Buy Session` မှ ဝယ်ယူနိုင်ပါပြီ။",
            reply_markup=get_back_button(),
            parse_mode="Markdown"
        )
    except Exception as e:
        await status_msg.edit_text(
            f"❌ **ဖိုင်ဒေါင်းလုဒ် မအောင်မြင်ပါ။**\n\n"
            f"Error: {str(e)[:200]}",
            reply_markup=get_back_button(),
            parse_mode="Markdown"
        )
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
