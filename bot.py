from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ConversationHandler,
    filters, ContextTypes, Application
)
import sqlite3
import os
import asyncio
import json
from datetime import datetime
from keep_alive import keep_alive
from fastapi import FastAPI, Request
import atexit  # اضافه کردن ماژول atexit

# تعریف FastAPI برای Webhook
app = FastAPI()

# تعریف مراحل مکالمه
CLASS_SELECTION, AGE_SELECTION, NAME_INPUT, PHONE_INPUT, GETDB_PASSWORD = range(5)

# راه‌اندازی دیتابیس
try:
    conn = sqlite3.connect("data.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            class TEXT,
            age_range TEXT,
            name TEXT,
            phone TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
except sqlite3.Error as e:
    print(f"خطای دیتابیس: {e}")
    exit(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت دستور /start و نمایش منوی کلاس‌ها"""
    try:
        await update.message.reply_text(
            "سلام به باشگاه رباتیک موسیتو خوش آمدید! 😊\n"
            "باشگاه رباتیک موسیتو، جایی برای ساختن آینده‌ای پیشرفته با دست‌های کوچک اما اندیشه‌های بزرگ است. 🫡"
        )
        
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
            if not (phone.startswith("+") and phone[1:].isdigit() or phone.isdigit()) or len(phone) < 7:
                await update.message.reply_text("لطفاً شماره تماس معتبر وارد کنید یا از دکمه اشتراک استفاده کنید. 😊")
                return PHONE_INPUT
        
        user_id = update.effective_user.id
        selected_class = context.user_data.get("class")
        age_range = context.user_data.get("age_range")
        name = context.user_data.get("name")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            c.execute("INSERT OR REPLACE INTO users (id, class, age_range, name, phone, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                     (user_id, selected_class, age_range, name, phone, timestamp))
            conn.commit()
        except sqlite3.Error as e:
            await update.message.reply_text("خطایی در ذخیره‌سازی اطلاعات رخ داد. لطفاً دوباره امتحان کنید.")
            print(f"خطای دیتابیس در get_phone: {e}")
            return ConversationHandler.END  # اصلاح خطا
        
        await update.message.reply_text(
            "✅ ممنون از ثبت اطلاعات! 😊\n"
            "برای اطلاعات بیشتر، ما را در اینستاگرام دنبال کنید:\n"
            "لینک: https://www.instagram.com/ircstem?igsh=dXVvaGpnbTBkYnoy\n"
            "آیدی: @ircstem",
            reply_markup=ReplyKeyboardRemove()
        )
        
        await update.message.reply_text(
            "باشگاه رباتیک موسیتو با هدف پرورش نسل خلاق، نوآور و آشنا با فناوری‌های نوین، فعالیت خود را در حوزه آموزش رباتیک و هوش مصنوعی آغاز کرده و تاکنون میزبان صدها دانش‌آموز علاقه‌مند بوده است. "
            "در این باشگاه، کودکان و نوجوانان با مباحث پایه تا پیشرفته رباتیک، برنامه‌نویسی، الکترونیک، طراحی و ساخت ربات‌های واقعی آشنا می‌شوند و مهارت‌های عملی خود را در فضایی آموزشی، پویا و سرگرم‌کننده ارتقا می‌دهند."
        )
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        print(f"خطا در get_phone: {e}")
        return ConversationHandler.END

async def getdb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت دستور /getdb و درخواست رمز عبور"""
    try:
        await update.message.reply_text(
            "لطفاً رمز عبور را وارد کنید:",
            reply_markup=ReplyKeyboardRemove()
        )
        return GETDB_PASSWORD
    except Exception as e:
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        print(f"خطا در getdb: {e}")
        return ConversationHandler.END

async def verify_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تأیید رمز عبور و ارسال فایل JSON"""
    try:
        password = update.message.text.strip()
        if password != "102030":
            await update.message.reply_text("رمز عبور نادرست است. 😊")
            return ConversationHandler.END
        
        try:
            c.execute("SELECT id, class, age_range, name, phone, timestamp FROM users")
            users = c.fetchall()
        except sqlite3.Error as e:
            await update.message.reply_text("خطایی در دریافت اطلاعات رخ داد.")
            print(f"خطای دیتابیس در verify_password: {e}")
            return ConversationHandler.END
        
        users_list = [
            {
                "id": user[0],
                "class": user[1],
                "age_range": user[2],
                "name": user[3],
                "phone": user[4],
                "timestamp": user[5]
            } for user in users
        ]
        
        json_file_path = "users_data.json"
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(users_list, f, ensure_ascii=False, indent=4)
        
        with open(json_file_path, "rb") as f:
            await update.message.reply_document(document=f, filename="users_data.json")
        
        os.remove(json_file_path)
        
        await update.message.reply_text("فایل اطلاعات کاربران با موفقیت ارسال شد.")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        print(f"خطا در verify_password: {e}")
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

# تابع بررسی قفل
def acquire_lock():
    lock_file = "bot.lock"
    if os.path.exists(lock_file):
        print("خطا: یک نمونه دیگر از ربات در حال اجراست.")
        exit(1)
    with open(lock_file, "w") as f:
        f.write(str(os.getpid()))
    return lock_file

# تابع حذف قفل
def release_lock(lock_file):
    if os.path.exists(lock_file):
        os.remove(lock_file)

# Webhook endpoint
@app.post("/webhook")
async def webhook(request: Request):
    update = Update.de_json(await request.json(), application.bot)
    await application.process_update(update)
    return {"status": "ok"}

# متغیر جهانی برای application
application = None

if __name__ == "__main__":
    try:
        lock_file = acquire_lock()
        atexit.register(release_lock, lock_file)
        keep_alive()
        TOKEN = os.environ.get("TOKEN")
        if not TOKEN:
            print("خطا: متغیر محیطی TOKEN تنظیم نشده است")
            exit(1)
        
        application = ApplicationBuilder().token(TOKEN).build()
        
        conv = ConversationHandler(
            entry_points=[
                CommandHandler("start", start),
                CommandHandler("getdb", getdb)
            ],
            states={
                CLASS_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_class)],
                AGE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
                NAME_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
                PHONE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND | filters.CONTACT, get_phone)],
                GETDB_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_password)],
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        
        application.add_handler(conv)
        application.add_error_handler(error_handler)
        
        # تنظیم Webhook
        webhook_url = os.environ.get("WEBHOOK_URL", "https://last-mossito.onrender.com")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(application.bot.setWebhook(f"{webhook_url}/webhook"))
        
        # اجرای FastAPI با uvicorn
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
        
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

atexit.register(cleanup)
