# 🎬 RootSense for SAC — Video Recording & Demo Script

> **Target Video Length:** 5 to 6 minutes (ideal for executive & client showcases).  
> **Formatting Guide:**  
> - 🎥 **[ON SCREEN / ACTION]** tells you exactly where to click or hover your mouse.  
> - 🎙️ **"NARRATION"** is your word-for-word speaking script—read it naturally at a steady pace.

---

## 🛠️ Pre-Recording Setup Checklist (Do This Before Hitting Record)

1. **Start the RootSense Streamlit Dashboard:**
   ```powershell
   .\.venv\Scripts\python.exe -m streamlit run frontend/streamlit_app.py
   ```
2. *(Optional)* **Start the Standalone Neuro-SAN Studio `nsflow` UI** (if you also want to show port `4173` in a second browser tab):
   ```powershell
   .\start_neurosan.ps1
   ```
3. **Browser Prep:**
   - Open `http://localhost:8501` in full-screen (`F11`) or at **100% browser zoom**.
   - Click **Reset Presentation Session** in the left sidebar (then collapse the sidebar) so the dashboard starts in a clean `IDLE` state with the **🕸️ Neuro-SAN Logical Path** tab visible on the right.

---

## ⏱️ Scene-by-Scene Recording Script

### Scene 1: The Hook & Business Problem (0:00 – 0:55)

🎥 **[ON SCREEN / ACTION]**  
Start on the main **RootSense for SAP Analytics Cloud (SAC)** dashboard (`http://localhost:8501`). Slowly move your cursor across the top banner badges (`[🟢 Gemini 1.5 Active]`, `[🟢 Mock SAC REST Gateway Online]`, `[🟢 IT4You API Bridge Ready]`, `[🟣 Neuro-SAN nsflow Active]`).

🎙️ **"NARRATION"**  
> "Hi everyone. Today I’m excited to walk you through **RootSense for SAP Analytics Cloud**—an enterprise **Neuro-Symbolic Multi-Agent Diagnostic Assistant** built using **Cognizant’s Neuro-SAN framework** and **Google Gemini**."
>
> "In large enterprise financial planning environments running SAP Analytics Cloud—or SAC—financial analysts constantly run into frustrating data discrepancies during budget and forecast cycles:
> - A planner enters a `$70,000` travel budget, and 15 minutes later it mysteriously drops to `$52,000`.
> - Or they update headcount numbers, and their director says, *'I can’t see your numbers in the report.'*
> - Or regional Gross Margin percentages don't add up across columns."
>
> "Today, analysts raise hundreds of L1 and L2 IT support tickets for these issues. IT teams then spend hours manually digging through SAC Data Change Logs, Multi-Action batch schedules, Data Locking consoles, and Version Management tables—even when 65% of those tickets are actually user-fixable."
>
> "**RootSense for SAC** eliminates that bottleneck. Instead of letting an LLM guess or hallucinate why a number changed, RootSense combines **Neuro-SAN decentralized multi-agent routing** with a **deterministic 7-step symbolic verification engine** that inspects live SAC audit logs, model metadata, and enterprise knowledge bases—resolving user-fixable issues on the spot and auto-drafting L3 engineering tickets with complete forensic evidence when a true system issue occurs."

---

### Scene 2: Neuro-SAN (`nsflow`) Architecture Overview (0:55 – 1:50)

🎥 **[ON SCREEN / ACTION]**  
Point your cursor at the **Interactive Neuro-SAN `nsflow` Topology Canvas** on the right side of the screen (inside the **🕸️ Neuro-SAN Logical Path** tab). Highlight the three tiers:
1. `SupervisorOrchestrator` (Front-Man)
2. `SACDiagnosticAgent` & `KnowledgeBaseAgent` (AAOSA Specialists)
3. `SACAuditDiagnosticTool`, `IT4YouTicketingTool`, and `EnterpriseKBRAGTool` (CodedTools) + the `sly_data` purple bar at the bottom.

🎙️ **"NARRATION"**  
> "Before we run our first live scenario, let’s look at the **Neuro-SAN `nsflow` Agent Topology** on the right panel, which is declaratively defined in `registries/rootsense_sac.hocon`."
>
> "Our architecture follows Cognizant’s **AAOSA protocol—Adaptive Agent-Oriented Software Architecture**:
> 1. At the top is our **Front-Man**, the `SupervisorOrchestrator`.
> 2. When a user asks a question, the Front-Man broadcasts the inquiry in **`Determine` mode** to its down-chain specialists: the `SACDiagnosticAgent` and the `KnowledgeBaseAgent`. Each specialist returns a relevance claim and a confidence strength from 1 to 10.
> 3. The Front-Man then invokes the winning specialist in **`Fulfill` mode**, which executes deterministic Python **CodedTools** against the SAC REST Gateway, ServiceNow, Confluence, and IT4You ticketing.
> 4. Notice the **`sly_data` Private State Bus** at the bottom: sensitive cell coordinates, audit payloads, and ticket drafts travel through `sly_data` out-of-band so the LLM can never corrupt or hallucinate structured system data."

