import asyncio
import feedparser
import json
import os
import hashlib
from datetime import datetime, timedelta, timezone
from io import BytesIO
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from dotenv import load_dotenv

load_dotenv()

# ==================== CONFIG ====================

TOKEN = os.getenv("TELEGRAM_TOKEN")

_raw_channel = os.getenv("CHANNEL_ID", "").strip()
if not _raw_channel:
    CHANNEL_ID = None
else:
    if _raw_channel.startswith("@"):
        CHANNEL_ID = _raw_channel
    else:
        try:
            CHANNEL_ID = int(_raw_channel)
        except ValueError:
            # fallback to raw string if it cannot be converted (rare)
            CHANNEL_ID = _raw_channel



RSS_FEEDS = {
    'tech': [
        {'name': 'Bitcoin Core', 'url': 'https://bitcoincore.org/en/releasesrss.xml'},
        {'name': 'Ars Technica', 'url': 'https://feeds.arstechnica.com/arstechnica/index'},
        {'name': 'TechCrunch', 'url': 'https://techcrunch.com/feed/'},
        {'name': 'The Verge', 'url': 'https://www.theverge.com/rss/index.xml'},
        {'name': 'Wired', 'url': 'https://www.wired.com/feed/category/technology/latest/rss'},
        {'name': 'Engadget', 'url': 'https://www.engadget.com/rss.xml'},
        {'name': 'CNET', 'url': 'https://www.cnet.com/rss/news/'},
        {'name': 'ZDNet', 'url': 'https://www.zdnet.com/news/rss.xml'},
        {'name': 'VentureBeat', 'url': 'https://venturebeat.com/feed/'},
        {'name': 'Mashable', 'url': 'https://mashable.com/feeds/rss/all'},
        {'name': 'Gizmodo', 'url': 'https://gizmodo.com/rss'},
        {'name': 'Tecnoblog', 'url': 'https://tecnoblog.net/feed'},
        {'name': 'CanalTech', 'url': 'https://feeds.feedburner.com/canaltech'},
        {'name': 'Brazil Journal', 'url': 'https://www.braziljournal.com/feed'},
        {'name': 'Silicon Canals', 'url': 'https://siliconcanals.com/feed'},
        {'name': 'Euractiv', 'url': 'https://www.euractiv.com/section/digital/feed/'},
        {'name': 'The European', 'url': 'https://the-european.eu/technology/feed/'},
        {'name': 'Tech in Asia', 'url': 'https://www.techinasia.com/feed'},
        {'name': 'The Diplomat', 'url': 'https://thediplomat.com/feed/'},
        {'name': 'Nikkei Asia', 'url': 'https://asia.nikkei.com/RSS/Technology'},
        {'name': 'iTnews Asia', 'url': 'https://www.itnews.asia/rss'},
        {'name': 'The Times', 'url': 'https://www.thetimes.co.uk/technology/rss'},
        {'name': 'The New York Times', 'url': 'https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml'},
        {'name': 'The Guardian', 'url': 'https://www.theguardian.com/technology/rss'},
        {'name': 'Stacker.news', 'url': 'https://stacker.news/~tech/rss'},
    ],
}


SENT_FILE = 'sent_news.json'
PENDING_FILE = 'pending.json'
BLOCKS_FILE = 'blocks.json'

# Global storage
sent_news = {}
pending = {}
blocks = [] 

# ==================== PERSISTENCE FUNCTIONS ====================

def load_json(path, default):
    """Load JSON safely"""
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load {path}: {e}")        
    return default

def save_json(path, data):
    """Save JSON safely"""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[ERROR] Failed to save {path}: {e}")

