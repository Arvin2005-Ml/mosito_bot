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

# تعریف FastAPI برای Webhook
fastapi_app = FastAPI()

# مسیر ریشه
@fastapi_app.get("/")
async def root():
    return {"message": "Welcome to the Telegram Bot API. Use /webhook for bot updates."}

@fastapi_app.get("/webhook")
async def webhook_get():
    return {"message": "This endpoint only accepts POST requests from Telegram."}

@fastapi_app.get("/db")
async def get_db(password: str = None):
    if password != "102030":
        raise HTTPException(status_code=403, detail="Invalid password")
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
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# مسیر جدید برای دریافت لاگ‌های ورود و خروج
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
        return {"status": "ok", "message": "Attendance logs received"}
    except Exception as e:
        print(f"خطا در دریافت لاگ‌های ورود و خروج: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing attendance logs: {str(e)}")

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
            branch TEXT,
            course_number TEXT,
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
    print("Database initialized successfully")
except sqlite3.Error as e:
    print(f"خطای دیتابیس در راه‌اندازی: {e}")
    exit(1)

# لیست شعبه‌ها
BRANCHES = ["تهران", "اصفهان", "شیراز", "مشهد"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        print(f"Received /start from user {update.effective_user.id}")
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
        print(f"خطا در start برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

async def manage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        print(f"User {update.effective_user.id} requested /manage")
        await update.message.reply_text(
            "لطفاً رمز عبور را وارد کنید:",
            reply_markup=ReplyKeyboardRemove()
        )
        return MANAGE_PASSWORD
    except Exception as e:
        print(f"خطا در manage برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

async def verify_manage_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        password = update.message.text.strip()
        print(f"User {update.effective_user.id} entered manage password: {password}")
        if password != "102030":
            await update.message.reply_text("رمز عبور نادرست است. 😊")
            return ConversationHandler.END
        
        reply_keyboard = ReplyKeyboardMarkup([BRANCHES], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "لطفاً شعبه خود را انتخاب کنید:",
            reply_markup=reply_keyboard
        )
        return BRANCH_SELECTION
    except Exception as e:
        print(f"خطا در verify_manage_password برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

async def select_branch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        branch = update.message.text
        print(f"User {update.effective_user.id} selected branch: {branch}")
        if branch not in BRANCHES:
            await update.message.reply_text("لطفاً یکی از شعبه‌های موجود را انتخاب کنید. 😊")
            return BRANCH_SELECTION
        
        context.user_data["branch"] = branch
        manage_options = [
            ["افزودن دوره", "مشاهده و ویرایش دوره‌ها"],
            ["نمایش غایبین", "تغییر شعبه"]
        ]
        reply_keyboard = ReplyKeyboardMarkup(manage_options, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            f"شعبه {branch} انتخاب شد. لطفاً یکی از گزینه‌ها را انتخاب کنید:",
            reply_markup=reply_keyboard
        )
        return MANAGE_MENU
    except Exception as e:
        print(f"خطا در select_branch برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

async def manage_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        choice = update.message.text
        print(f"User {update.effective_user.id} selected manage option: {choice}")
        if choice == "افزودن دوره":
            reply_keyboard = [["فایل اکسل", "دستی"]]
            await update.message.reply_text(
                "لطفاً روش افزودن دوره را انتخاب کنید:",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
            )
            return ADD_COURSE_METHOD
        elif choice == "مشاهده و ویرایش دوره‌ها":
            branch = context.user_data.get("branch")
            c.execute("SELECT course_number FROM courses WHERE branch = ?", (branch,))
            courses = c.fetchall()
            if not courses:
                await update.message.reply_text("هیچ دوره‌ای برای این شعبه ثبت نشده است.")
                return MANAGE_MENU
            reply_keyboard = [[course[0] for course in courses]]
            await update.message.reply_text(
                "لطفاً دوره موردنظر را انتخاب کنید:",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
            )
            return VIEW_COURSES
        elif choice == "نمایش غایبین":
            return await view_absentees(update, context)
        elif choice == "تغییر شعبه":
            reply_keyboard = ReplyKeyboardMarkup([BRANCHES], one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "لطفاً شعبه جدید را انتخاب کنید:",
                reply_markup=reply_keyboard
            )
            return BRANCH_SELECTION
        else:
            await update.message.reply_text("لطفاً یکی از گزینه‌های منو را انتخاب کنید. 😊")
            return MANAGE_MENU
    except Exception as e:
        print(f"خطا در manage_menu برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

async def add_course_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        method = update.message.text
        print(f"User {update.effective_user.id} selected add course method: {method}")
        if method == "فایل اکسل":
            await update.message.reply_text(
                "لطفاً فایل اکسل را آپلود کنید (ستون‌ها: course_number, participants, days, start_date, end_date)",
                reply_markup=ReplyKeyboardRemove()
            )
            return ADD_COURSE_METHOD
        elif method == "دستی":
            await update.message.reply_text(
                "لطفاً شماره دوره را وارد کنید:",
                reply_markup=ReplyKeyboardRemove()
            )
            context.user_data["course_data"] = {}
            return ADD_COURSE_MANUAL
        else:
            await update.message.reply_text("لطفاً یکی از گزینه‌های منو را انتخاب کنید. 😊")
            return ADD_COURSE_METHOD
    except Exception as e:
        print(f"خطا در add_course_method برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

async def add_course_excel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        if not update.message.document:
            await update.message.reply_text("لطفاً یک فایل اکسل آپلود کنید.")
            return ADD_COURSE_METHOD
        file = await update.message.document.get_file()
        file_path = f"temp_{update.effective_user.id}.xlsx"
        await file.download_to_drive(file_path)
        
        required_columns = ["course_number", "participants", "days", "start_date", "end_date"]
        try:
            df = pd.read_excel(file_path)
            if not all(col in df.columns for col in required_columns):
                missing = [col for col in required_columns if col not in df.columns]
                await update.message.reply_text(f"ستون‌های زیر در فایل وجود ندارند: {', '.join(missing)}")
                os.remove(file_path)
                return ADD_COURSE_METHOD
            extra_columns = [col for col in df.columns if col not in required_columns]
            if extra_columns:
                await update.message.reply_text(f"ستون‌های اضافی حذف شدند: {', '.join(extra_columns)}")
                df = df[required_columns]
            
            branch = context.user_data.get("branch")
            for _, row in df.iterrows():
                c.execute("INSERT INTO courses (branch, course_number, participants, days, start_date, end_date) VALUES (?, ?, ?, ?, ?, ?)",
                         (branch, row["course_number"], row["participants"], row["days"], row["start_date"], row["end_date"]))
            conn.commit()
            await update.message.reply_text("دوره‌ها با موفقیت از فایل اکسل اضافه شدند.")
            os.remove(file_path)
            return await manage_menu(update, context)
        except Exception as e:
            await update.message.reply_text(f"خطا در پردازش فایل اکسل: {str(e)}")
            os.remove(file_path)
            return ADD_COURSE_METHOD
    except Exception as e:
        print(f"خطا در add_course_excel برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

async def add_course_manual(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        text = update.message.text.strip()
        course_data = context.user_data.get("course_data", {})
        if "course_number" not in course_data:
            course_data["course_number"] = text
            await update.message.reply_text("لطفاً اسامی افراد حاضر در دوره را وارد کنید (با Enter جدا کنید):")
            context.user_data["course_data"] = course_data
            return ADD_COURSE_MANUAL
        elif "participants" not in course_data:
            course_data["participants"] = text
            await update.message.reply_text("لطفاً روزهای برگزاری را وارد کنید (با Enter جدا کنید، مثلاً: شنبه,یکشنبه):")
            context.user_data["course_data"] = course_data
            return ADD_COURSE_MANUAL
        elif "days" not in course_data:
            course_data["days"] = text
            await update.message.reply_text("لطفاً تاریخ شروع دوره (YYYY-MM-DD) را وارد کنید:")
            context.user_data["course_data"] = course_data
            return ADD_COURSE_MANUAL
        elif "start_date" not in course_data:
            try:
                datetime.strptime(text, "%Y-%m-%d")
                course_data["start_date"] = text
                await update.message.reply_text("لطفاً تاریخ پایان دوره (YYYY-MM-DD) را وارد کنید:")
                context.user_data["course_data"] = course_data
                return ADD_COURSE_MANUAL
            except ValueError:
                await update.message.reply_text("لطفاً تاریخ را با فرمت YYYY-MM-DD وارد کنید.")
                return ADD_COURSE_MANUAL
        else:
            try:
                datetime.strptime(text, "%Y-%m-%d")
                course_data["end_date"] = text
                branch = context.user_data.get("branch")
                c.execute("INSERT INTO courses (branch, course_number, participants, days, start_date, end_date) VALUES (?, ?, ?, ?, ?, ?)",
                         (branch, course_data["course_number"], course_data["participants"], course_data["days"], course_data["start_date"], course_data["end_date"]))
                conn.commit()
                await update.message.reply_text("دوره با موفقیت اضافه شد.")
                context.user_data.pop("course_data", None)
                return await manage_menu(update, context)
            except ValueError:
                await update.message.reply_text("لطفاً تاریخ را با فرمت YYYY-MM-DD وارد کنید.")
                return ADD_COURSE_MANUAL
    except Exception as e:
        print(f"خطا در add_course_manual برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

async def view_courses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        course_number = update.message.text
        branch = context.user_data.get("branch")
        c.execute("SELECT * FROM courses WHERE branch = ? AND course_number = ?", (branch, course_number))
        course = c.fetchone()
        if not course:
            await update.message.reply_text("دوره یافت نشد.")
            return MANAGE_MENU
        context.user_data["selected_course"] = course
        reply_keyboard = [["شماره دوره", "افراد حاضر"], ["روزهای برگزاری", "تاریخ شروع"], ["تاریخ پایان"]]
        await update.message.reply_text(
            f"دوره: {course[1]}\nلطفاً فیلدی که می‌خواهید ویرایش کنید را انتخاب کنید:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return EDIT_COURSE
    except Exception as e:
        print(f"خطا در view_courses برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

async def edit_course(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        field = update.message.text
        print(f"User {update.effective_user.id} wants to edit field: {field}")
        context.user_data["edit_field"] = field
        field_map = {
            "شماره دوره": "course_number",
            "افراد حاضر": "participants",
            "روزهای برگزاری": "days",
            "تاریخ شروع": "start_date",
            "تاریخ پایان": "end_date"
        }
        if field not in field_map:
            await update.message.reply_text("لطفاً یکی از گزینه‌های منو را انتخاب کنید. 😊")
            return EDIT_COURSE
        await update.message.reply_text(f"لطفاً مقدار جدید برای {field} را وارد کنید:")
        return EDIT_COURSE
    except Exception as e:
        print(f"خطا در edit_course برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

async def update_course(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        new_value = update.message.text.strip()
        field = context.user_data.get("edit_field")
        course = context.user_data.get("selected_course")
        branch = context.user_data.get("branch")
        field_map = {
            "شماره دوره": "course_number",
            "افراد حاضر": "participants",
            "روزهای برگزاری": "days",
            "تاریخ شروع": "start_date",
            "تاریخ پایان": "end_date"
        }
        db_field = field_map[field]
        if db_field in ["start_date", "end_date"]:
            try:
                datetime.strptime(new_value, "%Y-%m-%d")
            except ValueError:
                await update.message.reply_text("لطفاً تاریخ را با فرمت YYYY-MM-DD وارد کنید.")
                return EDIT_COURSE
        c.execute(f"UPDATE courses SET {db_field} = ? WHERE branch = ? AND course_number = ?",
                 (new_value, branch, course[1]))
        conn.commit()
        await update.message.reply_text(f"{field} با موفقیت به‌روزرسانی شد.")
        return await manage_menu(update, context)
    except Exception as e:
        print(f"خطا در update_course برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

async def view_absentees(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        branch = context.user_data.get("branch")
        c.execute("SELECT course_number, participants, days, start_date, end_date FROM courses WHERE branch = ?", (branch,))
        courses = c.fetchall()
        if not courses:
            await update.message.reply_text("هیچ دوره‌ای برای این شعبه ثبت نشده است.")
            return MANAGE_MENU
        
        today = datetime.now().strftime("%Y-%m-%d")
        today_day = datetime.now().strftime("%A")  # روز هفته به انگلیسی
        day_map = {
            "Monday": "دوشنبه",
            "Tuesday": "سه‌شنبه",
            "Wednesday": "چهارشنبه",
            "Thursday": "پنج‌شنبه",
            "Friday": "جمعه",
            "Saturday": "شنبه",
            "Sunday": "یکشنبه"
        }
        today_day_persian = day_map.get(today_day, "")
        
        absentees = []
        for course in courses:
            course_number, participants, days, start_date, end_date = course
            if start_date <= today <= end_date and today_day_persian in days.split(","):
                participants_list = participants.split("\n")
                c.execute("SELECT user_id FROM attendance_logs WHERE event_type = 'entry' AND timestamp LIKE ?", (f"{today}%",))
                present_ids = [row[0] for row in c.fetchall()]
                absentees_list = [p for p in participants_list if p.split("_")[-1] not in present_ids]
                if absentees_list:
                    absentees.append(f"دوره {course_number}: {', '.join(absentees_list)}")
        
        if not absentees:
            await update.message.reply_text("هیچ غایبی برای امروز یافت نشد.")
        else:
            await update.message.reply_text("\n".join(absentees))
        return MANAGE_MENU
    except Exception as e:
        print(f"خطا در view_absentees برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

async def get_class(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        selected_class = update.message.text
        print(f"User {update.effective_user.id} selected class: {selected_class}")
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
        print(f"خطا در get_class برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        age_range = update.message.text
        print(f"User {update.effective_user.id} selected age range: {age_range}")
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
        print(f"خطا در get_age برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        name = update.message.text.strip()
        print(f"User {update.effective_user.id} entered name: {name}")
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
        print(f"خطا در get_name برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        phone = None
        if update.message.contact:
            phone = update.message.contact.phone_number
            print(f"User {update.effective_user.id} shared contact: {phone}")
        else:
            phone = update.message.text.strip()
            print(f"User {update.effective_user.id} entered phone: {phone}")
            if not (phone.startswith("+") and phone[1:].isdigit() or phone.isdigit()) or len(phone) < 7:
                await update.message.reply_text("لطفاً شماره تماس معتبر وارد کنید یا از دکمه اشتراک استفاده کنید. 😊")
                return PHONE_INPUT
        
        user_id = update.effective_user.id
        selected_class = context.user_data.get("class")
        age_range = context.user_data.get("age_range")
        name = context.user_data.get("name")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            c.execute("INSERT INTO users (id, class, age_range, name, phone, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                     (user_id, selected_class, age_range, name, phone, timestamp))
            conn.commit()
            print(f"User {user_id} data saved successfully")
        except sqlite3.Error as e:
            await update.message.reply_text("خطایی در ذخیره‌سازی اطلاعات رخ داد. لطفاً دوباره امتحان کنید.")
            print(f"خطای دیتابیس در get_phone برای کاربر {user_id}: {e}")
            return ConversationHandler.END
        
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
        print(f"خطا در get_phone برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

async def getdb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        print(f"User {update.effective_user.id} requested /getdb")
        await update.message.reply_text(
            "لطفاً رمز عبور را وارد کنید:",
            reply_markup=ReplyKeyboardRemove()
        )
        return GETDB_PASSWORD
    except Exception as e:
        print(f"خطا در getdb برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

async def verify_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        password = update.message.text.strip()
        print(f"User {update.effective_user.id} entered password: {password}")
        if password != "102030":
            await update.message.reply_text("رمز عبور نادرست است. 😊")
            return ConversationHandler.END
        
        try:
            c.execute("SELECT id, class, age_range, name, phone, timestamp FROM users")
            users = c.fetchall()
            print(f"Retrieved {len(users)} users from database")
        except sqlite3.Error as e:
            await update.message.reply_text("خطایی در دریافت اطلاعات رخ داد.")
            print(f"خطای دیتابیس در verify_password برای کاربر {update.effective_user.id}: {e}")
            return ConversationHandler.END
        
        if not users:
            await update.message.reply_text("هیچ کاربری در دیتابیس ثبت نشده است.")
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
        print(f"خطا در verify_password برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        print(f"User {update.effective_user.id} canceled conversation")
        await update.message.reply_text("لغو شد.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    except Exception as e:
        print(f"خطا در cancel برای کاربر {update.effective_user.id}: {e}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if isinstance(context.error, telegram.error.Conflict):
            print("خطای Conflict: نمونه دیگری از ربات در حال اجراست")
            if update and update.message:
                await update.message.reply_text("ربات در حال حاضر فعال است. لطفاً بعداً امتحان کنید.")
        else:
            print(f"خطا برای کاربر {update.effective_user.id} در پردازش: {context.error}")
            if update and update.message:
                await update.message.reply_text("خطایی رخ داد. لطفاً دوباره امتحان کنید.")
    except Exception as e:
        print(f"خطا در error_handler برای کاربر {update.effective_user.id}: {e}")

def acquire_lock():
    lock_file = "bot.lock"
    if os.path.exists(lock_file):
        print("خطا: یک نمونه دیگر از ربات در حال اجراست.")
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
        print("Application is not initialized!")
        raise RuntimeError("Application is not initialized!")
    update = Update.de_json(await request.json(), application.bot)
    if update is None:
        print("Invalid update received")
        return {"status": "error", "message": "Invalid update"}
    print(f"Processing update: {update}")
    await application.process_update(update)
    return {"status": "ok"}

application = None

async def initialize_application():
    global application
    try:
        TOKEN = os.environ.get("TOKEN")
        if not TOKEN:
            print("خطا: متغیر محیطی TOKEN تنظیم نشده است")
            exit(1)
        
        application = ApplicationBuilder().token(TOKEN).build()
        
        await application.initialize()
        print("Application initialized successfully")
        
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
        print("Handlers added successfully")
        
        webhook_url = os.environ.get("WEBHOOK_URL", "https://last-mossito.onrender.com")
        if not webhook_url:
            print("خطا: متغیر محیطی WEBHOOK_URL تنظیم نشده است")
            exit(1)
        await application.bot.setWebhook(f"{webhook_url}/webhook")
        print(f"Webhook تنظیم شد: {webhook_url}/webhook")
        
    except Exception as e:
        print(f"خطا در مقداردهی اولیه Application: {e}")
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
        print(f"خطا در main: {e}")
        exit(1)

def cleanup():
    try:
        conn.close()
        print("اتصال دیتابیس بسته شد")
    except Exception as e:
        print(f"خطا در بستن دیتابیس: {e}")

atexit.register(cleanup)
