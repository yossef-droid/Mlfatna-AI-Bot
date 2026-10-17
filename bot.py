import os
import asyncio
import logging

from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from telegram.error import TelegramError


from database import (
    initialize_database,

    add_user,
    get_all_users,

    get_stages,
    get_stage,

    get_semesters,
    get_semester,

    get_subjects,
    get_subject,
    add_subject,
    delete_subject,

    get_categories,
    get_category,

    add_file,
    get_files,
    get_file_record,
    delete_file,
    rename_file,
    search_files,

    get_statistics,
)


# =========================================================
# إعدادات عامة
# =========================================================

load_dotenv()


BOT_TOKEN = os.getenv(
    "BOT_TOKEN"
)

ADMIN_IDS_RAW = os.getenv(
    "ADMIN_IDS"
)


if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN غير موجود داخل ملف .env"
    )


if not ADMIN_IDS_RAW:
    raise ValueError(
        "ADMIN_ID غير موجود داخل ملف .env"
    )


ADMIN_IDS = {
    int(admin_id.strip())
    for admin_id in ADMIN_IDS_RAW.split(",")
    if admin_id.strip()
}


logging.basicConfig(
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    ),
    level=logging.INFO
)


logger = logging.getLogger(
    __name__
)


# =========================================================
# أدوات مساعدة
# =========================================================

def is_admin(user_id):
    return user_id in ADMIN_IDS

def category_icon(name_en):

    icons = {
        "Lectures": "📖",
        "Labs": "🧪",
        "Assignments": "📝",
        "Previous Questions": "❓",
        "Books": "📚",
        "Summaries": "📑",
    }

    return icons.get(
        name_en,
        "📂"
    )


def admin_home_keyboard():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ إضافة مادة",
                    callback_data="a_add_sub"
                )
            ],
            [
                InlineKeyboardButton(
                    "📤 رفع ملف",
                    callback_data="a_add_file"
                )
            ],
            [
                InlineKeyboardButton(
                    "📚 إدارة المواد",
                    callback_data="a_manage_sub"
                )
            ],
            [
                InlineKeyboardButton(
                    "📂 إدارة الملفات",
                    callback_data="a_manage_files"
                )
            ],
            [
                InlineKeyboardButton(
                    "📊 الإحصائيات",
                    callback_data="a_stats"
                )
            ],
            [
                InlineKeyboardButton(
                    "📢 إرسال إعلان",
                    callback_data="a_broadcast"
                )
            ],
            [
                InlineKeyboardButton(
                    "🎓 واجهة الطالب",
                    callback_data="u_home"
                )
            ],
        ]
    )


def student_home_keyboard():

    keyboard = []

    stages = get_stages()

    for stage in stages:

        keyboard.append(
            [
                InlineKeyboardButton(
                    f"🎓 {stage['name_ar']}",
                    callback_data=f"u_stage:{stage['id']}"
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                "🔎 البحث عن ملف",
                callback_data="u_search"
            )
        ]
    )

    return InlineKeyboardMarkup(
        keyboard
    )


# =========================================================
# /start
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    add_user(
        telegram_id=user.id,
        first_name=user.first_name,
        username=user.username
    )

    context.user_data.clear()

    text = (
        f"أهلاً {user.first_name} 👋\n\n"
        "🎓 مكتبة قسم الذكاء الاصطناعي\n\n"
        "يمكنك الوصول إلى المحاضرات والملفات "
        "والكتب والأسئلة والملخصات من هنا.\n\n"
        "اختر المرحلة الدراسية:"
    )

    await update.message.reply_text(
        text,
        reply_markup=student_home_keyboard()
    )


# =========================================================
# /admin
# =========================================================

async def admin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(
        update.effective_user.id
    ):

        await update.message.reply_text(
            "⛔ ليس لديك صلاحية "
            "الوصول إلى لوحة الإدارة."
        )

        return

    context.user_data.clear()

    await update.message.reply_text(
        "⚙️ لوحة إدارة المكتبة\n\n"
        "اختر العملية المطلوبة:",
        reply_markup=admin_home_keyboard()
    )


