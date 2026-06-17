import telebot
from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
import json
import re

# ========== تنظیمات ==========
TOKEN = "توکن_ربات_خود_را_اینجا_قرار_دهید"
ADMIN_IDS = [123456789]  # آیدی عددی ادمین را اینجا وارد کنید

# شماره کارت و نام صاحب حساب
CARD_NUMBER = "6280231325093895"
CARD_OWNER = "کیان جلیلیان"

# قیمت‌ها (به تومان)
PRICES = {
    1: 15, 2: 29, 3: 45, 4: 60, 5: 75,
    6: 90, 7: 112, 8: 120, 9: 135, 10: 140
}

bot = telebot.TeleBot(TOKEN)

# ========== مدیریت وضعیت کاربران (ذخیره در RAM) ==========
user_states = {}  # {user_id: "waiting_for_photo"} یا دیکشنری کامل خرید
user_purchases = {}  # {user_id: {"volume": 5, "price": 75, "status": "pending"}}

# ========== صفحه کلید شیشه‌ای اصلی ==========
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_buy = KeyboardButton("🛒 خرید سرویس")
    btn_renew = KeyboardButton("🔄 تمدید سرویس")
    btn_my_services = KeyboardButton("📋 سرویس‌های من")
    btn_wallet = KeyboardButton("💰 کیف پول")
    btn_support = KeyboardButton("📞 پشتیبانی")
    markup.add(btn_buy, btn_renew, btn_my_services, btn_wallet, btn_support)
    return markup

# ========== منوی انتخاب حجم (اینلاین) ==========
def volume_keyboard():
    markup = InlineKeyboardMarkup(row_width=3)
    buttons = []
    for gb in range(1, 11):
        buttons.append(InlineKeyboardButton(f"{gb} GB", callback_data=f"vol_{gb}"))
    markup.add(*buttons)
    return markup

# ========== شروع ربات ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    bot.send_message(
        user_id,
        "🟢 به فروشگاه کانفیگ خوش آمدید!\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=main_menu()
    )

# ========== هندلر منوی اصلی ==========
@bot.message_handler(func=lambda msg: msg.text == "🛒 خرید سرویس")
def buy_service(message):
    bot.send_message(
        message.chat.id,
        "📦 حجم مورد نظر خود را انتخاب کنید (1 تا 10 گیگابایت):",
        reply_markup=volume_keyboard()
    )

@bot.message_handler(func=lambda msg: msg.text == "🔄 تمدید سرویس")
def renew_service(message):
    bot.send_message(message.chat.id, "⏳ در حال توسعه ... به زودی امکان تمدید خودکار فراهم می‌شود.")

@bot.message_handler(func=lambda msg: msg.text == "📋 سرویس‌های من")
def my_services(message):
    bot.send_message(message.chat.id, "📋 لیست سرویس‌های فعال شما:\n(هنوز سرویسی خریداری نکرده‌اید)")

@bot.message_handler(func=lambda msg: msg.text == "💰 کیف پول")
def wallet(message):
    bot.send_message(message.chat.id, "💰 موجودی کیف پول شما: 0 تومان\n(به زودی شارژ کیف پول فعال می‌شود)")

@bot.message_handler(func=lambda msg: msg.text == "📞 پشتیبانی")
def support(message):
    bot.send_message(
        message.chat.id,
        "👤 پشتیبانی: @config100originala\n"
        "برای راهنمایی و پاسخ به سوالات با ایشان تماس بگیرید."
    )

# ========== انتخاب حجم ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("vol_"))
def select_volume(call):
    volume = int(call.data.split("_")[1])
    price = PRICES[volume]
    user_id = call.from_user.id

    # ذخیره اطلاعات خرید موقت
    user_purchases[user_id] = {
        "volume": volume,
        "price": price,
        "status": "awaiting_payment"
    }

    # نمایش گزینه پرداخت
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💳 پرداخت با کارت به کارت", callback_data="pay_by_card"))
    markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_volume"))
    bot.edit_message_text(
        f"✅ حجم {volume} گیگابایت با قیمت {price} تومان انتخاب شد.\n"
        "روش پرداخت را انتخاب کنید:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_volume")
def back_to_volume(call):
    bot.edit_message_text(
        "📦 حجم مورد نظر خود را انتخاب کنید:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=volume_keyboard()
    )
    bot.answer_callback_query(call.id)

