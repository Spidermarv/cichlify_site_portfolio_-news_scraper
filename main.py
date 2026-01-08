"""
Automated Tech News Scraper and Social Media Poster
Scrapes tech news, ranks by interest, and posts to Instagram and LinkedIn
Schedule: Monday, Thursday, Saturday
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import schedule
import time
import json
from dataclasses import dataclass
from typing import List
import os

@dataclass
class NewsArticle:
    title: str
    url: str
    source: str
    summary: str
    interest_score: float

class TechNewsScraper:
    def __init__(self):
        self.sources = [
            'https://news.ycombinator.com/',
            'https://techcrunch.com/',
            'https://www.theverge.com/',
        ]
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
                    
                    # Get score for ranking
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
                        interest_score=score / 10
                    ))
        except Exception as e:
            print(f"Error scraping Hacker News: {e}")
        
        return articles
    
    def rank_articles(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Rank articles by interest score and filter for tech relevance"""
        # Keywords that indicate high-interest tech news
        tech_keywords = [
            'ai', 'artificial intelligence', 'machine learning', 'chatgpt', 'openai',
            'startup', 'funding', 'security', 'breach', 'vulnerability',
            'apple', 'google', 'microsoft', 'meta', 'amazon', 'tesla',
            'blockchain', 'cryptocurrency', 'quantum', 'robotics',
            'breakthrough', 'innovation', 'launch', 'release'
        ]
        
        for article in articles:
            title_lower = article.title.lower()
            # Boost score for relevant keywords
            keyword_boost = sum(2 for kw in tech_keywords if kw in title_lower)
            article.interest_score += keyword_boost
        
        # Sort by interest score and return top 10
        return sorted(articles, key=lambda x: x.interest_score, reverse=True)[:10]
    
    def get_top_news(self) -> List[NewsArticle]:
        """Get and rank top tech news"""
        all_articles = []
        all_articles.extend(self.scrape_hacker_news())
        
        return self.rank_articles(all_articles)

class SocialMediaPoster:
    def __init__(self, instagram_token=None, linkedin_token=None):
        self.instagram_token = instagram_token or os.getenv('INSTAGRAM_ACCESS_TOKEN')
        self.linkedin_token = linkedin_token or os.getenv('LINKEDIN_ACCESS_TOKEN')
    
    def create_post_content(self, articles: List[NewsArticle], date: str) -> str:
        """Create formatted post content"""
        post = f"🚀 Top 10 Tech News - {date}\n\n"
        
        for i, article in enumerate(articles, 1):
            emoji = self._get_emoji(i)
            post += f"{emoji} {article.title}\n"
            if len(article.url) < 100:
                post += f"🔗 {article.url}\n"
            post += "\n"
        
        post += "#TechNews #Technology #Innovation #AI #Startups #TechTrends"
        return post
    
    def _get_emoji(self, rank: int) -> str:
        """Get emoji for ranking"""
        emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
        return emojis.get(rank, f"{rank}️⃣")
    
    def post_to_instagram(self, content: str, image_path: str = None):
        """Post to Instagram (requires Facebook Graph API)"""
        if not self.instagram_token:
            print("Instagram token not configured")
            return
        
        # Instagram posting requires:
        # 1. Instagram Business Account
        # 2. Facebook Graph API access
        # 3. Image upload first, then create media container
        
        print(f"Would post to Instagram:\n{content[:200]}...")
        # Actual API call would go here
        # url = f"https://graph.facebook.com/v18.0/{instagram_account_id}/media"
        # Response handling...
    
    def post_to_linkedin(self, content: str):
        """Post to LinkedIn"""
        if not self.linkedin_token:
            print("LinkedIn token not configured")
            return
        
        # LinkedIn API posting
        url = "https://api.linkedin.com/v2/ugcPosts"
        headers = {
            'Authorization': f'Bearer {self.linkedin_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }
        
        payload = {
            "author": f"urn:li:person:{os.getenv('LINKEDIN_PERSON_ID')}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": content
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        print(f"Would post to LinkedIn:\n{content[:200]}...")
        # Uncomment to actually post:
        # response = requests.post(url, headers=headers, json=payload)
        # return response.json()

class NewsBot:
    def __init__(self):
        self.scraper = TechNewsScraper()
        self.poster = SocialMediaPoster()
        self.last_run = None
    
    def run_job(self):
        """Main job to scrape and post"""
        print(f"\n{'='*50}")
        print(f"Running job at {datetime.now()}")
        print(f"{'='*50}\n")
        
        # Get top news
        top_articles = self.scraper.get_top_news()
        
        if not top_articles:
            print("No articles found")
            return
        
        # Create post content
        date_str = datetime.now().strftime("%B %d, %Y")
        post_content = self.poster.create_post_content(top_articles, date_str)
        
        print("Top 10 Articles:")
        for i, article in enumerate(top_articles, 1):
            print(f"{i}. {article.title} (Score: {article.interest_score:.1f})")
        
        print(f"\n{'-'*50}")
        print("POST CONTENT:")
        print(f"{'-'*50}")
        print(post_content)
        print(f"{'-'*50}\n")
        
        # Post to social media
        self.poster.post_to_linkedin(post_content)
        self.poster.post_to_instagram(post_content)
        
        self.last_run = datetime.now()
        print(f"Job completed at {self.last_run}\n")
    
    def start_scheduler(self):
        """Start the scheduler for Monday, Thursday, Saturday"""
        # Schedule for 9 AM on specified days
        schedule.every().monday.at("09:00").do(self.run_job)
        schedule.every().thursday.at("09:00").do(self.run_job)
        schedule.every().saturday.at("09:00").do(self.run_job)
        
        print("🤖 Tech News Bot Started!")
        print("📅 Scheduled for: Monday, Thursday, Saturday at 9:00 AM")
        print("Press Ctrl+C to stop\n")
        
        # Run immediately for testing
        self.run_job()
        
        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    # Setup (you'll need to add your API tokens)
    # export INSTAGRAM_ACCESS_TOKEN="your_token"
    # export LINKEDIN_ACCESS_TOKEN="your_token"
    # export LINKEDIN_PERSON_ID="your_id"
    
    bot = NewsBot()
    bot.start_scheduler()