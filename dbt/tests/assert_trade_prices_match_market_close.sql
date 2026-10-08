{{ config(severity='warn') }}

-- Data quality check: every logged trade should have a real stock price on its trade date,
-- and the price paid should match that day's close (within 1 cent).
-- Returns the trades that fail. Set to 'warn' because a trade log is manually entered.
select
    t.trade_id,
    t.ticker,
    t.trade_date,
    t.price_paid_usd,
    p.close_price_usd
from {{ ref('stg_trades') }} t
left join {{ ref('stg_stock_prices') }} p
    on  p.ticker = t.ticker
    and p.price_date = t.trade_date
where p.price_key is null
   or abs(t.price_paid_usd - p.close_price_usd) > 0.01
