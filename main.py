import os
import discord
from discord.ext import commands
import asyncio
from config import TOKEN

intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"Бот {bot.user.name} успешно запущен!")
    print(f"ID бота: {bot.user.id}")
    
    try:
        print("Начинаем синхронизацию slash-команд...")
        synced = await bot.tree.sync()
        print(f"Успешно синхронизировано {len(synced)} slash-команд")
    except Exception as e:
        print(f"Ошибка при синхронизации команд: {e}")
        
    print("------")

async def load_cogs():
    if not os.path.exists("cogs"):
        os.makedirs("cogs")
        print("Создана папка cogs")
        
    for filename in os.listdir("cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"Ког {filename} успешно загружен")
            except Exception as e:
                print(f"Не удалось загрузить ког {filename}: {e}")

# Запуск бота
async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