def init_storage():
    """Initialize storage files"""
    global sent_news, pending, blocks
    
    # Load sent news history (last 30 days)
    sent_news = load_json(SENT_FILE, {})
    cutoff = (datetime.now() - timedelta(days=30)).isoformat()
    sent_news = {k: v for k, v in sent_news.items() if v >= cutoff}

    # Load pending news
    pending = load_json(PENDING_FILE, {})
    
    # Load blockchain
    blocks = load_json(BLOCKS_FILE, [])

    # Save cleaned state
    save_json(SENT_FILE, sent_news)
    save_json(PENDING_FILE, pending)
    save_json(BLOCKS_FILE, blocks)
    
    # If no blocks exist, create a genesis block and persist it
    if not blocks:
        try:
            genesis = create_genesis_block()
            blocks.append(genesis)
            save_json(BLOCKS_FILE, blocks)
            print("[SYSTEM] Genesis Block initialized - The Guardian 05/Nov/2025")
        except Exception as e:
            print(f"[ERROR] Failed to create genesis block: {e}")

    print(f"[SYSTEM] Storage loaded: {len(sent_news)} news, {len(pending)} pending, {len(blocks)} blocks")

# ==================== CRYPTOGRAPHIC FUNCTIONS ====================

def create_genesis_block():
    title = "The Guardian 05/Nov/2025 - on the brink of a financial crisis for AIs in companies"
    link = "https://www.theguardian.com/business/2025/nov/05/global-stock-markets-fall-sharply-over-ai-bubble-fears"
    source = "The Guardian"
    published = "2025-11-05"
    ihash = hashlib.sha256((title + link + source + published).encode('utf-8')).hexdigest()

    genesis_block = {
        "block_number": 0,
        "timestamp": "2025-11-05T11:20:00Z",
        "news": [{
            "title": title,
            "link": link,
            "source": source,
            "published": published,
            "summary": "Global stock markets fall sharply amid fears of an AI-driven financial bubble collapse.",
            "iHash": ihash
        }],
        "blockhash": hashlib.sha256(ihash.encode('utf-8')).hexdigest(),
        "previous": None
    }
    return genesis_block


def create_iHash(title: str, link: str, source: str, published: str) -> str:
    """Create a unique hash for a news item (iHash)"""
    data = (title or "") + (link or "") + (source or "") + (published or "")
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def compute_block_hash(iHashes: list) -> str:
    """Compute block hash based on the iHashes of the news items"""
    sorted_hashes = sorted(iHashes)
    concat = "".join(sorted_hashes)
    return hashlib.sha256(concat.encode('utf-8')).hexdigest()

# ==================== BLOCKCHAIN FUNCTIONS ====================

def verify_chain() -> bool:
    """Verify blockchain integrity"""
    if len(blocks) <= 1:
        return True

    for i in range(1, len(blocks)):
        # Check if the previous hash matches
        if blocks[i]['previous'] != blocks[i-1]['blockhash']:
            print(f"[ERROR] Block #{blocks[i]['block_number']}: previous hash mismatch")
            return False

        # Check if the blockhash is correct
        recalculated = compute_block_hash([n['iHash'] for n in blocks[i]['news']])
        if blocks[i]['blockhash'] != recalculated:
            print(f"[ERROR] Block #{blocks[i]['block_number']}: invalid blockhash")
            return False

    return True


def get_stats() -> dict:
    """Return source statistics"""
    sources = {}
    for block in blocks:
        for news in block['news']:
            source = news['source']
            sources[source] = sources.get(source, 0) + 1
    return sources

# ==================== NEWS FUNCTIONS ====================

def fetch_rss_items(limits_per_feed=3) -> list:
    """Fetch news from all RSS feeds"""
    items = []

    for feed_info in RSS_FEEDS.get('tech', []):
        try:
            feed = feedparser.parse(feed_info['url'])
            # FIXED: correct slice
            for entry in feed.entries[:limits_per_feed]:
                link = entry.get('link', '').strip()
                title = entry.get('title', '').strip()
                published = entry.get('published', '') or entry.get('updated', '')
                summary = entry.get('summary', '') or entry.get('description', '')

                if not link:
                    continue
                
                items.append({
                    'title': title or link,
                    'link': link,
                    'source': feed_info['name'],
                    'published': published,
                    'summary': summary[:300] if summary else ''
                })
        except Exception as e:
            print(f"[ERROR] Failed to fetch RSS from {feed_info['name']}: {e}")
    
    return items

