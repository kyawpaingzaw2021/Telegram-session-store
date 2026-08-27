import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.config import is_admin, ADMIN_IDS
from database import crud
from bot.keyboards.inline import (
    get_admin_menu_keyboard, get_back_button, get_back_to_admin_button,
    get_health_result_keyboard, get_confirm_delete_keyboard,
    get_confirm_delete_inactive_keyboard, get_wallet_manage_keyboard,
    get_sync_activate_keyboard, get_reset_all_keyboard, get_cleanup_confirm_keyboard,
    get_clear_orders_confirm_keyboard, get_user_list_keyboard
)
from utils.otp_fetcher import check_session_health
from utils.rate_limiter import check_rate_limit

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        if update.callback_query:
            await update.callback_query.answer("ခွင့်ပြုချက်မရှိပါ။", show_alert=True)
        else:
            await update.message.reply_text("⛔ ခွင့်ပြုချက်မရှိပါ။")
        return
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("🛠️ **Admin Panel**\n\nအောက်ပါခလုတ်များထဲမှ တစ်ခုကို ရွေးပါ။",
                                      reply_markup=get_admin_menu_keyboard(), parse_mode="Markdown")
    else:
        await update.message.reply_text("🛠️ **Admin Panel**\n\nအောက်ပါခလုတ်များထဲမှ တစ်ခုကို ရွေးပါ။",
                                        reply_markup=get_admin_menu_keyboard(), parse_mode="Markdown")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    total_orders = crud.get_total_orders()
    total_mmk = crud.get_total_mmk_income()
    total_wallet = crud.get_total_wallet_income()
    today_orders = crud.get_today_orders()
    pending_orders = crud.get_pending_orders()
    text = f"📊 **Statistics**\n\n📦 **စုစုပေါင်း Order**: {total_orders}\n💵 **MMK ဝင်ငွေ (Slip)**: {total_mmk:,} MMK\n💰 **Wallet ဝင်ငွေ**: {total_wallet:,} MMK\n📅 **ယနေ့ Order**: {today_orders}\n⏳ **စောင့်ဆိုင်းနေသော Order**: {pending_orders}\n"
    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats")],
                [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    orders = crud.get_recent_orders(limit=10)
    if not orders:
        text = "📋 **Orders**\n\nOrder မရှိသေးပါ။"
    else:
        text = "📋 **Recent Orders (Last 10)**\n\n"
        for order in orders:
            emoji = "⏳" if order.status == "pending" else "✅" if order.status == "delivered" else "🔐" if order.status == "login_required" else "📦" if order.status == "paid" else "✔️"
            text += f"{emoji} Order #{order.id} | @{order.buyer_username} | {order.payment_method} | {order.status}\n"
    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="admin_orders")],
                [InlineKeyboardButton("🔍 Order Details", callback_data="admin_order_detail")],
                [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin_order_detail_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['awaiting_order_id'] = True
    await query.edit_message_text("🔍 **Order Detail**\n\nကြည့်ရှုလိုသော **Order ID** ကို ရိုက်ထည့်ပါ။",
                                  reply_markup=get_back_button(), parse_mode="Markdown")

async def receive_order_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_order_id', False):
        return
    try:
        order_id = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ ဂဏန်းတစ်ခုသာ ရိုက်ထည့်ပါ။")
        return
    order = crud.get_order(order_id)
    if not order:
        await update.message.reply_text(f"❌ Order #{order_id} မတွေ့ပါ။")
        context.user_data['awaiting_order_id'] = False
        return
    product = crud.get_product(order.product_id)
    product_name = product.name if product else "Unknown"
    two_fa = crud.decrypt_2fa(product.encrypted_2fa) if product else "N/A"
    text = f"🔍 **Order Detail**\n\n🆔 Order ID: `{order.id}`\n👤 Buyer: @{order.buyer_username} (ID: `{order.buyer_id}`)\n📄 Product: {product_name}\n💳 Method: {order.payment_method}\n📅 Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}\n📊 Status: {order.status}\n🔑 2FA: `{two_fa}`\n📸 Slip: {'✅' if order.slip_file_id else '❌'}\n"
    context.user_data['awaiting_order_id'] = False
    await update.message.reply_text(text, parse_mode="Markdown")

async def admin_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    products = [p for p in crud.get_all_products() if p.is_active == 1]
    if not products:
        text = "📦 **Active Products**\n\nActive Product မရှိသေးပါ။\n\n💡 '🔄 Sync & Activate All' ကိုနှိပ်ပြီး ပြန်လည်အသက်သွင်းပါ။"
    else:
        text = "📦 **Active Products List**\n\n"
        for product in products:
            text += f"🆔 #{product.id} | {product.name} | {product.price} MMK | ✅ Active\n"
    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="admin_products")],
                [InlineKeyboardButton("❌ Deactivate", callback_data="admin_deactivate")],
                [InlineKeyboardButton("🗑 Delete Permanently", callback_data="admin_delete_permanent")],
                [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    products = crud.get_all_products()
    active = [p for p in products if p.is_active == 1]
    inactive = [p for p in products if p.is_active == 0]
    text = f"📦 **Stock (လက်ကျန်)**\n\n✅ Active Sessions: `{len(active)}`\n❌ Inactive Sessions: `{len(inactive)}`\n📦 Total: `{len(products)}`\n\n"
    if active:
        text += "━━━ Active ━━━\n"
        for p in active[:5]:
            text += f"• {p.name} | {p.price} MMK\n"
        if len(active) > 5:
            text += f"... and {len(active) - 5} more\n"
    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="admin_stock")],
                [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin_sync_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔄 **Sync & Activate All**\n\n"
        "Session Folder ထဲက `.session` ဖိုင်တွေကို စစ်ဆေးပြီး:\n"
        "• DB ထဲမှာ Record မရှိရင် အသစ်ဖန်တီးမယ်\n"
        "• Record ရှိပြီးသားဆိုရင် Active ပြန်ဖြစ်အောင်လုပ်မယ်\n\n"
        "ဆက်လက်လုပ်ဆောင်ရန် '✅ Yes, Sync & Activate' ကိုနှိပ်ပါ။",
        reply_markup=get_sync_activate_keyboard(),
        parse_mode="Markdown"
    )

