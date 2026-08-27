import asyncio
import os
from aiohttp import web
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.request import HTTPXRequest
from bot.config import BOT_TOKEN
from database import crud

from bot.handlers.menu import show_main_menu, back_to_menu, show_rules, invite_friend, send_message_prompt, receive_user_message
from bot.handlers.buy import buy_product, select_quantity, receive_custom_quantity, bulk_confirm
from bot.handlers.payment import (receive_payment_slip, admin_approve_slip, get_otp_code, login_success, receive_topup_slip, my_orders)
from bot.handlers.wallet import (pay_with_wallet, pay_with_slip)
from bot.handlers.upload import admin_upload_prompt, receive_uploaded_file
from bot.handlers.admin import (admin_panel, admin_stats, admin_orders, admin_order_detail_prompt,
    admin_products, admin_deactivate_prompt, admin_stock, admin_settings, admin_broadcast,
    admin_delete_inactive, admin_confirm_delete_inactive, admin_wallets, admin_add_balance_prompt,
    receive_add_balance, admin_manage_admins, admin_add_admin_prompt, receive_add_admin,
    admin_remove_admin_prompt, receive_remove_admin, admin_delete_permanent_prompt,
    receive_delete_permanent, admin_health, admin_delete_bad, admin_confirm_delete,
    admin_cleanup, admin_confirm_cleanup, admin_sync_activate, admin_confirm_sync,
    admin_reset_all, admin_confirm_reset, admin_reset_wallet_prompt, receive_reset_wallet,
    admin_clear_orders_prompt, admin_confirm_clear_orders, admin_user_list, admin_user_list_page,
    admin_bot_logs, admin_backup_db,
    change_kbz_prompt, receive_new_kbz, change_wave_prompt, receive_new_wave,
    change_2fa_prompt, receive_new_2fa, change_price_setting_prompt, receive_new_price_setting,
    receive_order_id, receive_deactivate_product, send_broadcast)
from bot.handlers.wallet import (my_wallet, refresh_wallet, topup_request,
    topup_amount_selected, receive_custom_topup, approve_topup, reject_topup, withdraw_wallet,
    withdraw_amount_prompt, receive_withdraw_amount)
from bot.handlers.settings import (settings_panel, change_default_2fa_prompt,
    receive_default_2fa, change_default_price_prompt, receive_default_price)
from utils.rate_limiter import check_rate_limit

async def health_check(request):
    return web.Response(text="OK", status=200)

async def run_health_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("Health check server running on port 8080")
    await asyncio.Event().wait()

async def cleanup_orphaned():
    products = crud.get_all_products()
    deleted = 0
    for product in products:
        if product.file_path and not os.path.exists(product.file_path):
            crud.permanently_delete_product(product.id)
            deleted += 1
    if deleted > 0:
        print(f"🧹 Cleaned up {deleted} orphaned records")

async def handle_referral_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args and context.args[0].startswith("ref_"):
        try:
            referrer_id = int(context.args[0].split("_")[1])
            user_id = update.effective_user.id
            if referrer_id != user_id:
                existing = crud.get_referral_by_referred(user_id)
                if not existing:
                    crud.create_referral(referrer_id, user_id)
                    await update.message.reply_text("🎉 သင့်ကို သူငယ်ချင်းတစ်ယောက်က ခေါ်လာတာပါ။ ပထမဆုံး ဝယ်ယူမှုပြီးသွားရင် သူငယ်ချင်းအတွက် ဘောနပ်စ်ရပါမယ်။")
        except:
            pass
    await show_main_menu(update, context)

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    if user_data.get('awaiting_custom_qty'): await receive_custom_quantity(update, context); return
    if user_data.get('awaiting_default_2fa'): await receive_default_2fa(update, context); return
    if user_data.get('awaiting_default_price'): await receive_default_price(update, context); return
    if user_data.get('awaiting_kbz'): await receive_new_kbz(update, context); return
    if user_data.get('awaiting_wave'): await receive_new_wave(update, context); return
    if user_data.get('awaiting_2fa'): await receive_new_2fa(update, context); return
    if user_data.get('awaiting_price_setting'): await receive_new_price_setting(update, context); return
    if user_data.get('awaiting_order_id'): await receive_order_id(update, context); return
    if user_data.get('awaiting_deactivate'): await receive_deactivate_product(update, context); return
    if user_data.get('awaiting_broadcast'): await send_broadcast(update, context); return
    if user_data.get('awaiting_add_balance'): await receive_add_balance(update, context); return
    if user_data.get('awaiting_add_admin'): await receive_add_admin(update, context); return
    if user_data.get('awaiting_remove_admin'): await receive_remove_admin(update, context); return
    if user_data.get('awaiting_topup_custom'): await receive_custom_topup(update, context); return
    if user_data.get('awaiting_delete_permanent'): await receive_delete_permanent(update, context); return
    if user_data.get('awaiting_reset_wallet'): await receive_reset_wallet(update, context); return
    if user_data.get('awaiting_withdraw'): await receive_withdraw_amount(update, context); return
    if user_data.get('awaiting_user_message'): await receive_user_message(update, context); return
    await update.message.reply_text("❓ နားမလည်ပါ။ /start နှိပ်ပြီး ပြန်စပါ။")

