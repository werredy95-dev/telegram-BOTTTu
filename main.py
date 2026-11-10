# -*- coding: utf-8 -*-
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import AsyncOpenAI

# =====================================================================
# ⚠️ ضع مفاتيحك هنا
# =====================================================================
TELEGRAM_TOKEN = ""
GROQ_API_KEY = ""
# =====================================================================

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# إعداد الذكاء الاصطناعي
ai_client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
MODEL = "openai/gpt-oss-120b" # هذا النموذج ممتاز جداً في اللغات المتعددة

# ذاكرة المحادثات لكل مستخدم (ليتذكر سياق الكلام)
chat_histories = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌍 أهلاً بك! أنا بوت ذكي أفهم وأتحدث جميع لغات العالم.\n"
        "في الخاص: اسألني أي شيء وسأجيبك.\n"
        "في المجموعة: اكتب اسمي (منشن) مع سؤالك لكي أرد عليك."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_type = update.effective_chat.type
    user_text = update.message.text or ""
    
    # =======================================================
    # فلتر المجموعات: لا يرد إلا إذا تم عمل منشن أو رد على رسالته
    # =======================================================
    if chat_type in ['group', 'supergroup']:
        # هل تم عمل منشن للبوت؟
        is_mentioned = f"@{context.bot.username}" in user_text
        
        # هل المستخدم يرد (Reply) على رسالة سابقة للبوت؟
        is_reply_to_bot = False
        if update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
            is_reply_to_bot = True

        # إذا لم يتم منشنه ولم يرد على رسالته، يتجاهل الرسالة تماماً
        if not (is_mentioned or is_reply_to_bot):
            return
        
        # تنظيف النص من المنشن قبل إرساله للذكاء الاصطناعي
        user_text = user_text.replace(f"@{context.bot.username}", "").strip()

    # إذا كانت الرسالة فارغة بعد التنظيف
    if not user_text:
        return

    # إظهار مؤشر "يكتب..."
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # إعداد الذاكرة
        if user_id not in chat_histories:
            # تعليمات صارمة للذكاء الاصطناعي ليكون متعدد اللغات
            chat_histories[user_id] = [
                {"role": "system", "content": "You are a highly intelligent multilingual assistant. You must ALWAYS reply in the EXACT same language the user used. If they speak Arabic, reply in Arabic. If they speak English, reply in English, etc. Be extremely accurate and helpful."}
            ]

        history = chat_histories[user_id]
        history.append({"role": "user", "content": user_text})

        # حد أقصى للذاكرة (آخر 10 رسائل) لعدم استهلاك الحد المسموح
        if len(history) > 11:
            history = [history[0]] + history[-10:]
            chat_histories[user_id] = history

        # إرسال الطلب لجروك
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=history,
            temperature=0.6,
            max_tokens=1024
        )
        
        answer = response.choices[0].message.content
        history.append({"role": "assistant", "content": answer})
        
        # إرسال الرد
        await update.message.reply_text(answer)
        
    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("⚠️ حدث خطأ في الاتصال بالذكاء الاصطناعي. حاول لاحقاً.")

if __name__ == '__main__':
    print("🌍 بوت اللغات المتعددة يعمل الآن...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(drop_pending_updates=True)