async def admin_confirm_sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ စစ်ဆေးနေပါသည်...")
    session_dir = "sessions"
    if not os.path.exists(session_dir):
        await query.edit_message_text("❌ `sessions/` folder မရှိပါ။", reply_markup=get_back_to_admin_button())
        return
    session_files = [f for f in os.listdir(session_dir) if f.endswith('.session')]
    if not session_files:
        await query.edit_message_text("❌ `sessions/` folder ထဲမှာ `.session` ဖိုင်မရှိပါ။", reply_markup=get_back_to_admin_button())
        return
    created, activated, total = 0, 0, len(session_files)
    for sf in session_files:
        file_path = os.path.join(session_dir, sf)
        existing = None
        for p in crud.get_all_products():
            if p.file_path and os.path.basename(p.file_path) == sf:
                existing = p
                break
        if existing:
            if existing.is_active == 0:
                crud.activate_product(existing.id)
                activated += 1
        else:
            phone = sf.replace('.session', '')
            default_2fa = crud.get_default_2fa()
            default_price = crud.get_default_price()
            crud.create_product(name=sf, file_id="sync_created", two_fa_plain=default_2fa, price=default_price, file_path=file_path)
            created += 1
    text = f"✅ **Sync & Activate Complete!**\n\n📁 Total Session Files: {total}\n🆕 New Records Created: {created}\n🔄 Reactivated: {activated}\n\n📌 Active Products များကို '📦 Active Products' မှာ ကြည့်ပါ။"
    await query.edit_message_text(text, reply_markup=get_back_to_admin_button(), parse_mode="Markdown")