# ========== نمایش پیش‌فاکتور ==========
@bot.callback_query_handler(func=lambda call: call.data == "pay_by_card")
def show_invoice(call):
    user_id = call.from_user.id
    purchase = user_purchases.get(user_id)
    if not purchase or purchase["status"] != "awaiting_payment":
        bot.answer_callback_query(call.id, "لطفا دوباره خرید را شروع کنید.", show_alert=True)
        return

    volume = purchase["volume"]
    price = purchase["price"]

    # متن پیش‌فاکتور با قابلیت کپی شماره کارت
    invoice_text = (
        "☑️ ممنون از انتخاب و اعتماد شما\n"
        f"لطفا مبلغ **{price} تومان** به کارت زیر واریز کنید:\n\n"
        f"💳 شماره کارت:\n`{CARD_NUMBER}`\n\n"
        f"{CARD_OWNER}\n\n"
        "⚠️ توجه توجه: دوستان مبلغ رو دقیق واریز کنید در غیر این صورت رسید شما تایید نخواهد شد.\n\n"
        "در صورت استفاده از اپ یا نرم‌افزارهای مشابه ممکن است پیام محدودیت کارت نمایش داده شود، در این صورت از همراه بانک خود استفاده کنید.\n\n"
        "✅ پس از واریز، روی دکمه زیر کلیک کرده و تصویر رسید را ارسال کنید."
    )

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📸 ارسال تصویر رسید", callback_data="send_receipt"))

    bot.edit_message_text(
        invoice_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

# ========== درخواست ارسال عکس رسید ==========
@bot.callback_query_handler(func=lambda call: call.data == "send_receipt")
def ask_for_photo(call):
    user_id = call.from_user.id
    if user_id not in user_purchases or user_purchases[user_id]["status"] != "awaiting_payment":
        bot.answer_callback_query(call.id, "لطفا ابتدا حجم و روش پرداخت را انتخاب کنید.", show_alert=True)
        return

    user_purchases[user_id]["status"] = "waiting_photo"
    bot.edit_message_text(
        "📸 لطفاً تصویر رسید واریزی خود را ارسال کنید.\n(یک عکس واضح از فیش بانکی یا پیام موفقیت آمیز پرداخت)",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    )
    bot.answer_callback_query(call.id)

# ========== دریافت عکس از کاربر ==========
@bot.message_handler(content_types=['photo'])
def handle_receipt_photo(message):
    user_id = message.from_user.id
    if user_id not in user_purchases or user_purchases[user_id].get("status") != "waiting_photo":
        bot.reply_to(message, "❌ در حال حاضر درخواست خرید فعالی ندارید. لطفا از طریق منوی اصلی اقدام کنید.")
        return

    # دریافت بهترین کیفیت عکس
    photo = message.photo[-1].file_id
    volume = user_purchases[user_id]["volume"]
    price = user_purchases[user_id]["price"]
    user_info = f"👤 کاربر: {message.from_user.first_name} (@{message.from_user.username or 'بدون یوزرنیم'})\n🆔 آیدی: {user_id}\n📦 حجم: {volume} GB\n💰 مبلغ: {price} تومان"

    # ارسال به همه ادمین‌ها
    for admin_id in ADMIN_IDS:
        try:
            caption = f"🆕 درخواست خرید جدید:\n{user_info}\n\nلطفاً تصویر رسید را بررسی کنید."
            bot.send_photo(admin_id, photo, caption=caption)
            # همچنین دکمه‌های تایید/رد برای ادمین
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("✅ تایید و ارسال کانفیگ", callback_data=f"confirm_{user_id}"),
                InlineKeyboardButton("❌ رد درخواست", callback_data=f"reject_{user_id}")
            )
            bot.send_message(admin_id, "جهت تایید یا رد خرید از دکمه‌های زیر استفاده کنید:", reply_markup=markup)
        except Exception as e:
            print(f"خطا در ارسال به ادمین {admin_id}: {e}")

    # بروزرسانی وضعیت کاربر
    user_purchases[user_id]["status"] = "pending_admin"
    bot.reply_to(message, "✅ تصویر شما با موفقیت دریافت شد.\nدر انتظار تایید ادمین هستید، به زودی کانفیگ برای شما ارسال خواهد شد.")

# ========== هندلر تایید/رد توسط ادمین ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_") or call.data.startswith("reject_"))
def admin_decision(call):
    admin_id = call.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "شما دسترسی ادمین ندارید.", show_alert=True)
        return

    action, user_id_str = call.data.split("_")
    user_id = int(user_id_str)

    if action == "confirm":
        # درخواست از ادمین برای ارسال کانفیگ
        bot.send_message(
            admin_id,
            f"لطفاً لینک کانفیگ کاربر {user_id} را ارسال کنید.\n"
            "با استفاده از دستور:\n"
            f"/sendconfig {user_id} [لینک کانفیگ]\n"
            "مثال: /sendconfig 123456789 vless://..."
        )
        bot.answer_callback_query(call.id, "درخواست تایید شد. حالا کانفیگ را ارسال کنید.")
    else:  # reject
        if user_id in user_purchases:
            del user_purchases[user_id]
        bot.send_message(user_id, "❌ متاسفانه درخواست خرید شما رد شد. لطفا با پشتیبانی تماس بگیرید.")
        bot.send_message(admin_id, f"درخواست کاربر {user_id} رد شد.")
        bot.answer_callback_query(call.id)

# ========== دستور ادمین برای ارسال کانفیگ ==========
@bot.message_handler(commands=['sendconfig'])
def send_config(message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "شما دسترسی به این دستور ندارید.")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "فرمت صحیح:\n/sendconfig [user_id] [config_link]")
        return

    _, user_id_str, config_link = parts
    try:
        user_id = int(user_id_str)
    except ValueError:
        bot.reply_to(message, "آیدی کاربر باید عددی باشد.")
        return

    # ارسال کانفیگ به کاربر
    success_text = (
        "✅ پرداخت شما تایید شد!\n\n"
        "کانفیگ اختصاصی شما:\n"
        f"`{config_link}`\n\n"
        "روی لینک کلیک کنید تا در اپ V2Ray نصب شود.\n"
        "از خرید خود سپاسگزاریم."
    )
    try:
        bot.send_message(user_id, success_text, parse_mode="Markdown")
        bot.reply_to(message, f"کانفیگ با موفقیت به کاربر {user_id} ارسال شد.")
        # پاک کردن اطلاعات خرید کاربر
        if user_id in user_purchases:
            del user_purchases[user_id]
    except Exception as e:
        bot.reply_to(message, f"خطا در ارسال پیام به کاربر: {e}")

# ========== راه اندازی ربات ==========
if __name__ == "__main__":
    print("ربات فروش کانفیگ با موفقیت استارت خورد...")
    bot.infinity_polling()