def format_block_message(block: dict) -> str:
    """Format a block for sending to Telegram"""
    header = f"[BLOCK #{block['block_number']}]\n"
    header += f"TIME: {block['timestamp']} UTC\n"
    header += f"NEWS: {len(block['news'])}\n"
    header += f"HASH: `{block['blockhash'][:16]}...`\n"
    if block.get('previous'):
        header += f"PREV: `{block['previous'][:16]}...`\n"
    header += "\n"
    
    lines = [header]
    
    for i, n in enumerate(block['news'], 1):
        lines.append(f"{i}. *{n['source']}* — {n['title'][:100]}")
        if n.get('link'):
            lines.append(f"   > {n['link']}")
        lines.append(f"   `iHash: {n['iHash'][:16]}...`\n")
    
    return "\n".join(lines)
 
def build_block_from_items(items: list, max_news=5) -> dict:
    """Create a new block from a list of news items"""
    selected = []
    iHashes = []

    for it in items:
        link = it['link']

        if link in sent_news:
            continue

    # Skip if already sent
        if link in sent_news:
            continue
        
    # Create iHash
        ih = create_iHash(it['title'], link, it['source'], it['published'])
        
    # Skip duplicates (same iHash)
        if ih in iHashes:
            continue
        
        selected.append({
            'title': it.get('title', '')[:280],
            'link': link,
            'source': it.get('source', ''),
            'published': it.get('published', ''),
            'summary': it.get('summary', '')[:300],
            'iHash': ih
        })
        iHashes.append(ih)
        
        if len(selected) >= max_news:
            break
    
    if not selected:
        return None
    
    # Calculate block number
    block_number = len(blocks) + 1
    # Use timezone-aware UTC timestamp
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    blockhash = compute_block_hash(iHashes)
    
    # Create block
    block = {
        'block_number': block_number,
        'timestamp': timestamp,
        'news': selected,
        'blockhash': blockhash,
        'previous': blocks[-1]['blockhash'] if blocks else None
    }
    
    # Update storage
    for n in selected:
        sent_news[n['link']] = timestamp
        if n['link'] in pending:
            del pending[n['link']]
    
    blocks.append(block)
    save_json(SENT_FILE, sent_news)
    save_json(PENDING_FILE, pending)
    save_json(BLOCKS_FILE, blocks)
    
    return block

# ==================== BOT COMMANDS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /start - Bot information"""
    msg = (
        "BICLE Node v0.1\n"
        "_The Decentralized Feed Protocol_\n\n"
        "Human curation + Verifiable information blocks\n\n"
        "*Core Commands:*\n"
        "• /submit <link> - Submit news\n"
        "• /mine - Mine new block\n"
        "• /block <n> - View block\n"
        "• /hash - View latest hash\n"
        "• /proof - View latest blocks\n"
        "• /verify - Verify blockchain\n"
        "• /export - Export blockchain\n"
        "• /stats - View statistics\n"
        "• /status - Node status\n\n"
        "[SYS] Auto-mining: " + ("ACTIVE" if CHANNEL_ID else "DISABLED")
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /submit - Submit a news link"""
    if not context.args:
        await update.message.reply_text("[ERROR] Usage: /submit <link>")
        return
    
    link = context.args[0].strip()
    user = update.effective_user.username or update.effective_user.first_name

    # Try to extract information from the link
    title = link
    source = "user-submission"
    published = ""
    
    try:
        parsed = feedparser.parse(link)
        if parsed and parsed.feed and parsed.entries:
            entry = parsed.entries[0]
            title = entry.get('title', title)
            published = entry.get('published', '') or entry.get('updated', '')
            source = parsed.feed.get('title', source)
    except Exception as e:
        print(f"[ERROR] Failed to parse link: {e}")

    # Create iHash
    ih = create_iHash(title, link, source, published)
    
    # Check duplicates
    if link in sent_news:
        await update.message.reply_text("[ERROR] News already broadcasted.")
        return
    
    if link in pending:
        await update.message.reply_text("[WARN] News already in pending queue.")
        return
    
    # Add to pending
    pending[link] = {
        'title': title,
        'link': link,
        'source': source,
        'published': published,
        'submitter': user,
        # Use timezone-aware UTC timestamp for submissions
        'added_at': datetime.now(timezone.utc).isoformat(),
        'iHash': ih
    }
    save_json(PENDING_FILE, pending)
    
    await update.message.reply_text(
        f"[SUCCESS] News submitted by {user}\n"
        f"Status: Added to pending queue\n"
        f"`iHash: {ih[:16]}...`",
        parse_mode=ParseMode.MARKDOWN
    )

async def mine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /mine - Mine a new block"""
    await update.message.reply_text("[SYSTEM] Mining block...")
    
    # Fetch RSS news
    rss_items = fetch_rss_items(limits_per_feed=3)
    candidates = []

    # Add pending submissions
    for link, p in pending.items():
        candidates.append({
            'title': p.get('title'),
            'link': link,
            'source': p.get('source'),
            'published': p.get('published'),
            'summary': ''
        })
    
    # Add RSS news
    for it in rss_items:
        if it['link'] not in sent_news and it['link'] not in pending:
            candidates.append(it)

    # Create block
    block = build_block_from_items(candidates, max_news=5)
    
    if not block:
        await update.message.reply_text("[ERROR] Insufficient new data for block mining.")
        return
    
    # Send to the user
    msg = format_block_message(block)
    await update.message.reply_text(
        "[SUCCESS] Block successfully mined\n\n" + msg,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )
    
    # Post to the channel if configured
    if CHANNEL_ID:
        try:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=msg,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"[ERROR] Channel broadcast failed: {e}")

