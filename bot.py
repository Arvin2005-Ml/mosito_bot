from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, filters, CallbackContext
from telegram.error import InvalidToken, NetworkError
import sqlite3
import os
import asyncio
import json
import io
from keep_alive import keep_alive

# تعریف مراحل مکالمه
CLASS_SELECTION, AGE_SELECTION, NAME_INPUT, PHONE_INPUT = range(4)

# راه‌اندازی دیتابیس
try:
    conn = sqlite3.connect("data.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, class TEXT, age_range TEXT, name TEXT, phone TEXT)")
    conn.commit()
    print("دیتابیس با موفقیت راه‌اندازی شد.")
except sqlite3.Error as e:
    print(f"خطای دیتابیس: {e}")
    raise

def start(update: Update, context: CallbackContext) -> int:
    """مدیریت دستور /start و نمایش منوی دوره‌ها"""
    try:
        print(f"دستور /start دریافت شد از کاربر: {update.effective_user.id}")
        update.message.reply_text(
            "سلام به باشگاه موسینو خوش آمدید! 😊\n"
            "باشگاه رباتیک موسیتو، جایی برای ساختن آینده‌ای پیشرفته با دست‌های کوچک اما اندیشه‌های بزرگ است."
        )
        
        class_options = [
            ["کلاس آموزشی رباتیک", "کلاس آموزشی پایتون"],
            ["کلاس آموزشی هوش مصنوعی", "کلاس زبان انگلیسی تخصصی رباتیک"],
            ["دوره‌های آموزشی سلول خورشیدی"]
        ]
        reply_keyboard = ReplyKeyboardMarkup(class_options, one_time_keyboard=True, resize_keyboard=True)
        
        update.message.reply_text(
            "لطفاً یکی از دوره‌های آموزشی زیر را انتخاب کنید:",
            reply_markup=reply_keyboard
        )
        return CLASS_SELECTION
    except Exception as e:
        print(f"خطا در start: {e}")
        update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

def get_class(update: Update, context: CallbackContext) -> int:
    """مدیریت انتخاب دوره و اعتبارسنجی"""
    try:
        selected_class = update.message.text
        print(f"انتخاب دوره توسط کاربر {update.effective_user.id}: {selected_class}")
        valid_classes = [
            "کلاس آموزشی رباتیک", "کلاس آموزشی پایتون",
            "کلاس آموزشی هوش مصنوعی", "کلاس زبان انگلیسی تخصصی رباتیک",
            "دوره‌های آموزشی سلول خورشیدی"
        ]
        
        if selected_class not in valid_classes:
            update.message.reply_text("لطفاً فقط یکی از دوره‌های منو را انتخاب کنید. 😊")
            return CLASS_SELECTION
        
        context.user_data["class"] = selected_class
        
        age_options = [
            ["8-10 سال", "10-14 سال"],
            ["14-15 سال", "20-35 سال"]
        ]
        reply_keyboard = ReplyKeyboardMarkup(age_options, one_time_keyboard=True, resize_keyboard=True)
        
        update.message.reply_text(
            "شما چند سال سن دارید؟ لطفاً بازه سنی خود را انتخاب کنید:",
            reply_markup=reply_keyboard
        )
        return AGE_SELECTION
    except Exception as e:
        print(f"خطا در get_class: {e}")
        update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