---

### Scene 3: Scenario 1 — Nightly Scheduler Overwrite & Auto-Ticketing (1:50 – 3:15)

🎥 **[ON SCREEN / ACTION]**  
1. On the left panel, hover over **Scenario 1 Card** (`Scenario 1 • System Overwrite` — *"Why did my Travel Expense entry drop from 70K to 52K?"*) and click **Run Scenario 1: Travel Expense Drop**.
2. Pause 2 seconds as the **Neuro-SAN `nsflow` graph** lights up with green and amber animated signal lines!
3. Hover over the `SACDiagnosticAgent` node (`FULFILL ★`, `Strength: 9/10`) and the glowing amber `IT4YouTicketingTool` node.
4. Scroll slightly down on the right panel to show the **7-Step Neuro-Symbolic SAC Planning Diagnostic Checklist**.

🎙️ **"NARRATION"**  
> "Let’s test **Scenario 1**: An analyst asks, *'Why did my Travel Expense entry drop from 70K to 52K?'*"
>
> "Look at the **Neuro-SAN `nsflow` graph** on the right immediately light up:
> - In AAOSA `Determine` mode, `SACDiagnosticAgent` claimed the query with a strength of **9 out of 10**, beating `KnowledgeBaseAgent` at **2 out of 10**.
> - `SACDiagnosticAgent` entered `Fulfill` mode and ran our **7-Step Neuro-Symbolic Diagnostic Checklist**:
>   - **Step 1 & 2** captured the coordinates—Account `EXP_TRAVEL_ENTERTAINMENT`, Cost Center `CC_NA_1020`, Version `Public.Forecast_2025`, Period `202509`—and queried the SAC Data Change Log.
>   - **Step 3** evaluated the actor and caught the culprit: a system batch job!"

🎥 **[ON SCREEN / ACTION]**  
Click the second tab on the right panel: **📊 SAC Cell & Audit Log Inspector**. Point to the **4 KPI coordinate cards**, the **DataFrame**, and the **Chronological Cell Modification Timeline** at the bottom (`MANUAL ANALYST EDIT` vs `SYSTEM BATCH OVERWRITE`).

🎙️ **"NARRATION"**  
> "Switching to the **SAC Cell & Audit Log Inspector** tab, we see the exact forensic timeline pulled from the SAC API:
> - At **10:14 UTC**, `analyst.user@cognizant.com` manually edited the cell from `45,000` to `70,000`.
> - Just 16 minutes later, at **10:30 UTC**, `SYSTEM_SAC_SCHEDULER` executed the Multi-Action `DA_OVERHEAD_ALLOCATION`, overwriting the cell in `Public.Forecast_2025` down to `52,000`."

🎥 **[ON SCREEN / ACTION]**  
Move your cursor to the bottom of the **Left Panel** where the amber **⚠️ Administrative / L3 Escalation Required (`SYSTEM_OVERWRITE`)** banner appears, and click the **`⚡ Submit IT4You Ticket on My Behalf`** button. Then click the **🎫 Generated IT4You Ticket Payload** tab on the right panel.

🎙️ **"NARRATION"**  
> "Because an analyst cannot modify nightly Multi-Action allocation rules in a Public version, RootSense classifies this as **`SYSTEM_OVERWRITE` (Not User-Fixable)** and automatically pre-assembles a **P2 - High** escalation brief in `sly_data`."
>
> "With a single click on **Submit IT4You Ticket on My Behalf**, the ticket is validated by Pydantic, assigned to the **`SAP-BTP-PLANNING-L3`** queue with a 4-hour SLA, and persisted. On the **Generated IT4You Ticket Payload** tab, L3 engineers receive the exact cell coordinates and audit timestamps—zero back-and-forth required."

---

### Scene 4: Scenario 2 — Private Draft Version Mismatch (Ticket Deflection) (3:15 – 4:05)

🎥 **[ON SCREEN / ACTION]**  
1. Click **Scenario 2 Card** on the left (`Scenario 2 • Private Draft` — *"I updated headcount in Draft but my manager cannot see it."*).
2. Click back to the **🕸️ Neuro-SAN Logical Path** tab on the right. Notice that `SACAuditDiagnosticTool` is active (green), while `IT4YouTicketingTool` stays idle!
3. Scroll the left chat response to show the **4-Step Version Management Publish Guide**.

