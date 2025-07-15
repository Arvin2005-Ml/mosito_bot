from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ConversationHandler,
    filters, ContextTypes
)
import sqlite3
import os
import asyncio
from keep_alive import keep_alive

# تعریف مراحل مکالمه
CLASS_SELECTION, AGE_SELECTION, NAME_INPUT, PHONE_INPUT = range(4)

# راه‌اندازی دیتابیس
try:
    conn = sqlite3.connect("data.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, class TEXT, age_range TEXT, name TEXT, phone TEXT)")
    conn.commit()
except sqlite3.Error as e:
    print(f"خطای دیتابیس: {e}")
    exit(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت دستور /start و نمایش منوی کلاس‌ها"""
    try:
        await update.message.reply_text("سلام به باشگاه موسینو خوش آمدید! 😊")
        
        # تعریف گزینه‌های کلاس (هر کدام یک دوره جداگانه)
        class_options = [
            ["کلاس آموزشی رباتیک", "کلاس آموزشی پایتون"],
            ["کلاس آموزشی هوش مصنوعی", "کلاس زبان انگلیسی تخصصی رباتیک"],
            ["دوره‌های آموزشی سلول خورشیدی"]
        ]
        reply_keyboard = ReplyKeyboardMarkup(class_options, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "لطفاً یکی از دوره‌های آموزشی زیر را انتخاب کنید:",
            reply_markup=reply_keyboard
        )
        return CLASS_SELECTION
    except Exception as e:
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        print(f"خطا در start: {e}")
        return ConversationHandler.END

async def get_class(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت انتخاب دوره و اعتبارسنجی"""
    try:
        selected_class = update.message.text
        valid_classes = [
            "کلاس آموزشی رباتیک", "کلاس آموزشی پایتون",
            "کلاس آموزشی هوش مصنوعی", "کلاس زبان انگلیسی تخصصی رباتیک",
            "دوره‌های آموزشی سلول خورشیدی"
        ]
        
        if selected_class not in valid_classes:
            await update.message.reply_text("لطفاً فقط یکی از دوره‌های منو را انتخاب کنید. 😊")
            return CLASS_SELECTION
        
        context.user_data["class"] = selected_class
        
        # تعریف بازه‌های سنی
        age_options = [
            ["8-10 سال", "10-14 سال"],
            ["14-15 سال", "20-35 سال"]
        ]
        reply_keyboard = ReplyKeyboardMarkup(age_options, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "شما چند سال سن دارید؟ لطفاً بازه سنی خود را انتخاب کنید:",
            reply_markup=reply_keyboard
        )
        return AGE_SELECTION
    except Exception as e:
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        print(f"خطا در get_class: {e}")
        return ConversationHandler.END

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت انتخاب سن و اعتبارسنجی"""
    try:
        age_range = update.message.text
        valid_ages = ["8-10 سال", "10-14 سال", "14-15 سال", "20-35 سال"]
        
        if age_range not in valid_ages:
            await update.message.reply_text("لطفاً فقط یکی از بازه‌های سنی منو را انتخاب کنید. 😊")
            return AGE_SELECTION
        
        selected_class = context.user_data.get("class")
        
        # بررسی محدودیت سنی برای دوره هوش مصنوعی
        if selected_class == "کلاس آموزشی هوش مصنوعی" and age_range == "8-10 سال":
            class_options = [
                ["کلاس آموزشی رباتیک", "کلاس آموزشی پایتون"],
                ["کلاس زبان انگلیسی تخصصی رباتیک", "دوره‌های آموزشی سلول خورشیدی"]
            ]
            await update.message.reply_text(
                "متأسفیم، دوره هوش مصنوعی برای بازه سنی 8-10 سال مناسب نیست. لطفاً دوره دیگری انتخاب کنید.",
                reply_markup=ReplyKeyboardMarkup(class_options, one_time_keyboard=True, resize_keyboard=True)
            )
            return CLASS_SELECTION
        
        context.user_data["age_range"] = age_range
        
        # درخواست نام
        await update.message.reply_text(
            "لطفاً نام خود را وارد کنید:",
            reply_markup=ReplyKeyboardRemove()
        )
        return NAME_INPUT
    except Exception as e:
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        print(f"خطا در get_age: {e}")
        return ConversationHandler.END

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت ورودی نام"""
    try:
        name = update.message.text.strip()
        if not name or len(name) < 2:
            await update.message.reply_text("لطفاً نام معتبر (حداقل 2 حرف) وارد کنید. 😊")
            return NAME_INPUT
        
        context.user_data["name"] = name
        
        # درخواست شماره تماس با دکمه اشتراک
        reply_keyboard = [[KeyboardButton("اشتراک شماره تماس", request_contact=True)]]
        await update.message.reply_text(
            "لطفاً شماره تماس خود را با استفاده از دکمه زیر به اشتراک بگذارید:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return PHONE_INPUT
    except Exception as e:
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        print(f"خطا در get_name: {e}")
        return ConversationHandler.END

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت ورودی شماره تماس"""
    try:
        phone = None
        if update.message.contact:
            phone = update.message.contact.phone_number
        else:
            phone = update.message.text.strip()
            # اعتبارسنجی ساده شماره تماس
            if not (phone.startswith("+") and phone[1:].isdigit() or phone.isdigit()) or len(phone) < 7:
                await update.message.reply_text("لطفاً شماره تماس معتبر وارد کنید یا از دکمه اشتراک استفاده کنید. 😊")
                return PHONE_INPUT
        
        user_id = update.effective_user.id
        selected_class = context.user_data.get("class")
        age_range = context.user_data.get("age_range")
        name = context.user_data.get("name")
        
        # ذخیره اطلاعات در دیتابیس
        try:
            c.execute("INSERT OR REPLACE INTO users (id, class, age_range, name, phone) VALUES (?, ?, ?, ?, ?)",
                     (user_id, selected_class, age_range, name, phone))
            conn.commit()
        except sqlite3.Error as e:
            await update.message.reply_text("خطایی در ذخیره‌سازی اطلاعات رخ داد. لطفاً دوباره امتحان کنید.")
            print(f"خطای دیتابیس در get_phone: {e}")
            return ConversationHandler.END
        
        # ارسال لینک اینستاگرام و پیام تشکر
        await update.message.reply_text(
            "✅ ممنون از ثبت اطلاعات! 😊\n"
            "برای اطلاعات بیشتر، ما را در اینستاگرام دنبال کنید:\n"
            "لینک: https://www.instagram.com/musino_academy\n"
            "آیدی: @MusinoAcademy",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        print(f"خطا در get_phone: {e}")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت دستور /cancel"""
    try:
        await update.message.reply_text("لغو شد.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        print(f"خطا در cancel: {e}")
        return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """مدیریت خطاهای کلی"""
    try:
        if isinstance(context.error, telegram.error.Conflict):
            print("خطای Conflict: نمونه دیگری از ربات در حال اجراست")
            await update.message.reply_text("ربات در حال حاضر فعال است. لطفاً بعداً امتحان کنید.")
        else:
            print(f"خطا: {context.error}")
            if update and update.message:
                await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
    except Exception as e:
        print(f"خطا در error_handler: {e}")

if __name__ == "__main__":
    try:
        keep_alive()
        TOKEN = os.environ.get("TOKEN")
        if not TOKEN:
            print("خطا: متغیر محیطی TOKEN تنظیم نشده است")
            exit(1)
        
        app = ApplicationBuilder().token(TOKEN).build()
        
        conv = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states={
                CLASS_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_class)],
                AGE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
                NAME_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
                PHONE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND | filters.CONTACT, get_phone)],
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        
        app.add_handler(conv)
        app.add_error_handler(error_handler)
        
        # اجرای polling با توقف صحیح
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(app.run_polling(allowed_updates=Update.ALL_TYPES))
        finally:
            loop.run_until_complete(app.updater.stop())
            loop.run_until_complete(app.stop())
            loop.close()
    except Exception as e:
        print(f"خطا در main: {e}")
        exit(1)

# بستن اتصال دیتابیس هنگام خروج
def cleanup():
    try:
        conn.close()
        print("اتصال دیتابیس بسته شد")
    except Exception as e:
        print(f"خطا در بستن دیتابیس: {e}")

import atexit
atexit.register(cleanup)
