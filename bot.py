import logging
import random
import re
from nba_api.stats.static import players as nba_players
from nba_api.stats.endpoints import commonplayerinfo, playerdashboardbygeneralsplits, leagueleaders
from telegram import Update, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

TELEGRAM_TOKEN = "7996765199:AAFzTsCHWW5OG45WcB1r_fjxvKE2al0FOkY"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

FUN_FACTS = {
    "lebron james":           "The only player in NBA history with 40,000+ points.",
    "stephen curry":          "Changed the game — made the 3-pointer the most dangerous shot in basketball.",
    "kevin durant":           "One of only a few players to score 50+ points in a Finals game.",
    "giannis antetokounmpo":  "Went from selling items on the streets of Athens to NBA MVP.",
    "luka doncic":            "Youngest player with a 40-pt triple-double in NBA history.",
    "nikola jokic":           "The slowest-looking superstar who somehow makes everyone look slow.",
    "jayson tatum":           "First Celtic to average 30+ PPG in a playoff series since Larry Bird.",
    "devin booker":           "Scored 70 points in a single game at just 20 years old.",
    "anthony davis":          "One of the rare bigs who can guard all 5 positions.",
    "jimmy butler":           "Went from the 30th pick to an NBA Finals MVP candidate.",
    "default":                "One of the few people skilled enough to make the NBA — top 0.0001% of all players."
}

FAMOUS_PLAYERS = [
    "LeBron James", "Stephen Curry", "Kevin Durant",
    "Giannis Antetokounmpo", "Luka Doncic", "Nikola Jokic",
    "Jayson Tatum", "Devin Booker", "Anthony Davis",
    "Jimmy Butler", "Kawhi Leonard", "Damian Lillard"
]

def get_photo_url(player_id: int) -> str:
    """
    Return the NBA CDN headshot URL for a given player ID.
    Images are 1040x760 PNG hosted at cdn.nba.com.
    """
    return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"

def find_player(name: str):
    """
    Search for an NBA player by full or partial name.
    Tries full name match first, then falls back to last name.
    Returns the first active player found, or any match if none are active.
    """
    results = nba_players.find_players_by_full_name(name)
    if results:
        active = [p for p in results if p["is_active"]]
        return active[0] if active else results[0]
    results = nba_players.find_players_by_last_name(name.split()[-1])
    if results:
        active = [p for p in results if p["is_active"]]
        return active[0] if active else results[0]
    return None

def get_player_info(player_id: int) -> dict:
    """
    Fetch detailed player profile from the NBA API using player ID.
    Returns a dict with fields like DISPLAY_FIRST_LAST, TEAM_NAME,
    POSITION, JERSEY, COUNTRY, HEIGHT, WEIGHT, SEASON_EXP.
    """
    info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
    return info.get_normalized_dict()["CommonPlayerInfo"][0]

def get_player_stats(player_id: int) -> dict | None:
    """
    Fetch per-game season averages for a player from the NBA API.
    Tries seasons 2024-25, 2023-24, 2022-23 in order.
    Returns the first season with non-zero PTS, or None if unavailable.
    """
    for season in ["2024-25", "2023-24", "2022-23"]:
        try:
            dash = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(
                player_id=player_id, season=season, per_mode_detailed="PerGame"
            )
            rows = dash.get_normalized_dict().get("OverallPlayerDashboard", [])
            if rows and rows[0].get("PTS", 0):
                rows[0]["_season"] = season
                return rows[0]
        except Exception:
            continue
    return None

def format_card(info: dict, stats: dict | None, fun_fact: str) -> str:
    """
    Format a player card as a Markdown string for Telegram.
    Includes profile info, season averages (if available), and a fun fact.
    """
    name    = info.get("DISPLAY_FIRST_LAST", "Unknown")
    team    = info.get("TEAM_NAME") or "—"
    pos     = info.get("POSITION") or "—"
    jersey  = info.get("JERSEY") or "—"
    country = info.get("COUNTRY") or "—"
    height  = info.get("HEIGHT") or "—"
    weight  = info.get("WEIGHT") or "—"
    exp     = info.get("SEASON_EXP", "—")

    card = (
        f"🏀 *{name}*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🏢 Team: *{team}*\n"
        f"📍 Position: *{pos}*\n"
        f"👕 Jersey: *#{jersey}*\n"
        f"🌍 Country: *{country}*\n"
        f"📏 Height: *{height}* | ⚖️ Weight: *{weight} lbs*\n"
        f"📅 Experience: *{exp} years*\n"
    )
    if stats:
        pts = round(stats.get("PTS", 0), 1)
        ast = round(stats.get("AST", 0), 1)
        reb = round(stats.get("REB", 0), 1)
        stl = round(stats.get("STL", 0), 1)
        blk = round(stats.get("BLK", 0), 1)
        fg  = stats.get("FG_PCT", 0)
        fg3 = stats.get("FG3_PCT", 0)
        season_label = stats.get("_season", "2024-25")
        card += (
            f"\n📊 *{season_label} Season Averages*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🔥 PTS: *{pts}* | 🎯 AST: *{ast}* | 💪 REB: *{reb}*\n"
            f"🛡 STL: *{stl}* | 🚫 BLK: *{blk}*\n"
            f"🎯 FG%: *{round(fg*100,1)}%* | 3P%: *{round(fg3*100,1)}%*\n"
        )
    else:
        card += "\n📊 _No stats available for this season_\n"

    card += f"\n⚡ *Fun Fact:* _{fun_fact}_"
    return card

