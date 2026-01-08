# Project Requirements & Specifications

## Overview
This project is an **Automated Tech News Scraper and Social Media Poster**. 
It runs on a schedule to gather high-interest tech news and publish them to professional social networks.

## Functional Requirements

### 1. Data Collection (Scraping)
- **Source**: Hacker News (https://news.ycombinator.com/)
- **Target**: Top stories (First 30 items)
- **Data Points**: 
  - Title
  - URL
  - Score/Points
  - Source Name

### 2. Data Processing & Ranking
- **Filtering**: Boost importance of articles containing key tech terms:
  - AI/ML (ChatGPT, OpenAI, etc.)
  - Big Tech (Apple, Google, etc.)
  - Startups & Funding
  - Security & Crypto
- **Ranking Algorithm**: 
  - Base HN Score (normalized)
  - +2.0 boost for every matching keyword
- **Selection**: Top 10 articles based on final calculated score.

### 3. Content Generation
- **Format**:
  - Header: "🚀 Top 10 Tech News - {Date}"
  - Body: List of 10 articles with ranking emojis (🥇, 🥈, 🥉, 4️⃣...)
  - Links: Included if URL length < 100 chars
  - Footer: Hash tags (#TechNews #AI etc.)

### 4. Integration (Social Media)
- **LinkedIn**:
  - Uses v2 API (`ugcPosts`)
  - Posts as Person (requires `LINKEDIN_PERSON_ID`)
- **Instagram**:
  - Requires Business Account
  - Uses Facebook Graph API (Placeholder implementation in current code)

### 5. Scheduling
- **Frequency**: Monday, Thursday, Saturday
- **Time**: 09:00 AM (System Time)

## Technical Requirements

### Dependencies
- Python 3.8+
- `requests` (HTTP Client)
- `beautifulsoup4` (HTML Parsing)
- `schedule` (Job Scheduling)

### Environment Variables
The following environment variables must be set for deployment:
- `INSTAGRAM_ACCESS_TOKEN`: For authorization with Facebook Graph API.
- `LINKEDIN_ACCESS_TOKEN`: For authorization with LinkedIn API.
- `LINKEDIN_PERSON_ID`: The URN ID of the LinkedIn profile to post to.

## Project Structure
- `main.py`: Entry point and core logic.
- `requirements/`: Dependency definitions (base, dev, prod).
