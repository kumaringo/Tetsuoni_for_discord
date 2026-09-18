from station_data import STATION_COORDINATES
from pin import send_map_with_pins, USER_CONFIG

async def handle_registration_logic(message, participant_data, users_participated, REQUIRED_USERS):
    text = message.content.strip()

    chat_id = message.channel.id
    user_id = str(message.author.id)
    display_name = message.author.display_name

    # IDからユーザー設定を取得（未登録の場合は白チーム・表示名でフォールバック）
    config = USER_CONFIG.get(user_id, {"team": "白", "real_name": display_name})
    team = config["team"]
    real_name = config["real_name"]

    if chat_id not in participant_data:
        participant_data[chat_id] = {}
        users_participated[chat_id] = set()

    is_update = user_id in participant_data[chat_id]

    if text in STATION_COORDINATES:
        participant_data[chat_id][user_id] = {
            "station": text,
            "display_name": display_name
        }
        users_participated[chat_id].add(user_id)
        display_text = text
    else:
        await message.channel.send(f"「{text}」は駅名リストにありません。")
        return

    current_count = len(users_participated[chat_id])

    if current_count >= REQUIRED_USERS:
        await send_map_with_pins(message.channel, participant_data[chat_id])
        participant_data[chat_id] = {}
        users_participated[chat_id] = set()
    else:
        status_line = "【報告更新】" if is_update else "【報告受理】"
        reply_text = f"{status_line}\n名前: {real_name}\nチーム: {team}\n内容: {display_text}\n現在: {current_count} / {REQUIRED_USERS} 人"
        await message.channel.send(reply_text)