def get_age(update: Update, context: CallbackContext) -> int:
    """مدیریت انتخاب سن و اعتبارسنجی"""
    try:
        age_range = update.message.text
        print(f"انتخاب بازه سنی توسط کاربر {update.effective_user.id}: {age_range}")
        valid_ages = ["8-10 سال", "10-14 سال", "14-15 سال", "20-35 سال"]
        
        if age_range not in valid_ages:
            update.message.reply_text("لطفاً فقط یکی از بازه‌های سنی منو را انتخاب کنید. 😊")
            return AGE_SELECTION
        
        selected_class = context.user_data.get("class")
        
        if selected_class == "کلاس آموزشی هوش مصنوعی" and age_range == "8-10 سال":
            class_options = [
                ["کلاس آموزشی رباتیک", "کلاس آموزشی پایتون"],
                ["کلاس زبان انگلیسی تخصصی رباتیک", "دوره‌های آموزشی سلول خورشیدی"]
            ]
            update.message.reply_text(
                "متأسفیم، دوره هوش مصنوعی برای بازه سنی 8-10 سال مناسب نیست. لطفاً دوره دیگری انتخاب کنید.",
                reply_markup=ReplyKeyboardMarkup(class_options, one_time_keyboard=True, resize_keyboard=True)
            )
            return CLASS_SELECTION
        
        context.user_data["age_range"] = age_range
        
        update.message.reply_text(
            "لطفاً نام خود را وارد کنید:",
            reply_markup=ReplyKeyboardRemove()
        )
        return NAME_INPUT
    except Exception as e:
        print(f"خطا در get_age: {e}")
        update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

