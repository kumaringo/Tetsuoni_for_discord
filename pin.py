import os
import io
from PIL import Image, ImageDraw, ImageFont
import discord
from station_data import STATION_COORDINATES

# DiscordユーザーID (18桁の数字) でユーザー・チームを定義
USER_CONFIG = {
    "1279023323950350371": {"team": "赤", "real_name": "茂野"},
    "1549752859581481041": {"team": "赤", "real_name": "小林"},
    "1549709823744933901": {"team": "赤", "real_name": "仁田"},
    "1073580722247450704": {"team": "赤", "real_name": "二宮"},
    "1203962597351755806": {"team": "赤", "real_name": "上保"},

    "1047412751259140187": {"team": "青", "real_name": "井原"},
    "1550112124930490400": {"team": "青", "real_name": "小澤"},
    "1550437565549649924": {"team": "青", "real_name": "伊藤"},
    "1341744353978355837": {"team": "青", "real_name": "高木"},
    "": {"team": "青", "real_name": "茂野"},

    "1534202522896699592": {"team": "白", "real_name": "猪狩"},
    "1352999265231966281": {"team": "白", "real_name": "工藤"},
    "777050829571227688": {"team": "白", "real_name": "遠藤"},
    "1550265450502291607": {"team": "白", "real_name": "村山"},
    "": {"team": "白", "real_name": "茂野"},
    
    "1550079091225534536": {"team": "ゲームマスター", "real_name": "成田"},
}

TEAM_COLORS = {
    "赤": (255, 0, 0),
    "青": (0, 191, 255),
    "白": (255, 255, 255),
    "ゲームマスター": (255, 255, 0),  # 黄色
    "重複": (0, 0, 0)
}

TEAMS_ORDER = ["赤", "青", "白", "ゲームマスター"]

PIN_RADIUS = 10
PIN_OUTLINE_WIDTH = 2

async def send_map_with_pins(channel, participants):
    try:
        orig_img = Image.open("Rosenzu.png").convert("RGBA")
        orig_w, orig_h = orig_img.size

        target_alpha = int(255 * 0.7)
        new_alpha = Image.new('L', orig_img.size, color=target_alpha)
        orig_img.putalpha(new_alpha)
        img = Image.new("RGBA", (orig_w, orig_h), (255, 255, 255, 255))
        img.paste(orig_img, (0, 0), orig_img)

        draw = ImageDraw.Draw(img)
        scale_x, scale_y = 1.0, 1.0
        scaled_radius = PIN_RADIUS
        outline_extra = PIN_OUTLINE_WIDTH

        font_path = os.path.join(os.path.dirname(__file__), 'fonts', 'NotoSansJP-Regular.ttf')
        try:
            font = ImageFont.truetype(font_path, 16) 
        except Exception:
            font = ImageFont.load_default()

        station_to_users = {}
        report_buckets = {t: [] for t in TEAMS_ORDER}

        for user_id, data in participants.items():
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

        # --- 駅ピンの描画 ---
        for st_name, users in station_to_users.items():
            x = int(STATION_COORDINATES[st_name][0] * scale_x)
            y = int(STATION_COORDINATES[st_name][1] * scale_y)
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
                for dx, dy in [(-1,-1),(1,-1),(-1,1),(1,1),(0,-1),(0,1),(-1,0),(1,0)]:
                    draw.text((text_pos[0]+dx, text_pos[1]+dy), txt, fill=(0,0,0), font=font)
                draw.text(text_pos, txt, fill=text_color, font=font)
                current_y += 18 

        out_buf = io.BytesIO()
        img.save(out_buf, format='PNG')
        out_buf.seek(0)

        total_users = sum(len(v) for v in report_buckets.values())
        report_text = f"🚨 参加者 {total_users} 人のデータ 🚨\n"
        for t in TEAMS_ORDER:
            if report_buckets.get(t):
                report_text += "\n" + "\n".join(report_buckets[t])

        discord_file = discord.File(fp=out_buf, filename="map.png")
        await channel.send(content=report_text.strip(), file=discord_file)

    except Exception as e:
        await channel.send(f"描画エラー: {e}")