async def admin_reset_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🗑️ **Reset All & Clean**\n\n"
        "⚠️ **သတိပြုရန်:**\n"
        "• Database ထဲက Product Record အကုန်ဖျက်မယ်\n"
        "• Session Folder ထဲက `.session` ဖိုင်အကုန်ဖျက်မယ်\n"
        "• ဤလုပ်ဆောင်ချက်ကို ပြန်လည်ဖျက်သိမ်း၍မရပါ။",
        reply_markup=get_reset_all_keyboard(),
        parse_mode="Markdown"
    )

async def admin_confirm_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ ဖျက်နေပါသည်...")
    session_dir = "sessions"
    products = crud.get_all_products()
    deleted_db = 0
    for product in products:
        if crud.permanently_delete_product(product.id):
            deleted_db += 1
    deleted_files = 0
    if os.path.exists(session_dir):
        for f in os.listdir(session_dir):
            if f.endswith('.session'):
                os.remove(os.path.join(session_dir, f))
                deleted_files += 1
    text = f"🗑️ **Reset & Clean Complete!**\n\n🗑️ DB Records Deleted: {deleted_db}\n🗑️ Session Files Deleted: {deleted_files}\n\n📌 ယခု '📤 Upload Session' နဲ့ Session အသစ်တင်ပါ။"
    await query.edit_message_text(text, reply_markup=get_back_to_admin_button(), parse_mode="Markdown")

async def admin_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    products = crud.get_all_products()
    orphaned = [p for p in products if p.file_path and not os.path.exists(p.file_path)]
    if not orphaned:
        await query.edit_message_text("🧹 **Orphaned Records မရှိပါ။**", reply_markup=get_back_to_admin_button())
        return
    text = f"🧹 **Orphaned Records တွေ့ရှိပါပြီ။**\n\n📦 ဖျက်မည့် Record အရေအတွက်: `{len(orphaned)}`"
    await query.edit_message_text(text, reply_markup=get_cleanup_confirm_keyboard(), parse_mode="Markdown")

async def admin_confirm_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ ရှင်းလင်းနေပါသည်...")
    products = crud.get_all_products()
    orphaned = [p for p in products if p.file_path and not os.path.exists(p.file_path)]
    deleted_count = 0
    for product in orphaned:
        if crud.permanently_delete_product(product.id):
            deleted_count += 1
    await query.edit_message_text(f"🧹 **Orphaned Records များကို အောင်မြင်စွာ ရှင်းလင်းပြီးပါပြီ။**\n\n🗑️ ဖျက်ပြီးသော Record: {deleted_count}",
                                  reply_markup=get_back_to_admin_button(), parse_mode="Markdown")

async def admin_delete_inactive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    inactive = [p for p in crud.get_all_products() if p.is_active == 0]
    if not inactive:
        await query.edit_message_text("❌ Inactive Product မရှိပါ။", reply_markup=get_back_to_admin_button())
        return
    text = f"🗑️ **Inactive Products များကို အပြီးအပိုင် ဖျက်တော့မည်။**\n\n📦 ဖျက်မည့် Product အရေအတွက်: `{len(inactive)}`"
    await query.edit_message_text(text, reply_markup=get_confirm_delete_inactive_keyboard(), parse_mode="Markdown")

async def admin_confirm_delete_inactive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ ဖျက်နေပါသည်...")
    inactive = [p for p in crud.get_all_products() if p.is_active == 0]
    deleted_count = 0
    for product in inactive:
        if crud.permanently_delete_product(product.id):
            deleted_count += 1
    await query.edit_message_text(f"✅ **Inactive Products များကို အောင်မြင်စွာ ဖျက်ပြီးပါပြီ။**\n\n🗑️ ဖျက်ပြီးသော Product: {deleted_count}",
                                  reply_markup=get_back_to_admin_button(), parse_mode="Markdown")