async def block_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /block - View a specific block"""
    if not context.args:
        await update.message.reply_text("[ERROR] Usage: /block <number>")
        return
    
    try:
        n = int(context.args[0])
    except:
        await update.message.reply_text("[ERROR] Invalid block number.")
        return
    
    # Search block
    found = next((b for b in blocks if b['block_number'] == n), None)
    
    if not found:
        await update.message.reply_text(f"[ERROR] Block #{n} not found.")
        return
    
    msg = format_block_message(found)
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

async def hash_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /hash - View last hash"""
    if not blocks:
        await update.message.reply_text("[ERROR] No blocks mined yet.")
        return
    
    last = blocks[-1]
    await update.message.reply_text(
        f"[BLOCK INFO]\n\n"
        f"Number: #{last['block_number']}\n"
        f"`Hash: {last['blockhash']}`",
        parse_mode=ParseMode.MARKDOWN
    )

async def proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /proof - Show recent blocks (proof of work)"""
    if not blocks:
        await update.message.reply_text("[ERROR] No blocks mined yet.")
        return
    
    summary = []
    for b in blocks[-5:]:
        summary.append(
            f"[#{b['block_number']}] {b['timestamp']}\n"
            f"   NEWS: {len(b['news'])} | HASH: `{b['blockhash'][:16]}...`"
        )
    
    await update.message.reply_text(
        "[PROOF OF WORK]\n\nLast Blocks:\n\n" + "\n\n".join(summary),
        parse_mode=ParseMode.MARKDOWN
    )

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /verify - Verify blockchain integrity"""
    await update.message.reply_text("[SYSTEM] Verifying blockchain integrity...")
    
    if verify_chain():
        await update.message.reply_text(
            f"[VERIFIED] Blockchain integrity confirmed\n\n"
            f"Status: All {len(blocks)} blocks valid\n"
            f"Hash verification: PASSED",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            "[CRITICAL] Blockchain integrity compromised\n\n"
            "Details: One or more blocks show inconsistencies",
            parse_mode=ParseMode.MARKDOWN
        )

