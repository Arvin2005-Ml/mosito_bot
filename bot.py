import telegram
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
from fastapi import FastAPI, Request, HTTPException
import atexit
import uvicorn
import pandas as pd
import requests
import jdatetime
from datetime import datetime as dt

# تعریف FastAPI برای Webhook
fastapi_app = FastAPI()

# مسیر ریشه
@fastapi_app.get("/")
async def root():
    return {"message": "خوش اومدی به ربات موسیتو! 😎 برای آپدیت‌های ربات از /webhook استفاده کن."}

@fastapi_app.get("/webhook")
async def webhook_get():
    return {"message": "اینجا فقط درخواست‌های POST از تلگرام قبول می‌کنیم! 😊"}

@fastapi_app.get("/db")
async def get_db(password: str = None):
    if password != "102030":
        raise HTTPException(status_code=403, detail="رمز اشتباهه! 😅")
    try:
        c.execute("SELECT id, class, age_range, name, phone, timestamp FROM users")
        users = c.fetchall()
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
        return users_list
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"خطا تو دیتابیس: {str(e)}")

# مسیر برای دریافت لاگ‌های ورود و خروج
@fastapi_app.post("/attendance")
async def receive_attendance(request: Request):
    try:
        data = await request.json()
        events = data.get("events", [])
        for event in events:
            name = event.get("name", "")
            user_id = name.split("_")[-1] if "_" in name else ""
            timestamp = event.get("timestamp", "")
            event_type = event.get("event_type", "")
            duration = event.get("duration", 0)
            c.execute("INSERT INTO attendance_logs (user_id, name, timestamp, event_type, duration) VALUES (?, ?, ?, ?, ?)",
                     (user_id, name, timestamp, event_type, duration))
        conn.commit()
        return {"status": "ok", "message": "لاگ‌های ورود و خروج با موفقیت دریافت شد! 😊"}
    except Exception as e:
        print(f"خطا در دریافت لاگ‌های ورود و خروج: {e}")
        raise HTTPException(status_code=500, detail=f"خطا تو پردازش لاگ‌ها: {str(e)}")

