"""
Tech News API with REST Endpoints for Dashboard/App Integration
FastAPI server with endpoints for news scraping, scheduling, and post management
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import schedule
import json
import sqlite3
from threading import Thread
import uvicorn

# Data Models
class NewsArticle(BaseModel):
    id: Optional[int] = None
    title: str
    url: str
    source: str
    summary: str
    interest_score: float
    scraped_at: Optional[str] = None

class SocialPost(BaseModel):
    id: Optional[int] = None
    content: str
    platform: str
    status: str  # pending, posted, failed
    scheduled_for: str
    created_at: Optional[str] = None
    posted_at: Optional[str] = None

class ScheduleConfig(BaseModel):
    days: List[str]  # ["monday", "thursday", "saturday"]
    time: str  # "09:00"
    enabled: bool

# Database Manager
class DatabaseManager:
    def __init__(self, db_name="tech_news.db"):
        # Check if running on Render with disk (path variable or check existence)
        # Using a fixed path for Render disk mount if available
        render_disk_path = "/var/data/tech_news.db"
        if os.path.exists("/var/data"):
             self.db_name = render_disk_path
        else:
             self.db_name = db_name
        self.init_db()
    
    def init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS articles
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     title TEXT,
                     url TEXT,
                     source TEXT,
                     summary TEXT,
                     interest_score REAL,
                     scraped_at TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS posts
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     content TEXT,
                     platform TEXT,
                     status TEXT,
                     scheduled_for TEXT,
                     created_at TEXT,
                     posted_at TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS schedule_config
                    (id INTEGER PRIMARY KEY,
                     days TEXT,
                     time TEXT,
                     enabled INTEGER)''')
        
        # Insert default schedule if not exists
        c.execute("SELECT COUNT(*) FROM schedule_config")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO schedule_config VALUES (1, ?, '09:00', 1)",
                     (json.dumps(["monday", "thursday", "saturday"]),))
        
        conn.commit()
        conn.close()
    
    def save_articles(self, articles: List[NewsArticle]):
        """Save scraped articles to database"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        for article in articles:
            c.execute('''INSERT INTO articles 
                        (title, url, source, summary, interest_score, scraped_at)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (article.title, article.url, article.source, 
                      article.summary, article.interest_score, 
                      datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_articles(self, limit=50):
        """Get recent articles"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("SELECT * FROM articles ORDER BY scraped_at DESC LIMIT ?", (limit,))
        articles = c.fetchall()
        conn.close()
        return articles
    
    def save_post(self, post: SocialPost):
        """Save social media post"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('''INSERT INTO posts 
                    (content, platform, status, scheduled_for, created_at)
                    VALUES (?, ?, ?, ?, ?)''',
                 (post.content, post.platform, post.status, 
                  post.scheduled_for, datetime.now().isoformat()))
        conn.commit()
        post_id = c.lastrowid
        conn.close()
        return post_id
    
    def get_posts(self, status=None):
        """Get posts, optionally filtered by status"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        if status:
            c.execute("SELECT * FROM posts WHERE status=? ORDER BY created_at DESC", (status,))
        else:
            c.execute("SELECT * FROM posts ORDER BY created_at DESC")
        posts = c.fetchall()
        conn.close()
        return posts
    
    def update_post_status(self, post_id: int, status: str):
        """Update post status"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        posted_at = datetime.now().isoformat() if status == "posted" else None
        c.execute("UPDATE posts SET status=?, posted_at=? WHERE id=?",
                 (status, posted_at, post_id))
        conn.commit()
        conn.close()
    
    def get_schedule(self):
        """Get current schedule configuration"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("SELECT days, time, enabled FROM schedule_config WHERE id=1")
        result = c.fetchone()
        conn.close()
        return result
    
    def update_schedule(self, days: List[str], time: str, enabled: bool):
        """Update schedule configuration"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("UPDATE schedule_config SET days=?, time=?, enabled=? WHERE id=1",
                 (json.dumps(days), time, 1 if enabled else 0))
        conn.commit()
        conn.close()

# News Scraper
class TechNewsScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def scrape_hacker_news(self) -> List[NewsArticle]:
        """Scrape top stories from Hacker News"""
        articles = []
        try:
            r = requests.get('https://news.ycombinator.com/', headers=self.headers, timeout=10)
            soup = BeautifulSoup(r.content, 'html.parser')
            
            stories = soup.find_all('tr', class_='athing')[:30]
            
            for story in stories:
                title_elem = story.find('span', class_='titleline')
                if title_elem and title_elem.find('a'):
                    title = title_elem.find('a').text
                    url = title_elem.find('a')['href']
                    
                    score_row = story.find_next_sibling('tr')
                    score = 0
                    if score_row:
                        score_elem = score_row.find('span', class_='score')
                        if score_elem:
                            score = int(score_elem.text.split()[0])
                    
                    articles.append(NewsArticle(
                        title=title,
                        url=url if url.startswith('http') else f'https://news.ycombinator.com/{url}',
                        source='Hacker News',
                        summary=title,
                        interest_score=score / 10,
                        scraped_at=datetime.now().isoformat()
                    ))
        except Exception as e:
            print(f"Error scraping: {e}")
        
        return articles
    
    def rank_articles(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Rank articles by interest score"""
        tech_keywords = [
            'ai', 'artificial intelligence', 'machine learning', 'chatgpt', 'openai',
            'startup', 'funding', 'security', 'breach', 'vulnerability',
            'apple', 'google', 'microsoft', 'meta', 'amazon', 'tesla',
            'blockchain', 'cryptocurrency', 'quantum', 'robotics',
            'breakthrough', 'innovation', 'launch', 'release'
        ]
        
        for article in articles:
            title_lower = article.title.lower()
            keyword_boost = sum(2 for kw in tech_keywords if kw in title_lower)
            article.interest_score += keyword_boost
        
        return sorted(articles, key=lambda x: x.interest_score, reverse=True)

# FastAPI App
app = FastAPI(title="Tech News API", version="1.0.0")

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
db = DatabaseManager()
scraper = TechNewsScraper()

# API Endpoints

@app.get("/")
def root():
    """API info"""
    return {
        "name": "Tech News API",
        "version": "1.0.0",
        "endpoints": {
            "GET /articles": "Get all articles",
            "GET /articles/top": "Get top 10 articles",
            "POST /scrape": "Trigger news scraping",
            "GET /posts": "Get all posts",
            "POST /posts": "Create new post",
            "PUT /posts/{id}/status": "Update post status",
            "GET /schedule": "Get schedule config",
            "PUT /schedule": "Update schedule config",
            "GET /stats": "Get statistics"
        }
    }

@app.get("/articles")
def get_articles(limit: int = 50):
    """Get recent articles"""
    articles = db.get_articles(limit)
    return {
        "count": len(articles),
        "articles": [
            {
                "id": a[0],
                "title": a[1],
                "url": a[2],
                "source": a[3],
                "summary": a[4],
                "interest_score": a[5],
                "scraped_at": a[6]
            }
            for a in articles
        ]
    }

@app.get("/articles/top")
def get_top_articles(limit: int = 10):
    """Get top ranked articles"""
    articles = db.get_articles(100)
    sorted_articles = sorted(articles, key=lambda x: x[5], reverse=True)[:limit]
    return {
        "count": len(sorted_articles),
        "articles": [
            {
                "id": a[0],
                "title": a[1],
                "url": a[2],
                "source": a[3],
                "summary": a[4],
                "interest_score": a[5],
                "scraped_at": a[6]
            }
            for a in sorted_articles
        ]
    }

@app.post("/scrape")
def scrape_news(background_tasks: BackgroundTasks):
    """Trigger news scraping"""
    def scrape_task():
        articles = scraper.scrape_hacker_news()
        ranked = scraper.rank_articles(articles)
        db.save_articles(ranked[:50])
    
    background_tasks.add_task(scrape_task)
    return {"message": "Scraping started", "status": "processing"}

@app.get("/posts")
def get_posts(status: Optional[str] = None):
    """Get all posts or filter by status"""
    posts = db.get_posts(status)
    return {
        "count": len(posts),
        "posts": [
            {
                "id": p[0],
                "content": p[1],
                "platform": p[2],
                "status": p[3],
                "scheduled_for": p[4],
                "created_at": p[5],
                "posted_at": p[6]
            }
            for p in posts
        ]
    }

@app.post("/posts")
def create_post(post: SocialPost):
    """Create a new social media post"""
    post_id = db.save_post(post)
    return {"message": "Post created", "post_id": post_id}

@app.put("/posts/{post_id}/status")
def update_post_status(post_id: int, status: str):
    """Update post status (pending, posted, failed)"""
    if status not in ["pending", "posted", "failed"]:
        raise HTTPException(400, "Invalid status")
    
    db.update_post_status(post_id, status)
    return {"message": "Status updated", "post_id": post_id, "status": status}

@app.get("/posts/generate")
def generate_post_content():
    """Generate post content from top articles"""
    articles = db.get_articles(100)
    sorted_articles = sorted(articles, key=lambda x: x[5], reverse=True)[:10]
    
    date_str = datetime.now().strftime("%B %d, %Y")
    content = f"🚀 Top 10 Tech News - {date_str}\n\n"
    
    emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
    for i, a in enumerate(sorted_articles, 1):
        emoji = emojis.get(i, f"{i}️⃣")
        content += f"{emoji} {a[1]}\n"
        if len(a[2]) < 100:
            content += f"🔗 {a[2]}\n"
        content += "\n"
    
    content += "#TechNews #Technology #Innovation #AI #Startups"
    
    return {"content": content, "article_count": len(sorted_articles)}

@app.get("/schedule")
def get_schedule():
    """Get current schedule configuration"""
    schedule_data = db.get_schedule()
    return {
        "days": json.loads(schedule_data[0]),
        "time": schedule_data[1],
        "enabled": bool(schedule_data[2])
    }

@app.put("/schedule")
def update_schedule(config: ScheduleConfig):
    """Update schedule configuration"""
    db.update_schedule(config.days, config.time, config.enabled)
    return {"message": "Schedule updated", "config": config}

@app.get("/stats")
def get_statistics():
    """Get system statistics"""
    articles = db.get_articles(1000)
    posts = db.get_posts()
    
    return {
        "total_articles": len(articles),
        "total_posts": len(posts),
        "pending_posts": len([p for p in posts if p[3] == "pending"]),
        "posted_posts": len([p for p in posts if p[3] == "posted"]),
        "failed_posts": len([p for p in posts if p[3] == "failed"]),
        "last_scrape": articles[0][6] if articles else None
    }

if __name__ == "__main__":
    print("🚀 Starting Tech News API Server...")
    print("📊 Dashboard: http://localhost:8000/docs")
    print("🔗 API: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)