async def admin_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ Session များကို စစ်ဆေးနေပါသည်...")
    products = [p for p in crud.get_all_products() if p.is_active == 1]
    if not products:
        await query.edit_message_text("📦 Active Session မရှိသေးပါ။", reply_markup=get_back_to_admin_button())
        return
    health_results, bad_sessions, good_sessions = [], [], []
    for product in products:
        if not product.file_path or not os.path.exists(product.file_path):
            health_results.append(f"❌ {product.name} | File not found")
            bad_sessions.append(product)
            continue
        if await check_session_health(product.file_path):
            health_results.append(f"✅ {product.name} | Healthy")
            good_sessions.append(product)
        else:
            health_results.append(f"❌ {product.name} | Invalid/Expired")
            bad_sessions.append(product)
    text = f"🩺 **Session Health Check**\n\n✅ Healthy: {len(good_sessions)}\n❌ Bad: {len(bad_sessions)}\n📦 Total: {len(products)}\n\n━━━━━━━━━━━━━━━━━━━━\n"
    for result in health_results[:10]: text += f"{result}\n"
    if len(health_results) > 10: text += f"... and {len(health_results) - 10} more\n"
    if bad_sessions:
        text += f"\n⚠️ Bad sessions: {len(bad_sessions)}"
        await query.edit_message_text(text, reply_markup=get_health_result_keyboard(), parse_mode="Markdown")
        context.user_data['bad_sessions'] = [p.id for p in bad_sessions]
    else:
        await query.edit_message_text(text + "\n\n✅ All sessions are healthy!", reply_markup=get_back_to_admin_button(), parse_mode="Markdown")

async def admin_delete_bad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bad_sessions = context.user_data.get('bad_sessions', [])
    if not bad_sessions:
        await query.edit_message_text("❌ ဖျက်စရာ Bad Session မရှိပါ။", reply_markup=get_back_to_admin_button())
        return
    text = f"⚠️ **Bad Sessions များကို အပြီးအပိုင် ဖျက်တော့မည်။**\n\n📦 ဖျက်မည့် Session အရေအတွက်: `{len(bad_sessions)}`"
    await query.edit_message_text(text, reply_markup=get_confirm_delete_keyboard(), parse_mode="Markdown")

async def admin_confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ ဖျက်နေပါသည်...")
    bad_sessions = context.user_data.get('bad_sessions', [])
    deleted_count = 0
    for product_id in bad_sessions:
        if crud.permanently_delete_product(product_id):
            deleted_count += 1
    context.user_data['bad_sessions'] = []
    await query.edit_message_text(f"✅ **Bad Sessions များကို အောင်မြင်စွာ ဖျက်ပြီးပါပြီ။**\n\n🗑️ ဖျက်ပြီးသော Session: {deleted_count}",
                                  reply_markup=get_back_to_admin_button(), parse_mode="Markdown")

async def admin_delete_permanent_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['awaiting_delete_permanent'] = True
    await query.edit_message_text("🗑️ **Delete Product (Permanent)**\n\nဖျက်ပစ်လိုသော **Product ID** ကို ရိုက်ထည့်ပါ။",
                                  reply_markup=get_back_button(), parse_mode="Markdown")

async def receive_delete_permanent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_delete_permanent', False):
        return
    try:
        product_id = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ ဂဏန်းတစ်ခုသာ ရိုက်ထည့်ပါ။")
        return
    product = crud.get_product(product_id)
    if not product:
        await update.message.reply_text(f"❌ Product #{product_id} မတွေ့ပါ။")
        context.user_data['awaiting_delete_permanent'] = False
        return
    if crud.permanently_delete_product(product_id):
        context.user_data['awaiting_delete_permanent'] = False
        await update.message.reply_text(f"✅ **Product #{product_id} ကို အောင်မြင်စွာ ဖျက်ပစ်လိုက်ပါပြီ။**", parse_mode="Markdown")

