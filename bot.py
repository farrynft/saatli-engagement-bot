from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import re
import logging
from datetime import datetime, time as dt_time
import asyncio

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Config
TOKEN = "7958058721:AAEXx4Zw3RYj_7Bnr_eMfUWcsjlxYbsfRBk"
ADMIN_ID = 1004037545
GROUP_ID = -1002158416026
TOPIC_ID = 16848
RULES_CHANNEL = "https://t.me/zaxengage/12/26852"

# 3 SEANS
SESSIONS = [
    {'name': 'Sabah', 'start': dt_time(10, 0), 'end': dt_time(12, 0)},
    {'name': 'Öğle', 'start': dt_time(14, 0), 'end': dt_time(15, 0)},
    {'name': 'Akşam', 'start': dt_time(21, 0), 'end': dt_time(22, 0)}
]

session_data = {
    'Sabah': {'links': [], 'users': set(), 'date': None},
    'Öğle': {'links': [], 'users': set(), 'date': None},
    'Akşam': {'links': [], 'users': set(), 'date': None}
}

all_time_links = set()

DAILY_STATS = {
    'links_shared': 0,
    'rejected_duplicate': 0,
    'rejected_session_limit': 0,
    'rejected_closed': 0,
    'date': datetime.now().date()
}

RULES_TEXT = """
📚 Check rules / Kuralları kontrol et:
{rules_channel}
"""

def get_current_session():
    """Şu anki seans hangisi?"""
    now = datetime.now().time()
    
    for session in SESSIONS:
        if session['start'] <= now <= session['end']:
            return session['name']
    
    return None

def reset_session_data(session_name):
    """Seans verilerini sıfırla"""
    session_data[session_name] = {
        'links': [],
        'users': set(),
        'date': datetime.now().date()
    }
    logger.info(f"Seans verileri sıfırlandı: {session_name}")

def reset_daily_stats():
    """Günlük istatistikleri sıfırla"""
    global DAILY_STATS
    DAILY_STATS = {
        'links_shared': 0,
        'rejected_duplicate': 0,
        'rejected_session_limit': 0,
        'rejected_closed': 0,
        'date': datetime.now().date()
    }

async def send_session_summary(context: ContextTypes.DEFAULT_TYPE, session_name: str):
    """Seans bitiminde özet gönder"""
    
    session = session_data[session_name]
    
    if not session['links']:
        logger.info(f"{session_name} seansında paylaşılan link yok")
        reset_session_data(session_name)
        return
    
    # 1. ÖNCE LİNKLERİ GÖNDER (Sadece linkler)
    summary = ""
    for link_data in session['links']:
        summary += f"{link_data['link']}\n"
    
    try:
        await context.bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=TOPIC_ID,
            text=summary,
            disable_web_page_preview=True
        )
        logger.info(f"{session_name} link özeti gönderildi: {len(session['links'])} link")
    except Exception as e:
        logger.error(f"Link özeti gönderilemedi: {e}")
    
    # 2. SONRA KURALLARI GÖNDER
    try:
        await context.bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=TOPIC_ID,
            text=RULES_TEXT.format(rules_channel=RULES_CHANNEL),
            disable_web_page_preview=True
        )
        logger.info(f"{session_name} kurallar mesajı gönderildi")
    except Exception as e:
        logger.error(f"Kurallar gönderilemedi: {e}")
    
    reset_session_data(session_name)

async def send_daily_report(context: ContextTypes.DEFAULT_TYPE):
    """Admin'e günlük rapor gönder"""
    
    report = f"""
📊 GÜNLÜK RAPOR (SAATLİ MOD)
━━━━━━━━━━━━━━━━━━━━

📅 Tarih: {DAILY_STATS['date'].strftime('%d.%m.%Y')}

📈 İSTATİSTİKLER:
   ✅ Paylaşılan link: {DAILY_STATS['links_shared']}
   ❌ Duplicate reddedilen: {DAILY_STATS['rejected_duplicate']}
   ❌ Seans limiti: {DAILY_STATS['rejected_session_limit']}
   ⏰ Kapalı saatte: {DAILY_STATS['rejected_closed']}

━━━━━━━━━━━━━━━━━━━━
⏰ Rapor zamanı: {datetime.now().strftime('%H:%M')}
"""
    
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=report
    )
    
    logger.info("Günlük rapor admin'e gönderildi")
    reset_daily_stats()

async def schedule_session_tasks(application: Application):
    """Seans görevlerini planla"""
    
    while True:
        now = datetime.now()
        next_event = None
        next_event_type = None
        
        for session in SESSIONS:
            end_datetime = now.replace(
                hour=session['end'].hour,
                minute=session['end'].minute,
                second=0,
                microsecond=0
            )
            
            if now < end_datetime:
                if next_event is None or end_datetime < next_event:
                    next_event = end_datetime
                    next_event_type = ('end', session['name'])
        
        if next_event is None:
            from datetime import timedelta
            tomorrow = now + timedelta(days=1)
            first_session = SESSIONS[0]
            next_event = tomorrow.replace(
                hour=first_session['end'].hour,
                minute=first_session['end'].minute,
                second=0,
                microsecond=0
            )
            next_event_type = ('end', first_session['name'])
        
        wait_seconds = (next_event - now).total_seconds()
        
        logger.info(f"Sonraki event: {next_event_type[1]} sonu - {next_event.strftime('%d.%m.%Y %H:%M')}")
        
        await asyncio.sleep(wait_seconds)
        
        event_type, session_name = next_event_type
        
        if event_type == 'end':
            logger.info(f"{session_name} seansı bitti, özet gönderiliyor...")
            await send_session_summary(application, session_name)
