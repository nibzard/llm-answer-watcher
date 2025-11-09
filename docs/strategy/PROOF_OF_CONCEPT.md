# Evidence-Based GEO: Proof of Concept

> **Goal**: Manually validate that API vs Browser divergence exists and is significant enough to build features around.

## Quick Validation (Do This First)

Before investing 2-3 weeks in building comparison features, validate the core assumption:

**Hypothesis**: "LLM responses differ significantly between API and Browser channels, especially for brand mentions in buyer-intent queries."

### Step 1: Manual Test (30 minutes)

```bash
# 1. Run the comparison config
export OPENAI_API_KEY="your-key"
export STEEL_API_KEY="your-steel-key"

llm-answer-watcher run \
  --config examples/internal/api-vs-browser-comparison.config.yaml

# 2. Check the output directory
ls -la output/2025-11-09T*

# Expected files:
# - intent_email-warmup_raw_openai_gpt-4o-mini.json (API)
# - intent_email-warmup_raw_chatgpt-web.json (Browser)
# - screenshot_email-warmup_chatgpt_*.png (Visual proof)
```

### Step 2: Manual Comparison (15 minutes)

Open both JSON files side-by-side and compare:

**Questions to answer:**
1. ✅ Are the responses identical? (Likely NO)
2. ✅ Do they mention different brands? (Check parsed JSON)
3. ✅ Are brand rankings different? (Check rank positions)
4. ✅ Is response length/style different? (Word count, formatting)
5. ✅ Are sources/citations different? (API tools vs Browser UI)

**Document findings:**
```markdown
## Manual Comparison Results

Query: "What are the best email warmup tools?"
Date: 2025-11-09

### API Response (gpt-4o-mini)
- Length: 342 words
- Brands mentioned: Instantly.ai (#1), Warmup Inbox (#2), Lemwarm (#3)
- Web search used: Yes (3 sources)
- Cost: $0.0012

### Browser Response (ChatGPT Web)
- Length: 398 words  (+16% longer)
- Brands mentioned: Warmup Inbox (#1), Instantly.ai (#2), Mailreach (#3), Lemlist (#4)
- Web search used: Unknown (integrated into UI)
- Cost: $0.00 (free tier)

### Divergence Analysis
- ✅ Different brand rankings (Warmup Inbox moved from #2 to #1)
- ✅ Unique brand in Browser: Mailreach, Lemlist
- ✅ Missing brand in Browser: Lemwarm
- ✅ Response style differs (Browser more conversational)

**CONCLUSION: Significant divergence detected (would benefit from automated comparison)**
```

### Step 3: Visual Evidence (10 minutes)

Create a simple side-by-side comparison for social media:

**Tool**: Any image editor or HTML

**Layout**:
```
┌─────────────────────────────┬─────────────────────────────┐
│  OpenAI API Response        │  ChatGPT Browser UI         │
├─────────────────────────────┼─────────────────────────────┤
│  [Text from API]            │  [Screenshot from Browser]  │
│                             │                             │
│  Brands mentioned:          │  Brands mentioned:          │
│  1. Instantly.ai ✓          │  1. Warmup Inbox            │
│  2. Warmup Inbox ✓          │  2. Instantly.ai ✓          │
│  3. Lemwarm                 │  3. Mailreach               │
│                             │  4. Lemlist                 │
└─────────────────────────────┴─────────────────────────────┘

⚠️ Same provider, different channel = different answers!
```

**Usage**:
- Twitter/LinkedIn post
- Blog post header image
- Conference slide

---

## If Validation Succeeds: Implementation Roadmap

### Week 1: Core Comparison Module

**Goal**: Calculate divergence metrics programmatically

#### Tasks:
1. ✅ Create `llm_answer_watcher/analysis/` module
2. ✅ Implement text similarity (cosine, Jaccard)
3. ✅ Implement brand mention diff
4. ✅ Write tests (80%+ coverage)
5. ✅ Document API in docstrings

**Deliverable**: Python module that can compare two responses and return divergence metrics

**Test**:
```python
from llm_answer_watcher.analysis.similarity import detect_divergence

api_text = "Here are top tools: Instantly.ai, Warmup Inbox, Lemwarm"
browser_text = "Popular options: Warmup Inbox, Instantly.ai, Mailreach, Lemlist"

result = detect_divergence(api_text, browser_text)
# {
#   "diverged": True,
#   "similarity_score": 0.68,
#   "analysis": {
#     "unique_to_api": ["Lemwarm"],
#     "unique_to_browser": ["Mailreach", "Lemlist"]
#   }
# }
```

---

### Week 2: Visual Comparison Report

**Goal**: Generate beautiful HTML reports showing side-by-side comparisons

#### Tasks:
1. ✅ Create Jinja2 template: `comparison_report.html.j2`
2. ✅ Implement report generator: `comparison_generator.py`
3. ✅ Query database for paired responses (API + Browser)
4. ✅ Add screenshot embedding in HTML
5. ✅ Write tests for report generation

**Deliverable**: HTML report generator

**Test**:
```python
from llm_answer_watcher.report.comparison_generator import generate_comparison_report

report_path = generate_comparison_report(
    run_id="2025-11-09T10-00-00Z",
    db_path="./llm_answers.db",
    output_path="./comparison-report.html"
)

# Opens in browser:
# - Side-by-side layout
# - Divergence alerts
# - Screenshot comparison
# - Summary statistics
```

---

### Week 3: CLI Integration

**Goal**: Make comparison reports accessible via CLI

#### Tasks:
1. ✅ Add `compare` command to CLI
2. ✅ Add `--format` flag for output (HTML, JSON, CSV)
3. ✅ Add `--threshold` flag for divergence sensitivity
4. ✅ Update documentation
5. ✅ Write integration tests

