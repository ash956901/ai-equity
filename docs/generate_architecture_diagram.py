#!/usr/bin/env python3
"""
Enterprise Architecture Diagram — AI Equity Research Platform
Generates: AGENT_SYSTEM_API_ETL_OVERALL_SYSTEM_ARCHITECTURE_AGENTS_ORCHESTRATION_LIST_OF_TOOLS.png
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Polygon
import matplotlib.patheffects as pe
from datetime import date
import os

# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT PATH
# ─────────────────────────────────────────────────────────────────────────────
OUTPUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "AGENT_SYSTEM_API_ETL_OVERALL_SYSTEM_ARCHITECTURE_AGENTS_ORCHESTRATION_LIST_OF_TOOLS.png"
)

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL STYLE
# ─────────────────────────────────────────────────────────────────────────────
BG = '#060B18'

# Layer color dicts: f=fill, b=border, h=header-accent, t=text
C = {
    'src':  dict(f='#150800', b='#FF6B35', h='#FF6B35', t='#FF8C5A'),
    'etl':  dict(f='#0D0025', b='#7C3AED', h='#7C3AED', t='#A78BFA'),
    'db':   dict(f='#001810', b='#059669', h='#059669', t='#34D399'),
    'ai':   dict(f='#000C2A', b='#2563EB', h='#2563EB', t='#60A5FA'),
    'llm':  dict(f='#250015', b='#DB2777', h='#DB2777', t='#F472B6'),
    'api':  dict(f='#120C00', b='#D97706', h='#D97706', t='#FCD34D'),
    'fe':   dict(f='#001520', b='#0EA5E9', h='#0EA5E9', t='#38BDF8'),
    'cel':  dict(f='#002800', b='#22C55E', h='#22C55E', t='#86EFAC'),
    'tool': dict(f='#150F00', b='#EAB308', h='#EAB308', t='#FDE047'),
    'mem':  dict(f='#150015', b='#8B5CF6', h='#8B5CF6', t='#C4B5FD'),
    'iris': dict(f='#051530', b='#60A5FA', h='#3B82F6', t='#FFFFFF'),
}

# ─────────────────────────────────────────────────────────────────────────────
# FIGURE SETUP  (coordinate space: x∈[0,100], y∈[0,100])
# ─────────────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(56, 36), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.set_aspect('auto')
ax.axis('off')
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

# Subtle dot-grid background
import numpy as _np
gx, gy = _np.meshgrid(_np.arange(2, 100, 3.5), _np.arange(2, 100, 3.5))
ax.scatter(gx.ravel(), gy.ravel(), s=0.6, c='#1A2A4A', alpha=0.5, zorder=0)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def rbox(x, y, w, h, fc, ec, lw=1.5, r=0.4, alpha=1.0, z=2):
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle=f"round,pad=0,rounding_size={r}",
                       fc=fc, ec=ec, lw=lw, alpha=alpha, zorder=z)
    ax.add_patch(p)
    return p


def zone_draw(x, y, w, h, c, lw=2.0, z=1):
    """Filled zone with glowing border."""
    rbox(x, y, w, h, c['f'], c['b'], lw=lw, r=0.8, alpha=0.35, z=z)
    rbox(x, y, w, h, 'none', c['b'], lw=lw, r=0.8, alpha=0.8, z=z + 1)


def txt(x, y, s, col, fs, bold=False, ha='center', va='center', z=10, glow=False):
    w = 'bold' if bold else 'normal'
    obj = ax.text(x, y, s, color=col, fontsize=fs, fontweight=w,
                  ha=ha, va=va, zorder=z, fontfamily='DejaVu Sans')
    if glow:
        obj.set_path_effects([pe.withStroke(linewidth=3, foreground='#000010')])
    return obj


def badge(cx, cy, r, s, bg, fg='white', fs=6):
    ax.add_patch(Circle((cx, cy), r, fc=bg, ec='white', lw=0.8, zorder=8))
    txt(cx, cy, s, fg, fs, bold=True, z=9)


def layer_hdr(x, y, w, h, title, c, icon='▸', z=5):
    rbox(x, y, w, h, c['h'], 'none', lw=0, r=0.3, alpha=0.18, z=z)
    lbl = f'{icon}  {title}'
    obj = txt(x + w / 2, y + h / 2, lbl, c['h'], 10, bold=True, z=z + 1)
    obj.set_path_effects([pe.withStroke(linewidth=2, foreground='#000000')])


def arr(x0, y0, x1, y1, col, ls='-', rad=0.0, lw=1.5, z=6, lbl='', lbl_offset=(0, 0)):
    props = dict(arrowstyle='->', color=col, lw=lw,
                 connectionstyle=f'arc3,rad={rad}', linestyle=ls, mutation_scale=14)
    ax.annotate('', xy=(x1, y1), xytext=(x0, y0), arrowprops=props, zorder=z)
    if lbl:
        mx = (x0 + x1) / 2 + lbl_offset[0]
        my = (y0 + y1) / 2 + lbl_offset[1]
        bg_box = dict(fc=BG, ec='none', pad=0.4, alpha=0.9)
        txt(mx, my, lbl, col, 4.8, z=z + 1)


def bidir(x0, y0, x1, y1, col, ls='-', rad=0.0, lw=1.5, z=6, lbl=''):
    props = dict(arrowstyle='<->', color=col, lw=lw,
                 connectionstyle=f'arc3,rad={rad}', linestyle=ls, mutation_scale=14)
    ax.annotate('', xy=(x1, y1), xytext=(x0, y0), arrowprops=props, zorder=z)
    if lbl:
        txt((x0 + x1) / 2, (y0 + y1) / 2, lbl, col, 4.5, z=z + 1)


def comp_box(x, y, w, h, title, lines, c, abbr=None, abbr_col=None, z=3):
    """Component box with optional badge, title, divider, bullet lines."""
    rbox(x, y, w, h, c['f'], c['b'], lw=1.2, r=0.45, alpha=0.97, z=z)
    # Header strip
    rbox(x, y + h - 1.8, w, 1.8, abbr_col or c['h'], 'none', lw=0, r=0.45, alpha=0.22, z=z + 1)
    if abbr and abbr_col:
        badge(x + 1.2, y + h - 0.9, 0.6, abbr, abbr_col, fs=5)
        txt(x + 2.5, y + h - 0.9, title, c['t'], 7, bold=True, ha='left', z=z + 1)
    else:
        txt(x + w / 2, y + h - 0.9, title, c['t'], 7, bold=True, z=z + 1)
    ax.plot([x + 0.3, x + w - 0.3], [y + h - 1.85, y + h - 1.85],
            color=c['b'], lw=0.6, alpha=0.5, zorder=z + 1)
    slot_h = (h - 2.2) / max(len(lines), 1)
    for i, ln in enumerate(lines):
        ly = y + h - 2.2 - (i + 0.5) * slot_h
        txt(x + 0.5, ly, '· ' + ln, '#BBBBBB', 5.5, ha='left', z=z + 1)


# ─────────────────────────────────────────────────────────────────────────────
# ══ LAYER 0: HEADER BANNER  y=[96.5, 100] ══
# ─────────────────────────────────────────────────────────────────────────────

rbox(0, 96.5, 100, 3.5, '#0B1640', '#2563EB', lw=2.5, r=0.0, alpha=1.0, z=2)
# Left accent stripe
rbox(0, 96.5, 0.7, 3.5, '#FF6B35', 'none', lw=0, r=0.0, alpha=1.0, z=3)
# Platform logo box
rbox(1.0, 96.9, 14, 2.9, '#152A5A', '#3B82F6', lw=1.2, r=0.3, alpha=1.0, z=3)
badge(3.2, 98.35, 1.0, 'AI', '#2563EB', fs=7)
txt(5.5, 98.6, 'EQUITY RESEARCH', '#FFFFFF', 8, bold=True, ha='left', z=4)
txt(5.5, 97.7, 'PLATFORM  v1.0', '#60A5FA', 6.5, ha='left', z=4)

# Main title
obj = txt(50, 98.6, 'SYSTEM ARCHITECTURE', '#FFFFFF', 24, bold=True, z=4)
obj.set_path_effects([pe.withStroke(linewidth=4, foreground='#000030')])
txt(50, 97.3,
    'ETL Pipeline  ·  Data Storage  ·  AI Agents (IRIS + 8 Specialists)  ·  LLM Providers  ·  FastAPI Backend  ·  React Frontend',
    '#60A5FA', 8, z=4)

# Right meta
txt(91, 98.8, f'Generated: {date.today().strftime("%Y-%m-%d")}', '#8B9DC3', 6.5, ha='left', z=4)
txt(91, 98.0, 'Indian Equity Markets', '#8B9DC3', 6.5, ha='left', z=4)
txt(91, 97.2, 'NSE / BSE  ·  Production Grade', '#8B9DC3', 6.5, ha='left', z=4)


# ─────────────────────────────────────────────────────────────────────────────
# ══ LAYER 1: EXTERNAL DATA SOURCES  y=[83, 96.2] ══
# ─────────────────────────────────────────────────────────────────────────────

zone_draw(1, 83, 98, 13.2, C['src'], lw=2.5, z=1)
layer_hdr(1, 93.5, 98, 2.3, 'EXTERNAL DATA SOURCES & APIs', C['src'], icon='◈', z=5)

SOURCES = [
    ('NSE',  'NSE India\nExchange',        '#FF6B00', 'Corporate Filings\nDaily crawl'),
    ('BSE',  'BSE India\nExchange',        '#0066CC', 'Corporate Filings\nTwice daily'),
    ('FMP',  'Financial\nModeling Prep',   '#00BCD4', '30+ endpoints\nFS · Ratios · News'),
    ('FRED', 'Fed Reserve\nEconomic Data', '#3F51B5', 'Macro indicators\nUSA & Global'),
    ('NEWS', 'NewsAPI\nGlobal News',       '#E53935', 'Real-time articles\nEvery 6 hours'),
    ('NDio', 'NewsData.io\nNews Feed',     '#43A047', 'Multi-region\nEvery 6 hours'),
    ('AV',   'Alpha Vantage\nCommodities', '#0288D1', 'WTI · Brent · Gold\nNatGas · Coal'),
    ('GDLT', 'GDELT\nGeo-Events',         '#546E7A', 'Conflict & events\nFree public API'),
    ('UPST', 'Upstox\nBroker API',        '#7B1FA2', 'Live quotes\nNSE / BSE'),
    ('KITE', 'Kite / Zerodha\nConnect',   '#00695C', 'Portfolio data\nLive market feed'),
]

n = len(SOURCES)
sw = 8.6
sg = (98 - n * sw) / (n + 1)
sy0, sh = 84.2, 7.8

for i, (abbr, name, col, detail) in enumerate(SOURCES):
    sx = 1 + sg * (i + 1) + i * sw
    rbox(sx, sy0, sw, sh, '#080E1C', col, lw=2.0, r=0.5, alpha=0.97, z=3)
    badge(sx + sw / 2, sy0 + sh - 1.7, 1.0, abbr, col, fs=5.5)
    txt(sx + sw / 2, sy0 + sh - 3.5, name, col, 6, bold=True, z=4)
    txt(sx + sw / 2, sy0 + 2.1, detail, '#AAAAAA', 5.5, z=4)
    rbox(sx + 0.4, sy0 + 0.3, sw - 0.8, 0.9, col, 'none', lw=0, r=0.2, alpha=0.25, z=4)
    txt(sx + sw / 2, sy0 + 0.75, 'REST API', col, 4.5, bold=True, z=5)


# ─────────────────────────────────────────────────────────────────────────────
# ══ LAYER 2: ETL PIPELINE  y=[69, 83] ══
# ─────────────────────────────────────────────────────────────────────────────

zone_draw(1, 69, 98, 14, C['etl'], lw=2.5, z=1)
layer_hdr(1, 80.5, 98, 2.2, 'ETL PIPELINE  —  Celery 5.4 Workers + Beat Scheduler (9 cron tasks, Asia/Kolkata TZ)', C['etl'], icon='⟳', z=5)

# Celery Beat control box (center-top)
rbox(34, 79.3, 32, 2.8, '#003A00', '#22C55E', lw=2.0, r=0.4, alpha=0.97, z=4)
badge(36.5, 80.7, 0.85, 'CB', '#22C55E', fs=6)
txt(50, 80.7, 'CELERY BEAT SCHEDULER  ·  Redis Broker  ·  TTL 3600s', '#86EFAC', 7.5, bold=True, z=5)

# ── Group A: Document Ingestion (left) ──
zone_draw(1.5, 69.5, 30, 9.5, C['etl'], lw=1.2, z=2)
txt(16.5, 78.3, '▸ DOCUMENT INGESTION', C['etl']['t'], 7.5, bold=True, z=5)

DOC_STEPS = [
    ('NSE Filing Crawler',  'crawler_nse.py · 9:30 AM IST daily'),
    ('BSE Filing Crawler',  'crawler_bse.py · 9 AM + 3 PM IST'),
    ('IR Page Crawler',     'crawler_ir.py · 2 AM Sat (weekly)'),
    ('Document Processor',  'PyMuPDF + pdfplumber (PDF/DOCX/PPTX)'),
    ('Semantic Chunker',    'Section-aware splitting with overlap'),
    ('Embedding Generator', 'nomic-embed-text · 768-dim vectors'),
    ('LLM Enricher',        'Gemini 2.5 Flash · summaries + red flags'),
]
sh2 = 1.12
for i, (name, detail) in enumerate(DOC_STEPS):
    sy = 77.2 - i * sh2
    rbox(2.2, sy - 0.9, 28.8, sh2 - 0.1, '#1A0040', '#7C3AED', lw=0.8, r=0.2, alpha=0.9, z=3)
    txt(3.0, sy - 0.42, f'→  {name}', '#A78BFA', 6, bold=True, ha='left', z=4)
    txt(30.5, sy - 0.42, detail, '#777777', 5, ha='right', z=4)

# ── Group B: Market Data Sync (center) ──
zone_draw(34.5, 69.5, 31, 9.5, C['etl'], lw=1.2, z=2)
txt(50, 78.3, '▸ MARKET DATA SYNC', C['etl']['t'], 7.5, bold=True, z=5)

MKT_STEPS = [
    ('Stock Universe Sync',  '6:00 AM IST · NSE + BSE · all tickers'),
    ('Company Enrichment',   '7:00 AM IST · batch_size=100 companies'),
    ('Financial Data AM',    '8:00 AM IST · income + balance + cashflow'),
    ('Financial Data PM',    '6:00 PM IST · ratios + market-close data'),
    ('Commodity Prices',     'Alpha Vantage + Yahoo Finance fallback'),
    ('ETL Run Logger',       'etl_runs table · status + timing metrics'),
]
for i, (name, detail) in enumerate(MKT_STEPS):
    sy = 77.2 - i * sh2
    rbox(35.2, sy - 0.9, 29.5, sh2 - 0.1, '#1A0040', '#7C3AED', lw=0.8, r=0.2, alpha=0.9, z=3)
    txt(36.0, sy - 0.42, f'→  {name}', '#A78BFA', 6, bold=True, ha='left', z=4)
    txt(64.0, sy - 0.42, detail, '#777777', 5, ha='right', z=4)

# ── Group C: News & Events (right) ──
zone_draw(68.5, 69.5, 30, 9.5, C['etl'], lw=1.2, z=2)
txt(83.5, 78.3, '▸ NEWS & EVENTS', C['etl']['t'], 7.5, bold=True, z=5)

NEWS_STEPS = [
    ('News Aggregator',       'NewsAPI + NewsData.io · every 6 hours'),
    ('FinBERT Sentiment',     'Hugging Face sentiment classification'),
    ('DistilBERT Classifier', 'Zero-shot topic & impact scoring'),
    ('Geopolitical Tracker',  'GDELT Cloud · 7 active event types'),
    ('Portfolio News Corr.',  'every 30 min · holding-level alerts'),
    ('Signal Engine',         'Market signal detection & alert trigger'),
]
for i, (name, detail) in enumerate(NEWS_STEPS):
    sy = 77.2 - i * sh2
    rbox(69.2, sy - 0.9, 28.5, sh2 - 0.1, '#1A0040', '#7C3AED', lw=0.8, r=0.2, alpha=0.9, z=3)
    txt(70.0, sy - 0.42, f'→  {name}', '#A78BFA', 6, bold=True, ha='left', z=4)
    txt(97.0, sy - 0.42, detail, '#777777', 5, ha='right', z=4)

# Celery Beat → group headers (dashed schedule arrows)
arr(50, 79.3, 16.5, 78.5, '#22C55E', ls='--', rad=-0.12, lw=1.3, lbl='schedules')
arr(50, 79.3, 50.0, 78.5, '#22C55E', ls='--', rad=0.0,   lw=1.3)
arr(50, 79.3, 83.5, 78.5, '#22C55E', ls='--', rad=0.12,  lw=1.3)


# ─────────────────────────────────────────────────────────────────────────────
# ══ LAYER 3: DATA STORAGE  y=[57, 69] ══
# ─────────────────────────────────────────────────────────────────────────────

zone_draw(1, 57, 98, 12, C['db'], lw=2.5, z=1)
layer_hdr(1, 66.5, 98, 2.2, 'DATA STORAGE LAYER', C['db'], icon='◈', z=5)

DBS = [
    dict(abbr='PG', name='PostgreSQL 15', port=':5432', col='#336791',
         sub=['32 ORM tables · SQLAlchemy 2.0',
              'companies · filings · portfolios',
              'chat_sessions · chat_messages',
              'causal_chains · simulator_stats',
              'Alembic migrations · pool_size=10']),
    dict(abbr='QD', name='Qdrant', port=':6333', col='#6B35FF',
         sub=['Vector semantic search engine',
              'company_filings collection',
              'user_uploads collection',
              '768-dim nomic-embed-text',
              'Cosine similarity · ANN index']),
    dict(abbr='RD', name='Redis 7', port=':6379', col='#DC382D',
         sub=['Analysis cache · 1hr TTL',
              'SHA-256 keyed responses',
              'Celery broker + result backend',
              'chat / compare / causal cache',
              'AOF persistence enabled']),
    dict(abbr='MG', name='MongoDB', port=':27017', col='#47A248',
         sub=['Optional (motor async client)',
              'Netflix-style user profiles',
              'Multi-profile JSON storage',
              'MONGODB_URI env var required',
              'Lazy init · graceful fallback']),
]

dbw = 23.5
dbh = 8.5
dbg = (98 - 4 * dbw) / 5
for i, db in enumerate(DBS):
    dx = 1 + dbg * (i + 1) + i * dbw
    dy = 57.8
    rbox(dx, dy, dbw, dbh, '#040D1A', db['col'], lw=2.2, r=0.5, alpha=0.98, z=3)
    rbox(dx, dy + dbh - 2.3, dbw, 2.3, db['col'], 'none', lw=0, r=0.5, alpha=0.22, z=4)
    badge(dx + 1.5, dy + dbh - 1.15, 0.85, db['abbr'], db['col'], fs=6.5)
    txt(dx + 3.2, dy + dbh - 1.15, db['name'], db['col'], 8.5, bold=True, ha='left', z=5)
    txt(dx + dbw - 0.4, dy + dbh - 1.15, db['port'], '#666666', 6, ha='right', z=5)
    ax.plot([dx + 0.3, dx + dbw - 0.3], [dy + dbh - 2.4, dy + dbh - 2.4],
            color=db['col'], lw=0.8, alpha=0.5, zorder=4)
    start = dy + dbh - 3.1
    for j, ln in enumerate(db['sub']):
        txt(dx + 0.5, start - j * 1.15, '•  ' + ln, '#CCCCCC', 6, ha='left', z=4)


# ─────────────────────────────────────────────────────────────────────────────
# ══ LAYER 4: AI AGENT SYSTEM  y=[22, 57] ══
# ─────────────────────────────────────────────────────────────────────────────

zone_draw(1, 22, 98, 35, C['ai'], lw=2.5, z=1)
layer_hdr(1, 54, 98, 2.7,
          'AI AGENT SYSTEM  —  DeepAgents 0.4  +  LangGraph 0.3  ·  IRIS Orchestrator  +  8 Specialist Agents  +  11 Tools',
          C['ai'], icon='⬡', z=5)

# ── LLM Providers (right column) ──
zone_draw(80.5, 29, 18.5, 24.5, C['llm'], lw=1.5, z=2)
txt(89.75, 53.1, 'LLM PROVIDERS', C['llm']['t'], 7.5, bold=True, z=5)

LLMS = [
    ('AN', 'Anthropic Claude',  'claude-sonnet-4-6',      '#FF6B35'),
    ('GQ', 'Groq',              'llama-3.3-70b-versatile', '#22C55E'),
    ('OA', 'OpenAI',            'gpt-4o-mini',             '#74AA9C'),
    ('DS', 'DeepSeek',          'deepseek-chat',            '#1E6ECA'),
    ('OL', 'Ollama (Local)',    'deepseek-r1:8b',           '#888888'),
]
llmh = 4.0
for i, (ab, name, model, col) in enumerate(LLMS):
    ly = 48.5 - i * (llmh + 0.35)
    rbox(81.0, ly, 17.5, llmh, '#050515', col, lw=1.5, r=0.4, alpha=0.97, z=3)
    badge(82.8, ly + llmh / 2, 0.8, ab, col, fs=6)
    txt(84.2, ly + llmh - 1.0, name, col, 6.5, bold=True, ha='left', z=4)
    txt(84.2, ly + 1.1, model, '#777777', 5.5, ha='left', z=4)

arr(80.5, 44.0, 61.5, 51.0, '#DB2777', ls='--', rad=-0.1, lw=1.8, lbl='inference')

# Gemini note (used in ETL enrichment, not main agent LLM)
rbox(81.0, 27.2, 17.5, 1.5, '#0A0015', '#DB2777', lw=0.8, r=0.3, alpha=0.9, z=3)
txt(89.75, 27.95, '+ Gemini 2.5 Flash (ETL enrichment)', '#F472B6', 5, z=4)

# ── IRIS Orchestrator ──
ix, iy, iw, ih = 31, 48.5, 29, 7.0
rbox(ix, iy, iw, ih, '#040F28', '#60A5FA', lw=3.0, r=0.8, alpha=1.0, z=4)
rbox(ix + 0.25, iy + 0.25, iw - 0.5, ih - 0.5, 'none', '#2563EB', lw=1.2, r=0.6, alpha=0.6, z=5)
# Glow fill overlay
rbox(ix + 0.5, iy + 0.5, iw - 1, ih - 1, '#0A1F50', 'none', lw=0, r=0.5, alpha=0.5, z=4)

obj = txt(ix + iw / 2, iy + ih - 1.7, 'IRIS  ORCHESTRATOR', '#FFFFFF', 13, bold=True, z=6, glow=True)
txt(ix + iw / 2, iy + 3.7, 'DeepAgents + LangGraph StateGraph', '#60A5FA', 7.5, z=6)
txt(ix + iw / 2, iy + 2.4, 'Context routing  ·  Session management  ·  Tool dispatch', '#888888', 6, z=6)
txt(ix + iw / 2, iy + 1.2, 'MemorySaver checkpointer  ·  StoreBackend  ·  CompositeBackend', '#888888', 6, z=6)

# Diamond decision node at base of IRIS
dpts = [[ix + iw / 2, iy - 0.2],
        [ix + iw / 2 + 2.0, iy + 1.6],
        [ix + iw / 2, iy + 3.4],
        [ix + iw / 2 - 2.0, iy + 1.6]]
# Note: This overlaps the IRIS box — skip it, IRIS box IS the orchestrator

# ── Specialist Sub-Agents ──
AGENTS = [
    ('CO', 'Company\nAnalyst',    '#3B82F6',
     ['Fundamentals & ratios', 'LLM-powered enrichment', 'Red flag detection', 'Balance sheet deep-dive']),
    ('CM', 'Comparison\nAnalyst', '#8B5CF6',
     ['Peer benchmarking', 'Side-by-side metrics', 'Competitive moat analysis', 'Sector ranking']),
    ('PM', 'Portfolio\nManager',  '#06B6D4',
     ['Beta computation (0.33–1.18)', 'Sharpe ratio', 'HHI diversification score', 'Volatility & drawdown']),
    ('NA', 'News\nAnalyst',       '#F59E0B',
     ['Sentiment scoring', 'Filing impact alerts', 'Market signal detection', 'Portfolio news corr.']),
    ('DR', 'Document\nReader',    '#10B981',
     ['RAG over Qdrant filings', 'PDF / DOCX analysis', 'Semantic passage retrieval', 'Citation extraction']),
    ('TE', 'Thematic\nExplorer',  '#EC4899',
     ['Macro theme discovery', 'Sector / ESG / AI themes', 'Vector similarity search', 'company_filings RAG']),
    ('CD', 'Causal\nDetective',   '#EF4444',
     ['11 causal chains', '19 sector exposures', 'Domino-effect prediction', 'Event → Commodity → Sector']),
    ('PA', 'Performance\nAnalyst','#14B8A6',
     ['Return attribution', 'Backtesting logic', 'P&L breakdown', 'Benchmark comparison']),
]

aw, ah = 18.0, 9.5
cols = 4
agap = (79 - 1 - cols * aw) / (cols + 1)

for i, (ab, name, col, details) in enumerate(AGENTS):
    c = i % 4
    r = i // 4
    ax_pos = 1 + agap * (c + 1) + c * aw
    ay_pos = 37.5 - r * (ah + 1.5)

    rbox(ax_pos, ay_pos, aw, ah, '#040D1A', col, lw=1.8, r=0.5, alpha=0.97, z=3)
    rbox(ax_pos, ay_pos + ah - 2.5, aw, 2.5, col, 'none', lw=0, r=0.5, alpha=0.2, z=4)
    badge(ax_pos + 1.5, ay_pos + ah - 1.25, 0.85, ab, col, fs=6)
    txt(ax_pos + 3.1, ay_pos + ah - 1.25, name, col, 7.5, bold=True, ha='left', z=5)
    ax.plot([ax_pos + 0.4, ax_pos + aw - 0.4],
            [ay_pos + ah - 2.65, ay_pos + ah - 2.65],
            color=col, lw=0.7, alpha=0.5, zorder=4)
    slot = (ah - 3.0) / 4
    for j, d in enumerate(details):
        txt(ax_pos + 0.6, ay_pos + ah - 3.3 - j * slot, '· ' + d, '#CCCCCC', 5.5, ha='left', z=4)

# IRIS → Row 0 agents (fan-out)
iris_bx = ix + iw / 2
iris_by = iy
for ci in range(4):
    ax_c = 1 + agap * (ci + 1) + ci * aw + aw / 2
    ay_t = 37.5 + ah
    arr(iris_bx, iris_by, ax_c, ay_t, '#2563EB', lw=1.1, rad=0.04 * (ci - 1.5))

# Row 0 → Row 1 agents
for ci in range(4):
    ax_c = 1 + agap * (ci + 1) + ci * aw + aw / 2
    arr(ax_c, 37.5, ax_c, 27.0 + ah, '#2563EB', ls='--', lw=0.9, rad=0.0)

# ── Agent Tools Bar ──
tz, th = 22.5, 3.6
zone_draw(1, tz, 79, th, C['tool'], lw=1.2, z=2)
txt(40.5, tz + th - 0.65, '▸ AGENT TOOLS  (11 tools)', C['tool']['t'], 7, bold=True, z=5)

TOOLS = [
    ('resolve_company',    '#EAB308'),
    ('internet_search\n(Tavily)', '#FF6B35'),
    ('vector_search',      '#6B35FF'),
    ('document_analysis',  '#059669'),
    ('financial_metrics',  '#2563EB'),
    ('portfolio_metrics',  '#06B6D4'),
    ('news_retrieval',     '#F59E0B'),
    ('causal_tools',       '#EF4444'),
    ('performance_tools',  '#14B8A6'),
    ('web_scraper',        '#8B5CF6'),
    ('signal_engine',      '#EC4899'),
]
tw = (79 - 1.8) / len(TOOLS) - 0.35
for i, (tn, tc) in enumerate(TOOLS):
    tx = 1.5 + i * (tw + 0.4)
    rbox(tx, tz + 0.45, tw, th - 1.1, '#050E00', tc, lw=1.1, r=0.35, alpha=0.97, z=3)
    txt(tx + tw / 2, tz + th / 2 - 0.15, tn, tc, 5.0, bold=True, z=4)

# Row 1 agents → Tools
for ci in range(4):
    ax_c = 1 + agap * (ci + 1) + ci * aw + aw / 2
    arr(ax_c, 27.0, ax_c, tz + th, '#EAB308', ls='--', lw=0.9)

# Memory & Observability
rbox(80.5, tz, 18.5, th, '#100015', '#8B5CF6', lw=1.2, r=0.4, alpha=0.97, z=3)
txt(89.75, tz + th - 0.75, 'MEMORY + OBSERVABILITY', '#C4B5FD', 6, bold=True, z=4)
txt(89.75, tz + 2.0, 'StoreBackend · MemorySaver', '#888888', 5.5, z=4)
txt(89.75, tz + 1.1, 'observability.py · LangGraph traces', '#888888', 5.5, z=4)


# ─────────────────────────────────────────────────────────────────────────────
# ══ LAYER 5: FastAPI BACKEND  y=[11, 22] ══
# ─────────────────────────────────────────────────────────────────────────────

zone_draw(1, 11, 98, 11, C['api'], lw=2.5, z=1)
layer_hdr(1, 19.5, 98, 2.2,
          'FastAPI BACKEND  —  Port 8001  ·  60+ REST Endpoints  ·  SQLAlchemy 2.0  ·  Pydantic 2.10  ·  Uvicorn',
          C['api'], icon='⬡', z=5)

ROUTES = [
    ('/chat',       'POST',     '#FF6B35'),
    ('/upload',     'POST',     '#FB923C'),
    ('/companies',  'GET',      '#2563EB'),
    ('/portfolios', 'GET/POST', '#06B6D4'),
    ('/news',       'GET',      '#F59E0B'),
    ('/compare',    'POST',     '#8B5CF6'),
    ('/alerts',     'CRUD',     '#EF4444'),
    ('/watchlists', 'CRUD',     '#10B981'),
    ('/timeline',   'GET',      '#14B8A6'),
    ('/screens',    'GET/POST', '#EC4899'),
    ('/users',      'GET/PUT',  '#6366F1'),
    ('/profiles',   'CRUD',     '#A855F7'),
    ('/causal',     'GET',      '#DC2626'),
    ('/simulator',  'CRUD',     '#059669'),
]

rw = (98 - 2.0) / len(ROUTES) - 0.45
rh = 6.5
ry0 = 11.8

for i, (route, method, rc) in enumerate(ROUTES):
    rx = 1.5 + i * (rw + 0.45)
    rbox(rx, ry0, rw, rh, '#0A0800', rc, lw=1.6, r=0.45, alpha=0.97, z=3)
    rbox(rx, ry0 + rh - 1.8, rw, 1.8, rc, 'none', lw=0, r=0.45, alpha=0.22, z=4)
    txt(rx + rw / 2, ry0 + rh - 0.9, route, rc, 7, bold=True, z=5)
    txt(rx + rw / 2, ry0 + 2.8, method, '#AAAAAA', 5.5, z=4)
    txt(rx + rw / 2, ry0 + 1.4, 'FastAPI\nRouter', '#555555', 4.5, z=4)

# Health & tech bar
rbox(1.5, 11.3, 18, 0.9, '#003300', '#22C55E', lw=0.8, r=0.2, alpha=0.9, z=3)
txt(10.5, 11.75, 'GET /health  ·  GET /api/v1/status', '#86EFAC', 5.5, z=4)
rbox(60, 11.3, 39, 0.9, '#120C00', '#D97706', lw=0.8, r=0.2, alpha=0.9, z=3)
txt(79.5, 11.75,
    'FastAPI 0.115  ·  Uvicorn  ·  Pydantic 2.10  ·  SQLAlchemy 2.0  ·  Alembic  ·  JWT (planned)  ·  CORS enabled',
    '#FCD34D', 5, z=4)


# ─────────────────────────────────────────────────────────────────────────────
# ══ LAYER 6: REACT FRONTEND  y=[0.4, 11] ══
# ─────────────────────────────────────────────────────────────────────────────

zone_draw(1, 0.4, 98, 10.6, C['fe'], lw=2.5, z=1)
layer_hdr(1, 9.2, 98, 1.6,
          'REACT FRONTEND  —  Port 5173  ·  React 19  ·  TypeScript 5.8  ·  Vite  ·  Tailwind CSS  ·  Recharts',
          C['fe'], icon='⬡', z=5)

VIEWS_R1 = [
    ('Dashboard',      '#0EA5E9'), ('Minerva Chat',   '#60A5FA'),
    ('Discovery',      '#38BDF8'), ('Compare',        '#7C3AED'),
    ('Portfolio',      '#06B6D4'), ('Domino Effect',  '#EF4444'),
    ('Company WS',     '#2563EB'), ('Money',          '#10B981'),
]
VIEWS_R2 = [
    ('Simulator',      '#F59E0B'), ('Filings',        '#8B5CF6'),
    ('Timeline',       '#14B8A6'), ('News',           '#EC4899'),
    ('Performance',    '#6366F1'), ('Profile',        '#A855F7'),
    ('Settings',       '#64748B'),
]

def draw_views(views, y0, h):
    vw = (98 - 1.5) / len(views) - 0.45
    for i, (nm, vc) in enumerate(views):
        vx = 1.5 + i * (vw + 0.45)
        rbox(vx, y0, vw, h, '#000D1A', vc, lw=1.5, r=0.4, alpha=0.97, z=3)
        rbox(vx, y0 + h - 1.0, vw, 1.0, vc, 'none', lw=0, r=0.4, alpha=0.22, z=4)
        txt(vx + vw / 2, y0 + h / 2 + 0.2, nm, vc, 6.5, bold=True, z=5)

draw_views(VIEWS_R1, 5.8, 3.1)
draw_views(VIEWS_R2, 2.2, 3.1)

# Tech stack strip
rbox(1.5, 0.5, 97, 1.2, '#001520', '#0EA5E9', lw=0.8, r=0.2, alpha=0.92, z=3)
txt(50, 1.1,
    'React 19.1  ·  TypeScript 5.8  ·  Vite  ·  Tailwind CSS  ·  Recharts 3.8  ·  Chart.js 4.5  ·  React-Markdown  ·  jsPDF 4.2  ·  Lucide Icons  ·  Vitest',
    '#38BDF8', 6, z=4)


# ─────────────────────────────────────────────────────────────────────────────
# INTER-LAYER ARROWS
# ─────────────────────────────────────────────────────────────────────────────

# -- External Sources → ETL Groups --
# NSE/BSE → Doc Ingestion
arr(7.3,  84.2, 7.3,  82.0,  '#FF6B00', lw=1.8, lbl='filings')
arr(16.0, 84.2, 16.0, 82.0,  '#0066CC', lw=1.8, lbl='filings')
# FMP/FRED → Market Data
arr(26.0, 84.2, 42.0, 82.0,  '#00BCD4', lw=1.5, rad=-0.1, lbl='financials')
arr(35.5, 84.2, 50.5, 82.0,  '#3F51B5', lw=1.5, rad=-0.05, lbl='macro')
# NewsAPI/NDio → News
arr(45.0, 84.2, 72.0, 82.0,  '#E53935', lw=1.5, rad=-0.1, lbl='headlines')
arr(54.5, 84.2, 80.0, 82.0,  '#43A047', lw=1.5, rad=-0.05, lbl='articles')
# AV → Market Data (commodities)
arr(63.5, 84.2, 55.0, 82.0,  '#0288D1', lw=1.5, rad=0.05, lbl='commodities')
# GDELT → News
arr(72.5, 84.2, 85.0, 82.0,  '#546E7A', lw=1.5, rad=0.08, lbl='geo events')
# Upstox/Kite → Market Data
arr(81.5, 84.2, 50.5, 82.0,  '#7B1FA2', lw=1.5, rad=0.12, lbl='live quotes')
arr(90.5, 84.2, 57.0, 82.0,  '#00695C', lw=1.5, rad=0.15, lbl='quotes')

# -- ETL → Data Storage --
arr(16.5, 69.5, 12.5, 66.3,  '#A78BFA', lw=1.8, lbl='vectors\n768-dim')    # Doc → Qdrant
arr(16.5, 69.5, 36.5, 66.3,  '#A78BFA', ls='--', rad=-0.1, lw=1.2, lbl='vectors')  # also Qdrant
arr(50.0, 69.5, 13.0, 66.3,  '#7C3AED', lw=1.5, rad=-0.15, lbl='companies\nfilings')  # MktData → PG
arr(50.0, 69.5, 50.0, 66.3,  '#7C3AED', lw=1.8, lbl='structured\ndata')    # MktData → center
arr(83.5, 69.5, 62.0, 66.3,  '#7C3AED', lw=1.5, rad=0.1,  lbl='news\ncache')  # News → Redis
arr(83.5, 69.5, 74.5, 66.3,  '#7C3AED', lw=1.5, rad=0.05, lbl='events\nprofiles')  # News → Mongo

# -- Data Storage ↔ Agent Tools --
bidir(12.5, 57.0, 12.5, 26.1, '#059669', ls='--', lw=1.4, lbl='SQL queries')
bidir(36.5, 57.0, 36.5, 26.1, '#6B35FF', ls='--', lw=1.4, lbl='vector search')
arr(62.0,  57.0, 62.0, 26.1,  '#DC382D', ls='--', lw=1.2, lbl='cache hit\n1hr TTL')

# -- AI Agent System → API Layer --
arr(35.0, 22.0, 35.0, 21.8,  '#2563EB', lw=2.2, lbl='streaming response')
arr(65.0, 22.0, 65.0, 21.8,  '#2563EB', lw=2.2)

# -- API → Frontend --
arr(40.0, 11.0, 40.0, 10.8,  '#D97706', lw=2.2, lbl='JSON / SSE')
arr(62.0, 11.0, 62.0, 10.8,  '#D97706', lw=2.2)


# ─────────────────────────────────────────────────────────────────────────────
# LEGEND
# ─────────────────────────────────────────────────────────────────────────────

lx, ly, lw2, lh2 = 1.5, 22.8, 16, 8.5
rbox(lx, ly, lw2, lh2, '#050D1A', '#334466', lw=1.2, r=0.4, alpha=0.97, z=10)
txt(lx + lw2 / 2, ly + lh2 - 0.65, 'LEGEND', '#FFFFFF', 7, bold=True, z=11)
ax.plot([lx + 0.4, lx + lw2 - 0.4], [ly + lh2 - 1.1, ly + lh2 - 1.1],
        color='#334466', lw=0.8, alpha=0.8, zorder=11)

LEGEND = [
    ('■  External Data Sources', '#FF6B35'),
    ('■  ETL Pipeline (Celery)', '#7C3AED'),
    ('■  Data Storage',          '#059669'),
    ('■  AI Agent System',       '#2563EB'),
    ('■  LLM Providers',         '#DB2777'),
    ('■  FastAPI Backend',       '#D97706'),
    ('■  React Frontend',        '#0EA5E9'),
]
for i, (ltxt, lc) in enumerate(LEGEND):
    txt(lx + 0.6, ly + lh2 - 1.85 - i * 0.93, ltxt, lc, 6, ha='left', z=11)

# Arrow type legend
ax.plot([lx + 0.6, lx + 3.5], [ly + 0.85, ly + 0.85], color='#FFFFFF', lw=1.5, zorder=11)
txt(lx + 4.5, ly + 0.85, '= Data flow', '#AAAAAA', 5, ha='left', z=11)
ax.plot([lx + 0.6, lx + 3.5], [ly + 0.35, ly + 0.35], color='#FFFFFF', lw=1.0, ls='--', zorder=11)
txt(lx + 4.5, ly + 0.35, '= Scheduled / cached', '#AAAAAA', 5, ha='left', z=11)


# ─────────────────────────────────────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────────────────────────────────────

plt.savefig(OUTPUT, dpi=100, bbox_inches='tight',
            facecolor=fig.get_facecolor(), edgecolor='none')
plt.close(fig)

sz = os.path.getsize(OUTPUT) / (1024 * 1024)
print(f"✓ Saved: {OUTPUT}")
print(f"  Size:  {sz:.1f} MB  |  5600 × 3600 px @ 100 DPI")