def get_name(update: Update, context: CallbackContext) -> int:
    """مدیریت ورودی نام"""
    try:
        name = update.message.text.strip()
        print(f"ورود نام توسط کاربر {update.effective_user.id}: {name}")
        if not name or len(name) < 2:
            update.message.reply_text("لطفاً نام معتبر (حداقل 2 حرف) وارد کنید. 😊")
            return NAME_INPUT
        
        context.user_data["name"] = name
        
        reply_keyboard = [[KeyboardButton("اشتراک شماره تماس", request_contact=True)]]
        update.message.reply_text(
            "لطفاً شماره تماس خود را با استفاده از دکمه زیر به اشتراک بگذارید:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return PHONE_INPUT
    except Exception as e:
        print(f"خطا در get_name: {e}")
        update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

def get_phone(update: Update, context: CallbackContext) -> int:
    """مدیریت ورودی شماره تماس"""
    try:
        phone = None
        if update.message.contact:
            phone = update.message.contact.phone_number
        else:
            phone = update.message.text.strip()
            print(f"ورود شماره توسط کاربر {update.effective_user.id}: {phone}")
            if not (phone.startswith("+") and phone[1:].isdigit() or phone.isdigit()) or len(phone) < 7:
                update.message.reply_text("لطفاً شماره تماس معتبر وارد کنید یا از دکمه اشتراک استفاده کنید. 😊")
                return PHONE_INPUT
        
        user_id = update.effective_user.id
        selected_class = context.user_data.get("class")
        age_range = context.user_data.get("age_range")
        name = context.user_data.get("name")
        
        try:
            c.execute("INSERT OR REPLACE INTO users (id, class, age_range, name, phone) VALUES (?, ?, ?, ?, ?)",
                     (user_id, selected_class, age_range, name, phone))
            conn.commit()
            print(f"داده‌های کاربر {user_id} با موفقیت ذخیره شد.")
        except sqlite3.Error as e:
            update.message.reply_text("خطایی در ذخیره‌سازی اطلاعات رخ داد. لطفاً دوباره امتحان کنید.")
            print(f"خطای دیتابیس در get_phone: {e}")
            return ConversationHandler.END
        
        update.message.reply_text(
            "✅ ممنون از ثبت اطلاعات! 😊\n"
            "باشگاه رباتیک موسیتو با هدف پرورش نسل خلاق، نوآور و آشنا با فناوری‌های نوین، فعالیت خود را در حوزه آموزش رباتیک و هوش مصنوعی آغاز کرده و تاکنون میزبان صدها دانش‌آموز علاقه‌مند بوده است. در این باشگاه، کودکان و نوجوانان با مباحث پایه تا پیشرفته رباتیک، برنامه‌نویسی، الکترونیک، طراحی و ساخت ربات‌های واقعی آشنا می‌شوند و مهارت‌های عملی خود را در فضایی آموزشی، پویا و سرگرم‌کننده ارتقا می‌دهند.\n"
            "برای اطلاعات بیشتر، ما را در اینستاگرام دنبال کنید:\n"
            "لینک: https://www.instagram.com/ircstem?igsh=dXVvaGpnbTBkYnoy\n"
            "آیدی: @ircstem",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    except Exception as e:
        print(f"خطا در get_phone: {e}")
        update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

def get_db(update: Update, context: CallbackContext) -> None:
    """ارسال داده‌های دیتابیس به صورت فایل JSON"""
    try:
        print(f"دستور /getdb دریافت شد از کاربر: {update.effective_user.id}")
        c.execute("SELECT id, class, age_range, name, phone FROM users")
        rows = c.fetchall()
        
        users_data = [
            {"id": row[0], "class": row[1], "age_range": row[2], "name": row[3], "phone": row[4]} for row in rows
        ]
        
        json_data = json.dumps(users_data, ensure_ascii=False, indent=2)
        json_file = io.BytesIO(json_data.encode('utf-8'))
        json_file.name = "users_data.json"
        
        update.message.reply_document(
            document=InputFile(json_file, filename="users_data.json"),
            caption="داده‌های دیتابیس به صورت JSON"
        )
    except sqlite3.Error as e:
        update.message.reply_text("خطایی در دسترسی به دیتابیس رخ داد. لطفاً دوباره امتحان کنید.")
        print(f"خطای دیتابیس در get_db: {e}")
    except Exception as e:
        update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        print(f"خطا در get_db: {e}")

def cancel(update: Update, context: CallbackContext) -> int:
    """مدیریت دستور /cancel"""
    try:
        print(f"دستور /cancel دریافت شد از کاربر: {update.effective_user.id}")
        update.message.reply_text("لغو شد.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    except Exception as e:
        print(f"خطا در cancel: {e}")
        update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

def error_handler(update: Update, context: CallbackContext) -> None:
    """مدیریت خطاهای کلی"""
    try:
        if context.error.__class__.__name__ == "Conflict":
            print("خطای Conflict: نمونه دیگری از ربات در حال اجراست")
            if update and update.message:
                update.message.reply_text("ربات در حال حاضر فعال است. لطفاً بعداً امتحان کنید.")
        else:
            print(f"خطا: {context.error}")
            if update and update.message:
                update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
    except Exception as e:
        print(f"خطا در error_handler: {e}")

def main():
    """تابع اصلی برای اجرای ربات"""
    try:
        print("شروع اجرای ربات...")
        # اجرای keep_alive در یک task جداگانه
        asyncio.run(keep_alive())
        print("keep_alive با موفقیت راه‌اندازی شد.")

        TOKEN = os.environ.get("TOKEN")
        if not TOKEN:
            print("خطا: متغیر محیطی TOKEN تنظیم نشده است")
            raise ValueError("TOKEN is not set")
        print(f"توکن دریافت شد: {TOKEN[:4]}... (بخشی از توکن برای امنیت نمایش داده شد)")

        # ایجاد Updater و Dispatcher
        updater = Updater(TOKEN, use_context=True)
        dp = updater.dispatcher
        print("Updater و Dispatcher با موفقیت ایجاد شدند.")

        # تنظیم ConversationHandler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states={
                CLASS_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_class)],
                AGE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
                NAME_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
                PHONE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND | filters.CONTACT, get_phone)],
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        
        dp.add_handler(conv_handler)
        dp.add_handler(CommandHandler("getdb", get_db))
        dp.add_error_handler(error_handler)
        print("هندلرها با موفقیت اضافه شدند.")

        # شروع ربات
        print("شروع ربات...")
        updater.start_polling()
        print("ربات با موفقیت شروع شد.")

        # نگه داشتن ربات در حال اجرا
        print("ربات در حال اجرا...")
        updater.idle()

    except InvalidToken as e:
        print(f"خطای توکن: توکن نامعتبر است - {e}")
        raise
    except NetworkError as e:
        print(f"خطای شبکه: {e}")
        raise
    except Exception as e:
        print(f"خطا در main: {e}")
        raise
    finally:
        try:
            print("توقف ربات...")
            conn.close()
            print("اتصال دیتابیس بسته شد.")
        except Exception as e:
            print(f"خطا در توقف ربات یا بستن دیتابیس: {e}")

if __name__ == "__main__":
    try:
        print("اجرای ربات شروع شد...")
        main()
    except Exception as e:
        print(f"خطا در اجرای اصلی: {e}")
