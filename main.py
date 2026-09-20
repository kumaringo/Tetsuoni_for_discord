import os
import io
import asyncio
from threading import Thread
from flask import Flask
from PIL import Image, ImageDraw, ImageFont
import discord
from station_data import STATION_COORDINATES

# === 1. UptimeRobot応答用の軽量Webサーバー設定 ===
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_http_server)
    t.daemon = True
    t.start()


# === 2. ユーザーおよびチーム設定 ===
USER_CONFIG = {
    # 赤チーム
    "1279023323950350371": {"team": "赤", "real_name": "茂野"},
    "1549752859581481041": {"team": "赤", "real_name": "小林"},
    "1549709823744933901": {"team": "赤", "real_name": "仁田"},
    "1073580722247450704": {"team": "赤", "real_name": "二宮"},
    "1203962597351755806": {"team": "赤", "real_name": "上保"},

    # 青チーム
    "1047412751259140187": {"team": "青", "real_name": "井原"},
    "1550112124930490400": {"team": "青", "real_name": "小澤"},
    "1550437565549649924": {"team": "青", "real_name": "伊藤"},
    "1341744353978355837": {"team": "青", "real_name": "高木"},

    # 白チーム
    "1534202522896699592": {"team": "白", "real_name": "猪狩"},
    "1352999265231966281": {"team": "白", "real_name": "工藤"},
    "777050829571227688": {"team": "白", "real_name": "遠藤"},
    "1550265450502291607": {"team": "白", "real_name": "村山"},
    
    # ゲームマスター
    "1550079091225534536": {"team": "ゲームマスター", "real_name": "成田"},
}

TEAM_COLORS = {
    "赤": (255, 0, 0),
    "青": (0, 191, 255),
    "白": (255, 255, 255),
    "ゲームマスター": (255, 255, 0),
    "重複": (0, 0, 0)
}

TEAMS_ORDER = ["赤", "青", "白", "ゲームマスター"]

PIN_RADIUS = 6.5
PIN_OUTLINE_WIDTH = 2

# === 3. 状態管理変数 ===
participants = {}    # 参加者の入力データ辞書
is_accepting = True   # 受付フラグ

# === 4. 画像・フォント事前ロード ===
BASE_DIR = os.path.dirname(__file__)

_orig_img = Image.open(os.path.join(BASE_DIR, "Rosenzu.png")).convert("RGBA")
_target_alpha = int(255 * 0.7)
_new_alpha = Image.new('L', _orig_img.size, color=_target_alpha)
_orig_img.putalpha(_new_alpha)

PRELOADED_MAP = Image.new("RGBA", _orig_img.size, (255, 255, 255, 255))
PRELOADED_MAP.paste(_orig_img, (0, 0), _orig_img)

font_path = os.path.join(BASE_DIR, 'fonts', 'NotoSansJP-Regular.ttf')
try:
    PRELOADED_FONT = ImageFont.truetype(font_path, 13)
except Exception:
    PRELOADED_FONT = ImageFont.load_default()


# === 5. マップ生成ロジック ===
def _generate_map_image_sync(participants_data):
    img = PRELOADED_MAP.copy()
    draw = ImageDraw.Draw(img)

    scaled_radius = PIN_RADIUS
    outline_extra = PIN_OUTLINE_WIDTH
    font = PRELOADED_FONT

    station_to_users = {}
    report_buckets = {t: [] for t in TEAMS_ORDER}

    for user_id, data in participants_data.items():
        st_name = data.get("station")
        if not st_name:
            continue

        default_name = data.get("display_name", "ゲスト")
        config = USER_CONFIG.get(str(user_id), {"team": "白", "real_name": default_name})
        team = config["team"]
        real_name = config["real_name"]

        if team not in report_buckets:
            report_buckets[team] = []
        report_buckets[team].append(f"「{team}:{real_name}」: {st_name}")

        if st_name in STATION_COORDINATES:
            if st_name not in station_to_users:
                station_to_users[st_name] = []
            station_to_users[st_name].append({"team": team, "char": real_name[0]})

    for st_name, users in station_to_users.items():
        x = int(STATION_COORDINATES[st_name][0])
        y = int(STATION_COORDINATES[st_name][1])
        pin_color = TEAM_COLORS["重複"] if len(users) > 1 else TEAM_COLORS.get(users[0]["team"], (255, 255, 255))

        draw.ellipse((x - (scaled_radius + outline_extra), y - (scaled_radius + outline_extra), 
                      x + (scaled_radius + outline_extra), y + (scaled_radius + outline_extra)), fill=(0, 0, 0))
        draw.ellipse((x - scaled_radius, y - scaled_radius, x + scaled_radius, y + scaled_radius), fill=pin_color)
        
        team_summary = {t: [] for t in TEAMS_ORDER}
        for u in users:
            if u['team'] in team_summary:
                team_summary[u['team']].append(u['char'])

        display_lines = []
        for t in TEAMS_ORDER:
            if team_summary.get(t):
                line_txt = f"{t}:{ ''.join(team_summary[t]) }"
                display_lines.append((t, line_txt))

        current_y = y - scaled_radius
        for t_name, txt in display_lines:
            text_color = TEAM_COLORS.get(t_name, (255, 255, 255))
            text_pos = (x + scaled_radius + 5, current_y)
            
            draw.text(
                text_pos, 
                txt, 
                fill=text_color, 
                font=font, 
                stroke_width=1, 
                stroke_fill=(0, 0, 0)
            )
            current_y += 14

    out_buf = io.BytesIO()
    img.save(out_buf, format='PNG', compress_level=1)
    out_buf.seek(0)

    total_users = sum(len(v) for v in report_buckets.values())
    report_text = f"🚨 参加者 {total_users} 人のデータ 🚨\n"
    for t in TEAMS_ORDER:
        if report_buckets.get(t):
            report_text += "\n" + "\n".join(report_buckets[t])

    return out_buf, report_text.strip()


