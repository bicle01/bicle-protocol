# BICLE v0.1 — The Genesis Feed

Experimental decentralized feed protocol.
Like Bitcoin for truth.

## Features
- Immutable blockchain of verified news
- Genesis Block: The Guardian 05/Nov/2025
- Telegram Bot Node interface
- Auto-mining and manual curation
- Only Tech categories in RSS news sources 

## Run
1. Copy `.env.example` → `.env`
2. Add your `TELEGRAM_TOKEN` and `CHANNEL_ID`
3. Run: `python bicle.py`

Note: The bot uses the `JobQueue` feature from `python-telegram-bot` for scheduled auto-mining jobs.
To enable JobQueue support, install the package with the `job-queue` extra:

```powershell
python -m pip install "python-telegram-bot[job-queue]"
```

If you prefer to install from `requirements.txt` first, run:

```powershell
python -m pip install -r .\requirements.txt
python -m pip install "python-telegram-bot[job-queue]"
```
Remember when adding your bot to the Telegram channel, to give permissions to send messages.

## Read '.env.example'
There, it explains how your 'node configuration' should be.
You should just create a Telegram bot for yourself and understand how the concept and the Bicle protocol work.

## Commands
`/mine`, `/verify`, `/submit`, `/export`, etc.

## How This Works

### 1. Information as Blocks
Just like Bitcoin records **transactions**, Bicle records **information**.

Each “block” contains up to **5 news items**, each hashed individually using **SHA-256** (`iHash`).

These are combined into a **blockHash**, linking each block to the previous one — forming the **blockchain of news**.

### 2. Mining Information
Unlike Bitcoin, Bicle does not mine coins — it mines **truth**.

- Every 5 minutes (auto mode) or manually (`/mine`), the 'node' collects **public RSS feeds** and **community submissions**.
- It validates, hashes, and stores the items in a new block.
- Each block is linked to the previous one with its `blockHash`, ensuring continuity and proof of integrity.

### 3. Proof of Information
Every news item gets a unique **fingerprint** (`iHash`):

This allows anyone to:
- Verify if an article existed.
- Detect if it was ever changed or deleted.
- Export the entire blockchain (`/export`) for public audit.

### 4. Decentralization Path
v0.1 is the **transitional phase** — still using centralized RSS sources.  
Future versions will introduce:

**P2P relay** (via NOSTR)  
**Community validation**  
**Reputation and trust scores**  
**Independent journalist nodes**  

Each node will contribute to the **collective verification of truth**, forming a distributed network of information.


### 5. Running Your Own 'Node'

```bash
git clone https://github.com/bicle01/bicle-protocol
cd bicle-protocol
pip install -r requirements.txt



#The first block (Block #0) is embedded in the code:

#> “The Guardian 05/Nov/2025 — On the brink of a financial crisis for AIs in companies.”

#This parallels Bitcoin’s historic message:
#> “The Times 03/Jan/2009 — Chancellor on brink of second bailout for banks.”

#The Bicle Genesis Block marks the **birth of decentralized information** —  
#immutable, transparent, and symbolically resistant to manipulation.

## License
MIT — Open for forks and independent nodes.