🎙️ **"NARRATION"**  
> "Now let’s look at **Scenario 2**: *'I updated headcount in Draft, but my manager cannot see it.'*"
>
> "Watch the `nsflow` topology: `SACDiagnosticAgent` invokes `SACAuditDiagnosticTool`, which discovers in **Step 4** that the analyst's edits on `EXP_HEADCOUNT` are sitting inside an unpublished private version—`Private.Draft_v1`—while their manager is viewing `Public.Forecast_2025`."
>
> "Notice that `IT4YouTicketingTool` **did not fire**. Why? Because RootSense knows this is **`VERSION_MISMATCH`—100% user-fixable!** Instead of flooding IT with a ticket, RootSense deflects the ticket and gives the analyst the exact 4-step workflow inside SAC’s **Version Management** panel to publish `Private.Draft_v1` to `Public.Forecast_2025`."

---

### Scene 5: Scenario 3 — Non-Additive Formula Rollup (`MARGIN_PCT`) (4:05 – 4:45)

🎥 **[ON SCREEN / ACTION]**  
1. Click **Scenario 3 Card** on the left (`Scenario 3 • Formula Rollup` — *"Why doesn't Total Gross Margin % sum up across columns?"*).
2. Show **Step 5 (`Evaluate Aggregation & Formula Metadata`)** in the checklist on the right, and briefly click **📊 SAC Cell & Audit Log Inspector** to show the metadata record (`FORMULA: [Gross Margin]/[Revenue]`, `rollup_behavior: WEIGHTED_AVG`).

🎙️ **"NARRATION"**  
> "In **Scenario 3**, the analyst asks why **Total Gross Margin %** doesn't simply sum up across regional columns."
>
> "Here, RootSense doesn't even need change-log edits—in **Step 5**, it inspects the SAC Model Metadata for `MARGIN_PCT`. It proves that `MARGIN_PCT` uses `FORMULA` aggregation (`[Gross Margin]/[Revenue]`) with a `WEIGHTED_AVG` hierarchy rollup. Adding percentages horizontally across regions is mathematically invalid, so SAC recalculates the ratio at the parent node. Again, RootSense explains the exact formula math and prevents a false bug report."

---

### Scene 6: Scenario 4 — Enterprise Knowledge Base RAG (VPN / SSO) (4:45 – 5:25)

🎥 **[ON SCREEN / ACTION]**  
1. Click **Scenario 4 Card** on the left (`Scenario 4 • VPN / SSO RAG` — *"I'm having SSO errors when logging onto the corporate VPN."*).
2. Switch to the **🕸️ Neuro-SAN Logical Path** tab on the right and point out how the **right-hand branch** of the `nsflow` graph (`KnowledgeBaseAgent` -> `EnterpriseKBRAGTool`) is now glowing blue (`Strength: 9/10`)!
3. Click the **📚 Knowledge Base Matches** tab on the right to show the retrieved ServiceNow Incident (`INC0088231`) and Confluence SOP cards with match confidence bars.

🎙️ **"NARRATION"**  
> "What if a user asks a general IT or connectivity question, like **Scenario 4**: *'I'm having SSO errors when logging onto the corporate VPN'*?"
>
> "Look at the **Neuro-SAN `nsflow` graph** now: the signal automatically shifts to the right branch! `KnowledgeBaseAgent` wins the AAOSA `Determine` bid with **9 out of 10** and triggers `EnterpriseKBRAGTool`."
>
> "In the **Knowledge Base Matches** tab, our hybrid semantic + lexical RAG engine retrieves ServiceNow incident **`INC0088231`** (*VPN SSO Connection Timeout to SAC Tenant*) and guides the user to refresh their SAML 2.0 token and verify Global Secure Tunnel client `v4.2`."

---

### Scene 7: Under-the-Hood Inspection & Closing Summary (5:25 – 6:00)

🎥 **[ON SCREEN / ACTION]**  
On the **🕸️ Neuro-SAN Logical Path** tab, click the expander at the bottom: **`Inspect Live sly_data Private Channel & rootsense_sac.hocon`**. Scroll briefly through the live `sly_data` JSON and the declarative HOCON file.

🎙️ **"NARRATION"**  
> "Finally, opening the developer drawer at the bottom of the inspector, we can see the live **`sly_data` private dictionary** alongside our declarative **`rootsense_sac.hocon`** agent network definition—which can also be launched directly in standalone **Neuro-SAN Studio (`nsflow`)** on port `4173` using `start_neurosan.ps1`."
>
> "Backed by a FastAPI service layer and 28 end-to-end automated pytest tests, **RootSense for SAC** delivers three measurable outcomes for enterprise finance and IT operations:
> 1. **60%+ L1/L2 Ticket Deflection** for user-fixable version and formula questions.
> 2. **Zero-Hallucination Root-Cause Forensics** grounded in deterministic SAC audit logs.
> 3. **Instant L3 Escalation Readiness** via automated IT4You ticket payloads."
>
> "Thank you for watching!"