async def admin_deactivate_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['awaiting_deactivate'] = True
    await query.edit_message_text("❌ **Deactivate Product**\n\nProduct ID ကို ရိုက်ထည့်ပါ။",
                                  reply_markup=get_back_button(), parse_mode="Markdown")

async def receive_deactivate_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_deactivate', False):
        return
    try:
        product_id = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ ဂဏန်းတစ်ခုသာ ရိုက်ထည့်ပါ။")
        return
    product = crud.get_product(product_id)
    if not product:
        await update.message.reply_text(f"❌ Product #{product_id} မတွေ့ပါ။")
        context.user_data['awaiting_deactivate'] = False
        return
    crud.deactivate_product(product_id)
    context.user_data['awaiting_deactivate'] = False
    await update.message.reply_text(f"✅ Product #{product_id} (`{product.name}`) ကို ပိတ်ပစ်လိုက်ပါပြီ။", parse_mode="Markdown")

async def admin_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    wallets = crud.get_all_wallets()
    text = "👛 **Manage Wallets**\n\n"
    if wallets:
        for w in wallets[:10]:
            text += f"👤 ID: {w.user_id} | {w.balance:,} MMK\n"
        if len(wallets) > 10:
            text += f"... and {len(wallets) - 10} more\n"
    else:
        text += "Wallet မရှိသေးပါ။\n"
    await query.edit_message_text(text, reply_markup=get_wallet_manage_keyboard(), parse_mode="Markdown")

async def admin_add_balance_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['awaiting_add_balance'] = True
    await query.edit_message_text("➕ **Add Balance**\n\nUser ID နဲ့ ပမာဏကို ရိုက်ထည့်ပါ။\n\nပုံစံ: `{user_id} {amount}`", reply_markup=get_back_button(), parse_mode="Markdown")

async def receive_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_add_balance', False):
        return
    try:
        parts = update.message.text.strip().split()
        user_id = int(parts[0])
        amount = int(parts[1])
        if amount <= 0:
            await update.message.reply_text("❌ ပမာဏသည် 0 ထက်ကြီးရပါမည်။")
            return
    except:
        await update.message.reply_text("❌ `{user_id} {amount}` ပုံစံအတိုင်း ရိုက်ထည့်ပါ။")
        return
    new_balance = crud.add_wallet_balance(user_id, amount, "admin_add", None)
    context.user_data['awaiting_add_balance'] = False
    await update.message.reply_text(f"✅ User {user_id} ရဲ့ Wallet ထဲကို {amount:,} MMK ထည့်သွင်းပြီးပါပြီ။\n💰 လက်ရှိလက်ကျန်: {new_balance:,} MMK")

async def admin_reset_wallet_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['awaiting_reset_wallet'] = True
    await query.edit_message_text(
        "🗑️ **Reset User Wallet**\n\n"
        "ဖျက်ပစ်လိုသော **User ID** (Telegram ID) ကို ရိုက်ထည့်ပါ။\n\n"
        "⚠️ **သတိပြုရန်:**\n"
        "- ဤ User ၏ Wallet Balance နဲ့ Transaction မှတ်တမ်းအကုန်လုံး ဖျက်ပစ်မည်။",
        reply_markup=get_back_button(),
        parse_mode="Markdown"
    )

async def receive_reset_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_reset_wallet', False):
        return
    try:
        user_id = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ ဂဏန်းတစ်ခုသာ ရိုက်ထည့်ပါ။")
        return
    crud.reset_user_wallet(user_id)
    context.user_data['awaiting_reset_wallet'] = False
    await update.message.reply_text(f"✅ User `{user_id}` ရဲ့ Wallet Data ကို အောင်မြင်စွာ ဖျက်ပစ်လိုက်ပါပြီ။", parse_mode="Markdown")

