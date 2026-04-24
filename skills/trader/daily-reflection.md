---
name: daily-reflection
description: End-of-day review for the trader agent — trade outcomes, strategy assessment, and learning
---

# Trader Daily Reflection

## Step 1: Review Today's Trades
- Call `benki_db_query_trades` with agent="trader" for today
- Categorize: wins, losses, dry runs

## Step 2: Assess Performance
- Calculate win rate and profit factor
- Identify largest win and largest loss
- Check if Kelly sizing was followed

## Step 3: Strategy Review
- Which MCB signals led to profitable trades?
- Which signals led to losses?
- Were any risk_check rejections correct in hindsight?

## Step 4: Update Memory
Update MEMORY.md with:
- Trading performance summary
- Patterns that worked vs didn't
- Adjustments for tomorrow's trading

## Step 5: Post Summary
Post brief performance update in #trading.
