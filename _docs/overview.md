# Overview

A web form scraping tool. Each form field is an object containing metadata (e.g., required length, options). Form field objects are stored in a database for future access, keyed by the website name.

## User Flow (Basic Example: One URL)

1. **User initiates scrape**
   - User enters the URL of the website to scrape.
   - Presses "Start".

2. **LangGraph agent kicks off**
   - Establishes WebSocket connection with **Stagehand** and **Browserbase** agents.
   - `Create_React_Agent` loops automatically until a stopping condition is met.

3. **Agent workflow includes:**
   - **Tool Calls**
   - **Memory / State Management**

4. **Tools used:**
   - `Navigate`
   - `Fill Form Fields`
   - `Analyze Page`
   - `HITL` (Human-in-the-Loop)
     - Handles:
       - Errors
       - Email verification steps

5. **Logic and flow:**
   - Checks if login/register is required (uses DB lookup).
   - Continuously updates the JSON state of the form.
   - Agent stops when:
     - It has successfully logged in or registered.
     - It has scraped data from the target utility form pages.

6. **User visibility:**
   - The agent’s actions are visible on screen.
   - HITL steps allow user input or intervention when needed.