async def admin_clear_orders_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🗑️ **Clear All Orders**\n\n"
        "⚠️ **သတိပြုရန်:**\n"
        "- Order အကုန်လုံးကို အပြီးအပိုင် ဖျက်ပစ်မည်။\n"
        "- ပြန်လည်ဖျက်သိမ်း၍မရပါ။\n"
        "- Wallet Data နဲ့ Product Data ကို မထိခိုက်ပါ။",
        reply_markup=get_clear_orders_confirm_keyboard(),
        parse_mode="Markdown"
    )

async def admin_confirm_clear_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ ဖျက်နေပါသည်...")
    total = crud.get_total_orders()
    crud.clear_all_orders()
    await query.edit_message_text(
        f"🗑️ **Clear All Orders Complete!**\n\n"
        f"🗑️ ဖျက်ပြီးသော Order: {total}",
        reply_markup=get_back_to_admin_button(),
        parse_mode="Markdown"
    )

# ==================== USER LIST ====================
async def admin_user_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    users = crud.get_all_users()
    if not users:
        await query.edit_message_text("👥 **User List**\n\nUser မရှိသေးပါ။", reply_markup=get_back_to_admin_button())
        return
    context.user_data['user_list'] = users
    context.user_data['user_page'] = 1
    await show_user_page(update, context, query)

async def admin_user_list_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split("_")[3])
    context.user_data['user_page'] = page
    await show_user_page(update, context, query)