async def send_map_with_pins(channel, participants_data):
    try:
        print("[INFO] マップ画像作成を開始します...")
        out_buf, report_text = await asyncio.to_thread(_generate_map_image_sync, participants_data)
        
        print("[INFO] 画像作成完了。Discordへ送信中...")
        discord_file = discord.File(fp=out_buf, filename="map.png")
        await channel.send(content=report_text, file=discord_file)
        print("[INFO] 送信完了！")

    except Exception as e:
        print(f"[ERROR] 描画・送信エラー: {e}")
        await channel.send(f"描画エラー: {e}")


# === 6. Discord Botイベント処理 ===
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"[INFO] ログインしました: {client.user}")

@client.event
async def on_message(message):
    global is_accepting, participants

    if message.author.bot:
        return

    # 全角スラッシュを半角にし、大文字を小文字に変換して前後空白を除去
    content = message.content.strip().replace("／", "/").lower()

    # --- コマンド1: /finish （マップ出力＆データを自動リセットして次の新しい受付を開始） ---
    if content == "/finish":
        if not participants:
            await message.channel.send("⚠️ まだ入力データがありません。")
            return

        await message.channel.send("🗺️ マップを集計して出力します...")
        await send_map_with_pins(message.channel, participants)

        # データをリセットし、新しい受付を即座に開始
        participants.clear()
        is_accepting = True
        await message.channel.send("✨ 記録を自動リセットしました！新しいゲームの受付を開始します（1人目から登録可能です）。")
        return

    # --- コマンド2: /reset （マップ出力なしで記録をリセットして1人目からやり直す） ---
    if content == "/reset":
        participants.clear()
        is_accepting = True
        await message.channel.send("🔄 今までの記録をリセットしました！1人目からの集計をやり直します。")
        return

    # --- コマンド3: /remaining （未入力者リスト出力：ゲームマスターを含む全チーム対象） ---
    if content == "/remaining":
        unsubmitted_by_team = {t: [] for t in TEAMS_ORDER}
        
        for user_id, config in USER_CONFIG.items():
            team = config["team"]
            real_name = config["real_name"]
            
            if user_id not in participants or not participants[user_id].get("station"):
                if team in unsubmitted_by_team:
                    unsubmitted_by_team[team].append(real_name)

        total_unsubmitted = sum(len(names) for names in unsubmitted_by_team.values())

        if total_unsubmitted == 0:
            await message.channel.send("🎉 全員の入力が完了しています！")
            return

        msg = f"⏳ **未入力者（残り {total_unsubmitted} 人）:**\n"
        for team in TEAMS_ORDER:
            names = unsubmitted_by_team.get(team, [])
            if names:
                msg += f"・【{team}チーム】: {', '.join(names)}\n"

        await message.channel.send(msg.strip())
        return

    # --- 通常処理: 駅名登録 ---
    raw_content = message.content.strip()
    if raw_content in STATION_COORDINATES:
        if not is_accepting:
            await message.channel.send("❌ 現在は受付を停止しています。次のゲーム開始までお待ちください。")
            return

        user_id = str(message.author.id)
        display_name = message.author.display_name

        participants[user_id] = {
            "station": raw_content,
            "display_name": display_name
        }
        await message.channel.send(f"✅ {message.author.mention} さんの駅を「{raw_content}」で受け付けました！（現在 {len(participants)} 人）")


# === 7. 起動処理 ===
if __name__ == "__main__":
    keep_alive()
    
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if TOKEN:
        client.run(TOKEN)
    else:
        print("[ERROR] DISCORD_BOT_TOKEN 環境変数が設定されていません。")
