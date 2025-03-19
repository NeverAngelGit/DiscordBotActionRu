import discord
from discord.ext import commands
from discord import app_commands, ui
import datetime
import sys
import os
import re
from datetime import datetime, timedelta

# Добавляем родительский каталог в sys.path для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Модальное окно для ввода продолжительности мьюта
class MuteModal(ui.Modal, title="Установить продолжительность мьюта"):
    def __init__(self, user_id, mute_type, role_id):
        super().__init__()
        self.user_id = user_id
        self.mute_type = mute_type
        self.role_id = role_id
        
    duration = ui.TextInput(
        label="Продолжительность (1ч-16ч)",
        placeholder="Введите продолжительность (например, 2ч)",
        min_length=2,
        max_length=3,
        required=True
    )
    
    reason = ui.TextInput(
        label="Причина мьюта",
        placeholder="Введите причину наказания",
        min_length=3,
        max_length=100,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Проверка формата продолжительности (должна быть от 1ч до 16ч)
        duration_str = self.duration.value.lower()
        if not re.match(r'^([1-9]|1[0-6])ч$', duration_str):
            await interaction.response.send_message("Неверный формат продолжительности. Пожалуйста, используйте значение от 1ч до 16ч.", ephemeral=True)
            return
            
        # Извлечение часов из ввода
        hours = int(duration_str[:-1])
        if hours < 1 or hours > 16:
            await interaction.response.send_message("Продолжительность должна быть от 1 до 16 часов.", ephemeral=True)
            return
            
        # Получение участника и роли
        member = interaction.guild.get_member(self.user_id)
        role = interaction.guild.get_role(int(self.role_id))
        
        if not member or not role:
            await interaction.response.send_message("Не удалось найти пользователя или роль.", ephemeral=True)
            return
            
        # Добавление роли пользователю
        try:
            reason_text = self.reason.value
            await member.add_roles(role, reason=f"{self.mute_type} мьют: {reason_text}")
            
            # Отправка подтверждающего сообщения
            await interaction.response.send_message(
                f"✅ {self.mute_type} мьют применен к {member.mention} на {duration_str}. Причина: {reason_text}", 
                ephemeral=False
            )
            
            # Логирование действия в указанный канал
            if hasattr(config, 'CHANNEL_LOG_ID') and config.CHANNEL_LOG_ID:
                try:
                    log_channel = interaction.guild.get_channel(int(config.CHANNEL_LOG_ID))
                    if log_channel:
                        # Создание встраиваемого сообщения для лога
                        log_embed = discord.Embed(
                            title=f"{self.mute_type} Мьют применен",
                            color=discord.Color.dark_embed(),
                            timestamp=datetime.now()
                        )
                        log_embed.add_field(name="Модератор", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
                        log_embed.add_field(name="Пользователь", value=f"{member.mention} ({member.id})", inline=False)
                        log_embed.add_field(name="Продолжительность", value=duration_str, inline=True)
                        log_embed.add_field(name="Причина", value=reason_text, inline=True)
                        
                        # Добавление аватара пользователя, если доступно
                        if member.avatar:
                            log_embed.set_thumbnail(url=member.avatar.url)
                            
                        await log_channel.send(embed=log_embed)
                except Exception as e:
                    print(f"Не удалось записать действие мьюта в лог: {e}")
            
        except discord.Forbidden:
            await interaction.response.send_message("У меня нет прав добавлять роли этому пользователю.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Произошла ошибка: {str(e)}", ephemeral=True)

# Вид кнопок для действий с мьютом
# Обновление класса MuteView для включения кнопок локального бана
class MuteView(ui.View):
    def __init__(self, user_id, member):
        super().__init__(timeout=60)  # Кнопки истекают через 60 секунд
        self.user_id = user_id
        self.member = member
        
        # Проверка наличия у пользователя ролей мьюта и отключение кнопок соответственно
        voice_mute_role = member.guild.get_role(int(config.VOICE_MUTE_ID))
        text_mute_role = member.guild.get_role(int(config.TEXT_MUTE_ID))
        local_ban_role = member.guild.get_role(int(config.LOCAL_BAN_ID))
        
        # Отключение кнопок снятия мьюта, если у пользователя нет соответствующей роли
        self.remove_voice_mute_button.disabled = voice_mute_role not in member.roles
        self.remove_text_mute_button.disabled = text_mute_role not in member.roles
        self.remove_local_ban_button.disabled = local_ban_role not in member.roles
        
    @ui.button(label="Голосовой мьют", style=discord.ButtonStyle.grey, emoji="🔇", row=0)
    async def voice_mute_button(self, interaction: discord.Interaction, button: ui.Button):
        # Проверка наличия у пользователя прав
        has_permission = False
        for role_id in config.MODERATION:
            role = interaction.guild.get_role(int(role_id))
            if role in interaction.user.roles:
                has_permission = True
                break
                
        if not has_permission:
            await interaction.response.send_message("У вас нет прав использовать эту команду.", ephemeral=True)
            return
            
        # Открытие модального окна для ввода продолжительности
        await interaction.response.send_modal(MuteModal(self.user_id, "Голосовой", config.VOICE_MUTE_ID))
        
    @ui.button(label="Текстовый мьют", style=discord.ButtonStyle.grey, emoji="🔒", row=0)
    async def text_mute_button(self, interaction: discord.Interaction, button: ui.Button):
        # Проверка наличия у пользователя прав
        has_permission = False
        for role_id in config.MODERATION:
            role = interaction.guild.get_role(int(role_id))
            if role in interaction.user.roles:
                has_permission = True
                break
                
        if not has_permission:
            await interaction.response.send_message("У вас нет прав использовать эту команду.", ephemeral=True)
            return
            
        # Открытие модального окна для ввода продолжительности
        await interaction.response.send_modal(MuteModal(self.user_id, "Текстовый", config.TEXT_MUTE_ID))
    
    @ui.button(label="Снять голосовой мьют", style=discord.ButtonStyle.grey, emoji="🔊", row=1)
    async def remove_voice_mute_button(self, interaction: discord.Interaction, button: ui.Button):
        # Проверка наличия у пользователя прав
        has_permission = False
        for role_id in config.MODERATION:
            role = interaction.guild.get_role(int(role_id))
            if role in interaction.user.roles:
                has_permission = True
                break
                
        if not has_permission:
            await interaction.response.send_message("У вас нет прав использовать эту команду.", ephemeral=True)
            return
        
        # Получение роли голосового мьюта
        voice_mute_role = interaction.guild.get_role(int(config.VOICE_MUTE_ID))
        
        # Проверка наличия у пользователя роли
        if voice_mute_role not in self.member.roles:
            await interaction.response.send_message("У этого пользователя нет голосового мьюта.", ephemeral=True)
            return
            
        # Открытие модального окна для ввода причины
        await interaction.response.send_modal(UnmuteModal(self.member, "Голосовой", config.VOICE_MUTE_ID))
    
    @ui.button(label="Снять текстовый мьют", style=discord.ButtonStyle.grey, emoji="🔓", row=1)
    async def remove_text_mute_button(self, interaction: discord.Interaction, button: ui.Button):
        # Проверка наличия у пользователя прав
        has_permission = False
        for role_id in config.MODERATION:
            role = interaction.guild.get_role(int(role_id))
            if role in interaction.user.roles:
                has_permission = True
                break
                
        if not has_permission:
            await interaction.response.send_message("У вас нет прав использовать эту команду.", ephemeral=True)
            return
        
        # Получение роли текстового мьюта
        text_mute_role = interaction.guild.get_role(int(config.TEXT_MUTE_ID))
        
        # Проверка наличия у пользователя роли
        if text_mute_role not in self.member.roles:
            await interaction.response.send_message("У этого пользователя нет текстового мьюта.", ephemeral=True)
            return
            
        # Открытие модального окна для ввода причины
        await interaction.response.send_modal(UnmuteModal(self.member, "Текстовый", config.TEXT_MUTE_ID))
    
    @ui.button(label="Локальный бан", style=discord.ButtonStyle.grey, emoji="⛔", row=2)
    async def local_ban_button(self, interaction: discord.Interaction, button: ui.Button):
        # Проверка наличия у пользователя прав
        has_permission = False
        for role_id in config.MODERATION:
            role = interaction.guild.get_role(int(role_id))
            if role in interaction.user.roles:
                has_permission = True
                break
                
        if not has_permission:
            await interaction.response.send_message("У вас нет прав использовать эту команду.", ephemeral=True)
            return
            
        # Открытие модального окна для ввода продолжительности и причины
        await interaction.response.send_modal(LocalBanModal(self.user_id))
        
    @ui.button(label="Снять локальный бан", style=discord.ButtonStyle.grey, emoji="🔓", row=2)
    async def remove_local_ban_button(self, interaction: discord.Interaction, button: ui.Button):
        # Проверка наличия у пользователя прав
        has_permission = False
        for role_id in config.MODERATION:
            role = interaction.guild.get_role(int(role_id))
            if role in interaction.user.roles:
                has_permission = True
                break
                
        if not has_permission:
            await interaction.response.send_message("У вас нет прав использовать эту команду.", ephemeral=True)
            return
        
        # Получение роли локального бана
        local_ban_role = interaction.guild.get_role(int(config.LOCAL_BAN_ID))
        
        # Проверка наличия у пользователя роли
        if local_ban_role not in self.member.roles:
            await interaction.response.send_message("У этого пользователя нет локального бана.", ephemeral=True)
            return
            
        # Открытие модального окна для ввода причины
        await interaction.response.send_modal(RemoveLocalBanModal(self.member))

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="action", description="Получить информацию о пользователе (только для модерации)")
    async def action(self, interaction: discord.Interaction, user: discord.User):
        # Проверка наличия у пользователя роли модерации
        has_permission = False
        
        # Если список MODERATION пуст, отказать всем в доступе
        if not config.MODERATION:
            await interaction.response.send_message("Эта команда в настоящее время ограничена. Роли модерации не настроены.", ephemeral=True)
            return
            
        # Проверка наличия у пользователя любой из ролей модерации
        for role_id in config.MODERATION:
            role = interaction.guild.get_role(int(role_id))
            if role in interaction.user.roles:
                has_permission = True
                break
                
        if not has_permission:
            await interaction.response.send_message("У вас нет прав использовать эту команду.", ephemeral=True)
            return
            
        # Получение объекта участника для доступа к дате присоединения
        member = interaction.guild.get_member(user.id)
        if not member:
            await interaction.response.send_message(f"Пользователь {user.name} не является участником этого сервера.", ephemeral=True)
            return
            
        # Создание встраиваемого сообщения с информацией о пользователе
        embed = discord.Embed(
            title=f"Информация о пользователе: {user.name}",
            color=discord.Color.dark_embed(),
            timestamp=datetime.now()
        )
        
        # Добавление полей информации о пользователе
        embed.add_field(name="Имя пользователя", value=user.mention, inline=True)
        embed.add_field(name="ID пользователя", value=f"```{user.id}```", inline=True)
        embed.add_field(name="Регистрация в Discord", value=f"```{user.created_at.strftime("%Y-%m-%d %H:%M:%S")}```", inline=False)
        embed.add_field(name="Дата присоединения к серверу", value=f"```{member.joined_at.strftime("%Y-%m-%d %H:%M:%S")}```", inline=False)
        
        # Установка аватара пользователя в качестве миниатюры, если доступно
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
            
        embed.set_footer(text=f"Запрошено {interaction.user.name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        
        # Создание вида с кнопками мьюта
        view = MuteView(user.id, member)
        
        # Отправка встраиваемого сообщения с кнопками
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Moderation(bot))


# Сначала добавим новое модальное окно для причин снятия мьюта
class UnmuteModal(ui.Modal, title="Снять мьют"):
    def __init__(self, member, mute_type, role_id):
        super().__init__()
        self.member = member
        self.mute_type = mute_type
        self.role_id = role_id
        
    reason = ui.TextInput(
        label=f"Причина снятия мьюта",
        placeholder="Введите причину снятия наказания",
        min_length=3,
        max_length=100,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Получение роли
        role = interaction.guild.get_role(int(self.role_id))
        
        if not role:
            await interaction.response.send_message("Не удалось найти роль.", ephemeral=True)
            return
            
        # Проверка наличия у пользователя роли (могла быть снята, пока модальное окно было открыто)
        if role not in self.member.roles:
            await interaction.response.send_message(f"У этого пользователя больше нет {self.mute_type.lower()} мьюта.", ephemeral=True)
            return
            
        # Снятие роли
        try:
            reason_text = self.reason.value
            await self.member.remove_roles(role, reason=f"{self.mute_type} мьют снят: {reason_text}")
            
            # Отправка подтверждающего сообщения
            await interaction.response.send_message(
                f"✅ {self.mute_type} мьют снят с {self.member.mention}. Причина: {reason_text}", 
                ephemeral=False
            )
            
            # Логирование действия
            if hasattr(config, 'CHANNEL_LOG_ID') and config.CHANNEL_LOG_ID:
                try:
                    log_channel = interaction.guild.get_channel(int(config.CHANNEL_LOG_ID))
                    if log_channel:
                        # Создание встраиваемого сообщения для лога
                        log_embed = discord.Embed(
                            title=f"{self.mute_type} Мьют снят",
                            color=discord.Color.dark_embed(),
                            timestamp=datetime.now()
                        )
                        log_embed.add_field(name="Модератор", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
                        log_embed.add_field(name="Пользователь", value=f"{self.member.mention} ({self.member.id})", inline=False)
                        log_embed.add_field(name="Причина", value=reason_text, inline=False)
                        
                        # Добавление аватара пользователя, если доступно
                        if self.member.avatar:
                            log_embed.set_thumbnail(url=self.member.avatar.url)
                            
                        await log_channel.send(embed=log_embed)
                except Exception as e:
                    print(f"Не удалось записать снятие мьюта в лог: {e}")
                    
        except discord.Forbidden:
            await interaction.response.send_message("У меня нет прав снимать роли с этого пользователя.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Произошла ошибка: {str(e)}", ephemeral=True)

# Модальное окно для ввода продолжительности локального бана
class LocalBanModal(ui.Modal, title="Применить локальный бан"):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        
    duration = ui.TextInput(
        label="Продолжительность (7-30д или 0 для постоянного)",
        placeholder="Введите продолжительность (например, 7д, 14д, 30д или 0)",
        min_length=1,
        max_length=3,
        required=True
    )
    
    reason = ui.TextInput(
        label="Причина локального бана",
        placeholder="Введите причину наказания",
        min_length=3,
        max_length=100,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Проверка формата продолжительности
        duration_str = self.duration.value.lower()
        permanent = False
        
        if duration_str == "0":
            permanent = True
            duration_display = "постоянный"
        elif not re.match(r'^([7-9]|[1-2][0-9]|30)д$', duration_str):
            await interaction.response.send_message("Неверный формат продолжительности. Пожалуйста, используйте значение от 7д до 30д или 0 для постоянного.", ephemeral=True)
            return
        else:
            duration_display = duration_str
            
        # Получение участника и роли
        member = interaction.guild.get_member(self.user_id)
        ban_role = interaction.guild.get_role(int(config.LOCAL_BAN_ID))
        
        if not member or not ban_role:
            await interaction.response.send_message("Не удалось найти пользователя или роль локального бана.", ephemeral=True)
            return
            
        # Проверка наличия у пользователя роли бана
        if ban_role in member.roles:
            await interaction.response.send_message("У этого пользователя уже есть локальный бан.", ephemeral=True)
            return
            
        # Создание каталога для ролей пользователя, если он не существует
        if not os.path.exists('user_roles'):
            os.makedirs('user_roles')
            
        # Сохранение текущих ролей пользователя (кроме @everyone) для восстановления позже
        role_ids = [str(role.id) for role in member.roles if role.id != interaction.guild.id]
        with open(f'user_roles/{member.id}.txt', 'w') as f:
            f.write(','.join(role_ids))
            
        # Удаление всех ролей и добавление роли бана
        try:
            reason_text = self.reason.value
            
            # Удаление всех ролей, кроме @everyone
            roles_to_remove = [role for role in member.roles if role.id != interaction.guild.id]
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason=f"Локальный бан: {reason_text}")
                
            # Добавление роли бана
            await member.add_roles(ban_role, reason=f"Локальный бан: {reason_text}")
            
            # Отправка подтверждающего сообщения
            await interaction.response.send_message(
                f"✅ Локальный бан применен к {member.mention} на {duration_display}. Причина: {reason_text}", 
                ephemeral=False
            )
            
            # Логирование действия
            if hasattr(config, 'CHANNEL_LOG_ID') and config.CHANNEL_LOG_ID:
                try:
                    log_channel = interaction.guild.get_channel(int(config.CHANNEL_LOG_ID))
                    if log_channel:
                        # Создание встраиваемого сообщения для лога
                        log_embed = discord.Embed(
                            title="Локальный бан применен",
                            color=discord.Color.dark_embed(),
                            timestamp=datetime.now()
                        )
                        log_embed.add_field(name="Модератор", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
                        log_embed.add_field(name="Пользователь", value=f"{member.mention} ({member.id})", inline=False)
                        log_embed.add_field(name="Продолжительность", value=duration_display, inline=True)
                        log_embed.add_field(name="Причина", value=reason_text, inline=True)
                        
                        # Добавление аватара пользователя, если доступно
                        if member.avatar:
                            log_embed.set_thumbnail(url=member.avatar.url)
                            
                        await log_channel.send(embed=log_embed)
                except Exception as e:
                    print(f"Не удалось записать действие локального бана в лог: {e}")
            
        except discord.Forbidden:
            await interaction.response.send_message("У меня нет прав управлять ролями этого пользователя.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Произошла ошибка: {str(e)}", ephemeral=True)

# Модальное окно для снятия локального бана
class RemoveLocalBanModal(ui.Modal, title="Снять локальный бан"):
    def __init__(self, member):
        super().__init__()
        self.member = member
        
    reason = ui.TextInput(
        label="Причина снятия локального бана",
        placeholder="Введите причину снятия наказания",
        min_length=3,
        max_length=100,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Получение роли бана
        ban_role = interaction.guild.get_role(int(config.LOCAL_BAN_ID))
        
        if not ban_role:
            await interaction.response.send_message("Не удалось найти роль локального бана.", ephemeral=True)
            return
            
        # Проверка наличия у пользователя роли бана
        if ban_role not in self.member.roles:
            await interaction.response.send_message("У этого пользователя нет локального бана.", ephemeral=True)
            return
            
        # Снятие роли бана
        try:
            reason_text = self.reason.value
            await self.member.remove_roles(ban_role, reason=f"Локальный бан снят: {reason_text}")
            
            # Восстановление оригинальных ролей, если доступно
            roles_restored = False
            roles_file_path = f'user_roles/{self.member.id}.txt'
            
            if os.path.exists(roles_file_path):
                with open(roles_file_path, 'r') as f:
                    role_ids = f.read().strip().split(',')
                    
                roles_to_add = []
                for role_id in role_ids:
                    if role_id:  # Пропуск пустых строк
                        role = interaction.guild.get_role(int(role_id))
                        if role:
                            roles_to_add.append(role)
                
                if roles_to_add:
                    await self.member.add_roles(*roles_to_add, reason=f"Восстановление ролей после снятия локального бана")
                    roles_restored = True
                    
                # Удаление файла ролей после восстановления
                os.remove(roles_file_path)
            
            # Отправка подтверждающего сообщения
            restored_msg = " Оригинальные роли были восстановлены." if roles_restored else ""
            await interaction.response.send_message(
                f"✅ Локальный бан снят с {self.member.mention}. Причина: {reason_text}.{restored_msg}", 
                ephemeral=False
            )
            
            # Логирование действия
            if hasattr(config, 'CHANNEL_LOG_ID') and config.CHANNEL_LOG_ID:
                try:
                    log_channel = interaction.guild.get_channel(int(config.CHANNEL_LOG_ID))
                    if log_channel:
                        # Создание встраиваемого сообщения для лога
                        log_embed = discord.Embed(
                            title="Локальный бан снят",
                            color=discord.Color.dark_embed(),
                            timestamp=datetime.now()
                        )
                        log_embed.add_field(name="Модератор", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
                        log_embed.add_field(name="Пользователь", value=f"{self.member.mention} ({self.member.id})", inline=False)
                        log_embed.add_field(name="Причина", value=reason_text, inline=False)
                        
                        # Добавление аватара пользователя, если доступно
                        if self.member.avatar:
                            log_embed.set_thumbnail(url=self.member.avatar.url)
                            
                        await log_channel.send(embed=log_embed)
                except Exception as e:
                    print(f"Не удалось записать снятие локального бана в лог: {e}")
                    
        except discord.Forbidden:
            await interaction.response.send_message("У меня нет прав снимать роли с этого пользователя.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Произошла ошибка: {str(e)}", ephemeral=True)