async def send_player_card(update, player: dict, info: dict, stats: dict | None):
    """
    Send a player card to the user with their photo.
    Falls back to text-only if the photo URL is unavailable.
    """
    fact  = FUN_FACTS.get(player["full_name"].lower(), FUN_FACTS["default"])
    text  = format_card(info, stats, fact)
    photo = get_photo_url(player["id"])
    try:
        await update.message.reply_photo(photo=photo, caption=text, parse_mode="Markdown")
    except Exception:
        await update.message.reply_text(text, parse_mode="Markdown")

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    text = (
        "👋 *Welcome to NBA Player Card Bot!*\n\n"
        "Commands:\n"
        "🔍 `/player LeBron James` — get player card\n"
        "🎲 `/random` — random famous player\n"
        "🏆 `/top` — top 5 scorers this season\n"
        "⚔️ `/compare LeBron James vs Stephen Curry` — compare 2 players\n\n"
        "_Just type a player name after the command._"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def player_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    name = " ".join(ctx.args)
    if not name:
        await update.message.reply_text("Usage: `/player LeBron James`", parse_mode="Markdown")
        return
    msg = await update.message.reply_text("🔍 Searching...")
    player = find_player(name)
    if not player:
        await msg.edit_text(f"❌ Player *{name}* not found.", parse_mode="Markdown")
        return
    try:
        info  = get_player_info(player["id"])
        stats = get_player_stats(player["id"])
        await msg.delete()
        await send_player_card(update, player, info, stats)
    except Exception as e:
        log.error(e)
        await msg.edit_text("❌ Error fetching player data. Try again.")

async def random_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    msg = await update.message.reply_text("🎲 Getting a random player...")
    name   = random.choice(FAMOUS_PLAYERS)
    player = find_player(name)
    if not player:
        await msg.edit_text("❌ Something went wrong. Try again.")
        return
    try:
        info  = get_player_info(player["id"])
        stats = get_player_stats(player["id"])
        await msg.delete()
        await send_player_card(update, player, info, stats)
    except Exception as e:
        log.error(e)
        await msg.edit_text("❌ Error fetching player data. Try again.")

async def top_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    msg = await update.message.reply_text("🏆 Loading top scorers...")
    try:
        leaders = leagueleaders.LeagueLeaders(
            season="2024-25",
            stat_category_abbreviation="PTS",
            per_mode48="PerGame"
        )
        rows = leaders.get_normalized_dict()["LeagueLeaders"][:5]
        text = "🏆 *Top 5 Scorers — 2024-25 Season*\n━━━━━━━━━━━━━━━━\n"
        medals = ["🥇","🥈","🥉","4️⃣","5️⃣"]
        for i, r in enumerate(rows):
            text += f"{medals[i]} *{r['PLAYER']}* ({r['TEAM']}) — *{round(r['PTS'],1)} PPG*\n"
        await msg.delete()
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        log.error(e)
        try:
            await msg.edit_text("❌ Could not load top scorers. Try again.")
        except Exception:
            await update.message.reply_text("❌ Could not load top scorers. Try again.")

async def compare_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    raw = " ".join(ctx.args)
    if " vs " not in raw.lower():
        await update.message.reply_text(
            "Usage: `/compare LeBron James vs Stephen Curry`", parse_mode="Markdown")
        return
    parts = re.split(r"(?i) vs ", raw)
    name1, name2 = parts[0].strip(), parts[1].strip()
    msg = await update.message.reply_text("⚔️ Comparing players...")
    p1 = find_player(name1)
    p2 = find_player(name2)
    if not p1 or not p2:
        await msg.edit_text("❌ Could not find one or both players.")
        return
    try:
        s1 = get_player_stats(p1["id"])
        s2 = get_player_stats(p2["id"])

        def val(s, key):
            return round(s.get(key, 0), 1) if s else 0

        def row(label, key, emoji):
            v1, v2 = val(s1, key), val(s2, key)
            w1 = " ✅" if v1 > v2 else ""
            w2 = " ✅" if v2 > v1 else ""
            return f"{emoji} {label}: *{v1}*{w1} | *{v2}*{w2}\n"

        n1 = p1["full_name"]
        n2 = p2["full_name"]
        text = (
            f"⚔️ *{n1}* vs *{n2}*\n"
            f"━━━━━━━━━━━━━━━━\n"
            + row("PTS", "PTS", "🔥")
            + row("AST", "AST", "🎯")
            + row("REB", "REB", "💪")
            + row("STL", "STL", "🛡")
            + row("BLK", "BLK", "🚫")
        )
        await msg.delete()
        await update.message.reply_media_group(media=[
            InputMediaPhoto(media=get_photo_url(p1["id"]), caption=f"🏀 {n1}"),
            InputMediaPhoto(media=get_photo_url(p2["id"]), caption=f"🏀 {n2}"),
        ])
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        log.error(e)
        await msg.edit_text("❌ Error comparing players. Try again.")

async def unknown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text("❓ Unknown command. Type /start to see all commands.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("player",  player_cmd))
    app.add_handler(CommandHandler("random",  random_cmd))
    app.add_handler(CommandHandler("top",     top_cmd))
    app.add_handler(CommandHandler("compare", compare_cmd))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))
    print("🏀 NBA Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()