async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /export - Export blockchain for audit"""
    if not blocks:
        await update.message.reply_text("[ERROR] No blocks to export.")
        return
    
    await update.message.reply_text("[SYSTEM] Generating export file...")
    
    try:
        # Create complete JSON 
        data = json.dumps(blocks, indent=2, ensure_ascii=False)
        file = BytesIO(data.encode('utf-8'))
        file.name = f"bicle_blockchain_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        await update.message.reply_document(
            document=file,
            filename=file.name,
            caption=f"[EXPORT] Blockchain exported: {len(blocks)} blocks"
        )
    except Exception as e:
        await update.message.reply_text(f"[ERROR] Export failed: {e}")

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /stats - Show source statistics"""
    if not blocks:
        await update.message.reply_text("[ERROR] No blocks mined yet.")
        return
    
    sources = get_stats()
    
    # Order by quantity
    sorted_sources = sorted(sources.items(), key=lambda x: x[1], reverse=True)
    
    msg = "[STATISTICS] Source Distribution\n\n"
    
    for source, count in sorted_sources[:10]:  # Top 10
        msg += f"| {source}: {count} entries\n"
    
    total = sum(sources.values())
    msg += f"\n[TOTAL] {total} entries across {len(blocks)} blocks"
    
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /status - Node status"""
    integrity = "VERIFIED" if verify_chain() else "COMPROMISED"
    
    msg = (
        "[NODE STATUS]\n\n"
        f"HISTORY: {len(sent_news)} entries\n"
        f"PENDING: {len(pending)} submissions\n"
        f"BLOCKS: {len(blocks)} mined\n"
        f"INTEGRITY: {integrity}\n"
        f"CHANNEL: {'CONFIGURED' if CHANNEL_ID else 'NOT CONFIGURED'}\n"
        f"AUTO-MINE: {'ACTIVE (5min)' if CHANNEL_ID else 'MANUAL'}"
    )
    
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== AUTOMATIC MINING ====================

async def auto_mine_job(context: ContextTypes.DEFAULT_TYPE):
    """Automatic mining job (runs every 5 minutes if CHANNEL_ID configured)"""
    print("[AUTO-MINE] Initializing mining cycle...")
    
    # Fetch news
    rss_items = fetch_rss_items(limits_per_feed=2)
    candidates = []

    # Add pending
    for link, p in pending.items():
        candidates.append({
            'title': p['title'],
            'link': link,
            'source': p['source'],
            'published': p['published'],
            'summary': ''
        })

    # Add RSS
    for it in rss_items:
        if it['link'] not in sent_news and it['link'] not in pending:
            candidates.append(it)

    # Create block
    block = build_block_from_items(candidates, max_news=5)
    
    if block and CHANNEL_ID:
        msg = format_block_message(block)
        try:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=msg,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            print(f"[SUCCESS] Block #{block['block_number']} broadcasted to channel")
        except Exception as e:
            print(f"[ERROR] Broadcast failed: {e}")
    else:
        print("[INFO] No new data for mining")

# ==================== MAIN ====================

def main():
    """Main function"""
    print("\n[INIT] BICLE Node v0.1 - The Decentralized Feed Protocol")
    print("=" * 60)
    
    print("[DEBUG]")
    print(f"TOKEN loaded: {TOKEN[:20] if TOKEN else 'NONE'}...")
    print(f"CHANNEL_ID: {CHANNEL_ID}")


    # Initialize storage
    init_storage()
    
    # Create application
    app = Application.builder().token(TOKEN).build()

    # Register commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("submit", submit))
    app.add_handler(CommandHandler("mine", mine))
    app.add_handler(CommandHandler("block", block_cmd))
    app.add_handler(CommandHandler("hash", hash_cmd))
    app.add_handler(CommandHandler("proof", proof))
    app.add_handler(CommandHandler("verify", verify))
    app.add_handler(CommandHandler("export", export))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("status", status))

    # Configure auto-mining if CHANNEL_ID is set
    if CHANNEL_ID:
        jobq = app.job_queue
        jobq.run_repeating(auto_mine_job, interval=300, first=60)
        print("[SYSTEM] Auto-mining: ACTIVE (interval: 5 minutes)")
    else:
        print("[SYSTEM] Auto-mining: DISABLED (manual mode)")

    print(f"[SYSTEM] Channel: {CHANNEL_ID if CHANNEL_ID else 'Not configured'}")
    print(f"[SYSTEM] Blockchain: {len(blocks)} blocks loaded")
    print("=" * 60)
    print("[SYSTEM] Node initialized. Press Ctrl+C to terminate.\n")

    # Start polling
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':

    main()
