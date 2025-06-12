import requests
import sqlite3
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TELEGRAM_TOKEN = '7662899091:AAG8W8Zp_AoqqbzvSSi6ymixaxXjsxfciHw'
OPENROUTER_API_KEY = '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'

conn = sqlite3.connect("players.db", check_same_thread=False)
cursor = conn.cursor()

# Drop old table to avoid schema mismatch errors
cursor.execute("DROP TABLE IF EXISTS players")
conn.commit()

# Create table with all required columns
cursor.execute('''
    CREATE TABLE players (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        rank TEXT,
        goals TEXT,
        level INTEGER DEFAULT 1,
        stamina INTEGER DEFAULT 100,
        task TEXT,
        task_count INTEGER DEFAULT 0
    )
''')
conn.commit()

def get_player(user_id):
    cursor.execute("SELECT user_id, name, rank, goals, level, stamina, task, task_count FROM players WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def save_player(user_id, name=None, rank=None, goals=None, level=None, stamina=None, task=None, task_count=None):
    player = get_player(user_id)
    if player is None:
        cursor.execute("INSERT INTO players (user_id) VALUES (?)", (user_id,))
        conn.commit()
        player = get_player(user_id)

    updates = []
    values = []
    for col, val in zip(["name", "rank", "goals", "level", "stamina", "task", "task_count"],
                        [name, rank, goals, level, stamina, task, task_count]):
        if val is not None:
            updates.append(f"{col}=?")
            values.append(val)

    if updates:
        values.append(user_id)
        cursor.execute(f"UPDATE players SET {', '.join(updates)} WHERE user_id=?", values)
        conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_player(user_id)
    await update.message.reply_text("🧬 SYSTEM: Welcome, Player. You have been activated.")
    await asyncio.sleep(1)
    await update.message.reply_text("Enter your name:")
    context.user_data['step'] = 'get_name'

async def chat_with_gpt(prompt):
    res = requests.post(
        'https://openrouter.ai/api/v1/chat/completions',
        headers={
            'Authorization': f'Bearer {OPENROUTER_API_KEY}',
            'Content-Type': 'application/json'
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a Solo Leveling character. Keep the tone in character."},
                {"role": "user", "content": prompt}
            ]
        }
    )
    result = res.json()
    return result['choices'][0]['message']['content']

async def assign_new_task(user_id, context):
    player = get_player(user_id)
    if not player:
        await context.bot.send_message(chat_id=user_id, text="⚠️ SYSTEM ERROR: Player not registered. Use /start.")
        return
    prompt = f"""
You are SYSTEM. Generate a cold, short mission (1 sentence) for the player.
Player Info: Name: {player[1]}, Rank: {player[2]}, Level: {player[4]}, Goals: {player[3]}.

Rules:
- Task must be doable at home.
- No equipment required.
- Use numbers for physical quests: e.g., 50 sit-ups, 20 push-ups, 1-min plank.
- In case of IQ questions, give a logical problem: math puzzle or decision-based scenario.
- Give quests according to the player’s chosen category.
- Do not repeat the same exercise type more than once every 5 missions (e.g., don’t keep using jumping jacks repeatedly).
- Do not create variations of the same task (e.g., “100 jumping jacks,” “jumping jacks in sets,” or “jumping jacks followed by squats”). Only use a task once in any form.
- Be cold and short. Do not explain.
"""
    task = await chat_with_gpt(prompt)
    save_player(user_id, task=task)
    button = [[InlineKeyboardButton("✅ Done", callback_data="task_done")]]
    await context.bot.send_message(user_id, f"📌 {task}", reply_markup=InlineKeyboardMarkup(button))

async def handle_task_completion(user_id, context):
    player = get_player(user_id)

    if not player:
        await context.bot.send_message(chat_id=user_id, text="⚠️ SYSTEM ERROR: Player not registered. Restart with /start.")
        return

    new_level = player[4]
    new_stamina = player[5]
    task_count = player[7]

    new_level += 1
    new_stamina = max(0, new_stamina - 10)
    task_count += 1

    save_player(user_id, level=new_level, stamina=new_stamina, task_count=task_count)

    if task_count % 2 == 0:
        await context.bot.send_message(user_id, f"📊 SYSTEM Report:\nLevel: {new_level}\nStamina: {new_stamina}")

    if task_count % 5 == 0:
        buttons = [
            [InlineKeyboardButton("🗣 Talk to Jinwoo", callback_data="talk|Jinwoo")],
            [InlineKeyboardButton("🦅 Talk to Beru", callback_data="talk|Beru")],
            [InlineKeyboardButton("❌ Skip", callback_data="skip_talk")]
        ]
        await context.bot.send_message(user_id, "🧠 SYSTEM: You have earned a privilege.", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await assign_new_task(user_id, context)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    player = get_player(user_id)

    step = context.user_data.get('step')
    if step == 'get_name':
        save_player(user_id, name=text)
        context.user_data['step'] = 'get_rank'
        buttons = [[InlineKeyboardButton(rank, callback_data=f"rank|{rank}")] for rank in ["E", "D", "C", "B", "A", "S"]]
        await update.message.reply_text("Choose your rank:", reply_markup=InlineKeyboardMarkup(buttons))
    elif step == 'get_goal':
        save_player(user_id, goals=text)
        context.user_data['step'] = None
        await update.message.reply_text("⚠️ From now onwards you don't have any option.")
        await asyncio.sleep(1)
        await update.message.reply_text("This was your final decision.")
        await asyncio.sleep(1)
        await update.message.reply_text("The battle begins.")
        await asyncio.sleep(1)
        await update.message.reply_text("Good Luck")
        await asyncio.sleep(1)
        await assign_new_task(user_id, context)
    else:
        await update.message.reply_text("SYSTEM: Awaiting task completion or command.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("rank|"):
        rank = data.split("|")[1]
        save_player(user_id, rank=rank)
        context.user_data['step'] = 'get_goal'
        goals_list = [
            "Weight Loss / Fat Burn", "Muscle Gain / Bodybuilding", "Improving Strength / Power",
            "Cardiovascular Health", "Flexibility / Mobility", "Improving Endurance / Stamina", "IQ"
        ]
        buttons = [[InlineKeyboardButton(g, callback_data=f"goal|{g}")] for g in goals_list]
        await query.message.reply_text("Select your goal:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("goal|"):
        goal = data.split("|")[1]
        save_player(user_id, goals=goal)
        context.user_data['step'] = None
        await query.message.reply_text("⚠️ From now onwards you don't have any option.")
        await asyncio.sleep(1)
        await query.message.reply_text("This was your final decision.")
        await asyncio.sleep(1)
        await query.message.reply_text("The battle begins.")
        await asyncio.sleep(1)
        await query.message.reply_text("Good Luck")
        await asyncio.sleep(1)
        await assign_new_task(user_id, context)

    elif data == "task_done":
        await handle_task_completion(user_id, context)

    elif data.startswith("talk|"):
        character = data.split("|")[1]
        reply = await chat_with_gpt(f"I just completed 5 quests. Give me a message as {character} from Solo Leveling.")
        await context.bot.send_message(user_id, reply)
        await assign_new_task(user_id, context)

    elif data == "skip_talk":
        await context.bot.send_message(user_id, "🧬 SYSTEM: Privilege skipped. Continuing mission.")
        await assign_new_task(user_id, context)

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.run_polling()

if __name__ == '__main__':
    main()