**Deliverable**: CLI command

**Test**:
```bash
# Generate comparison report
llm-answer-watcher compare \
  --run-id 2025-11-09T10-00-00Z \
  --output ./comparison.html \
  --threshold 0.85

# Output:
# ✓ Found 5 paired responses (API + Browser)
# ⚠️ 3 of 5 queries diverged (60.0%)
# ✓ Report saved: ./comparison.html
```

---

### Week 4: Trend Analysis

**Goal**: Track divergence rates over time

#### Tasks:
1. ✅ Create SQL query for trend analysis
2. ✅ Add `trends` command to CLI
3. ✅ Generate trend charts (matplotlib or Chart.js)
4. ✅ Add alert system for unusual changes
5. ✅ Write documentation

**Deliverable**: Trend tracking system

**Test**:
```bash
# Show divergence trends
llm-answer-watcher trends \
  --provider openai \
  --days 30 \
  --output ./trends.html

# Output:
# 📊 OpenAI API vs Browser Divergence (30 days)
#
# Average divergence: 58.3%
# Trend: ↑ +12% over last 7 days
# Alert: Significant change detected on 2025-11-07
```

---

## Marketing & Positioning Timeline

### Month 1: Build + Validate

**Week 1-2**: Implement comparison module + report generator
**Week 3**: Run comparison on 100+ queries, document findings
**Week 4**: Write draft research report

### Month 2: Launch Campaign

**Week 1**: Publish research report + blog post
**Week 2**: Social media campaign (Twitter, LinkedIn, Reddit)
**Week 3**: Submit conference talks (BrightonSEO, MozCon)
**Week 4**: Create public dashboard

### Month 3: Measure Impact

**Week 1-4**: Track metrics (downloads, stars, citations)

---

## Success Criteria (Proof of Concept)

### Must Have (Validate these manually first)

1. ✅ **Divergence exists**: At least 30% of queries show significant differences
2. ✅ **Brand mentions differ**: At least 20% of queries have unique brand mentions per channel
3. ✅ **Screenshots compelling**: Visual evidence is convincing/shareable
4. ✅ **Story is clear**: "You can't trust API results to match Browser UI"

### Nice to Have (Validate if time permits)

1. ⭐ **Rank changes**: Brand rankings differ significantly (>2 positions)
2. ⭐ **Temporal changes**: Same query run 1 week apart shows different results
3. ⭐ **Provider patterns**: Some providers diverge more than others
4. ⭐ **Query type correlation**: Certain query types trigger more divergence

---

## Next Actions (Prioritized)

### IMMEDIATE (Do Today)

1. ✅ **Share strategy doc** with team/advisors for feedback
2. ✅ **Run manual test** (30 min): Execute comparison config, document findings
3. ✅ **Create visual mockup** (15 min): Side-by-side comparison for social media

### THIS WEEK

1. 🛠️ **Validate demand** (2 hours):
   - Post on Twitter: "Would you care if ChatGPT API != ChatGPT Browser?"
   - Post on Reddit r/SEO: "Anyone else notice API responses differ from web UI?"
   - Email 5 potential users/beta testers

2. 🛠️ **Create PoC artifacts** (4 hours):
   - Run 10 queries through API + Browser
   - Manually compare and document findings
   - Create 3-5 comparison screenshots
   - Draft Twitter thread

### NEXT WEEK (If Validation Succeeds)

1. 🚀 **Start implementation**: Begin Week 1 tasks (comparison module)
2. 📝 **Draft research report outline**: "The API vs Browser Gap"
3. 🎨 **Design report template**: Mockup comparison HTML report

---

## Open Questions (Answer During PoC)

1. **How much divergence is "significant"?**
   - 50%? 70%? 90% text similarity?
   - What threshold triggers an alert?

2. **What matters most: text similarity or brand mentions?**
   - Users care about brands appearing/disappearing
   - Or full answer accuracy?

3. **How often do responses diverge?**
   - If only 10% diverge, is that enough for a campaign?
   - If 90% diverge, is that expected or surprising?

4. **Which providers diverge most?**
   - OpenAI? Anthropic? Google?
   - Is there a pattern?

5. **What causes divergence?**
   - System prompts?
   - Web search behavior?
   - Model version differences?
   - A/B testing on browser UI?

---

## Risk Mitigation

### Risk: "No one cares about divergence"

**Mitigation**: Validate demand BEFORE building
- Twitter poll
- Reddit discussion
- User interviews

**Decision point**: If <50 people express interest, reconsider priority

### Risk: "Divergence is too low to be interesting"

**Mitigation**: Test with buyer-intent queries specifically
- Focus on commercial queries where brand mentions matter
- Not general knowledge questions

**Decision point**: If <30% divergence rate, pivot messaging

### Risk: "Implementation takes too long"

**Mitigation**: Start with manual process
- Generate comparison reports manually for first 10 users
- Validate value before automating

**Decision point**: If manual reports get traction, prioritize automation

---

## Conclusion

**Proof of Concept Goals**:
1. ✅ Validate divergence exists (manual test)
2. ✅ Validate users care (social media poll)
3. ✅ Create compelling visual evidence (screenshots)
4. ✅ Document findings (research notes)

**Timeline**: 1 week for validation, 3-4 weeks for implementation

**Investment**: ~40 hours of focused development

**Payoff**: Thought leadership position, inbound marketing, conference talks, GitHub stars

**Next Step**: Run the manual test and share findings.

---

**Status**: READY FOR VALIDATION
**Created**: 2025-11-09
**Owner**: Claude (Strategic AI Assistant)
