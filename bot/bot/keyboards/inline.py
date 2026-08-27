from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.config import is_admin

def get_main_menu_keyboard(user_id: int):
    keyboard = [
        [InlineKeyboardButton("🛒 Buy Session", callback_data="buy_product")],
        [InlineKeyboardButton("ℹ️ Rules & Info", callback_data="show_rules")],
        [InlineKeyboardButton("📤 Invite Friend", callback_data="invite_friend")],
        [InlineKeyboardButton("💬 Send Message", callback_data="send_message")],
        [InlineKeyboardButton("📊 My Orders", callback_data="my_orders")],
        [InlineKeyboardButton("💰 My Wallet", callback_data="my_wallet")],
    ]
    if is_admin(user_id):
        keyboard.insert(1, [InlineKeyboardButton("🛠️ Admin Panel", callback_data="admin_panel")])
        keyboard.insert(2, [InlineKeyboardButton("📤 Upload Session", callback_data="admin_upload")])
    keyboard.append([InlineKeyboardButton("🏠 Back to Menu", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back to Menu", callback_data="back_to_menu")]])

def get_back_to_admin_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]])

def get_admin_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"), InlineKeyboardButton("📋 Orders", callback_data="admin_orders")],
        [InlineKeyboardButton("📦 Active Products", callback_data="admin_products"), InlineKeyboardButton("🩺 Session Health", callback_data="admin_health")],
        [InlineKeyboardButton("📦 Stock", callback_data="admin_stock"), InlineKeyboardButton("🗑 Delete Inactive", callback_data="admin_delete_inactive")],
        [InlineKeyboardButton("🧹 Cleanup Orphaned", callback_data="admin_cleanup"), InlineKeyboardButton("🔄 Sync & Activate All", callback_data="admin_sync_activate")],
        [InlineKeyboardButton("🗑️ Reset All & Clean", callback_data="admin_reset_all"), InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")],
        [InlineKeyboardButton("📤 Upload Session", callback_data="admin_upload"), InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👛 Manage Wallets", callback_data="admin_wallets"), InlineKeyboardButton("👥 User List", callback_data="admin_user_list")],
        [InlineKeyboardButton("📜 Bot Logs", callback_data="admin_bot_logs"), InlineKeyboardButton("💾 Backup DB", callback_data="admin_backup_db")],
        [InlineKeyboardButton("🏠 Back to Menu", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_quantity_keyboard():
    keyboard = [
        [InlineKeyboardButton("1", callback_data="qty_1"), InlineKeyboardButton("2", callback_data="qty_2")],
        [InlineKeyboardButton("3", callback_data="qty_3"), InlineKeyboardButton("4", callback_data="qty_4")],
        [InlineKeyboardButton("5", callback_data="qty_5"), InlineKeyboardButton("6", callback_data="qty_6")],
        [InlineKeyboardButton("7", callback_data="qty_7"), InlineKeyboardButton("8", callback_data="qty_8")],
        [InlineKeyboardButton("9", callback_data="qty_9"), InlineKeyboardButton("10", callback_data="qty_10")],
        [InlineKeyboardButton("📝 Custom", callback_data="qty_custom")],
        [InlineKeyboardButton("🏠 Back to Menu", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_payment_method_keyboard(wallet_balance, total_price):
    keyboard = []
    if wallet_balance >= total_price:
        keyboard.append([InlineKeyboardButton("✅ Pay with Wallet", callback_data="pay_wallet")])
    else:
        keyboard.append([InlineKeyboardButton("💰 Top-up Wallet", callback_data="topup_wallet")])
    keyboard.append([InlineKeyboardButton("📸 Pay with Slip", callback_data="pay_slip")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_bulk_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm Order", callback_data="bulk_confirm")],
        [InlineKeyboardButton("❌ Cancel", callback_data="back_to_menu")]
    ])

def get_otp_request_keyboard(order_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Get OTP Code", callback_data=f"get_otp_{order_id}")],
        [InlineKeyboardButton("🏠 Back to Menu", callback_data="back_to_menu")]
    ])

def get_otp_result_keyboard(order_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Get OTP Again", callback_data=f"get_otp_{order_id}")],
        [InlineKeyboardButton("✅ Login Success", callback_data="login_success")],
        [InlineKeyboardButton("🏠 Back to Menu", callback_data="back_to_menu")]
    ])

def get_wallet_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_wallet")],
        [InlineKeyboardButton("📤 Request Top-up", callback_data="topup_request")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw_wallet")],
        [InlineKeyboardButton("📤 Invite Friend", callback_data="invite_friend")],
        [InlineKeyboardButton("🏠 Back to Menu", callback_data="back_to_menu")]
    ])

def get_topup_amount_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1000 MMK", callback_data="topup_1000"), InlineKeyboardButton("2000 MMK", callback_data="topup_2000")],
        [InlineKeyboardButton("5000 MMK", callback_data="topup_5000"), InlineKeyboardButton("10000 MMK", callback_data="topup_10000")],
        [InlineKeyboardButton("📝 Custom Amount", callback_data="topup_custom")],
        [InlineKeyboardButton("🏠 Back to Menu", callback_data="back_to_menu")]
    ])

def get_withdraw_amount_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1000 MMK", callback_data="withdraw_1000"), InlineKeyboardButton("2000 MMK", callback_data="withdraw_2000")],
        [InlineKeyboardButton("5000 MMK", callback_data="withdraw_5000"), InlineKeyboardButton("10000 MMK", callback_data="withdraw_10000")],
        [InlineKeyboardButton("📝 Custom Amount", callback_data="withdraw_custom")],
        [InlineKeyboardButton("🏠 Back to Menu", callback_data="back_to_menu")]
    ])

def get_health_result_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh Health", callback_data="admin_health")],
        [InlineKeyboardButton("🗑 Delete All Bad", callback_data="admin_delete_bad")],
        [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
    ])

def get_confirm_delete_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, Delete All", callback_data="admin_confirm_delete")],
        [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
    ])

def get_confirm_delete_inactive_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, Delete All Inactive", callback_data="admin_confirm_delete_inactive")],
        [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
    ])

def get_wallet_manage_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Balance", callback_data="admin_add_balance")],
        [InlineKeyboardButton("🗑️ Reset User Wallet", callback_data="admin_reset_wallet")],
        [InlineKeyboardButton("🗑️ Clear All Orders", callback_data="admin_clear_orders")],
        [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
    ])

def get_topup_approve_keyboard(tx_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve Top-up", callback_data=f"approve_topup_{tx_id}")],
        [InlineKeyboardButton("❌ Reject", callback_data=f"reject_topup_{tx_id}")]
    ])

def get_sync_activate_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, Sync & Activate", callback_data="admin_confirm_sync")],
        [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
    ])

def get_reset_all_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, Reset Everything", callback_data="admin_confirm_reset")],
        [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
    ])

def get_cleanup_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, Cleanup All", callback_data="admin_confirm_cleanup")],
        [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
    ])

def get_clear_orders_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, Clear All Orders", callback_data="admin_confirm_clear_orders")],
        [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
    ])

def get_user_list_keyboard(page, total_pages):
    buttons = []
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin_user_page_{page-1}"))
    nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="admin_user_list"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin_user_page_{page+1}"))
    buttons.append(nav_row)
    buttons.append([InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(buttons)

def get_referral_stats_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="my_wallet")],
        [InlineKeyboardButton("📤 Invite More", callback_data="invite_friend")],
        [InlineKeyboardButton("🏠 Back to Menu", callback_data="back_to_menu")]
    ])