# تعریف مراحل مکالمه
CLASS_SELECTION, AGE_SELECTION, NAME_INPUT, PHONE_INPUT, GETDB_PASSWORD, MANAGE_PASSWORD, BRANCH_SELECTION, MANAGE_MENU, ADD_COURSE_METHOD, ADD_COURSE_MANUAL, EDIT_COURSE, VIEW_COURSES, VIEW_ABSENTEES, CHANGE_BRANCH = range(14)

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
    c.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT,
            participants TEXT,
            days TEXT,
            start_date TEXT,
            end_date TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            name TEXT,
            timestamp TEXT,
            event_type TEXT,
            duration INTEGER
        )
    """)
    conn.commit()
    print("دیتابیس با موفقیت راه‌اندازی شد! 🚀")
except sqlite3.Error as e:
    print(f"خطا تو راه‌اندازی دیتابیس: {e}")
    exit(1)

# لیست شعبه‌ها
BRANCHES = ["باغ کتاب", "چیتگر", "ایران شهر", "قلهک"]

# تابع تبدیل تاریخ شمسی به میلادی
def shamsi_to_miladi(date_str):
    try:
        if "/" in date_str:
            year, month, day = map(int, date_str.split("/"))
            j_date = jdatetime.date(year, month, day)
            g_date = j_date.togregorian()
            return g_date.strftime("%Y-%m-%d")
        else:
            # فرض می‌کنیم تاریخ میلادی است
            dt.strptime(date_str, "%Y-%m-%d")
            return date_str
    except ValueError:
        return None

# تابع تبدیل تاریخ میلادی به شمسی برای نمایش
def miladi_to_shamsi(date_str):
    try:
        g_date = dt.strptime(date_str, "%Y-%m-%d")
        j_date = jdatetime.date.fromgregorian(date=g_date)
        return f"{j_date.year}/{j_date.month:02d}/{j_date.day:02d}"
    except ValueError:
        return date_str

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        print(f"دریافت /start از کاربر {update.effective_user.id}")
        await update.message.reply_text(
            "سلام به ربات موسیتو خوش اومدی! 😄\n"
            "اینجا جاییه که آینده با دستای کوچیک و فکرای بزرگ ساخته میشه! 🚀"
        )
        
        class_options = [
            ["کلاس رباتیک", "کلاس پایتون"],
            ["کلاس هوش مصنوعی", "کلاس زبان تخصصی رباتیک"],
            ["دوره‌های سلول خورشیدی", "بازگشت ⬅️"]
        ]
        reply_keyboard = ReplyKeyboardMarkup(class_options, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "یکی از دوره‌های جذاب زیر رو انتخاب کن: 😊",
            reply_markup=reply_keyboard
        )
        return CLASS_SELECTION
    except Exception as e:
        print(f"خطا تو start برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("اوپس! یه مشکلی پیش اومد. دوباره امتحان کن! 😅")
        return ConversationHandler.END

async def manage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        print(f"کاربر {update.effective_user.id} دستور /manage رو زد")
        await update.message.reply_text(
            "رمز عبور رو وارد کن تا بریم تو بخش مدیریت! 🔐",
            reply_markup=ReplyKeyboardRemove()
        )
        return MANAGE_PASSWORD
    except Exception as e:
        print(f"خطا تو manage برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("اوپس! یه مشکلی پیش اومد. دوباره امتحان کن! 😅")
        return ConversationHandler.END

async def verify_manage_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        password = update.message.text.strip()
        print(f"کاربر {update.effective_user.id} رمز مدیریت رو وارد کرد: {password}")
        if password != "102030":
            await update.message.reply_text("رمز اشتباهه! یه بار دیگه امتحان کن! 😊")
            return ConversationHandler.END
        
        reply_keyboard = ReplyKeyboardMarkup([BRANCHES + ["بازگشت ⬅️"]], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "حالا کدوم شعبه رو می‌خوای مدیریت کنی؟ 🏢",
            reply_markup=reply_keyboard
        )
        return BRANCH_SELECTION
    except Exception as e:
        print(f"خطا تو verify_manage_password برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("اوپس! یه مشکلی پیش اومد. دوباره امتحان کن! 😅")
        return ConversationHandler.END

async def select_branch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        branch = update.message.text
        print(f"کاربر {update.effective_user.id} شعبه رو انتخاب کرد: {branch}")
        if branch == "بازگشت ⬅️":
            await update.message.reply_text(
                "رمز عبور رو دوباره وارد کن: 🔐",
                reply_markup=ReplyKeyboardRemove()
            )
            return MANAGE_PASSWORD
        if branch not in BRANCHES:
            await update.message.reply_text("لطفاً فقط یکی از شعبه‌های موجود رو انتخاب کن! 😊")
            return BRANCH_SELECTION
        
        context.user_data["branch"] = branch
        manage_options = [
            ["افزودن دوره جدید", "مشاهده و ویرایش دوره‌ها"],
            ["نمایش غایبین", "تغییر شعبه"],
            ["بازگشت ⬅️"]
        ]
        reply_keyboard = ReplyKeyboardMarkup(manage_options, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            f"شعبه {branch} انتخاب شد! حالا چیکار می‌خوای بکنی؟ 😎",
            reply_markup=reply_keyboard
        )
        return MANAGE_MENU
    except Exception as e:
        print(f"خطا تو select_branch برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("اوپس! یه مشکلی پیش اومد. دوباره امتحان کن! 😅")
        return ConversationHandler.END

async def manage_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        choice = update.message.text
        print(f"کاربر {update.effective_user.id} گزینه مدیریت رو انتخاب کرد: {choice}")
        if choice == "بازگشت ⬅️":
            reply_keyboard = ReplyKeyboardMarkup([BRANCHES + ["بازگشت ⬅️"]], one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "خب، کدوم شعبه رو می‌خوای؟ 🏢",
                reply_markup=reply_keyboard
            )
            return BRANCH_SELECTION
        elif choice == "افزودن دوره جدید":
            reply_keyboard = [["فایل اکسل", "دستی"], ["بازگشت ⬅️"]]
            await update.message.reply_text(
                "می‌خوای دوره رو چطور اضافه کنی؟ 📝",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
            )
            return ADD_COURSE_METHOD
        elif choice == "مشاهده و ویرایش دوره‌ها":
            branch = context.user_data.get("branch")
            c.execute("SELECT id, start_date, end_date FROM courses WHERE branch = ?", (branch,))
            courses = c.fetchall()
            if not courses:
                await update.message.reply_text("هیچ دوره‌ای تو این شعبه ثبت نشده! 😕")
                return MANAGE_MENU
            reply_keyboard = [[str(course[0])] for course in courses] + [["بازگشت ⬅️"]]
            await update.message.reply_text(
                "یکی از دوره‌ها رو انتخاب کن: 📚",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
            )
            return VIEW_COURSES
        elif choice == "نمایش غایبین":
            return await view_absentees(update, context)
        elif choice == "تغییر شعبه":
            reply_keyboard = ReplyKeyboardMarkup([BRANCHES + ["بازگشت ⬅️"]], one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "خب، کدوم شعبه جدید رو می‌خوای؟ 🏢",
                reply_markup=reply_keyboard
            )
            return BRANCH_SELECTION
        else:
            await update.message.reply_text("لطفاً فقط یکی از گزینه‌های منو رو انتخاب کن! 😊")
            return MANAGE_MENU
    except Exception as e:
        print(f"خطا تو manage_menu برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("اوپس! یه مشکلی پیش اومد. دوباره امتحان کن! 😅")
        return ConversationHandler.END

async def add_course_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        method = update.message.text
        print(f"کاربر {update.effective_user.id} روش افزودن دوره رو انتخاب کرد: {method}")
        if method == "بازگشت ⬅️":
            return await manage_menu(update, context)
        elif method == "فایل اکسل":
            await update.message.reply_text(
                "یه فایل اکسل آپلود کن که شامل ستون‌های زیر باشه:\n"
                "participants, days, start_date, end_date\n"
                "📌 تاریخ‌ها می‌تونن شمسی (YYYY/MM/DD) یا میلادی (YYYY-MM-DD) باشن!",
                reply_markup=ReplyKeyboardRemove()
            )
            return ADD_COURSE_METHOD
        elif method == "دستی":
            await update.message.reply_text(
                "اسامی افراد حاضر در دوره رو وارد کن (با Enter از هم جداشون کن): 😊",
                reply_markup=ReplyKeyboardRemove()
            )
            context.user_data["course_data"] = {}
            return ADD_COURSE_MANUAL
        else:
            await update.message.reply_text("لطفاً فقط یکی از گزینه‌های منو رو انتخاب کن! 😊")
            return ADD_COURSE_METHOD
    except Exception as e:
        print(f"خطا تو add_course_method برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("اوپس! یه مشکلی پیش اومد. دوباره امتحان کن! 😅")
        return ConversationHandler.END

async def add_course_excel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        if not update.message.document:
            await update.message.reply_text("لطفاً یه فایل اکسل آپلود کن! 📂")
            return ADD_COURSE_METHOD
        file = await update.message.document.get_file()
        file_path = f"temp_{update.effective_user.id}.xlsx"
        await file.download_to_drive(file_path)
        
        required_columns = ["participants", "days", "start_date", "end_date"]
        try:
            df = pd.read_excel(file_path)
            if not all(col in df.columns for col in required_columns):
                missing = [col for col in required_columns if col not in df.columns]
                await update.message.reply_text(f"این ستون‌ها تو فایلت نیستن: {', '.join(missing)} 😕")
                os.remove(file_path)
                return ADD_COURSE_METHOD
            extra_columns = [col for col in df.columns if col not in required_columns]
            if extra_columns:
                await update.message.reply_text(f"این ستون‌های اضافی حذف شدن: {', '.join(extra_columns)} 🗑️")
                df = df[required_columns]
            
            branch = context.user_data.get("branch")
            for _, row in df.iterrows():
                start_date = shamsi_to_miladi(str(row["start_date"]))
                end_date = shamsi_to_miladi(str(row["end_date"]))
                if not start_date or not end_date:
                    await update.message.reply_text("یکی از تاریخ‌ها فرمت درستی نداره! شمسی (YYYY/MM/DD) یا میلادی (YYYY-MM-DD) وارد کن. 😊")
                    os.remove(file_path)
                    return ADD_COURSE_METHOD
                c.execute("INSERT INTO courses (branch, participants, days, start_date, end_date) VALUES (?, ?, ?, ?, ?)",
                         (branch, str(row["participants"]), str(row["days"]), start_date, end_date))
            conn.commit()
            await update.message.reply_text("دوره‌ها با موفقیت اضافه شدن! 🎉 حالا چیکار کنیم؟")
            os.remove(file_path)
            return await manage_menu(update, context)
        except Exception as e:
            await update.message.reply_text(f"خطا تو پردازش فایل اکسل: {str(e)} 😕")
            os.remove(file_path)
            return ADD_COURSE_METHOD
    except Exception as e:
        print(f"خطا تو add_course_excel برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("اوپس! یه مشکلی پیش اومد. دوباره امتحان کن! 😅")
        return ConversationHandler.END

async def add_course_manual(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        text = update.message.text.strip()
        if text == "بازگشت ⬅️":
            context.user_data.pop("course_data", None)
            reply_keyboard = [["فایل اکسل", "دستی"], ["بازگشت ⬅️"]]
            await update.message.reply_text(
                "می‌خوای دوره رو چطور اضافه کنی؟ 📝",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
            )
            return ADD_COURSE_METHOD
        course_data = context.user_data.get("course_data", {})
        if "participants" not in course_data:
            course_data["participants"] = text
            await update.message.reply_text(
                "روزهای برگزاری دوره رو وارد کن (با کاما جدا کن، مثلاً: شنبه,یکشنبه): 📅",
                reply_markup=ReplyKeyboardMarkup([["بازگشت ⬅️"]], one_time_keyboard=True, resize_keyboard=True)
            )
            context.user_data["course_data"] = course_data
            return ADD_COURSE_MANUAL
        elif "days" not in course_data:
            course_data["days"] = text
            await update.message.reply_text(
                "تاریخ شروع دوره رو وارد کن (شمسی YYYY/MM/DD یا میلادی YYYY-MM-DD): 📅",
                reply_markup=ReplyKeyboardMarkup([["بازگشت ⬅️"]], one_time_keyboard=True, resize_keyboard=True)
            )
            context.user_data["course_data"] = course_data
            return ADD_COURSE_MANUAL
        elif "start_date" not in course_data:
            start_date = shamsi_to_miladi(text)
            if not start_date:
                await update.message.reply_text(
                    "فرمت تاریخ درست نیست! شمسی (YYYY/MM/DD) یا میلادی (YYYY-MM-DD) وارد کن. 😊",
                    reply_markup=ReplyKeyboardMarkup([["بازگشت ⬅️"]], one_time_keyboard=True, resize_keyboard=True)
                )
                return ADD_COURSE_MANUAL
            course_data["start_date"] = start_date
            await update.message.reply_text(
                "تاریخ پایان دوره رو وارد کن (شمسی YYYY/MM/DD یا میلادی YYYY-MM-DD): 📅",
                reply_markup=ReplyKeyboardMarkup([["بازگشت ⬅️"]], one_time_keyboard=True, resize_keyboard=True)
            )
            context.user_data["course_data"] = course_data
            return ADD_COURSE_MANUAL
        else:
            end_date = shamsi_to_miladi(text)
            if not end_date:
                await update.message.reply_text(
                    "فرمت تاریخ درست نیست! شمسی (YYYY/MM/DD) یا میلادی (YYYY-MM-DD) وارد کن. 😊",
                    reply_markup=ReplyKeyboardMarkup([["بازگشت ⬅️"]], one_time_keyboard=True, resize_keyboard=True)
                )
                return ADD_COURSE_MANUAL
            course_data["end_date"] = end_date
            branch = context.user_data.get("branch")
            c.execute("INSERT INTO courses (branch, participants, days, start_date, end_date) VALUES (?, ?, ?, ?, ?)",
                     (branch, course_data["participants"], course_data["days"], course_data["start_date"], course_data["end_date"]))
            conn.commit()
            await update.message.reply_text("دوره جدید با موفقیت اضافه شد! 🎉 حالا چیکار کنیم؟")
            context.user_data.pop("course_data", None)
            return await manage_menu(update, context)
    except Exception as e:
        print(f"خطا تو add_course_manual برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("اوپس! یه مشکلی پیش اومد. دوباره امتحان کن! 😅")
        return ConversationHandler.END

async def view_courses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        course_id = update.message.text
        if course_id == "بازگشت ⬅️":
            return await manage_menu(update, context)
        branch = context.user_data.get("branch")
        c.execute("SELECT * FROM courses WHERE branch = ? AND id = ?", (branch, course_id))
        course = c.fetchone()
        if not course:
            await update.message.reply_text("این دوره پیدا نشد! 😕")
            return MANAGE_MENU
        context.user_data["selected_course"] = course
        reply_keyboard = [["افراد حاضر", "روزهای برگزاری"], ["تاریخ شروع", "تاریخ پایان"], ["بازگشت ⬅️"]]
        await update.message.reply_text(
            f"دوره شماره {course[0]}:\n"
            f"افراد: {course[2]}\n"
            f"روزها: {course[3]}\n"
            f"شروع: {miladi_to_shamsi(course[4])}\n"
            f"پایان: {miladi_to_shamsi(course[5])}\n"
            "کدوم بخش رو می‌خوای ویرایش کنی؟ ✏️",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return EDIT_COURSE
    except Exception as e:
        print(f"خطا تو view_courses برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("اوپس! یه مشکلی پیش اومد. دوباره امتحان کن! 😅")
        return ConversationHandler.END

async def edit_course(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        field = update.message.text
        print(f"کاربر {update.effective_user.id} می‌خواد این فیلد رو ویرایش کنه: {field}")
        if field == "بازگشت ⬅️":
            branch = context.user_data.get("branch")
            c.execute("SELECT id, start_date, end_date FROM courses WHERE branch = ?", (branch,))
            courses = c.fetchall()
            if not courses:
                await update.message.reply_text("هیچ دوره‌ای تو این شعبه ثبت نشده! 😕")
                return MANAGE_MENU
            reply_keyboard = [[str(course[0])] for course in courses] + [["بازگشت ⬅️"]]
            await update.message.reply_text(
                "یکی از دوره‌ها رو انتخاب کن: 📚",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
            )
            return VIEW_COURSES
        context.user_data["edit_field"] = field
        field_map = {
            "افراد حاضر": "participants",
            "روزهای برگزاری": "days",
            "تاریخ شروع": "start_date",
            "تاریخ پایان": "end_date"
        }
        if field not in field_map:
            await update.message.reply_text("لطفاً فقط یکی از گزینه‌های منو رو انتخاب کن! 😊")
            return EDIT_COURSE
        if field in ["تاریخ شروع", "تاریخ پایان"]:
            await update.message.reply_text(
                f"مقدار جدید برای {field} رو وارد کن (شمسی YYYY/MM/DD یا میلادی YYYY-MM-DD): 📅",
                reply_markup=ReplyKeyboardMarkup([["بازگشت ⬅️"]], one_time_keyboard=True, resize_keyboard=True)
            )
        else:
            await update.message.reply_text(
                f"مقدار جدید برای {field} رو وارد کن: ✏️",
                reply_markup=ReplyKeyboardMarkup([["بازگشت ⬅️"]], one_time_keyboard=True, resize_keyboard=True)
            )
        return EDIT_COURSE
    except Exception as e:
        print(f"خطا تو edit_course برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("اوپس! یه مشکلی پیش اومد. دوباره امتحان کن! 😅")
        return ConversationHandler.END

async def update_course(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        new_value = update.message.text.strip()
        if new_value == "بازگشت ⬅️":
            course = context.user_data.get("selected_course")
            reply_keyboard = [["افراد حاضر", "روزهای برگزاری"], ["تاریخ شروع", "تاریخ پایان"], ["بازگشت ⬅️"]]
            await update.message.reply_text(
                f"دوره شماره {course[0]}:\n"
                f"افراد: {course[2]}\n"
                f"روزها: {course[3]}\n"
                f"شروع: {miladi_to_shamsi(course[4])}\n"
                f"پایان: {miladi_to_shamsi(course[5])}\n"
                "کدوم بخش رو می‌خوای ویرایش کنی؟ ✏️",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
            )
            return EDIT_COURSE
        field = context.user_data.get("edit_field")
        course = context.user_data.get("selected_course")
        branch = context.user_data.get("branch")
        field_map = {
            "افراد حاضر": "participants",
            "روزهای برگزاری": "days",
            "تاریخ شروع": "start_date",
            "تاریخ پایان": "end_date"
        }
        db_field = field_map[field]
        if db_field in ["start_date", "end_date"]:
            new_value = shamsi_to_miladi(new_value)
            if not new_value:
                await update.message.reply_text(
                    "فرمت تاریخ درست نیست! شمسی (YYYY/MM/DD) یا میلادی (YYYY-MM-DD) وارد کن. 😊",
                    reply_markup=ReplyKeyboardMarkup([["بازگشت ⬅️"]], one_time_keyboard=True, resize_keyboard=True)
                )
                return EDIT_COURSE
        c.execute(f"UPDATE courses SET {db_field} = ? WHERE branch = ? AND id = ?",
                 (new_value, branch, course[0]))
        conn.commit()
        await update.message.reply_text(f"{field} با موفقیت به‌روزرسانی شد! 🎉 حالا چیکار کنیم؟")
        return await manage_menu(update, context)
    except Exception as e:
        print(f"خطا تو update_course برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("اوپس! یه مشکلی پیش اومد. دوباره امتحان کن! 😅")
        return ConversationHandler.END

async def view_absentees(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        branch = context.user_data.get("branch")
        c.execute("SELECT id, participants, days, start_date, end_date FROM courses WHERE branch = ?", (branch,))
        courses = c.fetchall()
        if not courses:
            await update.message.reply_text("هیچ دوره‌ای تو این شعبه ثبت نشده! 😕")
            return MANAGE_MENU
        
        today = dt.now().strftime("%Y-%m-%d")
        today_day = jdatetime.date.fromgregorian(date=dt.now()).strftime("%A")  # روز هفته به فارسی
        
        absentees = []
        for course in courses:
            course_id, participants, days, start_date, end_date = course
            if start_date <= today <= end_date and today_day in days.split(","):
                participants_list = participants.split("\n")
                c.execute("SELECT user_id FROM attendance_logs WHERE event_type = 'entry' AND timestamp LIKE ?", (f"{today}%",))
                present_ids = [row[0] for row in c.fetchall()]
                absentees_list = [p for p in participants_list if p.split("_")[-1] not in present_ids]
                if absentees_list:
                    absentees.append(f"دوره شماره {course_id}: {', '.join(absentees_list)}")
        
        if not absentees:
            await update.message.reply_text("امروز هیچ غایبی نداریم! همه سر کلاس بودن! 😎")
        else:
            await update.message.reply_text("غایبین امروز:\n" + "\n".join(absentees))
        return await manage_menu(update, context)
    except Exception as e:
        print(f"خطا تو view_absentees برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("اوپس! یه مشکلی پیش اومد. دوباره امتحان کن! 😅")
        return ConversationHandler.END

async def get_class(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        selected_class = update.message.text
        print(f"کاربر {update.effective_user.id} کلاس رو انتخاب کرد: {selected_class}")
        if selected_class == "بازگشت ⬅️":
            await update.message.reply_text(
                "سلام به ربات موسیتو خوش اومدی! 😄\n"
                "اینجا جاییه که آینده با دستای کوچیک و فکرای بزرگ ساخته میشه! 🚀"
            )
            class_options = [
                ["کلاس رباتیک", "کلاس پایتون"],
                ["کلاس هوش مصنوعی", "کلاس زبان تخصصی رباتیک"],
                ["دوره‌های سلول خورشیدی", "بازگشت ⬅️"]
            ]
            await update.message.reply_text(
                "یکی از دوره‌های جذاب زیر رو انتخاب کن: 😊",
                reply_markup=ReplyKeyboardMarkup(class_options, one_time_keyboard=True, resize_keyboard=True)
            )
            return CLASS_SELECTION
        valid_classes = [
            "کلاس رباتیک", "کلاس پایتون",
            "کلاس هوش مصنوعی", "کلاس زبان تخصصی رباتیک",
            "دوره‌های سلول خورشیدی"
        ]
        
        if selected_class not in valid_classes:
            await update.message.reply_text("لطفاً فقط یکی از کلاس‌های منو رو انتخاب کن! 😊")
            return CLASS_SELECTION
        
        context.user_data["class"] = selected_class
        
        age_options = [
            ["8-10 سال", "10-14 سال"],
            ["14-15 سال", "20-35 سال"],
            ["بازگشت ⬅️"]
        ]
        reply_keyboard = ReplyKeyboardMarkup(age_options, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "چند سالته؟ یه بازه سنی انتخاب کن: 😄",
            reply_markup=reply_keyboard
        )
        return AGE_SELECTION
    except Exception as e:
        print(f"خطا تو get_class برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("اوپس! یه مشکلی پیش اومد. دوباره امتحان کن! 😅")
        return ConversationHandler.END

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        age_range = update.message.text
        print(f"کاربر {update.effective_user.id} بازه سنی رو انتخاب کرد: {age_range}")
        if age_range == "بازگشت ⬅️":
            class_options = [
                ["کلاس رباتیک", "کلاس پایتون"],
                ["کلاس هوش مصنوعی", "کلاس زبان تخصصی رباتیک"],
                ["دوره‌های سلول خورشیدی", "بازگشت ⬅️"]
            ]
            await update.message.reply_text(
                "یکی از دوره‌های جذاب زیر رو انتخاب کن: 😊",
                reply_markup=ReplyKeyboardMarkup(class_options, one_time_keyboard=True, resize_keyboard=True)
            )
            return CLASS_SELECTION
        valid_ages = ["8-10 سال", "10-14 سال", "14-15 سال", "20-35 سال"]
        
        if age_range not in valid_ages:
            await update.message.reply_text("لطفاً فقط یکی از بازه‌های سنی منو رو انتخاب کن! 😊")
            return AGE_SELECTION
        
        selected_class = context.user_data.get("class")
        
        if selected_class == "کلاس هوش مصنوعی" and age_range == "8-10 سال":
            class_options = [
                ["کلاس رباتیک", "کلاس پایتون"],
                ["کلاس زبان تخصصی رباتیک", "دوره‌های سلول خورشیدی"],
                ["بازگشت ⬅️"]
            ]
            await update.message.reply_text(
                "اوپس! هوش مصنوعی برای 8-10 سال مناسب نیست. یه کلاس دیگه انتخاب کن! 😊",
                reply_markup=ReplyKeyboardMarkup(class_options, one_time_keyboard=True, resize_keyboard=True)
            )
            return CLASS_SELECTION
        
        context.user_data["age_range"] = age_range
        
        await update.message.reply_text(
            "اسمت چیه؟ 😄",
            reply_markup=ReplyKeyboardMarkup([["بازگشت ⬅️"]], one_time_keyboard=True, resize_keyboard=True)
        )
        return NAME_INPUT
    except Exception as e:
        print(f"خطا تو get_age برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("اوپس! یه مشکلی پیش اومد. دوباره امتحان کن! 😅")
        return ConversationHandler.END

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        name = update.message.text.strip()
        print(f"کاربر {update.effective_user.id} اسم وارد کرد: {name}")
        if name == "بازگشت ⬅️":
            age_options = [
                ["8-10 سال", "10-14 سال"],
                ["14-15 سال", "20-35 سال"],
                ["بازگشت ⬅️"]
            ]
            await update.message.reply_text(
                "چند سالته؟ یه بازه سنی انتخاب کن: 😄",
                reply_markup=ReplyKeyboardMarkup(age_options, one_time_keyboard=True, resize_keyboard=True)
            )
            return AGE_SELECTION
        if not name or len(name) < 2:
            await update.message.reply_text("لطفاً یه اسم معتبر (حداقل 2 حرف) وارد کن! 😊")
            return NAME_INPUT
        
        context.user_data["name"] = name
        
        reply_keyboard = [[KeyboardButton("ارسال شماره تماس 📱", request_contact=True)], ["بازگشت ⬅️"]]
        await update.message.reply_text(
            "شماره تماست رو با دکمه زیر برام بفرست: 😄",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return PHONE_INPUT
    except Exception as e:
        print(f"خطا تو get_name برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("اوپس! یه مشکلی پیش اومد. دوباره امتحان کن! 😅")
        return ConversationHandler.END

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        if update.message.text == "بازگشت ⬅️":
            await update.message.reply_text(
                "اسمت چیه؟ 😄",
                reply_markup=ReplyKeyboardMarkup([["بازگشت ⬅️"]], one_time_keyboard=True, resize_keyboard=True)
            )
            return NAME_INPUT
        phone = None
        if update.message.contact:
            phone = update.message.contact.phone_number
            print(f"کاربر {update.effective_user.id} شماره تماس رو به اشتراک گذاشت: {phone}")
        else:
            phone = update.message.text.strip()
            print(f"کاربر {update.effective_user.id} شماره تماس وارد کرد: {phone}")
            if not (phone.startswith("+") and phone[1:].isdigit() or phone.isdigit()) or len(phone) < 7:
                await update.message.reply_text("لطفاً یه شماره تماس معتبر وارد کن یا از دکمه اشتراک استفاده کن! 😊")
                return PHONE_INPUT
        
        user_id = update.effective_user.id
        selected_class = context.user_data.get("class")
        age_range = context.user_data.get("age_range")
        name = context.user_data.get("name")
        timestamp = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            c.execute("INSERT INTO users (id, class, age_range, name, phone, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                     (user_id, selected_class, age_range, name, phone, timestamp))
            conn.commit()
            print(f"داده‌های کاربر {user_id} با موفقیت ذخیره شد")
        except sqlite3.Error as e:
            await update.message.reply_text("اوپس! خطایی تو ذخیره اطلاعات پیش اومد. دوباره امتحان کن! 😅")
            print(f"خطای دیتابیس تو get_phone برای کاربر {user_id}: {e}")
            return ConversationHandler.END
        
        await update.message.reply_text(
            "مرسی که اطلاعاتت رو ثبت کردی! 🎉\n"
            "برای خبرهای بیشتر، ما رو تو اینستا دنبال کن:\n"
            "لینک: https://www.instagram.com/ircstem?igsh=dXVvaGpnbTBkYnoy\n"
            "آیدی: @ircstem 😎",
            reply_markup=ReplyKeyboardRemove()
        )
        
        await update.message.reply_text(
            "باشگاه رباتیک موسیتو جاییه که بچه‌ها و جوونا با رباتیک، برنامه‌نویسی و تکنولوژی‌های باحال آشنا می‌شن! 🚀 "
            "ما کلی دانش‌آموز خلاق داریم که دارن چیزای جدید یاد می‌گیرن و آینده رو می‌سازن! 😄"
        )
        return ConversationHandler.END
    except Exception as e:
        print(f"خطا تو get_phone برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("اوپس! یه مشکلی پیش اومد. دوباره امتحان کن! 😅")
        return ConversationHandler.END

async def getdb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        print(f"کاربر {update.effective_user.id} دستور /getdb رو زد")
        await update.message.reply_text(
            "رمز عبور رو وارد کن: 🔐",
            reply_markup=ReplyKeyboardRemove()
        )
        return GETDB_PASSWORD
    except Exception as e:
        print(f"خطا تو getdb برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("اوپس! یه مشکلی پیش اومد. دوباره امتحان کن! 😅")
        return ConversationHandler.END

async def verify_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        password = update.message.text.strip()
        print(f"کاربر {update.effective_user.id} رمز رو وارد کرد: {password}")
        if password != "102030":
            await update.message.reply_text("رمز اشتباهه! یه بار دیگه امتحان کن! 😊")
            return ConversationHandler.END
        
        try:
            c.execute("SELECT id, class, age_range, name, phone, timestamp FROM users")
            users = c.fetchall()
            print(f"{len(users)} کاربر از دیتابیس دریافت شد")
        except sqlite3.Error as e:
            await update.message.reply_text("اوپس! خطایی تو دریافت اطلاعات پیش اومد. 😕")
            print(f"خطای دیتابیس تو verify_password برای کاربر {update.effective_user.id}: {e}")
            return ConversationHandler.END
        
        if not users:
            await update.message.reply_text("هیچ کاربری تو دیتابیس ثبت نشده! 😕")
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
        
        await update.message.reply_text("فایل اطلاعات کاربران برات ارسال شد! 🎉")
        return ConversationHandler.END
    except Exception as e:
        print(f"خطا تو verify_password برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("اوپس! یه مشکلی پیش اومد. دوباره امتحان کن! 😅")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        print(f"کاربر {update.effective_user.id} مکالمه رو کنسل کرد")
        await update.message.reply_text("مکالمه کنسل شد! 😊 اگه باز خواستی برگرد!", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    except Exception as e:
        print(f"خطا تو cancel برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("اوپس! یه مشکلی پیش اومد. دوباره امتحان کن! 😅")
        return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if isinstance(context.error, telegram.error.Conflict):
            print("خطای Conflict: یه نمونه دیگه از ربات داره اجرا می‌شه")
            if update and update.message:
                await update.message.reply_text("ربات الان مشغوله! یه کم دیگه امتحان کن! 😅")
        else:
            print(f"خطا برای کاربر {update.effective_user.id} تو پردازش: {context.error}")
            if update and update.message:
                await update.message.reply_text("اوپس! یه مشکلی پیش اومد. دوباره امتحان کن! 😅")
    except Exception as e:
        print(f"خطا تو error_handler برای کاربر {update.effective_user.id}: {e}")

def acquire_lock():
    lock_file = "bot.lock"
    if os.path.exists(lock_file):
        print("خطا: یه نمونه دیگه از ربات داره اجرا می‌شه")
        exit(1)
    with open(lock_file, "w") as f:
        f.write(str(os.getpid()))
    return lock_file

def release_lock(lock_file):
    if os.path.exists(lock_file):
        os.remove(lock_file)

@fastapi_app.post("/webhook")
async def webhook(request: Request):
    global application
    if application is None:
        print("اپلیکیشن راه‌اندازی نشده!")
        raise RuntimeError("اپلیکیشن راه‌اندازی نشده!")
    update = Update.de_json(await request.json(), application.bot)
    if update is None:
        print("آپدیت نامعتبر دریافت شد")
        return {"status": "error", "message": "آپدیت نامعتبر"}
    print(f"پردازش آپدیت: {update}")
    await application.process_update(update)
    return {"status": "ok"}

application = None

async def initialize_application():
    global application
    try:
        TOKEN = os.environ.get("TOKEN")
        if not TOKEN:
            print("خطا: متغیر محیطی TOKEN تنظیم نشده")
            exit(1)
        
        application = ApplicationBuilder().token(TOKEN).build()
        
        await application.initialize()
        print("اپلیکیشن با موفقیت راه‌اندازی شد! 🚀")
        
        conv = ConversationHandler(
            entry_points=[
                CommandHandler("start", start),
                CommandHandler("getdb", getdb),
                CommandHandler("manage", manage)
            ],
            states={
                CLASS_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_class)],
                AGE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
                NAME_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
                PHONE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND | filters.CONTACT, get_phone)],
                GETDB_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_password)],
                MANAGE_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_manage_password)],
                BRANCH_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_branch)],
                MANAGE_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, manage_menu)],
                ADD_COURSE_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_course_method), MessageHandler(filters.Document.ALL, add_course_excel)],
                ADD_COURSE_MANUAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_course_manual)],
                VIEW_COURSES: [MessageHandler(filters.TEXT & ~filters.COMMAND, view_courses)],
                EDIT_COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_course)],
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        
        application.add_handler(conv)
        application.add_error_handler(error_handler)
        print("هندلرها با موفقیت اضافه شدن! 😊")
        
        webhook_url = os.environ.get("WEBHOOK_URL", "https://last-mossito.onrender.com")
        if not webhook_url:
            print("خطا: متغیر محیطی WEBHOOK_URL تنظیم نشده")
            exit(1)
        await application.bot.setWebhook(f"{webhook_url}/webhook")
        print(f"Webhook تنظیم شد: {webhook_url}/webhook")
        
    except Exception as e:
        print(f"خطا تو راه‌اندازی اپلیکیشن: {e}")
        exit(1)

if __name__ == "__main__":
    try:
        lock_file = acquire_lock()
        atexit.register(release_lock, lock_file)
        keep_alive()
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(initialize_application())
        
        uvicorn.run(fastapi_app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
        
    except Exception as e:
        print(f"خطا تو main: {e}")
        exit(1)

def cleanup():
    try:
        conn.close()
        print("اتصال دیتابیس بسته شد")
    except Exception as e:
        print(f"خطا تو بستن دیتابیس: {e}")

atexit.register(cleanup)