# =========================================================
# CALLBACK HANDLER
# =========================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    data = query.data

    user_id = query.from_user.id


    # =====================================================
    # حماية أزرار الإدارة
    # =====================================================

    if data.startswith("a_"):

        if not is_admin(user_id):

            await query.answer(
                "⛔ ليس لديك صلاحية.",
                show_alert=True
            )

            return


    # =====================================================
    # واجهة الطالب الرئيسية
    # =====================================================

    if data == "u_home":

        context.user_data.clear()

        await query.edit_message_text(
            "🎓 مكتبة قسم الذكاء الاصطناعي\n\n"
            "اختر المرحلة الدراسية:",
            reply_markup=student_home_keyboard()
        )

        return


    # =====================================================
    # اختيار المرحلة
    # =====================================================

    if data.startswith("u_stage:"):

        stage_id = int(
            data.split(":")[1]
        )

        stage = get_stage(
            stage_id
        )

        semesters = get_semesters(
            stage_id
        )

        keyboard = []

        for semester in semesters:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"📅 {semester['name_ar']}",
                        callback_data=(
                            f"u_sem:{semester['id']}"
                        )
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "🏠 الرئيسية",
                    callback_data="u_home"
                )
            ]
        )

        await query.edit_message_text(
            f"🎓 {stage['name_ar']}\n\n"
            "اختر الفصل الدراسي:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    # =====================================================
    # اختيار الفصل
    # =====================================================

    if data.startswith("u_sem:"):

        semester_id = int(
            data.split(":")[1]
        )

        semester = get_semester(
            semester_id
        )

        subjects = get_subjects(
            semester_id
        )

        keyboard = []

        for subject in subjects:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"📚 {subject['name_ar']}",
                        callback_data=(
                            f"u_sub:{subject['id']}"
                        )
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "⬅️ رجوع",
                    callback_data=(
                        f"u_stage:"
                        f"{semester['stage_id']}"
                    )
                )
            ]
        )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "🏠 الرئيسية",
                    callback_data="u_home"
                )
            ]
        )

        if not subjects:

            text = (
                "📚 لا توجد مواد مضافة "
                "لهذا الفصل حالياً."
            )

        else:

            text = (
                f"📅 {semester['name_ar']}\n\n"
                "اختر المادة:"
            )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    # =====================================================
    # اختيار المادة
    # =====================================================

    if data.startswith("u_sub:"):

        subject_id = int(
            data.split(":")[1]
        )

        subject = get_subject(
            subject_id
        )

        categories = get_categories()

        keyboard = []

        for category in categories:

            icon = category_icon(
                category["name_en"]
            )

            keyboard.append(
                [
                    InlineKeyboardButton(
                        (
                            f"{icon} "
                            f"{category['name_ar']}"
                        ),
                        callback_data=(
                            f"u_cat:"
                            f"{subject_id}:"
                            f"{category['id']}"
                        )
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "⬅️ رجوع",
                    callback_data=(
                        f"u_sem:"
                        f"{subject['semester_id']}"
                    )
                )
            ]
        )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "🏠 الرئيسية",
                    callback_data="u_home"
                )
            ]
        )

        await query.edit_message_text(
            f"📚 {subject['name_ar']}\n\n"
            "اختر نوع الملفات:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    # =====================================================
    # عرض ملفات القسم
    # =====================================================

    if data.startswith("u_cat:"):

        parts = data.split(":")

        subject_id = int(
            parts[1]
        )

        category_id = int(
            parts[2]
        )

        subject = get_subject(
            subject_id
        )

        category = get_category(
            category_id
        )

        files = get_files(
            subject_id,
            category_id
        )

        keyboard = []

        for file in files:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"📄 {file['title']}",
                        callback_data=(
                            f"u_file:{file['id']}"
                        )
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "⬅️ رجوع",
                    callback_data=(
                        f"u_sub:{subject_id}"
                    )
                )
            ]
        )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "🏠 الرئيسية",
                    callback_data="u_home"
                )
            ]
        )

        if files:

            text = (
                f"📚 {subject['name_ar']}\n"
                f"📂 {category['name_ar']}\n\n"
                "اختر الملف:"
            )

        else:

            text = (
                f"📚 {subject['name_ar']}\n"
                f"📂 {category['name_ar']}\n\n"
                "لا توجد ملفات هنا حالياً."
            )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    # =====================================================
    # إرسال الملف للطالب
    # =====================================================

    if data.startswith("u_file:"):

        file_db_id = int(
            data.split(":")[1]
        )

        file = get_file_record(
            file_db_id
        )

        if not file:

            await query.message.reply_text(
                "❌ الملف غير موجود."
            )

            return

        try:

            await context.bot.send_document(
                chat_id=query.message.chat_id,

                document=(
                    file["telegram_file_id"]
                ),

                caption=(
                    f"📄 {file['title']}\n"
                    f"📚 {file['subject_name']}\n"
                    f"📂 {file['category_name']}"
                )
            )

        except TelegramError as error:

            logger.error(
                "File send error: %s",
                error
            )

            await query.message.reply_text(
                "❌ حدث خطأ أثناء إرسال الملف."
            )

        return


    # =====================================================
    # البحث
    # =====================================================

    if data == "u_search":

        context.user_data.clear()

        context.user_data[
            "action"
        ] = "student_search"

        await query.edit_message_text(
            "🔎 البحث عن ملف\n\n"
            "أرسل اسم المادة أو اسم الملف.\n\n"
            "مثال:\n"
            "Numerical Analysis\n"
            "أو\n"
            "Lecture 3",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🏠 الرئيسية",
                            callback_data="u_home"
                        )
                    ]
                ]
            )
        )

        return


    # =====================================================
    # لوحة الإدارة الرئيسية
    # =====================================================

    if data == "a_home":

        context.user_data.clear()

        await query.edit_message_text(
            "⚙️ لوحة إدارة المكتبة\n\n"
            "اختر العملية المطلوبة:",
            reply_markup=admin_home_keyboard()
        )

        return


    # =====================================================
    # ADMIN - إضافة مادة
    # =====================================================

    if data == "a_add_sub":

        stages = get_stages()

        keyboard = []

        for stage in stages:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"🎓 {stage['name_ar']}",
                        callback_data=(
                            f"a_ss:{stage['id']}"
                        )
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "⬅️ لوحة الإدارة",
                    callback_data="a_home"
                )
            ]
        )

        await query.edit_message_text(
            "➕ إضافة مادة جديدة\n\n"
            "اختر المرحلة:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    if data.startswith("a_ss:"):

        stage_id = int(
            data.split(":")[1]
        )

        semesters = get_semesters(
            stage_id
        )

        keyboard = []

        for semester in semesters:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"📅 {semester['name_ar']}",
                        callback_data=(
                            f"a_sm:"
                            f"{semester['id']}"
                        )
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "⬅️ رجوع",
                    callback_data="a_add_sub"
                )
            ]
        )

        await query.edit_message_text(
            "📅 اختر الفصل الدراسي:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    if data.startswith("a_sm:"):

        semester_id = int(
            data.split(":")[1]
        )

        context.user_data.clear()

        context.user_data[
            "action"
        ] = "add_subject_ar"

        context.user_data[
            "semester_id"
        ] = semester_id

        await query.edit_message_text(
            "✏️ أرسل اسم المادة بالعربي.\n\n"
            "مثال:\n"
            "التحليل العددي"
        )

        return


    # =====================================================
    # ADMIN - رفع ملف
    # =====================================================

    if data == "a_add_file":

        stages = get_stages()

        keyboard = []

        for stage in stages:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"🎓 {stage['name_ar']}",
                        callback_data=(
                            f"a_fs:{stage['id']}"
                        )
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "⬅️ لوحة الإدارة",
                    callback_data="a_home"
                )
            ]
        )

        await query.edit_message_text(
            "📤 رفع ملف جديد\n\n"
            "اختر المرحلة:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    if data.startswith("a_fs:"):

        stage_id = int(
            data.split(":")[1]
        )

        semesters = get_semesters(
            stage_id
        )

        keyboard = []

        for semester in semesters:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"📅 {semester['name_ar']}",
                        callback_data=(
                            f"a_fm:"
                            f"{semester['id']}"
                        )
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "⬅️ رجوع",
                    callback_data="a_add_file"
                )
            ]
        )

        await query.edit_message_text(
            "📅 اختر الفصل:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    if data.startswith("a_fm:"):

        semester_id = int(
            data.split(":")[1]
        )

        subjects = get_subjects(
            semester_id
        )

        keyboard = []

        for subject in subjects:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"📚 {subject['name_ar']}",
                        callback_data=(
                            f"a_fsub:"
                            f"{subject['id']}"
                        )
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "⬅️ لوحة الإدارة",
                    callback_data="a_home"
                )
            ]
        )

        if not subjects:

            text = (
                "❌ لا توجد مواد في هذا الفصل.\n\n"
                "أضف المادة أولاً."
            )

        else:

            text = "📚 اختر المادة:"

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    if data.startswith("a_fsub:"):

        subject_id = int(
            data.split(":")[1]
        )

        categories = get_categories()

        keyboard = []

        for category in categories:

            icon = category_icon(
                category["name_en"]
            )

            keyboard.append(
                [
                    InlineKeyboardButton(
                        (
                            f"{icon} "
                            f"{category['name_ar']}"
                        ),
                        callback_data=(
                            f"a_fcat:"
                            f"{subject_id}:"
                            f"{category['id']}"
                        )
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "⬅️ لوحة الإدارة",
                    callback_data="a_home"
                )
            ]
        )

        await query.edit_message_text(
            "📂 اختر نوع الملف:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    if data.startswith("a_fcat:"):

        parts = data.split(":")

        subject_id = int(
            parts[1]
        )

        category_id = int(
            parts[2]
        )

        subject = get_subject(
            subject_id
        )

        category = get_category(
            category_id
        )

        context.user_data.clear()

        context.user_data[
            "action"
        ] = "await_file"

        context.user_data[
            "subject_id"
        ] = subject_id

        context.user_data[
            "category_id"
        ] = category_id

        await query.edit_message_text(
            "📤 الآن أرسل الملف إلى البوت.\n\n"
            f"📚 المادة: {subject['name_ar']}\n"
            f"📂 القسم: {category['name_ar']}\n\n"
            "يمكنك إرسال PDF أو Word أو PowerPoint "
            "أو أي ملف يظهر في Telegram كـ Document."
        )

        return


    # =====================================================
    # ADMIN - إدارة المواد
    # =====================================================

    if data == "a_manage_sub":

        stages = get_stages()

        keyboard = []

        for stage in stages:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"🎓 {stage['name_ar']}",
                        callback_data=(
                            f"a_ms_stage:"
                            f"{stage['id']}"
                        )
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "⬅️ لوحة الإدارة",
                    callback_data="a_home"
                )
            ]
        )

        await query.edit_message_text(
            "📚 إدارة المواد\n\n"
            "اختر المرحلة:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    if data.startswith("a_ms_stage:"):

        stage_id = int(
            data.split(":")[1]
        )

        semesters = get_semesters(
            stage_id
        )

        keyboard = []

        for semester in semesters:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"📅 {semester['name_ar']}",
                        callback_data=(
                            f"a_ms_sem:"
                            f"{semester['id']}"
                        )
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "⬅️ رجوع",
                    callback_data="a_manage_sub"
                )
            ]
        )

        await query.edit_message_text(
            "📅 اختر الفصل:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    if data.startswith("a_ms_sem:"):

        semester_id = int(
            data.split(":")[1]
        )

        subjects = get_subjects(
            semester_id
        )

        keyboard = []

        for subject in subjects:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"📚 {subject['name_ar']}",
                        callback_data=(
                            f"a_ms_item:"
                            f"{subject['id']}"
                        )
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "⬅️ لوحة الإدارة",
                    callback_data="a_home"
                )
            ]
        )

        if subjects:

            text = (
                "📚 اختر المادة التي تريد إدارتها:"
            )

        else:

            text = (
                "لا توجد مواد في هذا الفصل."
            )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    if data.startswith("a_ms_item:"):

        subject_id = int(
            data.split(":")[1]
        )

        subject = get_subject(
            subject_id
        )

        await query.edit_message_text(
            (
                "📚 المادة\n\n"
                f"العربي: {subject['name_ar']}\n"
                f"English: {subject['name_en']}"
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🗑 حذف المادة",
                            callback_data=(
                                f"a_sub_delq:"
                                f"{subject_id}"
                            )
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⬅️ لوحة الإدارة",
                            callback_data="a_home"
                        )
                    ]
                ]
            )
        )

        return


    if data.startswith("a_sub_delq:"):

        subject_id = int(
            data.split(":")[1]
        )

        subject = get_subject(
            subject_id
        )

        await query.edit_message_text(
            "⚠️ تأكيد الحذف\n\n"
            f"هل تريد حذف مادة:\n"
            f"{subject['name_ar']}؟\n\n"
            "سيتم حذف الملفات المرتبطة بها أيضاً.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ نعم، احذف",
                            callback_data=(
                                f"a_sub_del:"
                                f"{subject_id}"
                            )
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "❌ إلغاء",
                            callback_data="a_home"
                        )
                    ]
                ]
            )
        )

        return


    if data.startswith("a_sub_del:"):

        subject_id = int(
            data.split(":")[1]
        )

        delete_subject(
            subject_id
        )

        await query.edit_message_text(
            "✅ تم حذف المادة.",
            reply_markup=admin_home_keyboard()
        )

        return


    # =====================================================
    # ADMIN - إدارة الملفات
    # =====================================================

    if data == "a_manage_files":

        stages = get_stages()

        keyboard = []

        for stage in stages:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"🎓 {stage['name_ar']}",
                        callback_data=(
                            f"a_mf_stage:"
                            f"{stage['id']}"
                        )
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "⬅️ لوحة الإدارة",
                    callback_data="a_home"
                )
            ]
        )

        await query.edit_message_text(
            "📂 إدارة الملفات\n\n"
            "اختر المرحلة:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    if data.startswith("a_mf_stage:"):

        stage_id = int(
            data.split(":")[1]
        )

        semesters = get_semesters(
            stage_id
        )

        keyboard = []

        for semester in semesters:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"📅 {semester['name_ar']}",
                        callback_data=(
                            f"a_mf_sem:"
                            f"{semester['id']}"
                        )
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "⬅️ رجوع",
                    callback_data="a_manage_files"
                )
            ]
        )

        await query.edit_message_text(
            "📅 اختر الفصل:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    if data.startswith("a_mf_sem:"):

        semester_id = int(
            data.split(":")[1]
        )

        subjects = get_subjects(
            semester_id
        )

        keyboard = []

        for subject in subjects:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"📚 {subject['name_ar']}",
                        callback_data=(
                            f"a_mf_sub:"
                            f"{subject['id']}"
                        )
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "⬅️ لوحة الإدارة",
                    callback_data="a_home"
                )
            ]
        )

        await query.edit_message_text(
            "📚 اختر المادة:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    if data.startswith("a_mf_sub:"):

        subject_id = int(
            data.split(":")[1]
        )

        categories = get_categories()

        keyboard = []

        for category in categories:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        (
                            f"{category_icon(category['name_en'])} "
                            f"{category['name_ar']}"
                        ),
                        callback_data=(
                            f"a_mf_cat:"
                            f"{subject_id}:"
                            f"{category['id']}"
                        )
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "⬅️ لوحة الإدارة",
                    callback_data="a_home"
                )
            ]
        )

        await query.edit_message_text(
            "📂 اختر القسم:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    if data.startswith("a_mf_cat:"):

        parts = data.split(":")

        subject_id = int(
            parts[1]
        )

        category_id = int(
            parts[2]
        )

        files = get_files(
            subject_id,
            category_id
        )

        keyboard = []

        for file in files:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"📄 {file['title']}",
                        callback_data=(
                            f"a_file:{file['id']}"
                        )
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "⬅️ لوحة الإدارة",
                    callback_data="a_home"
                )
            ]
        )

        if files:

            text = (
                "📂 اختر الملف الذي تريد إدارته:"
            )

        else:

            text = (
                "لا توجد ملفات في هذا القسم."
            )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    if data.startswith("a_file:"):

        file_db_id = int(
            data.split(":")[1]
        )

        file = get_file_record(
            file_db_id
        )

        if not file:

            await query.edit_message_text(
                "❌ الملف غير موجود.",
                reply_markup=admin_home_keyboard()
            )

            return

        keyboard = [
            [
                InlineKeyboardButton(
                    "📤 إرسال الملف",
                    callback_data=(
                        f"a_send_file:"
                        f"{file_db_id}"
                    )
                )
            ],
            [
                InlineKeyboardButton(
                    "✏️ تغيير الاسم",
                    callback_data=(
                        f"a_rename:"
                        f"{file_db_id}"
                    )
                )
            ],
            [
                InlineKeyboardButton(
                    "🗑 حذف الملف",
                    callback_data=(
                        f"a_del_file_q:"
                        f"{file_db_id}"
                    )
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ لوحة الإدارة",
                    callback_data="a_home"
                )
            ],
        ]

        await query.edit_message_text(
            (
                f"📄 {file['title']}\n\n"
                f"📚 المادة: "
                f"{file['subject_name']}\n"
                f"📂 القسم: "
                f"{file['category_name']}\n"
                f"🗂 الاسم الأصلي: "
                f"{file['file_name']}"
            ),
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    if data.startswith("a_send_file:"):

        file_db_id = int(
            data.split(":")[1]
        )

        file = get_file_record(
            file_db_id
        )

        if file:

            await context.bot.send_document(
                chat_id=query.message.chat_id,

                document=(
                    file["telegram_file_id"]
                ),

                caption=f"📄 {file['title']}"
            )

        return


    if data.startswith("a_rename:"):

        file_db_id = int(
            data.split(":")[1]
        )

        context.user_data.clear()

        context.user_data[
            "action"
        ] = "rename_file"

        context.user_data[
            "rename_file_id"
        ] = file_db_id

        await query.edit_message_text(
            "✏️ أرسل الاسم الجديد للملف:"
        )

        return


    if data.startswith("a_del_file_q:"):

        file_db_id = int(
            data.split(":")[1]
        )

        file = get_file_record(
            file_db_id
        )

        await query.edit_message_text(
            (
                "⚠️ هل تريد حذف الملف؟\n\n"
                f"📄 {file['title']}"
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ نعم، احذف",
                            callback_data=(
                                f"a_del_file:"
                                f"{file_db_id}"
                            )
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "❌ إلغاء",
                            callback_data="a_home"
                        )
                    ]
                ]
            )
        )

        return


    if data.startswith("a_del_file:"):

        file_db_id = int(
            data.split(":")[1]
        )

        delete_file(
            file_db_id
        )

        await query.edit_message_text(
            "✅ تم حذف الملف.",
            reply_markup=admin_home_keyboard()
        )

        return


    # =====================================================
    # ADMIN - الإحصائيات
    # =====================================================

    if data == "a_stats":

        stats = get_statistics()

        await query.edit_message_text(
            (
                "📊 إحصائيات البوت\n\n"
                f"👥 المستخدمون: "
                f"{stats['users']}\n\n"
                f"📚 المواد: "
                f"{stats['subjects']}\n\n"
                f"📄 الملفات: "
                f"{stats['files']}"
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⬅️ لوحة الإدارة",
                            callback_data="a_home"
                        )
                    ]
                ]
            )
        )

        return


    # =====================================================
    # ADMIN - الإعلان
    # =====================================================

    if data == "a_broadcast":

        context.user_data.clear()

        context.user_data[
            "action"
        ] = "broadcast"

        await query.edit_message_text(
            "📢 إرسال إعلان\n\n"
            "أرسل الآن نص الإعلان الذي تريد "
            "إرساله لجميع مستخدمي البوت."
        )

        return


