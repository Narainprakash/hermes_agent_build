---
name: daily-reflection
description: End-of-day review for the predictor agent — prediction accuracy, calibration, and learning
---

# Predictor Daily Reflection

## Step 1: Review Today's Predictions
- Call `benki_db_query_trades` with agent="predictor" for today
- List all bets placed (Polymarket + Drift BET)

## Step 2: Check Resolved Markets
- Use web_search to check if any of your open markets have resolved
- Compare outcomes to your probability estimates

## Step 3: Calibration Check
- Calculate prediction accuracy over last 7 days
- Are you consistently over-confident or under-confident?
- Brier score: avg((forecast - outcome)^2) — lower is better

## Step 4: Update Memory
Update MEMORY.md with:
- Prediction accuracy metrics
- Calibration adjustments needed
- Market types where you perform best/worst
- Edge threshold adjustments if accuracy is poor

## Step 5: Post Summary
Post prediction performance update in #predictions.