async def show_user_page(update, context, query=None):
    users = context.user_data.get('user_list', [])
    page = context.user_data.get('user_page', 1)
    per_page = 10
    total_pages = (len(users) + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    page_users = users[start:end]
    
    text = f"👥 **User List (Page {page}/{total_pages})**\n\n"
    for user_id in page_users:
        wallet = crud.get_wallet(user_id)
        text += f"🆔 {user_id} | Wallet: {wallet.balance:,} MMK\n"
    keyboard = get_user_list_keyboard(page, total_pages)
    if query:
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

# ==================== BOT LOGS ====================
async def admin_bot_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    log_file = "bot.log"
    if not os.path.exists(log_file):
        await query.edit_message_text("📜 **Bot Logs**\n\nLog file မရှိသေးပါ။", reply_markup=get_back_to_admin_button())
        return
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()[-20:]
        text = "📜 **Bot Logs (Last 20)**\n\n"
        for line in lines:
            text += f"{line[:80]}...\n" if len(line) > 80 else line
        if len(text) > 4000:
            text = text[:4000] + "\n... (truncated)"
        await query.edit_message_text(text, reply_markup=get_back_to_admin_button(), parse_mode="Markdown")
    except Exception as e:
        await query.edit_message_text(f"❌ Error reading logs: {e}", reply_markup=get_back_to_admin_button())

# ==================== BACKUP DATABASE ====================
async def admin_backup_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db_path = "data/bot.db"
    if not os.path.exists(db_path):
        await query.edit_message_text("💾 **Backup Database**\n\nDatabase file မရှိပါ။", reply_markup=get_back_to_admin_button())
        return
    size = os.path.getsize(db_path) / 1024
    text = f"💾 **Database Backup**\n\n📁 Current DB: bot.db\n📊 Size: {size:.2f} KB\n📅 Last Modified: {datetime.fromtimestamp(os.path.getmtime(db_path)).strftime('%Y-%m-%d %H:%M:%S')}"
    keyboard = [
        [InlineKeyboardButton("⬇️ Download Backup", callback_data="admin_download_backup")],
        [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==================== SETTINGS ====================
async def admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    settings = crud.get_all_settings_json()
    text = f"⚙️ **Settings**\n\n🏦 KBZ Pay: `{settings.get('kbz_number', '09255477757')}`\n🏦 Wave Pay: `{settings.get('wave_number', '09255477757')}`\n🔑 Default 2FA: `{settings.get('default_2fa', '123456')}`\n💰 Default Price: `{settings.get('default_price', '1000')}` MMK\n👥 Admins: {', '.join(str(a) for a in ADMIN_IDS)}\n"
    keyboard = [[InlineKeyboardButton("✏️ Change KBZ", callback_data="admin_change_kbz"), InlineKeyboardButton("✏️ Change Wave", callback_data="admin_change_wave")],
                [InlineKeyboardButton("🔑 Change Default 2FA", callback_data="admin_change_2fa"), InlineKeyboardButton("💰 Change Default Price", callback_data="admin_change_price_setting")],
                [InlineKeyboardButton("👥 Manage Admins", callback_data="admin_manage_admins")],
                [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def change_kbz_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['awaiting_kbz'] = True
    await query.edit_message_text("✏️ **Change KBZ Pay Number**\n\nနံပါတ်အသစ်ကို ရိုက်ထည့်ပါ။", reply_markup=get_back_button(), parse_mode="Markdown")

async def receive_new_kbz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_kbz', False):
        return
    new_number = update.message.text.strip()
    if not new_number.isdigit() or len(new_number) < 10:
        await update.message.reply_text("❌ နံပါတ်မှန်ကန်မှု မရှိပါ။")
        return
    crud.update_setting('kbz_number', new_number)
    context.user_data.clear()
    await update.message.reply_text(f"✅ KBZ Pay ကို `{new_number}` သို့ အောင်မြင်စွာ ပြောင်းလဲပြီးပါပြီ။", parse_mode="Markdown")

async def change_wave_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['awaiting_wave'] = True
    await query.edit_message_text("✏️ **Change Wave Pay Number**\n\nနံပါတ်အသစ်ကို ရိုက်ထည့်ပါ။", reply_markup=get_back_button(), parse_mode="Markdown")

async def receive_new_wave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_wave', False):
        return
    new_number = update.message.text.strip()
    if not new_number.isdigit() or len(new_number) < 10:
        await update.message.reply_text("❌ နံပါတ်မှန်ကန်မှု မရှိပါ။")
        return
    crud.update_setting('wave_number', new_number)
    context.user_data.clear()
    await update.message.reply_text(f"✅ Wave Pay ကို `{new_number}` သို့ အောင်မြင်စွာ ပြောင်းလဲပြီးပါပြီ။", parse_mode="Markdown")

async def change_2fa_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['awaiting_2fa'] = True
    await query.edit_message_text("🔑 **Change Default 2FA**\n\n2FA အသစ် (ဂဏန်း ၄-၈ လုံး) ကို ရိုက်ထည့်ပါ။", reply_markup=get_back_button(), parse_mode="Markdown")

async def receive_new_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_2fa', False):
        return
    new_2fa = update.message.text.strip()
    if not new_2fa.isdigit() or len(new_2fa) < 4:
        await update.message.reply_text("❌ ဂဏန်း ၄ လုံးထက်မနည်း ဖြစ်ရပါမည်။")
        return
    crud.update_setting('default_2fa', new_2fa)
    context.user_data.clear()
    await update.message.reply_text(f"✅ Default 2FA ကို `{new_2fa}` သို့ အောင်မြင်စွာ ပြောင်းလဲပြီးပါပြီ။", parse_mode="Markdown")

async def change_price_setting_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['awaiting_price_setting'] = True
    await query.edit_message_text("💰 **Change Default Price**\n\nPrice အသစ် (MMK) ကို ရိုက်ထည့်ပါ။", reply_markup=get_back_button(), parse_mode="Markdown")

async def receive_new_price_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_price_setting', False):
        return
    try:
        new_price = int(update.message.text.strip())
        if new_price < 100:
            await update.message.reply_text("❌ အနည်းဆုံး 100 MMK ဖြစ်ရပါမည်။")
            return
    except:
        await update.message.reply_text("❌ ဂဏန်းတစ်ခုသာ ရိုက်ထည့်ပါ။")
        return
    crud.update_setting('default_price', str(new_price))
    context.user_data.clear()
    await update.message.reply_text(f"✅ Default Price ကို {new_price} MMK သို့ အောင်မြင်စွာ ပြောင်းလဲပြီးပါပြီ။")

async def admin_manage_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "👥 **Manage Admins**\n\n📋 လက်ရှိ Admin များ:\n"
    for admin_id in ADMIN_IDS:
        text += f"🆔 {admin_id}\n"
    keyboard = [[InlineKeyboardButton("➕ Add Admin", callback_data="admin_add_admin"), InlineKeyboardButton("❌ Remove Admin", callback_data="admin_remove_admin")],
                [InlineKeyboardButton("🔙 Back to Settings", callback_data="admin_settings")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin_add_admin_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['awaiting_add_admin'] = True
    await query.edit_message_text("➕ **Add Admin**\n\nAdmin အဖြစ် ထည့်သွင်းလိုသော **User ID** ကို ရိုက်ထည့်ပါ။", reply_markup=get_back_button(), parse_mode="Markdown")

async def receive_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_add_admin', False):
        return
    try:
        new_admin = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ ဂဏန်းတစ်ခုသာ ရိုက်ထည့်ပါ။")
        return
    if new_admin in ADMIN_IDS:
        await update.message.reply_text(f"❌ {new_admin} သည် Admin ဖြစ်နေပြီးသားပါ။")
        context.user_data['awaiting_add_admin'] = False
        return
    ADMIN_IDS.append(new_admin)
    context.user_data['awaiting_add_admin'] = False
    await update.message.reply_text(f"✅ {new_admin} ကို Admin စာရင်းထဲ ထည့်သွင်းပြီးပါပြီ။")

async def admin_remove_admin_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['awaiting_remove_admin'] = True
    await query.edit_message_text("❌ **Remove Admin**\n\nဖယ်ရှားလိုသော **Admin ID** ကို ရိုက်ထည့်ပါ။", reply_markup=get_back_button(), parse_mode="Markdown")

async def receive_remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_remove_admin', False):
        return
    try:
        remove_id = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ ဂဏန်းတစ်ခုသာ ရိုက်ထည့်ပါ။")
        return
    if remove_id == ADMIN_IDS[0]:
        await update.message.reply_text("❌ သင်ကိုယ်တိုင်ကို မဖယ်ရှားနိုင်ပါ။")
        context.user_data['awaiting_remove_admin'] = False
        return
    if remove_id not in ADMIN_IDS:
        await update.message.reply_text(f"❌ {remove_id} သည် Admin မဟုတ်ပါ။")
        context.user_data['awaiting_remove_admin'] = False
        return
    ADMIN_IDS.remove(remove_id)
    context.user_data['awaiting_remove_admin'] = False
    await update.message.reply_text(f"✅ {remove_id} ကို Admin စာရင်းမှ ဖယ်ရှားပြီးပါပြီ။")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['awaiting_broadcast'] = True
    await query.edit_message_text("📢 **Broadcast**\n\nUser အားလုံးသို့ ပို့လိုသော စာသားကို ရိုက်ထည့်ပါ။", reply_markup=get_back_button(), parse_mode="Markdown")

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_broadcast', False):
        return
    message_text = update.message.text
    context.user_data['awaiting_broadcast'] = False
    users = crud.get_all_users()
    success_count, fail_count = 0, 0
    await update.message.reply_text("⏳ Broadcast ပို့နေပါပြီ...")
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=f"📢 **Announcement**\n\n{message_text}", parse_mode="Markdown")
            success_count += 1
        except:
            fail_count += 1
    await update.message.reply_text(f"✅ Broadcast ပြီးဆုံးပါပြီ။\n📤 အောင်မြင်သူ: {success_count}\n❌ မအောင်မြင်သူ: {fail_count}")