# =========================================================
# استقبال النصوص
# =========================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    text = update.message.text.strip()

    action = context.user_data.get(
        "action"
    )


    # =====================================================
    # بحث الطالب
    # =====================================================

    if action == "student_search":

        results = search_files(
            text
        )

        context.user_data.clear()

        keyboard = []

        for file in results:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        (
                            f"📄 {file['title']} "
                            f"— {file['subject_name']}"
                        ),
                        callback_data=(
                            f"u_file:{file['id']}"
                        )
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "🔎 بحث جديد",
                    callback_data="u_search"
                )
            ]
        )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "🏠 الرئيسية",
                    callback_data="u_home"
                )
            ]
        )

        if results:

            message = (
                f"🔎 نتائج البحث عن:\n{text}\n\n"
                f"تم العثور على "
                f"{len(results)} نتيجة."
            )

        else:

            message = (
                "❌ لم أعثر على ملف مطابق.\n\n"
                "جرّب كتابة جزء من اسم المادة "
                "أو اسم المحاضرة."
            )

        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    # =====================================================
    # جميع العمليات التالية خاصة بالمدير
    # =====================================================

    if not is_admin(user.id):

        return


    # =====================================================
    # إضافة مادة - الاسم العربي
    # =====================================================

    if action == "add_subject_ar":

        context.user_data[
            "subject_ar"
        ] = text

        context.user_data[
            "action"
        ] = "add_subject_en"

        await update.message.reply_text(
            "✅ تم حفظ الاسم العربي.\n\n"
            "الآن أرسل اسم المادة بالإنكليزي.\n\n"
            "مثال:\n"
            "Numerical Analysis"
        )

        return


    # =====================================================
    # إضافة مادة - الاسم الإنكليزي
    # =====================================================

    if action == "add_subject_en":

        semester_id = context.user_data.get(
            "semester_id"
        )

        name_ar = context.user_data.get(
            "subject_ar"
        )

        success = add_subject(
            semester_id=semester_id,
            name_ar=name_ar,
            name_en=text
        )

        context.user_data.clear()

        if success:

            message = (
                "✅ تمت إضافة المادة بنجاح.\n\n"
                f"📚 {name_ar}\n"
                f"🌐 {text}"
            )

        else:

            message = (
                "⚠️ هذه المادة موجودة مسبقاً "
                "في هذا الفصل."
            )

        await update.message.reply_text(
            message,
            reply_markup=admin_home_keyboard()
        )

        return


    # =====================================================
    # اسم الملف بعد الرفع
    # =====================================================

    if action == "await_file_title":

        pending = context.user_data.get(
            "pending_file"
        )

        if not pending:

            context.user_data.clear()

            await update.message.reply_text(
                "❌ حدث خطأ. أعد رفع الملف."
            )

            return

        add_file(
            subject_id=(
                pending["subject_id"]
            ),

            category_id=(
                pending["category_id"]
            ),

            title=text,

            telegram_file_id=(
                pending["file_id"]
            ),

            telegram_unique_id=(
                pending["file_unique_id"]
            ),

            file_name=(
                pending["file_name"]
            ),

            mime_type=(
                pending["mime_type"]
            ),

            uploaded_by=user.id
        )

        context.user_data.clear()

        await update.message.reply_text(
            (
                "✅ تم حفظ الملف بنجاح.\n\n"
                f"📄 {text}"
            ),
            reply_markup=admin_home_keyboard()
        )

        return


    # =====================================================
    # تغيير اسم الملف
    # =====================================================

    if action == "rename_file":

        file_db_id = context.user_data.get(
            "rename_file_id"
        )

        rename_file(
            file_db_id,
            text
        )

        context.user_data.clear()

        await update.message.reply_text(
            (
                "✅ تم تغيير اسم الملف إلى:\n\n"
                f"📄 {text}"
            ),
            reply_markup=admin_home_keyboard()
        )

        return


    # =====================================================
    # إعلان جماعي
    # =====================================================

    if action == "broadcast":

        context.user_data.clear()

        users = get_all_users()

        sent = 0
        failed = 0

        progress_message = (
            await update.message.reply_text(
                "📢 جاري إرسال الإعلان..."
            )
        )

        for row in users:

            telegram_id = row[
                "telegram_id"
            ]

            try:

                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=(
                        "📢 إعلان\n\n"
                        f"{text}"
                    )
                )

                sent += 1

                await asyncio.sleep(
                    0.05
                )

            except TelegramError:

                failed += 1

        await progress_message.edit_text(
            (
                "✅ اكتمل إرسال الإعلان.\n\n"
                f"📨 نجح: {sent}\n"
                f"❌ فشل: {failed}"
            ),
            reply_markup=admin_home_keyboard()
        )

        return