def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    request = HTTPXRequest(connection_pool_size=8, connect_timeout=120.0, read_timeout=120.0, write_timeout=120.0)
    application = Application.builder().token(BOT_TOKEN).request(request).build()

    application.add_handler(CommandHandler("start", handle_referral_start))
    application.add_handler(CommandHandler("admin", admin_panel))

    application.add_handler(CallbackQueryHandler(show_main_menu, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
    application.add_handler(CallbackQueryHandler(buy_product, pattern="^buy_product$"))
    application.add_handler(CallbackQueryHandler(select_quantity, pattern="^qty_"))
    application.add_handler(CallbackQueryHandler(bulk_confirm, pattern="^bulk_confirm$"))
    application.add_handler(CallbackQueryHandler(pay_with_wallet, pattern="^pay_wallet$"))
    application.add_handler(CallbackQueryHandler(pay_with_slip, pattern="^pay_slip$"))
    # ✅ Order Approve အတွက် pattern ကို approve_order_ လို့ပြောင်းပါ
    application.add_handler(CallbackQueryHandler(admin_approve_slip, pattern="^approve_order_"))
    application.add_handler(CallbackQueryHandler(admin_upload_prompt, pattern="^admin_upload$"))
    application.add_handler(CallbackQueryHandler(show_rules, pattern="^show_rules$"))
    application.add_handler(CallbackQueryHandler(invite_friend, pattern="^invite_friend$"))
    application.add_handler(CallbackQueryHandler(send_message_prompt, pattern="^send_message$"))
    application.add_handler(CallbackQueryHandler(my_orders, pattern="^my_orders$"))
    application.add_handler(CallbackQueryHandler(get_otp_code, pattern="^get_otp_"))
    application.add_handler(CallbackQueryHandler(login_success, pattern="^login_success$"))

    application.add_handler(CallbackQueryHandler(my_wallet, pattern="^my_wallet$"))
    application.add_handler(CallbackQueryHandler(refresh_wallet, pattern="^refresh_wallet$"))
    application.add_handler(CallbackQueryHandler(topup_request, pattern="^topup_request$"))
    application.add_handler(CallbackQueryHandler(topup_amount_selected, pattern="^topup_"))
    application.add_handler(CallbackQueryHandler(approve_topup, pattern="^approve_topup_"))
    application.add_handler(CallbackQueryHandler(reject_topup, pattern="^reject_topup_"))
    application.add_handler(CallbackQueryHandler(withdraw_wallet, pattern="^withdraw_wallet$"))
    application.add_handler(CallbackQueryHandler(withdraw_amount_prompt, pattern="^withdraw_"))

    application.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    application.add_handler(CallbackQueryHandler(admin_stats, pattern="^admin_stats$"))
    application.add_handler(CallbackQueryHandler(admin_orders, pattern="^admin_orders$"))
    application.add_handler(CallbackQueryHandler(admin_order_detail_prompt, pattern="^admin_order_detail$"))
    application.add_handler(CallbackQueryHandler(admin_products, pattern="^admin_products$"))
    application.add_handler(CallbackQueryHandler(admin_deactivate_prompt, pattern="^admin_deactivate$"))
    application.add_handler(CallbackQueryHandler(admin_delete_permanent_prompt, pattern="^admin_delete_permanent$"))
    application.add_handler(CallbackQueryHandler(admin_health, pattern="^admin_health$"))
    application.add_handler(CallbackQueryHandler(admin_delete_bad, pattern="^admin_delete_bad$"))
    application.add_handler(CallbackQueryHandler(admin_confirm_delete, pattern="^admin_confirm_delete$"))
    application.add_handler(CallbackQueryHandler(admin_stock, pattern="^admin_stock$"))
    application.add_handler(CallbackQueryHandler(admin_delete_inactive, pattern="^admin_delete_inactive$"))
    application.add_handler(CallbackQueryHandler(admin_confirm_delete_inactive, pattern="^admin_confirm_delete_inactive$"))
    application.add_handler(CallbackQueryHandler(admin_wallets, pattern="^admin_wallets$"))
    application.add_handler(CallbackQueryHandler(admin_add_balance_prompt, pattern="^admin_add_balance$"))
    application.add_handler(CallbackQueryHandler(admin_manage_admins, pattern="^admin_manage_admins$"))
    application.add_handler(CallbackQueryHandler(admin_add_admin_prompt, pattern="^admin_add_admin$"))
    application.add_handler(CallbackQueryHandler(admin_remove_admin_prompt, pattern="^admin_remove_admin$"))
    application.add_handler(CallbackQueryHandler(admin_settings, pattern="^admin_settings$"))
    application.add_handler(CallbackQueryHandler(admin_broadcast, pattern="^admin_broadcast$"))
    application.add_handler(CallbackQueryHandler(admin_cleanup, pattern="^admin_cleanup$"))
    application.add_handler(CallbackQueryHandler(admin_confirm_cleanup, pattern="^admin_confirm_cleanup$"))
    application.add_handler(CallbackQueryHandler(admin_sync_activate, pattern="^admin_sync_activate$"))
    application.add_handler(CallbackQueryHandler(admin_confirm_sync, pattern="^admin_confirm_sync$"))
    application.add_handler(CallbackQueryHandler(admin_reset_all, pattern="^admin_reset_all$"))
    application.add_handler(CallbackQueryHandler(admin_confirm_reset, pattern="^admin_confirm_reset$"))
    application.add_handler(CallbackQueryHandler(admin_reset_wallet_prompt, pattern="^admin_reset_wallet$"))
    application.add_handler(CallbackQueryHandler(admin_clear_orders_prompt, pattern="^admin_clear_orders$"))
    application.add_handler(CallbackQueryHandler(admin_confirm_clear_orders, pattern="^admin_confirm_clear_orders$"))
    application.add_handler(CallbackQueryHandler(admin_user_list, pattern="^admin_user_list$"))
    application.add_handler(CallbackQueryHandler(admin_user_list_page, pattern="^admin_user_page_"))
    application.add_handler(CallbackQueryHandler(admin_bot_logs, pattern="^admin_bot_logs$"))
    application.add_handler(CallbackQueryHandler(admin_backup_db, pattern="^admin_backup_db$"))
    application.add_handler(CallbackQueryHandler(change_kbz_prompt, pattern="^admin_change_kbz$"))
    application.add_handler(CallbackQueryHandler(change_wave_prompt, pattern="^admin_change_wave$"))
    application.add_handler(CallbackQueryHandler(change_2fa_prompt, pattern="^admin_change_2fa$"))
    application.add_handler(CallbackQueryHandler(change_price_setting_prompt, pattern="^admin_change_price_setting$"))

    application.add_handler(CallbackQueryHandler(settings_panel, pattern="^settings_panel$"))
    application.add_handler(CallbackQueryHandler(change_default_2fa_prompt, pattern="^settings_change_2fa$"))
    application.add_handler(CallbackQueryHandler(change_default_price_prompt, pattern="^settings_change_price$"))

    application.add_handler(MessageHandler(filters.PHOTO, receive_payment_slip))
    application.add_handler(MessageHandler(filters.Document.ALL, receive_uploaded_file))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))

    print("Bot started...")
    loop.run_until_complete(cleanup_orphaned())
    asyncio.ensure_future(run_health_server(), loop=loop)
    loop.run_until_complete(application.run_polling(allowed_updates=[]))

if __name__ == "__main__":
    main()
