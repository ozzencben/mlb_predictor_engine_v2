# MLB Predictor Engine - Platform Upgrade Roadmap

I've reviewed all your requests—from the new NRFI List View and Date Selector to the Result Tracking and Sportsbook filtering. To ensure we execute this flawlessly without breaking the current live system, I have categorized your requests into three distinct phases based on the technical scope and architectural changes required. 

Here is the breakdown of how we can build this out:

---

### 🟢 Phase 1: Quick Wins & Immediate UI Updates
*These are modifications we can make to the current interface almost immediately without needing to overhaul the backend data structures.*

*   **UI Decluttering:** Removing the advanced SP metrics (FIP, K-BB%) from the cards while keeping the F5 score projections prominent.
*   **AI Insight Formatting:** Updating our AI prompt so the "Matchup Insights" are generated as easily readable, hard-hitting bullet points rather than a long paragraph.
*   **Enhanced Record Display:** Adjusting the current tables to include Team Home/Away splits and Last 10 (L10) records. 
*   **Frontend Layout Foundation:** Building the toggle buttons at the top ("Daily Games" vs "NRFI/YRFI") and designing the compact, table-style List View for the NRFI model (complete with the 1-10 "Algo Score" green progress bar).

### 🟠 Phase 2: New Data Features & API Integrations
*These features require us to write new scraping logic and integrate additional data endpoints into our backend engine.*

*   **Team-Specific NRFI Records:** Scraping and calculating offensive/defensive NRFI statistics for teams (not just the starting pitchers) to populate the new UI.
*   **Team to Not Score (Team NRFI):** Implementing the logic to isolate and predict a specific team's likelihood of not scoring in the first inning.
*   **F5 and First Inning Odds:** Currently, we pull Full-Game Moneyline and Totals. We will need to integrate specific prop-market endpoints to pull the exact "1st Inning" and "First 5 Innings" lines.
*   **Sportsbook Filtering:** Customizing our API requests to filter out the noise and only pull odds from your preferred books (FanDuel, DraftKings, Fanatics, Caesars). This will also improve the app's loading speed.

### 🔴 Phase 3: Major Architectural Upgrades (The Tracking System)
*This phase involves the heaviest lifting. It transitions the application from a "Daily Predictor" into a historical tracking platform with persistent memory.*

*   **Elite Pick Result Tracking:** You mentioned wanting to track the Win/Loss record of our "High Score / Recommended" NRFI bets. To do this, we need to build an automated "Result Grader" bot that runs every morning, checks the official MLB box scores from the night before, and grades our AI's predictions as a Win or Loss.
*   **Date Selector & Archiving:** Currently, the engine overwrites data daily to show "today's slate." To support the Date Selector (clicking back to 5/18 or forward to 5/20), we must build a database/archiving architecture. This will allow the frontend to fetch historical prediction files and calculate the ongoing model Win % over time.

---

Hi Tyler,

I’ve reviewed all your recent requests. To ensure we keep the current system stable while we polish the UI, I have prioritized everything into two clear lists.

1. Currently Finalizing (Milestone 2 - Finishing Up):
I am putting the final touches on these items right now. My goal is to get this fully deployed today/tomorrow:

NRFI Table Redesign: Reorganizing the NRFI/YRFI section to feature the pitchers' Season/Last 10 records and the updated table view with streak emojis.

Weather Signals: Implementing the CBS-style alert word and the red-flag rain alerts as we discussed.

Stacked Records: Adding the Team Home/Away and L10 records (Covers style) to the main cards.

Mobile Responsiveness: Polishing the layout so it stacks perfectly on all mobile screens.

AI Insight Formatting: Switching the AI section to bullet points for better readability.

UI Polish: Updating terminology (e.g., "Bookie" to "Book") and aligning the Matchup/Details buttons.

2. Next Level - The "V3 Pro Terminal" (Milestone 3):
These features are fantastic additions that will transform this from a model viewer into a full betting terminal. Since these require significant backend architecture changes (like database archiving and new scrapers), I have categorized them for our next phase:

Model Result Tracking: Developing the "Result Grader" bot to archive outcomes and track Grade A-D performance over time.

Date Selector & History: Moving from a "daily overwrite" model to a date-stamped database so you can view past/future games.

Bookie Filtering: Adding a toggle to prioritize specific sportsbooks (FanDuel, DK, etc.).

Advanced Prop Odds: Adding F5 and 1st Inning specific lines.

I am finalizing the Milestone 2 items now. Once you check the live link and give me the green light on these updates, we can officially close out Milestone 2 and discuss the Milestone 3 plan.

Does this roadmap sound good to you?