# =========================================================
# استقبال الملفات من المدير
# =========================================================

async def document_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not is_admin(user.id):
        return


    action = context.user_data.get(
        "action"
    )


    if action != "await_file":

        await update.message.reply_text(
            "ℹ️ لرفع ملف استخدم:\n\n"
            "/admin → 📤 رفع ملف"
        )

        return


    document = update.message.document

    subject_id = context.user_data.get(
        "subject_id"
    )

    category_id = context.user_data.get(
        "category_id"
    )


    context.user_data[
        "pending_file"
    ] = {
        "subject_id": subject_id,
        "category_id": category_id,

        "file_id": document.file_id,

        "file_unique_id": (
            document.file_unique_id
        ),

        "file_name": (
            document.file_name
            or "Unknown file"
        ),

        "mime_type": (
            document.mime_type
            or ""
        ),
    }


    context.user_data[
        "action"
    ] = "await_file_title"


    await update.message.reply_text(
        (
            "✅ استلمت الملف.\n\n"
            f"🗂 الاسم الأصلي:\n"
            f"{document.file_name}\n\n"
            "✏️ الآن أرسل الاسم الذي تريد "
            "أن يظهر للطلاب.\n\n"
            "مثال:\n"
            "Lecture 1 - Bisection Method"
        )
    )


# =========================================================
# معالجة الأخطاء
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.exception(
        "Exception while handling an update:",
        exc_info=context.error
    )


# =========================================================
# أوامر Telegram
# =========================================================

async def post_init(
    application: Application
):

    commands = [
        BotCommand(
            "start",
            "فتح المكتبة"
        ),
        BotCommand(
            "admin",
            "لوحة الإدارة"
        ),
    ]

    await application.bot.set_my_commands(
        commands
    )


# =========================================================
# تشغيل البوت
# =========================================================

def main():

    initialize_database()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )


    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    application.add_handler(
        CommandHandler(
            "admin",
            admin_command
        )
    )


    application.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )


    application.add_handler(
        MessageHandler(
            filters.Document.ALL,
            document_handler
        )
    )


    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            text_handler
        )
    )


    application.add_error_handler(
        error_handler
    )


    print(
        "===================================="
    )

    print(
        "✅ Database initialized successfully"
    )

    print(
        "🤖 Mlfatna AI Bot is running..."
    )

    print(
        "===================================="
    )


    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()